"""Deformation-aware angular projection of the supplied transport/source laws.

See METHODS.md for the pullback, the explicit angular-field approximation,
the unchanged source extensions, and the distinction between S and the record A.
"""
import json
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from baseline import Hug as FixedHug,activation,raw_orbit,orbit_norm,exposure_weights,rows
ROOT=Path(__file__).resolve().parent
def protocol():return json.loads((ROOT/'protocol.json').read_text())

def metric(theta,gamma):
    """|F^{-T} t|^2 for F=[[1,gamma],[0,1]], t=(-sin(theta),cos(theta))."""
    return 1+gamma*np.sin(2*theta)+gamma**2*np.sin(theta)**2

class Hug(FixedHug):
    def __init__(self,p,n,selected=None):
        super().__init__(p,n,selected)
        self.diff_move=np.array([self.scenarios[r['scenario']]['moving_diffusion'] for r in self.rows])
        self.grad_move=np.array([self.scenarios[r['scenario']]['moving_gradient'] for r in self.rows])
        self.faces=2*np.pi*(np.arange(n)+1)/n
    def diffusion(self,S,gamma):
        # Flux at every face; a shared flux cancels across its two adjacent cells.
        g=metric(self.faces[None,:],np.asarray(gamma)[:,None])
        flux=self.f['diffusivity_m2_s']*g*(np.roll(S,-1,axis=1)-S)/self.ds
        return (flux-np.roll(flux,1,axis=1))/self.ds
    def deformed_force(self,S,gamma):
        grad=(np.roll(S,-1,axis=1)-np.roll(S,1,axis=1))/(2*self.ds)
        norm=np.abs(grad)*np.sqrt(metric(self.theta[None,:],np.asarray(gamma)[:,None]))
        a=activation(norm-self.f['threshold_per_m'],self.f['epsilon_per_m'])
        return -self.f['response_strength_Pa']*self.V*np.mean(a*self.phi,axis=1)
    def rhs(self,t,z,paused=False,input_rate=None):
        z=np.asarray(z).reshape(self.nr,self.width)
        out=super().rhs(t,z,paused,input_rate)
        S=z[:,7:7+self.n];gamma=z[:,0]*self.Q/self.L
        old_lap=self.f['diffusivity_m2_s']*(np.roll(S,1,axis=1)-2*S+np.roll(S,-1,axis=1))/self.ds**2
        out[:,7:7+self.n]+=self.diffusion(S,gamma*self.diff_move)-old_lap
        delta=self.deformed_force(S,gamma*self.grad_move)-self.memory_force(S)
        out[:,1]+=delta/(self.m['mass_kg']*self.Q)
        out[:,-3]+=delta*(self.Q*z[:,1])/self.E0
        return out

def simulate(p,n,accuracy='main',selected=None):
    m=Hug(p,n,selected);z=m.initial();num=p['numerics']
    times=np.unique(np.round(np.r_[np.arange(0,p['horizon_s']+.25,p['sample_s']),np.arange(0,p['horizon_s']+1e-8,p['orbit_period_s'])],10))
    saved=np.empty((len(times),m.nr,m.width));saved[0]=z
    bounds=sorted(set([0,p['horizon_s'],*p['pause_s'],*[e[k] for e in p['events'] for k in ['start_s','end_s']]]))
    for a,b in zip(bounds[:-1],bounds[1:]):
        paused=p['pause_s'][0]<=a<p['pause_s'][1];rate=m.input_rate((a+b)/2)
        ids=np.flatnonzero((times>a)&(times<=b))
        sol=solve_ivp(lambda t,y:m.rhs(t,y,paused,rate).ravel(),(a,b),z.ravel(),method='DOP853',rtol=num[accuracy+'_rtol'],atol=num[accuracy+'_atol'],max_step=num[accuracy+'_max_step_s'],t_eval=times[ids])
        if not sol.success:raise RuntimeError(sol.message)
        saved[ids]=sol.y.T.reshape(len(ids),m.nr,m.width);z=saved[ids[-1]].copy()
        print(f'{n} cells / {accuracy}: {a:g}–{b:g} s, {m.nr} paths',flush=True)
    return m,times,saved
