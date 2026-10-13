"""Reproduce all numeric CSVs/figures with python run_advanced.py.
No downloads, fitting, or external services during this run.
"""
from pathlib import Path
import csv,json,time,hashlib,platform,sys
import numpy as np
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import t as student_t
import advanced_model as m
from followup_model import fog_run,Fog

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,
                     'axes.titleweight':'bold','figure.dpi':140})
SUMMARY={};TRACES={}
def csvout(name,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/(name+'.csv')).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)
def savefig(fig,name):
    fig.savefig(OUT/(name+'.png'),bbox_inches='tight');fig.savefig(OUT/(name+'.svg'),bbox_inches='tight');plt.close(fig)
def log(x):print(x,flush=True)


def carbonate():
    rows=[];fig,ax=plt.subplots(1,2,figsize=(10,3.7),constrained_layout=True)
    for alk in (0.,5e-5,1e-4,2e-4):
        z=m.carbonate_run(alkalinity=alk)
        b=z['y'][1];target=b[-1]*.95;t95=float(np.interp(target,b,z['t']))
        row=dict(alkalinity_mol_L=alk,carbon_mol_L=2e-4,T_K=298.15,water_scale=1.,oh_scale=1.,
                 pH_initial=z['pH'][0],pH_final=z['pH'][-1],t95_hydration_s=t95,
                 hydrated_fraction=b[-1]/2e-4,carbon_error=z['carbon_error'])
        rows.append(row);label=f'{alk*1e6:g} micromol/L alkalinity'
        ax[0].semilogx(z['t'][1:],z['pH'][1:],label=label)
        ax[1].semilogx(z['t'][1:],100*b[1:]/2e-4,label=label)
        TRACES['carbonate_'+str(alk)]=np.column_stack([z['t'],z['pH'],z['y'].T,z['acid'],z['bic'],z['carb']])
    nominal=rows.copy()
    for sw,so in ((.5,1),(2,1),(1,.5),(1,2),(0,1),(1,0),(0,0)):
        z=m.carbonate_run(alkalinity=1e-4,water_scale=sw,oh_scale=so)
        rows.append(dict(alkalinity_mol_L=1e-4,carbon_mol_L=2e-4,T_K=298.15,
            water_scale=sw,oh_scale=so,pH_initial=z['pH'][0],pH_final=z['pH'][-1],
            hydrated_fraction=z['y'][1,-1]/2e-4,carbon_error=z['carbon_error']))
    refine=[]
    for step in (1.,.5,.25):
        z=m.carbonate_run(alkalinity=1e-4,max_step=step,rtol=1e-10)
        refine.append(dict(max_step_s=step,pH_at_1s=float(np.interp(1.,z['t'],z['pH'])),
                           pH_final=z['pH'][-1],carbon_error=z['carbon_error']))
    for a,title,ylabel in zip(ax,['CO2 hydration has a transient','Carbon changes form, not total inventory'],['pH','Hydrated carbon (%)']):
        a.set(xlabel='Time (s)',ylabel=ylabel,title=title);a.grid(alpha=.15)
    ax[0].legend(fontsize=7);savefig(fig,'carbonate_kinetics')
    csvout('carbonate_cases',rows);csvout('carbonate_refinement',refine)
    SUMMARY['carbonate']=dict(nominal=nominal,runs=len(rows)+len(refine),
        largest_carbon_error=max(r['carbon_error'] for r in rows),constants=m.carbonate_constants())
    log('Carbonate done')


