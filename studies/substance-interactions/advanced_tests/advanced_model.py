"""Transport/kinetics extensions; see METHODS.md for validity boundaries.

Concentrations for carbonate are mol/L; other computations use SI units.
No fit to the 18 collection observations is made in this module.
"""
from dataclasses import dataclass
import numpy as np
from scipy.integrate import solve_ivp, quad
from scipy.optimize import brentq
from baseline_model import R, KB, E, KE, EPS0, henry, mobility
from followup_model import interface, vapor_density, SPECIES, H298, SLOPES


def carbonate_constants(scale_water=1., scale_oh=1.):
    """Wang2010 Table1, 25 C. Detailed balance repairs only table rounding.

    kH=.037/s; krH=24.8/s; kOH=12100 L/(mol s); krOH=.00040/s.
    Derive true H2CO3 Ka so the two routes share equilibrium exactly.
    This is a dilute ideal-activity model; no buffers or carbonic anhydrase.
    """
    kh, krh, ko, kro, kw = .037, 24.8, 12100., .0004, 1e-14
    ktrue = (ko * kw / kro) / (kh / krh)
    return dict(kh=kh*scale_water, krh=krh*scale_water,
                ko=ko*scale_oh, kro=kro*scale_oh,
                ka=ktrue, kb=10**-10.33, kw=kw)


def speciate_hydrated(B, alkalinity, k=None):
    """B = H2CO3 + HCO3- + CO3--, excluding CO2(aq). mol/L.
    Fast proton transfer equilibrates at EACH kinetic RHS evaluation.
    """
    if k is None: k = carbonate_constants()
    B = max(float(B), 0.)
    def values(logH):
        H=10.**logH
        den=H*H+k['ka']*H+k['ka']*k['kb']
        return H, B*H*H/den, B*k['ka']*H/den, B*k['ka']*k['kb']/den
    def balance(logH):
        H, acid, bic, carb=values(logH)
        return bic+2*carb+k['kw']/H-H-alkalinity
    logH=brentq(balance,-16.,0.,xtol=1e-13)
    H, acid, bic, carb=values(logH)
    return dict(H=H, OH=k['kw']/H, acid=acid, bic=bic, carb=carb, pH=-logH)


def carbonate_run(alkalinity=0., carbon=2e-4, hydrated_initial=0.,
                  end=300., max_step=1., rtol=1e-9,
                  water_scale=1., oh_scale=1.):
    """Closed liquid with injected dissolved CO2; no gas transfer.
    Ideal-dilute cases only (0--0.2 mmol/L alkalinity, 0.2 mmol/L carbon).
    Independent integrated CO2 and hydrated-pool inventories audit carbon.
    """
    k=carbonate_constants(water_scale, oh_scale)
    def rates(y):
        s=speciate_hydrated(y[1], alkalinity, k)
        rh=k['kh']*y[0]-k['krh']*s['acid']
        ro=k['ko']*y[0]*s['OH']-k['kro']*s['bic']
        return rh,ro
    def rhs(t,y):
        rh,ro=rates(y);return [-rh-ro,rh+ro,rh,ro]
    z=solve_ivp(rhs,(0,end),[carbon-hydrated_initial,hydrated_initial,0.,0.],
        method='Radau',rtol=rtol,atol=1e-14,max_step=max_step,dense_output=True)
    if not z.success: raise RuntimeError(z.message)
    ts=np.r_[0.,np.geomspace(1e-5,end,499)]; y=z.sol(ts)
    ss=[speciate_hydrated(b,alkalinity,k) for b in y[1]]
    return dict(t=ts,y=y,pH=np.array([s['pH'] for s in ss]),
                acid=np.array([s['acid'] for s in ss]),
                bic=np.array([s['bic'] for s in ss]),carb=np.array([s['carb'] for s in ss]),
                carbon_error=float(np.max(abs(y[0]+y[1]-carbon))/carbon),constants=k)


