# Hug rhythm robustness: a finite parameter sweep

This is batch 15 of the dynamics study. It tests the existing synthetic active Hug without an orbit and under circular and six eccentric Kepler-shaped inputs. It changes numerical coefficients, without changing the Burgers clay law or adding physical measurements. The measured properties of the user's clay remain unknown.

## Scope and chosen scenarios

The baseline is the unchanged [synthetic calibration fixture](calibration/synthetic_truth.json), with the equations and units documented in [the rhythm methods](HUG_RHYTHM_METHODS.md). This sweep uses the fixture's known parameters; it neither refits those parameters nor treats the perturbations as experimental uncertainty.

There are 35 settings:

- One baseline.
- Twelve one-at-a-time settings: multiply each of the two clay stiffnesses, two viscosities, parallel restoring stiffness and feedback saturation by 0.5 or 2.
- Six feedback-gain settings: multiply gain by 0, 0.02, 0.05, 0.1, 0.5 or 2. The gain-zero control also removes the cubic feedback term, so it is fully passive.
- Sixteen joint settings: independently sample all seven multipliers uniformly from 0.75 to 1.25 with seed 20261013. These are reproducible sensitivity scenarios, not a probability distribution for real clay or a confidence interval.

Every setting uses two starts, [0.25, 0, 0, 0] and [-1, 0.2, 0.02, -0.01], in the established scaled state. Each is tested without forcing, with circular forcing, and with the saved eccentricities of Pasiphae, Elara, Himalia, Europa, Callisto and Thebe. Mass, geometry and controller delay remain fixed. The default orbital period is 5.7 simulation seconds and the force RMS is 6 micro-newtons. Four extra baseline conditions test circular and Pasiphae inputs at 4 and 6.3 seconds. That gives 284 setting/forcing pairs and 568 individual trajectories per numerical resolution.

The labels identify waveform eccentricities only. They do not reproduce the moons' physical periods, forces, distances or a clay sample moving through space. Inputs have equal time RMS; peak forces and waveform shapes can differ. No orbital frequency is adjusted to follow a changed natural rhythm, which makes loss of synchronization informative.

## Numerical method and checks

Each trajectory is integrated for 6,000 simulation seconds using classical fourth-order Runge-Kutta at a 0.0125-second step. The complete ensemble is independently repeated at 0.00625 seconds. Each row is a separate ODE trajectory: vectorized evaluation does not couple rows. Orbital forces are evaluated at all RK stages using period-aligned, exactly repeating samples of the pinned Kepler formula; no force interpolation is used.

The state and three work integrals use the same established scaling. The work terms track active input, orbital input and clay dissipation. The energy residual is checked every second. Nonfinite states or a magnitude above 1,000 scaled units are recorded as an integration guard, never interpreted as a proven physical instability.

The final 600 seconds are sampled every 0.05 second. Period and amplitude use the existing hysteretic crossing estimator. Full-state section and stroboscopic comparisons use cubic Hermite interpolation with ODE slopes. Forty-six independent 12-second Radau controls use the physical-unit equations: one for each unforced parameter setting and every baseline forcing condition. They start from the main trajectory's late state, so these validate local integration rather than independently repeating the entire transient.

The initial 0.025/0.0125-second sweep, sampled every 0.1 second, passed period, amplitude and classification refinement but failed two numerical accuracy gates. Its maximum accumulated energy error was about 0.00423 scaled units, and its worst independent comparison error was about 0.000309. A diagnostic separated stored-node error (about 0.0000091 in that case) from interpolation error between the 0.1-second samples. The entire sweep was repeated with finer integration and output sampling; the acceptance thresholds and scientific settings were kept unchanged. The [initial-resolution audit](hug_robustness_initial_audit.json) retains its protocol, failed checks and affected cases for reproduction. Independent comparisons use the same 0.05-second evaluation grid in both resolutions; the final run now stores actual integrated states at all those evaluation times.

The [protocol](hug_robustness_protocol.json) fixes all gates before the sweep: energy residual below 0.001 scaled units; observable period refinement below 0.01%; amplitude refinement below 0.1%; the same trajectory classification at both resolutions; independent segment error below 0.00002 scaled units; and no integration guard. Main/refined phase differences after 6,000 seconds are retained but do not alone reject an autonomous oscillator, because small frequency errors accumulate into phase drift.

## What each outcome means

**Self-sustained:** a nontrivial full-state periodic solution closes under shooting, has transverse Floquet multipliers below one, and the observed trajectory agrees with its period and section. The section tolerance is 0.0001 scaled units; the waveform's amplitude changes by less than 2% between the two halves of the late window. Both starts must receive this classification for the pair label. This establishes a local attracting cycle and convergence for the starts tested, not a global theorem or physical validation.

**Rest:** the entire late four-state signal lies below 0.0001 scaled units and the origin's Jacobian has negative real eigenvalues. A decaying signal that has not yet met this tolerance remains unsettled.

**Repeats with orbit:** the four-state solution returns after one, two, three or four full orbital periods to within 0.0001 scaled units at each of 20 late comparisons. Both starts must repeat and their final states at the same orbital phase must agree to within 0.0001. Agreement of two starts does not rule out other attractors. Periodic responses of a passive Hug are orbit-driven motion; they do not demonstrate self-sustained oscillation.

**No short repeat:** no full-state repeat was found over one to four orbits in the finite window. This does not establish chaos, quasiperiodicity, aperiodicity at all times, or failure of every possible synchronization ratio.

**Unsettled/start-dependent:** insufficient signal, continuing internal-memory drift, differing classifications from the two starts, or repeating responses that do not agree between starts. Such outcomes remain visible rather than being discarded. The 6,000-second horizon is finite and is not extended until every case looks settled.

## Outputs and reproduction

- [Saved outcomes, coefficients and checks](hug_robustness_results.json)
- [Unforced robustness plot](figures/hug_robustness_autonomous.png)
- [Circular/eccentric outcome map](figures/hug_robustness_orbits.png)
- [Selected waveforms](figures/hug_robustness_examples.png)
- [Illustrated study report](report.html#hug-robustness)

From this study directory, with the pinned requirements installed:

```text
python hug_robustness.py --cache-dir /path/to/local/robustness-cache
python hug_robustness.py --check
python -m unittest test_hug_robustness -v
python hug_robustness_report.py
```

The optional local cache stores both complete late-window arrays; it is not included in the repository. Saved JSON retains all scenario definitions, outcome metrics, refinement results, local stability checks, independent control errors and selected traces. Full reproduction regenerates both integrations. `--analyze-only` reuses the two arrays in the requested cache directory. The report's summary distinguishes a passing numerical check from the scientific outcome: a reliable nonrepeat or an unsettled trajectory is a valid recorded result.

The study is deterministic. It does not add actuator noise, delay uncertainty, geometric changes, constitutive-model alternatives or new noisy calibration fits. It adds no SIMS participant trajectories. Physical measurements are needed to decide which coefficients and mechanisms describe a real Hug.
