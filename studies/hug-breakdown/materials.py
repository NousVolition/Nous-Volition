"""Real-fluid materials table + mapping onto the fluid-shelter model.

Model only. Values at ~20 C, 1 atm unless stated; every entry carries a source
(see SOURCES; full citations and URLs also in README). Ranges are given where
the value is uncertain or depends on conditions (smoke loading, temperature).

Mapping (MaterialShelter): the model is nondimensional with density in units
of AIR at 20 C and viscosity in units of the model's mu_air = 0.01 per real
air viscosity. The anxiety swirl and the push are FORCES per unit volume, the
same in every gas (so a lighter gas is accelerated more by the same push).
Because the Dodd-Ferrante splitting in fluid_shelter.py uses rho0 = 1 = the
smallest density, every density, viscosity, surface tension and force is
divided by s = min(rho_liquid, rho_gas) (exact rescaling of the momentum
equation: same velocities, same time). Surface tension: sigma_model =
base_sigma * sigma_material / sigma_water_air. 2D, NO GRAVITY: density only
enters through inertia, so hot-smoke buoyancy and CO2 sinking are absent.
Not the Clay problem; says nothing about real people.
"""
import time
from dataclasses import dataclass, replace
import numpy as np
from fluid_shelter import FluidParams, FluidShelter, run as fluid_run

T_REF_K = 293.15
SOURCES = {
    "NIST": "NIST Chemistry WebBook, SRD 69, Thermophysical Properties of Fluid Systems "
            "(Lemmon, McLinden, Friend), https://webbook.nist.gov/chemistry/fluid/ "
            "(queried at 0.101325 MPa, 20 and 25 C)",
    "CRC": "CRC Handbook of Chemistry and Physics (Rumble ed.), fluid property tables",
    "ETB_air": "Engineering ToolBox, Air - dynamic and kinematic viscosity / density vs "
               "temperature, https://www.engineeringtoolbox.com/air-absolute-kinematic-viscosity-d_601.html",
    "IAPWS_ST": "IAPWS R1-76(2014) Surface tension of ordinary water substance (72.74 mN/m at 20 C)",
    "EVONIK": "Evonik Active Oxygens, H2O2 physico-chemical properties table (20 C), "
              "https://www.evonik.com/en/company/businesslines/ao/products-and-services/"
              "hydrogen-peroxide/general-information/physico-chemical-properties.html",
    "ECHA": "EU Risk Assessment Report, Hydrogen peroxide (ECHA, 2003), Tables 1.1-1.2 "
            "(pure: 1.4425 g/cm3 at 25 C; 35%: 1.1282 g/cm3, 74.6 mN/m, 1.11 mPa s)",
    "SHARQAWY": "Sharqawy, Lienhard & Zubair (2010), Thermophysical properties of seawater: "
                "a review of existing correlations and data, Desalination and Water Treatment "
                "16:354-380, eqs. for density and viscosity vs salinity (used as a dissolved-salt proxy)",
    "USGS_HARD": "USGS Water Science School, Hardness of water: 121-180 mg/L as CaCO3 = hard, "
                 ">180 = very hard, https://www.usgs.gov/water-science-school/science/hardness-water",
    "WEISSENBORN": "Weissenborn & Pugh (1996), Surface tension of aqueous solutions of electrolytes, "
                   "J. Colloid Interface Sci. 184:550-563 (salts raise sigma ~1-3 mN/m per mol/L)",
    "MULHOLLAND": "Mulholland & Croarkin (2000), Specific extinction coefficient of flame generated "
                  "smoke, Fire and Materials 24:227-230 (sigma_s = 8.7 +- 1.1 m2/g, C = K/sigma_s)",
    "JIN": "Jin, T. (1978) Visibility through fire smoke, J. Fire & Flammability 9:135; SFPE Handbook "
           "of Fire Protection Engineering, 'Visibility and human behavior in fire smoke' "
           "(extinction K ~ 0.1-10 1/m from light to very dense smoke)",
    "CHOI": "Choi, Mulholland, Hamins & Kashiwagi (1995), Combust. Flame 102:161-169 "
            "(soot material density ~1.74 g/cm3); Einstein (1906) suspension viscosity 1 + 2.5 phi",
    "IDEAL_GAS": "ideal-gas law at 1 atm, rho(T) = rho_air(20 C) * 293.15/T (air M = 28.96 g/mol); "
                 "agrees with Engineering ToolBox air-density-vs-temperature table",
    "MASSOUDI": "Massoudi & King (1974), Effect of pressure on the surface tension of water. "
                "Adsorption of low molecular weight gases on water at 25 C, J. Phys. Chem. "
                "78:2262-2266 (gas adsorption lowers sigma; small at 1 atm). Value vs air used here.",
}


