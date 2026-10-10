JOSEPHSON VOLTAGE SWEEP — COMPLETED NUMERICAL PILOT

Read report.html for results, figures, equations, uncertainty and limitations.
Streams and Rocks: https://github.com/NousVolition/Nous-Volition/tree/main/studies/fluid-organization/extensions/josephson-sweep
Code and recordings: https://github.com/NousVolition/My-Sources-Project-ALL/tree/main/reports/fluid-organization-pilot/extensions/josephson-sweep

Python 3.11+; install requirements.txt. requirements-lock.txt records this run.
  python -m pip install -r requirements.txt
  python -m pytest test_model.py -q
  python run_all.py

Individual stages: run_sweep.py, validate.py, diagnose_precision.py,
analyze.py, refine.py, analyze_reference.py, make_report.py, verify.py.
The original fixed-step gate remains a reported FAIL; all follow-up refinement
gates must pass for the final report. run_sweep.py caches source/protocol-matched
recordings. If changing the model/protocol, copy the package to a fresh directory
without data/ or use --out NEW_DIRECTORY for numerical exploration. Analysis
scripts read the package data/ directory. Do not reuse old data after a change.

If recordings are delivered as archive parts, run restore_recordings.py first.
All subsequent analysis can use recorded data without rerunning the sweeps.
  python analyze.py
  python analyze_reference.py
  python make_report.py
  python verify.py

The accepted equations use a mean/log-separation coordinate transform of the
original conditional circuit_rhs in the fluid pilot. No new physical memory
term is added. audit/ preserves the initial failed direct-phase checks and
instructions to reproduce them separately. Their raw traces are superseded.

Array layout in base/half_step/double_settle/both.npz:
  voltage: [bias index, mode, alpha, initialization, junction]
  states: [bias index, recorded time, mode, alpha, initialization, (p,z)]
  sign: [mode, alpha, initialization]; initial/settled/endpoint store (p,z).
  bias_order[:,0:3]: actual fresh/up/down current sequences.
Descending mode is reversed only when forming increasing-current tables.
windows.npz: states [recorded time, bias index, mode, alpha, initialization, (p,z)].
Use model.from_state(states,sign) to reconstruct unwrapped phases. Preserve z
when restarting: reconstructing it from rounded output phases loses precision.
Every primary and window trajectory is sampled every 5 dimensionless time units;
integration uses the separately recorded .05/.025 steps. Voltages use exact
integration endpoints, not differencing the coarsely sampled output.

All voltages are normalized by Ic*r. All durations use tau=(2e Ic r/hbar)t.
No dimensional device parameters or laboratory measurements are supplied.
