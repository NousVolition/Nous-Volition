# History prediction at increased Reynolds number

**Experiment in progress. Status recorded on 13 October 2026 UTC. There is no completed independent prediction result yet.** The [live acquisition run](https://github.com/NousVolition/My-Sources-Project-ALL/actions/runs/38478834942) shows subsequent progress.

The new experiment lowers dimensionless viscosity from 0.025 to 0.01, keeping the forcing, initial-speed distribution, localized disturbances and prediction comparisons from the [completed stationary study](../stationary-history/README.md). Its target is a measured approximate Taylor Reynolds number above 50, compared with the earlier measured mean of 29.20. The target is not an achieved result.

The registered design specifies 128 cubed main grids, 160 cubed controls, and fresh seeds for 24 training, 8 validation and 32 independent test flows. Four intervention times and two strengths yield eight dependent targets per flow; uncertainty treats each flow as one independent sampling unit.

Two separate pilot fields are integrated on both grids through time 44. A matched disturbance pilot compares halved steps and a finer grid at those smaller steps. Calibration starts only after the pilot gates pass, and its stationarity gate must pass before models are fitted and frozen. Test jobs then verify the immutable frozen source, calibration and pilot hashes before starting. Four preselected test flows also have matched restart controls at the final intervention, time 44.

**Completed so far:** the 22 solver and prediction-design tests passed on Windows and on the Linux runner, and the published analysis-tool audit passed. These tests do not establish that the new full-duration flows or disturbances are resolved. The achieved Reynolds number, ensemble stationarity, test refinement results and history-prediction comparison remain pending.

History will be compared with richer and global current measurements, wrong-run histories and training-only averages by strength and by intervention time. A supported advantage requires every declared comparison and the numerical/stationarity checks to pass. History here consists of causal Eulerian observations, not molecular interactions or passive-marker history.

[Runnable code and registered protocol](https://github.com/NousVolition/My-Sources-Project-ALL/tree/main/reports/fluid-organization-pilot/extensions/higher-re-history) · [Live experiment](https://github.com/NousVolition/My-Sources-Project-ALL/actions/runs/38478834942)

Completed numerical findings, plots and uncertainty will replace this dated status after acquisition and audit. Still larger Reynolds numbers, new observation designs and laboratory validation remain separate future experiments.
