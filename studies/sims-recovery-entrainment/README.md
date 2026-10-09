# SIMS: recovery, shared rhythms, and the arrangement

**[Read the results](report.html)** · **[Worked equations and model atlas](worked_models.html)**

This follow-up extends the six-group SIMS experiment and works through the equations
in the supplied page extracts. Download the repository and open either HTML file
locally; their figures are embedded and work offline. GitHub displays HTML source.

## What ran

- 1,152 cooperation-model trajectories: 60 SIMS, 480 rounds, four stress schedules,
  memory on/off, three networks, equal/unequal groups, 24 fresh seeds.
- 576 phase-oscillator trajectories: 30 SIMS, four signal placements, two occupant
  mappings, three networks, and independent discovery/replication seed batches.
- 96 single-phase trajectories, 732 Josephson sweep segments and 72 later
  fixed-bias diagnostics. Refinements are numerical checks, not independent evidence.
- Worked calculations and executed examples for circle flows, pendulum energy,
  damping, cylindrical phase space, vector-field index, gravity, hypercycles,
  the three-group model, Hamiltonians, predator–prey cycles, Van der Pol, Duffing,
  cubic velocity damping, pendulum averaging, and parametric swing instability.
- 13 main unit tests; 12 exact recovery reruns; matched-prefix, numerical refinement,
  invariant, eigenvalue, and winding checks. Records are included.

## Findings

After an early stress pulse, the memory-enabled mean rigidity difference in the
last 40 of 480 rounds was −0.000224 (95% seed interval −0.001350 to +0.000787).
That gives no clear evidence of a persistent average increase at this horizon.
Individual arrangements did not necessarily return to the same group boundaries.
First threshold attainment and sustained recovery are reported separately.

The same imposed rhythm was much more effective at selected high-degree than
low-degree sites in random and hub networks. With a hub arrangement, the mean
externally locked fraction was 100% versus 0.14% in replication. All ring sites
have equal degree, so its two site selections are ties. These results depend on
the specified coupling and forcing rules. Coherence among SIMS is distinct from
locking to an external rhythm; signal placement is not a measurement of leadership.

The main report separates the cooperation model from the oscillator model. The
mathematical atlas supplies exact derivations and original figures for the uploaded
extracts. It distinguishes centers from attractors, energy conservation from
damping, and index constraints from stability. No volunteer activity was run.

## Reproduce

Python 3.12, NumPy 2.3.5 and Matplotlib 3.11.2 were used. From this directory:

```sh
python -m pip install -r requirements.txt
python test_experiments.py
python verify_results.py
python analyze.py
python build_report.py
python package.py
```

Reanalysis uses the supplied arrays. The original six-group model must remain at
`../social-organization/model.py` for provenance/equivalence checks. No source or
result in that original experiment was changed to run this extension.

To rerun the entire follow-up in a **new** folder while preserving delivered data:

```sh
python reproduce.py --out ../../reproduced-sims --workers 4
```

That helper copies the source and reference model into a fresh layout and executes
the main design, its checks, the later mathematical additions, and both reports.
It refuses an existing destination. Depending on hardware, expect several minutes.
The main batch took about two minutes on the original machine.

For just the main simulations and analysis:

```sh
python run_experiments.py --workers 4 --out reproduced
python analyze.py --data reproduced --out reproduced-analysis
```

The runner refuses to overwrite an existing protocol. Later addendum scripts also
refuse to overwrite their result files. `--quick` on the main runner is an execution
check using two seeds; its intervals are not an adequate research result.

## Design and interpretation

`data/protocol.json` freezes the main design and source hashes before execution.
The 12 discovery seeds are 12100–12111; replication uses 22100–22111. Main intervals
bootstrap 12 independent seed means, averaging topology and group balance within
seed. They are descriptive and unadjusted. Rounds and paired runs are not independent
statistical units. This is an exploratory follow-up, not external preregistration.

Stress is present in zero-based half-open windows `[40,80)`, `[200,240)`, both,
or neither. The model copy changes only schedule handling; equivalence tests prove
that its default schedule and first 120 rounds reproduce the original model.
Ten-round block means and exact event digests are saved. Whole round/event records
can be regenerated from `data/tasks.json` and `recovery_model.run`.

The oscillator model uses 30 sites, coupling 4, intrinsic detuning uniform on
[0.08,0.16], a total external forcing of 12, and RK4 step 0.04. The last 30 of 120
time units determine coherence, drift, and finite-window locking. Swapping the two
selected occupants moves both their initial phase and detuning. Symbolic group
labels are not a force in this model.

`data/*_protocol.json` marks additions prompted by later screenshots. The critical
Josephson diagnostic was designed after observing a settling-time discrepancy;
both original results and the diagnostic are retained. At beta=10 and normalized
current 1, the initial upward sweep voltage changed from 0.471 to 0.995 with longer
settling. It is not reported as a precise converged threshold measurement.

## Files and scope

- `data/`: frozen designs, task list, saved arrays, per-case numerical results.
- `analysis/`: seed contrasts, recovery endpoints, network comparisons, PNG/SVG figures.
- `verification.json`: original-model equivalence, saved-result checks and refinements.
- `model_provenance.json`: exact source hash and two scheduling changes.
- `manifest_sha256.json`: file integrity; `delivery_checks.json`: report link checks.
- `recovery_model.py`, `oscillators.py`, and addendum scripts: runnable equations.

The final heteroclinic crop starts at part (c) and omits the governing equations.
That exercise is pending; saddle coordinates alone do not determine connecting
trajectories. Other clipped subparts were not reconstructed.

The supplied equations are mathematical inputs, not calibration data about people,
devices, or ecosystems. Sources are identified by the visible figure/exercise
numbers in the atlas. The scans themselves are not redistributed.
