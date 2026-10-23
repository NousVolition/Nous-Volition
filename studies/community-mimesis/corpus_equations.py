"""Direct implementations of the supplied corrected corpus, with no social calibration.

Paragraph numbers are zero-based body-paragraph ordinals in the pinned DOCX.
Additional finite test geometry is always passed explicitly, not inferred from text.
"""
import numpy as np

POSITIONS = np.array([[2,3,1],[2,3,2],[1,3,2],[3,3,1]], dtype=float)

def alignment(positions=POSITIONS, y_ref=3):
    """P93-97: coordinate residual, not temporal stability."""
    return np.asarray(positions)[:,1] - y_ref

def reciprocal(S, R, lam):
    """P498-501: reciprocal scaling, not a dynamical conservation law."""
    if not lam > 0: raise ValueError('lambda must be positive')
    return lam*S, R/lam

def compare_W(wi, wj, *, same_action, same_context):
    """P104/P615: abstain when the required comparison is not established."""
    if wi not in (0,1) or wj not in (0,1): raise ValueError('W must be binary')
    if not (same_action and same_context): return None
    return wi == wj

def edge_candidates(actions, permitted, margins, epsilon, minimum=False, atol=1e-12):
    """P105-107: exact-edge or explicitly different minimum-clearance set.

    Actions, metric margins and permitted membership are caller-supplied.
    This does not estimate a social metric from text.
    """
    if epsilon <= 0: raise ValueError('epsilon must be positive')
    m=np.asarray(margins);p=np.asarray(permitted,dtype=bool)
    eligible=p & ((m>=epsilon) if minimum else np.isclose(m,epsilon,rtol=0,atol=atol))
    return np.asarray(actions)[eligible]

def response(q, kind, epsilon=1.):
    """P261-264: sharp, signed tanh, smooth exact-off remain distinct."""
    q=np.asarray(q,dtype=float)
    if epsilon<=0: raise ValueError('epsilon must be positive')
    if kind=='sharp':return np.maximum(q,0.)
    if kind=='tanh':
        # Algebraically q*(1+tanh(q/epsilon))/2, stable in the negative tail.
        from scipy.special import expit
        return q*expit(2*q/epsilon)
    if kind=='smooth_off':
        y=np.zeros_like(q);positive=q>0
        with np.errstate(over='ignore',under='ignore'):
            y[positive]=q[positive]*np.exp(-(epsilon/q[positive])**2)
        return y
    raise ValueError(kind)

def gradient_excess(grad, threshold, delta=None, calibrated=False):
    """P263-264: optional smooth gradient changes the onset unless calibrated."""
    if threshold<0:raise ValueError('threshold must be nonnegative')
    norm=np.linalg.norm(np.asarray(grad),axis=-1)
    if delta is None:return norm-threshold
    if delta<=0:raise ValueError('delta must be positive')
    return np.hypot(norm,delta)-(np.hypot(threshold,delta) if calibrated else delta+threshold)

def force(q, sigma, rho, direction, kind, epsilon=1.):
    """P230: fixed direction; never silently replace by drag."""
    e=np.asarray(direction,dtype=float)
    if sigma<0 or rho<=0 or not np.isclose(np.linalg.norm(e),1):raise ValueError('Invalid force parameters')
    return -(sigma/rho)*np.asarray(response(q,kind,epsilon))[...,None]*e

def stress(velocity_gradient, mu0):
    """P545: symmetric Newtonian stress."""
    if mu0<=0:raise ValueError('mu0 must be positive')
    g=np.asarray(velocity_gradient);return mu0*(g+g.swapaxes(-1,-2))

def momentum_rhs(advection, pressure_gradient, laplacian, rho, mu, added_force):
    """P229/P549: u_t=-advection-grad(P)/rho+(mu/rho)lap(u)+f.

    Caller supplies compatible fields. This evaluator is not an incompressible
    projection solver and cannot independently enforce divergence-free velocity.
    """
    if rho<=0 or mu<=0:raise ValueError('Positive density and viscosity required')
    return -np.asarray(advection)-np.asarray(pressure_gradient)/rho+(mu/rho)*np.asarray(laplacian)+np.asarray(added_force)

def memory_step(A, total_field, excess, dt, gamma=1., kappa=1.):
    """P517-519: exact integral on one constant-input interval, closed boundaries.

    A'=gamma*excess and integral(S)'=kappa*A. No forgetting or W input is added.
    """
    if dt<0:raise ValueError('dt must be nonnegative')
    return A+gamma*excess*dt, total_field+kappa*(A*dt+.5*gamma*excess*dt*dt)

def transport(n=64, end=1., max_dt=.001, excess=1., gamma=1., kappa=1., source=True):
    """Specified verification fixture of P517: periodic length 2pi, u=.4, D=.05.

    S0=sin(x), normalized smooth kernel exp(3cos(x-pi)); RK4, centered fluxes.
    These domain/parameter choices verify code and are not measured social values.
    """
    if n<8 or end<0 or max_dt<=0:raise ValueError('Invalid numerical parameters')
    x=np.arange(n)*2*np.pi/n;dx=2*np.pi/n
    K=np.exp(3*np.cos(x-np.pi));K/=K.sum()*dx
    u=.4;D=.05
    dt=min(max_dt,.2*dx/u,.2*dx*dx/D)
    steps=max(1,int(np.ceil(end/dt)));dt=end/steps
    y=np.r_[np.sin(x),0.]
    def rhs(z):
        s=z[:-1];A=z[-1]
        adv=-u*(np.roll(s,-1)-np.roll(s,1))/(2*dx)
        diff=D*(np.roll(s,-1)-2*s+np.roll(s,1))/dx**2
        return np.r_[adv+diff+(K*kappa*A if source else 0.),gamma*excess]
    for _ in range(steps):
        k1=rhs(y);k2=rhs(y+.5*dt*k1);k3=rhs(y+.5*dt*k2);k4=rhs(y+dt*k3)
        y+=dt*(k1+2*k2+2*k3+k4)/6
    return x,y[:-1],float(y[-1]),float(y[:-1].sum()*dx)
