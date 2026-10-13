"""Live loss/recovery of orbital synchronization in the existing active clay Hug."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
import hug_robustness as r
from hug_rhythm import Model

ROOT=Path(__file__).resolve().parent

def protocol():return json.loads((ROOT/'hug_sync_protocol.json').read_text())

def boundaries(cfg):
    p=cfg['orbit_period_s'];a=cfg['baseline_orbits'];b=a+cfg['raised_stiffness_orbits']
    return [0.,a*p,b*p,(b+cfg['recovery_orbits'])*p]

def cases(cfg):
    return [dict(arm=a,condition=j,history=h) for a in cfg['arms'] for j in range(7) for h in cfg['start_histories']]

def initial_states(cfg):
    d=json.loads((ROOT/cfg['initial_results']).read_text())
    if d['numerical_status']!='passed' or not all(d['checks'].values()):raise ValueError('Verified baseline required')
    if cfg['absolute_start_s']!=d['protocol']['horizon_s']:raise ValueError('Initial absolute time mismatch')
    params=d['settings'][0]['parameters'];conditions=d['conditions'][1:8]
    if any(c['period_s']!=cfg['orbit_period_s'] for c in conditions):raise ValueError('Orbit period changed')
    if cfg['orbital_force_rms_N']!=d['protocol']['orbital_force_rms_N']:raise ValueError('Orbital force changed')
    rows=cases(cfg)
    states=[next(c['stroboscopic_last_state_scaled'] for c in d['cases'] if c['setting']==0 and c['condition']==x['condition']+1 and c['start']==x['history']) for x in rows]
    return params,conditions,np.array(states)

def factor(arm,stage,cfg):return cfg['stiffness_factor'] if arm!='sham' and (stage==1 or (stage==2 and arm=='hold_high')) else 1.

def spring_work_scaled(q_scaled,old_k,new_k,model):
    return .5*(new_k-old_k)*(model.qscale*np.asarray(q_scaled))**2/model.energy_scale

def integrate(cfg,dt,progress=True):
    params,conditions,initial=initial_states(cfg);rows=cases(cfg);base=Model(params)
    ens=r.Ensemble([base]*len(rows));z=np.column_stack((initial,np.zeros((len(rows),3))))
    bounds=boundaries(cfg);steps=[int(round(x/dt)) for x in bounds];stride=int(round(cfg['sample_interval_s']/dt))
    if not np.allclose(np.array(steps)*dt,bounds,rtol=0,atol=1e-9) or abs(stride*dt-cfg['sample_interval_s'])>1e-12:raise ValueError('Step must divide stages and sampling interval')
    count=int(round(2*cfg['orbit_period_s']/dt));cond=np.array([x['condition'] for x in rows])
    ft=cfg['absolute_start_s']+np.arange(count)*dt/2
    table=np.array([r.force(ft,c,cfg) for c in conditions]);ci=np.arange(7)
    initial_energy=ens.energy(z);work=np.zeros(len(rows));error=np.zeros(len(rows));guard=np.full(len(rows),-1.)
    saved=np.empty((steps[-1]//stride+1,len(rows),4));times=np.arange(len(saved))*cfg['sample_interval_s']
    events=[];stage=0;at=0
    for step in range(steps[-1]+1):
        if step in steps[1:-1]:
            stage+=1;old=ens.k.copy();before=z[:,:4].copy()
            ens.k=np.array([base.k*factor(x['arm'],stage,cfg) for x in rows])
            jump=spring_work_scaled(z[:,0],old,ens.k,base);work+=jump
            events.append(dict(time_s=step*dt,before_state_scaled=before.tolist(),after_state_scaled=z[:,:4].tolist(),spring_work_scaled=jump.tolist()))
        if step%stride==0:
            saved[at]=z[:,:4];at+=1
            error=np.maximum(error,np.abs(ens.energy(z)-initial_energy-z[:,4]-z[:,5]+z[:,6]-work))
            invalid=(~np.all(np.isfinite(z),axis=1))|(np.max(np.abs(z[:,:4]),axis=1)>cfg['gates']['state_guard_scaled'])
            if np.any(invalid):raise RuntimeError('Nonfinite or guarded trajectory; do not classify')
        if step==steps[-1]:break
        f0=table[ci,(2*step)%count][cond];fm=table[ci,(2*step+1)%count][cond];f1=table[ci,(2*step+2)%count][cond]
        a=ens.rhs(z,f0);b=ens.rhs(z+dt*a/2,fm);c=ens.rhs(z+dt*b/2,fm);d=ens.rhs(z+dt*c,f1)
        z+=dt*(a+2*b+2*c+d)/6
        if progress and (step+1)%max(1,steps[-1]//10)==0:print(f'dt={dt:g}: {(step+1)*dt:.1f}/{bounds[-1]:.1f} s',flush=True)
    return dict(time_s=times,state=saved,energy_error=error,final=z,switch_work=work,events=np.array(json.dumps(events)),guard=guard)

def repeat_windows(strobes,cfg):
    """All four state components; no window crosses a parameter switch."""
    nmax=cfg['maximum_repeat_orbits'];w=cfg['repeat_comparisons'];errors=[]
    for i in range(len(strobes)):
        errors.append(None if i<w+nmax-1 else [float(np.max(np.abs(strobes[i-w+1:i+1]-strobes[i-w+1-n:i+1-n]))) for n in range(1,nmax+1)])
    return errors

def classify(errors,history_error,half_amplitude,cfg):
    if errors is None:return 'assessing'
    if half_amplitude<=cfg['gates']['observable_half_amplitude_mm']:return 'quiet'
    if min(errors)<cfg['gates']['repeat_error_scaled'] and history_error<cfg['gates']['between_history_error_scaled']:return 'synchronized'
    return 'no_short_repeat'

def stable_first_time(times,statuses,target):
    tail=[i for i,s in enumerate(statuses) if s!=target]
    index=(tail[-1]+1) if tail else 0
    return float(times[index]) if index<len(times) else None

def summarize(cfg,data):
    rows=cases(cfg);bounds=boundaries(cfg);p=cfg['orbit_period_s'];dt=cfg['sample_interval_s'];out=[]
    for arm in cfg['arms']:
        for condition in range(7):
            indices=[i for i,x in enumerate(rows) if x['arm']==arm and x['condition']==condition]
            pair=data['state'][:,indices,:];stages=[]
            for stage,(a,b) in enumerate(zip(bounds[:-1],bounds[1:])):
                time=np.arange(int(round((b-a)/p))+1)*p+a
                ids=np.rint(time/dt).astype(int);z=pair[ids]
                errors=repeat_windows(z,cfg);history=np.max(np.abs(z[:,0]-z[:,1]),axis=1)
                lo=int(round(a/dt));hi=int(round(b/dt));half=float(np.ptp(pair[lo:hi+1,:,0],axis=0).min()*.05)
                labels=[classify(e,float(h),half,cfg) for e,h in zip(errors,history)]
                stages.append(dict(stage=stage,time_s=np.round(time,8).tolist(),errors_scaled=errors,status=labels,
                    between_history_error_scaled=history.tolist(),half_amplitude_mm=half,
                    first_sustained_lock_s=stable_first_time(time,labels,'synchronized'),
                    first_sustained_nonrepeat_s=stable_first_time(time,labels,'no_short_repeat'),end_status=labels[-1]))
            lost=stages[1]['first_sustained_nonrepeat_s']
            regained=stages[2]['first_sustained_lock_s'] if lost is not None else None
            out.append(dict(arm=arm,condition=condition,stages=stages,
                loss_confirmed_s=lost,relock_confirmed_s=regained,
                confirmation_delay_after_restore_s=None if regained is None else regained-bounds[2]))
    return out

def independent_controls(cfg,data):
    params,conditions,_=initial_states(cfg);base=Model(params);bounds=boundaries(cfg);rows=cases(cfg);p=cfg['orbit_period_s'];out=[]
    for condition in range(7):
        j=next(i for i,x in enumerate(rows) if x==dict(arm='restore',condition=condition,history=0))
        for label,begin,end in [('raise',bounds[1]-p,bounds[1]+p),('restore',bounds[2]-p,bounds[2]+p),('late',bounds[3]-2*p,bounds[3])]:
            first=int(round(begin/cfg['sample_interval_s']));last=int(round(end/cfg['sample_interval_s']));t=data['time_s'][first:last+1];truth=data['state'][first:last+1,j]
            y=truth[0]*base.scale;pred=np.empty_like(truth);pred[0]=y
            cuts=[begin]+[v for v in bounds[1:-1] if begin<v<end]+[end]
            for a,b in zip(cuts[:-1],cuts[1:]):
                stage=0 if (a+b)/2<bounds[1] else 1 if (a+b)/2<bounds[2] else 2;k=base.k*factor('restore',stage,cfg)
                def rhs(v,y):
                    q,speed,u,w=y;sigma=base.gm*(q/base.length-u-w)
                    f=float(r.force(cfg['absolute_start_s']+v,conditions[condition],cfg))
                    return [speed,(-k*q-base.volume*sigma/base.length+(base.gain-base.saturation*q*q)*speed+f)/base.mass,(sigma-base.gk*u)/base.ek,sigma/base.em]
                sol=solve_ivp(rhs,(a,b),y,method='Radau',rtol=2e-10,atol=2e-15,max_step=.035,dense_output=True)
                if not sol.success:raise RuntimeError(sol.message)
                mask=(t>=a-1e-8)&(t<=b+1e-8);pred[mask]=sol.sol(t[mask]).T;y=sol.y[:,-1]
            out.append(dict(condition=condition,window=label,error_scaled=float(np.max(np.abs(pred/base.scale-truth)))))
    return out

def analyze(cfg,main,fine):
    params,conditions,_=initial_states(cfg);a=summarize(cfg,main);b=summarize(cfg,fine)
    controls=independent_controls(cfg,main);events=json.loads(str(main['events']));g=cfg['gates'];rows=cases(cfg)
    timing=[]
    for x,y in zip(a,b):
        for key in ('loss_confirmed_s','relock_confirmed_s'):
            if (x[key] is None)!=(y[key] is None):timing.append(float('inf'))
            elif x[key] is not None:timing.append(abs(x[key]-y[key]))
    refinement=float(np.max(np.abs(main['state']-fine['state'])))
    checks=dict(finite_trajectories=bool(np.all(np.isfinite(main['state'])) and np.all(np.isfinite(fine['state']))),
        state_continuity=all(e['before_state_scaled']==e['after_state_scaled'] for e in events),
        energy_balance=max(float(main['energy_error'].max()),float(fine['energy_error'].max()))<g['energy_error_scaled'],
        full_path_refinement=refinement<g['full_path_refinement_error_scaled'],
        classification_refinement=all(s['status']==t['status'] for x,y in zip(a,b) for s,t in zip(x['stages'],y['stages'])),
        event_time_refinement=max(timing,default=0)<=g['event_time_refinement_orbits']*cfg['orbit_period_s'],
        independent_solver=max(c['error_scaled'] for c in controls)<g['independent_solver_error_scaled'])
    result=dict(origin=cfg['origin'],protocol=cfg,conditions=conditions,cases=rows,summary=a,refined_summary=b,checks=checks,
        numerical_status='passed' if all(checks.values()) else 'failed_checks_retained',physical_measurements=0,additional_sims_runs=0,
        maximum_full_path_refinement_error_scaled=refinement,maximum_event_time_refinement_s=max(timing,default=0),
        maximum_energy_error_scaled=max(float(main['energy_error'].max()),float(fine['energy_error'].max())),independent_controls=controls,
        switch_events=events,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [cfg['initial_results'],'hug_rhythm.py','hug_rhythm_protocol.json','hug_robustness.py','hug_sync_protocol.json','calibration/synthetic_truth.json']})
    audit=ROOT/'hug_sync_initial_audit.json'
    if audit.exists():result['initial_resolution_audit']=json.loads(audit.read_text())
    return compact_result(result)

def compact_result(result):
    """Keep main diagnostic timelines and compact the redundant refinement audit."""
    for row in result['summary']:
        for stage in row['stages']:
            if 'between_history_error_scaled' in stage:
                stage['maximum_between_history_error_scaled']=max(stage.pop('between_history_error_scaled'))
    for row in result['refined_summary']:
        if 'stages' in row:
            stages=row.pop('stages')
            row['stage_end_status']=[x['end_status'] for x in stages]
            row['maximum_between_history_error_scaled']=max(max(x['between_history_error_scaled']) for x in stages)
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache-dir',type=Path);ap.add_argument('--analyze-only',action='store_true');args=ap.parse_args()
    cfg=protocol();cache=args.cache_dir or ROOT/'.sync-cache';cache.mkdir(exist_ok=True,parents=True)
    for name,dt in [('main',cfg['main_step_s']),('refined',cfg['refined_step_s'])]:
        if not args.analyze_only:np.savez_compressed(cache/(name+'.npz'),**integrate(cfg,dt))
    with np.load(cache/'main.npz') as m,np.load(cache/'refined.npz') as f:
        result=analyze(cfg,{k:m[k] for k in m.files},{k:f[k] for k in f.files})
    (ROOT/'hug_sync_results.json').write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k in ('checks','maximum_energy_error_scaled','maximum_full_path_refinement_error_scaled','maximum_event_time_refinement_s')}),flush=True)
    for x in result['summary']:print(json.dumps({k:v for k,v in x.items() if k!='stages'}),flush=True)

if __name__=='__main__':main()
