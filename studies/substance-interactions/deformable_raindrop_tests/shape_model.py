"""One-mode liquid deformation, derived from volume, kinetic and surface energy.

SI throughout. The gas lookup is a quasi-steady approximation, not a moving
interface fluid solver. No empirical equilibrium shape or drag correlation.
"""
from pathlib import Path
import json
import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import least_squares

P=Path(__file__).resolve().parent
MAT=json.loads((P/'protocol.json').read_text())['material_20C']
U,W=np.polynomial.legendre.leggauss(64)

def geometry(s,diameter):
    R=diameter/2
    return R*np.exp(2*s/3),R*np.exp(-s/3)

def mechanics(s,diameter,mu=None,sigma=None):
    a,b=geometry(s,diameter);V=np.pi*diameter**3/6;m=MAT['rho_water_kg_m3']*V
    mu=MAT['mu_water_Pa_s'] if mu is None else mu
    sigma=MAT['surface_tension_N_m'] if sigma is None else sigma
    A=a*a*(1-U*U)+b*b*U*U;dA=(4*a*a*(1-U*U)-2*b*b*U*U)/3
    S=2*np.pi*b*np.dot(W,np.sqrt(A))
    dS=2*np.pi*b*np.dot(W,-np.sqrt(A)/3+dA/(2*np.sqrt(A)))
    M=m*(4*a*a+2*b*b)/45
    Mp=m*(16*a*a-4*b*b)/135
    damping=4*mu*V/3
    return M,Mp,sigma*S,sigma*dS,damping

def evolve(diameter,load=lambda s,t:0.,initial=(0.02,0.),duration=.3,dt=1e-5,mu=None,sigma=None):
    # Integral states track aerodynamic work and viscous loss independently.
    def rhs(t,y):
        s,v=y[:2];M,Mp,E,dE,C=mechanics(s,diameter,mu,sigma)
        Q=load(s,t)
        return [v,(Q-dE-C*v-.5*Mp*v*v)/M,Q*v,C*v*v]
    n=int(np.ceil(duration/dt));times=np.linspace(0,duration,n+1)
    sol=solve_ivp(rhs,[0,duration],[*initial,0,0],t_eval=times,max_step=dt,
                  method='DOP853',rtol=1e-9,atol=1e-12)
    if not sol.success:raise RuntimeError(sol.message)
    E=np.array([.5*mechanics(s,diameter,mu,sigma)[0]*v*v+mechanics(s,diameter,mu,sigma)[2]
                for s,v in sol.y[:2].T])
    residual=E-E[0]-sol.y[2]+sol.y[3]
    return np.column_stack((sol.t,sol.y[:2].T,np.exp(sol.y[0]),E,sol.y[2:].T,residual))

class GasLibrary:
    def __init__(self,rows,cd_scale=1.,cq_scale=1.):
        self.re=np.array(sorted(set(x['Re'] for x in rows)))
        self.aspect=np.array(sorted(set(x['aspect'] for x in rows)))
        cd=np.full((len(self.re),len(self.aspect)),np.nan);cq=cd.copy()
        for row in rows:
            i=np.where(self.re==row['Re'])[0][0];j=np.where(self.aspect==row['aspect'])[0][0]
            cd[i,j]=row['Cd']*cd_scale;cq[i,j]=row['Cq']*cq_scale
        if not np.isfinite(cd).all():raise ValueError('Incomplete rectangular gas library')
        self.cd=RegularGridInterpolator((self.re,self.aspect),cd,bounds_error=True)
        self.cq=RegularGridInterpolator((self.re,self.aspect),cq,bounds_error=True)

    def forces(self,diameter,speed,s):
        re=speed*diameter/MAT['nu_air_m2_s'];aspect=np.exp(s)
        p=np.array([[re,aspect]])
        cd=float(self.cd(p)[0]);cq=float(self.cq(p)[0]);a,b=geometry(s,diameter)
        drag=.5*MAT['rho_air_kg_m3']*speed**2*np.pi*b*b*cd
        load=MAT['rho_air_kg_m3']*speed**2*diameter**3*cq
        return drag,load

    def terminal(self,diameter):
        weight=(MAT['rho_water_kg_m3']-MAT['rho_air_kg_m3'])*np.pi*diameter**3/6*MAT['g_m_s2']
        cap=MAT['surface_tension_N_m']*diameter**2
        def residual(x):
            speed,s=x;drag,load=self.forces(diameter,speed,s)
            return [(drag-weight)/weight,(mechanics(s,diameter)[3]-load)/cap]
        bounds=([self.re[0]*MAT['nu_air_m2_s']/diameter,np.log(self.aspect[0])],
                [self.re[-1]*MAT['nu_air_m2_s']/diameter,np.log(self.aspect[-1])])
        x0=np.mean(bounds,axis=0)
        sol=least_squares(residual,x0,bounds=bounds,xtol=1e-12,ftol=1e-12,gtol=1e-12)
        error=float(np.max(np.abs(residual(sol.x))))
        return dict(diameter_mm=diameter*1000,speed_m_s=float(sol.x[0]),aspect=float(np.exp(sol.x[1])),
                    Re=float(sol.x[0]*diameter/MAT['nu_air_m2_s']),balance_error=error,
                    status='root_inside_library' if error<1e-5 else 'no_balanced_root_in_library')