def radial():
    rows=[];refine=[];fig,ax=plt.subplots(2,2,figsize=(10,7),constrained_layout=True)
    saved={}
    for RH in (.5,.9,.99):
        h=m.water_history(RH=RH,end=10.)
        old=fog_run(Fog(RH=RH,end=10.))
        for species in range(4):
            z=m.radial_uptake(h,species=species)
            oldfin=float(np.interp(h['end'],old['times'],old['state'][3+species]))
            rows.append(dict(species=m.SPECIES[species],T_K=298.15,RH=RH,A0_um=10.,cells=40,
                 Dl_m2_s=2e-9,alpha=1.,end_s=h['end'],final_radius_um=h['at'](h['end'])[0]*1e6,
                 peak_liquid_fraction=max(z['liquid']),final_liquid_fraction=z['liquid'][-1],
                 old_film_final_fraction=oldfin,mass_residual=z['conservation'],transfer_audit=z['transfer_audit']))
            if species==3:
                ax[0,0].plot(z['t'],100*z['liquid'],label=f'RH {RH:.0%}, radial')
                ax[0,0].plot(old['times'],100*old['state'][6],'--',alpha=.6)
            if RH==.9:
                saved[species]=z
                if species in (1,3):
                    v=h['number']*h['at'](h['end'])[0]**3*4*np.pi/3*np.diff(np.linspace(0,1,41)**3)
                    c=z['y'][:40,-1]/v
                    ax[0,1].plot(z['centres'],c/np.average(c,weights=v),label=m.SPECIES[species])
        log(f'Radial RH {RH} done')
    h=m.water_history(RH=.9,end=10.)
    for n in (20,40,80,160):
        z=m.radial_uptake(h,species=3,cells=n,rtol=3e-9)
        refine.append(dict(module='moving_H2O2',cells=n,final_liquid_fraction=z['liquid'][-1],
                           mass_residual=z['conservation']))
    for n in (20,40,80,160):
        z=m.fixed_sphere_dirichlet(n)
        refine.append(dict(module='analytic_diffusion_sphere',cells=n,max_mean_error=z['error']))
        ax[1,0].loglog(n,z['error'],'o',color='#126782')
    sens=[]
    for Dl in (1e-9,2e-9,4e-9):
        z=m.radial_uptake(h,species=3,Dl=Dl)
        sens.append(dict(species='H2O2',Dl_m2_s=Dl,alpha=1.,final_liquid_fraction=z['liquid'][-1]))
    # Acetone accommodation range at 293 K is a literature constraint, not a matched uptake trace.
    ha=m.water_history(T=293.,RH=.9,end=5.)
    for alpha in (.0028,.0054,.0099,1.):
        z=m.radial_uptake(ha,species=1,alpha=alpha)
        sens.append(dict(species='acetone',T_K=293.,Dl_m2_s=2e-9,alpha=alpha,final_liquid_fraction=z['liquid'][-1]))
        ax[1,1].plot(z['t'],100*z['liquid'],label=f'alpha={alpha:g}')
    for s,z in saved.items():TRACES['radial_'+m.SPECIES[s]]=np.column_stack([z['t'],z['liquid'],z['gas'],z['y'].T])
    ax[0,0].set(title='H2O2 uptake during shrinking fog',xlabel='Time (s)',ylabel='Initial solute in liquid (%)')
    ax[0,0].legend(fontsize=7);ax[0,0].text(.03,.03,'Dashed: previous film model',transform=ax[0,0].transAxes,fontsize=8)
    ax[0,1].set(title='Internal gradients at the 2 micrometre cutoff',xlabel='Fraction of droplet radius',ylabel='Concentration / volume mean');ax[0,1].legend()
    ax[1,0].set(title='Analytic sphere benchmark',xlabel='Radial cells',ylabel='Max absolute error in mean uptake')
    ax[1,1].set(title='Acetone accommodation sensitivity, 293 K',xlabel='Time (s)',ylabel='Initial solute in liquid (%)');ax[1,1].legend(fontsize=7)
    savefig(fig,'radial_diffusion');csvout('radial_cases',rows);csvout('radial_refinement',refine);csvout('radial_sensitivity',sens)
    SUMMARY['radial']=dict(runs=len(rows)+len(refine)+len(sens),max_mass_residual=max(r['mass_residual'] for r in rows),
        representative=[r for r in rows if r['RH']==.9],refinement=refine,
        independent_uptake_validation=False,independent_evaporation_validation=False)


