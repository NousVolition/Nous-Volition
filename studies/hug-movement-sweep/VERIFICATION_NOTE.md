# Saved phase-metric portability correction

The repository-wide source-chain audit exposed a failed exact float comparison in this pre-existing study. The model, analysis, trajectories and scientific effect criteria were unchanged. The first failing CI run printed only the metric name. A diagnostic-only follow-up retained equality and exposed the actual values:

- Recomputed phase offset: 7.2416217521542595e-06 cycles.
- Saved phase offset: 7.2416217522249385e-06 cycles.
- Absolute difference: 7.067897021774058e-17 cycles.

[Original failed run](https://github.com/NousVolition/Nous-Volition/actions/runs/40058866529) · [Diagnostic failed run](https://github.com/NousVolition/Nous-Volition/actions/runs/40059248000).

The unchanged saved verifier passed on the local Windows runtime and the preceding CI run. Disabling available CPU vector features and separately comparing scalar math.atan2 locally did not reproduce the discrepancy. Those negative diagnostics are not proof of its exact library/CPU cause. The observed discrepancy is at floating-point roundoff scale, not a changed scientific effect classification.

Only the bounded phase-offset metric now permits an absolute difference of 32 float64 epsilons, about 7.11e-15 cycles, with no relative tolerance. The formula uses atan2, complex exponential and angle, for which identical inputs need not produce bit-identical outputs on different numerical implementations. This is an explicit computational reproducibility tolerance, not a measurement uncertainty or a change to the predeclared effect threshold. Both values must be finite. All outcome flags and other paired metrics still require exact equality, and the existing path/field/source checks remain in place.

The regression tests accept the captured roundoff difference and reject a 1e-12-cycle discrepancy, non-finite phases, changed flags and a one-ULP change in a different metric. Saved results, input data, protocols, model equations and analysis functions remain unchanged. The verifier reports the maximum accepted phase difference so later runs remain inspectable. No empirical clay or inward-experience validation follows from this repair.
