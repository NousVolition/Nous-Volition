"""Dimensionless models transcribed from user-provided circle/firefly/junction pages."""
import numpy as np


def triangle(phi, normalized=False):
    x=(np.asarray(phi)+np.pi/2)%(2*np.pi)-np.pi/2
    value=np.where(x<=np.pi/2,x,np.pi-x)
    return value*(2/np.pi if normalized else 1)


def phase_rhs(phi, delta, amplitude=1., response='sine'):
    f=np.sin(phi) if response=='sine' else triangle(phi,response=='triangle_normalized')
    return delta-amplitude*f


def drift_period(delta, amplitude=1., response='sine'):
    d=np.abs(np.asarray(delta,dtype=float))
    peak=amplitude*(np.pi/2 if response=='triangle' else 1)
    answer=np.full(d.shape,np.inf)
    mask=d>peak
    if response=='sine': answer[mask]=2*np.pi/np.sqrt(d[mask]**2-amplitude**2)
    else:
        slope=amplitude*(2/np.pi if response=='triangle_normalized' else 1)
        answer[mask]=2/slope*np.log((d[mask]+peak)/(d[mask]-peak))
    return answer


def rk4(state, dt, rhs):
    k1=rhs(state); k2=rhs(state+dt*k1/2)
    k3=rhs(state+dt*k2/2); k4=rhs(state+dt*k3)
    return state+dt*(k1+2*k2+2*k3+k4)/6


def integrate_phase(deltas, response='sine', dt=.02, duration=240., transient=80.):
    deltas=np.asarray(deltas,float); phi=np.zeros(deltas.shape)
    start=np.zeros_like(phi); saved=[]; times=[]
    crossing=[[] for _ in deltas]
    sample=max(1,round(.5/dt))
    for step in range(round(duration/dt)):
        before=phi.copy(); phi=rk4(phi,dt,lambda x:phase_rhs(x,deltas,response=response))
        t=(step+1)*dt
        if step+1==round(transient/dt): start=phi.copy()
        # All execution-grid detunings are nonnegative. Interpolate complete turns.
        old=np.floor(before/(2*np.pi)); new=np.floor(phi/(2*np.pi))
        for j in np.flatnonzero((new>old)&(t>transient)):
            level=2*np.pi*new[j]
            crossing[j].append(t-dt+dt*(level-before[j])/(phi[j]-before[j]))
        if (step+1)%sample==0: saved.append(phi.copy());times.append(t)
    measured=np.array([np.mean(np.diff(x)) if len(x)>1 else np.nan for x in crossing])
    return dict(deltas=deltas,final=phi,mean_rate=(phi-start)/(duration-transient),
                measured_period=measured,crossings=np.array([len(x) for x in crossing]),
                times=np.array(times),phase=np.array(saved))


def junction_rhs(state, bias, beta):
    phi,velocity=state
    return np.array([velocity,(bias-velocity-np.sin(phi))/beta])


def junction_sweep(beta, dt=.04, settle=160., observe=80., grid=None):
    """Continuation up and back down, retaining phase and velocity between steps."""
    if grid is None: grid=np.linspace(0,1.5,61)
    betas=np.asarray(beta,float); state=np.zeros((2,len(betas)))
    records=[]
    for direction,values in [('up',grid),('down',grid[::-1])]:
        for bias in values:
            rhs=lambda z:junction_rhs(z,bias,betas)
            for _ in range(round(settle/dt)): state=rk4(state,dt,rhs)
            before=state[0].copy()
            for _ in range(round(observe/dt)): state=rk4(state,dt,rhs)
            rate=(state[0]-before)/observe
            for b,v in zip(betas,rate):
                records.append(dict(beta=float(b),direction=direction,bias=float(bias),voltage_ratio=float(v)))
            # Reduction by whole cycles avoids large-angle precision loss only.
            state[0]=(state[0]+np.pi)%(2*np.pi)-np.pi
    return records


