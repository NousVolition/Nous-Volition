"""Independent extensions of the published pilot. SI units throughout.

No empirical parameters are fitted. See METHODS.md and references.json for
equations, validity limits, measured-data provenance and assumed parameters.
"""
from dataclasses import dataclass
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from baseline_model import R, KB, E, KE, henry, mobility, saturation

SPECIES = ('CO', 'acetone', 'isoprene', 'H2O2')
H298 = np.array([9.7e-6, .27, 1.3e-4, 860.])
SLOPES = np.array([1300., 5500., 2700., 7300.])
PPM = np.array([1., 1., 1., .001])
MW = .01801528
RHO = 1000.
LV = 2.45e6
SIGMA = .072

def vapor_density(T):
    return saturation(T)*MW/(R*T)

def interface(Tair, vapor_kg_m3, radius, cooling=True, kelvin=True, dv_scale=1.):
    """Quasi-steady conductive heat = latent heat; no transient sensible heat.
    Dv and kair are explicitly assumed smooth fits, not inferred measurements.
    """
    Dv=2.5e-5*(Tair/298.15)**1.8*dv_scale
    kair=.026*(Tair/298.15)**.8
    def surface(T):
        factor=np.exp(2*SIGMA*MW/(RHO*R*T*radius)) if kelvin else 1.
        return vapor_density(T)*factor
    if cooling:
        def balance(T):return kair*(Tair-T)-LV*Dv*(surface(T)-vapor_kg_m3)
        Td=brentq(balance,240.,340.,xtol=1e-11)
    else:Td=Tair
    flux=Dv*(surface(Td)-vapor_kg_m3) # kg/(m s), dm/dt=-4*pi*a*flux
    residual=kair*(Tair-Td)-LV*flux if cooling else 0.
    return Td,flux,residual

@dataclass
class Fog:
    T:float=298.15
    RH:float=.9
    radius:float=1e-5
    liquid_kg_m3:float=.0005
    end:float=30.
    cooling:bool=True
    kelvin:bool=True
    water_exchange:bool=True
    solute_exchange:bool=True
    open_water_reservoir:bool=False
    dv_scale:float=1.
    transfer_scale:float=1.
    H_scale:float=1.
    max_step:float=.2
    rtol:float=2e-8
    method:str='Radau'

def fog_run(c=Fog()):
    if not (280<=c.T<=310 and 0<=c.RH<=1.01 and c.radius>2e-6 and c.liquid_kg_m3>0):
        raise ValueError('Outside documented liquid-water scenario bounds.')
    a0=c.radius;M0=c.liquid_kg_m3;rv0=c.RH*vapor_density(c.T)
    # State: radius squared/a0^2, evaporated water/M0, heat/(Lv*M0),
    # liquid and gas fractions of EACH conserved solute inventory.
    y0=np.r_[1.,0.,0.,np.zeros(4),np.ones(4)]
    def properties(y):
        u=max(float(y[0]),1e-6);a=a0*np.sqrt(u)
        rv=rv0 if c.open_water_reservoir else rv0+M0*y[1]
        Td,flux,err=interface(c.T,rv,a,c.cooling,c.kelvin,c.dv_scale)
        if not c.water_exchange:Td,flux,err=c.T,0.,0.
        return u,a,rv,Td,flux,err
    def rhs(t,y):
        u,a,rv,Td,flux,err=properties(y)
        du=-2*flux/(RHO*a0*a0)
        evap=-1.5*np.sqrt(u)*du
        m=henry(H298*c.H_scale,SLOPES,Td)*R*c.T
        vl=M0/RHO*u**1.5
        kl,kg=2e-9/a,2e-5/a
        kla=3/(1/kl+m/kg)/a*c.transfer_scale if c.solute_exchange else 0.
        df=kla*(m*vl*y[7:11]-y[3:7])
        return np.r_[du,evap,evap,df,-df]
    def cutoff(t,y):return y[0]-(2e-6/a0)**2
    cutoff.terminal=True;cutoff.direction=-1
    sol=solve_ivp(rhs,(0,c.end),y0,method=c.method,rtol=c.rtol,
        atol=np.r_[1e-11,1e-11,1e-11,np.full(4,1e-16),np.full(4,1e-12)],
        max_step=c.max_step,events=cutoff,dense_output=True)
    if not sol.success:raise RuntimeError(sol.message)
    tt=np.r_[0.,np.geomspace(1e-7,sol.t[-1],399)]
    y=sol.sol(tt);props=np.array([properties(y[:,i]) for i in range(len(tt))])
    water_error=np.max(abs(y[0]**1.5+y[1]-1))
    solute_error=np.max(abs(y[3:7]+y[7:11]-1))
    return dict(times=tt,state=y,radius=a0*np.sqrt(y[0]),Td=props[:,3],
        RH=(rv0+M0*y[1])/vapor_density(c.T) if not c.open_water_reservoir else np.full_like(tt,c.RH),
        pressure_Pa=101325+M0*y[1]*R*c.T/MW if not c.open_water_reservoir else np.full_like(tt,101325),
        stopped=bool(len(sol.t_events[0])),water_relative_error=float(water_error),
        solute_relative_error=float(solute_error),heat_budget_error=float(np.max(abs(y[2]-y[1]))),
        heat_balance_residual_W_m=float(np.max(abs(props[:,5]))),
        heat_J_m3=y[2]*LV*M0,initial_solute_mol_m3=PPM*1e-6*101325/(R*c.T))

