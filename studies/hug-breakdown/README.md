# Hug breakdown: how a hugged fluid holds, breaks and recovers

Two small 2D Navier-Stokes models of the SIMS idea "inner pressure (anxiety) is a
fluid; a hug boundary keeps it from ingesting its surroundings; an outside push
(drug, shock) can break it".

1. `hug_breakdown.py`: **clay hug**. Single fluid, vorticity-streamfunction,
   pseudo-spectral FFT, periodic box [0,2pi)^2, 2/3 dealiasing, RK2 (Heun). The
   wall is an elliptic band (semiaxes 1.6 x 1.3) with Brinkman penalization
   `-K g chi u`, computed in velocity space and then curled. `K = 1/eta` is the hug
   pushback. The clay integrity `g` in [0,1] yields where the fluid moves through
   the wall faster than `yield_speed = 0.25` and recovers toward 1 elsewhere. It
   uses a smooth tanh switch, and the exact ODE step keeps g in [0,1].
2. `fluid_shelter.py`: **fluid shelter**. The clay is replaced by real fluids.
   The inner air core holds the dye. Around it is a water layer, then a fog
   layer, then outside air. Surface tension holds the water together. The code is
   2D variable-density, variable-viscosity NS plus a Cahn-Hilliard phase field.
   The surface-tension force is `lam mu_c grad(phi)`. The projection uses a
   constant coefficient (Dodd & Ferrante 2014). Time stepping is SSP-RK3 with a
   CFL-limited step.

Both use the same anxiety (steady divergence-free swirl cells inside rho < 0.7,
A = 0.1) and the same push (Gaussian jet toward the right-hand wall,
`P exp(-t/1.5)`). Breakdown metrics:

* **leak** = fraction of the dye found beyond the outer edge of the wall at the end.
* **integrity**: clay = min g on the wall. Fluid = ring *closure*: in each of 48
  angular sectors, the largest water fraction present (near 0 = a gap opened).
* **break**: leak > 0.2 or integrity < 0.1. **Recovered**: integrity dipped below
  0.9 and is back above 0.9 at the end. Labels: hold, bend+recover, bent,
  break+heal, break.

Install: `python -m pip install -r requirements.txt`. Run: `python run_sweep.py` (about 4.5 min) and `python run_fluid_sweep.py`
(about 9 min on 8 cores). Tests: `python -m pytest -q tests` (40 tests across all models, about 1 min).

## Real fluid values used (about 20 C, 1 atm)

| quantity | value | source |
|---|---|---|
| water density | 998.2 kg/m^3 | CRC Handbook of Chemistry and Physics / NIST |
| water dynamic viscosity | 1.002e-3 Pa s (kinematic 1.004e-6 m^2/s) | CRC Handbook; IAPWS 2008 viscosity release |
| air density | 1.204 kg/m^3 | CRC Handbook / US Standard Atmosphere |
| air dynamic viscosity | 1.81e-5 Pa s (kinematic 1.50e-5 m^2/s) | CRC Handbook |
| water-air surface tension | 0.0728 N/m | IAPWS 2014 surface-tension release (72.74 mN/m at 20 C) |
| fog liquid water content | 0.05-0.5 g/m^3 | Rogers & Yau, *A Short Course in Cloud Physics* (table in course notes); ITU fog model (MATLAB `fogpl` docs) |

These give the ratios the code uses: density ratio 998.2/1.204 = **829** (the real
value is used in the main fluid sweep), dynamic viscosity ratio **55.4**, and fog
density excess at most 0.5e-3/1.204 = **0.04 %**. Real fog is dynamically almost
plain air. The model includes the fog only as that density excess on an advected
fog tracer, so it has no visible effect. That is the honest result, not a modeling
choice. Surface tension enters only through the nondimensional `sigma`, swept as
0, 0.3, 1, 3 and 10. A Weber number `We = rho_w U_ring^2 h / sigma` is reported per run.
Matching the real 0.0728 N/m would need a physical length and velocity scale,
which this metaphor does not have.

## Results (key numbers in `results/*.csv`)

