"""Explicit closures and input checks around the complete, pinned corpus PDE.

No empirical mapping is built in. Domain: periodic unit square. Coordinates/time
are experiment units until calibrated. The archived solver remains reproducible.
"""
from dataclasses import dataclass
import numpy as np
from legacy_field import Field as LegacyField, Parameters as LegacyParameters, activation

@dataclass(frozen=True)
class Parameters(LegacyParameters):
    mu0: float = None  # corpus stress coefficient: must be declared, not inferred
    gradient_law: str = 'raw'
    delta: float = .01

def excess_gradient(g, threshold, law='raw', delta=.01):
    g=np.asarray(g)
    if law=='raw': return g-threshold
    if not np.isfinite(delta) or delta<=0: raise ValueError('delta must be finite and positive')
    if law=='regularized': return np.hypot(g,delta)-delta-threshold
    if law=='calibrated': return np.hypot(g,delta)-np.hypot(threshold,delta)
    raise ValueError('Unknown corpus gradient alternative')

class Field(LegacyField):
    def __init__(self,p):
        scalars=[p.nu,p.diffusivity,p.rho,p.sigma,p.threshold,p.epsilon,p.h,p.gamma,p.kappa,p.baseline,p.mu0,p.delta]
        if any(x is None or not np.isfinite(x) for x in scalars): raise ValueError('All coefficients including mu0 must be explicit and finite')
        if isinstance(p.n,bool) or not isinstance(p.n,int): raise ValueError('Grid size must be an integer')
        if p.mu0<=0 or p.epsilon<=0 or p.delta<=0: raise ValueError('Positive mu0, epsilon and delta required')
        if len(p.direction)!=2 or not np.isfinite(p.direction).all(): raise ValueError('Finite 2D unit direction required')
        if p.law not in ('sharp','tanh','smooth_off'): raise ValueError('Unknown response law')
        if p.gradient_law not in ('raw','regularized','calibrated'): raise ValueError('Unknown gradient law')
        super().__init__(p)

    def terms(self,z,A):
        # Corpus momentum, pressure projection and signed S transport, all retained.
        p=self.p;u=self.real(z[:2]);gs=self.gradient(z[2])
        gu=np.array([self.gradient(z[i]) for i in range(2)])
        adv_u=np.einsum('jxy,ijxy->ixy',u,gu);adv_s=np.sum(u*gs,axis=0)
        q=excess_gradient(np.sqrt(np.sum(gs*gs,axis=0)),p.threshold,p.gradient_law,p.delta)
        force=-(p.sigma/p.rho)*np.asarray(p.direction)[:,None,None]*activation(q,p.law,p.epsilon)
        b=self.fft(-adv_u+force)*self.mask
        du=self.project(b)-p.nu*self.k2*z[:2]
        ds=(-self.fft(adv_s)+p.kappa*A*self.kh)*self.mask-p.diffusivity*self.k2*z[2]
        ph=np.divide(-1j*(self.kx*b[0]+self.ky*b[1]),self.k2,out=np.zeros_like(z[2]),where=self.k2!=0)
        return np.concatenate([du,ds[None]]),ph,u,gu,force

    def step(self,z,A,U,dt):
        if not np.isfinite([A,U,dt]).all() or dt<=0 or not np.isfinite(z).all(): raise ValueError('Finite state/input and positive finite dt required')
        return super().step(z,A,U,dt)

    def stress(self,z):
        gu=np.array([self.gradient(z[i]) for i in range(2)])
        return self.p.mu0*(gu+gu.swapaxes(0,1))

    def diagnostics(self,z,A):
        d=super().diagnostics(z,A)
        d['stress_rms']=float(np.sqrt(np.mean(self.stress(z)**2)))
        d['mu0']=self.p.mu0;d['dynamic_viscosity']=self.p.rho*self.p.nu
        d['stress_equals_dynamic_viscosity']=bool(self.p.mu0==self.p.rho*self.p.nu)
        d['gradient_law']=self.p.gradient_law
        return d

    def run(self,*args,**kwargs):
        raise ValueError('Use evolve with explicit observation-start state, A and history basis; no silent session reset')

def evolve(person,intervals,p,*,z,A,start,initial_state_basis,max_dt):
    if not person or not initial_state_basis: raise ValueError('Person and initial-history provenance required')
    if any(x is None for x in [A,start,max_dt]) or not np.isfinite([A,start,max_dt]).all() or max_dt<=0: raise ValueError('Finite A, time and positive finite max_dt required')
    f=Field(p);z=np.array(z,dtype=complex,copy=True)
    if z.shape!=(3,p.n,p.n) or not np.isfinite(z).all(): raise ValueError('Invalid full field')
    if np.max(np.abs(z*(~f.mask)))>1e-10: raise ValueError('Unresolved initial modes')
    physical=np.fft.ifft2(z,axes=(-2,-1))
    if np.max(np.abs(physical.imag))>1e-10: raise ValueError('Fourier coefficients must represent real fields')
    if f.diagnostics(z,A)['divergence_rms']>1e-10: raise ValueError('Initial velocity must be divergence free')
    t=float(start);mass=f.real(z[2]).mean();rows=[]
    cap=.45/(max(p.nu,p.diffusivity)*max(1.,float(f.k2[f.mask].max())))
    for e in intervals:
        if e['person']!=person: raise ValueError('Cross-person history')
        if not np.isfinite([e['start'],e['end'],e['utility']]).all(): raise ValueError('Unobserved input or time is not zero')
        if abs(e['start']-t)>1e-12 or e['end']<=t: raise ValueError('History gap, overlap or nonpositive duration')
        if e['role'] not in ('Smoke','Clay','both','unattributed') or not e['event_ref']: raise ValueError('Missing role/event provenance')
        duration=e['end']-t;n=int(np.ceil(duration/min(max_dt,cap)));dt=duration/n
        mass+=p.kappa*(A*duration+.5*p.gamma*(e['utility']-p.baseline)*duration**2)
        for _ in range(n):z,A=f.step(z,A,e['utility'],dt)
        if not np.isfinite(z).all(): raise FloatingPointError('Nonfinite evolution')
        t=e['end'];d=f.diagnostics(z,A)
        d.update(person=person,time=t,steps=n,dt=dt,requested_max_dt=max_dt,stability_cap=cap,mass_exact=float(mass),mass_error=float(d['mass']-mass),role=e['role'],event_ref=e['event_ref'],initial_state_basis=initial_state_basis)
        rows.append(d)
    return z,float(A),rows

def refinement_is_distinct(coarse,fine):
    """Check actual steps, not requested maxima; keep duplicated runs in the log."""
    return len(coarse)==len(fine)>0 and all(b['dt']<a['dt'] and b['steps']>a['steps'] and a['time']==b['time'] for a,b in zip(coarse,fine))
