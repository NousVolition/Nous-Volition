"""Reproduce mathematical probes from the inspected Miro frames, using the full solver."""
from pathlib import Path
import hashlib,json
import numpy as np
from scipy.optimize import brentq
from scipy.special import expit
from corpus_field import Parameters,Field,activation
from person_field import InputInterval,integrate

ROOT=Path(__file__).resolve().parent
SOLVER_SHA='00b50a93ae413d46109327ccf0c08e8e07d00028313eaa0da87d765e58705f35'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert sha(ROOT/'corpus_field.py')==SOLVER_SHA
    checks=[];runs=[];states={};probes=[];works=[]
    def check(name,ok):
        checks.append(dict(check=name,passed=bool(ok)))
        if not ok:raise AssertionError(name)
    q=np.array([-1.,-.639,0.,.1,1.])
    for law in ['sharp','tanh','smooth_off']:
        vals=activation(q,law,1.)
        probes.append(dict(law=law,q=q.tolist(),activation=vals.tolist()))
        check(law+' zero at onset',vals[2]==0.)
        check(law+' positive above onset',np.all(vals[3:]>0.))
        check(law+' signed below onset',np.all(vals[:2]<0.) if law=='tanh' else np.all(vals[:2]==0.))
        for n in [24,48]:
            p=Parameters(n=n,kappa=.3,law=law);f=Field(p);pair=[];endpoints=[]
            for sign in [1,-1]:
                z,A=f.initial(texture=sign*.04,speed=.1);tr=[];zs=[];aa=[]
                for j,U in enumerate([sign,-sign,0]):
                    event=InputInterval('synthetic-person',j*.2,(j+1)*.2,float(U),'unattributed',f'explicit-input-{j}')
                    z,A,rows=integrate('synthetic-person',[event],p,z,A,j*.2,max_dt=.002,initial_state_basis='declared synthetic initial field and uninterrupted input history')
                    tr.extend(rows);zs.append(z.copy());aa.append(A)
                pair.append((z,A,tr));endpoints.append((np.array(zs),np.array(aa)))
                states[f'{law}_{n}_{"plus" if sign==1 else "minus"}']=np.array(zs)
            plus,minus=endpoints;gplus=f.gradient(pair[0][0][2]);gminus=f.gradient(pair[1][0][2])
            d=dict(law=law,grid=n,
                velocity_max=float(np.max(np.abs(f.real(plus[0][:,:2])-f.real(minus[0][:,:2])))),
                mirrored_S_max=float(np.max(np.abs(f.real(plus[0][:,2])+f.real(minus[0][:,2])))),
                mirrored_A_max=float(np.max(np.abs(plus[1]+minus[1]))),
                gradient_norm_max=float(np.max(np.abs(np.linalg.norm(gplus,axis=0)-np.linalg.norm(gminus,axis=0)))))
            tp=f.terms(pair[0][0],pair[0][1]);tm=f.terms(pair[1][0],pair[1][1])
            d['pressure_max']=float(np.max(np.abs(f.real(tp[1])-f.real(tm[1]))))
            d['force_max']=float(np.max(np.abs(tp[4]-tm[4])))
            for key in ['velocity_max','mirrored_S_max','mirrored_A_max','gradient_norm_max','pressure_max','force_max']:
                check(f'{law} n={n} {key}',d[key]<1e-11)
            rows=pair[0][2]+pair[1][2]
            for key in ['mass_error','energy_identity_residual','divergence_rms']:
                d['max_'+key]=max(abs(t[key]) for t in rows)
                check(f'{law} n={n} {key}',d['max_'+key]<1e-12)
            d['endpoint_diagnostics']=[x[2] for x in pair];runs.append(d)
        f=Field(Parameters(law=law));z,_=f.initial(texture=.04,speed=0)
        z[:2]=f.fft(np.stack([np.ones((f.p.n,f.p.n)),np.zeros((f.p.n,f.p.n))]))
        wplus=f.diagnostics(z,0)['work'];z[:2]*=-1;wminus=f.diagnostics(z,0)['work']
        works.append(dict(law=law,velocity_plus_e_work=wplus,velocity_minus_e_work=wminus))
        check(law+' force is not automatic drag',wplus<0<wminus and abs(wplus+wminus)<1e-13)
    zmin=brentq(lambda z:1+2*z*(1-expit(2*z)),-1.,-.1,xtol=1e-14)
    minimum=float(activation(np.array([zmin]),'tanh',1)[0])
    check('tanh minimum position matches board rounding',abs(zmin+.639232)<5e-7)
    check('tanh minimum value matches board rounding',abs(minimum+.139232)<5e-7)
    logtiny=float(np.log(.01)-1/.01**2);floatvalue=float(activation(np.array([.01]),'smooth_off',1)[0])
    check('positive exact-off branch can underflow',floatvalue==0. and np.isfinite(logtiny) and logtiny<np.log(np.nextafter(0.,1.)))
    out=dict(scope='12 synthetic full coupled runs and mathematical response probes; not a fit to people',empirical_fit=False,substitute_predictor=False,solver_sha256=SOLVER_SHA,plan_sha256=sha(ROOT/'MIRO_TEST_PLAN.md'),coupled_runs=12,probes=probes,tanh_minimum=dict(q_over_epsilon=zmin,a_over_epsilon=minimum),positive_underflow=dict(q=.01,epsilon=1.,log_activation=logtiny,float64_activation=floatvalue,mathematically_positive=True),runs=runs,energy_work=works,checks=checks,check_count=len(checks),passed=all(x['passed'] for x in checks))
    np.savez_compressed(ROOT/'results/miro_states.npz',**states)
    (ROOT/'results/miro_checks.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:out[k] for k in ['coupled_runs','check_count','passed','tanh_minimum','positive_underflow']}))
if __name__=='__main__':main()
