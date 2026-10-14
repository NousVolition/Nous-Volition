# A community: coordination, boundaries and power

Streams and Rocks • seven fictional participants • an executed allocation benchmark inspired by the uploaded Foucault passage

**Water, Fog, Mist, Gas, Smoke, Clay and Ice can belong to the same community.** This study asks how organizing the same people changes their ability to meet needs, the distribution of help and the work required of each member. Different skills and contact opportunities can make a group more capable; a higher group total does not guarantee that every member benefits.

The supplied page matches Foucault’s *Discipline and Punish*, in the panopticism chapter. Its discussion of organization and power provides the questions. The numerical rules are our explicit synthetic assumptions. [How the passage is used](interpretation.md) · [Methods and units](methods.md) · [Source provenance](source_provenance.json) · [Verification](verification.json).

## What was actually tested

768 main allocation cases cross 24 seeds, two skill patterns, two demand levels and eight organizational rules. Another 576 cases vary who receives priority, how strong it is and how much time assessment consumes. There are 36 tighter-tolerance pairs and 19 passing unit tests. These are optimization cases, not observed families or simulated conversations. Every arrangement uses the same ideal solver with complete information; distributed negotiation is not modeled.

| Choice | What changes |
| --- | --- |
| Independent | Each person must supply their own two services |
| Connected, total-focused | Help can cross nine bidirectional ties; requested time limits remain |
| Partitioned | The same number of ties forms disconnected groups of three and four |
| One member has priority | That member receives triple weight in the allocation objective |
| Requests can be exceeded | The optimizer may use more time than members requested, within finite capacity |
| Priority + overrides | Unequal priority and relaxed requested limits together |
| Recording only | Metadata are recorded but do not alter allocation rules |
| Assessment time cost | An assumed 0.1 time unit per member is consumed; no information benefit is modeled |

Names are independent of abilities. Changing the seven labels leaves results exactly unchanged. Both graph types have nine undirected edges, but their degree sequences differ. A family-specific memory role for Clay or a contact style for Mist would require additional stated rules; those dynamics are not implied by the names.

## Results: the group total and the least-served member can move in opposite directions

The table below uses the differentiated-skill, higher-demand setting and the 12 independent replication seeds. Each person has one total available-time unit and requests a work limit between 0.5 and 0.8. A needs score is the fraction of both abstract services received, not a wellbeing score. Full discovery and replication results for every setting are in [summary.csv](data/summary.csv) and [paired_contrasts.csv](data/paired_contrasts.csv).

| Arrangement | Mean needs met | Mean of least-served score | Time beyond requests, total |
| --- | --- | --- | --- |
| Independent | 46.6% | 34.7% | 0.000 |
| Connected, total-focused | 77.2% | 13.1% | 0.000 |
| Partitioned | 74.3% | 9.9% | 0.000 |
| One member has priority | 77.2% | 13.7% | 0.000 |
| Requests can be exceeded | 97.3% | 81.3% | 1.980 |
| Priority + overrides | 97.3% | 81.3% | 1.980 |
| Recording only | 77.2% | 13.1% | 0.000 |
| Assessment time cost | 67.6% | 6.9% | 0.000 |

![Bars show means; dots show the 12 seed outcomes. The lowest member score is retained separately from the group average.](analysis/outcomes.png)

Bars show means; dots show the 12 seed outcomes. The lowest member score is retained separately from the group average.

Connected allocation raises mean needs met from **46.6% to 77.2%**, a gain of 30.6 percentage points (paired 95% seed-t interval 24.5–36.8 points). Yet the mean lowest-member score falls from **34.7% to 13.1%**. The objective maximizes total fulfillment and has no individual minimum guarantee. More available help does not force the optimizer to share its gains equally.

The direction of the optimized total gain is guaranteed when the connected arrangement includes every independent option. The amount of the gain and its distribution are the numerical findings. Holding each person’s arithmetic mean skill fixed, the corresponding higher-demand coordination gain is only 2.2 percentage points when their two skills are equal. This supports a complementarity mechanism within this model, not a general law about personality types.

