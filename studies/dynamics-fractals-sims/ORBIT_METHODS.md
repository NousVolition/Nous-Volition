# Circular and eccentric orbits inside the clay-SIMS test

The requested CO group is **Pasiphae, Elara and Himalia**; the eccentric group is **Europa, Callisto and Thebe**. The spelling assumptions “Dasiphae” → Pasiphae and “thebes” → Thebe are recorded in [the fixed protocol](orbit_protocol.json). Every moon receives both an idealized circular path and a reference eccentric ellipse. These groups describe the requested experimental selection, not an astronomical classification: the first three reference orbits are appreciably eccentric, while the last three are nearly circular.

## Source and orbital calculation

Semimajor axes, eccentricities and reference periods are transcribed from [JPL's grouped planetary satellite mean-element tables](https://ssd.jpl.nasa.gov/sats/elem/sep.html), retrieved 2026-10-10. The table epoch is 2000-01-01.5 TDB. Pasiphae, Elara and Himalia use JUP347/ecliptic elements; Europa, Callisto and Thebe use JUP365/local Laplace-plane elements. The protocol retains the frame, inclination and satellite code for provenance.

| Moon | Requested group | a (km) | e | Reference P (days) |
| --- | --- | ---: | ---: | ---: |
| Pasiphae | CO | 23,463,200 | 0.412 | 734.4215 |
| Elara | CO | 11,710,700 | 0.212 | 258.8861 |
| Himalia | CO | 11,439,000 | 0.160 | 249.9090 |
| Europa | Eccentric | 671,100 | 0.009 | 3.525463 |
| Callisto | Eccentric | 1,882,700 | 0.007 | 16.690440 |
| Thebe | Eccentric | 221,900 | 0.018 | 0.676105 |

For each independent orbit, n=2π/P, M=nt and eccentric anomaly E solves E−e sin E=M. Coordinates in that orbit's periapsis-aligned plane are

```text
x = a(cos E − e)
y = a sqrt(1 − e²) sin E
r = a(1 − e cos E)
vx = −a n sin E / (1 − e cos E)
vy = a n sqrt(1 − e²) cos E / (1 − e cos E)
```

The circular control sets e=0 and keeps a and P. Both paths start at the positive x-axis; the ellipse starts at periapsis. These are frozen shapes with a reference period, **not ephemeris predictions**. JPL cautions that mean elements are unsuitable for calculating accurate positions. Actual precession, solar perturbations, mutual moon interactions, and sky-plane orientations are absent. In particular, Pasiphae's retrograde inclination is retained as metadata, but not depicted by a direction relative to a common equatorial plane: each panel uses its own intrinsic orbital plane. Present-day phase and relative moon alignment are not inferred.

Energy and angular momentum checks use the effective two-body parameter μ=n²a³ of each frozen reference ellipse. Because mean a and sidereal P come from perturbed orbits, the model does not assert an exact common Jupiter μ across these fitted pairs. Twelve independent normalized Cartesian integrations (six moons × circular/eccentric) check the Kepler paths over one period. Normalizing by a and P avoids conditioning problems from their very different scales.

## Apply the distance signal to the current clay formula

The pressure mapping is an explicit SIMS experiment choice:

```text
phase = (SIMS_time − 20 s) / 100 s
E − e sin E = 2π phase
s(t) = 20 Pa × sqrt(1−e²) / (1−e cos E)², 20 ≤ t ≤ 120 s
s(t) = 0 otherwise
```

Both limits of the load jumps at 20 and 120 s are saved. One astronomical cycle is compressed into 100 SIMS seconds for a matched shape comparison. The physical periods remain in the orbital calculations. This is neither measured gravitational pressure nor a tidal-stress calculation; distance becomes a chosen common input. Semimajor axis and real period do not affect this normalized SIMS waveform. Comparisons isolate eccentricity and input timing rather than all physical differences between moons.

The normalization makes the **time-average pressure exactly 20 Pa**. With dM=(1−e cos E)dE, the orbit average of (a/r)² is 1/sqrt(1−e²). Its prefactor therefore equalizes the pressure impulse to 2,000 Pa·s across all conditions. Without normalization, higher eccentricity would also change total loading.

The frozen 20 Pa coefficient set and the reciprocal graph coupling come from [the current clay-SIMS methods](CLAY_SIMS_METHODS.md). Coefficients remain fixed while pressure varies: this is an extension of the linear Burgers model, not a calibration for these new waveforms or a claim about actual collective clay. Initial retained patterns use the same 32 predefined seeds as batch 9; the three 20-SIMS graphs are Menger L1, Ring 20 and Complete 20. Duration is 420 s, with recovery from 120 s onward.

There are **672 main runs**: (six eccentric inputs + one common circular input) × three graphs × 32 matched starts. All six circular SIMS waveforms are identical after normalization, so the circular ensemble is shared rather than counted six times. This adds 672 to the prior 15,200 main SIMS runs, giving **15,872 cumulative main runs**. Twelve orbital controls and twelve full-network DOP853/Radau checks are reported separately. Quadrature comparisons are diagnostic calculations, not additional participant runs.

## Mean response and participant differences

Uniform loading excites only the zero Laplacian mode. The population mean follows the scalar Burgers system:

```text
u_mean′ = (s − G_K u_mean) / eta_K
w_mean′ = s / eta_M
gamma_mean = s/G_M + u_mean + w_mean
```

Nonuniform initial retained patterns evolve with the same zero-input ClayNetwork dynamics for every waveform. The solver therefore combines exact modal initial-pattern evolution with a high-accuracy scalar forced response. Full-coordinate independent integrations check this decomposition; independent convolution quadrature checks the scalar solution.

Consequently, eccentric timing changes transient mean deformation and recoverable strain. The final retained population mean w is the same for every case (2,000/6,700,000 ≈ 0.00029850746 strain). Residual u at 420 s can differ because the timing of the load affects delayed recovery. Within each graph, participant spread is identical across the seven inputs. Graphs still redistribute the initial retained pattern differently. The experiment does not support a claim that eccentricity changes alignment under uniform linear forcing. Response-sign unanimity uses the existing normalized ±0.02 threshold and is distinguished from voluntary agreement.

## Verification and reproduction

Twenty-three new tests cover source transcription, name assumptions, elliptic Kepler residuals including high eccentricity, invalid inputs, circular radius/speed, apsides, periodic return, velocity derivatives, equal swept areas, conservation, time reversal, independent Cartesian integration, equal pressure impulse, jump limits, the original clay step-load reduction, independent convolution, equal retained means, graph spread invariance, a full-coordinate solver, matched starts and saved-result gates.

Maximum allowed orbital position discrepancy is 10⁻⁸a; clay discrepancy is 10⁻⁹ strain; mean and paired-spread discrepancies are 10⁻¹². Saved outcomes are compared tightly on replay; solver error diagnostics must pass the same fixed gates. Accuracy failures remain visible rather than being dropped from the ensemble.

```sh
python -m unittest -v
python orbits.py --check
```

To regenerate this batch, run `python orbits.py`, then rebuild its figures and the HTML report through `orbit_report.build_figures()` and `build_report.make_html()`. Full `python build_report.py` rebuilds all figures. [All runs, representative traces and diagnostics](orbit_results.json) and [the fixed protocol](orbit_protocol.json) are included. The report plots are computed originals; source screenshots are not repository assets.
