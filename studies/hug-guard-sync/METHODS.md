# Old and updated Hug: live loss and recovery of orbital repetition

This test extends the [evolving-guard comparison](../hug-active-guard/METHODS.md) by repeating the [earlier stiffness intervention](../dynamics-fractals-sims/HUG_SYNC_METHODS.md). It compares confirmation delays directly. The participant and guard equations, added damping, synthetic Burgers clay parameters, mass, feedback, length and volume remain unchanged from that comparison. The new intervention changes only the restoring stiffness.

## Matched experiment

Baseline stiffness is 0.7 N/m. It doubles to 1.4 N/m at elapsed time 171 seconds and returns to baseline at 741 seconds. The integration ends at 4161 seconds. Controls either retain baseline stiffness throughout or leave it high after the first switch. Both models use circular, Pasiphae, Elara, Himalia, Europa, Callisto and Thebe inputs with the same 5.7-second period, 6 micronewton force RMS and signed Kepler waveform. These names select eccentricity, not real lunar periods or forces.

There are 2 models × 3 intervention arms × 7 inputs × 2 histories = **84 live trajectories**, each integrated at two accuracy settings. The old model continues exactly the two published robustness states at absolute time 6000 seconds. The updated model first settles its two declared initial conditions from time 0 to 6000; this preparation is repeated independently at each accuracy. Its last 41 orbit-phase samples must repeat and the two histories must agree. The ensuing baseline stage must pass for every live trajectory pair. These settled histories do not constitute independent new basin samples.

The orbital clock is always absolute time 6000 + elapsed time during the intervention. Displacement, velocity, both internal clay strains and all updated participant/guard states remain continuous at each stiffness switch. No restoring of stored states, phase reset or phase correction is applied. A segment boundary is a solver handoff carrying the complete state forward.

The changing spring exchanges work with an external mechanism:

```text
delta W = 0.5 * (k_after - k_before) * q^2.
```

This work is added to active-feedback work and orbital work in the mechanical energy audit. Clay dissipation and guard damping are subtracted. Lowering stiffness can extract energy. The old and new mechanical equations differ through the previously declared guard damper; differences in recovery cannot be assigned to adaptation alone without a further frozen-damper comparison.

## Confirmation times, not exact onset times

The primary diagnostic preserves the old rule: once per full orbit, compare a state with its values 1, 2, 3 and 4 orbits earlier. For each lag take the largest absolute scaled-component difference over 20 successive comparisons and both histories. At least one lag must fall below 0.0001, the two histories must agree within 0.0001 at the current sample, and the motion must exceed the existing observable-amplitude threshold. The four old states are compared against all eight updated states. A separate four-state projection of the updated model shows whether its hidden states delay confirmation.

Each constant-stiffness stage starts a fresh diagnostic window. It takes 24 stroboscopic states to assess all four lags, so the earliest assessment is 23 orbits (131.1 seconds) into a stage. The animation labels the intervening period **assessing**. Window resets never reset a trajectory. As in the historical implementation, the nontrivial-motion check uses the minimum displacement half-range across the two histories over that stage; it is a retrospective stage check, not an instantaneous detector.

Sustained loss is the first assessed time after which every remaining assessment in the high-stiffness stage reports no short repeat. Sustained recovery is the first assessed time after which every remaining recovery-stage assessment passes. Delay is measured from restoration at 741 seconds. Recovery is only reported when loss was confirmed. No loss, no regained repeat, and right-censored recovery are valid scientific outcomes, not numerical failures to hide. No confirmed 1–4 orbit repeat does not establish chaos or exclude all other frequency ratios. Confirmation times include the waiting window, have 5.7-second grid resolution, and are checked retrospectively through 4161 seconds.

Old-model delays are recomputed and compared with the historical published delays. The scientific outcomes are not acceptance gates. Numerical and initial-settlement gates were frozen before integration, including source hashes in [freeze.json](freeze.json).

## Numerical verification

Main DOP853 settings are relative tolerance 2e-9, absolute tolerance 2e-11 and maximum step 0.15 seconds. The refined settings are 2e-11, 2e-13 and 0.075 seconds. Both split exactly at the imposed stiffness switches and retain state across 300-second storage blocks. Every live state is saved at 0.05-second spacing. The complete saved path is compared, not only selected animation clips.

The fixed gates require scaled full-state path discrepancy below 0.0002; scaled mechanical energy residual below 0.00001; matching diagnostic status timelines; confirmation-time differences no larger than one orbit; and bounded guards. The energy tolerance is stricter than the historical 0.001 gate. State scales are q/Q, qdot/Q, u/(Q/L), w/(Q/L), xA, xB, gAB and gBA, with Q = 0.1 mm and L = 0.1 m. Energy is normalized by the baseline (k + V G_M/L²)Q² throughout, including after switches.

Forty-two independent physical-unit Radau segments span each switch and late recovery in both models and all seven orbital inputs. Each starts from the saved state at the beginning of its segment and is split at the exact intervention time. Its maximum scaled state discrepancy must be below 0.00002. These segments validate evolution over their windows; the separate main/refined path comparison checks accumulated discrepancies across the full experiment.

Unit tests check schedules, exact spring-work jumps, hidden guard drift, four-orbit repetition, incomplete windows, disagreement between histories, quiet motion, transient false passes and the unchanged force clock. A passive unforced piecewise linear case is checked against exact matrix-exponential propagation for every intervention arm.

## Animation and interpretation

The [player](player.html) uses saved motion. Solid outlines show the current state, dotted outlines the same trajectory one orbit earlier. Old and updated models share the same clock and selected orbital input. It includes both histories and all three intervention arms. Explicitly labelled clips skip long waiting periods; the dynamics are never restarted. Status labels use the latest completed assessment, with duplicate switch timestamps resolved to the new stage. Quantitative timelines and confirmation delays use full precision; displayed shape samples use float32.

The display map is x′ = x + 150(q/L)y, y′ = y. It magnifies shear and preserves joins by construction. It is not a contact, rupture or moving-boundary calculation. Parameters, guard time mapping and damper strength remain synthetic. No physical clay measurements or real astronomical predictions are added.

## Reproduce

Keep this folder beside `hug-active-guard` and `dynamics-fractals-sims`. In a repository checkout, first follow its numerical-data restoration instructions so the historical initial states are present. Install the requirements, then from this study directory:

```sh
python -m unittest -v
python guard_sync.py --cache .cache --kind main
python guard_sync.py --cache .cache --kind fine
python analyze_sync.py --cache .cache
python report_sync.py --cache .cache
python verify_saved.py
node check_player.cjs
```

Each run refuses an existing cache directory. Preserve the published results by reproducing in a separate checkout. Raw memory-mapped trajectories remain local; sources, preparation/switch records, diagnostic timelines, comparisons, plot data and animation samples are published. Optional GIF export uses `python report_sync.py --cache .cache --gif-dir animation-export`. This updates the repository, not a website deployment.
