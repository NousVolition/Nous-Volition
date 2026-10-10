"""Proposed reduced dynamics of the hug; no fluid or material calibration.

The original pressure memory, mirrored arms and opening rule are retained.
New: a signed lean q with inertia, damping and cubic restoring force.
Memory may change its stiffness. A scalar load never chooses a lean direction.
All extension variables and time are in model units.
"""
from dataclasses import dataclass
from pathlib import Path
import sys
import math
import numpy as np
from scipy.integrate import solve_ivp

sys.path.insert(0, str(Path(__file__).parent / 'source'))
from hug_envelope import arm_points, smoothstep


@dataclass(frozen=True)
class Parameters:
    r: float = -1.0
    damping: float = 0.6
    pressure: float = 0.8
    memory_coupling: float = 0.8
    shear: float = 0.35
    pulse_duration: float = 4.0

    def __post_init__(self):
        if not all(math.isfinite(x) for x in self.__dict__.values()):
            raise ValueError('Parameters must be finite')
        if min(self.damping, self.pressure, self.memory_coupling, self.shear) < 0 or self.pulse_duration <= 0:
            raise ValueError('Invalid model parameter')


def pressure(t, p):
    """Nonnegative smooth pulse, normalized by the original opening limit."""
    return p.pressure * math.sin(math.pi*t/p.pulse_duration)**2 if 0 < t < p.pulse_duration else 0.0


def rhs(t, y, p):
    q, v, imprint, work, loss = y
    load = pressure(t, p)
    tau = .8 if load > imprint else 6.0
    feedback = p.memory_coupling * imprint * q
    return np.array([v, p.r*q-q**3-p.damping*v+feedback,
                     (load-imprint)/tau, feedback*v, p.damping*v*v])


def step(f, t, y, h, method='rk4'):
    k1 = f(t, y)
    if method == 'euler':
        return y+h*k1
    if method == 'heun':
        return y+h*(k1+f(t+h,y+h*k1))/2
    if method != 'rk4':
        raise ValueError('Use euler, heun or rk4')
    k2 = f(t+h/2, y+h*k1/2)
    k3 = f(t+h/2, y+h*k2/2)
    k4 = f(t+h, y+h*k3)
    return y+h*(k1+2*k2+2*k3+k4)/6


def integrate(p, q0=.04, dt=.02, end=24., method='rk4', v0=0.):
    if dt <= 0 or end <= 0 or not math.isfinite(dt+end+q0+v0):
        raise ValueError('Finite positive times and finite starting values required')
    count = int(round(end/dt))
    if count < 1 or not math.isclose(count*dt, end, abs_tol=1e-10):
        raise ValueError('End time must be an integer multiple of dt')
    times = np.linspace(0,end,count+1)
    values = np.zeros((count+1,5)); values[0,:2] = [q0,v0]
    for i,t in enumerate(times[:-1]):
        values[i+1] = step(lambda t,y:rhs(t,y,p), t, values[i], dt, method)
    if not np.isfinite(values).all():
        raise ArithmeticError('Nonfinite trajectory')
    return times,values


def reference(p, times, q0=.04, v0=0., tolerance=1e-11):
    solution = solve_ivp(lambda t,y:rhs(t,y,p), (times[0],times[-1]),
                         [q0,v0,0,0,0], method='DOP853', t_eval=times,
                         rtol=tolerance, atol=tolerance/100, max_step=.05)
    if not solution.success:
        raise RuntimeError(solution.message)
    return solution.y.T


def energy(y,p):
    return .5*y[...,1]**2-.5*p.r*y[...,0]**2+.25*y[...,0]**4


def opening_time(p):
    if p.pressure < 1:
        return None
    return p.pulse_duration/math.pi*math.asin(math.sqrt(1/p.pressure))


def geometry(t,y,p,points=65):
    q, _, m = y[:3]
    sx = 1+m*(.04+.02*math.sin(2*math.pi*t/3)); sy=1/sx
    opened = opening_time(p)
    bend = 1 if opened is None else 1-smoothstep((t-opened)/.8)
    left,right = arm_points(bend,sx,sy,points)
    # A unit-determinant shear: original geometry is exact when q=0.
    for arm in (left,right):
        for point in arm:
            point[0] += p.shear*q*point[1]
    return dict(left=left,right=right,sx=sx,sy=sy,bend=bend,
                gap=2*sx*(1-bend),shear=p.shear*q,
                opening_time=opened,closed=bend==1)


def equilibria(r,damping):
    roots=[0.] if r <= 0 else [-math.sqrt(r),0.,math.sqrt(r)]
    return [(q,np.linalg.eigvals([[0,1],[r-3*q*q,-damping]])) for q in roots]


def winding(f,center,radius=.1,n=1024):
    a=np.linspace(0,2*np.pi,n+1)
    vectors=np.array([f(center+radius*np.array([math.cos(t),math.sin(t)])) for t in a])
    if np.min(np.linalg.norm(vectors,axis=1)) < 1e-12:
        raise ValueError('Index undefined: a zero lies on the sampling curve')
    angles=np.unwrap(np.arctan2(vectors[:,1],vectors[:,0]))
    return float((angles[-1]-angles[0])/(2*np.pi))


PRESETS = {
 'original':('Original pressure and imprint',Parameters(memory_coupling=0),0.),
 'damped':('Added lean · light damping',Parameters(pressure=0,memory_coupling=0,damping=.2),.5),
 'overdamped':('Added lean · strong damping',Parameters(pressure=0,memory_coupling=0,damping=4),.5),
 'right':('Buckling · positive starting lean',Parameters(r=1,pressure=0,damping=1),.04),
 'left':('Buckling · negative starting lean',Parameters(r=1,pressure=0,damping=1),-.04),
 'balanced':('Buckling · exactly balanced start',Parameters(r=1,pressure=0,damping=1),0.),
 'memory':('Pressure memory changes stiffness',Parameters(r=-.25,damping=.6,memory_coupling=1.5),.04),
 'opening':('Original pressure opening',Parameters(pressure=1.2,memory_coupling=0),0.),
}
