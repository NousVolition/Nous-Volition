"""Continuous old/new Hug runs across exact stiffness changes."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,copy,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
ROOT=Path(__file__).resolve().parent
GUARD=ROOT.parent/'hug-active-guard';OLD=ROOT.parent/'dynamics-fractals-sims'
sys.path.insert(0,str(GUARD))
from model import Ensemble,physical_rhs,physical_scale,protocol as guard_protocol
import hug_sync as legacy

def protocol():return json.loads((ROOT/'protocol.json').read_text())
def cases(cfg):return [dict(model=m,arm=a,condition=c,history=h) for m in cfg['models'] for a in cfg['arms'] for c in range(1,8) for h in cfg['histories']]
def base_rows(rows):return [dict(model=r['model'],condition=r['condition'],start=r['history']) for r in rows]
def factor(arm,stage,cfg):return cfg['stiffness_factor'] if arm!='sham' and (stage==1 or stage==2 and arm=='hold_high') else 1.
def spring_work(q,old,new,m):return .5*(new-old)*(m.Q*q)**2/m.E0
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dependencies():
    p=['protocol.json','guard_sync.py','analyze_sync.py','../hug-active-guard/model.py','../hug-active-guard/protocol.json','../dynamics-fractals-sims/hug_sync.py','../dynamics-fractals-sims/hug_sync_protocol.json','../dynamics-fractals-sims/hug_sync_results.json','../dynamics-fractals-sims/hug_robustness_results.json']
    d={f:sha(ROOT/f) for f in p}
    for f in json.loads((GUARD/'provenance.json').read_text())['parent_sha256']:d['../dynamics-fractals-sims/'+f]=sha(OLD/f)
    return d

def settled(cfg,kind,destination):
    p=guard_protocol();rows=[dict(model='directional',condition=c,start=h) for c in range(1,8) for h in cfg['histories']];m=Ensemble(p,rows)
    z=np.column_stack([m.start(),np.zeros((14,4))]);energy0=m.energy(z);error=0;start=time.monotonic();solver=cfg['solver'];last=None
    for begin in range(0,cfg['absolute_start_s'],300):
        end=min(begin+300,cfg['absolute_start_s']);tt=np.linspace(begin,end,int(round((end-begin)/.05))+1)
        def rhs(t,y):
            if time.monotonic()-start>cfg['max_seconds_per_integration']:raise TimeoutError('Settlement wall limit')
            return m.rhs(t,y.reshape(14,12)).ravel()
        sol=solve_ivp(rhs,(begin,end),z.ravel(),method='DOP853',t_eval=tt,rtol=solver[kind+'_rtol'],atol=solver[kind+'_atol'],max_step=solver[kind+'_max_step_s'])
        if not sol.success:raise RuntimeError(sol.message)
        yy=sol.y.T.reshape(-1,14,12);z=yy[-1].copy();res=m.energy(yy)-energy0-yy[:,:,8]-yy[:,:,9]+yy[:,:,10]+yy[:,:,11];error=max(error,float(np.max(abs(res))))
        if not np.isfinite(yy).all():raise ArithmeticError('Settlement nonfinite')
        last=(tt,yy[:,:,:8].copy())
        if end%1200==0:print(f'{kind} settle {end}/6000 s',flush=True)
    tt,yy=last;np.savez_compressed(destination/'settling_tail.npz',time=tt,state=yy)
    # Fixed phase at absolute 6000; use the last 40 orbit samples from this tail.
    st=cfg['absolute_start_s']-np.arange(40,-1,-1)*cfg['orbit_period_s'];ix=np.rint((st-tt[0])/.05).astype(int);zz=yy[ix]
    repeat=float(np.max(abs(zz[1:]-zz[:-1])));history=float(np.max(abs(zz[:,0::2]-zz[:,1::2])))
    old_cfg=legacy.protocol();params,_,old_state=legacy.initial_states(old_cfg);assert all(params[k]==p[k] for k in ('material','mechanics','feedback'))
    initial={}
    for r,y in zip(legacy.cases(old_cfg),old_state):
        if r['arm']=='restore':initial[('old',r['condition']+1,r['history'])]=np.r_[y,np.zeros(4)]
    for r,y in zip(rows,z):initial[('directional',r['condition'],r['start'])]=y[:8]
    return np.array([initial[(r['model'],r['condition'],r['history'])] for r in cases(cfg)]),dict(repeat_error=repeat,history_error=history,energy_error=error,settling_seconds=time.monotonic()-start)

def integrate(cfg,p,rows,initial,destination,kind,progress=True):
    destination.mkdir(exist_ok=True,parents=True);m=Ensemble(p,base_rows(rows));base_k=float(m.k);m.k=np.full(len(rows),base_k);n=len(rows);dt=cfg['sample_interval_s'];bounds=cfg['boundaries_s'];solver=cfg['solver']
    time_grid=np.round(np.arange(int(round(bounds[-1]/dt))+1)*dt,8)
    saved=np.lib.format.open_memmap(destination/'state.npy',mode='w+',dtype='float64',shape=(len(time_grid),n,8));np.save(destination/'time.npy',time_grid)
    z=np.column_stack([initial,np.zeros((n,4))]);saved[0]=initial;energy0=m.energy(z);work=np.zeros(n);error=np.zeros(n);events=[];started=time.monotonic();lo=1.;hi=0.
    for stage,(begin,end) in enumerate(zip(bounds[:-1],bounds[1:])):
        previous=m.k.copy();m.k=np.array([base_k*factor(r['arm'],stage,cfg) for r in rows])
        if stage:
            before=z[:,:8].copy();jump=spring_work(z[:,0],previous,m.k,m);work+=jump
            events.append(dict(time_s=begin,before=before.tolist(),after=z[:,:8].tolist(),spring_work_scaled=jump.tolist()))
            error=np.maximum(error,abs(m.energy(z)-energy0-z[:,8]-z[:,9]+z[:,10]+z[:,11]-work))
        for a in np.arange(begin,end,300):
            b=min(a+300,end);ia=int(round(a/dt));ib=int(round(b/dt));tt=time_grid[ia:ib+1]
            def rhs(t,y):
                if time.monotonic()-started>cfg['max_seconds_per_integration']:raise TimeoutError('Live integration wall limit')
                return m.rhs(cfg['absolute_start_s']+t,y.reshape(n,12)).ravel()
            sol=solve_ivp(rhs,(a,b),z.ravel(),method='DOP853',t_eval=tt,rtol=solver[kind+'_rtol'],atol=solver[kind+'_atol'],max_step=solver[kind+'_max_step_s'])
            if not sol.success:raise RuntimeError(sol.message)
            yy=sol.y.T.reshape(-1,n,12);z=yy[-1].copy();saved[ia:ib+1]=yy[:,:,:8]
            error=np.maximum(error,np.max(abs(m.energy(yy)-energy0-yy[:,:,8]-yy[:,:,9]+yy[:,:,10]+yy[:,:,11]-work),axis=0))
            if not np.isfinite(yy).all() or np.max(abs(yy[:,:,:8]))>cfg['gates']['state_guard_scaled']:raise ArithmeticError('Invalid trajectory; no classification')
            if np.any(~m.old):gg=yy[:,~m.old,6:8];lo=min(lo,float(gg.min()));hi=max(hi,float(gg.max()))
            if progress:print(f'{kind} live {b:g}/{bounds[-1]} s; energy {error.max():.3g}',flush=True)
    saved.flush()
    meta=dict(cases=rows,events=events,energy_error=error.tolist(),guard_range=[lo,hi],runtime_s=time.monotonic()-started,initial=initial.tolist(),final=z[:,:8].tolist())
    (destination/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n');return meta

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache',type=Path,required=True);ap.add_argument('--kind',choices=['main','fine'],required=True);a=ap.parse_args();dest=a.cache/a.kind
    if dest.exists():raise FileExistsError('Preserve previous run; choose a new cache')
    dest.mkdir(parents=True);cfg=protocol();anchors=dependencies();freeze=ROOT/'freeze.json'
    if freeze.exists():assert json.loads(freeze.read_text())['sha256']==anchors,'Frozen source changed'
    else:freeze.write_text(json.dumps(dict(sha256=anchors,python=sys.version.split()[0],numpy=np.__version__),indent=2)+'\n')
    initial,settle=settled(cfg,a.kind,dest);meta=integrate(cfg,guard_protocol(),cases(cfg),initial,dest,a.kind)
    meta['settlement']=settle;(dest/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n');assert dependencies()==anchors
    print(json.dumps(dict(settlement=settle,max_energy=max(meta['energy_error']),runtime=meta['runtime_s'])),flush=True)
if __name__=='__main__':main()
