# SIMS: names, memory, and group boundaries

**SIMS** are the simulated participants in this six-group experiment.

**Social analogy, not fluid physics.** Six symbolic labels: Ice, Water, Fog, Mist,
Gas (water vapor), and Smoke. Fog and mist contain liquid droplets; Smoke is not a
water phase. No human data, molecular model, Navier–Stokes claim, or new law.

Open [report.html](report.html) for the accessible results and charts.
[methods.html](methods.html) specifies every model assumption and metric.
[Optional group-decision game](human_protocol.html) is a separate proposal for
volunteers; it has not been run.
All three HTML files work offline. Report chart images are embedded.

## Executed

- 6,444 ensemble trajectories (4,608 core factorial), 30/60/120 SIMS, 120 rounds.
- 12 discovery and 12 independent replication seeds; three network topologies.
- 72 later diagnostic trajectories and 35,928 membership shuffles.
- 144 influence assays and 288 synthetic attribution assays.
- 12 unit tests and 18 exact selected-trajectory reproduction checks passed.

The A/B/name-permutation comparison is exactly invariant in all 144 blocks when
semantic perception is absent. In the full model, combined stress reduced
cooperation by 18.43 percentage points (95% seed interval −18.88 to −17.97).
Same-group choice excess also fell. Memory delayed rigidity recovery under the
specified adaptation rule. An assumed negative label prior reduced nominations
to whichever word received it; this does not establish human dislike of Smoke.

The pre-execution simulation design is recorded, but the analysis is exploratory
and was not externally preregistered. No volunteers have been recruited.

## Reproduce

Python 3.12; tested with NumPy 2.3.5 and Matplotlib 3.11.2. The simulation and tests
require only NumPy. Run commands from this folder, preferably in a virtual
environment. Four worker processes are optional; a single worker produces the
same ordered outputs. No network is needed after installing dependencies.

```sh
python -m pip install -r requirements.txt
python restore_data.py
python test_model.py

# Reanalyze all delivered arrays, rebuild charts and reports:
python analyze.py
python diagnostics.py
python build_report.py
python verify_results.py

# Regenerate the full ensemble into a NEW directory (about 2 minutes on the
# original machine; hardware-dependent):
python run_study.py --workers 4 --out reproduced
python analyze.py --data reproduced --out reproduced-analysis

# Smaller execution check, not an adequate scientific replacement:
python run_study.py --workers 2 --quick --out quick-check
```

The runner refuses to overwrite an existing arrays.npz. Analysis files can be
regenerated. `diagnostics.py` runs its additional 72 trajectories and uses the
original `data/leadership.json` and `data/synthetic_attribution.json`.
`build_report.py` and `verify_results.py` target the delivered `data/` and
`analysis/` paths. The original report narrative contains recorded numerical
values; adapting parameters requires revising that narrative, not merely rerunning
its builder. The numeric tables/charts are programmatically generated.

## Data and statistical unit

`data/tasks.json` enumerates all configs and seeds, in array row order.
`data/schema.json` names every field in `data/arrays.npz`: round traces,
phase metrics, group summaries, group-pair counts/opportunities, and trajectory
event digests. Two paired example event logs are included. Other complete event
histories can be regenerated with `model.run(config, keep_events=True)`.

`analysis/run_phase_metrics.csv` exposes all run-level outcomes. Separate CSVs
contain main effects, interactions, stress components, recovery with censoring,
semantic targets, population/topology strata, sweeps, alliance proxies,
leadership, attribution, and permutation controls. PNG/SVG figures are included.

Intervals resample **12 independent seeds within each split**, after averaging
matched conditions within seed. Agents, rounds, topologies sharing a seed, and
counterfactual runs are not treated as independent replicates. These are
descriptive intervals, not model-uncertainty intervals or human causal estimates.

## Project context and publication

Published in **[Nous-Volition — Streams and Rocks](https://github.com/NousVolition/Nous-Volition)**
at the user's requested destination, under `studies/social-organization/`.
The main repository page links directly to this study.

The research was originally developed with context from
NousVolition/My-Sources-Project-ALL at commit
`277157c4f44d33a0d4eba29b60bcf2104e28a46a`. Its positional-water-influence and
isotope studies motivated the distinction between identity and position.
No numerical observations or physical laws from those studies were transferred
to this social model. The social analogy remains separate from the original
stream-function report and the fluid and molecular evidence.

The full recorded arrays and all scripts are included here. The 44 MB NPZ is stored
in eleven transport parts because of the upload API limit. `python restore_data.py`
reassembles the exact original bytes and verifies every part and the complete SHA-256.
The analysis and verification commands also restore it automatically when needed. Download the
repository ZIP and open this folder's `report.html` to read the offline report;
GitHub's HTML file view displays source. No volunteers have been recruited.

## Integrity

`data/protocol.json` and `data/execution.json` record design, execution times,
source hashes, environment, and run counts. `verification.json` records checks.
`manifest_sha256.json` covers repository files except itself, Python cache files,
and the reconstructed `data/arrays.npz`, whose checksum is in `data/arrays.parts.json`. `package.py` verifies local HTML links and creates that manifest.
Checks establish implementation consistency, not validity as a theory of people.
