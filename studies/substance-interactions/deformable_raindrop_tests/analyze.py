"""Read saved runs and score every preselected experimental row, without fitting."""
from pathlib import Path
import csv,json,hashlib
import numpy as np
from shape_model import GasLibrary,evolve,MAT,mechanics,geometry
from study_status import study_status

P=Path(__file__).resolve().parent
def average(h,key,lo,hi):
    keep=(h['tU_D']>=lo)&(h['tU_D']<=hi)
    x=h['tU_D'][keep];y=h[key][keep]
    return float(np.trapezoid(y,x)/(x[-1]-x[0])) if len(x)>1 else float('nan')

def flow_rows():
    rows=[]
    for mp in sorted((P/'flow').glob('*/metadata.json')):
        m=json.loads(mp.read_text());h=np.genfromtxt(mp.parent/'history.csv',names=True,delimiter=',')
        end=m['duration_completed'];begin=m['duration_requested']/2
        row=dict(name=m['name'],Re=m['Re_D'],aspect=m['aspect'],D=m['D_lattice'],status=m['status'],
             speed=m['speed'],width=m['width_D'],length=m['length_D'],duration=end,
             seed=m['seed'],cs=m['cs'],interpolated=m['interpolated'],elapsed_s=m['elapsed_s'])
        for field,key in [('Cd','Cd_projected'),('Cq','Cq')]:
            row[field]=average(h,key,begin,end)
            blocks=[average(h,key,a,b) for a,b in zip(np.linspace(begin,end,5)[:-1],np.linspace(begin,end,5)[1:])]
            row[field+'_block_means']=blocks
            row[field+'_block_sd']=float(np.std(blocks,ddof=1))
            row[field+'_first_second_difference']=float(np.mean(blocks[2:])-np.mean(blocks[:2]))
        row['max_mach']=float(h['max_speed_lattice'].max()*np.sqrt(3))
        row['max_mass_offset']=float(np.max(abs(h['mass_relative'])))
        row['gauge_correction_Cq']=float(average(h,'Cq',begin,end)-average(h,'Cq_uncorrected',begin,end))
        rows.append(row)
    return rows

def library_rows(rows,d):
    return [r for r in rows if r['D']==d and r['Re'] in [800,1600,2600] and r['aspect'] in [.55,.75,1.]
       and r['interpolated'] and r['speed']==.06 and r['width']==5 and r['length']==12
       and r['seed']==31 and r['cs']==.1 and r['duration']<41 and r['status']=='completed']

