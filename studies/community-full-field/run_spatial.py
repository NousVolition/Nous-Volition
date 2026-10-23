from dataclasses import replace,asdict
from pathlib import Path
import json,time
import numpy as np
from field import Field,Parameters

HERE=Path(__file__).parent;R=HERE/'results';R.mkdir(exist_ok=True)

def l2_low_difference(a,b):
    """Parseval norm of all component differences, including fine-only modes."""
    na=a.shape[-1];nb=b.shape[-1];m=np.rint(np.fft.fftfreq(na)*na).astype(int);idx=m%nb
    if nb<na:raise ValueError('Second array must be at least as fine')
    delta=b.copy()/nb**2;delta[:,idx[:,None],idx[None,:]]-=a/na**2
    return float(np.sqrt(np.sum(abs(delta)**2)))

def benchmarks():
    out={};times=[]
    # One step Richardson-style comparison to an analytic low-mode solution.
    for dt in [.1,.05,.025]:
        f=Field(Parameters(n=12,nu=.002,sigma=0.,kappa=0.));z,A=f.initial(texture=0.,speed=.3)
        for _ in range(round(.2/dt)):z,A=f.step(z,A,0.,dt)
        z0,_=f.initial(texture=0.,speed=.3);exact=f.real(z0[:2])*np.exp(-8*np.pi**2*.002*.2)
        times.append(dict(dt=dt,velocity_rms_error=float(np.sqrt(np.mean((f.real(z[:2])-exact)**2)))))
    out['taylor_green_time']=times
    f=Field(Parameters(n=24,sigma=0.,kappa=0.));r,z,_=f.run([0.],interval=1.,texture=0.)
    z0,_=f.initial(texture=0.);_,ph,_,_,_=f.terms(z,0.)
    pexact=.1**2/4*(np.cos(4*np.pi*f.x)+np.cos(4*np.pi*f.y))*np.exp(-16*np.pi**2*.02)
    out['taylor_green']=dict(velocity_rms_error=float(np.sqrt(np.mean((f.real(z[:2])-f.real(z0[:2])*np.exp(-8*np.pi**2*.02))**2))),pressure_rms_error=float(np.sqrt(np.mean((f.real(ph)-pexact)**2))),**r[-1])
    return out

def main():
    start=time.perf_counter();fit=json.loads((R/'data_results.json').read_text())['parameters'];pilots=json.loads((R/'pilot_selection.json').read_text())
    base=Parameters(kappa=fit['kappa'],baseline=fit['baseline']);allrows=[];finals={};saved={}
    for i,s in enumerate(pilots):
        settings=[('sharp24',base,.004,.04),('sharp48',replace(base,n=48),.002,.04),('sharp72',replace(base,n=72),.001,.04),
                  ('tanh24',replace(base,law='tanh'),.004,.04),('smooth_off24',replace(base,law='smooth_off'),.004,.04),
                  ('no_force24',replace(base,sigma=0.),.004,.04),('no_source24',replace(base,kappa=0.),.004,.04),
                  ('uniform_S24',base,.004,0.),('sharp24_half_dt',base,.002,.04)]
        for name,p,dt,texture in settings:
            print('RUN',i,name,flush=True);f=Field(p);rows,z,states=f.run(s['y'][:4],initial_total=s['y'][0],dt=dt,texture=texture,keep=name=='sharp48')
            for r in rows:allrows.append(dict(pilot=i,sequence=s['sequence'],run=name,**r))
            finals[i,name]=z
            if name in ['sharp48','tanh24','no_force24','uniform_S24']:
                saved[f'p{i}_{name}']=f.real(z);saved[f'p{i}_{name}_pressure']=f.real(f.terms(z,rows[-1]['A'])[1])
            if name=='sharp48':saved[f'p{i}_snapshots']=np.array(states)
    refinement=[]
    for i in range(len(pilots)):
        refinement.append(dict(pilot=i,n24_vs_n48=l2_low_difference(finals[i,'sharp24'],finals[i,'sharp48']),n48_vs_n72=l2_low_difference(finals[i,'sharp48'],finals[i,'sharp72']),n24_dt_vs_half=l2_low_difference(finals[i,'sharp24'],finals[i,'sharp24_half_dt'])))
    b=benchmarks();ident=[]
    for i in range(len(pilots)):
        z=finals[i,'sharp24']
        for name in ['tanh24','smooth_off24','no_force24','uniform_S24']:
            w=finals[i,name];f=Field(base)
            ident.append(dict(pilot=i,comparison=name,mean_S_difference=float(abs((z[2,0,0]-w[2,0,0])/base.n**2)),spatial_S_rms_difference=float(np.sqrt(np.mean((f.real(z[2])-f.real(w[2]))**2))),velocity_rms_difference=float(np.sqrt(np.mean((f.real(z[:2])-f.real(w[:2]))**2)))))
    result=dict(parameters=asdict(base),runs=18,pilot_records=allrows,refinement=refinement,identifiability_examples=ident,benchmarks=b,elapsed_seconds=time.perf_counter()-start,
                max_mass_error=max(abs(r['mass_error']) for r in allrows),max_divergence=max(r['divergence_rms'] for r in allrows),max_energy_identity_residual=max(abs(r['energy_identity_residual']) for r in allrows))
    (R/'spatial_results.json').write_text(json.dumps(result,indent=2)+'\n')
    np.savez_compressed(R/'fields.npz',**saved)
    np.savez_compressed(R/'final_coefficients.npz',**{f'p{i}_{name}':z for (i,name),z in finals.items()})
    print(json.dumps({k:result[k] for k in ['runs','refinement','max_mass_error','max_divergence','max_energy_identity_residual','elapsed_seconds','benchmarks']},indent=2))
if __name__=='__main__':main()
