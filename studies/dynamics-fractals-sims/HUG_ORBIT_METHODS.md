# Test the circular and eccentric input with the Hug itself

This batch applies the orbital inputs **directly to the current clay Hug**, then checks the deformed outline, release, retained strain, and work/energy balance. It supplements [the orbit-driven SIMS experiment](ORBIT_METHODS.md); it does not count the same participant runs again.

## Fixed experiment

- Seven inputs: one shared circular control, plus the reference eccentricities for Pasiphae, Elara, Himalia, Europa, Callisto and Thebe.
- Four frozen Burgers coefficient sets from [the located clay formula](CLAY_SIMS_METHODS.md), each using its own nominal stress of 10, 20, 30 or 40 Pa.
- Zero initial internal strain; no participant graph or lean dynamics.
- Rest to 20 s, one orbit-shaped loading cycle from 20–120 s, then recovery to 420 s.
- Original closed Hug outline, 65 points per arm, from the pinned original geometry. The current clay `shear_points` function supplies the deformation map.

There are **28 main material trajectories** (seven inputs × four coefficient sets) and **28 independent Radau solver controls**. The main solver is DOP853; independent convolution integrals check the internal material strains at selected loading/recovery times. There are **zero additional SIMS runs**: the package's cumulative main SIMS count remains 15,872. All 423 observations per path retain both limits at loading and release. Area and join checks at magnifications 1 and 200 cover 23,688 outline states; these are geometric checks, not additional material trajectories.

The [direct-Hug protocol](hug_orbit_protocol.json) and [pinned orbital protocol](orbit_protocol.json) specify the model and the JPL data already used in batch 10. “Dasiphae” is interpreted as Pasiphae and “thebes” as Thebe. Requested CO/eccentric groups remain recorded, while circular approximations are distinguished from reference eccentricities.

## From the orbit to the material law

Each row uses its own nominal pressure s0 and the existing equal-mean waveform:

```text
E − e sin E = 2π(t − 20)/100
s = s0 sqrt(1−e²)/(1−e cos E)², during 20–120 s
s = 0, otherwise

u′ = (s − G_K u)/eta_K
w′ = s/eta_M
gamma = s/G_M + u + w
```

Here u is delayed recoverable Kelvin strain, w is retained Maxwell-dashpot strain and gamma is engineering shear. Each waveform has pressure impulse s0 × 100 Pa·s, making within-row comparisons equal in total loading. The circular case reduces exactly to the original clay step-load solution. The direct 20 Pa row also reproduces the population mean in the previous orbit-driven clay-SIMS experiment.

One astronomical cycle is compressed into 100 Hug seconds. This is a chosen loading signal, not a calculation of gravitational or tidal pressure. True periods and physical orbital positions remain in the separate orbit controls. Coefficients are frozen through the waveform. Pasiphae's input peaks at about 2.64 times the nominal pressure, so these varying-load tests extend the fitted constitutive model beyond its original step-loading calibration. They are computational checks, not new material measurements or validation of full Hug mechanics. Differences across fitted rows cannot be attributed to stress alone.

## Actual Hug deformation and recovery

Both arms start in the original joined pose, then use

```text
x_display = x + magnification × gamma × y
y_display = y
```

Magnification 1 is the actual small-strain display. The report's outline comparison uses 200 to make the small response visible, following the source Hug display convention. Stored material strains and response charts are always actual values. Both versions of four outline snapshots per trajectory are saved: before loading, the maximum sampled loaded state, immediately after release and at 420 s.

The shear matrix has determinant 1 and is invertible. Thus it preserves enclosed area and maps the shared arm tips to shared tips. This guarantees geometrical closure in this model; it does not measure contact strength or predict whether a physical clay object would break. There is no opening-at-1 trigger in the current clay formula.

The instantaneous elastic component s/G_M vanishes at release. Delayed strain subsequently follows u(t)=u(120) exp[−G_K(t−120)/eta_K], while retained strain w remains fixed. Equal loading impulse gives the same final retained component within each coefficient row. Remaining delayed strain at 420 s depends on the preceding waveform. Pasiphae gives the largest sampled deformation in each row; the nearly circular Europa, Callisto and Thebe inputs stay close to the circular baseline. Peaks are explicitly **sampled** on the one-second grid, including the left limit at release.

## Work, energy and independent checks

Stored material energy density is

```text
E = s²/(2 G_M) + G_K u²/2
E′ = s gamma′ − eta_K u′² − eta_M w′²
```

Work at an instantaneous load jump is (s_before+s_after) × delta_gamma/2. Loading stores positive elastic energy and release returns it. Because the waveform begins and ends at the same periapsis pressure, its two elastic jump-work terms cancel over the entire experiment. Continuous elastic work is the exact endpoint difference (s_end²−s_start²)/(2G_M); internal work and loading dissipation are independently integrated by quadrature. Recovery dissipation is G_K[u(120)²−u(420)²]/2. The final delayed elastic energy equals total input work minus total dissipation. Retained viscous strain carries history without stored spring energy in this idealized model.

All 28 cases retain the solver, convolution, geometry and energy diagnostics. Gates require strain discrepancies below 10⁻⁹ (solver) and 10⁻¹⁰ (convolution), work/energy residual below 10⁻⁸ J/m³, join gaps below 10⁻¹² and relative area error below 10⁻¹². Failed gates are not discarded. Sixteen new tests check the complete paired design, original outline, both shear directions, inverse mapping, magnification, original circular formula, previous SIMS mean, jump continuity, recovery, retained strain, convolution, energy accounting, independent solvers and saved-result rejection.

```sh
python -m unittest -v
python hug_orbits.py --check
```

To regenerate, run `python hug_orbits.py`, then `hug_orbit_report.build_figures()` and `build_report.make_html()`. Full `python build_report.py` rebuilds all figures. [The full direct-Hug results](hug_orbit_results.json) include all material components, shape snapshots and diagnostics. The source screenshots remain references; all report figures are computed originals.
