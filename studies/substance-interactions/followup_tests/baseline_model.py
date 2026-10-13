"""Small, separate physical models. SI unless a variable explicitly says otherwise.

These are verification/pilot models, not a coupled atmospheric chemistry solver.
Reference IDs resolve in references.json. Scenario inputs are in config.json.
"""
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

R = 8.31446261815324
KB = 1.380649e-23
NA = 6.02214076e23
E = 1.602176634e-19
EPS0 = 8.8541878128e-12
KE = 1 / (4 * np.pi * EPS0)


def henry(H298, slope_K, T):
    """Hcp in mol/(m3 Pa), van't Hoff local fit (Sander2023)."""
    return H298 * np.exp(slope_K * (1 / T - 1 / 298.15))


def transfer_parameters(H, T, Vg, Vl, mode, radius=1e-5,
                        Dg=2e-5, Dl=2e-9, bulk_kLa=0.01):
    m = H * R * T  # dimensionless c_liquid/c_gas at equilibrium
    if mode == 'bulk':
        kla = bulk_kLa
    else:
        # Stagnant spherical-film closure; Sh=2 based on diameter.
        kl, kg = Dl / radius, Dg / radius
        KL = 1 / (1 / kl + m / kg)  # liquid-side overall transfer velocity
        kla = 3 * KL / radius
    capacity = m * Vl / Vg
    return capacity / (1 + capacity), kla * (1 + capacity), kla


def partition(H, T, Vg, Vl, times, mode='bulk', **kw):
    f, rate, kla = transfer_parameters(H, T, Vg, Vl, mode, **kw)
    sol = solve_ivp(lambda t, y: [rate * (f - y[0])],
                    (0, float(times[-1])), [0.], t_eval=times,
                    method='Radau', rtol=2e-10, atol=1e-18)
    if not sol.success:
        raise RuntimeError(sol.message)
    return sol.y[0], f, rate, kla


def carbonate_from_co2(c0_M):
    """Pure, zero-alkalinity freshwater at 298.15K. CO2* = CO2(aq)+H2CO3.
    K1, K2 are apparent dilute solution constants, concentrations in mol/L.
    Equilibrium only: no instantaneous hydration kinetic claim (USGS2012).
    """
    K1, K2, Kw = 10**-6.35, 10**-10.33, 1e-14
    def balance(pH):
        h = 10**(-pH)
        return h - Kw/h - K1*c0_M/h - 2*K1*K2*c0_M/h**2
    pH = brentq(balance, 1, 12, xtol=1e-13)
    h = 10**-pH
    bic, carb, oh = K1*c0_M/h, K1*K2*c0_M/h**2, Kw/h
    return dict(pH=pH, CO2star_M=c0_M, HCO3_M=bic, CO3_M=carb,
                H_M=h, OH_M=oh, DIC_M=c0_M+bic+carb,
                charge_residual_M=h-oh-bic-2*carb)


def carbonate_closed(initial_ppm=420, Vg=1, Vl=.001, T=298.15, P=101325):
    if T != 298.15:
        raise ValueError('Only 298.15 K carbonate constants are implemented.')
    initial = initial_ppm*1e-6*P*Vg/(R*T)
    H = 3.4e-4
    def residual(p):
        s = carbonate_from_co2(H*p/1000)
        return p*Vg/(R*T) + s['DIC_M']*1000*Vl - initial
    p = brentq(residual, 1e-12, initial_ppm*1e-6*P, xtol=1e-13)
    s = carbonate_from_co2(H*p/1000)
    s.update(gas_partial_pressure_Pa=p, initial_carbon_mol=initial,
             aqueous_carbon_mol=s['DIC_M']*1000*Vl,
             gas_carbon_mol=p*Vg/(R*T), carbon_residual_mol=residual(p))
    return s


