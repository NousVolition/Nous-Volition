LARGE-RAINDROP MODEL REVISION AND NEW-MEASUREMENT TEST
Streams and Rocks / NousVolition — 2026-10-15 local date

ADDED METHODS
ADDED_METHODS.txt now links Beard's 1974 resolved-flow/trajectory study to
the capture mechanism audit and adds a separate water-interface topology
classifier (Jedlovszky et al. 2025 / Foffi and Sciortino). The classifier has
14 passing synthetic/unit tests, including 175 independent shortest-path
comparisons. No new interface MD or resolved raindrop-flow simulation ran.
The frozen model, earlier measurements and numerical outcomes below remain
unchanged. See interface_topology/ for runnable code and a labeled toy example.

RESULT
An improved candidate implementation is complete and has been run. It adds
finite-Reynolds-number collection correlations, particle inertia, a published
wake-capture term, ventilated heat/evaporation balance, signed phoretic drift,
and number/mass averaging over particle sizes. It is a closure model, not a
new resolved-flow calculation or a new Navier–Stokes law.

The revision improves some known development cases substantially. For a
1.25 mm water drop collecting 0.22 micrometre particles, the earlier rare-event
trajectory diagnostic gave E=0.0000796616 (0.00797%); the new monodisperse
calculation gives E=0.0101644 (1.016%), versus measured 0.88% and 0.97%.
Those measurements are development data, NOT independent validation. The
largest particle case is highly sensitive to distribution width: 0.0679%,
9.84%, and 22.84% for GSD 1, 1.3, and 1.5, versus 7.9% measured. We did not
select the width with the best agreement. All three are retained. Row 6 of
that older table retains its previously identified arithmetic-conflict flag.

NEW OUTCOMES, MODEL UNCHANGED
Hong et al. (2025), DOI 10.1063/5.0263346, section III, printed page 6,
provides four explicit average collection efficiencies. These numerical
outcomes were first extracted after raindrop_model.py and the comparison
protocol were frozen. No physical coefficient was changed afterward.
The target's metadata and an abstract overview were available during source
screening. This is a documented new-numerical-outcome test, not a formally
blinded or externally preregistered trial. Future revisions informed by these
results must treat Hong2025 as development evidence, not reuse it as untouched.

Drop long axis / equivalent diameter: 4.46 / 3.94 mm
  Number collection: measured 31.1%, predicted 2.13% (14.62-fold low).
  Mass collection:   measured 18.4%, predicted 2.13% (8.65-fold low).
Drop long axis / equivalent diameter: 2.81 / 2.60 mm
  Number collection: measured 63.5%, predicted 12.51% (5.08-fold low).
  Mass collection:   measured 77.9%, predicted 12.51% (6.23-fold low).
Median absolute factor error across these four observables: 7.44; 0/4 within
a factor of two. These are four aggregate observables at TWO drop conditions,
not four independent experimental campaigns. The paper does not supply an
uncertainty for these aggregate means in the prose. Its plotted error bars
are standard deviations of five repeats, not transferable error bars for the
above aggregate means. No experimental confidence interval is invented.

This is a CONDITIONAL TRANSFER TEST, not matched water/smoke validation:
* The experiment used glycerol–water with a small acid addition, density
  1210 kg/m3, viscosity 0.0444 Pa s, surface tension 0.0606 N/m. The frozen
  candidate uses pure-water constitutive properties. Its water wet-bulb
  evaporation prediction is not a prediction of the glycerol mixture.
* Particles were hydrophobic PDMS-coated silica, density 1900 kg/m3,
  diameter range 1–5 micrometres, arithmetic mean 2.92 micrometres. They are
  not smoke. The numerical 20-bin input size histogram is unavailable here.
  The primary approximation puts all particles at the reported mean. Thus
  number and mass predictions coincide; that coincidence is an assumption,
  not a prediction that polydisperse number and mass efficiencies must match.
