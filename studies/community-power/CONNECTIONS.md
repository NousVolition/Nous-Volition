# Meaning expression context treatment and memory

Streams and Rocks community model • 20 October 2026

**The same person can be water, fog, smoke or clay as a situation changes.** To understand an encounter, follow what they mean, how they express it, the circumstances in which it is received, how they are treated, and what carries into the next encounter. A material name can help describe that experience; it does not decide the person's worth or what treatment they deserve.

The supplied diagrams provide this conceptual connection. The existing simulations test allocation rules and a particular feedback rule for remembered contributions. They do not yet test whether wording changes how real people are treated. The distinction below keeps the language strong and makes the next comparisons concrete.

**Completed extension, 21 October 2026:** [wording and prior-treatment tests](../community-encounters/README.md) now implement an explicit synthetic decision procedure with wording-blind, history-blind, corrective and reset controls. The chosen wording penalty gives a 25.4-percentage-point mean difference; reversing it reverses the result. A prior restriction changes the next 30 encounters' restriction rate by +1.28 points under reinforcement and −0.62 under correction. These values follow the chosen rules. Published aggregate evidence is checked separately, with two inconsistent wording estimates excluded. The need for new comparable human observations remains.

## Five parts of an encounter

| Part | Meaning in this model | What to record |
| --- | --- | --- |
| Meaning or **Sens** | What the person intends to communicate | Their account of the intended meaning, with uncertainty or disagreement preserved; an observer's interpretation is a separate field |
| Expression or **Sin** | The words, action or silence through which meaning is expressed in this setting | Exact wording or a traceable account of the action, including register and timing; silence does not have one automatic meaning |
| Context **c** | Conditions relevant to interpreting the expression and making a decision | Audience, relationship, rules and policy version, resources, relevant history and available alternatives, specified before comparing outcomes |
| Treatment | What others or an institution actually do in response | Permission or restriction, allocation of work or help, reasons, severity, duration and practical consequences; a binary decision captures only part of this |
| Memory | What from the encounter persists and can affect a later one | The person's remembered experience, other people's expectations and institutional records separately; identify who holds each record and whether it can be corrected |

The proposed sequence is **stated meaning → expression in context → treatment → remembered consequences → a later encounter**. Context also affects which expressions are available. A later response may change the speaker's expression or their intended meaning; do not assume either stays fixed. These arrows organize questions, not an established causal chain.

Water can describe adapting an expression while maintaining a boundary. Fog can describe meaning that an audience only partly understands. Smoke can describe an earlier account circulating into a new setting. Clay can describe an impression that persists or is reshaped. These orientations can coexist, change or be rejected. They do not automatically set a score, a permission or a memory parameter. See the [situational roles and four working hypotheses](SITUATIONAL_ROLES.md).

## What supports each connection

**Source described** means the relationship appears in the supplied material. **Tested in a synthetic model** means its consequences were calculated under stated fictional rules. **Defined or logically derived** means it follows from definitions and assumptions. **Needs observations** means the proposed claim about people has not been established by these calculations. A solid arrow in the source means source described, not empirically validated; a dashed arrow marks a proposed operational connection.

| Connection | Support available now | What still needs testing |
| --- | --- | --- |
| Meaning is expressed within a context | Source described in the Sens–Sin–Context diagram; the five-part record above is an operational proposal | Whether the record captures the speaker's meaning and the receiver's interpretation without collapsing them into one judgment |
| Expression affects treatment | Tested under a chosen literal-marker rule in the [synthetic encounter audit](../community-encounters/README.md); published wording summaries checked separately | Independently assess meaning equivalence and compare actual treatment; the authored templates and assigned penalty do not validate the social hypothesis |
| Rules and priorities affect access and allocation | Tested in the [allocation benchmark](README.md), with explicit constraints and a chosen weighted objective; [methods](methods.md) and [saved checks](verification.json) | Whether these rules describe a particular community; the solver has complete information and does not interpret language or consent |
| Treatment can be compared within a declared scope | Defined or logically derived once action, context and decision coding are fixed; see the consistency rule below | Comparable observed cases, including reasons, severity and duration; equal binary decisions alone do not demonstrate fairness |
| Past contributions affect later requests | Tested in the [adaptable-role experiment](../adaptable-roles/README.md) through its explicit expectation update and controls | Whether observed expectations or institutional records follow that update; whether earlier treatment causes later treatment after relevant alternatives are considered |
| Past treatment affects later treatment | Tested through stored restriction records in the [synthetic encounter audit](../community-encounters/README.md), including reinforcement, correction and resets | Actual time-ordered encounters with relevant alternatives controlled; a comment-rating experiment concerns later viewers of the same comment, not every kind of personal history |
| Adaptation can preserve meaning or alter it | Source described through the Socio-Didact and semantic-change proposals | Repeated accounts across contexts and time; preserve the possibility that someone resists, refuses, revises their meaning or rejects the label |
| A score or stored field maps to social permission | Proposed operational connection in the diagram | Specify the action representation, metric, update law and decision rule, then compare predictions with new observations |

