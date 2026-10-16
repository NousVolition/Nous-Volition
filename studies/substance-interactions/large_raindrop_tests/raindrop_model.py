"""SI-unit large-drop collection closure v1; NOT a resolved CFD solver.

Published Slinn/Fredericks/Jones correlations, wet-bulb heat balance, and
Depee-style signed phoretic surface drift. See METHODS in README.txt.
Physical coefficients are fixed before extracting the new Hong2025 outcomes.
"""
import numpy as np
from scipy.optimize import brentq
from scipy.integrate import quad

KB=1.380649e-23
G=9.8
RW=997.
R=8.314462618
COMPONENTS=('brownian','interception','impaction','rear','thermo','diffusio','total')

def air(T=293.15,P=101325.):
    if not (273.15 <= T <= 323.15 and 50000 <= P <= 110000):
        raise ValueError('This implementation is restricted to liquid water, 273.15--323.15 K.')
    mu=1.83e-5*(296.16+120)/(T+120)*(T/296.16)**1.5
    rho=P/(287.05*T)
    lam=2*mu/rho/np.sqrt(8*KB*T/(np.pi*4.78e-26))
    ka=418.4*(1.04645+.017*T)*1e-5
    Dv=.211e-4*(T/273.15)**1.94*101325/P
    return mu,rho,lam,ka,Dv

def slip(d,lam):
    return 1+2*lam/d*(1.257+.4*np.exp(-1.1*d/(2*lam)))

def psat(T):
    return 100*np.polynomial.polynomial.polyval(T-273.15,
        [6.107799961,.4436518521,.01428945805,.0002650648471,
         3.031240396e-6,2.034080948e-8,6.136820929e-11])

def terminal_speed(D,T=293.15,P=101325.):
    """Beard (1976), Jones supplement S1. D is volume-equivalent diameter.
    Regime boundary 1.07 mm follows supplement; no extrapolation beyond 7 mm.
    """
    if not 0.5e-6 <= D <= .007: raise ValueError('Drop diameter outside Beard range.')
    mu,rho,lam,_,_=air(T,P)
    if D<=19e-6: return slip(D,lam)*D*D*(RW-rho)*G/(18*mu)
    if D<=.00107:
        x=np.log(4*D**3*rho*(RW-rho)*G/(3*mu**2))
        re=slip(D,lam)*np.exp(np.polynomial.polynomial.polyval(x,
            [-3.18657,.992696,-.00153193,-.000987059,-.000578878,.0000855176,-.00000327815]))
    else:
        # S12 avoids numerical cancellation in the optional fitted S13 polynomial.
        q=(647.15-T)/647.15
        sigma=.2358*q**1.256*(1-.625*q)
        bo=4*D**2*(RW-rho)*G/(3*sigma)
        npart=sigma**3*rho**2/(mu**4*(RW-rho)*G)
        x=np.log(bo*npart**(1/6))
        re=npart**(1/6)*np.exp(np.polynomial.polynomial.polyval(x,
             [-5.00015,5.23778,-2.04914,.475294,-.0542819,.00238449]))
    return mu*re/(rho*D)

def surface(D,U,T,RH,P):
    """Quasi-steady ventilated latent/conductive heat balance, no radiation.
    Ranz-Marshall Nu/Sh, Re based on diameter. Positive flux is evaporation.
    """
    mu,rho,lam,ka,Dv=air(T,P)
    re=rho*U*D/mu
    nu=2+.6*np.sqrt(re)*(1003.5*mu/ka)**(1/3)
    sh=2+.6*np.sqrt(re)*(mu/rho/Dv)**(1/3)
    vapor=lambda temp: .01802*psat(temp)/(R*temp)
    far=RH*vapor(T)
    flux=lambda temp: sh*Dv/D*(vapor(temp)-far)
    Td=T if RH==1 else brentq(lambda ts:nu*ka/D*(T-ts)-2.45e6*flux(ts),max(253.15,T-35),T,xtol=1e-11)
    residual=nu*ka/D*(T-Td)-2.45e6*flux(Td)
    return Td,flux(Td),nu/2,sh/2,residual