**Clay hug** (`results/hold_break_map.png`), with P in {2,5,10,20,40} and K in {3,8,25,60}:
* Anxiety alone, with no push, breaks the soft hugs: K=3 leak 0.57 and g goes to 0;
  K=8 leak 0.28. The stiff ones hold: K=25 leak 0.08, K=60 leak 0.05.
* K=25 holds at P=2. At P=5, 10 and 20 it breaks and then heals: the wall
  re-closes (g_end 0.99) but the dye has already left (leak 0.12, 0.47, 0.70). At P=40 it breaks for good.
* K=60 holds up to P=5. At P=10 the wall opens briefly (min g 0), leak is only
  0.08, and it heals. At P=20 and 40 it breaks and heals (leak 0.38, 0.71).
* Push with no anxiety (P=40): it breaks at every K; only K=60 heals. No wall at all: leak 0.97.
* How it breaks: a positive feedback. Fast flow through the wall softens g, which
  lets more flow through. How it recovers: once the push fades, the wall speed
  falls below the yield level and g relaxes back. Leaked dye does not come back.
* N=96 check (K=25, P=10 and 20): leak 0.467 and 0.699, against 0.469 and 0.699 at N=64.

**Fluid shelter** (`results/fluid_hold_break_map.png`, `fluid_snapshots.png`,
`fluid_density_trend.png`), real density ratio 829:
* Every sigma, including 0, holds at P <= 10 with leak <= 0.03 and closure >= 0.93.
  The exception is sigma=0, P=10, which is "bent" (closure 0.86). At this density
  the water layer's **inertia** does most of the holding.
* Every sigma breaks at P=20 (leak 0.22-0.52, closure < 0.1). The way it breaks
  depends on surface tension:
  * sigma=0: shatters into 8 pieces (fingers and droplets).
  * sigma=0.3-3: rupture with 1-2 pieces pinched off.
  * sigma=10: the ruptured ring pulls itself into one drop, which un-wraps the
    core. Leak is 0.47.
  Surface tension minimizes interface, so it does not re-close a broken ring.
* Not one broken fluid shelter re-closed. Clay heals; this water does not.
* P=40: sigma=0.3 and sigma=1 break. sigma=0, 3 and 10, and the no-anxiety
  control, **blew up numerically** and have no result. Halving dt to 0.002 did not
  fix them; the no-anxiety case did run at dt=0.002 and broke (leak 0.66). The
  sigma=1, P=40 end state is water smeared into near-uniform mush. That is
  diffuse-interface dissolution of an under-resolved break-up, not physics.
* Density-ratio trend (P=10, sigma=1): ratios 1, 3, 10 and 30 break (leak 0.58,
  0.82, 0.80, 0.60). 100 is bent (leak 0.03, closure 0.15). 300 holds (0.015).
  829 holds (0.015). A capped ratio would have changed the answer, so the main
  sweep uses the real ratio.
* Time-step check at P=20: sigma=1 leak 0.218 at dt=0.004 vs 0.145 at dt=0.002;
  sigma=3 0.355 vs 0.44. The labels are unchanged, but the numbers carry roughly
  30 % uncertainty after break-up.
* Still circular drop (sigma=1, ratio 10): spurious currents reach max |u| = 8.3e-3,
  against a capillary speed sigma/mu_w of about 1.8.

## Honest scope and limitations

* This is a **model** that uses the NS equation as an engine for a SIMS-style
  metaphor. It is 2D, with walls, forcing, and (in variant 2) two phases with
  variable density and viscosity and surface tension. The Clay Millennium problem
  is single-phase, constant viscosity, 3D on R^3 or the torus, with no walls and no
  such forcing. **Nothing here says anything about the Clay problem.**
* The findings are about this model only. They make no claim about real people,
  anxiety, drugs or psychology.
* The clay wall is a penalization, so it is porous rather than an exact no-slip
  wall. "Yield on speed through the wall" is a chosen rule.
