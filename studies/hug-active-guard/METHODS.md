# Comparing the old Hug with continuously evolving guards

This study implements a declared reduced mechanical realization of the [updated working equations](https://github.com/NousVolition/My-Sources-Project-ALL/blob/7fbc7f28f685c86f824d7587aff91feedf20d3da/reports/interaction-equation.md). It retains the old synthetic clay oscillator and adds the draft's two abstract participant states and directional guards. The optional dissipative fluid-stress loop becomes a variable mechanical damper. This mapping is a new modeling choice; the general working equation does not uniquely prescribe a Hug coupling.

[Illustrated comparison](report.html) · [Animation](player.html) · [Frozen protocol](protocol.json) · [Results](results.json) · [Model](model.py)

## Equations and interpretation

The original physical-unit mechanical equations remain

```text
sigma = G_M (q/L - u - w)
m qddot + k q + (V/L) sigma = F_orbit + (a - b q^2) qdot - c(g_AB+g_BA) qdot
udot = (sigma - G_K u)/eta_K
wdot = sigma/eta_M.
```

The added final term is absent in the old model. AB means **A receives from B**. A and B are dimensionless internal response states, not two solid arms, positions, or material concentrations. Both influence directions remain inside the equations:

```text
xA_dot = lambda (bA-xA) + kAB gAB (xB-xA)
xB_dot = lambda (bB-xB) + kBA gBA (xA-xB)
tau gAB_dot = sigmoid(theta + beta(xB-xA) + chi S) - gAB
tau gBA_dot = sigmoid(theta + beta(xA-xB) + chi S) - gBA
S = 0.5 [qdot/(Q/t_ref)]^2
sigmoid(z) = 1/(1+exp(-z)).
```

Here Q=0.1 mm, L=0.1 m and t_ref=1 simulation second. S is a normalized simple-shear strain-rate invariant: engineering shear rate is qdot/L, with reference Q/(L t_ref), and D:D is one-half its square. Values follow the illustrative draft: baselines (-0.55,0.35), lambda=1/s, tau=0.6 s, theta=-0.4, beta=2 and chi=0.5. Interpreting one unit of that abstract draft as one simulation second is an explicit, uncalibrated time mapping. The new damper coefficient c=0.01 N s/m per guard is also a chosen value, not a fitted viscosity or a derivation from the fluid simulation.

The full loop is motion -> shear rate -> directed guards -> resistance -> motion, with participant states and guards continuously influencing one another. Current values enter every integration stage. Increasing a guard increases transmission of abstract influence **and**, under this optional closure, mechanical damping. That common assignment is an assumption to test, not the meaning of every possible guard.

There is no replacement of the Burgers material law, no new reference-gradient material energy, no Navier-Stokes field, and no contact or rupture calculation in this comparison. No irreversible memory is assigned to the guards. The internal clay strains remain separate from the abstract participant/guard states. All parameters are synthetic; no clay observations were added.

## Matched comparison

There are eight settings: old; directional evolving with weights (1,1); directional (1.5,0.5); directional (0.5,1.5); shared evolving; frozen; strain feedback off; and active energy source off. Weights are ordered A receives B, B receives A and have units 1/s. The unequal pairs have the same sum as the equal pair. Realized gains kAB*gAB and kBA*gBA need not have a fixed sum.

The shared control averages the two sigmoid targets. The frozen control holds both guards at 0.5 for both starts. The strain-off control removes chi only. The active-source-off control removes both a and b, preserving guard dynamics and orbital force. These are different, named interventions. Old versus frozen adds resistance; frozen versus directional tests adaptation with the same c. Old versus directional includes both changes and cannot isolate adaptation by itself.

An exact null follows for shared versus directional guards at equal weights. Let d=xB-xA and G=gAB+gBA. Then d_dot=lambda[(bB-bA)-d]-G*d, while tau*G_dot is the sum of the two sigmoid targets minus G. Together with the mechanical states these form a closed subsystem in both versions. Matched initial d and G therefore give identical mechanical motion, despite different individual guards and participant means. The tests verify this identity. Any observed amplitude reduction cannot be attributed to directional asymmetry alone.

Each setting has no orbit, circular forcing, and six eccentric inputs: Pasiphae 0.412, Elara 0.212, Himalia 0.160, Europa 0.009, Callisto 0.007 and Thebe 0.018. The old signed Kepler waveform is retained, F = 6 microN * (a_orbit/r)^3 sin(2 true anomaly) / its time RMS. All forced cases have period 5.7 simulation seconds and the same force RMS. The orbit is prescribed; the guard does not change celestial motion. These are eccentricity-shaped loads, not physical lunar forces or periods. Both source and numerical force tests verify the equal RMS and zero mean.

Two starts differ in displacement, velocity, both clay strains and abstract states. The frozen control always begins with guards (0.5,0.5); unused old-model abstract states are zero. There are 8 settings x 8 conditions x 2 starts = **128 scientific trajectories**, each run at two accuracy settings. Integration is continuous from 0 to 4,200 seconds. There is no stiffness-switch intervention, so the earlier loss/recovery delays are not recalculated by this experiment.

## Energy and limiting controls

Mechanical energy includes kinetic energy, the parallel spring, Maxwell spring and Kelvin spring:

```text
E = m qdot^2/2 + k q^2/2 + V sigma^2/(2 G_M) + V G_K u^2/2
Edot = (a-b q^2) qdot^2 + F_orbit qdot
       - V[(sigma-G_K u)^2/eta_K + sigma^2/eta_M]
       - c(g_AB+g_BA) qdot^2.
```

The final term is nonpositive for guards in [0,1]. Changing its coefficient does not add elastic storage or a coefficient-derivative work term. The abstract states have no assigned mechanical energy. They regulate a passive damper; the old active source supplies the self-sustained oscillator's energy. The passive unforced mechanical energy cannot grow under these equations. A forced periodic passive motion is not an autonomous rhythm.

Unit checks compare the old limit directly with the published four-state right-hand side, verify an independent physical-unit implementation, check the energy derivative, exact passive frozen-damper matrix-exponential evolution, directional relabeling, guard interval invariance, live feedback paths, and a zero-damper limit. Known-period, hidden-guard-drift and quiet-signal tests check interpretation of the diagnostics.

## Numerical and scientific tests

DOP853 main settings are rtol 2e-9, atol 2e-11 and maximum step 0.15 s; refined settings are 2e-11, 2e-13 and 0.075 s. Both use the same frozen equations, parameters and starts. Integrations split into 300-second blocks only for storage; state and work counters pass continuously. They save every second, every 0.05 s for the first 60 s, and every 0.05 s over the last 456 s. The path-refinement gate applies to these **saved** full-state samples, not a certified continuous maximum. Work residuals are checked at the same samples.

Additional Radau comparisons use independently written physical-unit equations on early and late 11.4-second segments. They cover every model in the no-orbit, circular and Pasiphae conditions, plus old/primary-updated Elara: 52 segments. Late comparisons start from the saved main state and test the subsequent segment; they do not independently revalidate its entire earlier history. The main/refined whole-run comparison supplies the separate accumulated-error check.

Autonomous motion uses upward q=0 crossings. The last 20 pairs of full-state section crossings must agree within 1e-4, as must the final five corresponding section states across starts. A positive half-amplitude above 0.0001 mm is required. Cubic Hermite interpolation uses ODE derivatives. Repeating primary and evolving-control cycles also receive periodic shooting and a variational/Floquet calculation. One multiplier should be neutral in phase; transverse moduli below 0.9999 establish local attraction of that computed orbit. Analytic Jacobians are checked against central differences. This is local stability, not proof of a global basin.

Forced tests sample at one fixed phase of the full orbit over the final 80 orbits. The largest absolute scaled-state difference across the last 20 comparisons is tested for lags 1-4 orbits. At least one lag must pass 1e-4, and the two starts must agree within 1e-4 over the last 20 orbital samples. The old model assesses its four mechanical states; updated models assess all eight. A repeating outline alone cannot pass if hidden participant or guard states drift. Failure is reported as no confirmed 1-4 orbit repeat, not as chaos or a proof of absent phase locking at every rational ratio.

State scaling is [q/Q, qdot/Q, u/(Q/L), w/(Q/L), xA, xB, gAB, gBA]. Time is in simulation seconds. Thresholds, horizon and scientific cases were fixed in protocol.json before integration. No favorable scientific outcome was required. Numerical failures, if present, remain in results.json and must not be hidden by changing a tolerance.

## Plots and animation

Plots use saved main trajectories; statuses and stability results use full-precision analysis. The offline player shows the early interval and a late interval on the actual common simulation clock. It includes all eccentric inputs, both starts and all controls. A late status describes the full final 456-second diagnostic window; it is not a new instantaneous event detector. Early clips are explicitly unclassified.

The old and new outlines use the same affine display shear x'=x+150(q/L)y. Deformation is magnified 150 times. This drawing map preserves joins by construction; it does not prove a material boundary can withstand the load. Display samples are stored as little-endian float32 at 0.1-second spacing; quantitative tests use the original float64 cache. Switching clips jumps in time; playback within a clip does not restart the dynamics. A visible orbit clock shows prescribed forcing phase and fixed eccentricity geometry without implying physical backreaction.

## Reproduce

Keep this folder beside `dynamics-fractals-sims`, which supplies the unchanged forcing and outline. Install requirements, then from this folder:

```sh
python -m unittest discover -v
python run.py --cache .cache --kind main
python run.py --cache .cache --kind fine
python analyze.py --cache .cache
python report.py --cache .cache
```

The run script refuses to overwrite a cache. The pre-run freeze records the model, protocol and runner; the final source record also identifies dependencies and analysis. Preserve published results before reproducing in a separate checkout/copy. Optional `python report.py --cache .cache --gif-dir animation-export` exports a GIF. Large raw trajectory caches are local and excluded from Git; compact per-start diagnostics, both-resolution summaries, controls, animation samples and reproducible sources are published. There is no measurement upload or website deployment.