@dataclass(frozen=True)
class Material:
    name: str
    kind: str                 # "liquid", "gas" or "smoke" (gas-particle suspension)
    density: float            # kg/m^3
    viscosity: float          # Pa s
    sigma_air: float          # N/m against air (0 for gases/smoke)
    source: str
    T_C: float = 20.0
    density_range: tuple = ()
    viscosity_range: tuple = ()
    note: str = ""


AIR = Material("air", "gas", 1.204, 1.81e-5, 0.0, "CRC; ETB_air (1.204 kg/m3; 18.13 uPa s at 20 C)",
               viscosity_range=(1.81e-5, 1.813e-5))
WATER = Material("water", "liquid", 998.21, 1.0016e-3, 0.0728, "NIST (998.21 kg/m3, 1.0016 mPa s); IAPWS_ST",
                 note="sigma 72.74-72.8 mN/m (IAPWS_ST; EVONIK 0%-column 72.8)")

# --- hard water: Ca(HCO3)2 hardness via seawater salt correlations (proxy) ---
M_CACO3, M_CA, M_HCO3 = 100.09, 40.08, 61.02          # g/mol


def hardness_tds(mg_per_L_as_caco3):
    """Dissolved mass (kg solute / kg water) if the hardness is Ca(HCO3)2:
    each mmol CaCO3-equivalent = 1 Ca2+ + 2 HCO3-."""
    mmol = mg_per_L_as_caco3/M_CACO3
    return mmol*(M_CA + 2*M_HCO3)*1e-3/WATER.density   # g/L -> kg/kg (rho ~ 1 kg/L)


def sharqawy_density_increment(S, T=20.0):
    """rho_sw - rho_w (kg/m3), Sharqawy et al. 2010 eq. (8), S in kg/kg."""
    a = (8.020e2, -2.001, 1.677e-2, -3.060e-5, -1.613e-5)
    return S*(a[0] + a[1]*T + a[2]*T**2 + a[3]*T**3 + a[4]*S*T**2)


def sharqawy_viscosity_factor(S, T=20.0):
    """mu_sw/mu_w = 1 + A S + B S^2, Sharqawy et al. 2010 (viscosity correlation)."""
    A = 1.541 + 1.998e-2*T - 9.52e-5*T**2
    B = 7.974 - 7.561e-2*T + 4.724e-4*T**2
    return 1 + A*S + B*S**2


def hard_water(mg_per_L_as_caco3=180.0):
    S = hardness_tds(mg_per_L_as_caco3)
    rho = WATER.density + sharqawy_density_increment(S)
    mu = WATER.viscosity*sharqawy_viscosity_factor(S)
    lo, hi = hardness_tds(120.0), hardness_tds(250.0)
    return Material(
        f"hard water ({mg_per_L_as_caco3:g} mg/L CaCO3)", "liquid", rho, mu, WATER.sigma_air,
        "USGS_HARD; SHARQAWY (computed); WEISSENBORN (sigma change ~2 mM*2 mN/m/M < 0.01 mN/m)",
        density_range=(WATER.density + sharqawy_density_increment(lo),
                       WATER.density + sharqawy_density_increment(hi)),
        viscosity_range=(WATER.viscosity*sharqawy_viscosity_factor(lo),
                         WATER.viscosity*sharqawy_viscosity_factor(hi)),
        note=f"dissolved {S*1e3:.3f} g/kg as Ca(HCO3)2; d rho/rho = "
             f"{(rho/WATER.density - 1)*100:.4f} %, d mu/mu = {(mu/WATER.viscosity - 1)*100:.4f} %")