def main():
    rows=flow_rows();(P/'flow_summary.json').write_text(json.dumps(rows,indent=2))
    fields=[k for k,v in rows[0].items() if not isinstance(v,list)]
    with (P/'flow_summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    obs=list(csv.DictReader((P/'measurements.csv').open()));predictions=[];libraries={}
    for d in [20,28]:
        librows=library_rows(rows,d)
        if len(librows)!=9:continue
        lib=GasLibrary(librows);libraries[d]=lib
        for o in obs:
            p=lib.terminal(float(o['diameter_mm'])/1000);p['gas_grid_D']=d
            p['observed_mean']=float(o['mean_axis_ratio']);p['observed_ci95']=float(o['reported_95CI_halfwidth'])
            p['observed_sd']=float(o['reported_sd']);p['residual']=p['aspect']-p['observed_mean']
            p['table3_residual']=p['aspect']-float(o['table3_mean'])
            p['fixed_07_residual']=.7-p['observed_mean']
            predictions.append(p)
    if not libraries:raise RuntimeError('No complete aerodynamic library yet')
    best=max(libraries);lib=libraries[best];chosen=[p for p in predictions if p['gas_grid_D']==best]
    with (P/'comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,list(predictions[0]));w.writeheader();w.writerows(predictions)
    byname={r['name']:r for r in rows};base=byname['pilot_re1600_a075_d20'];controls=[]
    for name in ['re1600_a075_d28','re1600_a075_d36','re1600_a075_d20_halfway','re1600_a075_d20_slow',
                 're1600_a075_d20_wide','re1600_a075_d20_seed97','re1600_a075_d28_long','re1600_a075_d36_long']:
        if name in byname:
            r=byname[name];controls.append(dict(name=name,Cd=r['Cd'],Cq=r['Cq'],
                Cd_percent_vs_d20=100*(r['Cd']/base['Cd']-1),Cq_percent_vs_d20=100*(r['Cq']/base['Cq']-1)))
    sensitivity=[];original=MAT.copy()
    # One-at-a-time perturbations, not a probabilistic uncertainty interval.
    for key,factors in [('surface_tension_N_m',[.97,1.03]),('rho_air_kg_m3',[.95,1.05]),
                        ('nu_air_m2_s',[.95,1.05]),('rho_water_kg_m3',[.998,1.002])]:
        for factor in factors:
            MAT.update(original);MAT[key]=original[key]*factor
            for D in [.0025,.004]:
                r=lib.terminal(D);r.update(parameter=key,factor=factor);sensitivity.append(r)
    MAT.update(original)
    for factor in [.98,1.02]:
        for D in [.0025,.004]:
            r=lib.terminal(D*factor);r.update(parameter='drop_diameter',factor=factor);sensitivity.append(r)
    for field in ['cd','cq']:
        for factor in [.9,1.1]:
            other=GasLibrary(library_rows(rows,best),**{field+'_scale':factor})
            r=other.terminal(.004);r.update(parameter=field+'_10percent_diagnostic',factor=factor);sensitivity.append(r)
    (P/'sensitivity.json').write_text(json.dumps(sensitivity,indent=2))
    # Evolve an initially slightly rounder shape at each self-consistent terminal
    # speed. Initial amplitude is a declared scenario, not inferred from images.
    traces={};dynamic=[]
    for p in chosen:
        if p['status']!='root_inside_library':continue
        D=p['diameter_mm']/1000;speed=p['speed_m_s'];s0=np.log(p['aspect'])+.02
        trace=evolve(D,load=lambda s,t:lib.forces(D,speed,s)[1],initial=(s0,0),duration=.3,dt=1e-4)
        key=f'D{p["diameter_mm"]:g}';traces[key]=trace
        a,b=geometry(trace[:,1],D)
        wall_speed=np.maximum(2*a/3,b/3)*abs(trace[:,2])
        dynamic.append(dict(diameter_mm=p['diameter_mm'],min_aspect=float(trace[:,3].min()),max_aspect=float(trace[:,3].max()),
             max_surface_speed_relative_to_air=float(wall_speed.max()/speed),
             energy_budget_relative=float(np.max(abs(trace[:,-1]))/(MAT['surface_tension_N_m']*D**2))))
    # Different initial amplitudes and liquid damping, all without changing the
    # physical coefficients used for the external-data comparison.
    p=chosen[-1];D=.004;speed=p['speed_m_s'];s0=np.log(p['aspect'])
    for label,amp,mufactor in [('larger_initial',.08,1),('double_damping',.02,2),('no_damping',.02,0)]:
        traces[label]=evolve(D,load=lambda s,t:lib.forces(D,speed,s)[1],initial=(s0+amp,0),duration=.3,dt=1e-4,
                            mu=MAT['mu_water_Pa_s']*mufactor)
    traces['no_air']=evolve(D,initial=(s0,0),duration=.3,dt=1e-4)
    np.savez_compressed(P/'deformation_traces.npz',**traces)
    paired=[]
    for a,b in [('re1600_a075_d28','re1600_a075_d36'),('re1600_a075_d28','re1600_a075_d28_long'),
                ('re2600_a075_d28','re2600_a075_d36'),
                ('pilot_re1600_a075_d20','re1600_a075_d20_slow'),('pilot_re1600_a075_d20','re1600_a075_d20_wide'),
                ('re1600_a075_d20_halfway','pilot_re1600_a075_d20')]:
        if a in byname and b in byname:
            paired.append(dict(reference=a,changed=b,Cd_percent=100*(byname[b]['Cd']/byname[a]['Cd']-1),
                               Cq_percent=100*(byname[b]['Cq']/byname[a]['Cq']-1)))
    interpolation_checks=[]
    for row in rows:
        if row['name'].startswith('midpoint_'):
            point=np.array([[row['Re'],row['aspect']]])
            cd=float(lib.cd(point)[0]);cq=float(lib.cq(point)[0])
            interpolation_checks.append(dict(name=row['name'],Cd_computed=row['Cd'],Cd_interpolated=cd,
                Cq_computed=row['Cq'],Cq_interpolated=cq,Cd_relative_error=cd/row['Cd']-1,Cq_relative_error=cq/row['Cq']-1))
    status=study_status();(P/'study_status.json').write_text(json.dumps(status,indent=2))
    result=dict(study_status=status,best_complete_library_D=best,predictions=predictions,controls=controls,paired_controls=paired,
        interpolation_checks=interpolation_checks,dynamics=dynamic,
        counts=dict(gas_attempts=status['started'],recorded_final_cases=len(rows),completed=sum(r['status']=='completed' for r in rows),planned=status['planned'],unfinished=len(status['unfinished'])),
        mean_absolute_axis_error=float(np.mean([abs(p['residual']) for p in chosen])),
        old_fixed_07_mean_absolute_axis_error=float(np.mean([abs(p['fixed_07_residual']) for p in chosen])),
        fixed_shape_control_note='Aspect0.7 is an illustrative prior fixed-body assumption, not a calibrated former predictor. Its error reduction is not a standalone model-validation claim.',
        decision='External comparison only; unresolved numerical and physical limitations prevent a validation claim.',
        source_freeze_matches={f:hashlib.sha256((P/f).read_bytes()).hexdigest()==sha for f,sha in json.loads((P/'source_freeze.json').read_text()).items()})
    (P/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