* Fluid shelter details:
  * Time stepping is fully explicit and first-order accurate in the lagged-pressure correction.
  * The interface is resolved by only about 2 cells (eps = 0.075 at N=64).
  * The Cahn-Hilliard mobility 1e-4 and the interface-keeping are numerical choices.
  * With sigma = 0 the force is switched off but Cahn-Hilliard still keeps a sharp interface.
  * The viscosity ratio is real (55.4), but absolute values are nondimensional
    (mu_air = 0.01, matching the clay model).
  * There is no gravity.
  * The mean momentum is held at zero.
  * The "fragments" count uses phi > 0 with periodic 4-neighbour connectivity.
  * Leak edges differ: the clay outer edge is rho > 1.12 and the fluid outer edge
    is rho > 1.2, because the water layer is thicker so that it can be resolved.

## Combined shelter: water layer + clay lining (`combined_shelter.py`)

`CombinedShelter` is a small subclass of `FluidShelter`. It uses the real density
ratio 829 and the real viscosity ratio. It adds the clay model's Brinkman wall,
`-K g chi u`, as a lining band (normalised radius 0.72-0.88) on the inner side of
the water layer, between the anxious air core and the water. The lining's g uses
`hug_breakdown.update_integrity` with the clay yield speed (0.25) and the clay
yield and recovery rates. The anxiety, fading push, dye, leak metric and
`classify()` are the same as before.

**Shelter integrity** = max(water ring closure, lining min g). The shelter counts
as open only when both layers are open.

**Note:** this is a global measure, not tied to a location. The two layers could
be open at different places at the same moment and still count as "closed". The
ring closure and the lining g are also recorded separately.

The sweep covers P in {0, 2, 5, 10, 20, 40} × sigma in {1, 3} × K in {25, 60}
(`run_combined_sweep.py`, about 17 min on 8 cores). Blown-up runs were retried
once at half the time step. Results are in `results/combined_results.csv`,
`results/combined_results.json` and `results/combined_compare.png`. The clay-only
and water-only rows come from the earlier result files and were not rerun.
There is no water-only sigma=3, P=0 row, because that case was never computed.

**Results**

* **Up to P = 20, the combination holds better than either layer alone.**
  * Combined: all 8 runs at P = 20 hold. Leak is 0.007, against 0.22 and 0.35 for
    water-only and 0.70 and 0.38 for clay K=25 and K=60. The lining barely yields
    (min g ≥ 0.987) and the water ring stays closed (≥ 0.93).
  * Below P = 20, leak is 0.006-0.007 at every P. That is lower than water-only
    (0.009-0.02) and clay-only (0.05-0.47).
  * Mechanism: the lining drags the push jet down before it reaches the water, so
    the water ring is never hit hard.
* **P = 40 depends on the case.**
  * sigma=3, K=25: holds. Leak is 0.011. The lining opens fully (min g 0.003)
    and heals (end g 0.95). The water ring thins (closure 0.64) but does not break.
    Label: bend+recover.
  * sigma=1, K=25: the dye stays in (leak 0.034). The water ring ruptures and
    pinches off (closure 0.03, 2 pieces) and does **not** re-close. The lining
    opens fully and heals (end g 0.95). Label: bend+recover, because the healed
    lining counts as closing the shelter.
  * sigma=1, K=60: breaks. Leak is 0.71, the lining ends at g = 0 and the ring
    ends at closure 0.11. This is a single run and stiffer did worse than K=25,
    so treat it as sensitive to the exact conditions, not as a trend.
  * sigma=3, K=60: blew up numerically at both time steps. No result.
* **Healing:** the clay lining re-closes after being fully opened in both
  K = 25 cases at P = 40. The water ring never re-closed in any run, alone or
  combined.

**Limitations (in addition to those above)**
* A single N = 64 resolution, with no resolution or time-step check for this variant.
* The lining is a porous Brinkman drag on the near-interface fluid, not a material.
* The P = 40 outcomes split by case and include a blow-up, so they should not be
  read as a smooth trend.
* The leak edge (normalised radius > 1.2) matches the water-only model; clay-only
  used > 1.12.

## More fluids: smoke, gases, hard water, peroxide (`materials.py`)

`materials.py` holds a table of real property values at 20 C and 1 atm, each with
a source string (the full citations are in `materials.SOURCES`). It maps any
shelter liquid / surround gas pair onto the fluid-shelter model:

