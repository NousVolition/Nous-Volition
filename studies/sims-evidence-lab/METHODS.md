# Model methods

## Participants and decisions

Nine numbered participants choose A or B. A ring gives each participant two neighbors; in a star, SIM 0 sees eight neighbors and each leaf sees the hub. Each network second uses a shuffled sequential update order, with activation probability 0.25 per participant. A block lasts 120 simulated seconds. Later decisions see earlier updates in that second.

| Rule | Action on an active turn |
| --- | --- |
| Copy neighbor | With probability 0.02, when enabled, flip the current choice. Otherwise sample a neighbor uniformly and copy, with 0.15 refusal probability if the proposed choice differs. |
| Hold start | Choose the participant's original starting choice. |
| Majority | Choose the local majority; retain the current choice on a tie. |
| Oppose | Choose the opposite of the local majority; retain the current choice on a tie. |

The original network model offers ordinary copying and a holding/opposing exception. The investigator models make all four rules available to each participant. The stated claim and the actual behavior rule are separate variables.

## Predict before observing

For every active decision, the investigator receives the participant's current and original choices, neighbor choices, and initiative setting. It computes each candidate rule's A/B probabilities before the simulator draws the action. The predictor and evidence scorer never receive the actual rule setting.

For copying, let `b = 1` when the prior choice is A, `f` be the fraction of neighbors choosing A, and `e` be the initiative probability:

```text
P(A | copy, context) = e (1 - b) + (1 - e) (0.85 f + 0.15 b)
```

The other three rules give probabilities 0 or 1 for a fully specified context. Inactive turns add no behavioral evidence.

The four candidates start with equal weights. Each observation multiplies each weight by that candidate's probability of the observed action; normalization makes the weights total 100%. The implementation uses log likelihoods to avoid numerical underflow during accumulation. A zero-probability action rules out that candidate for the scored block.

**Relative support** compares these four candidates under these assumptions. It does not measure honesty or establish that an omitted rule is impossible. Tied explanations remain tied. A likely explanation can still be wrong in a finite sample, especially when the network presents few distinguishing contexts.

## Controlled probes

Probe mode fixes the focal participant's prior choice at A or B and varies the number of A neighbors over `{0, floor(degree/2), degree}`, removing duplicates. Each distinct context is repeated eight times in shuffled order; the focal participant is forced active. The original starting choice used by Hold remains fixed. Other participants do not act during a probe.

A ring gives 48 decisions per participant and 432 total per block. A star gives 48 hub decisions plus 32 per leaf, for 304 total. Probe results are separate intervention trials. They describe decisions under imposed contexts.

## Evidence and response

Each participant receives its own complete likelihood summary and up to three representative actions. Repeated-round examples prioritize zero-probability contradictions, then high likelihood ratios. All recorded actions enter the scores.

Response policies are explicit model assumptions:

| Policy | Response when the evidence trigger is met |
| --- | --- |
| Revise claim | Change the stated rule to the identified alternative; keep behavior. |
| Align behavior | Retain the claim and issue a command to follow it. |
| Adopt best fit | Adopt the identified alternative as both claim and behavior. An already-matching behavior is recorded as unchanged. |
| Promise only | Promise to follow the claim while retaining the current behavior rule. |
| Keep both | Acknowledge the evidence and retain both settings. |

Below a policy's evidence requirements, it retains settings and requests more evidence. These choices implement a specified simulation policy; they are not inferred psychological traits.

### Version-specific triggers

The single-exchange model requires at least 12 actions and a unique alternative with at least 80% relative support and at least 10 times the stated rule's likelihood.

The repeated-round model also permits a response after at least 12 actions when an observed action had zero probability under the claim. This can trigger aligning behavior even if the remaining candidate explanations are tied. A policy that revises a claim to another rule still requires an identified alternative with the 80% and 10-times thresholds.

## Repeated rounds and promises

One initial action block supplies round 1's evidence. Participants receive evidence and respond while network decisions pause. Their resulting claims and behavior rules apply to the next action block. That block is both the follow-up for this round and the evidence for the next; it is not counted twice. The original Hold reference is preserved. In network mode, the final network choices also carry forward.

Each action block starts fresh likelihood weights. This prevents evidence about a previous behavior rule from being combined indiscriminately with observations after a change. Earlier evidence packets, replies, transitions, and promise reviews remain in round history. The latest recorded promise review is shown in later exchanges even if no new promise is made.

The history uses actual model-rule transitions:

- C: a changed stated rule.
- B: a changed behavior rule.
- P: a promise targeting a rule different from the current behavior, without a behavior-rule change.
- C+B: both changed.
- A dash: none of these events occurred in that round.

An action changing A/B alone is not necessarily a behavior-rule change: a fixed rule can produce different actions in different contexts.

Promise assessment uses only the promised rule and subsequent observations:

- **Contradicted:** an action had zero probability under the promised rule.
- **Supported:** at least 12 actions and a unique best fit with at least 80% support matching the promise.
- **Alternative favored:** an alternative passes the support threshold and has at least 10 times the promise's likelihood.
- **Inconclusive:** the available evidence meets none of those conditions.

P records the simulator's lack of follow-through. The evidence assessment can remain inconclusive even when the simulator's internal rule is known to the reader.

## Reproducibility and scope

The JavaScript simulation uses deterministic seeded randomness with separate initial-state, schedule, and action streams. Different round salts give fresh action blocks. Changing a stated claim alone does not affect the initial action simulator; subsequent behavior can change through the explicitly configured response policy.

The exported latest snapshot preserves the user's eight-round setting with seed `20261011`, both SIMs 0 and 1 initially holding, and the stated rules Majority and Oppose respectively. The comparison runners retain the separate seed-`20261008` examples. Their outcomes should be attributed to those exact configurations.

These models describe the specified network, four candidate rules, evidence windows, and response policies. They contain no human measurements, learned personality reconstruction, or empirical identification of a historical person's decisions.
