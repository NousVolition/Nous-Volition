"""Worked supplementary equations from the subsequently supplied exercise crops."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from oscillators import rk4


def hypercycle(x):
    previous=np.roll(x,1,axis=-1);q=(x*previous).sum(axis=-1,keepdims=True)
    return x*(previous-q)


def three_group(z,r):
    x,y,center=z
    return np.array([r*x*center,r*y*center,-r*(x+y)*center])


def integrate(rhs,initial,dt,duration,stride=1):
    z=np.array(initial,float);saved=[z.copy()]
    for step in range(round(duration/dt)):
        z=rk4(z,dt,rhs)
        if (step+1)%stride==0:saved.append(z.copy())
    return np.array(saved)


def main():
    data=Path('data');out=Path('analysis');target=data/'structural.json'
    if target.exists():raise SystemExit('Refusing to overwrite supplementary results.')
    protocol=dict(frozen_utc=datetime.now(timezone.utc).isoformat(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      status='Later supplied exercise addendum; explicit numerical examples, no fitted populations or materials.',
      hypercycle=dict(n=[2,3,4,5,6],seeds=[501,502,503],dt=.02,duration=300,initial='independent Dirichlet(2,...,2), positive simplex'),
      three_group=dict(initial=[.2,.3,.5],r=[-1,0,1],duration=12,dt=.01),
      gravity=dict(G=1,d=1,m1=1,m2=4,initial_offset=[-1e-5,1e-5],duration=.3,dt=.0005),
      hamiltonian=dict(sho='m=2,k=3,x0=1,p0=0; duration20',inverse='h=k=1,r0=1.2,p0=0; duration40',dt=[.02,.01]),
      predator_prey=dict(mu=[.5,1,2],initial=[.7,1.6],duration=40,dt=.01),
      pending='Final heteroclinic crop omits governing equations. No vector field is inferred from its stated saddle positions.')
    (data/'structural_protocol.json').write_text(json.dumps(protocol,indent=2))
    checks={};summary={};arrays={}
    hyper=[]
    for n in (2,3,4,5,6):
        initial=np.array([np.random.default_rng(s).dirichlet(np.full(n,2.)) for s in (501,502,503)])
        series=integrate(hypercycle,initial,.02,300,50);arrays[f'hypercycle_{n}']=series
        eig=np.exp(-2j*np.pi*np.arange(1,n)/n)/n
        # Independently differentiate on the simplex using x_n=1-sum(x_1..x_{n-1}).
        center=np.full(n,1/n);jac=np.zeros((n-1,n-1));eps=1e-6
        for j in range(n-1):
            direction=np.zeros(n);direction[j]=eps;direction[-1]=-eps
            jac[:,j]=(hypercycle(center+direction)[:n-1]-hypercycle(center-direction)[:n-1])/(2*eps)
        numerical=np.linalg.eigvals(jac);error=max(min(abs(v-eig)) for v in numerical)
        hyper.append(dict(n=n,tangent_eigenvalues=[[float(v.real),float(v.imag)] for v in eig],jacobian_error=float(error),
          max_simplex_error=float(abs(series.sum(-1)-1).max()),minimum_component=float(series.min()),
          initial_distance=np.linalg.norm(series[0]-1/n,axis=-1).tolist(),final_distance=np.linalg.norm(series[-1]-1/n,axis=-1).tolist()))
    checks['hypercycle_simplex_and_positivity']=all(r['max_simplex_error']<1e-12 and r['minimum_component']>=0 for r in hyper)
    checks['hypercycle_tangent_spectrum']=all(r['jacobian_error']<1e-8 for r in hyper);summary['hypercycle']=hyper
    time=np.arange(1201)*.01;groups=[]
    for r in (-1,0,1):
        series=integrate(lambda z:three_group(z,r),[.2,.3,.5],.01,12);s=1/(1+np.exp(-r*time))
        exact=np.column_stack([.4*s,.6*s,1-s]);arrays[f'three_group_{r}']=series
        groups.append(dict(r=r,max_solution_error=float(abs(series-exact).max()),max_simplex_error=float(abs(series.sum(1)-1).max()),
                           max_ratio_error=float(abs(series[:,0]/series[:,1]-2/3).max()),final=series[-1].tolist()))
    checks['three_group_exact_solution']=all(r['max_solution_error']<1e-9 and r['max_ratio_error']<1e-12 for r in groups);summary['three_group']=groups
    force=lambda x:4/(1-x)**2-1/x**2
    equilibrium=1/3;derivative=2*4/(1-equilibrium)**3+2/equilibrium**3
    gravity=[]
    for offset in (-1e-5,1e-5):
        series=integrate(lambda z:np.array([z[1],force(z[0])]),[equilibrium+offset,0],.0005,.3)
        linear=offset*np.cosh(np.sqrt(derivative)*np.arange(len(series))*.0005)
        gravity.append(dict(offset=offset,final_offset=float(series[-1,0]-equilibrium),linear_final=float(linear[-1]),
                            maximum_linear_error=float(abs(series[:,0]-equilibrium-linear).max())))
    checks['gravity_unstable_equilibrium']=abs(force(equilibrium))<1e-12 and derivative>0 and all(abs(r['final_offset'])>abs(r['offset']) for r in gravity)
    summary['gravity']=dict(equilibrium=equilibrium,force_derivative=derivative,eigenvalues=[-np.sqrt(derivative),np.sqrt(derivative)],runs=gravity)
    mechanical=[]
    for dt in (.02,.01):
        sho=integrate(lambda z:np.array([z[1]/2,-3*z[0]]),[1,0],dt,20)
        omega=np.sqrt(3/2);tt=np.arange(len(sho))*dt;exact=np.column_stack([np.cos(omega*tt),-2*omega*np.sin(omega*tt)])
        h=.25*sho[:,1]**2+1.5*sho[:,0]**2
        inv=integrate(lambda z:np.array([z[1],1/z[0]**3-1/z[0]**2]),[1.2,0],dt,40)
        hi=.5*inv[:,1]**2+.5/inv[:,0]**2-1/inv[:,0]
        mechanical.append(dict(dt=dt,sho_energy_error=float(abs(h-h[0]).max()),sho_state_error=float(abs(sho-exact).max()),inverse_energy_error=float(abs(hi-hi[0]).max())))
        if dt==.01:arrays['sho']=sho;arrays['inverse_square']=inv
    checks['hamiltonian_conservation']=all(r['sho_energy_error']<1e-7 and r['inverse_energy_error']<1e-8 for r in mechanical)
    checks['hamiltonian_refinement']=mechanical[1]['sho_state_error']<mechanical[0]['sho_state_error'];summary['hamiltonian']=mechanical
    predator=[]
    for mu in (.5,1,2):
        series=integrate(lambda z:np.array([z[0]*(1-z[1]),mu*z[1]*(z[0]-1)]),[.7,1.6],.01,40)
        h=mu*(series[:,0]-np.log(series[:,0]))+series[:,1]-np.log(series[:,1])
        arrays[f'predator_{mu:g}']=series
        predator.append(dict(mu=mu,minimum_population=float(series.min()),invariant_error=float(abs(h-h[0]).max())))
    checks['predator_prey_invariant']=all(r['minimum_population']>0 and r['invariant_error']<1e-7 for r in predator);summary['predator_prey']=predator
    summary.update(checks=checks,all_passed=all(checks.values()));target.write_text(json.dumps(summary,indent=2));np.savez_compressed(data/'structural_trajectories.npz',**arrays)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    def save(fig,name):
        fig.tight_layout()
        for ext in ('png','svg'):fig.savefig(out/(name+'.'+ext),dpi=150,bbox_inches='tight')
        plt.close(fig)
    fig,axs=plt.subplots(2,2,figsize=(11,6),sharex=True)
    for ax,n in zip(axs.ravel(),(3,4,5,6)):
        series=arrays[f'hypercycle_{n}'];ax.plot(np.arange(len(series)),series[:,0,:]);ax.set_title(f'Hypercycle n={n} · one of three initial conditions');ax.set_ylabel('Fraction');ax.set_xlabel('Time')
    fig.suptitle('Cyclic interactions: invariance does not imply a stable equal mixture');save(fig,'hypercycle')
    fig,axs=plt.subplots(1,3,figsize=(11,3.7))
    for ax,r in zip(axs,(-1,0,1)):
        ax.plot(time,arrays[f'three_group_{r}']);ax.set(xlabel='Time',ylabel='Fraction',title=f'Three-group model: r={r}')
    axs[0].legend(['x','y','z']);fig.suptitle('The assumed sign of r determines the outcome; x/y stays constant');save(fig,'three_group')
    fig,axs=plt.subplots(1,3,figsize=(12,3.8))
    xx=np.linspace(.08,.92,500);axs[0].plot(xx,-1/xx-4/(1-xx));axs[0].plot(equilibrium,-1/equilibrium-4/(1-equilibrium),'o',color='#c26436');axs[0].set(xlabel='Position between masses',ylabel='Potential',title='Gravitational balance is a maximum')
    series=arrays['sho'];axs[1].plot(series[:,0],series[:,1]);axs[1].set(xlabel='Displacement x',ylabel='Momentum p',title='Harmonic oscillator: conserved H')
    rr,pp=np.meshgrid(np.linspace(.28,5,500),np.linspace(-1.5,1.5,300));hh=.5*pp**2+.5/rr**2-1/rr
    axs[2].contour(rr,pp,hh,levels=[-.49,-.4,-.2,0,.2,.8],cmap='viridis');axs[2].plot(1,0,'o',color='#c26436');axs[2].set(xlabel='Radius r',ylabel='Radial momentum p',title='Inverse-square effective Hamiltonian');save(fig,'mechanics')
    fig,axs=plt.subplots(1,2,figsize=(10,4))
    for mu in (.5,1,2):
        series=arrays[f'predator_{mu:g}'];axs[0].plot(series[:,0],series[:,1],label=f'mu={mu:g}')
    axs[0].plot(1,1,'o',color='#c26436');axs[0].set(xlabel='Scaled prey x',ylabel='Scaled predators y',title='Positive trajectories lie on closed invariant curves');axs[0].legend()
    series=arrays['predator_1'];axs[1].plot(np.arange(len(series))*.01,series);axs[1].set(xlabel='Scaled time',ylabel='Population',title='Lotka–Volterra example: mu=1');axs[1].legend(['prey','predators']);save(fig,'predator_prey')
    print(json.dumps(summary,indent=2))
    if not summary['all_passed']:raise SystemExit(1)


if __name__=='__main__':main()