* T=284.15 +/- 1 K, RH=0.56 +/- 0.02 and measured fall speeds 9.32 and 8.04 m/s
  were supplied as external inputs. Pressure is assumed 101325 Pa, particle
  thermal conductivity 0.43 W/(m K). Sensitivities are saved.
* Grounded apparatus and charge-reduction measures do not establish that
  every droplet and particle is neutral. Charge distributions and sticking
  probabilities were not measured here; the model assumes no charge and
  perfect sticking. It cannot simulate hydrophobic ricochet or film rupture.
* Reynolds numbers 2575.9 and 1466.4 exceed the rear term's 20–800 domain.
  We follow its published zero-outside convention and FLAG it. Zero here
  means unsupported/unmodelled wake contribution, not proof of no wake.
* Source efficiencies use pi*l^2/4, where l is the horizontal long axis.
  Model efficiencies use pi*D^2/4 for volume-equivalent D. We multiply model
  E by (D/l)^2 before comparing. This is an observable area conversion, not
  a dynamical treatment of drop deformation. Shape/oscillation remain open.

WHAT THE ADDITIONAL TESTS SHOW
We tested GSD 1.3 and 1.5 distributions truncated to 1–5 micrometres,
normalized and adjusted ONLY to retain the reported arithmetic mean 2.92.
Number/mass averaging is explicit; no outcome fitting occurs. We also
scanned the entire source particle-size interval. At nominal conditions,
even the largest pointwise model efficiency is only 6.87% for the large
drop and 23.86% for the small drop. Any positive size-distribution average
of this particular model over that interval must lie below those maxima.
All four measured averages exceed them. Thus unknown distribution width
alone cannot fix this model at the stated nominal inputs. These are numerical
support bounds, not rigorous error bounds on real physics or confidence limits.

Sensitivity to T, humidity, speed (+/-10%), density (+/-10%), conductivity,
and size distribution is saved in results/sensitivities.csv. These are
one-factor scenarios, not an exhaustive joint uncertainty calculation.
Controls remove phoresis, impaction, or rear capture, and switch off the
Fredericks impaction correction. No model is selected using holdout scores.
There is no new stochastic trajectory simulation in this revision: repeated
seeds and time-step refinement would not apply to an algebraic closure.
The earlier stochastic results remain preserved in collection_external_check.

Five additional drop speeds from Hong Table I are compared with the Beard
pure-water terminal-speed estimate in results/speed_transfer.csv. This is
also a material-mismatched diagnostic, not velocity validation. Measured
speed, rather than the mismatched water estimate, drives the CE test.

NUMERICAL VERIFICATION
Run test_model.py for 12 tests, including independent saved outputs from
the authors' released code for Brownian/interception/rear terms, saturated-
humidity no-phoresis control, heat-balance residual, inertial threshold,
terminal-speed sanity bounds, rear-domain guard, quadrature refinement,
input validation and closed particle accounting. The saved airborne and
collected inventories follow the exact exponential-removal solution; their
sum is conserved by construction. This is an accounting identity, not an
independent integration test. No particle chemistry occurs.
Energy accounting here is the local quasi-steady latent/conductive balance,
not a closed thermodynamic simulation of the entire chamber/drop.
Distribution calculations use 501 then 1001 points; verify_results.py checks
the saved differences and all scores against the input/output CSVs. Unit
tests establish implementation consistency, not experimental correctness.

METHODS AND SOURCES
[1] Jones et al. 2022, https://doi.org/10.5194/acp-22-11381-2022
    Main Eq.12: rear capture, applicable only for 20<=Re_D<=800.
    Supplement S1: Beard fall-speed correlations, 0.5 micrometre–7 mm;
    S3: Slinn Brownian/interception and corrected inertial collection.
    https://acp.copernicus.org/articles/22/11381/2022/acp-22-11381-2022-supplement.pdf
    Development lineage includes historical measurements used by these
    published correlations; none is claimed as independent here.