def falling():
    data=json.loads((ROOT/'measured_collection.json').read_text());seeds=(4101,4102,4103,4104)
    rows=[];means=[]
    fig,ax=plt.subplots(1,3,figsize=(12,3.8),constrained_layout=True)
    for gi,g in enumerate(data['groups']):
        xx=[];yy=[];ee=[]
        for j,(a,obs) in enumerate(zip(g['wet_radius_nm'],g['CE'])):
            rr=[]
            for seed in seeds:
                z=m.falling_capture(A=g['drop_radius_um']*1e-6,a=a*1e-9,T=g['T_K'],
                    RH=g['RH_percent']/100,seed=seed,samples=4096,tmax=250.)
                row={k:v for k,v in z.items() if k not in ('t','traces','hit')}
                row.update(RH_percent=g['RH_percent'],wet_radius_nm=a,seed=seed,observed_CE=obs)
                rows.append(row);rr.append(z['CE'])
            ci=student_t.ppf(.975,3)*np.std(rr,ddof=1)/2
            means.append(dict(RH_percent=g['RH_percent'],wet_radius_nm=a,observed_CE=obs,
                predicted_CE=np.mean(rr),seed_t_halfwidth=ci,predicted_over_observed=np.mean(rr)/obs,
                max_censored_bound=max(r['censored_bound'] for r in rows[-4:]),Re=z['Re']))
            xx.append(a);yy.append(np.mean(rr));ee.append(ci)
            log(f'Capture RH {g["RH_percent"]} size {a}nm CE={np.mean(rr):.5g}')
        ax[gi].plot(xx,g['CE'],'ks',label='Published central values')
        ax[gi].errorbar(xx,yy,yerr=ee,fmt='o-',color='#126782',label='Candidate, seed-t 95%')
        ax[gi].set(title=f'RH {g["RH_percent"]}%',xlabel='Wet particle radius (nm)',ylabel='Collection efficiency')
        ax[gi].ticklabel_format(axis='y',style='sci',scilimits=(0,0));ax[gi].grid(alpha=.15)
    ax[0].legend(fontsize=7);savefig(fig,'falling_capture')
    csvout('capture_seeds',rows);csvout('capture_comparison',means)
    tests=[]
    configs=[('nominal',{}),('half_step',{'dt':.0125}),('double_step',{'dt':.05}),
             ('wide_disk',{'bmax':1.2}),('distant_planes',{'zmax':16.,'tmax':350.}),
             ('long_time',{'tmax':500.}),('no_phoresis',{'phoresis':False}),
             ('no_Brownian',{'brownian':False}),('point_interception',{'interception':False}),
             ('ventilation_1p2',{'vent':1.2}),('U_0p2',{'U':.2}),('U_0p3',{'U':.3})]
    for name,kw in configs:
        for seed in (8101,8102,8103,8104):
            opts=dict(samples=4096,seed=seed,tmax=250.);opts.update(kw)
            z=m.falling_capture(**opts)
            tests.append(dict(case=name,seed=seed,**{k:v for k,v in z.items() if k not in ('t','traces','hit')}))
        log('Capture control '+name)
    # Low Reynolds number pilot, intentionally separate from measured collection cases.
    low=m.falling_capture(A=1e-5,a=1e-7,T=298.15,RH=.9,U=.012,
        samples=4096,tmax=350.,seed=9101,trace=True)
    TRACES['falling_path_times']=low['t'];TRACES['falling_path_xyz']=low['traces']
    csvout('capture_controls',tests)
    SUMMARY['falling']=dict(main_ensembles=len(rows),main_paths=len(rows)*4096,control_ensembles=len(tests),
        ratio_min=min(r['predicted_over_observed'] for r in means),ratio_max=max(r['predicted_over_observed'] for r in means),
        median_factor_error=float(np.median([max(r['predicted_over_observed'],1/r['predicted_over_observed']) for r in means])),
        maximum_censored_bound=max(r['max_censored_bound'] for r in means),Re_range=[min(r['Re'] for r in means),max(r['Re'] for r in means)],
        low_Re_pilot={k:v for k,v in low.items() if k not in ('t','traces','hit')},validated_for_smoke=False)