def water_history(A0=1e-5,T=298.15,RH=.9,LWC=.0005,end=10.,evaporate=True):
    """Dense geometry history shared by radial and well-mixed controls.
    Closed 1 m3 vapor reservoir; droplet sensible heat still quasi-steady.
    """
    def properties(u):
        u=max(float(u),1e-8);A=A0*np.sqrt(u)
        evap=LWC*(1-u**1.5)
        if not evaporate: return A,0.,T
        Td,flux,_=interface(T,RH*vapor_density(T)+evap,A)
        return A,-flux/(1000*A),Td
    def rhs(t,y):
        A,Ad,Td=properties(y[0]);return [2*A*Ad/A0**2]
    def cutoff(t,y): return y[0]-(2e-6/A0)**2
    cutoff.terminal=True;cutoff.direction=-1
    z=solve_ivp(rhs,(0,end),[1.],events=cutoff,method='Radau',rtol=1e-10,
                atol=1e-12,max_step=.05,dense_output=True)
    if not z.success:raise RuntimeError(z.message)
    return dict(end=z.t[-1],at=lambda t:properties(z.sol(t)[0]),
                number=LWC/(1000*4*np.pi*A0**3/3),solution=z,A0=A0,T=T)


def radial_uptake(history, species=1, cells=40, Dl=2e-9,Dg=2e-5,
                  alpha=1.,exchange=True,initial_liquid=0.,max_step=.03,rtol=2e-8):
    """Conservative moving-shell finite-volume liquid diffusion + finite gas.
    State normalized by the initial total solute inventory. Gas volume 1 m3.
    Geometry moves inward with evaporation; liquid bulk velocity is zero.
    Robin condition includes moving-surface flux, not an imposed film k_l.
    """
    edges=np.linspace(0,1,cells+1);centres=(edges[:-1]+edges[1:])/2
    weights=4*np.pi/3*np.diff(edges**3);N=history['number'];T=history['T']
    molar_mass=[.0280101,.05808,.06812,.0340147][species]
    cbar=np.sqrt(8*R*T/(np.pi*molar_mass))
    init=np.r_[initial_liquid*np.diff(edges**3),1-initial_liquid,0.]
    def rhs(t,y):
        A,Ad,Td=history['at'](t)
        volumes=N*A**3*weights;c=y[:cells]/volumes;cg=y[cells]
        m=henry(H298[species],SLOPES[species],Td)*R*T
        kg=1/(A/Dg+4/(alpha*cbar)) if exchange else 0.
        face_speed=-Ad*edges[1:-1]
        up=np.where(face_speed>=0,c[:-1],c[1:])
        j=-Dl*np.diff(c)/(A/cells)+face_speed*up
        F=4*np.pi*N*(A*edges[1:-1])**2*j
        out=np.zeros(cells);out[:-1]-=F;out[1:]+=F
        halfcell=A/(2*cells)
        den=Dl/halfcell+Ad+kg/m
        if den<=0:raise ValueError('Surface Peclet too large: refine radial grid.')
        cs=(Dl/halfcell*c[-1]+kg*cg)/den
        incoming=4*np.pi*N*A*A*kg*(cg-cs/m)
        out[-1]+=incoming
        return np.r_[out,-incoming,incoming]
    z=solve_ivp(rhs,(0,history['end']),init,method='BDF',rtol=rtol,
                atol=np.r_[np.full(cells,1e-16),1e-12,1e-16],
                max_step=max_step,dense_output=True)
    if not z.success:raise RuntimeError(z.message)
    ts=np.r_[0.,np.geomspace(1e-7,z.t[-1],299)];y=z.sol(ts)
    return dict(t=ts,y=y,liquid=y[:cells].sum(axis=0),gas=y[cells],centres=centres,
                conservation=float(np.max(abs(y[:cells].sum(axis=0)+y[cells]-1))),
                transfer_audit=float(np.max(abs(y[:cells].sum(axis=0)-initial_liquid-y[-1]))))


def fixed_sphere_dirichlet(cells=40,end=.2):
    """Dimensionless test: dC/dt=Laplace C, radius=D=Cs=1, C(0)=0.
    Analytic volume mean 1-6/pi^2 sum exp(-n^2*pi^2*t)/n^2.
    """
    x=np.linspace(0,1,cells+1);vol=4*np.pi/3*np.diff(x**3)
    def rhs(t,c):
        F=-4*np.pi*x[1:-1]**2*np.diff(c)*cells
        out=np.zeros(cells);out[:-1]-=F;out[1:]+=F
        out[-1]+=4*np.pi*(1-c[-1])*2*cells
        return out/vol
    z=solve_ivp(rhs,(0,end),np.zeros(cells),method='BDF',rtol=2e-10,atol=1e-12,dense_output=True)
    ts=np.geomspace(.001,end,100);mean=(vol[:,None]*z.sol(ts)).sum(axis=0)/(4*np.pi/3)
    n=np.arange(1,2001,dtype=float)[:,None]
    exact=1-6/np.pi**2*np.sum(np.exp(-n*n*np.pi**2*ts)/n**2,axis=0)
    return dict(t=ts,mean=mean,exact=exact,error=float(max(abs(mean-exact))))