[2] Jones author code, https://doi.org/10.5281/zenodo.6617052
    Inspected and executed for independent component benchmarks. Code is
    Crown copyright under Non-Commercial Government Licence v2 and is NOT
    copied or relicensed in this bundle. Hash recorded in frozen protocol.
[3] Depee et al. 2021 Part I, https://doi.org/10.5194/acp-21-6945-2021
    Eq.12 supplies signed phoretic surface forces; conversion to surface
    speed uses Stokes–Cunningham mobility. We approximate contribution to
    E by -4*v_radial/U (spherical surface area / projected area). This is an
    additive surface-flux closure; it omits coupling to a resolved wake.
[4] Hong et al. 2025, https://doi.org/10.1063/5.0263346
    Publisher PDF: https://pubs.aip.org/aip/adv/article-pdf/doi/10.1063/5.0263346/20464501/045001_1_5.0263346.pdf
    Table I: five drop shapes and velocities. Section III printed p6:
    four aggregate CE values. Publisher text was accessible via the web
    reader; direct PDF download returned 403 and screenshot rendering failed.
    Figures 5–7 and three intermediate drop-size CE values were NOT digitized.
    No table-vs-figure consistency pass is claimed. Data include every explicit
    aggregate CE mean in the accessible prose, irrespective of agreement.
[5] Lemaitre et al. 2017, https://doi.org/10.5194/acp-17-4159-2017
    Table2 is now development data. Prior source audit, assumptions and
    stochastic uncertainty remain in ../collection_external_check/.

SOURCE DISCREPANCIES AND CHOICES (fixed before new numerical outcomes)
Jones supplement S42 uses Re based on DIAMETER in the Fredericks factor;
the archived code uses RADIUS. We implement the supplement. The exponent
is .173 in S42 and the code, versus .172 in the main equation: use .173.
The published/code S50 thermophoresis expression has dimensionally
inconsistent conductivity/length additions. We use the previously available
Depee force instead, including particle Knudsen number and thermal
conductivity. Independent code benchmarks EXCLUDE the discrepant impaction
and phoretic parts; passing them is not a claim the entire model matches
the author's code. Beard's 1.07 mm regime boundary follows the supplement;
S12 surface tension is used directly instead of its approximate polynomial.
These choices are documented in frozen_protocol.json, not made after seeing
Hong's collection-efficiency values.

Scalar E sums Brownian, interception, inertial, rear, inward thermophoretic
and signed outward diffusiophoretic contributions. A negative raw total is
clipped to zero with a flag; this is an approximation, not an exact coupling.
No such clipping occurs in the four primary holdout cases. Perfect sticking,
fixed drop size, dilute aerosol, quiescent far field, and quasi-steady thermal
balance are assumptions. No general smoke validation, resolved turbulent
wake, new chemical reaction, neutral-droplet repulsion or biological result
follows from this study.

NEXT SCIENTIFIC STEP
Resolve a deformable, finite-Re wake at Re about 1500–2600 with actual liquid
properties and transport/retention of the actual particles. Obtain the raw
input size distribution and quantified charges. A new model influenced by
Hong2025 then needs a DIFFERENT matched dataset for an untouched test. The
present run identifies that boundary; it does not close the validation gap.

REPRODUCE
Python 3.12.14; exact installed versions in requirements.txt.
  python -m pip install -r requirements.txt
  python test_model.py
  python run_study.py
  python verify_results.py
  python build_report.py
Run from this directory, or supply script paths. All data are bundled CSVs;
normal reproduction needs no external download. The frozen protocol contains
the SHA-256 of the model. The runner refuses a changed model. The saved
author benchmarks can be reproduced by downloading the licensed author's
scavenging_routines.py and running reproduce_author_benchmark.py locally.
No experiment, exposure, smoke generation or hazardous vapor is performed.
