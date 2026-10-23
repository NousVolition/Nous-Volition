"""Spatial expressed history + retained inputs + a projected clay Hug mode.

Source and extensions are specified in METHODS.md. Material-coordinate ring;
no hidden reset, no claims of measured hereditary memories or full fluid CFD.
"""
from pathlib import Path
import json
import numpy as np
from scipy.integrate import quad, solve_ivp

ROOT=Path(__file__).resolve().parent
def protocol(): return json.loads((ROOT/'protocol.json').read_text(encoding='utf-8'))

def activation(q,epsilon=1.):
    q=np.asarray(q); z=np.maximum(q,np.finfo(float).tiny)
    with np.errstate(over='ignore',under='ignore'):
        return np.where(q>0,q*np.exp(-(epsilon/z)**2),0.)

def raw_orbit(t,e,period):
    M=2*np.pi*np.asarray(t)/period; E=M.copy()
    for _ in range(9): E-=(E-e*np.sin(E)-M)/(1-e*np.cos(E))
    # Preserve the earlier Hug's signed waveform sin(2*true anomaly)/(r/a)^3.
    return 2*(np.cos(E)-e)*np.sqrt(1-e*e)*np.sin(E)/(1-e*np.cos(E))**5

def orbit_norm(e):
    return np.sqrt(quad(lambda t:float(raw_orbit(t,e,1))**2,0,1,epsabs=1e-12)[0])

def rows(p):
    return [dict(scenario=s['id'],condition=c,history=h) for s in p['scenarios'] for c in range(len(p['conditions'])) for h in range(2)]

def exposure_weights(s):
    w=np.array([s['transmission']**s['generation'],s['caregiver'],s['neighbor']],float)
    # A finite total incoming budget; retain route signs and their provenance.
    return w/max(1.,np.sum(np.abs(w)))