def source_audits():
    rows=[];fig,ax=plt.subplots(1,2,figsize=(10,3.8),constrained_layout=True)
    for pH in (3,5,8,10):
        z=m.peroxide_published_rate_audit(pH)
        rows.append(dict(pH=pH,T_K=303.15,loading_g_L=.333,BET_m2_g=6.5,H2O2_initial_mol_L=.02,
                         k_min=z['k_min'],half_life_min=z['half_min'],fraction_5min=1-np.exp(-5*z['k_min']),
                         fraction_30min=1-np.exp(-30*z['k_min']),hydrogen_residual=z['hydrogen_residual'],oxygen_residual=z['oxygen_residual']))
        ax[0].plot(z['t'],100*(1-z['y'][0]/.02),label=f'Table rate: pH {pH}')
    # Deliberately coarse visual readings, not exact digitization or measurement error bars.
    obs=[dict(pH=3,t_min=5,figure4_percent_approx=45,reading_tolerance_percentage_points=5),
         dict(pH=3,t_min=30,figure4_percent_approx=55,reading_tolerance_percentage_points=5)]
    for r in obs:
        r['table_rate_prediction_percent']=100*(1-np.exp(-.009*r['t_min']))
        r['within_reading_band']=abs(r['table_rate_prediction_percent']-r['figure4_percent_approx'])<=5
    ax[0].errorbar([5,30],[45,55],yerr=5,fmt='ks',label='Fig. 4 pH 3: coarse readings')
    ax[0].set(title='Peroxide source fails a consistency check',xlabel='Time (min)',ylabel='H2O2 decomposed (%)');ax[0].legend(fontsize=7)
    ice=[]
    for T in range(190,221,5):
        for gas in (1e9,1e10,1e11):
            f=m.ice_capacity(T,gas);a=m.ice_capacity(T,gas,True)
            ice.append(dict(T_K=T,gas_molecules_cm3=gas,fresh_upper_cm2=f['total_cm2'],
                             aged_cm2=a['total_cm2'],fresh_upper_over_aged=f['total_cm2']/a['total_cm2'],
                             aged_relaxation_s=a['timescale_s'][1]))
    xx=np.arange(190,221,5)
    for aged,label in ((False,'Fresh site-1 upper bound + site 2'),(True,'Aged: site 2 only')):
        ax[1].semilogy(xx,[m.ice_capacity(T,1e10,aged)['total_cm2'] for T in xx],'o-',label=label)
    ax[1].set(title='Acetone ice: aging endpoints, no aging clock',xlabel='Temperature (K)',ylabel='Adsorbed molecules per cm2');ax[1].legend(fontsize=7)
    savefig(fig,'source_constraints');csvout('peroxide_rate_audit',rows);csvout('peroxide_figure_audit',obs);csvout('ice_aging_endpoints',ice)
    SUMMARY['peroxide']=dict(runs=4,source_internally_consistent=False,accepted_predictive_model=False,readings=obs)
    SUMMARY['ice']=dict(cases=len(ice),conditions_200K=[r for r in ice if r['T_K']==200],calibrated_aging_clock=False)


def charges():
    rr=[];relax=[];near=[];fig,ax=plt.subplots(1,3,figsize=(12,3.8),constrained_layout=True)
    for a in (50e-9,100e-9,200e-9):
        q,p=m.boltzmann_charges(a,nmax=100)
        for qq,pp in zip(q,p):rr.append(dict(radius_nm=a*1e9,charge_e=int(qq),probability=pp,model='theoretical_bipolar'))
        ax[0].plot(q,p,'o-',ms=3,label=f'{a*1e9:g} nm')
    ax[0].set(xlim=(-10,10),xlabel='Charge (elementary units)',ylabel='Probability',title='Equilibrium charge scenario');ax[0].legend()
    for sigma in (5.5e-6,1e-4,1e-2):
        relax.append(dict(kind='internal_charge_redistribution',conductivity_S_m=sigma,relative_permittivity=78.3,
                          tau_s=78.3*m.EPS0/sigma,isolated_net_charge_decays=False))
    for sigma in (0.,1e-14,1e-13,1e-12):
        tau=m.EPS0/sigma if sigma else float('inf')
        relax.append(dict(kind='Ohmic_ambient_leakage_scenario',conductivity_S_m=sigma,relative_permittivity=1.,
                          tau_s=tau,isolated_net_charge_decays=False))
        ts=np.linspace(0,100,200);ax[1].plot(ts,np.exp(-ts/tau),label=f'air sigma={sigma:g}')
    ax[1].set(xlabel='Time (s)',ylabel='Q(t) / Q(0)',title='Net charge requires an external loss path');ax[1].legend(fontsize=6)
    for gap in (5e-6,2e-6,1e-6,.67e-6):
        h=m.approach_time(1e-5,gap);bare=m.approach_time(1e-5,gap,lubrication=False)[0]
        near.append(dict(initial_gap_um=10,final_gap_um=gap*1e6,radius1_um=10,radius2_um=10,force_N=1e-12,
                         time_hydro_s=h[0],time_bare_s=bare,ratio=h[0]/bare,quadrature_error_s=abs(h[0]-h[1])))
    ax[2].plot([r['final_gap_um'] for r in near],[r['time_hydro_s'] for r in near],'o-',label='Pair drag + lubrication')
    ax[2].plot([r['final_gap_um'] for r in near],[r['time_bare_s'] for r in near],'o--',label='Bare pair drag')
    ax[2].set(xlabel='Stopping gap (micrometres)',ylabel='Approach time (s)',title='Stops before continuum breakdown');ax[2].invert_xaxis();ax[2].legend(fontsize=7)
    savefig(fig,'charge_and_contact');csvout('charge_distribution',rr);csvout('charge_relaxation',relax);csvout('near_contact',near)
    SUMMARY['charge']=dict(near_contact=near,internal_tau_s=[r['tau_s'] for r in relax[:3]],
        actual_smoke_distribution_measured=False,coalescence_simulated=False)


