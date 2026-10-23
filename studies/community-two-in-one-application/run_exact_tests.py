"""New coupled tests; all inputs synthetic, never presented as participant data."""
from pathlib import Path
from dataclasses import replace,asdict
import json,hashlib,time
import numpy as np
from scipy.signal import resample
from corpus_field import Field,Parameters
from person_field import InputInterval,integrate
ROOT=Path(__file__).resolve().parent

def rms(x):return float(np.sqrt(np.mean(np.abs(x)**2)))
def compare(z1,z2):
    a=np.fft.ifft2(z1,axes=(-2,-1)).real;b=np.fft.ifft2(z2,axes=(-2,-1)).real
    if a.shape!=b.shape:a=resample(resample(a,b.shape[-2],axis=-2),b.shape[-1],axis=-1)
    return dict(state_rms=rms(a-b),S_rms=rms(a[2]-b[2]),u_rms=rms(a[:2]-b[:2]))

def run(p,values,texture=.04,roles=None,A0=0.,max_dt=.002):
    f=Field(p);z,_=f.initial(texture=texture,speed=.1)
    roles=roles or ['unattributed']*len(values)
    intervals=[InputInterval('synthetic-person',j*.2,(j+1)*.2,float(U),roles[j],f'declared-input-{j}') for j,U in enumerate(values)]
    return integrate('synthetic-person',intervals,p,z,A0,0.,max_dt,'synthetic initial state, not a measured biography')

def main():
    started=time.time();out=ROOT/'results';out.mkdir(exist_ok=True)
    p=Parameters(n=24,kappa=.3);states={};results=[];run_count=0
    for law in ['sharp','tanh','smooth_off']:
        pp=replace(p,law=law);f=Field(pp)
        z,A,rows=run(pp,[1,-1,0]);run_count+=1;states[law+'_history']=z
        rev,Ar,rr=run(pp,[-1,1,0]);run_count+=1;states[law+'_reversed']=rev
        one,A1,r1=run(pp,[1,-1,0],roles=['Smoke','Clay','both']);run_count+=1
        two,A2,r2=run(pp,[1,-1,0],roles=['Clay','Smoke','both']);run_count+=1
        c=2.;ps=replace(pp,threshold=c*pp.threshold,epsilon=c*pp.epsilon,kappa=c*pp.kappa,sigma=pp.sigma/c)
        scaled,As,rs=run(ps,[1,-1,0],texture=c*.04);run_count+=1;states[law+'_rescaled']=scaled
        norm=scaled.copy();norm[2]/=c
        pressure=f.terms(z,A)[1];pscaled=Field(ps).terms(scaled,As)[1]
        plus,Ap,rp=run(pp,[1,-1,0],texture=.0404);minus,Am,rm=run(pp,[1,-1,0],texture=.0396);run_count+=2
        states[law+'_plus1pct']=plus;states[law+'_minus1pct']=minus
        hi,Ah,rh=run(pp,[0],A0=.1);lo,Al,rl=run(pp,[0],A0=-.1);run_count+=2
        states[law+'_prior_plus']=hi;states[law+'_prior_minus']=lo
        fine,Af,rf=run(replace(pp,n=48),[1,-1,0]);run_count+=1;states[law+'_grid48']=fine
        finer,Aff,rff=run(replace(pp,n=72),[1,-1,0]);run_count+=1;states[law+'_grid72']=finer
        half,At,rt=run(pp,[1,-1,0],max_dt=.001);run_count+=1;states[law+'_halfdt']=half
        diagrows=rows+rr+r1+r2+rs+rp+rm+rh+rl+rf+rff+rt
        results.append(dict(law=law,parameters=asdict(pp),history_comparison=compare(z,rev),history_A=[A,Ar],history_final_mass=[rows[-1]['mass'],rr[-1]['mass']],role_relabel_difference=compare(one,two),state_rescaling=compare(z,norm),rescaled_pressure_max=float(np.max(np.abs(pressure-pscaled)))/pp.n**2,perturbation_comparison=compare(plus,minus),perturbation_input_S_rms=.0004,unknown_prior_comparison=compare(hi,lo),unknown_prior_final_mass=[rh[-1]['mass'],rl[-1]['mass']],grid24_48=compare(z,fine),grid48_72=compare(fine,finer),time_refinement=compare(z,half),max_mass_error=max(abs(r['mass_error']) for r in diagrows),max_divergence=max(r['divergence_rms'] for r in diagrows),max_energy_identity=max(abs(r['energy_identity_residual']) for r in diagrows),rows=rows))
        print(law,'complete',flush=True)
    # Analytic pure diffusion and Taylor-Green checks use the same full solver.
    pp=Parameters(n=24,sigma=0,kappa=0);f=Field(pp);z,_=f.initial(texture=0,speed=.1)
    vel,A,rows=integrate('analytic',[InputInterval('analytic',0,.2,0,'unattributed','analytic')],pp,z,0,0,initial_state_basis='analytic exact state')
    expected=f.real(z[:2])*np.exp(-pp.nu*8*np.pi**2*.2)
    analytic_error=float(np.max(abs(f.real(vel[:2])-expected)))
    np.savez_compressed(out/'states.npz',**states)
    result=dict(coupled_runs=run_count,analytic_runs=1,analytic_taylor_green_max_error=analytic_error,synthetic_inputs=True,empirical_model_fit=False,runs=results,seconds=time.time()-started,solver_sha256=hashlib.sha256((ROOT/'corpus_field.py').read_bytes()).hexdigest(),protocol_sha256=hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest(),numerical_plan_sha256=hashlib.sha256((ROOT/'NUMERICAL_PLAN.md').read_bytes()).hexdigest())
    (out/'equation_results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(runs=run_count,seconds=result['seconds'],analytic_error=analytic_error)))
if __name__=='__main__':main()