class Hug:
    def __init__(self,p,n,selected=None):
        self.p=p; self.n=n; self.rows=rows(p) if selected is None else selected; self.nr=len(self.rows)
        self.scenarios={s['id']:s for s in p['scenarios']}; f=p['field']; m=p['mechanics']; self.f=f;self.m=m;self.c=p['clay']
        self.theta=2*np.pi*(np.arange(n)+.5)/n; self.ds=2*np.pi*f['radius_m']/n
        # Reflection across the vertical axis; pairs preserve equal cell volume.
        self.partner=(n//2-1-np.arange(n))%n
        self.y=f['radius_m']*np.sin(self.theta); self.phi=self.y/m['length_m']
        self.upper=np.maximum(np.sin(self.theta),0.)**2
        self.upper[np.sin(self.theta)<=0]=0.
        centers=np.array([.7,2.2,4.1]); K=np.exp(f['kernel_concentration']*(np.cos(self.theta[None,:]-centers[:,None])-1))
        self.K=K/K.mean(axis=1)[:,None]
        self.w=np.array([exposure_weights(self.scenarios[r['scenario']]) for r in self.rows])
        self.sign=np.array([self.scenarios[r['scenario']]['exchange_sign'] for r in self.rows])[:,None]
        self.has_pause=np.array([self.scenarios[r['scenario']]['pause'] for r in self.rows])
        self.e=[p['conditions'][r['condition']]['e'] for r in self.rows]
        self.norm={e:orbit_norm(e) for e in set(self.e) if e is not None}
        self.Q=m['scale_m'];self.L=m['length_m'];self.V=m['volume_m3'];self.E0=(m['stiffness_N_m']+self.V*self.c['G_M_Pa']/self.L**2)*self.Q**2
        self.width=4+3+n+5
    def initial(self):
        z=np.zeros((self.nr,self.width))
        z[:,0]=[self.p['initial_displacements_scaled'][r['history']] for r in self.rows]
        return z
    def input_rate(self,t):
        out=np.zeros(3)
        for e in self.p['events']:
            if e['start_s']<=t<e['end_s']:out[e['channel']]+=e['rate_per_s']
        return out
    def exchange(self,S):
        f=self.f
        return self.sign*f['exchange_rate_per_s']*f['exchange_scale']*self.upper*(np.tanh((S[:,self.partner]-S)/f['exchange_scale']))
    def memory_force(self,S):
        grad=(np.roll(S,-1,axis=1)-np.roll(S,1,axis=1))/(2*self.ds)
        a=activation(np.abs(grad)-self.f['threshold_per_m'],self.f['epsilon_per_m'])
        # Virtual work: F_mode = integral(phi . b) dV, b=-sigma*a*e_x.
        return -self.f['response_strength_Pa']*self.V*np.mean(a*self.phi,axis=1)
    def bound(self):
        # Maximum principle: |source|<=jmax*Kmax*sum|w|; |I|<=k*s.
        f=self.f
        return (f['source_cap_per_s']*float(self.K.max())+f['exchange_rate_per_s']*f['exchange_scale'])/f['expression_relaxation_per_s']
    def rhs(self,t,z,paused=False,input_rate=None):
        z=np.asarray(z).reshape(self.nr,self.width);out=np.zeros_like(z);q,v,kstrain,mstrain=z[:,:4].T;A=z[:,4:7];S=z[:,7:7+self.n]
        f=self.f;m=self.m;c=self.c;Q=self.Q;L=self.L
        sigma=c['G_M_Pa']*(q-kstrain-mstrain)*Q/L
        out[:,0]=v;out[:,2]=(sigma-c['G_K_Pa']*kstrain*Q/L)/c['eta_K_Pa_s']*L/Q
        out[:,3]=sigma/c['eta_M_Pa_s']*L/Q
        stop=self.has_pause if paused else np.zeros(self.nr,dtype=bool)
        active=np.where(stop,0.,(m['active_gain_N_s_m']-m['active_saturation_N_s_m3']*(Q*q)**2)*Q*v)
        brake=stop*m['brake_N_s_m']*Q*v
        orbital_values={e:self.p['orbital_force_rms_N']*float(raw_orbit(t,e,self.p['orbit_period_s']))/self.norm[e] for e in self.norm}
        orbit=np.array([0. if e is None else orbital_values[e] for e in self.e])
        force=self.memory_force(S)
        out[:,1]=(active-brake+orbit+force-m['stiffness_N_m']*Q*q-self.V/L*sigma)/(m['mass_kg']*Q)
        out[:,4:7]=self.input_rate(t) if input_rate is None else input_rate
        source=(f['source_cap_per_s']*np.tanh(f['kappa_per_s']*A/f['source_cap_per_s'])*self.w)@self.K
        lap=(np.roll(S,1,axis=1)-2*S+np.roll(S,-1,axis=1))/self.ds**2
        out[:,7:7+self.n]=f['diffusivity_m2_s']*lap+source-f['expression_relaxation_per_s']*S+self.exchange(S)
        speed=Q*v
        dissip=self.V*((sigma-c['G_K_Pa']*kstrain*Q/L)**2/c['eta_K_Pa_s']+sigma**2/c['eta_M_Pa_s'])
        out[:,-5:]=np.column_stack([active*speed,orbit*speed,force*speed,brake*speed,dissip])/self.E0
        return out
    def energy(self,z):
        q,v,k,w=np.moveaxis(np.asarray(z)[...,:4],-1,0);m=self.m;c=self.c
        stress=c['G_M_Pa']*(q-k-w)*self.Q/self.L
        return (.5*m['mass_kg']*(self.Q*v)**2+.5*m['stiffness_N_m']*(self.Q*q)**2+.5*self.V*(stress**2/c['G_M_Pa']+c['G_K_Pa']*(self.Q*k/self.L)**2))/self.E0

def simulate(p,n,kind='main',selected=None):
    model=Hug(p,n,selected);z=model.initial()
    regular=np.arange(0,p['horizon_s']+p['sample_s']/2,p['sample_s'])
    strobe=np.arange(0,p['horizon_s']+1e-8,p['orbit_period_s'])
    times=np.unique(np.round(np.r_[regular,strobe],10));saved=np.empty((len(times),model.nr,model.width));saved[0]=z
    boundaries=sorted(set([0,p['horizon_s'],*p['pause_s'],*[e[k] for e in p['events'] for k in ('start_s','end_s')]]))
    discontinuities=[]; num=p['numerics'];start_state=z.copy()
    for a,b in zip(boundaries[:-1],boundaries[1:]):
        erased=[]
        if a==p['pause_s'][1]:
            for j,r in enumerate(model.rows):
                if model.scenarios[r['scenario']]['erase']:
                    erased.append(dict(row=j,A_before=z[j,4:7].tolist(),S_rms_before=float(np.sqrt(np.mean(z[j,7:7+n]**2)))))
                    z[j,4:7+n]=0.
            if erased:discontinuities.append(dict(time_s=a,erased=erased))
            saved[np.searchsorted(times,a)]=z
        paused=p['pause_s'][0]<=a<p['pause_s'][1]
        rate=model.input_rate((a+b)/2)
        idx=np.where((times>a)&(times<=b))[0]
        sol=solve_ivp(lambda t,y:model.rhs(t,y,paused,rate).ravel(),(a,b),z.ravel(),method='DOP853',rtol=num[kind+'_rtol'],atol=num[kind+'_atol'],max_step=num[kind+'_max_step_s'],t_eval=times[idx])
        if not sol.success:raise RuntimeError(sol.message)
        block=sol.y.T.reshape(len(idx),model.nr,model.width);saved[idx]=block;z=block[-1].copy()
        print(f'{kind}: {a:g}–{b:g} s, {model.nr} paths, {n} cells',flush=True)
    return model,times,saved,discontinuities
