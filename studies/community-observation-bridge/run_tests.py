"""Full coupled PDE compatibility/identifiability experiment, not a prediction fit."""
from pathlib import Path
import json,hashlib,time
from itertools import combinations
import numpy as np
from corpus_field import Field,Parameters
from observer import setup,readout,compatible
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def trial(law,distance,A0,n=24,max_dt=.004,kappa=1.,sigma=.1,keep=False):
    f=Field(Parameters(n=n,law=law,kappa=kappa,sigma=sigma))
    z,w=setup(f,distance);initial=readout(f,z,A0,w);A=float(A0)
    mass0=float(f.real(z[2]).mean());samples=[];maxmass=maxdiv=maxenergy=0.
    cap=.45/(max(f.p.nu,f.p.diffusivity)*float(f.k2[f.mask].max()))
    steps=int(np.ceil(.1/min(max_dt,cap)));dt=.1/steps
    for j in range(10):
        for _ in range(steps):z,A=f.step(z,A,0.,dt)
        if not np.isfinite(z).all():raise FloatingPointError('nonfinite state')
        t=(j+1)*.1;diag=f.diagnostics(z,A);mass_expected=mass0+kappa*A0*t
        maxmass=max(maxmass,abs(diag['mass']-mass_expected))
        maxdiv=max(maxdiv,abs(diag['divergence_rms']))
        maxenergy=max(maxenergy,abs(diag['energy_identity_residual']))
        samples.append(dict(t=t,**readout(f,z,A,w),**diag,mass_expected=mass_expected))
    result=dict(law=law,distance=distance,A0=A0,n=n,dt=dt,steps=10*steps,kappa=kappa,sigma=sigma,
        initial=initial,compatible=compatible(initial),final=samples[-1],trace=samples,
        mass_error_max=maxmass,divergence_max=maxdiv,energy_residual_max=maxenergy)
    return result,f.real(z) if keep else None

def main():
    t0=time.time();runs=[];finalstates=[]
    for law in ['sharp','tanh','smooth_off']:
        for d in [.15,.25,.35]:
            for A in [-.05,-.02,-.005,0.,.005,.02,.05]:
                r,z=trial(law,d,A,keep=True);r['index']=len(runs);runs.append(r);finalstates.append(z)
        print(json.dumps(dict(completed_law=law,runs=len(runs),seconds=round(time.time()-t0,1))),flush=True)
    witnesses=[]
    for law in ['sharp','tanh','smooth_off']:
        for d in [.15,.25,.35]:
            group=[r for r in runs if r['law']==law and r['distance']==d and r['compatible']]
            for a,b in combinations(group,2):
                if a['final']['contrast']*b['final']['contrast']<0 and min(abs(a['final']['contrast']),abs(b['final']['contrast']))>1e-4:
                    witnesses.append(dict(law=law,distance=d,indices=[a['index'],b['index']],A0=[a['A0'],b['A0']],
                        initial_c_max_difference=max(abs(a['initial'][k]-b['initial'][k]) for k in ['c_P','c_F']),
                        final_contrasts=[a['final']['contrast'],b['final']['contrast']]))
    refinements=[];controls=[];refstates={}
    if witnesses:
        selected=witnesses[0]
        for A in selected['A0']:
            for n,dt in [(48,.004),(72,.004),(48,.002)]:
                r,z=trial(selected['law'],selected['distance'],A,n,dt,keep=True);refinements.append(r)
                r['refinement_label']='nominal_halving_duplicate' if n==48 and dt==.002 else 'grid_refinement'
                refstates[f'A{A}_n{n}_dt{dt}']=z
            # Preserve the ineffective nominal halving above, then halve the actual step.
            base=next(r for r in refinements if r['A0']==A and r['n']==48)
            r,z=trial(selected['law'],selected['distance'],A,48,base['dt']/2,keep=True)
            r['refinement_label']='effective_half_step';refinements.append(r)
            refstates[f'A{A}_n48_effective_half']=z
            for name,k,s in [('no_source',0.,.1),('no_force',1.,0.)]:
                r,_=trial(selected['law'],selected['distance'],A,kappa=k,sigma=s);r['control']=name;controls.append(r)
    out=dict(protocol_sha256=sha(ROOT/'PROTOCOL.md'),solver_sha256=sha(ROOT/'corpus_field.py'),
        observation_operator_sha256=sha(ROOT/'observer.py'),numerical_amendment_sha256=sha(ROOT/'NUMERICAL_AMENDMENT.md'),empirical_prediction_score=None,
        experiment='Real-report-derived qualitative compatibility constraints; unmeasured histories and numerical scales',
        runs=runs,witnesses=witnesses,selected_witness=witnesses[0] if witnesses else None,
        refinements=refinements,controls=controls,elapsed_seconds=time.time()-t0)
    (ROOT/'results').mkdir(exist_ok=True)
    (ROOT/'results/results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    np.savez_compressed(ROOT/'results/states.npz',search=np.array(finalstates),**refstates)
    print(json.dumps(dict(runs=len(runs),compatible=sum(r['compatible'] for r in runs),witnesses=len(witnesses),selected=out['selected_witness'],refinements=len(refinements),controls=len(controls),seconds=time.time()-t0)),flush=True)
if __name__=='__main__':main()
