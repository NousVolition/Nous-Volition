"""Full-state repeat tests, independently integrated controls and cycle stability."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import CubicHermiteSpline
from scipy.optimize import brentq,root
from model import ROOT,Ensemble,protocol,cases,physical_rhs,physical_scale,raw_tide,tide_rms

def spline(p,row,t,z):
    e=p['conditions'][row['condition']]['e'];F=np.zeros(len(t)) if e is None else p['orbital_force_rms_N']*raw_tide(t/p['orbit_period_s'],e)/tide_rms(e)
    m=Ensemble(p,[row]*len(t));return CubicHermiteSpline(t,z,m.rhs(0,z,F))

def metrics(p,row,t,z):
    dim=4 if row['model']=='old' else 8;h=spline(p,row,t,z);half=float(np.ptp(z[:,0])*.05)
    idx=np.where((z[:-1,0]<0)&(z[1:,0]>=0))[0]
    cross=np.array([brentq(lambda v:h(v)[0],t[i],t[i+1],xtol=1e-12) for i in idx])
    out=dict(**row,half_amplitude_mm=half,mean_guard=np.mean(z[:,6:8],axis=0).tolist(),guard_range=[float(z[:,6:8].min()),float(z[:,6:8].max())],participant_mean=np.mean(z[:,4:6],axis=0).tolist())
    out['mean_added_damping_N_s_m']=0 if row['model']=='old' else float(p['guard']['damping_per_guard_N_s_m']*np.mean(z[:,6]+z[:,7]))
    if len(cross)>21 and half>p['gates']['observable_half_amplitude_mm']:
        section=h(cross[-21:]);interval=np.diff(cross[-21:])
        out.update(mean_period_s=float(interval.mean()),period_cv=float(interval.std()/interval.mean()),section_repeat_error=float(np.max(np.abs(np.diff(section[:,:dim],axis=0)))),section_last=section[-1].tolist(),section_recent=section[-5:,:dim].tolist())
    else:out.update(mean_period_s=None,period_cv=None,section_repeat_error=None,section_last=None,section_recent=None)
    if row['condition']:
        P=p['orbit_period_s'];st=np.arange(np.ceil(t[0]/P),np.floor(t[-1]/P)+1)*P;zz=h(st)
        out['orbit_repeat_errors']=[float(np.max(np.abs(zz[-20:,:dim]-zz[-20-n:-n,:dim]))) for n in range(1,5)]
        out['orbit_recent']=zz[-20:,:dim].tolist()
    else:out['orbit_repeat_errors']=None;out['orbit_recent']=None
    return out

def summarize(p,rows,t,state):
    mask=t>=p['horizon_s']-p['tail_s'];tailt=t[mask];details=[];summary=[]
    for j,row in enumerate(rows):details.append(metrics(p,row,tailt,state[mask,j]))
    for model in p['models']:
        for c in range(8):
            a,b=[x for x in details if x['model']==model and x['condition']==c]
            quiet=max(a['half_amplitude_mm'],b['half_amplitude_mm'])<=p['gates']['observable_half_amplitude_mm']
            compare='orbit_recent' if c else 'section_recent'
            history=None if a[compare] is None or b[compare] is None else float(np.max(np.abs(np.array(a[compare])-np.array(b[compare]))))
            if c:
                errors=np.maximum(a['orbit_repeat_errors'],b['orbit_repeat_errors']);best=int(errors.argmin());repeat=float(errors[best]);lag=best+1
            else:
                repeat=None if a['section_repeat_error'] is None or b['section_repeat_error'] is None else max(a['section_repeat_error'],b['section_repeat_error']);lag=None
            passed=repeat is not None and repeat<p['gates']['repeat_error'] and history is not None and history<p['gates']['history_error']
            status='quiet' if quiet else ('orbital repeat confirmed' if c else 'autonomous repeat confirmed') if passed else ('no confirmed 1-4 orbit repeat' if c else 'unsettled autonomous motion')
            summary.append(dict(model=model,condition=c,name=p['conditions'][c]['name'],status=status,repeat_error=repeat,between_start_error=history,best_lag_orbits=lag,
                half_amplitude_mm=a['half_amplitude_mm'],second_start_half_amplitude_mm=b['half_amplitude_mm'],mean_period_s=a['mean_period_s'],period_cv=a['period_cv'],mean_guard=a['mean_guard'],mean_added_damping_N_s_m=a['mean_added_damping_N_s_m']))
    return details,summary

def jacobian(p,row,y):
    m=Ensemble(p,[row]);q,v,u,w,A,B,ga,gb=y;g=p['guard'];d=B-A;J=np.zeros((8,8))
    J[0,1]=1;J[1,0]=-(m.k+m.ck+2*m.sat[0]*q*v)/m.mass
    J[1,1]=(m.gain[0]-m.sat[0]*q*q-m.c[0]*(ga+gb))/m.mass;J[1,2:4]=m.ck/m.mass;J[1,6:]=-m.c[0]*v/m.mass
    J[2,:4]=[m.gm/m.ek,0,-(m.gm+m.gk)/m.ek,-m.gm/m.ek];J[3,:4]=[m.gm/m.em,0,-m.gm/m.em,-m.gm/m.em]
    if row['model']=='old':return J
    J[4,4]=-g['lambda_per_s']-m.ka[0]*ga;J[4,5]=m.ka[0]*ga;J[4,6]=m.ka[0]*d
    J[5,4]=m.kb[0]*gb;J[5,5]=-g['lambda_per_s']-m.kb[0]*gb;J[5,7]=-m.kb[0]*d
    if row['model']=='frozen':return J
    from scipy.special import expit
    targets=expit(g['theta']+g['beta']*np.array([d,-d])+m.chi[0]*.5*(v*g['rate_reference_s'])**2)
    deriv=targets*(1-targets)/g['tau_s']
    for i,sign in enumerate([1,-1]):
        J[6+i,1]=deriv[i]*m.chi[0]*v*g['rate_reference_s']**2
        J[6+i,4]=-sign*g['beta']*deriv[i];J[6+i,5]=sign*g['beta']*deriv[i]
    if row['model']=='shared':J[6:8]=J[6:8].mean(axis=0,keepdims=True)
    J[6,6]=-1/g['tau_s'];J[7,7]=-1/g['tau_s'];return J

def cycle(p,row,seed,period):
    dim=4 if row['model']=='old' else 8;m=Ensemble(p,[row])
    def fun(t,z):return m.rhs(t,np.pad(z,(0,8-len(z)))[None],np.zeros(1))[0,:dim]
    def residual(a,return_sol=False):
        y=np.r_[0,a[:-1]];P=float(np.exp(a[-1]))
        if not .5<P<10:raise ValueError('Cycle solver left declared period search')
        sol=solve_ivp(fun,(0,P),y,method='DOP853',rtol=2e-11,atol=2e-13,max_step=.04)
        return sol if return_sol else sol.y[:,-1]-y
    fit=root(residual,np.r_[seed[1:dim],np.log(period)],tol=1e-9);err=float(np.max(np.abs(residual(fit.x))))
    y=np.r_[0,fit.x[:-1]];P=float(np.exp(fit.x[-1]));eps=1e-6;yy=np.pad(y,(0,8-dim));J=jacobian(p,row,yy)
    numeric=np.column_stack([(m.rhs(0,(yy+eps*np.eye(8)[j])[None],np.zeros(1))[0]-m.rhs(0,(yy-eps*np.eye(8)[j])[None],np.zeros(1))[0])/(2*eps) for j in range(8)])
    jerr=float(np.max(np.abs(J-numeric)))
    def variational(t,z):
        zz=np.pad(z[:dim],(0,8-dim));return np.r_[fun(t,z[:dim]),(jacobian(p,row,zz)[:dim,:dim]@z[dim:].reshape(dim,dim)).ravel()]
    sol=solve_ivp(variational,(0,P),np.r_[y,np.eye(dim).ravel()],method='DOP853',rtol=2e-11,atol=2e-13,max_step=.035)
    eig=np.linalg.eigvals(sol.y[dim:,-1].reshape(dim,dim));i=int(np.argmin(abs(eig-1)));trans=float(np.max(np.abs(np.delete(eig,i))))
    neutral=float(abs(eig[i]-1));passed=err<p['gates']['shooting_error'] and neutral<p['gates']['floquet_neutral_error'] and trans<p['gates']['floquet_transverse_max'] and y[1]>0 and jerr<1e-7
    return dict(model=row['model'],period_s=P,shooting_error=err,neutral_error=neutral,largest_transverse_modulus=trans,jacobian_error=jerr,multipliers=[[float(x.real),float(x.imag)] for x in eig],passed=bool(passed))

def independent(p,rows,t,state):
    results=[];scale=physical_scale(p)
    for j,row in enumerate(rows):
        if row['start'] or row['condition'] not in [0,1,2] and not(row['model'] in ['old','directional'] and row['condition']==3):continue
        for begin in [0,p['horizon_s']-11.4]:
            mask=(t>=begin-1e-8)&(t<=begin+11.4+1e-8);tt=t[mask];z=state[mask,j];fun=physical_rhs(p,row)
            sol=solve_ivp(fun,(tt[0],tt[-1]),z[0]*scale,t_eval=tt,method='Radau',rtol=2e-10,atol=2e-15,max_step=.04)
            if not sol.success:raise RuntimeError(sol.message)
            results.append(dict(**row,begin_s=float(tt[0]),error=float(np.max(np.abs(sol.y.T/scale-z)))))
    return results

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache',type=Path,required=True);a=ap.parse_args();p=protocol();rows=cases(p)
    with np.load(a.cache/'main.npz') as f:main={k:f[k] for k in f.files}
    with np.load(a.cache/'fine.npz') as f:fine={k:f[k] for k in f.files}
    assert np.array_equal(main['time'],fine['time']);t=main['time'];diff=float(np.max(np.abs(main['state']-fine['state'])))
    details,summary=summarize(p,rows,t,main['state']);_,refined=summarize(p,rows,t,fine['state'])
    controls=independent(p,rows,t,main['state']);cycles=[]
    for name in ['old','directional','A_receives_more','B_receives_more','shared','no_strain']:
        d=next(x for x in details if x['model']==name and x['condition']==0 and x['start']==0)
        s=next(x for x in summary if x['model']==name and x['condition']==0)
        if s['status']=='autonomous repeat confirmed':
            value=cycle(p,d,d['section_last'],d['mean_period_s']);cycles.append(value);print(json.dumps(value),flush=True)
    g=p['gates'];verification=dict(saved_path_refinement=diff<g['saved_path_difference'],energy_balance=max(float(main['energy_residual']),float(fine['energy_residual']))<g['energy_residual'],classification_refinement=[x['status'] for x in summary]==[x['status'] for x in refined],independent_solver=max(x['error'] for x in controls)<g['independent_error'],cycle_checks=bool(cycles) and all(x['passed'] for x in cycles),finite=bool(np.isfinite(main['state']).all() and np.isfinite(fine['state']).all()),guard_bounds=bool(min(main['guard_range'][0],fine['guard_range'][0])>=-g['guard_bounds'] and max(main['guard_range'][1],fine['guard_range'][1])<=1+g['guard_bounds']))
    for d in details:
        for k in ['section_recent','orbit_recent','section_last']:d.pop(k)
    result=dict(protocol=p,cases=rows,summary=summary,refined_summary=refined,per_start=details,cycles=cycles,independent_controls=controls,verification=verification,numerical_status='passed' if all(verification.values()) else 'failed checks retained',maximum_saved_path_difference=diff,maximum_energy_residual=max(float(main['energy_residual']),float(fine['energy_residual'])),maximum_independent_error=max(x['error'] for x in controls),guard_range=[min(main['guard_range'][0],fine['guard_range'][0]),max(main['guard_range'][1],fine['guard_range'][1])],integration_seconds=[float(main['elapsed_s']),float(fine['elapsed_s'])],source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['model.py','protocol.json','run.py','analyze.py']})
    (ROOT/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(checks=verification,refinement=diff,independent=result['maximum_independent_error'],energy=result['maximum_energy_residual'],summary=summary),indent=2))
if __name__=='__main__':main()