def stokes_velocity(pos):
    """Dimensionless stationary no-slip sphere A=1, far-field velocity +z=1."""
    rr=np.linalg.norm(pos,axis=-1);r=np.maximum(rr,1.)
    nhat=pos/r[...,None];ct=nhat[...,2]
    aa=1-.75/r-.25/r**3;bb=-.75/r+.75/r**3
    v=bb[...,None]*ct[...,None]*nhat;v[...,2]+=aa
    return v


def phoretic_speeds(A,a,T,RH,P=101325.,vent=1.):
    """Surface radial velocities from Depee2021 Eq12; positive=outward.
    Spherical steady gradients and equal assumed heat/vapor ventilation.
    Published sodium-fluorescein kAP=.43 W/(m K). No fitting to CE.
    """
    b,D,Cc=mobility(a,T,P)
    mu=1.8325e-5*(T/296.15)**1.5*(296.15+110.4)/(T+110.4)
    lam=67.3e-9*(mu/1.8325e-5)*(101325/P)*np.sqrt(T/296.15)
    Kn=lam/a;rhoair=P*.028965/(R*T);kap=.43
    ka=.026*(T/298.15)**.8;Dv=2.5e-5*(T/298.15)**1.8
    Td,flux,_=interface(T,RH*vapor_density(T),A,kelvin=False)
    # Same ventilation on heat and vapor preserves this surface-temperature balance.
    vdf=.74*.028965/(.01801528*rhoair)*flux/A*vent
    c=(ka+2.5*kap*Kn)*ka/((1+3*Kn)*(2*ka+kap+5*kap*Kn))
    fth=-12*np.pi*mu*a/(5*P)*c*(T-Td)*vent/A
    return dict(vdf=vdf,vth=b*fth,Td=Td,D=D,mu=mu,Kn=Kn,rhoair=rhoair)