HARD_WATER = hard_water(180.0)
H2O2_100 = Material("hydrogen peroxide (100 %)", "liquid", 1450.0, 1.25e-3, 0.0804,
                    "EVONIK (1.450 g/ml, 1.25 mPa s, 80.4 mN/m at 20 C); ECHA (1.4425 at 25 C); "
                    "CRC (1.245 mPa s at 20 C)",
                    density_range=(1442.5, 1450.0), viscosity_range=(1.245e-3, 1.25e-3))
H2O2_35 = Material("hydrogen peroxide 35 % aq.", "liquid", 1131.0, 1.12e-3, 0.0745,
                   "EVONIK (1.131, 1.12 mPa s, 74.5 mN/m); ECHA (1.1282 at 25 C, 1.11, 74.6)",
                   density_range=(1128.2, 1131.0), viscosity_range=(1.11e-3, 1.12e-3))
H2O2_30 = Material("hydrogen peroxide 30 % aq.", "liquid", 1111.0, 1.11e-3, 0.0742,
                   "EVONIK (1.111 g/ml, 1.11 mPa s, 74.2 mN/m at 20 C)")
# household 3 %: linear interpolation 0 -> 30 % of the Evonik columns (estimate, not a measurement)
H2O2_3 = Material("hydrogen peroxide 3 % (household)", "liquid",
                  998.0 + 0.1*(1111.0 - 998.0), 1.0e-3 + 0.1*(1.11e-3 - 1.0e-3), 0.0728 + 0.1*(0.0742 - 0.0728),
                  "estimate: linear interpolation of EVONIK 0 % and 30 % columns",
                  note="~1 % denser/more viscous than water: dynamically essentially water")

CO2 = Material("carbon dioxide", "gas", 1.8393, 1.4675e-5, 0.0, "NIST (20 C; 1.8080, 1.4915e-5 at 25 C)",
               density_range=(1.808, 1.8393), viscosity_range=(1.4675e-5, 1.4915e-5))
HELIUM = Material("helium", "gas", 0.16631, 1.9618e-5, 0.0, "NIST (20 C; 0.16352, 1.9846e-5 at 25 C)",
                  density_range=(0.16352, 0.16631), viscosity_range=(1.9618e-5, 1.9846e-5))
ARGON = Material("argon", "gas", 1.6618, 2.2307e-5, 0.0, "NIST (20 C)")
METHANE = Material("methane", "gas", 0.66816, 1.0914e-5, 0.0, "NIST (20 C)")

SMOKE_SIGMA_S = 8.7            # m^2/g (MULHOLLAND)
SMOKE_LOADING = 1.0e-3         # kg/m^3: dense fire smoke, extinction K ~ 8.7 1/m (MULHOLLAND, JIN)
SMOKE_LOADING_RANGE = (0.1/SMOKE_SIGMA_S*1e-3, 10/SMOKE_SIGMA_S*1e-3)   # K = 0.1..10 1/m
SOOT_DENSITY = 1740.0          # kg/m^3 (CHOI)


