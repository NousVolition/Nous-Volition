# Model and experimental design

This is a static linear-programming benchmark inspired by the supplied passage. It extends the community questions in SIMS using its own explicit allocation model; it does not modify or claim equivalence to the earlier SIMS cooperation dynamics. There is no time-integration step, molecular mass, chemical reaction, pressure or temperature in this model.

## State, units and constraints

Seven fictional people each have one available-time unit. They need two complementary abstract services. A fulfilled bundle fraction z_j between 0 and 1 requires that same fraction of *both* of person j's service demands. These service amounts are normalized quantities, not measurements of food, care, health or happiness.

For provider i and service t, e_it is effort in time units, s_it is service productivity per time unit, and f_ijt is the amount of that service delivered to recipient j. d_jt is recipient demand. The constraints are:

```
sum_j f_ijt <= s_it * e_it        production cannot exceed available effort
sum_t e_it <= B_i               work stays within the policy's budget
sum_i f_ijt >= d_jt * z_j        every credited bundle receives both services
f_ijt = 0 for disallowed i,j    graph determines direct help opportunities
e_it >= 0; f_ijt >= 0; 0 <= z_j <= 1
```

Transfers have no travel time, decay, strategic withholding or reciprocity requirement. The word reciprocal describes the bidirectional contact graph, not an enforced exchange norm. There is no re-export through intermediaries. There is no physiological fatigue or human utility function. Everyone's outcome is kept, including the lowest fulfillment and work above a requested limit.

All requested work budgets are drawn uniformly from 0.5 to 0.8. Respecting limits gives B_i=request_i; allowing overrides gives B_i=1. An assessment-cost scenario reduces that work budget by a specified fraction of the available-time unit, floored at zero. Excess over requests counts useful work plus this assessment time. The main assessment cost is 0.1 per member, an assumption rather than a measured cost.

Person-level productivity is uniform on [0.8,1.2]. For each seed a random sign chooses which service is stronger. Skills are productivity_i*(1+delta_i, 1-delta_i), with delta_i either zero or signed 0.55. The person's arithmetic mean skill is unchanged. Demands are 0.35*scarcity*Uniform(0.8,1.2) per service, with scarcity 1 or 1.4. These distributions are assumed exploratory inputs. No parameters are fitted to human observations or Foucault's text.

## Graph and priority controls

Independent cases have self-service only. The connected graph consists of a seven-person ring plus two randomly chosen remaining edges: nine undirected edges. The partitioned graph has complete clusters of size three and four, also nine edges, with members shuffled independently of the names. Both permit self-service. Equal edge counts do not imply equal degree sequences, connectedness or opportunities; this is an arrangement comparison, not an isolated causal estimate of partitioning at fixed degree sequence.

The first optimization maximizes sum_j w_j*z_j. All weights are 1 except in priority scenarios, where one member has weight 3. The main designated member is index 0, displayed as Water; this is arbitrary. Additional rotations move priority through all seven people. Triple weight describes unequal objective priority. It does not implement a leader making decisions, a pyramid of reporting, persuasion or obedience.

A second optimization holds the primary objective within 1e-9 of its optimum and minimizes weighted effort and flow. Effort coefficients are 1+0.01*Uniform(0,1); flow coefficients are 0.01+0.001*Uniform(0,1). The same coefficients are used across matched policies. They provide an explicit tie-breaking allocation, not fairness. Different secondary objectives could redistribute outcomes among primary-optimal solutions. Both objectives and all inventories are checked.

The eight main policy names and settings are in `model.POLICIES`. Recording-only is deliberately inert. The assessment-cost case has no information benefit because the optimizer already has perfect information; it cannot establish a general effect of surveillance or measurement.

## Execution and uncertainty

The main design crosses 24 seeds, two skill-differentiation settings, two demand settings and eight policies: 768 allocation cases. Discovery seeds are 31000-31011 and independent replication seeds are 41000-41011. The same generated people, needs, budgets and contact graphs are used across policies within a seed and setting.

Another 576 cases at differentiation 0.55 and scarcity 1.4 include 336 priority-position rotations (24 seeds, seven members, two budget rules), 120 assessment-cost settings (0,0.05,0.1,0.15,0.2) and 120 priority-weight settings (1,1.5,2,3,5). Some settings deliberately repeat main controls; they are not independent evidence. There are 36 numerical refinement pairs (72 additional allocation solves) comparing objective tolerance 1e-9 with 1e-10. Every allocation solve uses two linear programs. Unit-test solves are separate from these counts.

Intervals are Student-t 95% intervals across 12 independent seed estimates in each split and setting. Contrasts subtract matched policies within seed before computing intervals. These descriptive, unadjusted intervals describe random synthetic configurations, not real populations or model uncertainty. Because the intervals are untransformed, bounds may extend beyond the metric's physical range; raw bounds are retained, not interpreted as possible negative fulfillment. Rounds, services and the seven members are not counted as independent replicates. Additional position-rotation summaries first average within seed.

The design and source hashes were saved before the ensemble ran, after unit testing. This is an exploratory study, not an external preregistration. There is no ODE grid convergence to test. Instead, the checks compare an independent isolated-agent formula, a uniform analytic case, graph/label invariance, resource constraints, optimality and tighter solver tolerances.

## Reproducibility

Python 3.12.14, NumPy 2.5.3, SciPy 1.18.1 and Matplotlib 3.11.2. Run `python test_model.py`, then `python run_study.py --out reproduced`, and `python analyze.py --data reproduced --out reproduced-analysis`. The runner refuses an existing protocol to preserve delivered results. The shipped report is built from the delivered `data/` and `analysis/` using `python build_report.py`. `python verify.py` verifies saved constraints, exact selected reruns, source hashes, report links and the publication manifest.
