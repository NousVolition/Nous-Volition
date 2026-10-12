STABILITY, ENERGY AND PHYSICAL FORCES

Open report.html for the illustrated explanation of the eight new screenshots.
All 19 new verification tests pass. The previous 28 tests belong to the earlier
equation/transport supplement; this is a separate additional verification suite.
The three additional water-study figures are also covered: eight data-consistency
checks reanalyze their existing saved outputs. No new xTB/PIMD/CFD run is claimed.

REPRODUCE (Python 3.12 recommended; run from this folder)
  python -m venv .venv
  Windows: .venv\Scripts\activate
  macOS/Linux: source .venv/bin/activate
  python -m pip install -r requirements.txt
  python -m unittest -v test_stability.py > test_log.txt 2>&1
  python audit_water_figures.py
  python run_study.py

The report builder requires the successful 19-test log. Do not redirect its stdout
to a file in this folder while packaging: archive hashes must refer to completed
files. An external log path is fine. Runtime is a few seconds on the execution
host. No random sampling is used; results may vary slightly by floating-point
library/platform. No network is used after dependency installation.

FILES
models.py: explicitly defined equations and analytic comparisons
test_stability.py: 19 tests of stability, domains, conservation and force balance
run_study.py: completed examples, figures, report, hashes and archive
results.json: numerical findings, parameters, errors and library versions
trajectories.npz: all plotted simulated trajectories and traced stable manifold
stability_and_energy.png / .svg: six-panel scientific figure
test_log.txt: verification record
references.json: screenshot interpretations, physical constants and sources
audit_water_figures.py: independent recalculation of the water-figure statistics
water_figures_audit.json: all eight completed data checks and their results
water_evidence_audit.png / .svg: comparison of model, sampling and flow evidence
prior_water_data/: hashed copies of relevant preexisting quantum-water outputs;
  sources and original protocols are retained. Other study files were not modified.
manifest.json: SHA256 hashes for all packaged files
stability_tests.zip: portable reproducible package, without installed dependencies

SCREENSHOT MAPPING
1. Taylor linearization: checked on the supplied population system at (1,1).
   Finite-difference Jacobian and quadratic remainder verified. Local, finite-time
   validity; eigenvalues with zero real part need further analysis.
2. Poincare map: return times/radii and full variational multipliers verified.
   The printed forward AND backward convergence claim is corrected. r=0 is not
   part of the transverse positive-axis section. Backward existence is restricted.
3. Cubic spiral: a=-1,0,1, initial radius .2, end time 10. Exact solution checked.
   a=1 blows up at t=12.5 and is not integrated through that singularity.
4-5. Rabbit/sheep competition: all four equilibria classified; positive quadrant,
   opposite basins, stable manifold and local linearization checked. Dimensionless
   population model, not a molecular force or conserved chemical inventory.
6-7. Conservative systems: selected V=x^4/4-x^2/2, dimensionless m=1. The screenshot
   supplies no potential formula; this is an explicitly illustrative choice.
   Energy contours, homoclinic reference and damping gamma=.2 are checked.
8. Reversibility: integrate 12 time units, flip velocity, integrate another 12.
   Conservative motion retraces; same positive damping on both legs does not.

DIRECT RESEARCH AUDITS
Gas/water partition: use the earlier Henry coefficients for CO, acetone, H2O2.
T=298.15 K, P=101325 Pa, water volume fraction5e-7, fog radius10 micrometres,
gas diffusivity2e-5 m2/s, liquid diffusivity2e-9 m2/s, fixed inventory/no reaction.
The equilibrium line gives a zero eigenvalue from conservation. At fixed total
solute, the remaining negative eigenvalue sets the relaxation rate. No oscillator
or population equation is substituted for the physical transfer law.

Coulomb/drag: radius1 micrometre, charges+100e/+100e, +100e/-100e, or0/0;
separation20 micrometres, end1 s or stop at separation6 radii; 298.15 K,1 atm,
still air, slip-corrected Stokes mobility. Brownian forcing OFF for this analytic
energy audit. No near-contact hydrodynamics, polarization, collision, bonding or
coalescence claimed. Analytic separation and independent drag-heat integral tested.

This supplement is numerical verification, not experimental validation. It does
not generate chemicals, perform exposures, or propose a new Navier-Stokes law.

WATER-FIGURE CONNECTION
Small molecular vibrations are obtained by linearizing an energy potential:
K*v=omega^2*M*v. Isotope masses change frequencies with the same potential.
Classical equilibrium positions for fixed V(q), volume and temperature have
p(q) proportional to exp(-V/kBT), independent of isotope masses. The observed
classical structural differences are therefore a sampling/equilibration/numerical
diagnostic for that model. The source liquid study failed several quality screens
and did not estimate viscosity. Its bond means and radial-distribution peaks are
different estimators. Its continuum study instead supplies IAPWS material data.
For the matched pressure-driven channel, mean steady U=G*h^2/(12*mu), while the
slow relaxation time is rho*h^2/(mu*pi^2). Both identities reproduce saved results.
These checks distinguish verification, material-property consistency and missing
micro-to-macro validation. Details and limitations are in the illustrated report.