def network_rhs(phi, delta, adjacency, forcing, coupling=4.):
    degree=adjacency.sum(1)
    interaction=(np.sin(phi)*(np.cos(phi)@adjacency.T)-np.cos(phi)*(np.sin(phi)@adjacency.T))/degree
    return delta-coupling*interaction-forcing*np.sin(phi)


def network_block(seed, topology, dt=.04, duration=120., observe=30.):
    from recovery_model import Config, initialize
    n=30; a,_,_,_=initialize(Config(n=n,seed=seed,topology=topology))
    rng=np.random.default_rng(np.random.SeedSequence([seed,4421]))
    degree=a.sum(1)
    hi=int(rng.choice(np.flatnonzero(degree==degree.max())))
    low_candidates=np.flatnonzero((degree==degree.min())&(np.arange(n)!=hi))
    lo=int(rng.choice(low_candidates))
    permutation=np.arange(n);permutation[hi],permutation[lo]=permutation[lo],permutation[hi]
    delta=rng.uniform(.08,.16,n); initial=rng.uniform(-np.pi,np.pi,n)
    modes=('none','high_degree','low_degree','distributed')
    forcing=np.zeros((8,n));deltas=[];phases=[]
    for mapping,order in enumerate((np.arange(n),permutation)):
        for j,mode in enumerate(modes):
            row=4*mapping+j
            if mode=='high_degree':forcing[row,hi]=12
            if mode=='low_degree':forcing[row,lo]=12
            if mode=='distributed':forcing[row,:]=12/n
            deltas.append(delta[order]);phases.append(initial[order])
    deltas=np.array(deltas);phi=np.array(phases);start=None;minimum=None;maximum=None
    coherence=[];rhs=lambda x:network_rhs(x,deltas,a,forcing)
    for step in range(round(duration/dt)):
        phi=rk4(phi,dt,rhs)
        if step+1==round((duration-observe)/dt):
            start=phi.copy();minimum=phi.copy();maximum=phi.copy()
        if step+1>round((duration-observe)/dt):
            minimum=np.minimum(minimum,phi);maximum=np.maximum(maximum,phi)
            coherence.append(np.abs(np.mean(np.exp(1j*phi),axis=1)))
    drift=(phi-start)/observe;locked=(abs(drift)<.005)&((maximum-minimum)<.2)
    coh=np.mean(coherence,axis=0)
    return [dict(seed=seed,topology=topology,mapping=k//4,driver=modes[k%4],
        high_site=hi,low_site=lo,high_degree=int(degree[hi]),low_degree=int(degree[lo]),
        coherence=float(coh[k]),mean_drift=float(drift[k].mean()),
        drift_spread=float(drift[k].std()),locked_fraction=float(locked[k].mean()),
        all_locked=bool(locked[k].all())) for k in range(8)]


def circle_solutions(k=3):
    pi=np.pi
    return [
        dict(exercise='4.1.2',equation='1 + 2 cos(theta)',roots=[2*pi/3,4*pi/3],stability=['stable','unstable']),
        dict(exercise='4.1.3',equation='sin(2 theta)',roots=[0,pi/2,pi,3*pi/2],stability=['unstable','stable','unstable','stable']),
        dict(exercise='4.1.4',equation='sin(theta)^3',roots=[0,pi],stability=['unstable (nonhyperbolic)','stable (nonhyperbolic)']),
        dict(exercise='4.1.5',equation='sin(theta) + cos(theta)',roots=[3*pi/4,7*pi/4],stability=['stable','unstable']),
        dict(exercise='4.1.6',equation='3 + cos(2 theta)',roots=[],stability=[],period=float(pi/np.sqrt(2))),
        dict(exercise='4.1.7',equation=f'sin({k} theta)',roots=[m*pi/k for m in range(2*k)],stability=['stable' if m%2 else 'unstable' for m in range(2*k)])]
