"""Stability and energy tests for the eight supplied screenshots.

Screenshot models are dimensionless unless explicitly labelled otherwise.
The double-well potential is an illustrative choice: the image shows no formula.
Physical exchange/drag cases audit the earlier research model, not a new theory.
"""
import numpy as np
from scipy.integrate import solve_ivp

R=8.31446261815324
E_CHARGE=1.602176634e-19
KB=1.380649e-23
KE=1/(4*np.pi*8.8541878128e-12)


def integrate(fun,initial,end=10,points=1001,rtol=1e-11,max_step=.1):
    ts=np.linspace(0,end,points)
    sol=solve_ivp(fun,(0,end),initial,t_eval=ts,method='DOP853',rtol=rtol,
                  atol=rtol*1e-2,max_step=max_step)
    if not sol.success:raise RuntimeError(sol.message)
    return ts,sol.y


def cubic_rhs(t,z,a=1):
    x,y=z;rr=x*x+y*y
    return np.array([-y+a*x*rr,x+a*y*rr])


def cubic_exact(t,r0=.2,a=1):
    t=np.asarray(t)
    den=1-2*a*r0*r0*t
    if np.any(den<=0):raise ValueError('Beyond finite-time blow-up.')
    return r0/np.sqrt(den)


def cubic_case(a=1,r0=.2,end=10,rtol=1e-11,max_step=.1):
    tt,z=integrate(lambda t,z:cubic_rhs(t,z,a),[r0,0],end,rtol=rtol,max_step=max_step)
    radius=cubic_exact(tt,r0,a)
    exact=radius*np.array([np.cos(tt),np.sin(tt)])
    return tt,z,dict(a=a,r0=r0,end=end,final_radius=float(np.linalg.norm(z[:,-1])),
        exact_final_radius=float(radius[-1]),linear_prediction_radius=r0,
        max_state_error=float(np.max(np.linalg.norm(z-exact,axis=0))),
        forward_blowup_time=(1/(2*a*r0*r0) if a>0 and r0>0 else None))


def cycle_radius(t,r0):
    if r0<0:raise ValueError('Nonnegative radius required.')
    t=np.asarray(t)
    if r0==0:return np.zeros_like(t)
    den=r0*r0+(1-r0*r0)*np.exp(-2*t)
    if np.any(den<=0):raise ValueError('Outside the backward flow domain.')
    return r0/np.sqrt(den)


def cycle_rhs(t,z):
    x,y=z;rr=x*x+y*y
    return np.array([(1-rr)*x-y,x+(1-rr)*y])


def numerical_return(r0):
    if r0<=0:raise ValueError('The transverse positive-axis section excludes the origin.')
    def section(t,z):return z[1]
    section.direction=1
    sol=solve_ivp(cycle_rhs,(0,2*np.pi+.2),[r0,0],events=section,
        method='DOP853',rtol=1e-12,atol=1e-14,max_step=.05)
    i=np.flatnonzero(sol.t_events[0]>1e-5)[0]
    return float(sol.t_events[0][i]),float(sol.y_events[0][i,0])


def cycle_monodromy():
    def rhs(t,z):
        x,y=z[:2];rr=x*x+y*y
        J=np.array([[1-rr-2*x*x,-1-2*x*y],[1-2*x*y,1-rr-2*y*y]])
        return np.r_[cycle_rhs(t,z[:2]),(J@z[2:].reshape(2,2)).ravel()]
    tt,z=integrate(rhs,[1,0,1,0,0,1],2*np.pi,501)
    return z[2:,-1].reshape(2,2)


def competition_rhs(t,z):
    x,y=z
    return np.array([x*(3-x-2*y),y*(2-x-y)])


def competition_jacobian(z):
    x,y=z
    return np.array([[3-2*x-2*y,-2*x],[-y,2-x-2*y]])


def competition_fixed_points():
    points=[(0,0),(0,2),(3,0),(1,1)]
    labels=['unstable node','stable node','stable node','saddle']
    return [dict(point=list(p),jacobian=competition_jacobian(p).tolist(),
        eigenvalues=np.sort(np.real_if_close(np.linalg.eigvals(competition_jacobian(p)))).tolist(),
        classification=label) for p,label in zip(points,labels)]


def competition_examples():
    u=np.array([np.sqrt(2),-1]);u/=np.linalg.norm(u)
    initials=[(.1,.1),(.1,1),(1,.1),(.4,1.8),(2.5,.1),(1.8,1.4),
              tuple(np.ones(2)+1e-3*u),tuple(np.ones(2)-1e-3*u)]
    out=[]
    for initial in initials:
        tt,z=integrate(competition_rhs,initial,60,1201)
        out.append((tt,z,dict(initial=list(initial),final=z[:,-1].tolist(),
                             minimum=float(z.min()))))
    return out


def stable_manifold():
    v=np.array([np.sqrt(2),1]);v/=np.linalg.norm(v)
    curves=[]
    def boundary(t,z):return min(4-z[0],3-z[1])
    boundary.terminal=True;boundary.direction=-1
    for sign in [-1,1]:
        sol=solve_ivp(competition_rhs,(0,-22),np.ones(2)+sign*1e-7*v,
            method='DOP853',rtol=1e-11,atol=1e-13,max_step=.03,
            events=boundary)
        if not sol.success:raise RuntimeError(sol.message)
        curves.append(sol.y)
    return curves


