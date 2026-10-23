"""Person-specific runner for the unchanged corpus field equations.

History provenance and idea reports are preserved as records, not inferred labels.
No missing utility or unknown initial state is silently assigned zero.
"""
from dataclasses import dataclass
import numpy as np
from corpus_field import Field,Parameters

@dataclass(frozen=True)
class InputInterval:
    person:str
    start:float
    end:float
    utility:float
    role:str
    event_ref:str

def integrate(person,intervals,p=Parameters(),z=None,A=None,start=None,max_dt=.002,initial_state_basis=None):
    if not person or not initial_state_basis or z is None or A is None or start is None:
        raise ValueError('Supply person, full observation-start field, A, time and initial-state provenance; unknown is not zero')
    f=Field(p);z=np.array(z,dtype=complex,copy=True)
    if z.shape!=(3,p.n,p.n) or not np.isfinite(z).all() or not np.isfinite(A):raise ValueError('Invalid state')
    if np.sqrt(np.mean(f.real(1j*(f.kx*z[0]+f.ky*z[1]))**2))>1e-10:raise ValueError('Initial velocity must be divergence-free')
    if np.max(np.abs(z*(~f.mask)))>1e-10:raise ValueError('Initial state must use the declared resolved modes')
    t=float(start);mass=float(f.real(z[2]).mean());rows=[]
    cap=.45/(max(p.nu,p.diffusivity)*max(1.,float(f.k2[f.mask].max())))
    for e in intervals:
        if e.person!=person:raise ValueError('Cross-person history')
        if not np.isclose(e.start,t,rtol=0,atol=1e-12):raise ValueError('Unobserved time gap or overlapping interval: do not invent its input')
        if e.end<=e.start or e.utility is None or not np.isfinite(e.utility):raise ValueError('Missing/invalid measured or declared utility')
        if e.role not in {'Smoke','Clay','both','unattributed'} or not e.event_ref:raise ValueError('History provenance missing')
        duration=e.end-e.start;nsteps=max(1,int(np.ceil(duration/min(max_dt,cap))));dt=duration/nsteps
        mass+=p.kappa*(A*duration+.5*p.gamma*(e.utility-p.baseline)*duration**2)
        for _ in range(nsteps):
            z,A=f.step(z,A,e.utility,dt)
            if not np.isfinite(z).all():raise FloatingPointError('Nonfinite field')
        t=e.end;d=f.diagnostics(z,A)
        d.update(person=person,time=t,role=e.role,event_ref=e.event_ref,initial_state_basis=initial_state_basis,mass_exact=mass,mass_error=d['mass']-mass,steps=nsteps,dt=dt)
        rows.append(d)
    return z,float(A),rows

def observation_support(codebook):
    """No automatic conceptual relabeling: report exact available item names."""
    items=set(codebook.get('item',{}))
    return dict(recorded_items=sorted(items),full_two_in_one_measured=False,
                missing=['separate_inward_receiving','intended_meaning','utility','memory_contents_and_role_references','perceived_balance','felt_temporal_distance','unspoken_agreement','small_change_consequences'],
                partial_movement_report='mvmt' in items)
