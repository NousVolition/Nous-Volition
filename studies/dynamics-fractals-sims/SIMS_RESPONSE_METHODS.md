# Applying the references inside the SIMS test

This extension answers both parts of the request: the supplied dynamics now determine how interacting SIMS change, and 24 further tests check the mathematics and the resulting measurements. It adds **1,632 matched continuous-state SIMS trajectories**, following the settings in [sims_response_protocol.json](sims_response_protocol.json). The earlier 12,800 binary-copying runs remain a separate experimental arm with their original rules. Together the package contains 14,432 SIMS runs, with different response rules explicitly distinguished.

Each new run has 20 participants on a Menger level-1, ring, or complete contact graph. Every graph and condition reuses the same 32 starting states, with seeds 20261020–20261051. We draw two coordinates per SIM uniformly from [−0.6,0.6], center each coordinate across the population, and add the common mean (0.1,−0.04). This holds the collective starting state fixed while varying participant differences. The scalar experiments reuse the first coordinate. There is no added noise or learning between runs.

Let W be the undirected adjacency matrix divided by that graph's maximum degree, and L=diag(W1)−W. Every edge retains equal weight within a graph; total influence per participant is at most one. This normalization bounds total coupling while permitting the Menger graph's different node degrees. Comparing these graphs changes their complete connection structure, not a uniquely fractal property.

## Linear response: move together versus settle down

Each SIM has an expressed preference displacement and a response coordinate. Place its two numbers in row i of Y. The chosen rule is

```text
Y′ = Y Aᵀ − 2 L Y.
```

The seven matrices A are the six cases in the supplied phase-portrait report plus the reciprocal-coupling boundary b=1. Their exact values are in [bridge_references.json](bridge_references.json). They supply a center, stable and unstable spirals, a saddle, and reciprocal stable, neutral, and saddle cases. This gives 7 × 3 graphs × 32 starts = **672 trajectories**, each lasting 12 dimensionless time units.

The population mean obeys the original two-variable equation exactly: mean(Y)′=A mean(Y). Neighbor exchange acts on differences between participants. For a graph mode with Laplacian eigenvalue λ, the effective local matrix is A−2λI. Thus the real part of a local eigenvalue must be compared with 2λ to determine whether that participant-difference mode grows or decays. The experiment evaluates this solution using graph eigenmodes and the exact 2×2 exponential, and tests it against independently integrated coupled equations.

For the unstable spiral, the collective displacement grows by exp(0.2×12)=exp(2.4), approximately 11.02, on every graph. Meanwhile the average final RMS participant spread is:

| Graph | Final spread | Runs with a unanimous final choice |
| --- | ---: | ---: |
| Menger | 0.06069 | 32/32 |
| Ring | 0.52535 | 25/32 |
| Complete | 5.55e-11 | 32/32 |

The first nonzero Laplacian eigenvalues are approximately 0.14615, 0.04894, and 1.05263. Multiplying by the coupling strength 2 explains the contrast: the ring's slowest alignment modes cannot overcome growth rate 0.2, whereas the other two graphs can. Complete-graph agreement is therefore compatible with an unbounded collective trajectory. These linear growth cases are diagnostics on a finite interval; the state is an unbounded displacement, not a bounded preference probability.

The saved results retain every case, including stable systems whose coordinates approach zero. Near-zero coordinates are classified as undecided rather than counted as a common choice. At the neutral boundary, alignment can occur without attraction to zero. A linear center can synchronize while the collective mean keeps rotating.

## Reversal: the textbook rule acts on participants

With one preference coordinate per SIM, use

```text
x′ = −(2I+W) cos(x).
```

For two participants joined by one edge, W=[[0,1],[1,0]], so this becomes exactly x′=−2cos x−cos y, y′=−cos x−2cos y from the supplied textbook crop. For all tested graphs, 2I+W is symmetric positive definite. Therefore V=Σ sin(xᵢ) decreases strictly except at equilibria, since V′=−cos(x)ᵀ(2I+W)cos(x). The field is even, giving the reversal identity f(−x)=f(x). The uniform −π/2 state is locally attracting, and +π/2 is repelling.