def smoke(T_C=20.0, loading=SMOKE_LOADING):
    """Air at T carrying `loading` kg/m^3 of soot. Viscosity: hot air (ETB_air)
    times Einstein 1 + 2.5 phi (phi ~ 6e-7: negligible)."""
    T = T_C + 273.15
    rho_gas = AIR.density*T_REF_K/T
    mu_table = {20.0: 1.813e-5, 125.0: 2.279e-5, 200.0: 2.573e-5, 300.0: 2.928e-5}  # ETB_air
    mu = (AIR.viscosity if T_C == 20.0 else mu_table[T_C])*(1 + 2.5*loading/SOOT_DENSITY)
    hot = T_C > 20.0
    return Material(
        f"{'hot' if hot else 'cool'} smoke ({T_C:g} C, {loading*1e3:g} g/m3)", "smoke",
        rho_gas + loading, mu, 0.0,
        "MULHOLLAND; JIN (loading); CHOI (soot density, Einstein)" + ("; IDEAL_GAS; ETB_air" if hot else ""),
        T_C=T_C,
        density_range=((AIR.density*T_REF_K/573.15 + loading, AIR.density*T_REF_K/398.15 + loading) if hot
                       else (AIR.density + SMOKE_LOADING_RANGE[0], AIR.density + SMOKE_LOADING_RANGE[1])),
        viscosity_range=(2.279e-5, 2.928e-5) if hot else (),
        note=("125-300 C: rho 0.89-0.62 kg/m3, buoyant (needs gravity, absent here)" if hot else
              f"loading range {SMOKE_LOADING_RANGE[0]*1e3:.3f}-{SMOKE_LOADING_RANGE[1]*1e3:.2f} g/m3"))


SMOKE_COOL = smoke(20.0)
SMOKE_HOT = smoke(200.0)
FOG_LWC = 0.5e-3               # kg/m^3, thick fog band (as in fluid_shelter.py)

LIQUIDS = {"water": WATER, "hard_water": HARD_WATER, "h2o2_100": H2O2_100, "h2o2_35": H2O2_35,
           "h2o2_30": H2O2_30, "h2o2_3": H2O2_3}
GASES = {"air": AIR, "smoke_cool": SMOKE_COOL, "smoke_hot": SMOKE_HOT, "co2": CO2,
         "helium": HELIUM, "argon": ARGON, "methane": METHANE}
ALL = {**LIQUIDS, **GASES}


@dataclass
class MaterialParams(FluidParams):
    liquid: str = "water"
    gas: str = "air"
    scale: float = 1.0          # s = min density (air units); forces divided by s
    rho_gas: float = 1.0        # gas density / s
    band_excess: float = 0.0    # band tracer density excess / s
    miscible: bool = False      # True: no Cahn-Hilliard, phase field diffuses like dye
    push_phys: float = 0.0      # push in air-reference units (what we report)
    anxiety_phys: float = 0.1
    sigma_base: float = 1.0
    sigma_phys: float = 0.0     # base_sigma * sigma_mat/sigma_water (before /s)
    dt_floor: float = 2e-5      # stop if the CFL step collapses below this ...
    max_wall: float = 240.0     # ... or a run exceeds this many wall seconds


class StoppedRun(FloatingPointError):
    """Run stopped: blow-up in progress (CFL step collapse) or wall-clock cap."""


def pair_params(liquid, gas, push=0.0, base_sigma=1.0, anxiety=0.1, sigma_override=None,
                miscible=False, **kw):
    """MaterialParams for a shelter `liquid` (Material) in surrounding `gas`."""
    rl, rg = liquid.density/AIR.density, gas.density/AIR.density
    s = min(rl, rg)
    mu_g = 0.01*gas.viscosity/AIR.viscosity            # model mu_air = 0.01 for real air
    sig = (base_sigma*liquid.sigma_air/WATER.sigma_air if sigma_override is None else sigma_override)
    band = (SMOKE_LOADING if gas.kind == "smoke" else FOG_LWC)/AIR.density
    return MaterialParams(rho_ratio=rl/rg, mu_ratio=liquid.viscosity/gas.viscosity, mu_air=mu_g/s,
                          sigma=sig/s, anxiety=anxiety/s, push=push/s, liquid=liquid.name,
                          gas=gas.name, scale=s, rho_gas=rg/s, band_excess=band/s,
                          miscible=miscible, push_phys=push, anxiety_phys=anxiety,
                          sigma_base=base_sigma, sigma_phys=sig, **kw)


