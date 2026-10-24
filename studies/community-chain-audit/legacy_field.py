"""Coupled P229/230, P517/518 on a specified periodic 2D domain.

No fitted social geometry. Fourier Galerkin spatial approximation + RK4 time.
Pressure is the Helmholtz projection multiplier, with spatial mean zero.
"""
from dataclasses import dataclass, asdict
import numpy as np
from scipy.special import expit

@dataclass(frozen=True)
class Parameters:
    n:int=24
    nu:float=.02
    diffusivity:float=.01
    rho:float=1.
    sigma:float=.1
    threshold:float=.05
    epsilon:float=.1
    h:float=.12
    gamma:float=1.
    kappa:float=1.
    baseline:float=0.
    law:str='sharp'
    direction:tuple=(1.,0.)

def activation(q,law,epsilon):
    if epsilon<=0:raise ValueError('epsilon must be positive')
    if law=='sharp':return np.maximum(q,0)
    if law=='tanh':return q*expit(2*q/epsilon)
    if law=='smooth_off':
        out=np.zeros_like(q);pos=q>0
        with np.errstate(over='ignore',under='ignore'):out[pos]=q[pos]*np.exp(-(epsilon/q[pos])**2)
        return out
    raise ValueError(law)

class Field:
    def __init__(self,p=Parameters()):
        self.p=p;n=p.n
        if n<12 or n%2 or p.nu<=0 or p.diffusivity<0 or p.rho<=0 or p.sigma<0 or p.threshold<0 or p.h<=0:raise ValueError('Invalid parameters')
        if not np.isclose(np.linalg.norm(p.direction),1):raise ValueError('Unit direction required')
        m=np.rint(np.fft.fftfreq(n)*n).astype(int);self.kx,self.ky=np.meshgrid(2*np.pi*m,2*np.pi*m,indexing='ij')
        self.k2=self.kx**2+self.ky**2
        mx,my=np.meshgrid(m,m,indexing='ij');self.mask=(3*np.abs(mx)<n)&(3*np.abs(my)<n)
        x=np.arange(n)/n;self.x,self.y=np.meshgrid(x,x,indexing='ij')
        K=np.exp((np.cos(2*np.pi*(self.x-.5))+np.cos(2*np.pi*(self.y-.5))-2)/(2*np.pi*p.h)**2)
        self.K=K/K.mean();self.kh=self.fft(self.K)*self.mask
    def fft(self,z):return np.fft.fft2(z,axes=(-2,-1))
    def real(self,z):return np.fft.ifft2(z,axes=(-2,-1)).real
    def gradient(self,z):return self.real(1j*np.array([self.kx,self.ky])*z)
    def project(self,v):
        dot=self.kx*v[0]+self.ky*v[1]
        c=np.divide(dot,self.k2,out=np.zeros_like(dot),where=self.k2!=0)
        return (v-np.array([self.kx,self.ky])*c)*self.mask
    def initial(self,total=0.,texture=.04,speed=.1):
        x,y=2*np.pi*self.x,2*np.pi*self.y
        u=speed*np.array([np.sin(x)*np.cos(y),-np.cos(x)*np.sin(y)])
        S=total+texture*np.cos(x)*np.cos(y)
        return np.concatenate([self.project(self.fft(u)),self.fft(S)[None]*self.mask]),0.
    def terms(self,z,A):
        p=self.p;u=self.real(z[:2]);gs=self.gradient(z[2])
        gu=np.array([self.gradient(z[i]) for i in range(2)])
        # gu[i,j] = derivative of component i in direction j.
        adv_u=np.einsum('jxy,ijxy->ixy',u,gu)
        adv_s=np.sum(u*gs,axis=0)
        q=np.sqrt(np.sum(gs*gs,axis=0))-p.threshold
        force=-(p.sigma/p.rho)*np.asarray(p.direction)[:,None,None]*activation(q,p.law,p.epsilon)
        b=self.fft(-adv_u+force)*self.mask
        du=self.project(b)-p.nu*self.k2*z[:2]
        ds=(-self.fft(adv_s)+p.kappa*A*self.kh)*self.mask-p.diffusivity*self.k2*z[2]
        # div(b-grad(p))=0 -> p_hat=-i*k.b_hat/|k|^2.
        ph=np.divide(-1j*(self.kx*b[0]+self.ky*b[1]),self.k2,out=np.zeros_like(z[2]),where=self.k2!=0)
        return np.concatenate([du,ds[None]]),ph,u,gu,force
    def step(self,z,A,U,dt):
        da=self.p.gamma*(U-self.p.baseline)
        k1=self.terms(z,A)[0];k2=self.terms(z+.5*dt*k1,A+.5*dt*da)[0]
        k3=self.terms(z+.5*dt*k2,A+.5*dt*da)[0];k4=self.terms(z+dt*k3,A+dt*da)[0]
        out=(z+dt*(k1+2*k2+2*k3+k4)/6)*self.mask
        # Remove floating point divergence only; keep velocity zero mode.
        out[:2]=self.project(out[:2])
        return out,A+dt*da
    def diagnostics(self,z,A):
        dz,ph,u,gu,f=self.terms(z,A);S=self.real(z[2]);du=self.real(dz[:2])
        div=self.real(1j*(self.kx*z[0]+self.ky*z[1]))
        visc=self.p.nu*np.mean(np.sum(gu*gu,axis=(0,1)))
        work=np.mean(np.sum(u*f,axis=0));dE=np.mean(np.sum(u*du,axis=0))
        T=self.p.rho*self.p.nu*(gu+gu.swapaxes(0,1))
        return dict(A=float(A),mass=float(S.mean()),energy=float(.5*np.mean(np.sum(u*u,axis=0))),
                    velocity_rms=float(np.sqrt(np.mean(np.sum(u*u,axis=0)))),divergence_rms=float(np.sqrt(np.mean(div*div))),
                    work=float(work),viscous_dissipation=float(visc),energy_rate=float(dE),
                    energy_identity_residual=float(dE+visc-work),pressure_rms=float(np.sqrt(np.mean(self.real(ph)**2))),
                    stress_rms=float(np.sqrt(np.mean(T*T))),S_min=float(S.min()),S_max=float(S.max()))
    def run(self,inputs,initial_total=0.,dt=.004,interval=1.,texture=.04,speed=.1,keep=False):
        z,A=self.initial(initial_total,texture,speed);M=initial_total;rows=[];states=[]
        # Conservative RK4 diffusion cap; temporal refinement checks these runs.
        cap=.45/(max(self.p.nu,self.p.diffusivity)*max(1.,float(self.k2[self.mask].max())))
        nsteps=int(np.ceil(interval/min(dt,cap)));h=interval/nsteps
        for j,U in enumerate(inputs):
            oldA=A;M+=self.p.kappa*(oldA*interval+.5*self.p.gamma*(U-self.p.baseline)*interval**2)
            for _ in range(nsteps):
                z,A=self.step(z,A,U,h)
                if not np.all(np.isfinite(z)):raise FloatingPointError('Nonfinite field')
            d=self.diagnostics(z,A);d.update(time=(j+1)*interval,mass_exact=float(M),mass_error=float(d['mass']-M),dt=h,steps=nsteps)
            rows.append(d)
            if keep:states.append(self.real(z).copy())
        return rows,z,states