The 20 October conceptual addition introduced no new human observations or numerical experiments. The linked 21 October extension adds synthetic calculations and published-summary arithmetic, with no newly collected human observations. Earlier numerical results retain their original scope.

## An example that keeps the force of the language

Consider a **fictional** member who says, “I can help for twenty minutes. I will not take the whole task.” Their stated meaning is a limited offer. The exact sentence is the expression. The task, available helpers, prior agreement and authority to assign work form the context. Whether the group accepts the limit, redistributes the task or assigns the whole task anyway is the treatment. Whether the person is subsequently treated as always available is a possible memory effect.

If the whole task is assigned despite the stated limit, describe that action directly. If the person says, “I was forced to adapt,” preserve their words and attribution. Establishing what constrained their choice requires evidence about consequences and alternatives. Strong language can remain precise without turning a fictional example into an observation.

To test a wording effect, compare the limited offer with another expression of the same intended limit under declared comparable conditions. To test unequal treatment of actors, compare the same action and expression across actors while recording relevant differences. To test memory, follow later requests and prior events in time. A different outcome by itself does not identify which connection caused it.

## What the existing memory rule actually does

In the [adaptable-role model](../adaptable-roles/model.py), policies that route requests by expectation use each person's weight `b_i` to determine part or all of their request share. Shared allocation instead balances work against available capacity. When the group completes some work, the default expectation update is:

```text
b_i(next) = 0.75 × b_i(now) + 0.25 × share of this round's completed output
```

The weights are dimensionless and sum to one. If no output is completed, the weights remain unchanged. The assignment policy can separately direct 75% of requests to a designated person. Practice also changes skill through a separate learning rule. These are declared assumptions about fictional coordination, not estimates of human psychology.

**The existing no-memory control freezes the expectation weights at their initial equal values; it still allows learning through practice.** It is not a control that removes every consequence of history. The separate no-learning and no-bias controls help distinguish those mechanisms. See [methods](../adaptable-roles/METHODS.md), [sensitivity results](../adaptable-roles/analysis/sensitivity_summary.csv) and [verification](../adaptable-roles/verification.json).

Removing the assignment bias leaves the accumulated expectation weights and skills in place. Sharing after the switch changes allocation and resets expectations, so that comparison does not isolate the effect of removing a word. That adaptable-role model does not translate a reported insult, a moderation flag or a material name into a later penalty. The separate [encounter module](../community-encounters/METHODS.md) now specifies a hypothetical restriction-record rule; it is not a fitted law of moderation or human memory.

## Connections that require explicit definitions

The source's utility **U(a; c)** is a chosen value model. In the allocation study the objective counts weighted need fulfillment. Neither that objective nor an arbitrary score measures intended meaning, human worth or consent. A proposed mapping from meaning to a proxy must explain what it retains and loses. The source's **Socio-Didact** connection asks how someone observes and adapts while preserving what matters to them; that learning claim is not supplied by the allocation objective.

For the binary decision convention in the screenshot, **W = 1 means restriction and W = 0 means permission**. On a shared action domain `A`, a decision rule defines a permitted set:

```text
Ω_i(c) = {a in A : W(i, a; c) = 0}
```