class MaterialShelter(FluidShelter):
    """FluidShelter with a general gas density and band excess; optional
    miscible (smoke) ring whose phase field is a diffusing passive scalar."""

    def density(self, phi, fog):
        p = self.p
        H = np.clip((1 + phi)/2, 0, 1)
        return p.rho_gas + (p.rho_gas*p.rho_ratio - p.rho_gas)*H + p.band_excess*fog*(1 - H), H

    def step(self):
        if not hasattr(self, "_t0"):
            self._t0 = time.time()
        super().step()
        if not np.isfinite(self.last_dt) or self.last_dt < self.p.dt_floor:
            raise StoppedRun(f"CFL step collapsed (dt={self.last_dt:.1e}) at t={self.t:.2f}")
        if time.time() - self._t0 > self.p.max_wall:
            raise StoppedRun(f"wall-clock cap {self.p.max_wall:.0f}s hit at t={self.t:.2f}")

    def rhs(self, st, t):
        out = super().rhs(st, t)
        if self.p.miscible:
            u, v = (np.real(np.fft.ifft2(q)) for q in st[:2])
            phi = np.real(np.fft.ifft2(st[2]))
            f2 = np.fft.fft2
            out[2] = (-(1j*self.kx*f2(u*phi) + 1j*self.ky*f2(v*phi))*self.mask
                      - self.p.kappa*self.k2*st[2])
        return out


def closure_loss_time(history, level=0.1):
    """First sampled time at which ring closure drops below `level` (None if never)."""
    return next((h["t"] for h in history if h["integrity"] < level), None)


def run(p, **kw):
    r = fluid_run(p, sim_cls=MaterialShelter, **kw)
    h = 2*p.layer*0.5*(p.ring_a + p.ring_b)
    rho_l = p.rho_gas*p.rho_ratio*p.scale                # liquid density, air units
    r["weber"] = (rho_l*r["peak_ring_speed"]**2*h/p.sigma_phys) if p.sigma_phys > 0 else float("inf")
    r["t_closure_lost"] = closure_loss_time(r["history"], 0.1)
    r["t_closure_half"] = closure_loss_time(r["history"], 0.5)
    return r


def job(item, snap_times=()):
    """Run one case; on a blow-up retry ONCE with the max step halved."""
    group, p = item
    tries = []
    for q in (p, replace(p, dt=p.dt/2)):
        try:
            r = run(q, snap_times=snap_times)
            r.update(group=group, attempts=tries + ["ok"], dt_used=q.dt)
            return r
        except FloatingPointError as e:
            tries.append(f"dt={q.dt:g}: {str(e)[:70]}")
            if "wall-clock" in str(e):
                return dict(group=group, params=p.__dict__, label="stopped (too slow)",
                            attempts=tries, snapshots={})
    return dict(group=group, params=p.__dict__, label="blow-up", attempts=tries, snapshots={})


def table_rows():
    rows = []
    for key, m in ALL.items():
        rows.append(dict(key=key, name=m.name, kind=m.kind, T_C=m.T_C, density=m.density,
                         viscosity=m.viscosity, sigma_air=m.sigma_air,
                         density_range=m.density_range, viscosity_range=m.viscosity_range,
                         source=m.source, note=m.note))
    return rows


if __name__ == "__main__":
    for r in table_rows():
        print(f"{r['key']:11s} rho={r['density']:10.5g} mu={r['viscosity']:.4g} sig={r['sigma_air']:.4g} "
              f"| {r['source']} | {r['note']}")
    for hd in (120, 180):
        m = hard_water(hd)
        print(hd, m.density, m.viscosity, m.note)
