"""Supplied averaging exercises: cubic velocity damping, pendulum, and swing."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from oscillators import rk4


def floquet(gamma,epsilon=.1,steps=1600):
    gamma=np.asarray(gamma,float);state=np.repeat(np.eye(2)[:,:,None],len(gamma),axis=2);dt=np.pi/steps
    def rhs(m,t):return np.array([m[1],-(1+epsilon*gamma+epsilon*np.cos(2*t))*m[0]])
    for i in range(steps):
        t=i*dt;k1=rhs(state,t);k2=rhs(state+dt*k1/2,t+dt/2);k3=rhs(state+dt*k2/2,t+dt/2);k4=rhs(state+dt*k3,t+dt)
        state+=dt*(k1+2*k2+2*k3+k4)/6
    eigen=np.linalg.eigvals(np.moveaxis(state,-1,0))
    return np.max(np.log(abs(eigen)),axis=1)/np.pi,np.linalg.det(np.moveaxis(state,-1,0))


def main():
    data=Path('data');out=Path('analysis');target=data/'averaging.json'
    if target.exists():raise SystemExit('Refusing to overwrite averaging results.')
    (data/'averaging_protocol.json').write_text(json.dumps(dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
      source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      source='Supplied weak-oscillator exercise continuation, 7.6.15, 7.6.16 and visible 7.6.17(a).',
      cubic_damping='xddot+epsilon*xdot^3+x=0; a1 epsilon2 duration50; dt .01 and .005.',
      pendulum='Periods from exact energy quadrature for amplitudes .1,.3,.6,1; compare 1-a^2/16.',
      swing='epsilon .1, gamma -1..1 in 81 steps; monodromy over coefficient period pi; 1600/3200 RK4 steps; full nonlinear rest and .001 displacement at gamma0 over time120.',
      note='Figure8.1.7 lacks the original equations; explanatory normal forms in the atlas are explicitly illustrative.'),indent=2))
    damping=[];traces=[]
    for dt in (.01,.005):
        state=np.array([1.,0.]);saved=[state.copy()];max_inc=0.
        for _ in range(round(50/dt)):
            before=.5*(state@state);state=rk4(state,dt,lambda z:np.array([z[1],-z[0]-2*z[1]**3]));max_inc=max(max_inc,.5*(state@state)-before);saved.append(state.copy())
        saved=np.array(saved);t=np.arange(len(saved))*dt;approx=np.cos(t)/np.sqrt(1+1.5*t)
        damping.append(dict(dt=dt,maximum_averaging_error=float(abs(saved[:,0]-approx).max()),rms_averaging_error=float(np.sqrt(np.mean((saved[:,0]-approx)**2))),largest_energy_increase=float(max_inc)))
        traces.append(saved)
    psi=np.linspace(0,np.pi/2,100001);periods=[]
    for a in (.1,.3,.6,1.):
        period=4*np.trapezoid(1/np.sqrt(1-np.sin(a/2)**2*np.sin(psi)**2),psi)
        periods.append(dict(amplitude=a,exact_frequency=float(2*np.pi/period),averaged_frequency=1-a*a/16))
    gamma=np.linspace(-1,1,81);rate,det=floquet(gamma);fine,fine_det=floquet(gamma,steps=3200)
    prediction=.1/4*np.sqrt(np.maximum(0,1-4*gamma*gamma));swing=[]
    for initial in (0.,.001):
        state=np.array([initial,0.]);saved=[state.copy()];dt=.01
        def rhs(z,t):return np.array([z[1],-(1+.1*np.cos(2*t))*np.sin(z[0])])
        for i in range(12000):
            t=i*dt;k1=rhs(state,t);k2=rhs(state+dt*k1/2,t+dt/2);k3=rhs(state+dt*k2/2,t+dt/2);k4=rhs(state+dt*k3,t+dt);state+=dt*(k1+2*k2+2*k3+k4)/6;saved.append(state.copy())
        swing.append(np.array(saved))
    checks=dict(cubic_damping_energy_nonincreasing=all(r['largest_energy_increase']<1e-12 for r in damping),
       cubic_damping_step_refinement=float(abs(traces[0]-traces[1][::2]).max())<1e-7,
       pendulum_softening=all(r['exact_frequency']<1 for r in periods),
       floquet_unit_determinant=float(abs(det-1).max())<1e-10,
       floquet_refinement=float(abs(rate-fine).max())<1e-9,
       exact_rest_stays_at_rest=bool(np.array_equal(swing[0],np.zeros_like(swing[0]))),
       small_perturbation_can_grow=float(np.linalg.norm(swing[1][-1]))>.005)
    result=dict(cubic_damping=damping,pendulum=periods,floquet=[dict(gamma=float(g),numeric=float(n),averaged=float(p)) for g,n,p in zip(gamma,rate,prediction)],
       maximum_floquet_step_difference=float(abs(rate-fine).max()),checks=checks,all_passed=all(checks.values()))
    target.write_text(json.dumps(result,indent=2));np.savez_compressed(data/'averaging_trajectories.npz',cubic=traces[0],swing_rest=swing[0],swing_perturbed=swing[1])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,3,figsize=(12,4));time=np.arange(len(traces[0]))*.01
    axs[0].plot(time,traces[0][:,0],label='numerical');axs[0].plot(time,np.cos(time)/np.sqrt(1+1.5*time),'--',label='first-order averaging');axs[0].set(xlabel='Time',ylabel='x',title='Cubic velocity damping: epsilon=2');axs[0].legend(fontsize=8)
    axs[1].plot(gamma,rate,label='Floquet calculation');axs[1].plot(gamma,prediction,'--',label='first-order averaging');axs[1].set(xlabel='Detuning gamma',ylabel='Growth rate in time t',title='Parametric swing: epsilon=0.1');axs[1].legend(fontsize=8)
    time=np.arange(len(swing[1]))*.01;axs[2].plot(time,swing[1][:,0],label='initial displacement .001');axs[2].plot(time,swing[0][:,0],label='exact rest');axs[2].set(xlabel='Time',ylabel='Angle',title='An unstable rest state still needs a perturbation');axs[2].legend(fontsize=8);fig.tight_layout()
    for ext in ('png','svg'):fig.savefig(out/('averaging.'+ext),dpi=150,bbox_inches='tight')
    plt.close(fig);print(json.dumps({k:v for k,v in result.items() if k!='floquet'},indent=2))
    if not result['all_passed']:raise SystemExit(1)


if __name__=='__main__':main()