def falling_capture(A=5e-5,a=1e-7,T=273.42,RH=.824,U=.25,seed=1,
                    samples=2048,dt=.025,bmax=.6,zmax=8.,tmax=90.,
                    phoresis=True,brownian=True,interception=True,vent=1.,trace=False):
    """Candidate Lagrangian CE in creeping flow, not a validated smoke model.
    Brownian overdamped particle paths, finite interception radius. Midpoint drift.
    Sampling is flux-weighted at the upstream plane; finite-domain tails audited.
    CE convention pi*A^2*U. Every intercepted particle sticks by assumption.
    """
    p=phoretic_speeds(A,a,T,RH,vent=vent)
    Pe=U*A/p['D'];ph=(p['vdf']+p['vth'])/U if phoresis else 0.
    stop=1+a/A if interception else 1.
    rng=np.random.default_rng(seed)
    # Stratification is uniform area within the sampled injection disk.
    b=bmax*np.sqrt((np.arange(samples)+rng.random(samples))/samples)
    phi=rng.uniform(0,2*np.pi,samples)
    pos=np.column_stack([b*np.cos(phi),b*np.sin(phi),np.full(samples,-zmax)])
    inlet=stokes_velocity(pos)[:,2]+ph*pos[:,2]/np.linalg.norm(pos,axis=1)**3
    active=np.ones(samples,bool);hit=np.zeros(samples,bool);escaped=np.zeros(samples,bool)
    ts=[];tr=[]
    def drift(x):
        r=np.maximum(np.linalg.norm(x,axis=1),1.)
        return stokes_velocity(x)+ph*x/r[:,None]**3
    for step in range(int(np.ceil(tmax/dt))):
        ids=np.flatnonzero(active)
        if not len(ids):break
        old=pos[ids];v=drift(old);mid=old+.5*dt*v
        trial=old+dt*drift(mid)
        if brownian:trial+=np.sqrt(2*dt/Pe)*rng.normal(size=trial.shape)
        disp=trial-old;dd=np.sum(disp*disp,axis=1)
        f=np.clip(-np.sum(old*disp,axis=1)/np.maximum(dd,1e-300),0,1)
        h=np.linalg.norm(old+f[:,None]*disp,axis=1)<=stop
        # Segment crossing can still miss sub-step Brownian first passages.
        hit[ids[h]]=True;active[ids[h]]=False
        esc=trial[:,2]>zmax;escaped[ids[esc & ~h]]=True;active[ids[esc]]=False
        pos[ids]=trial
        if trace and step%20==0:
            ts.append(step*dt*A/U);tr.append(pos[::max(1,samples//40)].copy()*A)
    estimate=bmax*bmax*np.mean(inlet*hit)
    censored=bmax*bmax*np.mean(inlet*active)
    return dict(CE=float(estimate),censored_bound=float(censored),hits=int(hit.sum()),
                samples=samples,Re=float(2*A*U*p['rhoair']/p['mu']),Pe=float(Pe),
                vth=p['vth'],vdf=p['vdf'],Td=p['Td'],dt_s=dt*A/U,
                t=np.array(ts),traces=np.array(tr),hit=hit)


PEROXIDE_RATES={3:.009,5:.02878,8:.051,10:.058} # 1/min, Akhtar2012 table 1
def peroxide_published_rate_audit(pH=3,end_min=40.,rtol=1e-10):
    """Conditional reproduction ONLY; source consistency checks reject validation.
    Merck water/NaOH-washed MnO2, BET6.5m2/g, loading.333g/L,30C,
    initial H2O2 .020M, dark stirred, HCl/NH4OH-adjusted pH. No extrapolation.
    """
    if pH not in PEROXIDE_RATES:raise ValueError('No unambiguous tabulated rate for this pH.')
    k=PEROXIDE_RATES[pH]
    def rhs(t,y):
        v=k*y[0];return [-v,v,.5*v]
    z=solve_ivp(rhs,(0,end_min),[.02,0.,0.],rtol=rtol,atol=1e-13,dense_output=True,max_step=.25)
    ts=np.linspace(0,end_min,401);y=z.sol(ts)
    return dict(t=ts,y=y,k_min=k,half_min=np.log(2)/k,
        hydrogen_residual=float(max(abs(2*y[0]+2*y[1]-.04))),
        oxygen_residual=float(max(abs(2*y[0]+y[1]+2*y[2]-.04))))


def ice_capacity(T,gas_cm3=1e10,aged=False):
    """Behr2006 limiting fresh-upper-bound/aged site populations, not an aging clock."""
    if not 190<=T<=220:raise ValueError('Measured ice range is 190--220 K.')
    ka=np.array([3.8e-14,2.9e-15])*np.sqrt(T)
    kd=np.array([4e11,1.5e7])*np.exp(-np.array([5773.,3488.])/T)
    cap=np.array([0. if aged else 1e14,6e14])
    occ=ka*gas_cm3/(ka*gas_cm3+kd)
    return dict(sites_cm2=cap,adsorbed_cm2=cap*occ,ka_cm3_s=ka,kd_s=kd,
                timescale_s=1/(ka*gas_cm3+kd),total_cm2=float(sum(cap*occ)))


def boltzmann_charges(a,T=298.15,ion_ratio=.875,nmax=30):
    """Theoretical bipolar equilibrium distribution, NOT measured smoke charges.
    Discrete capacitive Boltzmann weights with specified ion asymmetry.
    Small-charge Wiedensohler corrections are not silently inferred.
    """
    q=np.arange(-nmax,nmax+1)
    var=4*np.pi*EPS0*a*KB*T/E**2
    logw=-q*q/(2*var)+q*np.log(ion_ratio)
    w=np.exp(logw-max(logw));w/=sum(w)
    return q,w


def approach_time(h0,h1,a=1e-5,A=1e-5,mu=1.84e-5,F=1e-12,lubrication=True):
    """Two immobilized spherical interfaces, constant inward test force.
    Far-field pair drag + leading no-slip lubrication. Analytical diagnostic;
    not a finite-conducting-droplet electrostatic or film-rupture solver.
    """
    if not 0<h1<h0:raise ValueError('Require positive decreasing gap.')
    ae=a*A/(a+A);zeta=6*np.pi*mu*ae
    exact=zeta/F*(h0-h1+(ae*np.log(h0/h1) if lubrication else 0))
    f=lambda h:zeta/F*(1+(ae/h if lubrication else 0))
    numeric=quad(f,h1,h0,epsabs=1e-13,epsrel=1e-12)[0]
    return exact,numeric