* Density is measured in units of air at 20 C. Viscosity is the model's
  `mu_air = 0.01` scaled by the real `mu/mu_air`.
* `sigma_model = base_sigma x sigma_liquid / sigma_water-air`.
* The inner core gas and the outer gas are both the chosen gas. The band outside
  the ring is a passive tracer layer carrying a small density excess: 1 g/m^3 of
  soot for the smoke surrounds, and the original 0.5 g/m^3 fog for the others.
* Anxiety and push are the same **force per volume** in every gas.
* The Dodd-Ferrante splitting in `fluid_shelter.py` assumes rho0 = 1 = the
  smallest density. So `MaterialShelter` divides every density, viscosity,
  sigma and force by `s = min(rho_liquid, rho_gas)`. This is an exact rescaling:
  velocities are unchanged.
* With water in air the mapping reproduces the original `FluidShelter` to
  round-off (this is tested).

Run: `python run_materials_sweep.py` (45 runs, 351 s on 5 workers),
`python run_materials_sweep.py dtcheck` (4 reruns at dt = 0.002, 67 s), and
`python run_smoke_vs_hardwater.py` (20 runs, 246 s on 3 workers). Tests:
`python -m pytest -q tests/test_materials.py` (21 tests, about 14 s).

| material (20 C, 1 atm) | density kg/m^3 | viscosity Pa s | sigma vs air N/m | source |
|---|---|---|---|---|
| water | 998.21 | 1.0016e-3 | 0.0728 (IAPWS 72.74 mN/m) | NIST WebBook; IAPWS R1-76(2014) |
| hard water, 180 mg/L as CaCO3 (top of USGS "hard" 121-180) | 998.43 (+0.0225 %) | 1.0022e-3 (+0.056 %) | 0.0728 (change < 0.01 mN/m) | USGS hardness classes; Sharqawy, Lienhard & Zubair 2010 salt correlations (computed, proxy); Weissenborn & Pugh 1996 |
| hard water, 120 mg/L | 998.36 (+0.015 %) | +0.037 % | 0.0728 | same |
| H2O2 100 % | 1450 (range 1442.5 at 25 C to 1450) | 1.25e-3 (1.245-1.25e-3) | 0.0804 | Evonik H2O2 property table; EU RAR / ECHA 2003; CRC |
| H2O2 35 % aq. | 1131 (1128.2 at 25 C) | 1.12e-3 (1.11-1.12) | 0.0745 | Evonik; ECHA |
| H2O2 30 % aq. | 1111 | 1.11e-3 | 0.0742 | Evonik |
| H2O2 3 % (household) | ~1009 | ~1.01e-3 | ~0.0729 | *estimate*: linear interpolation of Evonik 0 % / 30 %. Dynamically essentially water |
| air | 1.204 | 1.81e-5 | - | CRC; Engineering ToolBox (18.13 uPa s) |
| cool dense smoke (air + 1 g/m^3 soot) | 1.205 (range 1.204-1.205 for 0.011-1.15 g/m^3) | 1.81e-5 (Einstein factor 1 + 1.4e-6) | 0 | Mulholland & Croarkin 2000 (8.7 m^2/g, so C = K/8.7); Jin 1978 / SFPE (K ~ 0.1-10 1/m); Choi et al. 1995 (soot 1.74 g/cm^3) |
| hot smoke, 200 C | 0.747 (range 0.62 at 300 C to 0.89 at 125 C) | 2.57e-5 (2.28-2.93e-5) | 0 | ideal gas from air at 20 C; Engineering ToolBox air viscosity vs T |
| CO2 | 1.8393 (1.808 at 25 C) | 1.4675e-5 | - | NIST WebBook |
| helium | 0.16631 (0.16352 at 25 C) | 1.9618e-5 | - | NIST WebBook |
| argon (in table, not swept) | 1.6618 | 2.2307e-5 | - | NIST WebBook |
| methane (in table, not swept) | 0.66816 | 1.0914e-5 | - | NIST WebBook |

Notes on the table:

* **Hard water.** The hardness is treated as Ca(HCO3)2, so 180 mg/L as CaCO3 is
  0.292 g/kg of dissolved solids. The change from pure water is computed with
  the seawater correlations (which are NaCl-dominated, so this is a proxy). It
  is far below 1 %.
* **Liquid-CO2 and liquid-He surface tension.** The value against air is used.
  At 1 atm, gas adsorption lowers sigma only slightly (Massoudi & King 1974);
  that small change is not separately quantified here.

Sources:

* NIST WebBook fluid properties: https://webbook.nist.gov/chemistry/fluid/
* Evonik H2O2 property table:
  https://www.evonik.com/en/company/businesslines/ao/products-and-services/hydrogen-peroxide/general-information/physico-chemical-properties.html
* EU Risk Assessment Report, H2O2 (2003):
  https://www.echa.europa.eu/documents/10162/590965ca-33e7-43a0-a109-3a9148870d07
* USGS hardness classes: https://www.usgs.gov/water-science-school/science/hardness-water
* Engineering ToolBox air viscosity: https://www.engineeringtoolbox.com/air-absolute-kinematic-viscosity-d_601.html
* Mulholland & Croarkin, Fire and Materials 24:227 (2000)
* Sharqawy et al., Desalination and Water Treatment 16:354 (2010)
* Weissenborn & Pugh, J. Colloid Interface Sci. 184:550 (1996)
* Choi et al., Combust. Flame 102:161 (1995)
* Massoudi & King, J. Phys. Chem. 78:2262 (1974)

**Sweep results** (`results/materials_map.png`, `materials_snapshots.png`,
`materials_results.csv`). Liquid {water, hard water, H2O2 100 %} x gas {air,
cool smoke, hot smoke, CO2, helium} x P {5, 10, 20}, base sigma 1, A 0.1,
n 64, t_end 20:

* **P = 5:** all 15 combinations hold (leak <= 0.011, closure >= 0.97).
* **P = 10:**
  * Water and hard water hold in air, cool smoke, hot smoke and CO2.
  * Both are "bent" in helium (closure 0.90).
  * H2O2 is bent in air and cool smoke (closure 0.89) and in helium (closure
    0.47, one piece pinched).
  * H2O2 holds in hot smoke and CO2.
* **P = 20:** every result is a break, except as follows.
  * Helium blew up (see below).
  * H2O2 in air and cool smoke were "bent" (leak 0.03, closure 0.13-0.14, a
    pinch-off) at dt = 0.004. **At dt = 0.002, H2O2 in air breaks** (leak 0.30,
    closure 0.04). So it sits right at the threshold, and its label is not robust.
  * Break mode is pinch-off into 2-4 pieces.
  * The surround gas sets **when** the ring opens. Closure first drops below 0.1 at:

    | ring | hot smoke (0.75 kg/m^3) | air / cool smoke | CO2 (1.84) |
    |---|---|---|---|
    | water | t = 9.3 (leak 0.43) | t = 12.0 (leak 0.22) | t = 16.3 (leak 0.12) |
    | H2O2 | t = 9.3 | - (not below 0.1 at dt = 0.004) | t = 17.8 |

    The order holds at dt = 0.002 (water: hot smoke t = 10.5, CO2 t = 18.5).
  * Why: the push delivers the same force and impulse in every gas. A lighter
    gas carries less momentum itself, so more of the push lands on the ring.
    This is inertia only, not buoyancy.
* **Hard water = water.** Every hard-water number matches water to 2-3 digits.
  The +0.02 % density does nothing. The one exception is hot smoke at P = 20
  (leak 0.43 vs 0.30). That is the known post-break-up sensitivity: the dt
  check gave water 0.26.
* **Cool smoke = air.** The surround's +0.08 % density changes nothing, like fog.
* **Helium.** Helium is 7.2x lighter than air, so the same force drives the
  helium core about 7x harder.
  * P = 10 first blew up at dt = 0.004 for all three liquids. All three ran at
    dt/2 = 0.002: water and hard water are bent (closure 0.90); H2O2 is bent
    with a pinch-off (closure 0.47).
  * **P = 20 blew up at both dt = 0.004 and dt = 0.002 for every liquid**,
    around t = 1.7-2.2. The speed passes ~1e3 and the CFL step collapses below
    2e-5. There is no result for these runs.
