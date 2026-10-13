"""Run all follow-up cases, controls and refinements; no online inputs needed."""
from pathlib import Path
from dataclasses import asdict,replace
from itertools import product
import csv,hashlib,json,platform,subprocess,sys,time
import numpy as np
import scipy
from scipy.stats import t as student_t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from followup_model import *

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'
def json_default(z):
    if isinstance(z,np.generic):return z.item()
    raise TypeError(type(z).__name__)
def write_json(p,z):p.write_text(json.dumps(z,indent=2,ensure_ascii=False,allow_nan=False,default=json_default)+'\n',encoding='utf-8')
def write_csv(name,rows):
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def savefig(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=160,bbox_inches='tight')
    fig.savefig(OUT/(name+'.svg'),bbox_inches='tight');plt.close(fig)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fog_row(name,c,z):
    row=dict(case=name,**asdict(c),actual_end_s=float(z['times'][-1]),stopped_at_2um=z['stopped'],
        final_radius_um=float(z['radius'][-1]*1e6),initial_drop_T_K=float(z['Td'][0]),
        final_RH=float(z['RH'][-1]),remaining_liquid_fraction=float(z['state'][0,-1]**1.5),
        heat_J_m3=float(z['heat_J_m3'][-1]),water_error=z['water_relative_error'],solute_error=z['solute_relative_error'])
    for i,name in enumerate(SPECIES):
        row[name+'_final_liquid_fraction']=float(z['state'][3+i,-1])
        row[name+'_peak_liquid_fraction']=float(z['state'][3+i].max())
    return row

