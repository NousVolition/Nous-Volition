NOUSVOLITION / MY-SOURCES-PROJECT-ALL
Reproducible chemical / transport interaction pilot

Start with research_report.html, a self-contained illustrated report.
interaction_matrix.csv lists all 105 unordered baseline/self-pairs across 14
named systems, plus 9 explicit charge/reaction variants (114 rows total).
Statuses distinguish simulation, analytic calculation, assessment and literature.
Fog and mist are liquid droplets in air. Smoke is heterogeneous aerosol plus gas.
Air includes N2/O2; these overlapping matrix labels are not separate phases.

RUN (Python 3.12 recommended; commands from this directory)
  python -m venv .venv
  Windows: .venv\Scripts\activate
  macOS/Linux: source .venv/bin/activate
  python -m pip install -r requirements.txt
  python -m unittest -v test_models.py
  python run_study.py
  python build_report.py

No external data fetch, credentials, laboratory equipment or physical experiment
is required by these scripts. Reference constants are frozen in references.json.
Run time is typically under a few minutes. The executed study took about 20 s
plus tests on this host, excluding dependency installation and report building.
Exact elapsed time and package versions are recorded in results/summary.json.
Some floating point and stochastic details may differ across versions/platforms.

FILES
  model.py                Independent physical models, equations and units
  config.json             Baseline scenario documentation and selected run inputs
  references.json         Published constants, units, provenance and limitations
  run_study.py            Numerical pilots, sensitivity, uncertainty, plots, tables
  test_models.py          Physical invariant and analytic benchmark tests
  build_report.py         CSV interaction matrix and self-contained HTML report
  requirements.txt        Tested direct dependency versions
  test_log.txt            Captured completed verification output
  results/                Machine-readable results, PNG/SVG figures, NPZ fields
  results/input_hashes.json   SHA256 source/input snapshot from numerical run

SCENARIO EDITING
config.json documents the baseline and supplies the partition run, concentrations,
water inventory, seeds and some scenario controls. It is not a universal parameter
interface. Explicit sweep lists, independent charge-droplet scenarios, carbonate
constants and physical-model defaults remain readable in run_study.py/model.py.
If changing defaults, update report assumptions and matrix context accordingly;
build_report.py is written for the delivered baseline, not arbitrary scenarios.

WHAT WAS ACTUALLY RUN
1. Closed gas/liquid mass transfer for CO, CO2, acetone, isoprene, H2O2, N2 and O2,
   each with bulk water, fog or mist. Water volume fixed; clean, dilute solution.
2. Separate CO2/carbonate equilibrium at25C, zero alkalinity; no coupled reactive
   mass-transfer transient is claimed.
3. Low-pressure CO+OH->CO2+H kinetics at100Pa,298.15K in N2; finite oxidant and
   no-OH controls; evaluated low-pressure rate, conditional reduced mechanism.
4. 2D periodic conservative species transport with analytic Fourier comparison.
   A smoke-surrogate capture sink retains a complementary particle-material budget.
   Velocity prescribed; no Navier-Stokes or buoyancy solve.
5. 3D independent Brownian particle pairs with Coulomb force and Stokes/slip drag,
   five seeds per primary charge case, analytic drift and Einstein-MSD checks.
6. Thermostatted flat liquid/ice vapor exchange; independent seeded energy balance
   for freezing/melting. Acetone two-site ice adsorption at200,210,220K.
7. Analytic diffusion-only smoke scavenging and constant-kernel agglomeration /
   coalescence comparisons with explicit sticking assumptions.

IMPORTANT LIMITS
Numerically verified is not environmentally validated. Published equilibrium/rate
constants are used within stated limits, but transfer coefficients, concentrations,
geometry, diffusivities and sticking are pilot assumptions, not measurements.
No generic smoke surface is calibrated. No H2O2 catalytic kinetic curve is run;
the source lacks enough recovered operating conditions for a transferable rate.
The H2O2 prescribed-conversion test is stoichiometry only, not a reaction prediction.
No quantum chemistry, collective charged cloud, turbulence, nucleation kinetics,
near-contact polarization/lubrication, or full gas/aerosol reaction mechanism.
No-charge drift does not exclude polarization attraction in real charged-neutral
pairs. Neutral Brownian distance growth is not evidence of force-driven repulsion.

The 2D grids show finite numerical diffusion. Coarse-grid results must not be used
as measured diffusion coefficients. Particle pairs stop at6 radii separation;
stopped trajectories are censored, not collisions or proof of coalescence.
Fixed-radius water droplets require a sustained-water/saturation idealization.
Flat-interface humidity tests are separate; they do not update the fog inventory.
Cold acetone sorption is not extrapolated beyond the190-220K source range.

SAFETY / CLAIM BOUNDARY
Computational study only. No CO, smoke or VOC generation, exposure or smell test.
No proposed new Navier-Stokes law and no implication that CO+water becomes CO2.

Source/input hashes allow exact versions to be identified. The archive includes
no downloaded library binaries or installed environment; install requirements.
