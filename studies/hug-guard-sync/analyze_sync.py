"""Matched full-state confirmation times, projection audit and independent solves."""
import argparse,copy,json
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
import guard_sync as s

def summarize(cfg,rows,state,projection=False):
    out=[];P=cfg['orbit_period_s'];dt=cfg['sample_interval_s'];bounds=cfg['boundaries_s']
    for model in cfg['models']:
        for arm in cfg['arms']:
            for condition in range(1,8):
                ids=[i for i,r in enumerate(rows) if r['model']==model and r['arm']==arm and r['condition']==condition];dim=4 if model=='old' or projection else 8;stages=[]
                for stage,(a,b) in enumerate(zip(bounds[:-1],bounds[1:])):
                    tt=np.round(a+np.arange(int(round((b-a)/P))+1)*P,8);ix=np.rint(tt/dt).astype(int);z=state[ix][:,ids,:dim]
                    err=s.legacy.repeat_windows(z,cfg);history=np.max(abs(z[:,0]-z[:,1]),axis=1)
                    lo=int(round(a/dt));hi=int(round(b/dt));half=float(np.ptp(state[lo:hi+1,ids,0],axis=0).min()*.05)
                    status=[s.legacy.classify(e,float(h),half,cfg) for e,h in zip(err,history)]
                    stages.append(dict(stage=stage,time_s=tt.tolist(),errors=err,status=status,history_error=history.tolist(),half_amplitude_mm=half,end_status=status[-1],sustained_lock_s=s.legacy.stable_first_time(tt,status,'synchronized'),sustained_nonrepeat_s=s.legacy.stable_first_time(tt,status,'no_short_repeat')))
                loss=stages[1]['sustained_nonrepeat_s'];relock=stages[2]['sustained_lock_s'] if loss is not None else None
                out.append(dict(model=model,arm=arm,condition=condition,dimensions=dim,stages=stages,loss_confirmed_s=loss,relock_confirmed_s=relock,confirmation_delay_after_restore_s=None if relock is None else relock-bounds[2]))
    return out

def independent(cfg,p,rows,time_grid,state):
    bounds=cfg['boundaries_s'];P=cfg['orbit_period_s'];out=[];scale=s.physical_scale(p)
    for j,row in enumerate(rows):
        if row['arm']!='restore' or row['history']:continue
        for label,begin,end in [('raise',bounds[1]-P,bounds[1]+P),('restore',bounds[2]-P,bounds[2]+P),('late',bounds[-1]-2*P,bounds[-1])]:
            a=int(round(begin/.05));b=int(round(end/.05));tt=time_grid[a:b+1];truth=state[a:b+1,j];y=truth[0]*scale;pred=np.zeros_like(truth)
            cuts=[begin]+[x for x in bounds[1:-1] if begin<x<end]+[end]
            for start,stop in zip(cuts[:-1],cuts[1:]):
                stage=int(np.searchsorted(bounds[1:-1],(start+stop)/2,side='right'));pp=copy.deepcopy(p);pp['mechanics']['parallel_stiffness_N_m']*=s.factor(row['arm'],stage,cfg)
                physical=s.physical_rhs(pp,s.base_rows([row])[0]);fun=lambda t,z:physical(cfg['absolute_start_s']+t,z)
                sol=solve_ivp(fun,(start,stop),y,method='Radau',rtol=2e-11,atol=2e-16,max_step=.025,dense_output=True)
                if not sol.success:raise RuntimeError(sol.message)
                mask=(tt>=start-1e-8)&(tt<=stop+1e-8);pred[mask]=sol.sol(tt[mask]).T;y=sol.y[:,-1]
            out.append(dict(model=row['model'],condition=row['condition'],window=label,error_scaled=float(np.max(abs(pred/scale-truth)))))
    return out