* After break-up the numbers carry roughly 30 % uncertainty (dt check:
  `results/materials_dtcheck.json`). Labels at P <= 10 are robust.

## Smoke vs hard water (`run_smoke_vs_hardwater.py`, the separate test)

This is a head-to-head in air with the same ring geometry, A = 0.1, P in
{0, 2, 5, 10, 20}, t_end 20 (`results/smoke_vs_hardwater.png`, `.json`):

* (a) **hard-water ring**: density ratio 829.3, sigma = 1.
* (b) **cool smoke ring** (1 g/m^3): density ratio **1.0008**, viscosity ratio
  1.0000, **sigma = 0**. The phase field is kept, so Cahn-Hilliard still holds an edge.
* (b2) the same smoke made **miscible**: no Cahn-Hilliard, and the ring diffuses like the dye.
* (b3) **hot smoke ring** at 200 C: density ratio 0.62, viscosity ratio 1.42, sigma = 0.

| P | hard water: leak / closure min / t(closure < 0.5) | cool smoke: leak / closure min / t(closure < 0.5) / t(closure < 0.1) |
|---|---|---|
| 0 | 0.009 / 0.98 / never (hold) | 0.88 / 0.07 / 12.0 / 14.0 (break) |
| 2 | 0.009 / 0.98 / never (hold) | 0.89 / 0.05 / 4.3 / 11.5 (break) |
| 5 | 0.009 / 0.98 / never (hold) | 0.67 / 0.03 / 2.8 / 8.5 (break) |
| 10 | 0.015 / 0.93 / never (hold) | 0.93 / 0.03 / 1.8 / 8.0 (break, 8 pieces) |
| 20 | 0.22 / 0.07 / 9.5, < 0.1 at 12.0 (break) | 0.46 / 0.02 / 1.3 / 7.3 (break, 13 pieces) |

* **The hard-water ring holds up to P = 10 and breaks at P = 20.** It loses
  closure at t = 12.0.
* **The smoke ring breaks at every push, including P = 0.** With anxiety alone,
  0.88 of the dye leaks. Closure drops below 0.5 at t = 12 for P = 0 and at
  t = 1.3-4.3 for P >= 2. At the same P = 20, the smoke ring's closure goes
  below 0.5 at t = 1.3 against 9.5 for hard water (about 7x sooner), and below
  0.1 at t = 7.3 against 12.0.
* **The miscible and hot-smoke variants give the same verdict.** Miscible smoke
  ends with exactly the same leak (to 3 digits). At density ratio 1.0008 and
  sigma 0, the smoke is dynamically invisible: the flow, and so the dye, are
  the same whether or not the ring is there. Hot smoke: leak 0.68-0.88.
* The non-monotone smoke leak in P (0.46 at P = 20) is the unsheltered core's
  own chaotic mixing. It is not a property of the ring.
* **This is the physically honest result, not a bug.** A smoke ring has
  essentially nothing holding it together: no surface tension, no density
  contrast, no viscosity contrast. It smears and mixes with whatever moves it.
  In this model it shelters nothing.

## Scope and limitations of the materials work

* The model is 2D and has **no gravity**. Density enters only through inertia,
  so these effects are **not** captured: hot smoke's buoyant rise, CO2 sinking
  and pooling, helium rising, and drainage of the liquid ring.
* There is no heat transfer. A 200 C gas next to 20 C water would heat and
  evaporate it, and that is ignored.
* There is no peroxide chemistry, such as decomposition to O2 bubbles, and no
  soot deposition on the interface.
* Smoke is treated as a continuum with a tiny density excess. There is no
  particle slip and no particle-scale physics.
* sigma is still nondimensional (base 1). Only the material ratios are real;
  there is no physical length or speed scale.
* Helium at P >= 10 is at the edge of what this explicit scheme can run.
* Same model caveats as above. It is not the Clay Millennium problem, and the
  results are about this model, not about real people.
