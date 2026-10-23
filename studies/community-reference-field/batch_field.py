"""Batched numerical implementation of the unchanged coupled corpus PDEs.

Batch axis labels independent episodes, not an extra physical dimension.
"""
from pathlib import Path
import sys
import numpy as np
P=Path(__file__).parent
sys.path.insert(0,str(P.parent/('community_full_field' if (P.parent/'community_full_field').exists() else 'community-full-field')))
from field import Field,Parameters,activation

class BatchField:
    def __init__(self,episodes,p):
        self.episodes=episodes;self.p=p;self.base=Field(p);self.n=p.n;self.b=len(episodes)
        self.kx=self.base.kx;self.ky=self.base.ky;self.k2=self.base.k2;self.mask=self.base.mask
        self.targets=np.stack([[self.observed(points) for points in e['points']] for e in episodes])
        self.kh=np.stack([self.fft(self.kernel(np.mean(e['points'][0],axis=0))) for e in episodes])*self.mask
    def fft(self,z):return np.fft.fft2(z,axes=(-2,-1))
    def real(self,z):return np.fft.ifft2(z,axes=(-2,-1)).real
    def kernel(self,point):
        K=np.exp((np.cos(2*np.pi*(self.base.x-point[0]))+np.cos(2*np.pi*(self.base.y-point[1]))-2)/(2*np.pi*self.p.h)**2)
        return K/K.mean()
    def observed(self,points):
        return self.real(self.fft(sum(self.kernel(x) for x in points))*self.mask)
    def grad(self,z):return self.real(1j*np.array([self.kx,self.ky])[:,None]*z[None])
    def project(self,z):
        dot=self.kx*z[0]+self.ky*z[1];c=np.divide(dot,self.k2,out=np.zeros_like(dot),where=self.k2!=0)
        return (z-np.array([self.kx,self.ky])[:,None]*c[None])*self.mask
    def terms(self,z,A):
        p=self.p;u=self.real(z[:2]);gs=self.grad(z[2]);gu=np.array([self.grad(z[i]) for i in range(2)])
        adv=np.einsum('jbxy,ijbxy->ibxy',u,gu);q=np.sqrt(np.sum(gs*gs,axis=0))-p.threshold
        f=-(p.sigma/p.rho)*np.asarray(p.direction)[:,None,None,None]*activation(q,p.law,p.epsilon)
        b=self.fft(-adv+f)*self.mask;du=self.project(b)-p.nu*self.k2*z[:2]
        ds=(-self.fft(np.sum(u*gs,axis=0))+p.kappa*A[:,None,None]*self.kh)*self.mask-p.diffusivity*self.k2*z[2]
        ph=np.divide(-1j*(self.kx*b[0]+self.ky*b[1]),self.k2,out=np.zeros_like(z[2]),where=self.k2!=0)
        return np.concatenate([du,ds[None]]),ph,u,gu,f
    def step(self,z,A,U,dt):
        da=self.p.gamma*(U-self.p.baseline);h=dt[None,:,None,None]
        k1=self.terms(z,A)[0];k2=self.terms(z+.5*h*k1,A+.5*dt*da)[0]
        k3=self.terms(z+.5*h*k2,A+.5*dt*da)[0];k4=self.terms(z+h*k3,A+dt*da)[0]
        out=(z+h*(k1+2*k2+2*k3+k4)/6)*self.mask;out[:2]=self.project(out[:2]);return out,A+dt*da
    def run(self,max_dt=.005):
        z=np.zeros((3,self.b,self.n,self.n),complex);z[2]=self.fft(self.targets[:,0]);A=np.zeros(self.b)
        rows=[];states=[];M=np.array([e['counts'][0] for e in self.episodes],float)
        cap=.45/(max(self.p.nu,self.p.diffusivity)*self.k2[self.mask].max());dtmax=min(max_dt,cap)
        for j in range(2):
            duration=np.array([e['dt'][j] for e in self.episodes]);U=np.array([e['U'][j] for e in self.episodes]);steps=max(1,int(np.ceil(duration.max()/dtmax)));dt=duration/steps
            M+=self.p.kappa*(A*duration+.5*self.p.gamma*(U-self.p.baseline)*duration**2)
            for _ in range(steps):
                z,A=self.step(z,A,U,dt)
                if not np.isfinite(z).all():raise FloatingPointError('Nonfinite trajectory')
            zz=self.real(z);dz,ph,u,gu,f=self.terms(z,A);dE=np.mean(np.sum(u*self.real(dz[:2]),axis=0),axis=(-2,-1));diss=self.p.nu*np.mean(np.sum(gu*gu,axis=(0,1)),axis=(-2,-1));work=np.mean(np.sum(u*f,axis=0),axis=(-2,-1))
            div=self.real(1j*(self.kx*z[0]+self.ky*z[1]));T=self.p.rho*self.p.nu*(gu+gu.swapaxes(0,1))
            for i,e in enumerate(self.episodes):
                err=zz[2,i]-self.targets[i,j+1]
                rows.append(dict(case=e['case'],scenario=e['scenario'],split=e['split'],step=j+1,mse=float(np.mean(err**2)),shape_mse=float(np.mean((err-err.mean())**2)),mass=float(zz[2,i].mean()),target_mass=e['counts'][j+1],mass_exact=float(M[i]),mass_error=float(zz[2,i].mean()-M[i]),divergence=float(np.sqrt(np.mean(div[i]**2))),energy_identity=float(dE[i]+diss[i]-work[i]),energy=float(.5*np.mean(np.sum(u[:,i]**2,axis=0))),work=float(work[i]),dissipation=float(diss[i]),pressure_rms=float(np.sqrt(np.mean(self.real(ph[i])**2))),stress_rms=float(np.sqrt(np.mean(T[:,:,i]**2))),S_min=float(zz[2,i].min()),dt=float(dt[i]),steps=steps))
            states.append(zz.copy())
        return rows,np.array(states),self.targets
