"""Reproduce all pilot calculations, tables and figures. Run from any directory.

python run_study.py --out results
python -m unittest -v test_models.py
"""
import argparse, csv, json, sys, platform, time, hashlib
from pathlib import Path
import numpy as np
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from model import *

ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/'config.json').read_text())
REF=json.loads((ROOT/'references.json').read_text())
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
    'figure.dpi':130,'savefig.dpi':180,'axes.titleweight':'bold'})


def csvwrite(path, rows):
    if not rows: return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)


def savefig(fig,out,name):
    fig.savefig(out/(name+'.png'),bbox_inches='tight')
    fig.savefig(out/(name+'.svg'),bbox_inches='tight')
    plt.close(fig)


def run(out):
    start=time.perf_counter();out.mkdir(parents=True,exist_ok=True)
    T=CFG['temperature_K']; P=CFG['pressure_Pa']
    species=['CO','CO2','acetone','isoprene','H2O2','N2','O2']
    rows=[]; curves={}; budgets=[]
    for name in species:
        ref=REF[name+'_H'];H=ref['Hcp_mol_m3_Pa']
        if name in CFG['wet_mole_fraction_ppm']:
            ppm=CFG['wet_mole_fraction_ppm'][name]
        else:
            ppm=CFG['dry_air_mole_fractions'][name]*(1-saturation(T)/P)*1e6
        for mode,vl,a in [('bulk',CFG['bulk_water_volume_m3'],1e-5),
                          ('fog',CFG['fog_LWC_kg_m3']/1000,CFG['fog_radius_m']),
                          ('mist',CFG['fog_LWC_kg_m3']/1000,CFG['mist_radius_m'])]:
            tt=np.r_[0,np.geomspace(1e-5,CFG['partition_end_s'],300)]
            y,f,k,kla=partition(H,T,1,vl,tt,mode=mode,radius=a,
                Dg=CFG['gas_diffusivity_m2_s_assumed'],
                Dl=CFG['liquid_diffusivity_m2_s_assumed'],
                bulk_kLa=CFG['bulk_kLa_s_1_assumed'])
            n0=ppm*1e-6*P/(R*T);ng=n0*(1-y);nl=n0*y
            err=float(np.max(abs(ng+nl-n0))/n0)
            r=dict(species=name,medium=mode,T_K=T,P_Pa=P,RH_percent=100,
                initial_gas_ppm=ppm,gas_volume_m3=1,liquid_volume_m3=vl,
                radius_m=a if mode!='bulk' else '',Hcp_mol_m3_Pa=H,
                liquid_gas_concentration_ratio=H*R*T,kLa_s_1=kla,
                relaxation_rate_s_1=k,t90_s=np.log(10)/k,
                equilibrium_aqueous_percent=f*100,aqueous_percent_600s=y[-1]*100,
                final_liquid_mol_m3=nl[-1]/vl,initial_moles=n0,
                final_gas_moles=ng[-1],final_liquid_moles=nl[-1],
                relative_mole_budget_error=err,
                analytic_max_fraction_error=float(np.max(abs(y-f*(-np.expm1(-k*tt))))),
                chemistry='Physical partitioning only; CO2 carbonate handled separately' if name=='CO2' else 'None in this model',
                status='SIMULATED',source=ref['url'],
                limitation='Fixed water volume; dilute ideal solution; assumed transfer coefficients')
            rows.append(r);curves[(name,mode)]=(tt,y/f)
            budgets.append(dict(case=f'partition_{name}_{mode}',quantity='solute_moles',
                initial=n0,final=ng[-1]+nl[-1],relative_residual=err,
                interpretation='gas+liquid conserved'))
    csvwrite(out/'partition_results.csv',rows)
    fig,ax=plt.subplots(1,2,figsize=(11,4.4),layout='constrained')
    show=species[:5];xx=np.arange(len(show)); width=.36
    for j,mode in enumerate(['bulk','fog']):
        yy=[next(r['equilibrium_aqueous_percent'] for r in rows if r['species']==s and r['medium']==mode) for s in show]
        ax[0].bar(xx+(j-.5)*width,yy,width,label='1 L bulk water' if j==0 else '0.5 g fog water')
    ax[0].set(yscale='log',xticks=xx,xticklabels=show,ylabel='Solute inventory in water at equilibrium (%)',
              title='Water affinity × available water',ylim=(1e-7,200))
    ax[0].legend(fontsize=9);ax[0].grid(axis='y',alpha=.2)
    for s in show:
        tt,frac=curves[(s,'fog')];ax[1].semilogx(tt[1:],frac[1:],label=s)
    ax[1].set(xlabel='Time (s)',ylabel='Fraction of each species’ equilibrium uptake',
              title='Fog uptake transient',ylim=(0,1.04));ax[1].legend(fontsize=9)
    fig.suptitle('Closed 1 m³ gas, 25 °C, 1 atm. Physical partitioning; no reactions.',fontsize=12)
    savefig(fig,out,'partitioning')

    carb=[]
    for mode,vl in [('bulk',.001),('fog',5e-7)]:
        s=carbonate_closed(Vl=vl)
        s.update(medium=mode,liquid_volume_m3=vl,aqueous_percent=100*s['aqueous_carbon_mol']/s['initial_carbon_mol'],
                 status='EQUILIBRIUM_SOLVED_NOT_KINETIC',source=REF['USGS2012']['url'])
        carb.append(s)
        budgets.append(dict(case='carbonate_'+mode,quantity='carbon_moles',initial=s['initial_carbon_mol'],
            final=s['gas_carbon_mol']+s['aqueous_carbon_mol'],
            relative_residual=abs(s['carbon_residual_mol'])/s['initial_carbon_mol'],interpretation='CO2*+HCO3-+CO3--+gas carbon'))
    csvwrite(out/'carbonate_results.csv',carb)

    kin=[]
    for oh in [0,1e5,1e6,1e7]:
        for multiplier in ([1] if oh==0 else [10**-.05,1,10**.05]):
            zz=co_oh_kinetics(OH_molecules_cm3=oh,multiplier=multiplier)
            kin.append({k:v for k,v in zz.items() if not isinstance(v,np.ndarray)} |
                dict(OH_initial_molecules_cm3=oh,rate_multiplier=multiplier,status='SIMULATED_REDUCED_LOW_PRESSURE_CHEMISTRY'))
            budgets.append(dict(case=f'CO_OH_{oh}_{multiplier}',quantity='C_O_H_atom_moles',
                initial='see kinetics_results.csv',final='see kinetics_results.csv',
                relative_residual=zz['atom_relative_error'],interpretation='CO+OH -> CO2+H; finite OH; no replenishment'))
            if oh==1e6 and multiplier==1: kinetics=zz
    csvwrite(out/'kinetics_results.csv',kin)
    csvwrite(out/'kinetics_timeseries.csv',[dict(time_s=t,CO_mol=kinetics['moles'][0,i],OH_mol=kinetics['moles'][1,i],
        CO2_mol=kinetics['moles'][2,i],H_mol=kinetics['moles'][3,i]) for i,t in enumerate(kinetics['times_s'])])

    sens=[]
    for s in species[:5]:
        ref=REF[s+'_H']
        for temp in [278.15,288.15,298.15,308.15]:
            for lwc in [.0001,.0005,.001]:
                for a in [5e-6,1e-5,25e-6]:
                    H=henry(ref['Hcp_mol_m3_Pa'],ref['slope_K'],temp)
                    f,k,kla=transfer_parameters(H,temp,1,lwc/1000,'fog',radius=a)
                    sens.append(dict(species=s,T_K=temp,LWC_kg_m3=lwc,radius_m=a,
                        Hcp_mol_m3_Pa=H,equilibrium_aqueous_percent=100*f,t90_s=np.log(10)/k,
                        aqueous_percent_600s=100*f*(-np.expm1(-k*600)),
                        status='ANALYTIC_SENSITIVITY',RH_percent=100))
    csvwrite(out/'partition_sensitivity.csv',sens)
    # Assumed uncertainty distributions, NOT inferred confidence intervals.
    unc=[];rng=np.random.default_rng(20261010)
    for s in species[:5]:
        count=4000;h0=REF[s+'_H']['Hcp_mol_m3_Pa']
        hs=rng.uniform(1.3e-4,3.4e-4,count) if s=='isoprene' else h0*np.exp(rng.normal(0,np.log(1.3),count))
        lwc=rng.uniform(.0001,.001,count);radii=rng.uniform(5e-6,25e-6,count)
        dgs=2e-5*np.exp(rng.normal(0,np.log(2),count));dls=2e-9*np.exp(rng.normal(0,np.log(2),count))
        vals=[]
        for h,l,a,dg,dl in zip(hs,lwc,radii,dgs,dls):
            f,k,_=transfer_parameters(h,T,1,l/1000,'fog',radius=a,Dg=dg,Dl=dl)
            vals.append([100*f,100*f*(-np.expm1(-k*600)),np.log(10)/k])
        q=np.quantile(vals,[.05,.5,.95],axis=0)
        for i,metric in enumerate(['equilibrium_aqueous_percent','aqueous_percent_600s','t90_s']):
            unc.append(dict(species=s,metric=metric,p05=q[0,i],median=q[1,i],p95=q[2,i],samples=count,
                seed=20261010,interpretation='Assumption-driven 5-95% range; not measured uncertainty or a confidence interval'))
    csvwrite(out/'assumption_uncertainty.csv',unc)

    refinement=[]
    for n in [24,48,96,192]:
        dx=.1/n; dt=.4/(.013/dx+4*2e-5/dx**2)
        z=transport(n=n,dt=dt,snapshots=(n==96))
        refinement.append(dict(study='grid',n=n,dt_s=z['dt'],relative_L2=z['relative_L2'],mass_error=z['mass_error_no_sink'],minimum=z['minimum']))
        if n==96: baseline=z
    for dt in [.02,.01,.005]:
        z=transport(n=48,dt=dt)
        refinement.append(dict(study='time',n=48,dt_s=z['dt'],relative_L2=z['relative_L2'],mass_error=z['mass_error_no_sink'],minimum=z['minimum']))
    csvwrite(out/'transport_refinement.csv',refinement)
    fig,ax=plt.subplots(1,3,figsize=(12,3.8),layout='constrained')
    for a,(t,c) in zip(ax,baseline['frames']):
        im=a.imshow(c,origin='lower',extent=[0,10,0,10],vmin=.5,vmax=1.5,cmap='viridis')
        a.set(title=f't = {t:g} s',xlabel='x (cm)',ylabel='y (cm)')
    fig.colorbar(im,ax=ax,label='CO concentration (ppm, mean = 1)')
    fig.suptitle('Advection and diffusion in a periodic 10 × 10 cm domain; no chemistry',fontsize=12)
    savefig(fig,out,'mixing_fields')
    np.savez_compressed(out/'mixing_fields.npz',initial=baseline['initial'],final=baseline['field'],
                        analytic=baseline['exact'],x_m=baseline['x'])
    controls=[]
    for rh in [0,50,100]:
        z=transport(n=48,dt=.01)
        controls.append(dict(case=f'CO_in_air_RH{rh}',RH_percent=rh,chemical_conversion_fraction=0,
            mean_CO_ppm=z['mean'],relative_L2=z['relative_L2'],
            note='Identical fixed flow and D by design; humid mixture is all gas, no droplets'))
    for u in [0,.01,.03]:
        z=transport(n=48,dt=.005,u=u)
        controls.append(dict(case='flow_sensitivity',u_m_s=u,mean_CO_ppm=z['mean'],relative_L2=z['relative_L2'],
            note='Changes spatial distribution, not total inventory'))
    no_diff=transport(n=48,dt=.01,u=0,v=0,diffusivity=0)
    controls.append(dict(case='no_transport',max_field_change=float(abs(no_diff['field']-no_diff['initial']).max())))
    csvwrite(out/'transport_controls.csv',controls)
    budgets.append(dict(case='2D_CO_transport',quantity='domain_mean_CO_ppm',initial=1,
        final=baseline['mean'],relative_residual=abs(baseline['mean']-1),interpretation='Periodic boundaries, no chemical source/sink'))

    scrows=[]
    for smoke_a in [5e-8,1e-7,5e-7,1e-6]:
        for drop_a in [5e-6,1e-5,25e-6]:
            for stick in [0,.1,1]:
                z=brownian_scavenging(a=smoke_a,droplet_radius=drop_a,sticking=stick)
                scrows.append(dict(smoke_radius_m=smoke_a,drop_radius_m=drop_a,sticking=stick,**z,
                    status='IDEALIZED_DIFFUSION_ONLY',limitation='No activation, phoresis, impaction or measured smoke collection efficiency'))
    csvwrite(out/'smoke_scavenging.csv',scrows)
    coag=[]
    for radius,density,label in [(1e-7,1800,'smoke_surrogate'),(1e-5,1000,'water_droplet')]:
        _,D,_=mobility(radius)
        K=16*np.pi*D*radius
        single_mass=density*4*np.pi*radius**3/3
        for number in ([1e9,1e12] if label=='smoke_surrogate' else [1e8]):
            for sticking in [0,.1,1]:
                remaining=number/(1+.5*K*sticking*number*600)
                mean_mass=single_mass*number/remaining
                coag.append(dict(material=label,radius_m=radius,initial_number_m3=number,
                    sticking=sticking,kernel_m3_s=K*sticking,end_s=600,
                    final_number_m3=remaining,initial_mass_kg_m3=single_mass*number,
                    final_mass_kg_m3=mean_mass*remaining,mean_aggregate_mass_kg=mean_mass,
                    number_reduction_percent=100*(1-remaining/number),
                    status='ANALYTIC_CONSTANT_KERNEL_POPULATION_BALANCE',
                    limitation='Assumed sticking. No fragmentation, restructuring, hydrodynamic interaction or evolving size-dependent kernel. Water coalescence only if sticking succeeds.'))
                budgets.append(dict(case=f'coagulation_{label}_{number}_{sticking}',quantity='particle_material_kg_m3',
                    initial=single_mass*number,final=mean_mass*remaining,
                    relative_residual=abs(mean_mass*remaining/(single_mass*number)-1),
                    interpretation='Aggregate count changes; material mass conserved'))
    csvwrite(out/'agglomeration_coalescence.csv',coag)
    sc=brownian_scavenging()
    # Short 2D smoke tracer run uses number concentration normalization; capture
    # reservoir is a mass-equivalent count, not destruction of particle material.
    z=transport(n=48,dt=.01,decay=sc['rate_s_1'])
    budgets.append(dict(case='2D_smoke_plus_captured',quantity='normalized_particle_material',initial=1,
        final=z['mean']+z['captured'],relative_residual=abs(z['mean']+z['captured']-1),
        analytic_sink_error=z['sink_analytic_error'],interpretation='Airborne material + captured material conserved; particle number would change on coagulation'))

    erows=[];edata={};traces={}
    # Separate large droplets and smaller aerosol pairs.
    for regime,a,q,r0,end,dt in [('droplet',1e-5,1000,2e-4,10,.01),('aerosol',1e-6,100,2e-5,1,.0005)]:
        for label,q2 in [('like',q),('neutral',0),('opposite',-q)]:
            values=[];stops=[]
            for seed in CFG['particle_seeds']:
                zz=particle_pairs(a=a,q1_e=q if label!='neutral' else 0,q2_e=q2,r0=r0,
                    end=end,dt=dt,samples=CFG['pairs_per_seed'],seed=seed)
                values.extend(zz['final_separation_m']);stops.append(zz['stopped_fraction'])
                erows.append(dict(regime=regime,charge_case=label,seed=seed,n=CFG['pairs_per_seed'],radius_m=a,
                    q1_e=q if label!='neutral' else 0,q2_e=q2,initial_separation_m=r0,end_s=end,dt_s=dt,
                    mean_separation_m=np.mean(zz['final_separation_m']),sd_separation_m=np.std(zz['final_separation_m'],ddof=1),
                    reached_validity_boundary_fraction=zz['stopped_fraction']))
                if seed==CFG['particle_seeds'][0]:traces[(regime,label)]=zz
            vals=np.array(values); edata[(regime,label)]=dict(mean_m=float(vals.mean()),
                sd_m=float(vals.std(ddof=1)),sem_m=float(vals.std(ddof=1)/np.sqrt(len(vals))),
                p05_m=float(np.quantile(vals,.05)),p95_m=float(np.quantile(vals,.95)),
                n=len(vals),stopped_fraction=float(np.mean(stops)))
    csvwrite(out/'charge_seeds.csv',erows)
    csvwrite(out/'charge_summary.csv',[dict(regime=k[0],charge_case=k[1],**v) for k,v in edata.items()])
    fig,axes=plt.subplots(1,3,figsize=(12,4.2),layout='constrained')
    colors=['#3155a4','#b43b4b']
    for ax,label in zip(axes,['like','neutral','opposite']):
        zz=traces[('droplet',label)]
        for pair in range(3):
            for p in range(2):
                tr=zz['traces_m'][:,pair,p,:]*1e6
                ax.plot(tr[:,0],tr[:,1],color=colors[p],alpha=.65,lw=1)
                ax.scatter(tr[0,0],tr[0,1],s=24,marker='o',color=colors[p])
                ax.scatter(tr[-1,0],tr[-1,1],s=38,marker='x',color=colors[p])
        ax.set(title={'like':'Like charge: +1000e, +1000e','neutral':'Neutral: 0e, 0e','opposite':'Opposite: +1000e, −1000e'}[label],
            xlabel='x (µm)',ylabel='y (µm)',xlim=(-160,160),ylim=(-20,20))
        ax.grid(alpha=.15)
    fig.suptitle('Three Brownian trajectory pairs per case; 10 µm radius droplets, 10 s\n'
        'Top-view projection; x and y scales differ. Circles start, crosses finish.',fontsize=12)
    savefig(fig,out,'charged_droplets')
    fig,ax=plt.subplots(figsize=(8,4.5),layout='constrained')
    for label in ['like','neutral','opposite']:
        zz=traces[('droplet',label)];rr=np.linalg.norm(zz['traces_m'][:,:,1]-zz['traces_m'][:,:,0],axis=2)*1e6
        ax.plot(zz['times_s'],rr.mean(axis=1),label=label+' (four shown pairs)')
        qq={'like':1000,'neutral':0,'opposite':-1000}[label]
        exact=pair_analytic(2e-4,zz['times_s'],1e-5,1000,qq)*1e6
        ax.plot(zz['times_s'],exact,ls='--',alpha=.5)
    ax.set(xlabel='Time (s)',ylabel='Center separation (µm)',title='Charge changes mean drift; Brownian motion adds variation')
    ax.legend();ax.text(.02,.02,'Dashed: deterministic Coulomb/Stokes limit',transform=ax.transAxes)
    savefig(fig,out,'charge_separation')
    cr=[]
    for dt in [.04,.02,.01,.005]:
        zz=particle_pairs(a=1e-5,q1_e=1000,q2_e=1000,r0=2e-4,end=10,dt=dt,samples=1,brownian=False)
        exact=float(pair_analytic(2e-4,10,1e-5,1000,1000))
        cr.append(dict(test='deterministic_timestep',dt_s=dt,
            relative_error=abs(zz['final_separation_m'][0]/exact-1)))
    for dt in [.02,.01,.005]:
        vv=[]
        for seed in CFG['particle_seeds']:
            z=particle_pairs(a=1e-5,q1_e=1000,q2_e=1000,r0=2e-4,end=10,dt=dt,samples=256,seed=seed)
            vv.extend(z['final_separation_m'])
        cr.append(dict(test='stochastic_timestep_distribution',dt_s=dt,mean_m=np.mean(vv),
            sem_m=np.std(vv,ddof=1)/np.sqrt(len(vv)),n=len(vv),note='Independent discretized paths; compare sampling uncertainty, not pathwise convergence'))
    csvwrite(out/'charge_refinement.csv',cr)
    cs=[]
    for temp in [278.15,298.15,308.15]:
        for a in [5e-6,1e-5,2e-5]:
            for q in [0,100,1000,3000]:
                for sign in [-1,1]:
                    zz=particle_pairs(a=a,q1_e=q,q2_e=sign*q,r0=2e-4,end=10,dt=.01,
                        samples=128,seed=93,T=temp)
                    cs.append(dict(T_K=temp,radius_m=a,q1_e=q,q2_e=sign*q,
                        mean_separation_m=np.mean(zz['final_separation_m']),
                        stopped_fraction=zz['stopped_fraction'],seed=93,n=128))
    csvwrite(out/'charge_sensitivity.csv',cs)

    phase=[];pc=[]
    for temp in [258.15,263.15,268.15,298.15]:
        for rh in [.5,.95,1,1.05]:
            for isice in ([True,False] if temp<273.15 else [False]):
                zz=vapor_exchange(temp,rh,isice)
                r={k:v for k,v in zz.items() if not isinstance(v,np.ndarray)}
                r['mechanism']='deposition' if isice and r['transferred_water_mg']>0 else 'sublimation' if isice else 'condensation' if r['transferred_water_mg']>0 else 'evaporation' if r['transferred_water_mg']<0 else 'equilibrium'
                r.update(status='SIMULATED_THERMOSTATTED_INTERFACE',end_s=600)
                phase.append(r)
                if temp==263.15 and rh==.95: pc.append(zz)
                budgets.append(dict(case=f'phase_T{temp}_RH{rh}_ice{isice}',quantity='water_moles',
                    initial=zz['gas_mol'][0],final=zz['gas_mol'][-1]+zz['deposited_mol'][-1],
                    relative_residual=zz['conservation_relative'],interpretation='vapor+signed condensed-inventory change; thermostat heat recorded'))
    csvwrite(out/'water_phase_results.csv',phase)
    melts=[]
    for power in [-5,0,5]:
        zz=freezing_melting(power_W=power)
        melts.append(dict(power_W=power,T_K=273.15,initial_mass_kg=.01,end_s=600,
            converted_mass_kg=zz['converted_mass_kg'][-1],remaining_mass_kg=zz['remaining_mass_kg'][-1],
            phase_change='freezing' if power<0 else 'melting' if power>0 else 'no_change',
            latent_energy_J=zz['latent_energy_J'][-1],completion_time_s=zz['completion_time_s'],
            status='PRESCRIBED_HEAT_FLUX_CALCULATION',limitations='seeded phase interface; no nucleation, supercooling or evolving temperature'))
        budgets.append(dict(case=f'phase_change_{power}W',quantity='water_mass_kg',initial=.01,
            final=zz['converted_mass_kg'][-1]+zz['remaining_mass_kg'][-1],
            relative_residual=abs((zz['converted_mass_kg'][-1]+zz['remaining_mass_kg'][-1])/.01-1),
            interpretation='Solid+liquid mass conserved; latent heat balance separately tested'))
    csvwrite(out/'freezing_melting_results.csv',melts)
    ice=[];ic=[]
    for temp in [200,210,220]:
        for area in [.1,1,10]:
            zz=ice_adsorption(temp,surface_area=area)
            ice.append(dict(T_K=temp,surface_area_m2=area,initial_acetone_ppb=1,
                final_adsorbed_percent=zz['final_adsorbed_fraction']*100,
                analytic_equilibrium_error=zz['equilibrium_error'],
                k_ads1_cm3_molecule_s=zz['k_ads_cm3_molecule_s'][0],
                k_ads2_cm3_molecule_s=zz['k_ads_cm3_molecule_s'][1],
                k_des1_s_1=zz['k_des_s_1'][0],k_des2_s_1=zz['k_des_s_1'][1],
                status='SIMULATED_TWO_SITE_SURFACE',limitation='site1 assumed upper-bound density; source ice preparation and aging may not transfer'))
            if temp==210 and area==1:ic=zz
    csvwrite(out/'ice_adsorption_results.csv',ice)
    budgets.append(dict(case='acetone_ice',quantity='acetone_moles',initial=ic['total_mol'],
        final=ic['total_mol']*(ic['gas_fraction'][-1]+ic['adsorbed_fractions'][:,-1].sum()),
        relative_residual=abs(ic['gas_fraction'][-1]+ic['adsorbed_fractions'][:,-1].sum()-1),
        interpretation='gas + both adsorbed site inventories'))
    fig,ax=plt.subplots(1,2,figsize=(10,4.4),layout='constrained')
    for zz in pc:
        ax[0].plot(zz['times_s'],zz['deposited_mol']*.01801528*1e6,label='ice' if zz['ice'] else 'supercooled liquid')
    ax[0].set(title='−10 °C, initial RHwater = 95%',xlabel='Time (s)',ylabel='Water transferred to interface (mg)');ax[0].legend()
    ax[0].axhline(0,color='grey',lw=.7)
    ax[1].plot(ic['times_s'],100*ic['adsorbed_fractions'][0],label='site 1')
    ax[1].plot(ic['times_s'],100*ic['adsorbed_fractions'][1],label='site 2')
    ax[1].set(xscale='log',title='Acetone on ice: 210 K, 1 ppb, 1 m²',xlabel='Time (s)',ylabel='Initial acetone inventory adsorbed (%)');ax[1].legend()
    savefig(fig,out,'ice_and_water')

    # Stoichiometric conversion audit, explicitly not a kinetic simulation.
    p=decomposition_products(1e-6,.8)
    h_initial=2e-6;o_initial=2e-6
    for element,initial,final in [('H',h_initial,2*p[0]+2*p[1]),('O',o_initial,2*p[0]+p[1]+2*p[2])]:
        budgets.append(dict(case='H2O2_prescribed_extent_control',quantity=element+'_atom_moles',initial=initial,
            final=final,relative_residual=abs(final-initial)/initial,
            interpretation='80% prescribed conversion is a stoichiometry test, NOT a kinetic prediction'))
    csvwrite(out/'conservation_budgets.csv',budgets)
    summary=dict(partition_cases=len(rows),carbonate_cases=len(carb),
        transport_grid_cases=4,charge_ensemble_pairs=2*3*len(CFG['particle_seeds'])*CFG['pairs_per_seed'],
        water_phase_cases=len(phase),ice_adsorption_cases=len(ice),
        max_relative_inventory_error=max(r['relative_residual'] for r in budgets),
        best_transport_relative_L2=refinement[3]['relative_L2'],
        grid_errors=[r['relative_L2'] for r in refinement[:4]],
        fog_CO_aqueous_percent=next(r['equilibrium_aqueous_percent'] for r in rows if r['species']=='CO' and r['medium']=='fog'),
        bulk_CO2_pH=carb[0]['pH'],charge_droplet={k[1]:v for k,v in edata.items() if k[0]=='droplet'},
        smoke_diffusion_capture_percent_600s=sc['captured_fraction_600s']*100,
        ice_acetone_adsorbed_percent=ic['final_adsorbed_fraction']*100,
        CO_OH_converted_percent=kinetics['CO_converted_percent'],
        elapsed_seconds=time.perf_counter()-start,python=sys.version,numpy=np.__version__,
        scipy=scipy.__version__,matplotlib=matplotlib.__version__,platform=platform.platform(),
        status='Numerically verified reduced models; not validated against a new environmental dataset')
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    # Hash inputs and scripts for reproducible provenance; never hash outputs here.
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.iterdir()
              if p.suffix in ['.py','.json','.txt'] and p.name!='manifest.json'}
    (out/'input_hashes.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'results')
    run(parser.parse_args().out)
