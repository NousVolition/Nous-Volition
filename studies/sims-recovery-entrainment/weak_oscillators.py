"""Supplied weak Van der Pol and conservative Duffing equations."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from oscillators import rk4


def duffing(amplitudes,epsilon=.1,dt=.02,duration=200):
    amplitudes=np.array(amplitudes,float);z=np.array([amplitudes,np.zeros_like(amplitudes)])
    e0=.5*amplitudes**2+.25*epsilon*amplitudes**4;maximum=np.zeros_like(amplitudes)
    crossings=[[] for _ in amplitudes];trace=[]
    for step in range(round(duration/dt)):
        before=z.copy();z=rk4(z,dt,lambda q:np.array([q[1],-q[0]-epsilon*q[0]**3]))
        energy=.5*z[1]**2+.5*z[0]**2+.25*epsilon*z[0]**4;maximum=np.maximum(maximum,abs(energy-e0))
        for j in np.flatnonzero((before[0]>0)&(z[0]<=0)):
            crossings[j].append(step*dt+dt*before[0,j]/(before[0,j]-z[0,j]))
        if (step+1)%round(.2/dt)==0:trace.append(z.copy())
    psi=np.linspace(0,np.pi/2,50001)
    exact=np.array([4*np.trapezoid(1/np.sqrt(1+.5*epsilon*a*a*(1+np.sin(psi)**2)),psi) for a in amplitudes])
    return [dict(amplitude=float(a),dt=dt,measured_period=float(np.mean(np.diff(times))),quadrature_period=float(t),
                 first_order_frequency=float(1+3*epsilon*a*a/8),energy_error=float(err)) for a,times,t,err in zip(amplitudes,crossings,exact,maximum)],np.array(trace)


def main():
    data=Path('data');out=Path('analysis');target=data/'weak_oscillators.json'
    if target.exists():raise SystemExit('Refusing to overwrite weak-oscillator results.')
    (data/'weak_oscillators_protocol.json').write_text(json.dumps(dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
      source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      source='Supplied weakly nonlinear oscillator equations and Figure 7.6.1.',
      van_der_pol=dict(epsilon=[.05,.1,.2],initial_amplitude=[.1,1,3],velocity=0,duration=600,dt=.02),
      duffing=dict(epsilon=.1,amplitude=[.2,1,2],velocity=0,duration=200,dt=[.02,.01]),
      scope='Later standalone mathematical addendum, not a parameter fit to SIMS.'),indent=2))
    cases=[(e,a) for e in (.05,.1,.2) for a in (.1,1,3)];eps=np.array([c[0] for c in cases]);amplitudes=np.array([c[1] for c in cases])
    z=np.array([amplitudes,np.zeros(9)]);trace=[];time=[];maximum=np.full(9,-np.inf);minimum=np.full(9,np.inf)
    for step in range(30000):
        z=rk4(z,.02,lambda q:np.array([q[1],-q[0]-eps*(q[0]**2-1)*q[1]]))
        if step>=20000:maximum=np.maximum(maximum,z[0]);minimum=np.minimum(minimum,z[0])
        if (step+1)%10==0:trace.append(z.copy());time.append((step+1)*.02)
    rows=[dict(epsilon=e,initial_amplitude=a,late_half_range=float((hi-lo)/2)) for (e,a),hi,lo in zip(cases,maximum,minimum)]
    coarse,dtrace=duffing([.2,1,2]);fine,_=duffing([.2,1,2],dt=.01)
    checks=dict(vdp_amplitude_near_two=all(abs(r['late_half_range']-2)<.02 for r in rows),
      vdp_initial_conditions_agree=all(np.ptp([r['late_half_range'] for r in rows if r['epsilon']==e])<.002 for e in (.05,.1,.2)),
      duffing_periods_match_quadrature=all(abs(r['measured_period']/r['quadrature_period']-1)<1e-6 for r in coarse+fine),
      duffing_energy_error=all(r['energy_error']<1e-5 for r in coarse+fine),
      duffing_hardening=coarse[0]['measured_period']>coarse[1]['measured_period']>coarse[2]['measured_period'])
    result=dict(van_der_pol=rows,duffing=coarse,duffing_refined=fine,checks=checks,all_passed=all(checks.values()))
    target.write_text(json.dumps(result,indent=2));np.savez_compressed(data/'weak_trajectories.npz',time=time,van_der_pol=trace,duffing=dtrace)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    trace=np.array(trace);fig,axs=plt.subplots(1,3,figsize=(12,4))
    for j in (3,4,5):
        axs[0].plot(trace[:,0,j],trace[:,1,j],lw=.7,label=f'initial {cases[j][1]:g}')
        axs[1].plot(time,np.sqrt((trace[:,:,j]**2).sum(1)),lw=.8)
    axs[0].set(xlabel='x',ylabel='velocity',title='Van der Pol: inside and outside approach a cycle');axs[0].legend(fontsize=8)
    axs[1].axhline(2,color='#777',ls=':');axs[1].set(xlabel='Time',ylabel='Phase-plane radius',title='epsilon=0.1; averaged stable radius ≈2')
    for j in range(3):axs[2].plot(dtrace[:,0,j],dtrace[:,1,j],label=f'amplitude {coarse[j]["amplitude"]:g}')
    axs[2].set(xlabel='x',ylabel='velocity',title='Duffing: separate conserved-energy curves');axs[2].legend(fontsize=8);fig.tight_layout()
    for ext in ('png','svg'):fig.savefig(out/('weak_oscillators.'+ext),dpi=150,bbox_inches='tight')
    plt.close(fig);print(json.dumps(result,indent=2))
    if not result['all_passed']:raise SystemExit(1)


if __name__=='__main__':main()
