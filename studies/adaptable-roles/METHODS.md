# What “adaptable” means in this experiment

This is a separate synthetic social process, beside the physical substance study and the earlier static community allocator. Water, Fog, Mist, Gas, Smoke, Clay and Ice name seven fictional members. Each takes the designated role in turn. Labels never change a coefficient. None of the results assigns an inherent personality to a substance or a person.

Adaptation means doing unexpected coordination work: adjusting plans, resolving a clash or covering a gap. These are illustrative meanings for an abstract service. The model does not simulate language, emotions, intentions, a real household, fluid deformation or molecular interactions. Refusal is represented by a changed work budget, not an inference about why someone refuses.

## Assumed inputs and units

Every member has one time unit per round. Initial coordination skill is independently uniform on [0.8,1.2] service units per time unit. A chosen maximum coordination-work budget is uniform on [0.45,0.65]. Original planned work varies independently over rounds on [0.5,0.65] time units. Coordination is allocated first; original plans receive the remaining time, up to their requirement. Thus accepting enough extra work can displace original plans. There is no overtime beyond the one-unit capacity, fatigue, physiological recovery or wellbeing score.

Each round creates a group coordination requirement D = load * Uniform(0.85,1.15), with load 0.8 or 3.6 service units. It is an imposed requirement in this model; the model does not decide whether a real demand is necessary, fair or worth satisfying. Uncompleted requests expire each round, rather than accumulating. Planned work and coordination use different quantities and are reported separately, never added into a single moral or happiness score. All participants are available for handoff where the policy permits it; there is no spatial network or negotiation delay.

The same generated people and demand sequences are used across policies and role rotations within a seed. Random inputs do not depend on material names. The two loads share all draws except the demand scale. The 60 rounds are discrete decision events; they have no assigned duration in minutes or days.

## Requests, learning and persistence

Initially the request expectation b_i is 1/7. With an active assigned role, the target receives a fixed 75% request share plus its share of the remaining 25% according to b. The other members receive 0.25*b_i. Without that assignment bias, requests follow b. Completed output updates expectation:

`b_next = 0.75*b + 0.25*(individual completed output / total completed output)`.

If nobody completes any coordination, b is unchanged. Requests reflect an assumed shared expectation, not an explicit surveillance or decision network. Learning uses actual coordination-production time P accumulated through the previous round:

`skill_i = initial_skill_i + 0.6 * (1 - exp(-0.1*P_i))`.

This bounded practice effect is assumed, with no forgetting or fatigue. Handoff administration time does not build production skill. The skill law is evaluated directly, not numerically integrated. Expectation and skill are separate states: remembered role and actual ability need not change together.

In the ordinary assigned policy, each member accepts its initial requests only up to skill times its chosen coordination-time budget; unfinished requests are not automatically redirected. Assignment can therefore waste available capacity elsewhere. The strong 75% bias makes this bottleneck substantial by construction; its magnitude is not an estimate of a real family's expectations.

## Eight policy comparisons

1. **Shared from start:** coordinate allocation across all willing members from round 1.
2. **Assigned; continues:** maintain the designated role and accept work up to the chosen limit throughout.
3. **Label removed only:** after round 30 remove the 75% bias but retain learned expectations and skills.
4. **Target stops; no handoff:** after round 30 the designated member's coordination budget becomes zero; others initially receive requests by the old rule, which continues adapting through b.
5. **Target stops; handoff:** the same refusal and initial request rule, but redirect uncompleted requests to other willing members. Each transferred service unit costs an extra 0.05 time units of administration to its recipient.
6. **Share after round 30:** retain everyone's willingness, reset b to uniform at round 31 and replace initial allocation with shared scheduling. Learned skills remain. This changes several rules together, so its effect is not attributed solely to erasing a label.
7. **Everyone stops at round 30:** all coordination budgets become zero after the common assigned history.
8. **Nobody takes extra work:** all coordination budgets are zero from round 1; original plans still proceed.

Conditions 2-7 have identical paths for the first 30 rounds. The shared and nobody controls intentionally have different earlier histories. A designated target is only a reporting reference in the shared/nobody controls: their seven rotations reuse the same group trajectory and are not seven independent replicates.

Shared scheduling balances total coordination time as a fraction of each person's chosen budget. An exact piecewise-linear water-filling algorithm distributes output until demand is met or capacity exhausted. Handoff balances these same fractions after counting already accepted work and its administration cost. It is an ideal coordinator, not a simulation of how people reach agreement. No one exceeds their chosen coordination limit. Original plans can still be displaced within the total time budget.

## Accounting and checks

Every simulated round checks:

```
completed coordination + unmet coordination = external coordination requirement
coordination time + completed original-plan time + unused time = 1 per member
coordination output = current skill * (coordination time - handoff administration)
0 <= coordination time <= chosen policy budget <= 1
sum(expectation shares) = 1
```

The suite includes 19 tests: closed-form uniform/unequal-skill allocations, saturation, prior-load redistribution, overhead accounting, zero capacity/demand, refusal/all-stop, matched pre-switch history, no-learning/no-memory, inert names, reindexing people with their attributes, symmetry and invalid inputs. These check implementation, not human validity.

Twenty-four seeds (12 discovery, 12 replication), seven target positions, two loads and eight policies give 2,688 main paths of 60 rounds. Another 1,008 paths cross the 12 replication seeds, seven targets, three policies and four sensitivity variants: no expectation memory, no skill learning, no role bias, and handoff cost increased to 0.2. Some variants are deliberately inert for some policies and are controls. Eighteen pairs compare arithmetic tolerances 1e-11 and 1e-13 (36 paths). This is not an ODE, so halving a fictitious time step would change the decision process rather than refine it.

Reported summary outcomes cover rounds 31-60. Ratios use summed outputs divided by summed requirements within each path. Seven target rotations are first averaged within seed; Student-t 95% intervals then use 12 independent seeds per split. These intervals describe synthetic input variation, are unadjusted, and do not quantify uncertainty in the social rules. Every member's post-switch contribution and plan fulfillment is retained. Timelines store group completion and target/other burdens for every main path; 16 complete illustrative paths retain all internal arrays. The runner also audits full internal arrays for all main and sensitivity paths before discarding the unsaved detail.

## Foucault's role in the question

The supplied passage from [Discipline and Punish, Panopticism](https://depts.washington.edu/lsearlec/510/Texts/Foucault-Panopticism.pdf) asks how arranging and differentiating people produces collective capacity and embeds power. [The Subject and Power (1982)](https://warwick.ac.uk/fac/soc/philosophy/intranets/undergraduate/modules/ph348/2013-14/foucault_-_the_subject_and_power.pdf) further connects power to structuring possible actions, subject formation and resistance. Our operational question is whether the expectation “you are the adaptable one” shapes requests, practice and available choices, and what changes when the member refuses or the rule is revised.

The request bias, memory equation and learning law are our hypothetical choices, not equations proposed or empirically validated by Foucault. The model permits refusal and rule changes explicitly. It does not make a moral recommendation to maximize work, measure compliance, or classify a real family. Keeping the group's completed work beside each member's original plans makes the tension visible.