def finalize_existing():
    """Derive headline metrics from saved CSVs, independently of run memory.
    Also allows safe recovery after a report serialization failure.
    """
    def read(name):
        return list(csv.DictReader((OUT/(name+'.csv')).open(encoding='utf-8')))
    c=read('capture_comparison');r=read('radial_cases');co=read('carbonate_cases')
    ratios=np.array([float(x['predicted_over_observed']) for x in c])
    controls=read('capture_controls');control_summary=[]
    for label in dict.fromkeys(x['case'] for x in controls):
        part=[x for x in controls if x['case']==label];v=[float(x['CE']) for x in part]
        control_summary.append(dict(case=label,mean_CE=float(np.mean(v)),
            seed_t_halfwidth=float(student_t.ppf(.975,len(v)-1)*np.std(v,ddof=1)/np.sqrt(len(v))),
            maximum_censored_bound=max(float(x['censored_bound']) for x in part)))
    csvout('capture_control_summary',control_summary)
    summary=dict(
        status='Numerical batch complete; validation gaps remain',unit_tests=28,surface_unit_tests=6,
        versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__),
        falling=dict(main_ensembles=len(read('capture_seeds')),main_paths=len(read('capture_seeds'))*4096,
            control_ensembles=len(controls),control_paths=len(controls)*4096,low_Re_pilot_paths=4096,
            predicted_over_observed_min=float(min(ratios)),predicted_over_observed_max=float(max(ratios)),
            median_factor_error=float(np.median(np.maximum(ratios,1/ratios))),
            max_censored_main=max(float(x['max_censored_bound']) for x in c),
            controls=control_summary,validated_for_smoke=False),
        radial=dict(main_cases=len(r),refinement_cases=len(read('radial_refinement')),sensitivity_cases=len(read('radial_sensitivity')),
            max_mass_residual=max(float(x['mass_residual']) for x in r),
            H2O2_RH90=next(x for x in r if x['species']=='H2O2' and x['RH']=='0.9'),
            independent_uptake_validation=False,independent_evaporation_validation=False),
        carbonate=dict(cases=len(co),refinement_cases=len(read('carbonate_refinement')),
            max_carbon_error=max(float(x['carbon_error']) for x in co),nominal=co[:4],
            independent_transient_validation=False),
        peroxide=dict(rate_audit_curves=4,accepted_predictive_model=False,source_consistency_pass=False),
        ice=dict(endpoint_cases=len(read('ice_aging_endpoints')),calibrated_aging_clock=False),
        charge=dict(measured_smoke_charge_distribution=False,coalescence_simulated=False),
        serialization_recovery_note='Initial run completed all numerical CSVs and trajectories, then failed on a NumPy boolean during JSON summary serialization. Summary is now rebuilt from saved CSVs; the original failure log is retained.'
    )
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    names=['advanced_model.py','baseline_model.py','followup_model.py','run_advanced.py','measured_collection.json']
    (OUT/'input_hashes.json').write_text(json.dumps({n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},indent=2),encoding='utf-8')
    log('Finalization: all saved results summarized successfully')


if __name__=='__main__':
    start=time.time()
    if '--finalize-existing' not in sys.argv:
        carbonate();radial();source_audits();charges();falling()
        np.savez_compressed(OUT/'trajectories.npz',**TRACES)
    finalize_existing()
    log(f'Command completed in {time.time()-start:.1f}s')