def linearization_error(eps):
    p=np.ones(2);direction=np.array([1.,-.3]);direction/=np.linalg.norm(direction)
    J=competition_jacobian(p)
    residual=np.linalg.norm(competition_rhs(0,p+eps*direction)-eps*J@direction)
    tt,z=integrate(competition_rhs,p+eps*direction,1,301)
    tl,dl=integrate(lambda t,d:J@d,eps*direction,1,301)
    return dict(epsilon=eps,vector_field_remainder=float(residual),
        max_trajectory_error=float(np.max(np.linalg.norm(z-(p[:,None]+dl),axis=0))))


def potential(x):return np.asarray(x)**4/4-np.asarray(x)**2/2


def well_rhs(t,z,gamma=0):
    x,v,loss=z
    return np.array([v,x-x**3-gamma*v,gamma*v*v])


def well_case(initial=(1,.4),end=40,gamma=0):
    tt,z=integrate(lambda t,z:well_rhs(t,z,gamma),[*initial,0],end,1601)
    energy=z[1]**2/2+potential(z[0])
    return tt,z,energy,dict(initial=list(initial),gamma=gamma,end=end,
        initial_energy=float(energy[0]),final_energy=float(energy[-1]),
        final_state=z[:2,-1].tolist(),dissipated_energy=float(z[2,-1]),
        max_energy_balance_error=float(np.max(abs(energy+z[2]-energy[0]))),
        x_min=float(z[0].min()),x_max=float(z[0].max()))


def reversal_case(gamma=0):
    initial=[.8,.35];end=12
    tt,z,ee,row=well_case(initial,end,gamma)
    tr,zr,er,rr=well_case([z[0,-1],-z[1,-1]],end,gamma)
    target=z[:2,::-1]*np.array([[1],[-1]])
    return dict(gamma=gamma,time_each_leg=end,
        max_retrace_error=float(np.max(np.linalg.norm(zr[:2]-target,axis=0))),
        return_state=zr[:2,-1].tolist(),expected_reversed_initial=[initial[0],-initial[1]],
        end_error=float(np.linalg.norm(zr[:2,-1]-[initial[0],-initial[1]])))


def exchange_case(name,H,T=298.15,water_fraction=5e-7,a=1e-5):
    m=H*R*T;kl=2e-9/a;kg=2e-5/a
    k=3/(a*(1/kl+m/kg));b=water_fraction*m;rate=k*(1+b)
    J=np.array([[-k*b,k],[k*b,-k]])
    ts,z=integrate(lambda t,z:J@z,[1,0],10/rate,501)
    eq=b/(1+b);exact_liquid=eq*(1-np.exp(-rate*ts))
    err=float(np.max(abs(z[1]-exact_liquid)))
    return ts,z,dict(species=name,Hcp_mol_m3_Pa=H,temperature_K=T,
        water_volume_fraction=water_fraction,droplet_radius_m=a,
        jacobian_per_s=J.tolist(),eigenvalues_per_s=np.sort(np.real_if_close(np.linalg.eigvals(J))).tolist(),
        equilibrium_aqueous_percent=100*eq,relaxation_rate_per_s=rate,
        time_constant_s=1/rate,time_to_95_percent_of_equilibrium_s=np.log(20)/rate,
        max_mass_error=float(np.max(abs(z.sum(axis=0)-1))),
        max_liquid_fraction_error=err,final_aqueous_percent=100*float(z[1,-1]))


def air_mobility(a=1e-6,T=298.15,P=101325):
    # Same Sutherland and NIST2006/Kim slip closure as the earlier model.
    mu=1.8325e-5*(T/296.15)**1.5*(296.15+110.4)/(T+110.4)
    lam=67.3e-9*(mu/1.8325e-5)*(101325/P)*np.sqrt(T/296.15)
    Kn=lam/a;Cc=1+Kn*(1.165+.483*np.exp(-.997/Kn))
    return Cc/(6*np.pi*mu*a)


def charged_drag_case(sign=1,end=1,a=1e-6,s0=20e-6,charge_e=100):
    """Relative deterministic overdamped motion, with independent heat accumulator.
    Stop at 6 radii for attraction, before the point-charge near-contact limit.
    Brownian forcing disabled for this energy-identity control.
    """
    mobility=air_mobility(a)
    C=sign*KE*(charge_e*E_CHARGE)**2
    alpha=2*mobility*abs(C)/s0**3
    def rhs(t,z):
        u,loss=z
        return [sign*alpha/u**2,alpha/u**4]
    def cutoff(t,z):return z[0]-6*a/s0
    cutoff.terminal=True;cutoff.direction=-1
    sol=solve_ivp(rhs,(0,end),[1,0],method='DOP853',rtol=1e-11,atol=1e-13,
        max_step=.003,events=cutoff,dense_output=True)
    if not sol.success:raise RuntimeError(sol.message)
    ts=np.linspace(0,sol.t[-1],501);u,heat=sol.sol(ts)
    exact=np.cbrt(s0**3+6*mobility*C*ts)
    scale=abs(C)/s0
    potential_energy=sign/u*scale;heat_J=heat*scale
    balance=potential_energy+heat_J-(sign*scale)
    return ts,u*s0,potential_energy,heat_J,dict(charge_product_sign=sign,
        radius_m=a,initial_separation_m=s0,q1_e=(charge_e if sign else 0),q2_e=sign*charge_e,
        T_K=298.15,P_Pa=101325,Brownian=False,airflow_m_s=0,
        end_s=float(ts[-1]),final_separation_m=float(u[-1]*s0),
        max_separation_error_m=float(np.max(abs(u*s0-exact))),
        initial_potential_J=sign*scale,final_potential_J=float(potential_energy[-1]),
        heat_to_air_J=float(heat_J[-1]),max_energy_residual_J=float(np.max(abs(balance))),
        relative_energy_residual=float(np.max(abs(balance))/scale) if scale else 0,
        far_field_stop=bool(len(sol.t_events[0])))
