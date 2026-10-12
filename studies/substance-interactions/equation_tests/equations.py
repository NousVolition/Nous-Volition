"""Equations transcribed/reconstructed from the user's five screenshots.
No chemical identities or interaction forces are inferred from these equations.
"""
import numpy as np
from scipy.integrate import solve_ivp

HBAR=6.62607015e-34/(2*np.pi)
E_CHARGE=1.602176634e-19


def radial_exact(t,r0):
    """Forward radial flow, extended to its maximal real backward interval.
    r0=0 handled without the singular 1/r0^2 expression in screenshot1.
    """
    t=np.asarray(t,dtype=float)
    if r0<0:raise ValueError('Polar radius must be nonnegative.')
    if r0==0:return np.zeros_like(t)
    denominator=r0*r0+(1-r0*r0)*np.exp(-2*t)
    if np.any(denominator<=0):raise ValueError('Time outside finite real solution interval.')
    return r0/np.sqrt(denominator)


def cycle_cartesian(t,z):
    x,y=z;r2=x*x+y*y
    return [(1-r2)*x-y,x+(1-r2)*y]


def integrate_cycle(r0,theta0=.3,end=10,rtol=1e-10):
    times=np.linspace(0,end,1501)
    sol=solve_ivp(cycle_cartesian,(0,end),[r0*np.cos(theta0),r0*np.sin(theta0)],
        t_eval=times,method='DOP853',rtol=rtol,atol=rtol*1e-2)
    assert sol.success,sol.message
    rad=radial_exact(times,r0)
    exact=np.vstack([rad*np.cos(theta0+times),rad*np.sin(theta0+times)])
    return dict(time=times,numeric=sol.y,exact=exact,
        max_position_error=float(np.max(np.linalg.norm(sol.y-exact,axis=0))),
        final_radius=float(np.linalg.norm(sol.y[:,-1])))


def junction_parameters(alpha=.2,Ic=1e-6,C=1e-12):
    omega_p=np.sqrt(2*E_CHARGE*Ic/(HBAR*C))
    resistance=1/(alpha*C*omega_p)
    voltage_scale=HBAR*omega_p/(2*E_CHARGE)
    return dict(alpha=alpha,Ic_A=Ic,C_F=C,R_ohm=resistance,
                omega_p_rad_s=omega_p,V_scale_V=voltage_scale)


def junction(i=.5,alpha=.2,z0=(0,0),end=300,rtol=1e-10):
    """phi''+alpha phi'+sin(phi)=i. tau=omega_p t. Third state is loss.
    Energy H=.5v^2+1-cos(phi)-i*phi obeys H'=-alpha*v^2.
    """
    tt=np.linspace(0,end,6001)
    def rhs(t,z):
        phi,v,loss=z
        return [v,i-np.sin(phi)-alpha*v,alpha*v*v]
    sol=solve_ivp(rhs,(0,end),[*z0,0],t_eval=tt,method='DOP853',rtol=rtol,atol=rtol*1e-2)
    assert sol.success,sol.message
    phi,v,loss=sol.y
    energy=.5*v*v+1-np.cos(phi)-i*phi
    window=tt>=end-50
    mean_rate=(phi[-1]-phi[window][0])/(tt[-1]-tt[window][0])
    return dict(time=tt,phi=phi,v=v,loss=loss,energy=energy,
                mean_last50_rate=float(mean_rate),
                max_energy_balance_error=float(np.max(abs(energy+loss-energy[0]))))


def junction_si(i=.5,alpha=.2,z0=(0,0),end=300):
    """Independent dimensional KCL integration with voltage as state."""
    p=junction_parameters(alpha)
    wp,vs=p['omega_p_rad_s'],p['V_scale_V']
    def rhs(t,z):
        phase,voltage=z
        return [2*E_CHARGE*voltage/HBAR,
                (i*p['Ic_A']-voltage/p['R_ohm']-p['Ic_A']*np.sin(phase))/p['C_F']]
    ts=np.linspace(0,end,6001)/wp
    sol=solve_ivp(rhs,(0,end/wp),[z0[0],z0[1]*vs],t_eval=ts,
        method='DOP853',rtol=1e-10,atol=[1e-12,1e-16])
    assert sol.success,sol.message
    return dict(time_s=ts,phase=sol.y[0],voltage_V=sol.y[1],parameters=p)


