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
(about 9 min on 8 cores). Tests: `python -m pytest -q tests` (15 tests, about 35 s).

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

## In progress

A combined variant, a water layer with a clay lining (the two walls above together), is in progress. It is not included here, and no results from it are reported.
