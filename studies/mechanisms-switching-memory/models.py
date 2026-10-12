"""Explicit ideal mechanical model and uncalibrated biochemical hypothesis.

Spring time tau=k*t/gamma; biochemical time is seconds with ASSUMED rates.
No parameter is fitted to CO, CO2, water, fog, smoke, VOCs or H2O2.
"""
import math
import numpy as np
from scipy.integrate import solve_ivp, quad
from scipy.optimize import brentq

SPRING = dict(a_m=.01, L0_m=.02, k_N_m=1., gamma_N_s_m=2.,
              mass_kg=.01, g_m_s2=9.80665)
CHEM = dict(v=2., K=.3, n=4, d=1.)


def spring_force(y, bias=0., lam=2.):
    """Force/(k*a), not a molecular force."""
    return bias-y+lam*y/np.sqrt(1+y*y)


def spring_slope(y, lam=2.):
    return -1+lam/(1+y*y)**1.5


def spring_potential(y, bias=0., lam=2.):
    """Potential/(k*a*a); its negative gradient is spring_force."""
    return .5*(np.sqrt(1+y*y)-lam)**2-bias*y


def spring_folds(lam=2.):
    if lam <= 1:
        return None
    c=lam**(2/3)-1
    return math.sqrt(c), c**1.5


def spring_roots(bias=0., lam=2.):
    bound=abs(bias)+lam+1
    cuts=[-bound,bound]
    if lam > 1:
        yf,_=spring_folds(lam)
        cuts=[-bound,-yf,yf,bound]
    roots=[]
    for a,b in zip(cuts[:-1],cuts[1:]):
        fa,fb=spring_force(a,bias,lam),spring_force(b,bias,lam)
        if abs(fa)<1e-12: roots.append(a)
        if fa*fb<0: roots.append(brentq(lambda y:spring_force(y,bias,lam),a,b,xtol=1e-14))
        if abs(fb)<1e-12: roots.append(b)
    return sorted(set(round(r,13) for r in roots))


def integrate(fun, initial, duration, max_step=.1, rtol=1e-11, samples=801):
    sol=solve_ivp(fun,(0.,duration),np.asarray(initial,dtype=float),method='DOP853',
                  t_eval=np.linspace(0,duration,samples),rtol=rtol,atol=rtol*.01,
                  max_step=max_step)
    if not sol.success: raise RuntimeError(sol.message)
    return sol.t, sol.y


def spring_pulse(duration, bias=.8, lam=2., post=40., max_step=.1):
    """Sudden changes of tilt do parameter work; include both jumps."""
    y0=-math.sqrt(lam*lam-1) if lam>1 else 0.
    # z=(position, dissipated energy, parameter work), dimensionless energies.
    def rhs(b):
        def f(t,z):
            v=spring_force(z[0],b,lam)
            return [v,v*v,0.]
        return f
    z0=[y0,0.,-bias*y0]
    t1,z1=integrate(rhs(bias),z0,duration,max_step=max_step)
    reset=z1[:,-1].copy();reset[2]+=bias*reset[0]
    t2,z2=integrate(rhs(0.),reset,post,max_step=max_step)
    t=np.r_[t1,t2+duration];z=np.c_[z1,z2]
    b=np.r_[np.full(len(t1),bias),np.zeros(len(t2))]
    E=spring_potential(z[0],b,lam)
    residual=E+z[1]-z[2]-spring_potential(y0,0.,lam)
    return t,z,b,float(np.max(np.abs(residual)))


def spring_critical_pulse(bias=.8, lam=2.):
    if lam<=1 or bias<=spring_folds(lam)[1]:
        return math.inf
    return quad(lambda y:1/spring_force(y,bias,lam),-math.sqrt(lam*lam-1),0,
                epsabs=1e-12,epsrel=1e-12)[0]


def spring_ramp(half_duration=160., amplitude=.8, lam=2.):
    y0=spring_roots(-amplitude,lam)[0];z0=[y0,0.,0.]
    all_t=[];all_z=[];all_b=[];switch=[]
    for leg in [0,1]:
        start=(-amplitude if leg==0 else amplitude)
        slope=(2*amplitude/half_duration)*(1 if leg==0 else -1)
        def rhs(t,z):
            b=start+slope*t;v=spring_force(z[0],b,lam)
            return [v,v*v,-z[0]*slope]
        sol=solve_ivp(rhs,(0,half_duration),z0,method='DOP853',rtol=1e-11,atol=1e-13,
                      max_step=.5,dense_output=True,
                      events=lambda t,z:z[0])
        if not sol.success: raise RuntimeError(sol.message)
        times=np.linspace(0,half_duration,1001)
        all_t.append(times+leg*half_duration);all_z.append(sol.sol(times))
        all_b.append(start+slope*times)
        switch.extend([float(start+slope*t) for t in sol.t_events[0]])
        z0=sol.y[:,-1]
    t=np.concatenate(all_t);z=np.concatenate(all_z,axis=1);b=np.concatenate(all_b)
    residual=spring_potential(z[0],b,lam)+z[1]-z[2]-spring_potential(y0,-amplitude,lam)
    return t,z,b,switch,float(np.max(np.abs(residual)))


