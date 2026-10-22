"""Old clay oscillator plus a declared realization of evolving directional guards.

Scaled state: q/Q, qdot/Q, Kelvin strain/(Q/L), Maxwell strain/(Q/L),
abstract x_A, x_B, g_AB (A receives B), g_BA. Time is simulation seconds.
The added stress is purely dissipative. Work counters are normalized mechanical
energy; abstract x/g have no assigned mechanical storage.
"""
from pathlib import Path
import json, sys
import numpy as np
from scipy.special import expit
ROOT=Path(__file__).resolve().parent
PARENT=ROOT.parent/'dynamics-fractals-sims'
sys.path.insert(0,str(PARENT))
from active_hug import raw_tide, tide_rms

LABELS={'old':'Old Hug','directional':'Updated: directional guards','A_receives_more':'Updated: B to A stronger','B_receives_more':'Updated: A to B stronger','shared':'Shared evolving guard','frozen':'Frozen guards','no_strain':'Strain feedback off','feedback_off':'Active energy source off'}

def protocol():return json.loads((ROOT/'protocol.json').read_text(encoding='utf-8'))

def cases(p):
    return [dict(model=m,condition=c,start=s) for m in p['models'] for c in range(len(p['conditions'])) for s in range(len(p['starts_scaled']))]

class Ensemble:
    def __init__(self,p,rows):
        self.p=p;self.rows=rows;self.n=len(rows)
        mat=p['material'];mech=p['mechanics'];fb=p['feedback'];g=p['guard']
        self.gm=mat['G_M_Pa'];self.gk=mat['G_K_Pa'];self.em=mat['eta_M_Pa_s'];self.ek=mat['eta_K_Pa_s']
        self.mass=mech['effective_mass_kg'];self.k=mech['parallel_stiffness_N_m'];self.Q=p['displacement_scale_m'];self.L=p['length_m'];self.V=p['volume_m3']
        self.ck=self.V*self.gm/self.L**2;self.E0=(self.k+self.ck)*self.Q**2
        self.old=np.array([r['model']=='old' for r in rows]);self.frozen=np.array([r['model']=='frozen' for r in rows]);self.shared=np.array([r['model']=='shared' for r in rows])
        self.gain=np.array([0 if r['model']=='feedback_off' else fb['gain_N_s_m'] for r in rows])
        self.sat=np.array([0 if r['model']=='feedback_off' else fb['saturation_N_s_m3'] for r in rows])*self.Q**2
        self.c=g['damping_per_guard_N_s_m']*(~self.old)
        self.chi=np.array([0 if r['model']=='no_strain' else g['chi'] for r in rows])
        self.ka=np.array([1.5 if r['model']=='A_receives_more' else .5 if r['model']=='B_receives_more' else 1 for r in rows])
        self.kb=2-self.ka;self.cond=np.array([r['condition'] for r in rows])
        self.rms=np.array([1 if x['e'] is None else tide_rms(x['e']) for x in p['conditions']])

    def start(self):
        z=np.array([self.p['starts_scaled'][r['start']] for r in self.rows],float)
        z[self.old,4:]=0;z[self.frozen,6:]=.5
        return z

    def force(self,t):
        p=self.p
        f=np.array([0. if x['e'] is None else float(raw_tide(t/p['orbit_period_s'],x['e']))/r for x,r in zip(p['conditions'],self.rms)])
        return p['orbital_force_rms_N']*f[self.cond]

    def rhs(self,t,z,force=None):
        q,v,u,w,A,B,ga,gb=z[:,:8].T;g=self.p['guard'];d=B-A
        s=q-u-w;du=(self.gm*s-self.gk*u)/self.ek;dw=self.gm*s/self.em
        active=(self.gain-self.sat*q*q)*v;drag=self.c*(ga+gb)
        F=self.force(t) if force is None else np.asarray(force)
        out=np.zeros_like(z)
        out[:,0]=v;out[:,1]=(-self.k*q-self.ck*s+active-drag*v+F/self.Q)/self.mass
        out[:,2]=du;out[:,3]=dw
        out[:,4]=g['lambda_per_s']*(g['baselines'][0]-A)+self.ka*ga*d
        out[:,5]=g['lambda_per_s']*(g['baselines'][1]-B)-self.kb*gb*d
        strain=.5*(v*g['rate_reference_s'])**2
        target=np.column_stack([expit(g['theta']+g['beta']*d+self.chi*strain),expit(g['theta']-g['beta']*d+self.chi*strain)])
        target[self.shared]=target[self.shared].mean(axis=1,keepdims=True)
        out[:,6:8]=(target-z[:,6:8])/g['tau_s']
        out[self.frozen,6:8]=0;out[self.old,4:8]=0
        if z.shape[1]==12:
            speed=self.Q*v;sigma=self.gm*self.Q/self.L*s
            out[:,8]=active*self.Q*speed/self.E0
            out[:,9]=F*speed/self.E0
            out[:,10]=self.V*((sigma-self.gk*u*self.Q/self.L)**2/self.ek+sigma*sigma/self.em)/self.E0
            out[:,11]=drag*speed*speed/self.E0
        return out

    def energy(self,z):
        q,v,u,w=np.moveaxis(np.asarray(z)[...,:4],-1,0);sigma=self.gm*self.Q/self.L*(q-u-w)
        return (.5*self.mass*(self.Q*v)**2+.5*self.k*(self.Q*q)**2+.5*self.V*(sigma*sigma/self.gm+self.gk*(self.Q/self.L*u)**2))/self.E0