def transport(n=96, dt=.005, end=2, L=.1, u=.01, v=.003,
              diffusivity=2e-5, decay=0, snapshots=False):
    """Periodic finite-volume upwind advection + centered diffusion, SSPRK3.
    Uniform first-order capture sink has an explicit complementary reservoir.
    Dimensionless passive scalar; multiply by gas concentration or number density.
    """
    dx = L/n
    x = (np.arange(n)+.5)*dx
    X,Y = np.meshgrid(x,x,indexing='xy')
    c = 1 + .5*np.cos(2*np.pi*X/L)*np.cos(2*np.pi*Y/L)
    initial = c.copy()
    stability = abs(u)/dx + abs(v)/dx + 4*diffusivity/dx**2 + decay
    if dt*stability > .95:
        raise ValueError('Time step exceeds positive forward-Euler bound.')
    def rhs(a):
        xp,xm = np.roll(a,-1,1),np.roll(a,1,1)
        yp,ym = np.roll(a,-1,0),np.roll(a,1,0)
        ax = (a-xm) if u>=0 else (xp-a)
        ay = (a-ym) if v>=0 else (yp-a)
        return -u*ax/dx-v*ay/dx+diffusivity*(xp+xm+yp+ym-4*a)/dx**2-decay*a
    steps = int(np.ceil(end/dt)); h=end/steps
    frames = [(0,initial.copy())]
    for i in range(steps):
        a = c+h*rhs(c)
        b = .75*c+.25*(a+h*rhs(a))
        c = c/3+2*(b+h*rhs(b))/3
        if snapshots and i+1 in (steps//2,steps):
            frames.append(((i+1)*h,c.copy()))
    exact = np.exp(-decay*end)*(1+.5*np.exp(-2*diffusivity*(2*np.pi/L)**2*end)
             *np.cos(2*np.pi*(X-u*end)/L)*np.cos(2*np.pi*(Y-v*end)/L))
    captured = initial.mean()-c.mean()  # sink reservoir by conservative budget
    return dict(field=c, exact=exact, initial=initial, frames=frames, x=x,
                relative_L2=float(np.linalg.norm(c-exact)/np.linalg.norm(exact)),
                mean=float(c.mean()), captured=float(captured), dt=h,
                mass_error_no_sink=float(c.mean()-initial.mean()) if decay==0 else None,
                sink_analytic_error=float(abs(captured-(1-np.exp(-decay*end)))),
                minimum=float(c.min()))


def air_mu(T=298.15):
    # NIST2006 Sutherland scaling, reference viscosity rounded scenario input.
    return 1.8325e-5*(T/296.15)**1.5*(296.15+110.4)/(T+110.4)


def mobility(a, T=298.15, P=101325, slip=True):
    mu=air_mu(T)
    lam=67.3e-9*(mu/1.8325e-5)*(101325/P)*np.sqrt(T/296.15)
    Kn=lam/a
    cc=1+Kn*(1.165+.483*np.exp(-.997/Kn)) if slip else 1.
    b=cc/(6*np.pi*mu*a)
    return b, KB*T*b, cc


def pair_analytic(r0, t, a, q1_e, q2_e, T=298.15):
    b,_,_=mobility(a,T)
    return np.cbrt(r0**3+6*b*KE*q1_e*q2_e*E**2*np.asarray(t))


def particle_pairs(a=1e-6, q1_e=100, q2_e=100, r0=20e-6,
                   end=1, dt=.0005, samples=256, seed=41, brownian=True,
                   T=298.15, far_limit=6, trace_count=4):
    """3D overdamped independent pairs with Coulomb drift and independent noise.
    No hydrodynamic coupling or induced polarization. Stop at r=far_limit*a,
    BEFORE near-contact point-charge physics breaks down. No coalescence claim.
    Unbounded air; equal gravity cancels from relative separation.
    """
    if r0 <= far_limit*a:
        raise ValueError('Initial separation outside far-field validity.')
    b,D,_=mobility(a,T)
    rng=np.random.default_rng(seed)
    pos=np.zeros((samples,2,3)); pos[:,0,0]=-r0/2; pos[:,1,0]=r0/2
    active=np.ones(samples,dtype=bool)
    stop=np.full(samples,np.nan)
    steps=int(np.ceil(end/dt)); h=end/steps
    times=[0.]; traces=[pos[:trace_count].copy()]
    for k in range(steps):
        d=pos[:,1]-pos[:,0]; rr=np.linalg.norm(d,axis=1)
        force=KE*q1_e*q2_e*E**2*d/rr[:,None]**3
        drift=np.stack((-b*force,b*force),axis=1)
        noise=rng.normal(size=pos.shape)*np.sqrt(2*D*h) if brownian else 0.
        trial=pos+h*drift+noise
        pos[active]=trial[active]
        rr=np.linalg.norm(pos[:,1]-pos[:,0],axis=1)
        hit=active & (rr <= far_limit*a)
        stop[hit]=(k+1)*h; active[hit]=False
        if (k+1)%max(1,steps//200)==0 or k+1==steps:
            times.append((k+1)*h); traces.append(pos[:trace_count].copy())
    return dict(final_separation_m=np.linalg.norm(pos[:,1]-pos[:,0],axis=1),
                stopped_fraction=float((~active).mean()),stop_times_s=stop,
                times_s=np.array(times),traces_m=np.array(traces),
                particle_D_m2_s=D,mobility_m_N_s=b,dt=h)


def saturation(T, ice=False):
    """Murphy & Koop (2005), equations 7 and 10, pressure Pa, T K."""
    if ice:
        return np.exp(9.550426-5723.265/T+3.53068*np.log(T)-.00728332*T)
    return np.exp(54.842763-6763.22/T-4.210*np.log(T)+.000367*T
        +np.tanh(.0415*(T-218.8))*(53.878-1331.22/T-9.44523*np.log(T)+.014025*T))


def vapor_exchange(T=263.15, RH_water=.95, ice=True, end=600):
    """Closed vapor + macroscopic flat water/ice interface, thermostatted.
    Area=.01m2, Vgas=.001m3, effective vapor transfer velocity=.001m/s.
    Condensed inventory .01kg prevents reservoir exhaustion in these scenarios.
    Includes latent heat as thermostat load, not an energy equation.
    """
    Vg,A,km=.001,.01,.001
    mw=.01801528; p0=RH_water*saturation(T); ps=saturation(T,ice)
    rate=km*A/Vg
    times=np.linspace(0,end,301)
    # Integrate molar transfer rather than clamping saturation by hand.
    n0=p0*Vg/(R*T); ns=ps*Vg/(R*T)
    sol=solve_ivp(lambda t,y: [-rate*(y[0]-ns),rate*(y[0]-ns)],
        (0,end),[n0,0],t_eval=times,rtol=1e-10,atol=1e-16)
    ng,nd=sol.y
    return dict(T_K=T,RH_water=RH_water,RH_ice=p0/saturation(T,True),
        ice=ice,p_initial_Pa=p0,p_saturation_Pa=ps,rate_s_1=rate,
        times_s=times,gas_mol=ng,deposited_mol=nd,
        transferred_water_mg=float(nd[-1]*mw*1e6),
        heat_to_thermostat_J=float(nd[-1]*mw*(2.834e6 if ice else 2.45e6)),
        conservation_relative=float(np.max(np.abs(ng+nd-n0))/n0))


def ice_adsorption(T=210, gas_ppb=1, surface_area=1, end=600):
    """Acetone two-site ice model, IceAcetone2006 (190--220 K ONLY).
    k_ads in cm3 molecule^-1 s^-1; gas molecules/cm3 converted explicitly.
    Closed 1 m3 gas volume; site-1 upper-bound capacity used as an assumption.
    k_ads/k_des defines kinetic equilibrium; independently fitted K_L NOT mixed in.
    """
    if not 190<=T<=220:
        raise ValueError('Ice adsorption fit valid only for 190-220 K.')
    total=gas_ppb*1e-9*101325/(KB*T)
    sites=np.array([1e14,6e14])*1e4*surface_area
    ka=np.array([3.8e-14,2.9e-15])*T**.5
    kd=np.array([4e11*np.exp(-5773/T),1.5e7*np.exp(-3488/T)])
    def fun(t,y):
        ng=max(0,1-y.sum())*total/1e6
        return ka*ng*(sites/total-y)-kd*y
    tt=np.r_[0,np.geomspace(.001,end,250)]
    sol=solve_ivp(fun,(0,end),[0.,0.],t_eval=tt,method='Radau',rtol=1e-10,atol=1e-14)
    def balance(gf):
        theta=ka*(gf*total/1e6)/(kd+ka*(gf*total/1e6))
        return gf+np.sum(sites*theta)/total-1
    geq=brentq(balance,0,1)
    return dict(T_K=T,times_s=tt,adsorbed_fractions=sol.y,
        total_mol=total/NA,gas_fraction=1-sol.y.sum(axis=0),
        final_adsorbed_fraction=float(sol.y[:,-1].sum()),
        analytic_equilibrium_adsorbed_fraction=1-geq,
        equilibrium_error=float(abs(sol.y[:,-1].sum()-(1-geq))),
        k_ads_cm3_molecule_s=ka,k_des_s_1=kd)


def brownian_scavenging(a=1e-7, droplet_radius=1e-5, LWC_kg_m3=.0005,
                        T=298.15, sticking=1):
    """Dilute Smoluchowski diffusion-only perfect-sink kernel (idealized).
    Slip-corrected particle diffusion; near-surface hydrodynamics and phoresis
    omitted. Sticking probability is assumed, NOT measured smoke chemistry.
    """
    _,Dp,_=mobility(a,T); _,Dd,_=mobility(droplet_radius,T)
    kernel=4*np.pi*(Dp+Dd)*(a+droplet_radius)*sticking
    nd=LWC_kg_m3/(1000*4*np.pi*droplet_radius**3/3)
    rate=kernel*nd
    return dict(kernel_m3_s=kernel,droplet_number_m3=nd,rate_s_1=rate,
                captured_fraction_600s=float(-np.expm1(-rate*600)))


def decomposition_products(n0, extent_fraction):
    """Stoichiometry only: 2 H2O2 -> 2 H2O + O2. No invented kinetic rate."""
    used=n0*extent_fraction
    return np.array([n0-used,used,used/2])


def co_oh_kinetics(end=600, OH_molecules_cm3=1e6, multiplier=1):
    """Closed, low-pressure elementary-channel benchmark: CO+OH -> CO2+H.
    298.15 K, 100 Pa N2, CO=1ppm. IUPAC low-pressure k=1.44e-13
    cm3 molecule^-1 s^-1. Finite oxidant inventory, no radical replenishment.
    The pressure correction to combined k is <0.06%; HOCO stabilization
    omitted in this low-pressure limit. No claim to a full radical mechanism.
    """
    T=298.15;P=100.;V=1.
    co0=1e-6*P*V/(R*T)
    oh0=OH_molecules_cm3*1e6*V/NA
    k=1.44e-13*1e-6*NA*multiplier # m3 mol^-1 s^-1
    tt=np.linspace(0,end,301)
    if oh0==0:
        extent=np.zeros(len(tt))
    else:
        sol=solve_ivp(lambda t,y:[k*(co0-oh0*y[0])*(1-y[0])/V],
            (0,end),[0.],t_eval=tt,rtol=1e-11,atol=1e-13)
        extent=sol.y[0]*oh0
    concentrations=np.vstack([co0-extent,oh0-extent,extent,extent])
    # Columns CO, OH, CO2, H; rows elemental C,O,H inventories.
    atoms=np.array([[1,0,1,0],[1,1,2,0],[0,1,0,1]])@concentrations
    resid=np.max(abs(atoms-atoms[:,0,None]),axis=1)
    return dict(times_s=tt,moles=concentrations,k_m3_mol_s=k,T_K=T,P_Pa=P,
        CO_initial_mol=co0,OH_initial_mol=oh0,CO_converted_percent=100*extent[-1]/co0,
        OH_consumed_percent=100*extent[-1]/oh0 if oh0 else 0,
        atom_relative_error=float(np.max(resid/np.maximum(atoms[:,0],1e-30))),
        combined_k_pressure_correction_fraction=P/(KB*T)/1e6/4.2e19)


def freezing_melting(power_W=5, end=600, mass_kg=.01):
    """Isothermal seeded phase change at273.15K with prescribed heat flux.
    Positive power melts ice; negative freezes liquid. No nucleation law.
    Heat of fusion rounded to334 kJ/kg (scenario approximation).
    """
    latent=334000.
    t=np.linspace(0,end,301)
    converted=np.minimum(abs(power_W)*t/latent,mass_kg)
    latent_energy=converted*latent
    excess=abs(power_W)*t-latent_energy
    return dict(times_s=t,converted_mass_kg=converted,
        remaining_mass_kg=mass_kg-converted,latent_energy_J=latent_energy,
        unused_heat_after_completion_J=excess,completion_time_s=mass_kg*latent/abs(power_W) if power_W else np.inf)