Partitioning changes mean fulfillment by −2.9 percentage points relative to the connected graph; the paired seed interval is −8.3 to +2.4 points. This finite sample does not establish a consistent direction. Keeping the tie count equal prevents explaining the comparison solely by “more relationships,” but does not control every graph property.

## Who receives the benefit?

![One illustrative community, the first replication seed. The priority position is arbitrary. A work/request ratio above 1 means the chosen allocation exceeds that member’s requested time; zero fulfillment displayed here is not a property of the Clay label.](analysis/members.png)

One illustrative community, the first replication seed. The priority position is arbitrary. A work/request ratio above 1 means the chosen allocation exceeds that member’s requested time; zero fulfillment displayed here is not a property of the Clay label.

With member 0 given triple priority, that member’s mean fulfillment rises from 80.7% to 100.0%, while the other six fall from 76.7% to 73.3%. The group average barely changes. Moving priority through all seven positions gives an average recipient gain of **21.3 percentage points** and a **-3.9-point** change among the others, averaging within seed before calculating intervals.

Allowing work beyond requested limits raises average fulfillment to 97.3%, but uses **1.98 extra time units across seven people** beyond their requests. Relaxing a constraint can only improve this optimized objective. That is not evidence that overrides improve consent, wellbeing or family relationships; these are not modeled.

![Priority and assessment-cost sensitivities. The intervals describe synthetic seed variation; untransformed interval bounds can extend beyond the metric range.](analysis/sensitivity.png)

Priority and assessment-cost sensitivities. The intervals describe synthetic seed variation; untransformed interval bounds can extend beyond the metric range.

Recording alone changes nothing exactly, because the model gives it no causal effect. Assessment that only consumes time reduces available work by construction. Measuring a real benefit of information would require imperfect knowledge, an explicit observation process and a rule for how information changes decisions. No claim that all assessment is harmful follows from these scenarios.

## What the passage adds to your project

It adds a question about power inside the arrangement: who sets the objective, who has access to whom, whose needs receive priority and whose time counts as available? Your community can contain different members without treating one material name as superior. The model makes it possible to inspect both collective capacity and individual outcomes instead of using output alone as success.

The earlier [family/community guide](https://github.com/NousVolition/Nous-Volition/blob/main/studies/substance-interactions/followup_tests/COMMUNITY.md), [SIMS model](https://github.com/NousVolition/Nous-Volition/tree/main/studies/social-organization) and [shared-rhythm study](https://github.com/NousVolition/Nous-Volition/tree/main/studies/sims-recovery-entrainment) remain separate, linked components. The substance study supplies physically tested transport mechanisms; this passage supplies a conceptual basis for organizational comparisons. No chemical kinetics or droplet forces were changed.

A minimum-service guarantee, negotiation, fatigue, memory, changing relationships and a benefit from better information remain possible extensions. They were not silently added. No human participants, real family data or empirical validation of Foucault’s wider argument are involved.

## Reproduce and inspect

The completed ensemble ran in 11.6 seconds on the recorded environment. Maximum allocation-constraint residual was 8.9e-16; tightening the objective tolerance changed a member’s fulfillment by at most 9e-10. Numerical units are defined in [methods.md](methods.md). [Per-person results](data/members.csv) preserve who contributes and who receives help.

```sh
python -m pip install -r requirements.txt
python test_model.py
python verify.py

# Preserve the delivered data while rerunning:
python run_study.py --out reproduced
python analyze.py --data reproduced --out reproduced-analysis

# Rebuild the delivered report from delivered data:
python build_report.py
```

`data/protocol.json` records the design and source hashes. `data/allocations.npz` contains every main effort, service flow and needs fraction, with order in `data/case_order.json`. `verification.json` records saved-result checks and selected reruns; `manifest.json` records packaged hashes. The runner refuses to overwrite a previous protocol. Counts of repeated controls and refinement solves are explicit in [execution.json](data/execution.json).