def physical_rhs(p,row):
    """Independent scalar equations in metres, m/s and physical clay strains."""
    import math
    mat=p['material'];g=p['guard'];fb=p['feedback'];mc=p['mechanics']
    old=row['model']=='old';frozen=row['model']=='frozen';off=row['model']=='feedback_off';shared=row['model']=='shared'
    ka,kb=(1.5,.5) if row['model']=='A_receives_more' else (.5,1.5) if row['model']=='B_receives_more' else (1.,1.)
    Q=p['displacement_scale_m'];L=p['length_m'];V=p['volume_m3'];e=p['conditions'][row['condition']]['e'];norm=1 if e is None else tide_rms(e)
    def sigmoid(x):return .5*(1+math.tanh(x/2))
    def fun(t,y):
        q,v,u,w,A,B,ga,gb=y;sigma=mat['G_M_Pa']*(q/L-u-w)
        F=0 if e is None else p['orbital_force_rms_N']*float(raw_tide(t/p['orbit_period_s'],e))/norm
        active=0 if off else (fb['gain_N_s_m']-fb['saturation_N_s_m3']*q*q)*v
        drag=0 if old else g['damping_per_guard_N_s_m']*(ga+gb)*v
        dq=v;dv=(F+active-drag-mc['parallel_stiffness_N_m']*q-V/L*sigma)/mc['effective_mass_kg']
        du=(sigma-mat['G_K_Pa']*u)/mat['eta_K_Pa_s'];dw=sigma/mat['eta_M_Pa_s']
        if old:return [dq,dv,du,dw,0,0,0,0]
        d=B-A;chi=0 if row['model']=='no_strain' else g['chi']
        strain=.5*(v/Q*g['rate_reference_s'])**2
        ta=sigmoid(g['theta']+g['beta']*d+chi*strain);tb=sigmoid(g['theta']-g['beta']*d+chi*strain)
        if shared:ta=tb=(ta+tb)/2
        return [dq,dv,du,dw,g['lambda_per_s']*(g['baselines'][0]-A)+ka*ga*d,g['lambda_per_s']*(g['baselines'][1]-B)-kb*gb*d,0 if frozen else (ta-ga)/g['tau_s'],0 if frozen else (tb-gb)/g['tau_s']]
    return fun

def physical_scale(p):
    Q=p['displacement_scale_m'];return np.array([Q,Q,Q/p['length_m'],Q/p['length_m'],1,1,1,1])
