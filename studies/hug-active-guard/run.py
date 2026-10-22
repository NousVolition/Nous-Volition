"""Frozen, bounded main/refined integrations; caches are not published."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import argparse,hashlib,json,time,platform
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from model import ROOT,Ensemble,cases,protocol

def anchors():
    return {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['model.py','protocol.json','run.py']}

def integrate(p,rows,kind):
    model=Ensemble(p,rows);z=np.column_stack([model.start(),np.zeros((len(rows),4))]);initial=model.energy(z)
    H=p['horizon_s'];tail=H-p['tail_s'];sample=np.unique(np.round(np.r_[np.arange(0,H+1,p['history_sample_s']),np.arange(0,60+.025,.05),np.arange(tail,H+.025,.05)],8))
    cfg=p['solver'];states=[];times=[];energy=0.;lo=1.;hi=0.;nfev=0;started=time.monotonic()
    for begin in np.arange(0,H,300):
        end=min(begin+300,H);tt=sample[(sample>=begin)&(sample<=end)]
        def fun(t,flat):
            if time.monotonic()-started>p['resources']['max_seconds_per_integration']:raise TimeoutError('Frozen integration wall budget exceeded')
            return model.rhs(t,flat.reshape(len(rows),12)).ravel()
        sol=solve_ivp(fun,(begin,end),z.ravel(),method='DOP853',t_eval=tt,rtol=cfg[kind+'_rtol'],atol=cfg[kind+'_atol'],max_step=cfg[kind+'_max_step_s'])
        if not sol.success:raise RuntimeError(sol.message)
        yy=sol.y.T.reshape(-1,len(rows),12);nfev+=sol.nfev;z=yy[-1].copy()
        residual=model.energy(yy)-initial-yy[:,:,8]-yy[:,:,9]+yy[:,:,10]+yy[:,:,11]
        energy=max(energy,float(np.max(np.abs(residual))))
        gg=yy[:,~model.old,6:8];lo=min(lo,float(gg.min()));hi=max(hi,float(gg.max()))
        if not np.isfinite(yy).all():raise ArithmeticError('Nonfinite trajectory')
        if lo < -p['gates']['guard_bounds'] or hi>1+p['gates']['guard_bounds']:raise ArithmeticError('Guard escaped interval; no clipping')
        keep=tt>begin if len(times) else np.ones(len(tt),bool)
        states.append(yy[keep,:,:8]);times.extend(tt[keep].tolist())
        print(f'{kind}: {end:g}/{H:g} s; residual {energy:.3g}; elapsed {time.monotonic()-started:.1f} s',flush=True)
    return dict(time=np.array(times),state=np.concatenate(states),final=z,energy_residual=np.array(energy),guard_range=np.array([lo,hi]),elapsed_s=np.array(time.monotonic()-started),nfev=np.array(nfev))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache',type=Path,required=True);ap.add_argument('--kind',choices=['main','fine'],required=True);a=ap.parse_args()
    a.cache.mkdir(parents=True,exist_ok=True);target=a.cache/(a.kind+'.npz')
    if target.exists():raise FileExistsError('Preserve prior run; choose a fresh cache')
    freeze=ROOT/'freeze.json';now=anchors()
    if freeze.exists():assert json.loads(freeze.read_text())['sha256']==now,'Frozen source changed'
    else:freeze.write_text(json.dumps(dict(sha256=now,python=platform.python_version(),numpy=np.__version__),indent=2)+'\n')
    p=protocol();data=integrate(p,cases(p),a.kind);np.savez_compressed(target,**data)
    assert anchors()==now
    print(json.dumps(dict(file=str(target),energy_residual=float(data['energy_residual']),guard_range=data['guard_range'].tolist(),elapsed_s=float(data['elapsed_s']))))
if __name__=='__main__':main()