def efficiency(D,d,T=293.15,RH=.77,P=101325.,rho_p=1300.,k_p=.43,
               U=None,rear=True,phoresis=True,impaction=True,correction=True):
    """Dimensionless E referenced to pi D^2/4; perfect sticking assumed.
    d is PHYSICAL in-chamber particle diameter, not aerodynamic diameter.
    Rear term zero outside Re_D 20--800 is the published convention, flagged.
    Signed phoretic flux is a closure approximation, not resolved trajectories.
    """
    if not (D>0 and 0<d<D/10 and rho_p>2 and k_p>0 and 0<=RH<=1):
        raise ValueError('Invalid input or insufficient drop/particle scale separation.')
    U=terminal_speed(D,T,P) if U is None else float(U)
    if U<=0: raise ValueError('Positive falling speed required.')
    mu,rho,lam,ka,Dv=air(T,P)
    re=rho*U*D/mu; rer=re/2
    cc=slip(d,lam); Db=KB*T*cc/(3*np.pi*mu*d)
    tau=(rho_p-rho)*d*d*cc/(18*mu)
    up=tau*G; st=2*tau*max(U-up,0)/D
    star=(1.2+np.log1p(re)/12)/(1+np.log1p(re))
    sc=mu/rho/Db; phi=d/D
    muw=1.3788e-4*(T/225.66-1)**-1.6438
    eb=4/(rer*sc)*(1+.4*np.sqrt(rer)*sc**(1/3)+.16*np.sqrt(rer*sc))
    ei=4*phi*(mu/muw+(1+2*np.sqrt(rer))*phi)
    em=0.
    if impaction and st>star:
        em=((st-star)/(st-star+2/3))**1.5*np.sqrt(RW/rho_p)
        # S42 has Re_DIAMETER, unlike archived code's Re_RADIUS. .173 in S42.
        if correction: em*=10**(2.905-3.07*np.log10(st/star)**.173-2.61e-14*re**3.9)
    er=0.
    if rear and 20<=re<=800 and st>0:
        ls,lr=np.log(st),np.log(re)
        er=np.exp(-np.log(1.37e10)-3.625*ls+1.444*lr-.243*ls*ls+.08144*ls*lr)
    Td,flux,fh,fv,residual=surface(D,U,T,RH,P)
    et=ed=0.
    if phoresis:
        a=d/2; A=D/2; kn=lam/a
        # Depee2021 thermophoretic force, as in prior model, with material k_p.
        c=(ka+2.5*k_p*kn)*ka/((1+3*kn)*(2*ka+k_p+5*k_p*kn))
        vth=cc/(6*np.pi*mu*a)*(-12*np.pi*mu*a/(5*P)*c*(T-Td)*fh/A)
        # Evaporation drives outward diffusiophoretic drift in this convention.
        vdf=.74*.02896/(.01802*rho)*flux
        et=-4*vth/U; ed=-4*vdf/U
    raw=eb+ei+em+er+et+ed
    return dict(brownian=eb,interception=ei,impaction=em,rear=er,thermo=et,diffusio=ed,
                total=max(0.,raw),raw_total=raw,Re_D=re,St=st,St_critical=star,U=U,
                surface_T_K=Td,heat_residual_W_m2=residual,particle_speed_ratio=up/U,
                rear_in_domain=bool(20<=re<=800),clipped_negative=bool(raw<0))

def distribution(D,median,gsd=1.,moment=0,eps=1e-7,**kwargs):
    """Number (moment=0) or mass (3) weighted lognormal CE, ±8 normal SD.
    Tilting the normal by moment*ln(gsd) incorporates exact moment weights.
    Adaptive quadrature; no stochastic trajectory sampling is involved.
    """
    if gsd<1 or moment not in (0,3): raise ValueError('Invalid distribution.')
    if gsd==1: return {k:efficiency(D,median,**kwargs)[k] for k in COMPONENTS}
    sig=np.log(gsd)
    def fun(z,k):
        d=median*np.exp(sig*z+moment*sig*sig)
        return efficiency(D,d,**kwargs)[k]*np.exp(-z*z/2)/np.sqrt(2*np.pi)
    return {k:quad(fun,-8,8,args=(k,),epsabs=eps*1e-3,epsrel=eps,limit=200)[0] for k in COMPONENTS}

def inventory(E,D,U,Ndrop,n0,t):
    """Exact closed air/collected accounting; no particle chemistry/creation."""
    rate=E*np.pi*D*D/4*U*Ndrop
    airborne=n0*np.exp(-rate*np.asarray(t))
    return airborne,n0-airborne,rate