def run():
    start=time.perf_counter();OUT.mkdir(exist_ok=True)
    arrays={};fog_rows=[];fog_saved={};configs=[]
    for T,RH,a,cooling in product([283.15,298.15,308.15],[.5,.9,.99,.995,1.,1.005],[5e-6,1e-5,25e-6],[False,True]):
        c=Fog(T=T,RH=RH,radius=a,cooling=cooling);configs.append(c)
    for i,c in enumerate(configs):
        name=f'fog_{i:03d}';z=fog_run(c);fog_rows.append(fog_row(name,c,z));fog_saved[(c.T,c.RH,c.radius,c.cooling)]=z
        arrays[name+'_time']=z['times'];arrays[name+'_state']=z['state'];arrays[name+'_temperature']=z['Td']
    controls=[]
    for name,c in [('fixed_water',Fog(water_exchange=False)),('no_transfer',Fog(solute_exchange=False)),
                   ('flat_saturated',Fog(RH=1,kelvin=False)),('maxwell_open',Fog(RH=.5,cooling=False,kelvin=False,open_water_reservoir=True))]:
        z=fog_run(c);controls.append(fog_row(name,c,z));arrays[name+'_time']=z['times'];arrays[name+'_state']=z['state']
    sensitivity=[]
    for parameter,levels in [('dv_scale',[.8,1.,1.2]),('transfer_scale',[.5,1.,2.]),('H_scale',[.5,1.,2.]),('kelvin',[False,True])]:
        for level in levels:
            c=replace(Fog(),**{parameter:level});z=fog_run(c)
            sensitivity.append(dict(parameter=parameter,value=level,**fog_row(parameter+'_'+str(level),c,z)))
    refinement=[]
    for rh in [.5,.995,1.005]:
        configurations=[Fog(RH=rh,max_step=h) for h in [.2,.1,.05]]+[Fog(RH=rh,max_step=.05,rtol=2e-10,method='BDF')]
        zz=[fog_run(c) for c in configurations];ref=zz[-1]
        for c,z in zip(configurations,zz):
            refinement.append(dict(RH=rh,max_step=c.max_step,method=c.method,rtol=c.rtol,
                end_time_relative_difference=abs(float(z['times'][-1]/ref['times'][-1]-1)),
                final_liquid_fraction_max_absolute_difference=float(np.max(abs(z['state'][3:7,-1]-ref['state'][3:7,-1]))),
                radius_relative_difference=abs(float(z['radius'][-1]/ref['radius'][-1]-1))))
    print('Fog: 108 main, 4 controls, 11 sensitivities, 12 refinement solves completed',flush=True)
    write_csv('fog_cases.csv',fog_rows);write_csv('fog_controls.csv',controls);write_csv('fog_sensitivity.csv',sensitivity);write_csv('fog_refinement.csv',refinement)

    cases=[('neutral',0,0,True),('charged_neutral_50e',50,0,True),('charged_neutral_100e',100,0,True),
        ('charged_neutral_monopole',100,0,False),('weak_like_charge',100,1,True),
        ('strong_like_charge',100,100,True),('opposite_charge',100,-100,True)]
    seeds=list(range(101,107));pair_rows=[];pair_summary=[];det_rows=[];det={}
    for name,q,Q,polar in cases:
        z=deterministic_pair(q_e=q,Q_e=Q,polarization=polar);det[name]=z
        arrays[name+'_det_time']=z['times'];arrays[name+'_det_distance']=z['radius']
        det_rows.append(dict(case=name,q_e=q,Q_e=Q,polarization=polar,final_separation_um=float(z['radius'][-1]*1e6),
            end_time_s=float(z['times'][-1]),stopped=z['stopped'],energy_relative_residual=z['energy_relative_residual'],
            initial_force_N=float(electro_force(3e-5,q,Q,polarization=polar))))
        for seed in seeds:
            zz=brownian_pairs(q_e=q,Q_e=Q,seed=seed,polarization=polar)
            pair_rows.append(dict(case=name,q_e=q,Q_e=Q,polarization=polar,seed=seed,samples=512,
                stopped_fraction=zz['stopped_fraction'],mean_separation_um=zz['mean_separation_m']*1e6))
            arrays[f'{name}_seed{seed}_final']=zz['final_position'];arrays[f'{name}_seed{seed}_stops']=zz['stops']
            if seed==101:arrays[name+'_traces']=zz['traces'];arrays[name+'_trace_time']=zz['times']
        vals=np.array([r['stopped_fraction'] for r in pair_rows if r['case']==name])
        half=float(student_t.ppf(.975,len(vals)-1)*vals.std(ddof=1)/np.sqrt(len(vals)))
        pair_summary.append(dict(case=name,mean_stop_fraction=float(vals.mean()),CI95_low=float(vals.mean()-half),CI95_high=float(vals.mean()+half),independent_seeds=len(seeds),paths=512*len(seeds)))
        print('Particle paths:',name,'completed',flush=True)
    paired=[]
    neutral={r['seed']:r for r in pair_rows if r['case']=='neutral'}
    for name,_,_,_ in cases:
        differences=np.array([r['stopped_fraction']-neutral[r['seed']]['stopped_fraction'] for r in pair_rows if r['case']==name])
        half=float(student_t.ppf(.975,5)*differences.std(ddof=1)/np.sqrt(6))
        paired.append(dict(case=name,mean_stop_fraction_difference=float(differences.mean()),CI95_low=float(differences.mean()-half),CI95_high=float(differences.mean()+half)))
    pair_refine=[]
    for q in [0,100]:
        for seed in [201,202,203,204,205,206]:
            baseline=None
            for dt in [.0005,.001,.002]:
                z=brownian_pairs(q_e=q,dt=dt,seed=seed)
                if baseline is None:baseline=z
                pair_refine.append(dict(q_e=q,seed=seed,dt_s=dt,stopped_fraction=z['stopped_fraction'],
                    paired_stop_difference=z['stopped_fraction']-baseline['stopped_fraction'],
                    paired_mean_separation_difference_um=(z['mean_separation_m']-baseline['mean_separation_m'])*1e6))
    pair_sensitivity=[]
    for T,a,q in product([283.15,298.15,308.15],[.05e-6,.1e-6,.2e-6],[20,50,100]):
        z=deterministic_pair(T=T,a=a,q_e=q)
        pair_sensitivity.append(dict(T_K=T,aerosol_radius_um=a*1e6,q_e=q,stopped=z['stopped'],
            end_time_s=float(z['times'][-1]),final_separation_um=float(z['radius'][-1]*1e6),energy_relative_residual=z['energy_relative_residual']))
    write_csv('particle_seeds.csv',pair_rows);write_csv('particle_summary.csv',pair_summary);write_csv('particle_paired_controls.csv',paired)
    write_csv('particle_refinement.csv',pair_refine);write_csv('particle_deterministic.csv',det_rows);write_csv('particle_sensitivity.csv',pair_sensitivity)

    data=json.loads((ROOT/'measured_collection.json').read_text(encoding='utf-8'));measured=[];ranges=[]
    for g in data['groups']:
        for i,(an,obs) in enumerate(zip(g['wet_radius_nm'],g['CE'])):
            a=an*1e-9;A=g['drop_radius_um']*1e-6;T=g['T_K'];v=data['speed_m_s_approximate']
            pred=brownian_collection_efficiency(a,A,T,v)
            envelope=[brownian_collection_efficiency(a,A+da,T+dT,u,s) for da,dT,u,s in product([-1.3e-6,1.3e-6],[-.5,.5],[.2,.3],[.5,1.])]
            measured.append(dict(RH_percent=g['RH_percent'],size_selection=i+1,wet_radius_nm=an,drop_radius_um=g['drop_radius_um'],T_K=T,
                measured_CE=obs,brownian_only_CE=pred,measured_over_prediction=obs/pred,
                sensitivity_min=min(envelope),sensitivity_max=max(envelope),measured_above_sensitivity=obs>max(envelope)))
    for i in range(1,7):
        high=next(r for r in measured if r['RH_percent']==93.5 and r['size_selection']==i)
        low=next(r for r in measured if r['RH_percent']==71.1 and r['size_selection']==i)
        ranges.append(dict(size_selection=i,measured_lowRH_over_highRH=low['measured_CE']/high['measured_CE'],
            brownian_lowRH_over_highRH=low['brownian_only_CE']/high['brownian_only_CE']))
    write_csv('published_data_comparison.csv',measured);write_csv('published_humidity_ratios.csv',ranges)
    np.savez_compressed(OUT/'trajectories.npz',**arrays)

    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for rh in [.5,.9,.995,1.005]:
        z=fog_saved[(298.15,rh,1e-5,True)]
        ax[0,0].plot(z['times'],z['radius']*1e6,label=f'{rh*100:g}% RH')
    ax[0,0].set(xlabel='Time (s)',ylabel='Droplet radius (µm)',title='Finite fog water: shrink, persist or grow',xscale='symlog',xlim=(0,30));ax[0,0].legend(fontsize=9)
    for cool in [False,True]:
        z=fog_saved[(298.15,.5,1e-5,cool)]
        ax[0,1].plot(z['times'],z['radius']*1e6,label='Conductive cooling' if cool else 'Temperature held at 25 °C')
    ax[0,1].set(xlabel='Time (s)',ylabel='Droplet radius (µm)',title='Cooling changes evaporation time');ax[0,1].legend(fontsize=9)
    z=fog_saved[(298.15,.9,1e-5,True)]
    for j,sp in enumerate(SPECIES):ax[1,0].semilogy(z['times'],np.maximum(100*z['state'][3+j],1e-10),label=sp)
    ax[1,0].set(xlabel='Time (s)',ylabel='Initial solute inventory in liquid (%)',title='90% RH: uptake and release as water shrinks');ax[1,0].legend(fontsize=9)
    x=np.arange(4);final=100*z['state'][3:7,-1]
    ax[1,1].bar(x-.18,final,.36,label='Evaporating at cutoff time')
    held=fog_run(Fog(water_exchange=False,end=float(z['times'][-1])))
    ax[1,1].bar(x+.18,100*held['state'][3:7,-1],.36,label='Fixed water at same time')
    ax[1,1].set(xticks=x,xticklabels=SPECIES,yscale='log',ylabel='Aqueous fraction (%)',title='Same inventory, time and temperature of air');ax[1,1].legend(fontsize=8)
    fig.suptitle('Coupled evaporation and partitioning · 1 m³ gas, initial liquid water 0.5 g\nModel stops at 2 µm radius; no chemical reactions',fontsize=13)
    savefig(fig,'evaporating_fog')

    fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    short={'neutral':'No charge','charged_neutral_100e':'100e / neutral','charged_neutral_monopole':'100e / neutral, no polarization','weak_like_charge':'100e / 1e','strong_like_charge':'100e / 100e','opposite_charge':'100e / −100e'}
    for name,label in short.items():
        zz=det[name];ax[0,0].plot(zz['times'],zz['radius']*1e6,label=label)
    ax[0,0].axhline(20,ls=':',c='black');ax[0,0].set(xlabel='Time (s)',ylabel='Separation (µm)',title='Deterministic force and drag controls');ax[0,0].legend(fontsize=7)
    selected=[r for r in pair_summary if r['case'] in short];xx=np.arange(len(selected))
    ax[0,1].bar(xx,[100*r['mean_stop_fraction'] for r in selected],yerr=[100*(r['CI95_high']-r['mean_stop_fraction']) for r in selected],capsize=3)
    ax[0,1].set(xticks=xx,xticklabels=['Neutral','100e / 0','No polar.','100e / 1e','Like','Opposite'],ylabel='Reached 20 µm boundary (%)',title='Brownian paths · six independent seeds');ax[0,1].tick_params(axis='x',labelrotation=25)
    for name,col in [('charged_neutral_100e','#277da1'),('strong_like_charge','#e76f51')]:
        tr=arrays[name+'_traces']*1e6
        for j in range(4):ax[1,0].plot(tr[:,j,0],tr[:,j,1],c=col,alpha=.65,label=name.replace('_',' ') if j==0 else None)
    ax[1,0].add_patch(plt.Circle((0,0),20,color='grey',alpha=.2));ax[1,0].plot([0],[0],'ko')
    ax[1,0].set(xlabel='Relative x (µm)',ylabel='Relative y (µm)',title='3D paths projected into a plane');ax[1,0].axis('equal');ax[1,0].legend(fontsize=7)
    for q in [0,100]:
        groups=[[r['paired_stop_difference']*100 for r in pair_refine if r['q_e']==q and r['dt_s']==dt] for dt in [.002,.001,.0005]]
        means=np.array([np.mean(x) for x in groups]);err=[student_t.ppf(.975,5)*np.std(x,ddof=1)/np.sqrt(6) for x in groups]
        ax[1,1].errorbar([.002,.001,.0005],means,yerr=err,fmt='o-',capsize=3,label=f'q={q}e')
    ax[1,1].set(xlabel='Step (s)',ylabel='Difference from finest step (percentage points)',title='Shared Brownian paths: step sensitivity');ax[1,1].legend(fontsize=9)
    fig.suptitle('Polarization can attract a charged aerosol toward a neutral conducting droplet\n100 nm aerosol, 10 µm droplet; stopping boundary is not a collision',fontsize=13)
    savefig(fig,'polarization_controls')

    fig,ax=plt.subplots(1,2,figsize=(12,4.6),layout='constrained')
    for rh,col in [(93.5,'#277da1'),(82.4,'#f4a261'),(71.1,'#9b2226')]:
        rows=[r for r in measured if r['RH_percent']==rh];x=[r['wet_radius_nm'] for r in rows]
        ax[0].semilogy(x,[r['measured_CE'] for r in rows],'o-',c=col,label=f'Measured {rh}% RH')
        ax[0].semilogy(x,[r['brownian_only_CE'] for r in rows],'--',c=col,label=f'Diffusion only {rh}%')
    ax[0].set(xlabel='Wet aerosol radius (nm)',ylabel='Collection efficiency',title='Independent data challenge, no fitted factors');ax[0].legend(fontsize=7,ncol=2)
    ax[1].plot([r['size_selection'] for r in ranges],[r['measured_lowRH_over_highRH'] for r in ranges],'o-',label='Measured')
    ax[1].plot([r['size_selection'] for r in ranges],[r['brownian_lowRH_over_highRH'] for r in ranges],'s--',label='Diffusion-only prediction')
    ax[1].set(xlabel='Matched dry-size selection (Table 3 column row)',ylabel='Collection at 71.1% / collection at 93.5% RH',title='Wet-size change alone misses the humidity response');ax[1].legend()
    fig.suptitle('Dépée et al. 2021, Part I, Table 3 · sodium fluorescein aerosol\nThe stagnant diffusion kernel is challenged outside its complete-physics scope',fontsize=12)
    savefig(fig,'measured_capture_challenge')

    tests=subprocess.run([sys.executable,'-m','unittest','-v','test_followup.py'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    (ROOT/'test_log.txt').write_text(tests.stdout+tests.stderr,encoding='utf-8')
    if tests.returncode:raise RuntimeError(tests.stderr)
    chosen=fog_saved[(298.15,.9,1e-5,True)];dry_iso=fog_saved[(298.15,.5,1e-5,False)];dry_cool=fog_saved[(298.15,.5,1e-5,True)]
    summary=dict(completed_date='2026-10-13',unit_tests_passed=29,
        fog=dict(main_cases=len(fog_rows),control_cases=len(controls),sensitivity_cases=len(sensitivity),refinement_cases=len(refinement),additional_same_time_control=1,
            max_water_error=max(r['water_error'] for r in fog_rows),max_solute_error=max(r['solute_error'] for r in fog_rows),
            RH50_isothermal_cutoff_s=float(dry_iso['times'][-1]),RH50_cooled_cutoff_s=float(dry_cool['times'][-1]),
            RH90_cutoff_s=float(chosen['times'][-1]),RH90_H2O2_final_aqueous_percent=float(100*chosen['state'][6,-1]),
            RH90_H2O2_peak_aqueous_percent=float(100*chosen['state'][6].max()),
            RH90_H2O2_fixed_water_same_time_percent=float(100*held['state'][6,-1]),
            final_CO_percent=float(100*chosen['state'][3,-1]),max_refinement_end_time_difference=max(r['end_time_relative_difference'] for r in refinement),
            max_refinement_liquid_fraction_difference=max(r['final_liquid_fraction_max_absolute_difference'] for r in refinement)),
        particles=dict(main_ensembles=len(pair_rows),main_paths=len(pair_rows)*512,refinement_ensembles=len(pair_refine),refinement_paths=len(pair_refine)*512,
            deterministic_cases=len(det_rows),deterministic_sensitivities=len(pair_sensitivity),summary=pair_summary,paired_controls=paired,
            max_energy_error=max(r['energy_relative_residual'] for r in det_rows+pair_sensitivity),
            dt001_max_mean_stop_change_percentage_points=max(abs(np.mean([r['paired_stop_difference']*100 for r in pair_refine if r['q_e']==q and r['dt_s']==.001])) for q in [0,100])),
        measurements=dict(points=len(measured),min_measured_over_prediction=min(r['measured_over_prediction'] for r in measured),
            median_measured_over_prediction=float(np.median([r['measured_over_prediction'] for r in measured])),max_measured_over_prediction=max(r['measured_over_prediction'] for r in measured),
            above_sensitivity_envelope=sum(r['measured_above_sensitivity'] for r in measured),matched_humidity_ratios=ranges,
            verdict='The diffusion-only pilot does not describe these falling-droplet measurements; no factor fitted and no full microphysics validation claimed.'),
        seconds=time.perf_counter()-start,versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__))
    write_json(OUT/'summary.json',summary)
    write_json(OUT/'input_hashes.json',{name:digest(ROOT/name) for name in ['baseline_model.py','baseline_references.json','followup_model.py','run_followup.py','test_followup.py','measured_collection.json']})
    print(json.dumps(summary,indent=2,default=json_default),flush=True)

if __name__=='__main__':run()