def overdamped_period(i):
    """C=0 separate limit: dphi/ds=i-sin(phi), s=(2e R Ic/hbar)t."""
    if i<=1:raise ValueError('Finite rotating period requires i>1.')
    exact=2*np.pi/np.sqrt(i*i-1)
    def event(t,z):return z[0]-2*np.pi
    event.terminal=True;event.direction=1
    sol=solve_ivp(lambda t,z:[i-np.sin(z[0])],(0,2*exact),[0],events=event,
        method='DOP853',rtol=1e-11,atol=1e-13,max_step=exact/50)
    return float(sol.t_events[0][0]),exact


def clock_alignment():
    """Both hands point the same way (not opposite); t in minutes."""
    omega_min=2*np.pi/60;omega_hour=2*np.pi/720
    def event(t,z):return z[0]-z[1]-2*np.pi
    event.terminal=True;event.direction=1
    sol=solve_ivp(lambda t,z:[omega_min,omega_hour],(0,120),[0,0],events=event,
        rtol=1e-12,atol=1e-13,max_step=1)
    return float(sol.t_events[0][0])


def saddle_transit(r,cutoff=1):
    """xdot=r+x^2; stop at+cutoff, starting at-cutoff; r>0."""
    if r<=0:raise ValueError('This bottleneck transit requires r>0.')
    exact=2*np.arctan(cutoff/np.sqrt(r))/np.sqrt(r)
    def event(t,z):return z[0]-cutoff
    event.terminal=True;event.direction=1
    sol=solve_ivp(lambda t,z:[r+z[0]**2],(0,exact*1.3),[-cutoff],events=event,
        method='DOP853',rtol=1e-11,atol=1e-13,max_step=exact/50)
    return float(sol.t_events[0][0]),exact


def saddle_scaled(r):
    """x=sqrt(r)u, t=tau/sqrt(r). All r>0 collapse onto u'=1+u^2."""
    tau=np.linspace(0,2.2,501)
    sol=solve_ivp(lambda t,z:[r+z[0]**2],(0,tau[-1]/np.sqrt(r)),[-2*np.sqrt(r)],
        t_eval=tau/np.sqrt(r),method='DOP853',rtol=1e-11,atol=1e-14)
    exact=np.tan(tau-np.arctan(2))
    return tau,sol.y[0]/np.sqrt(r),exact


def oscillator(omega=1,x0=1,v0=0,periods=10,step=.02,method='DOP853'):
    end=periods*2*np.pi/omega;steps=int(np.ceil(end/step));dt=end/steps
    times=np.linspace(0,end,steps+1)
    if method=='DOP853':
        sol=solve_ivp(lambda t,z:[z[1],-omega**2*z[0]],(0,end),[x0,v0],
            t_eval=times,method=method,rtol=1e-11,atol=1e-13)
        z=sol.y
    else:
        z=np.empty((2,steps+1));z[:,0]=x0,v0
        for j in range(steps):
            x,v=z[:,j]
            if method=='Euler':z[:,j+1]=x+dt*v,v-dt*omega**2*x
            elif method=='Verlet':
                vh=v-.5*dt*omega**2*x
                xn=x+dt*vh;z[:,j+1]=xn,vh-.5*dt*omega**2*xn
            else:raise ValueError(method)
    exact=np.vstack([x0*np.cos(omega*times)+v0/omega*np.sin(omega*times),
                     -omega*x0*np.sin(omega*times)+v0*np.cos(omega*times)])
    energy=.5*(z[1]**2+omega**2*z[0]**2)
    return dict(time=times,state=z,exact=exact,energy=energy,dt=dt,
        max_position_error=float(np.max(np.abs(z[0]-exact[0]))),
        max_relative_energy_error=float(np.max(abs(energy/energy[0]-1))),
        final_energy_ratio=float(energy[-1]/energy[0]),steps=steps)