def rates(p, stimulus=0., v=2., K=.3, n=4, d=1.):
    """Effective per-total-protein rates (s^-1); p is an active fraction."""
    hill=p**n/(K**n+p**n)
    return (stimulus+v*hill)*(1-p),d*p


def chemical_slope(p, stimulus=0., v=2., K=.3, n=4, d=1.):
    hill=p**n/(K**n+p**n)
    dh=n*K**n*p**(n-1)/(K**n+p**n)**2
    return v*dh*(1-p)-(stimulus+v*hill)-d


def chemical_roots(stimulus=0., **params):
    pars=CHEM|params;v,K,n,d=[pars[k] for k in ['v','K','n','d']]
    # Polynomial after multiplication by the strictly positive Hill denominator.
    c=np.zeros(n+2);c[0]+=stimulus*K**n;c[1]-=(stimulus+d)*K**n
    c[n]+=stimulus+v;c[n+1]-=stimulus+v+d
    roots=np.polynomial.polynomial.polyroots(c)
    return sorted(float(np.clip(r.real,0,1)) for r in roots
                  if abs(r.imag)<1e-8 and -1e-10<=r.real<=1+1e-10)


def chemical_critical_pulse(stimulus=.5, **params):
    roots=chemical_roots(**params)
    if len(roots)!=3: return math.inf
    low,threshold,_=roots
    pars=CHEM|params
    def f(p):
        up,down=rates(p,stimulus,**pars)
        return up-down
    if any(f(p)<=0 for p in np.linspace(low,threshold,100)):return math.inf
    return quad(lambda p:1/f(p),low,threshold,epsabs=1e-12,epsrel=1e-12)[0]


def chemical_pulse(duration, stimulus=.5, post=30., mode='feedback',max_step=.1,
                   **params):
    """Track active fraction and cumulative activation/deactivation counts.

    One activation uses one ATP per protein event; reservoir replenishment is
    assumed. This is a bookkeeping convention, not calibrated enzyme kinetics.
    """
    pars=CHEM|params
    if mode=='no_feedback':pars['v']=0.
    z0=[0.,0.,0.];out_t=[];out_z=[]
    for leg,(s,duration_leg) in enumerate([(stimulus,duration),(0.,post)]):
        def rhs(t,z):
            up,down=rates(z[0],s,**pars)
            if leg==1 and mode=='fuel_off':up=0.
            if leg==1 and mode=='feedback_off':up,down=rates(z[0],0.,**(pars|{'v':0.}))
            return [up-down,up,down]
        t,z=integrate(rhs,z0,duration_leg,max_step=max_step)
        out_t.append(t+(duration if leg else 0));out_z.append(z);z0=z[:,-1]
    return np.concatenate(out_t),np.concatenate(out_z,axis=1)


def finite_fuel(duration=40., ATP0_uM=2., KmATP_uM=.1):
    """Closed adenylate/phosphate inventories; buffered water and H+ omitted.

    Total protein=1 uM; initial active fraction is the chemostatted high state.
    The ATP availability factor is another explicitly ASSUMED kinetic law.
    """
    p0=chemical_roots()[-1]
    def rhs(t,z):
        p,ATP,ADP,Pi=z;up,down=rates(p)
        up*=ATP/(KmATP_uM+ATP)
        return [up-down,-up,up,down]
    return integrate(rhs,[p0,ATP0_uM,0.,0.],duration,max_step=.02)


def rk4_piecewise(fun1,fun2,initial,duration1,duration2,h):
    """Independent fixed-step implementation for refinement checks."""
    y=np.array(initial,dtype=float)
    for fun,duration in [(fun1,duration1),(fun2,duration2)]:
        if duration==0:continue
        steps=math.ceil(duration/h);dt=duration/steps
        for i in range(steps):
            k1=np.asarray(fun(y));k2=np.asarray(fun(y+dt*k1/2))
            k3=np.asarray(fun(y+dt*k2/2));k4=np.asarray(fun(y+dt*k3))
            y+=dt*(k1+2*k2+2*k3+k4)/6
    return y


def gillespie(N, seed, pulse_duration, stimulus=.5, post=20., v=2.):
    """Exact jumps of a phenomenological Hill birth/death process.

    The count of total protein is fixed. This is NOT an elementary-reaction
    derivation of cooperative kinase kinetics or a stochastic laboratory fit.
    """
    rng=np.random.default_rng(seed);j=0;births=0;deaths=0
    for duration,s in [(pulse_duration,stimulus),(post,0.)]:
        t=0.
        while t<duration:
            up,down=rates(j/N,s,v=v);birth=N*up;death=N*down;total=birth+death
            if total<=0:break
            t+=rng.exponential(1/total)
            if t>=duration:break
            if rng.random()<birth/total:j+=1;births+=1
            else:j-=1;deaths+=1
            if not 0<=j<=N:raise AssertionError('protein count left physical bounds')
    return dict(final_active_count=j,activation_events=births,deactivation_events=deaths,
                balance_residual=j-births+deaths)


def wilson(successes,trials,z=1.95996398454):
    p=successes/trials;den=1+z*z/trials
    center=(p+z*z/(2*trials))/den
    half=z*math.sqrt(p*(1-p)/trials+z*z/(4*trials*trials))/den
    return [center-half,center+half]