The control runs forward for eight units. Its paired intervention uses the same rule until time 2, changes its sign from 2 to 4, then restores it. The middle interval is an explicit intervention on the response rule; it retraces the earlier path. Both conditions are integrated with RK4 step 0.02, splitting exactly at the intervention times. This gives 2 × 3 × 32 = **192 trajectories**.

Across the 96 interventions, the largest componentwise return error at time 4 is 7.052e-8. Repeating both conditions for the first three starts on every graph with step 0.01 gives 18 numerical control trajectories; their largest difference from the main paths is 6.901e-8. These controls are reported separately and are not included in the 1,632 main-run count. Tests also verify the potential, the two-participant reduction, relabeling invariance, and decreasing return errors on step refinement.

## Response rates: distinguish target changes from timing changes

The water screenshot separates density, dynamic viscosity, and their combined effect. We apply its saved 25 °C ratios as dimensionless response settings for SIMS. This is an explicit sensitivity experiment, not a fitted account of participant behavior.

```text
x′ = q s(t) 1 − r (I+2L)x
r = (μ/ρ)/(μH/ρH)
s(t) = +1 for t<4, and −1 thereafter.
```

Every participant receives the same signal. The four settings use the reference values, the changed density alone, the changed viscosity alone, or both. With **fixed input**, q=ρH/ρ, and the common steady value is s q/r=s μH/μ. With **the same target**, q=r, making the common steady value s for every setting. This second control separates response speed from steady amplitude. Its constant-signal evolution is exactly the reference trajectory with time multiplied by r, an identity covered by a test.

There are 4 settings × 2 input controls × 3 graphs × 32 starts = **768 trajectories**, each lasting 12 units. Exact graph-mode evolution handles the signal switch. Independent RK4 integration provides an implementation check.

For the Menger graph with the target matched, the measured settling times after the switch are 3.7 units for the reference, 4.1 for the density change, 3.1 for the viscosity change, and 3.4 for both. Density alone slows the response. The viscosity ratio speeds relaxation and, under fixed input, reduces the final preference magnitude to approximately 0.8145. The target-matched control restores the final magnitude to one. All main rate runs confirm settling within the stated window. Every run's outcome is retained, and a separate slow-response test checks that an unfinished response is recorded as unconfirmed.

## Measurements and limits

All trajectories are sampled every 0.1 time unit. RMS spread measures differences from the population mean across all state coordinates. The norm of that mean measures collective displacement. A unanimous choice requires every preference to exceed +0.02 or every preference to be below −0.02; values between these bounds are undecided. We retain first sampled unanimity, final unanimity, the sampled fraction of agreement, and sampled agreement breaks. Events between samples are not resolved.

Rate settling requires every SIM to remain within 5% of the final target through the remaining sampled window, with at least one unit of confirmation. It is finite-window confirmation, measured to the 0.1 sampling grid. Agreement and attraction are separate: a growing trajectory can have common choices, and a stable near-zero state can leave participants undecided.

The data include per-run outcomes, graph spectra, representative traces, and paired differences in final spread against the ring. Approximate normal 95% intervals describe variation over the selected 32 matched initial states. They are not confidence intervals for participant behavior. Uniform forcing makes the rate experiment's collective dynamics independent of graph shape; graphs affect the decay of participant differences. The new model has continuous state and chosen response rules, so its times and outcome frequencies must not be pooled with the original binary-copying experiment as if the protocols were identical.

## Run the experiment and tests

From this directory, with the pinned requirements installed:

```sh
python -m unittest -v
python bridge_checks.py --check
python sims_response.py --check
```

The full suite now has **162 tests**. To generate new saved results, run `python sims_response.py`; to rebuild the complete illustrated report, run `python build_report.py`. [sims_response_results.json](sims_response_results.json) records all 1,632 main outcomes, the 18 refinement comparisons, and the exact protocol used.