def electro_force(r,q_e,Q_e,A=1e-5,polarization=True):
    """Signed outward force on a point aerosol from a conducting sphere.
    Depee et al. 2021 Part II Eq10; no finite-aerosol polarization correction.
    Stable algebraic form of image term avoids large-r cancellation.
    """
    r=np.asarray(r,dtype=float)
    if np.any(r<=A):raise ValueError('Outside conducting sphere only.')
    q,Q=q_e*E,Q_e*E
    f=KE*q*Q/r**2
    if polarization:f=f-KE*q*q*A**3*(2*r*r-A*A)/(r**3*(r*r-A*A)**2)
    return f

def electro_potential(r,q_e,Q_e,A=1e-5,polarization=True):
    r=np.asarray(r,dtype=float)
    if np.any(r<=A):raise ValueError('Outside conducting sphere only.')
    q,Q=q_e*E,Q_e*E
    u=KE*q*Q/r
    if polarization:u=u-KE*q*q*A**3/(2*r*r*(r*r-A*A))
    return u

def deterministic_pair(q_e=100,Q_e=0,A=1e-5,a=1e-7,T=298.15,end=1.,polarization=True,max_step=.005,rtol=1e-10):
    b=mobility(a,T)[0]+mobility(A,T)[0];r0=3*A;stop=2*A
    scale=max(abs(float(electro_potential(r0,q_e,Q_e,A,polarization))),KB*T)
    def rhs(t,y):
        r=max(y[0]*A,1.5*A);f=electro_force(r,q_e,Q_e,A,polarization)
        return [b*f/A,b*f*f/scale]
    def event(t,y):return y[0]-2
    event.terminal=True;event.direction=-1
    z=solve_ivp(rhs,(0,end),[3.,0.],events=event,rtol=rtol,atol=1e-12,max_step=max_step,dense_output=True)
    if not z.success:raise RuntimeError(z.message)
    tt=np.linspace(0,z.t[-1],201);yy=z.sol(tt);rr=yy[0]*A
    energy=electro_potential(rr,q_e,Q_e,A,polarization)+scale*yy[1]
    return dict(times=tt,radius=rr,heat=scale*yy[1],stopped=bool(len(z.t_events[0])),
        energy_relative_residual=float(np.max(abs(energy-energy[0]))/scale))

def brownian_pairs(q_e=100,Q_e=0,A=1e-5,a=1e-7,T=298.15,end=1.,dt=.001,
                   samples=512,seed=101,polarization=True,noise_dt=.0005,trace_count=8):
    """Independent relative 3D paths, censored at r=2A; NOT collisions.
    Coupled Brownian increments allow paired time-step comparisons.
    """
    stride=round(dt/noise_dt);fine_steps=round(end/noise_dt)
    if stride<1 or abs(stride*noise_dt-dt)>1e-12 or fine_steps%stride:raise ValueError('Nested noise time grid required.')
    b1,D1,_=mobility(a,T);b2,D2,_=mobility(A,T);b=b1+b2;D=D1+D2
    rng=np.random.default_rng(seed)
    noise=rng.normal(size=(fine_steps,samples,3))*np.sqrt(2*D*noise_dt)
    increments=noise.reshape(fine_steps//stride,stride,samples,3).sum(axis=1)
    pos=np.zeros((samples,3));pos[:,0]=3*A
    active=np.ones(samples,bool);stops=np.full(samples,np.nan);rcut=2*A
    traces=[pos[:trace_count].copy()];times=[0.]
    max_step_ratio=0.
    for k,dW in enumerate(increments):
        old=pos.copy();r=np.linalg.norm(old,axis=1)
        force=electro_force(r,q_e,Q_e,A,polarization)
        trial=old+(dt*b*force/r)[:,None]*old+dW
        pos[active]=trial[active]
        hit=active & (np.linalg.norm(pos,axis=1)<=rcut)
        if np.any(hit):
            d=trial[hit]-old[hit];p=old[hit];aa=(d*d).sum(axis=1);bb=2*(p*d).sum(axis=1);cc=(p*p).sum(axis=1)-rcut**2
            frac=(-bb-np.sqrt(np.maximum(0,bb*bb-4*aa*cc)))/(2*aa)
            frac=np.clip(frac,0,1)
            pos[hit]=p+frac[:,None]*d;stops[hit]=(k+frac)*dt;active[hit]=False
        if (k+1)%max(1,len(increments)//200)==0:
            traces.append(pos[:trace_count].copy());times.append((k+1)*dt)
    return dict(final_position=pos,stops=stops,stopped_fraction=float((~active).mean()),
        mean_separation_m=float(np.linalg.norm(pos,axis=1).mean()),times=np.array(times),traces=np.array(traces),Drelative=D)

def brownian_collection_efficiency(a,A,T=273.73,speed=.25,sticking=1.):
    """Original stagnant diffusion kernel, normalized to experimental CE.
    This intentionally tests the incomplete pilot against falling-drop data.
    It is NOT the full Depee collection model.
    """
    if min(a,A,T,speed)<=0 or not 0<=sticking<=1:raise ValueError('Invalid collection input.')
    Da=mobility(a,T)[1];DA=mobility(A,T)[1]
    K=4*np.pi*(Da+DA)*(a+A)*sticking
    return K/(np.pi*A*A*speed)
