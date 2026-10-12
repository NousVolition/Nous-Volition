FIVE SCREENSHOT EQUATIONS: INDEPENDENT AND COMBINED NUMERICAL TESTS

Open report.html for the self-contained illustrated report.
Completed: 20 independent equation checks, 8 coupled-model checks, 12 transport
runs. All 28 checks passed. This supplements the broader NousVolition /
My-Sources-Project-ALL substance-interaction study.

All five equations produce bounded signals controlling an imposed incompressible
flow. The flow transports CO, acetone and H2O2 in gas and fixed fog water using
explicit gas/liquid mass transfer. This is a constructed, one-way coupling: its
gains and time mappings are assumptions, not measured chemical or hardware links.
The equations do not replace substance-specific coefficients or force laws.
Images 4/5 are cropped; the report states the explicit reconstruction.

REPRODUCE (Python3.12 recommended; from this folder)
  python -m venv .venv
  Windows: .venv\Scripts\activate
  macOS/Linux: source .venv/bin/activate
  python -m pip install -r requirements.txt
  python -m unittest -v test_equations.py > test_log.txt 2>&1
  python -m unittest -v combined_transport.CombinedTests > combined_test_log.txt 2>&1
  python combined_transport.py
  python run_examples.py

The final command checks both test logs before generating its report and archive.
No account connection or network access is needed after dependencies are installed.
The model is deterministic; the randomized conservation test uses fixed seed 123.
Do not redirect the last command into a file in this folder: the archive hashes
the files here before that command finishes. Redirect outside the folder instead.

CONTENTS
equations.py: model functions, explicit equations, exact reference solutions
test_equations.py: 20 checks covering domains, analytic limits, energy and scaling
combined_transport.py: all-five controller coupling, gas/fog transport, 8 tests
run_examples.py: completed numerical examples, plots, JSON results and report
results.json: full numerical findings, conditions and package versions
combined_results.json: 12 transport runs, controls, mass balances and refinement
controller_and_transport_history.json: time-varying flow and transport outputs
trajectories.npz: saved state arrays for plotted trajectories
combined_fields.npz: concentration fields, including the 96x96 refinement
five_equations.png / .svg: scientific figure
combined_transport.png / .svg: computed CO mixing fields
test_log.txt: completed verification log
combined_test_log.txt: completed coupled-model verification log
references.json: Henry coefficients, source links and explicit assumptions
manifest.json: SHA256 file hashes
equation_tests.zip: portable bundle, without installed dependencies

COMBINED CONDITIONS
T=298.15 K, P=101325 Pa, 1x1x1 m gas domain, periodic x/y, 180 s duration.
Uniform fixed water volume fraction 5e-7, 10 micrometre droplets, imposed RH=100%.
Initial wet-gas means: CO 1 ppm, acetone 1 ppm, H2O2 0.001 ppm; liquid solute zero.
Initial field: C/C0=1+0.5 cos(2pi*x/L) cos(2pi*y/L), using exact cell averages.
Shared assumed gas diffusivity 2e-5 m2/s and liquid diffusivity 2e-9 m2/s.
Fog co-advects horizontally; gravity, evaporation and heat transfer are excluded.
No reaction or electrostatic forces. Molecular identities are preserved by design.
Eight flow cases: diffusion alone, steady flow, all five controllers, and five
separate runs removing one controller. Additional no-uptake run plus three
refinement runs bring the transport total to twelve.
Main grid 48x48, dt=0.25 s; grids 24x24 and 96x96; time check dt=0.125 s.
MUSCL conservative flux, MC limiter, SSPRK3, centered diffusion, exact exchange.
Spatial discretization remains the main numerical uncertainty; see report values.
Mass closure and unchanged global partition do not prove real-world validity.
Controller scales (30 s for junction, cycle and oscillator; 3 s for saddle gate)
are chosen signal mappings. They are not physical circuit times from item 2 below.
No ice, smoke, surface adsorption or Coulomb forces are included in this supplement;
they retain their separate modules in the earlier substance-interaction study.

INDEPENDENT CONDITIONS
1. Limit-cycle equation: dimensionless t,r; Cartesian origin explicitly retained.
   r0 in0,.01,.2,.8,1,1.5,3, t=0..10. Backward-domain exception checked.
2. Josephson junction: Ic=1uA,C=1pF,alpha=.2,R derived consistently. Currents
   i=.5 and1.2, different initial velocities, tau=0..300. SI circuit integration
   independently checked against normalized pendulum form. Overdamped C=0 limit
   is a separate model with a different dimensionless time convention.
3. Clock: uniform ideal hand speeds, minutes since noon, first same-direction
   coincidence. Opposite-direction collinearity is separately explained.
4. Saddle-node: xdot=r+x^2. r=1,.1,.01,.001,.0001. Finite-cutoff transit x=-1..1;
   scaled trajectories start at x=-2sqrt(r). No extrapolation of real sqrt(r) to r<0.
5. Oscillator: xdot=v,vdot=-omega^2x, primary omega=1,x0=1,v0=0. Ten periods;
   DOP853, forward Euler and velocity Verlet compared. Additional frequencies,
   long-time Verlet energy bounds and timestep refinement are in the tests.

The reported errors are mathematical/numerical verification errors, not estimated
experimental uncertainty. SI constants h and e use their exact defining values.
The illustrative circuit parameters are assumptions, not extracted measurements.
No molecular reaction, exposure, fluid instability or new physical law is inferred.
