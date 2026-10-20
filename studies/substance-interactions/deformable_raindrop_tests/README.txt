DEFORMABLE LARGE RAINDROPS — STREAMS AND ROCKS
Simulations: 17 October 2026. Interim publication: 20 October 2026.

Open report.html for the saved calculations, figures, animation and
measurement comparison. Read results.json and comparison.csv for exact
values. The model and all scientific limits are specified in METHODS.txt.



BEGIN RECORDED RESULTS
INTERIM RELEASE: 24 of 28 planned flow cases completed.
Four numerical checks remain unfinished; simulations remain paused.
  Unfinished: midpoint_re1200_a0875_d28 — not_run.
  Unfinished: midpoint_re2100_a065_d28 — not_run.
  Unfinished: re1600_a075_d28_long — interrupted_by_user_no_final_record.
  Unfinished: re2600_a075_d36 — not_run.
24 completed gas-flow cases. Shape predictions below use the
complete 28-cell-per-diameter gas library. Axis ratio is vertical/horizontal.
  2.5 mm: predicted 0.8817; measured 0.892; difference -0.0103.
  2.9 mm: predicted 0.8493; measured 0.874; difference -0.0247.
  3.6 mm: predicted 0.7913; measured 0.798; difference -0.0067.
  4 mm: predicted 0.7585; measured 0.808; difference -0.0495.
Mean absolute ratio error: 0.0228.
From 28 to 36 cells, drag changes by -4.7% and the deformation load by -6.6% in the reference case.
The measured means were not fitted. These are conditional comparisons,
not validation of a fully moving liquid-air interface or smoke capture.
END RECORDED RESULTS

WHAT IS NEW
- Actual resolved 3D gas-flow calculations at multiple Reynolds numbers and
  spheroid shapes, with exact curved-wall intersections and interpolated
  boundary reflection.
- Separate complete 20- and 28-cell-per-diameter airflow libraries, and
  one completed 36-cell reference calculation; domain, time/Mach and seed
  controls. Longer averaging, two interpolation checks and the high-Re
  36-cell control are unfinished. Full 3D fields are advanced; snapshots are center-plane
  slices. These are not 2D flow calculations.
- A computed liquid shape responding to airflow, inertia, surface tension
  and viscosity, conserving exact spheroidal volume. This is a one-coordinate
  reduced model with quasi-steady gas coupling, not two-fluid DNS.
- All four preselected new experimental mean axis ratios, source audit,
  uncertainty/sensitivity and both favorable and unfavorable outcomes.
- Analytic frequency/damping, volume/energy, gas diffusion, manufactured
  surface traction and numerical gas-mass-budget checks.

SCIENTIFIC STATUS
The new measurements were not used to fit model coefficients. Source/model
choices preceded numerical table extraction, but search previews exposed
qualitative outcomes. No blinded-validation claim is made. The experiment
has oscillating, potentially nonspheroidal drops; the primary prediction
is an equilibrium spheroid. Grid and model errors remain. This is not
validated smoke capture and not a new Navier-Stokes law.

REPRODUCE THE SAVED ANALYSIS (CPU)
Use Python 3.12+, NumPy, SciPy, Matplotlib and Pillow. From this folder:
  python verify_shape.py
  python analyze.py
  python audit_saved.py
  python make_report.py

All force histories, metadata, mean/instantaneous gas slices, shape traces,
transcribed measurements and analysis inputs are included. Exact floating
point identity on another environment is not guaranteed. The dense 3D
population fields were not stored: the scripts regenerate them.

REPEAT THE GPU CALCULATIONS
Make a fresh COPY of this study and remove its generated flow/ directory
before regenerating all runs. Do not overwrite the published record.
CuPy requires a compatible NVIDIA GPU and CUDA 12 runtime/toolkit. The
original machine has a 10 GB RTX 3080. The optional gpu_environment.py only
configures already installed workspace-local CUDA wheels on the original
Windows computer; it makes no machine-wide changes. On a normal CUDA
installation that helper returns without changing runtime paths.

Run sequentially on one GPU:
  python verify_gas.py
  python verify_surface_load.py
  python verify_mass_budget.py
  python run_flows.py
  python run_refined_library.py
  python analyze.py
  python audit_saved.py
  python make_report.py

Individual case (on one line):
  python flow_lbm.py --name NEW_NAME --diameter 36 --reynolds 1600 --aspect 0.75
The drivers skip already recorded names, including failed attempts, so a
failed case is not silently replaced. Inspect metadata status. Run times
and the actual GPU/software environment are saved.

INDEPENDENCE AND PROVENANCE
protocol.json: choices before the measured table was extracted.
source_freeze.json: source hashes, checked against the final physical code.
amendments.json: additional numerical checks/refinement, with reasons.
source_audit.json: observable/condition matching and table discrepancy.
source_files.json: author-hosted paper URL and source SHA256.
measurements.csv: four preselected measured outcomes, units and uncertainty.
METHODS.txt: equations, units, assumptions and primary references.
flow_summary.csv: all completed and failed flow attempts, including controls.
sensitivity.json: declared one-at-a-time perturbations, not confidence bands.
saved_data_audit.json: consistency checks on available records, not a pass for unfinished tests.
study_status.json: all 28 planned cases; 24 completed and four unfinished.
release_context.json: the pause and interim-publication policy.
manifest.json: hashes and sizes of the published package files.

The new data become development evidence if later used to change the model.
Further validation would need a truly coupled moving liquid/gas interface,
more resolved wakes, transverse shape modes and matched-condition data.