This connection is valid by definition only when the decision and set refer to the same actor, action representation, context and policy version. An optimizer chooses within its feasible set; a utility score alone does not define every constraint.

The scoped universal consistency claim is `W(i, a; c) = W(j, a; c)` for every actor pair and action in the declared comparison. One confirmed comparable counterexample defeats that deterministic claim. For a stochastic rule, unequal single outcomes do not by themselves establish unequal decision probabilities; repeated trials are needed. Missing or incomparable records do not automatically become counterexamples. Equal permission/restriction outcomes can still conceal different reasons, severity or burdens. Consistency and fairness need separate assessments.

Declare relevant context and any actor-specific modifiers before inspecting disparities. Different settings can have different rules, but redefining context after seeing a disparity must not make it disappear by definition. If a policy promises invariance across a difference, test that promise explicitly.

**Score clearance is not automatically geometric distance.** As an illustrative mathematical case only, if normalized features `x` obey `w·x ≤ b` under a declared Euclidean metric and nonzero `w`, signed clearance is `b − w·x` and signed distance to the plane is `(b − w·x) / ||w||`. Changing feature scales or the metric changes that distance. No social distance has been measured by writing this formula.

The source's field quantities **S, q and a(q)** also need definitions, units, a time-update rule and a mapping to observable decisions. Stored input in a physical or mathematical field does not establish that institutional penalties accumulate in the same way.

## Comparisons that could strengthen the claims

1. **Recover the language audit.** The selected counts displayed in the screenshot total 83 (69 in its first count column and 14 in its second). This verifies arithmetic only. Reproducing the count requires the exact manuscript and version, matching and overlap rules, traceable occurrences, and separation of quotations from narration. Frequency alone establishes neither bias nor warranted use. Keep participant representations of “the Left” distinct from researcher representations of liberalism or public discourse; these referents are not interchangeable.
2. **Compare expression and treatment.** Record meaning, wording, actor, context, history, policy and outcome consistently. Decide in advance which differences should leave treatment unchanged. Use paired alternatives and repeated cases, including cases that would weaken the hypothesis. Check that the supposed wording alternatives preserve content and meaning for the participants.
3. **Test memory over time.** Specify which previous event updates which state, who has access to it, how it changes later requests or decisions, and how it decays or is corrected. Compare with a model omitting that history, while keeping practice learning separate. Frozen-state and order-shuffled controls can diagnose mechanisms but are not interchangeable. Keep later outcomes out of earlier predictors.
4. **Reserve new observations for evaluation.** Use development records to choose mappings and parameters. Then freeze those choices and evaluate entire new sequences, with people or groups separated where needed to prevent leakage. Report uncertainty, alternative explanations and failures. Data that influenced a revision remain development evidence even if no parameters were fitted to them.

A useful episode record contains the time, actor, speaker's intended meaning, exact expression, recipient's interpretation, policy and relevant context, decision, actual treatment and reasons, prior records available at that time, and later outcomes. Add who chose the material description and whether it was accepted, contested or changed. Use attributable accounts with appropriate consent; the record is a proposed research structure, not a population measurement or a classification of people.

## Source scope

The four supplied screenshots are the sources for the conceptual diagram, the evidence roadmap, the scoped consistency example and the reported language counts. Their underlying manuscript and corpus were not supplied with this addition. Source-described connections and reported counts therefore retain that status.

For traceability, the attachment filenames begin `codex-clipboard-7f9d094a` (connections), `codex-clipboard-894ba7b6` (roadmap), `codex-clipboard-a853434a` (consistency) and `codex-clipboard-9f7c646a` (language counts). The screenshots are not redistributed here. The formal examples and proposed comparisons above are this project's operationalization of that material.

Foucault's place in the model remains the question of who defines categories, controls access, records conduct and makes an expectation persist. The [passage-to-model interpretation](interpretation.md) gives its source and limits. The physical substance calculations supply no validation of these social connections.

[Community allocation results](README.md) · [Situational roles](SITUATIONAL_ROLES.md) · [Adaptable-role results](../adaptable-roles/README.md)