def compact(rows):
    return [{k:v for k,v in r.items() if k!='stages'}|dict(stage_end_status=[x['end_status'] for x in r['stages']]) for r in rows]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache',type=Path,required=True);a=ap.parse_args();cfg=s.protocol();p=s.guard_protocol();rows=s.cases(cfg)
    main=np.load(a.cache/'main/state.npy',mmap_mode='r');fine=np.load(a.cache/'fine/state.npy',mmap_mode='r');tt=np.load(a.cache/'main/time.npy');assert np.array_equal(tt,np.load(a.cache/'fine/time.npy'))
    meta=[json.loads((a.cache/k/'metadata.json').read_text()) for k in ['main','fine']]
    full=summarize(cfg,rows,main);ref=summarize(cfg,rows,fine);proj=summarize(cfg,rows,main,True);controls=independent(cfg,p,rows,tt,main)
    difference=max(float(np.max(abs(main[i:i+1000]-fine[i:i+1000]))) for i in range(0,len(tt),1000));timing=[]
    for x,y in zip(full,ref):
        for key in ['loss_confirmed_s','relock_confirmed_s']:
            timing.append(0 if x[key] is None and y[key] is None else None if x[key] is None or y[key] is None else abs(x[key]-y[key]))
    historical=json.loads((s.OLD/'hug_sync_results.json').read_text());comparison=[]
    for c in range(1,8):
        old=next(x for x in full if x['model']=='old' and x['arm']=='restore' and x['condition']==c);new=next(x for x in full if x['model']=='directional' and x['arm']=='restore' and x['condition']==c);legacy=next(x for x in historical['summary'] if x['arm']=='restore' and x['condition']==c-1);projected=next(x for x in proj if x['model']=='directional' and x['arm']=='restore' and x['condition']==c)
        A=old['confirmation_delay_after_restore_s'];B=new['confirmation_delay_after_restore_s'];C=legacy['confirmation_delay_after_restore_s']
        comparison.append(dict(condition=c,name=p['conditions'][c]['name'],old_delay_s=A,updated_delay_s=B,updated_mechanical_projection_delay_s=projected['confirmation_delay_after_restore_s'],historical_old_delay_s=C,updated_minus_old_s=None if A is None or B is None else B-A,historical_reproduction_difference_s=None if A is None or C is None else A-C))
    g=cfg['gates'];guards=[min(x['guard_range'][0] for x in meta),max(x['guard_range'][1] for x in meta)];energy=max(max(x['energy_error']) for x in meta);ind=max(x['error_scaled'] for x in controls)
    check=dict(finite=all(bool(np.isfinite(x[i:i+1000]).all()) for x in [main,fine] for i in range(0,len(tt),1000)),state_continuity=all(e['before']==e['after'] for x in meta for e in x['events']),energy_balance=energy<g['energy_error_scaled'],path_refinement=difference<g['full_path_refinement_error_scaled'],classifications=all(x['status']==y['status'] for r,v in zip(full,ref) for x,y in zip(r['stages'],v['stages'])),confirmation_timing=all(x is not None and x<=g['event_time_refinement_orbits']*cfg['orbit_period_s'] for x in timing),independent_solver=ind<g['independent_solver_error_scaled'],guard_bounds=guards[0]>=-g['guard_bounds'] and guards[1]<=1+g['guard_bounds'],updated_settlement=all(x['settlement']['repeat_error']<g['repeat_error_scaled'] and x['settlement']['history_error']<g['between_history_error_scaled'] and x['settlement']['energy_error']<g['energy_error_scaled'] for x in meta),baseline_locked=all(r['stages'][0]['end_status']=='synchronized' for r in full))
    result=dict(origin=cfg['origin'],protocol=cfg,model_protocol=p,conditions=p['conditions'][1:],cases=rows,summary=full,refined_summary=compact(ref),mechanical_projection=compact(proj),comparison=comparison,checks=check,numerical_status='passed' if all(check.values()) else 'failed_checks_retained',maximum_path_difference=difference,maximum_energy_residual=energy,maximum_independent_error=ind,confirmation_time_differences_s=timing,guard_range=guards,independent_controls=controls,run_metadata=meta,historical_results_sha256=s.sha(s.OLD/'hug_sync_results.json'),source_sha256=s.dependencies(),physical_measurements=0)
    (s.ROOT/'results.json').write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(checks=check,path=difference,energy=energy,independent=ind,comparison=comparison),indent=2),flush=True)
if __name__=='__main__':main()
