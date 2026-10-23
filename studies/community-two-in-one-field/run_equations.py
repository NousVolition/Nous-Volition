"""Full coupled PDE verification, explicitly synthetic dimensionless inputs."""
from dataclasses import asdict,replace
import hashlib,json,time
from pathlib import Path
import numpy as np
from corpus_field import Field,Parameters

ROOT=Path(__file__).resolve().parent;R=ROOT/'results'

def difference(a,b):
    """Parseval L2, retaining fine-only modes; normalization is domain mean."""
    na=a.shape[-1];nb=b.shape[-1]
    if na>nb:raise ValueError('fine grid must be second')
    m=np.rint(np.fft.fftfreq(na)*na).astype(int);idx=m%nb
    delta=b.copy()/nb**2
    delta[:,idx[:,None],idx[None,:]]-=a/na**2
    return float(np.sqrt(np.sum(np.abs(delta)**2)))

def main():
    R.mkdir(exist_ok=True);start=time.perf_counter()
    solver_sha=hashlib.sha256((ROOT/'corpus_field.py').read_bytes()).hexdigest()
    assert solver_sha=='00b50a93ae413d46109327ccf0c08e8e07d00028313eaa0da87d765e58705f35'
    base=Parameters(kappa=.3);inputs=[1.,-.5,0.];runs={};states={};refine=[];invariant=[]
    def run(name,p,dt=.002):
        f=Field(p);rows,z,s=f.run(inputs,dt=dt,interval=.2,keep=True)
        runs[name]=dict(parameters=asdict(p),requested_dt=dt,rows=rows)
        states[name]=z
        print('completed',name,flush=True)
        return f,rows,z,s
    for law in ['sharp','tanh','smooth_off']:
        p=replace(base,law=law)
        for n in [24,48,72]:run(f'{law}_{n}',replace(p,n=n))
        run(f'{law}_half_dt',p,.001)
        _,r0,z0,_=run(f'{law}_scaled_memory',replace(p,gamma=4.,kappa=.075))
        z=states[f'{law}_24'];f=Field(p);a=runs[f'{law}_24']['rows'][-1]['A']
        pa=f.real(f.terms(z,a)[1]);pb=Field(replace(p,gamma=4.,kappa=.075)).real(f.terms(z0,r0[-1]['A'])[1])
        invariant.append(dict(law=law,gamma_scale=4.,state_L2=difference(z,z0),pressure_rms_difference=float(np.sqrt(np.mean((pa-pb)**2))),A_ratio=r0[-1]['A']/a))
        refine.append(dict(law=law,grid24_48=difference(states[f'{law}_24'],states[f'{law}_48']),grid48_72=difference(states[f'{law}_48'],states[f'{law}_72']),time_dt_half=difference(states[f'{law}_24'],states[f'{law}_half_dt'])))
    run('no_force',replace(base,sigma=0.))
    run('no_source',replace(base,kappa=0.))
    run('different_spatial_parameters',replace(base,sigma=.3,diffusivity=.04))
    f=Field(base);z1=states['sharp_24'];z2=states['different_spatial_parameters']
    mass_demo=dict(mean_S_difference=float(abs(z1[2,0,0]-z2[2,0,0])/24**2),spatial_S_rms_difference=float(np.sqrt(np.mean((f.real(z1[2])-f.real(z2[2]))**2))),velocity_rms_difference=float(np.sqrt(np.mean((f.real(z1[:2])-f.real(z2[:2]))**2))))
    # Analytic checks have deliberately inactive terms; only these are special cases.
    ft=Field(replace(base,sigma=0.,kappa=0.));rr,zt,_=ft.run([0.],interval=.2,texture=0.,dt=.002)
    zi,_=ft.initial(texture=0.);exact=ft.real(zi[:2])*np.exp(-8*np.pi**2*base.nu*.2)
    analytic=dict(taylor_green_velocity_max_error=float(np.max(abs(ft.real(zt[:2])-exact))))
    fp=Field(replace(base,sigma=0.,kappa=0.));zp,ap=fp.initial(texture=0.,speed=0.)
    zp[0,0,0]=24**2*.2;zp[2]=fp.fft(np.sin(2*np.pi*fp.x))
    for _ in range(100):zp,ap=fp.step(zp,ap,0.,.001)
    exact=np.exp(-base.diffusivity*4*np.pi**2*.1)*np.sin(2*np.pi*(fp.x-.2*.1))
    analytic['advected_diffusing_scalar_max_error']=float(np.max(abs(fp.real(zp[2])-exact)))
    allrows=[r for v in runs.values() for r in v['rows']]
    s=dict(solver_sha256=solver_sha,protocol_sha256=hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest(),
        experiment_type='synthetic dimensionless numerical verification; no human fit',inputs=inputs,interval=.2,runs=runs,refinement=refine,
        gamma_kappa_invariance=invariant,global_mean_nonidentification=mass_demo,analytic_checks=analytic,
        completed_coupled_runs=len(runs),completed_analytic_runs=2,
        max_mass_error=max(abs(r['mass_error']) for r in allrows),max_divergence=max(r['divergence_rms'] for r in allrows),
        max_energy_identity_residual=max(abs(r['energy_identity_residual']) for r in allrows),elapsed_seconds=time.perf_counter()-start)
    (R/'equation_results.json').write_text(json.dumps(s,indent=2)+'\n')
    np.savez_compressed(R/'final_fields.npz',**states)
    print(json.dumps({k:v for k,v in s.items() if k!='runs'},indent=2))

if __name__=='__main__':main()
