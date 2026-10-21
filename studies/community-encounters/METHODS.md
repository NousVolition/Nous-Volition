# Testing wording and prior treatment in community encounters

Completed computational study • Streams and Rocks • 21 October 2026

## Scope and design

This study tests an explicit **synthetic decision procedure**, then checks selected published numerical evidence. It does not recruit people, send messages, call an AI language service or observe a family. It extends the [community connections guide](../community-power/CONNECTIONS.md). Prior allocation and adaptable-role calculations are unchanged.

Two questions are separate: does a procedure respond differently to different expressions of the same authored offer, and can a prior decision change its response to an identical later encounter? Material words are optional descriptions of an encounter. They are not inputs to the decision rule, fixed classes of people, or measured properties of water, fog, smoke or clay.

## What is held fixed in the wording comparison

There are 12 authored offers, each specifying a task, an offered duration and the same maximum duration. Durations cycle through 10, 20 and 30 minutes. Four expressions retain those slots: direct, courteous, formal and forceful. These are descriptive labels chosen by the author, not independent ratings. The full texts appear in [wording_cases.csv](data/wording_cases.csv).

“Same meaning” here means **the same intended propositional offer and limit by construction**. Tone, perceived urgency, relationship signals and implications may differ. No participant has confirmed complete semantic or pragmatic equivalence. This limitation is part of the test definition, not something a numerical result can resolve.

Context is a scalar decision offset of −0.8, 0 or +0.8 in log-odds units. It represents different assumed decision thresholds, not a measured audience or culture. Each paired contrast holds task, offer, limit, context and history fixed. The tasks repeat the same linguistic templates; they are not independent evidence of language generalization. Results are exact contrasts over a designed set, so no sampling confidence interval is assigned to those repeated templates.

## Decision and memory rules

`W = 1` means restriction and `W = 0` permission. The procedure draws a binary decision from a specified probability:

```text
p(restriction) = logistic(log(0.2 / 0.8) + context + beta × x(text) + gamma × m)
logistic(z) = 1 / (1 + exp(-z))
m(next) = rho × m(now) + alpha × W(now)
```

`x(text)` is a deliberately simple literal marker: +1 for the token pair “will not,” +1 for “refuse,” and −1 for “please.” Matching ignores case and punctuation. It does not measure harm, politeness or warranted refusal. Direct and forceful templates both score +1, the courteous template −1, and the formal template 0. The scorer cannot establish what a speaker meant.

The wording-blind rule has `beta = 0`; stress tests use `beta = +0.8` and `−0.8`. Reversing the coefficient reverses which marker is penalized. These contrasts audit consequences of an assumed procedure; they do not independently discover a language bias in people or a deployed platform.

Memory `m` is a dimensionless stored restriction record, not emotion or a measured memory strength. Default retention `rho = 0.8` and input gain `alpha = 0.25` are chosen. Default history sensitivity is `gamma = +1.2`; its sign can also be reversed to model correction. With these defaults and binary inputs, memory stays between 0 and 1.25. All coefficients are illustrative and were not fitted to the papers. One step is one encounter, not a second or day.

## Paired history intervention

At encounter zero, one copy of an otherwise identical actor is forcibly permitted and the other forcibly restricted. The resulting states are 0 and 0.25. All later wording is the same formal offer. Each pair receives the same context sequence, drawn uniformly from −0.8 to +0.8, and the same uniform random numbers. Shared randomness reduces variance; it is a numerical coupling, not a claim that people's decisions share hidden random numbers.

Only encounters 1–30 enter the outcome. The forced initial difference is excluded. Six policies each use 1,000 independent seeds:

| Policy | Mechanism |
| --- | --- |
| History blind | Stored history does not enter the decision probability; `gamma = 0` |
| Record only decay | The initial restriction record fades; later decisions do not feed back |
| Reinforcing feedback | Later restrictions also enter memory; `gamma = +1.2` |
| Corrective feedback | Prior restrictions reduce the next restriction probability; `gamma = −1.2` |
| Reset before round 6 | Both stored states are cleared before encounter 6; subsequent dynamics continue |
| Zero input | `alpha = 0` prevents restrictions entering memory |

Unlike the earlier adaptable-role model, this module has no practice learning or skill state. The history intervention isolates the stored decision record. The reset control clears that model state; it does not claim that real people can erase experiences or that record deletion always repairs harm.

For each seed, average the paired difference in later restriction outcomes over 30 encounters. Then summarize across seeds using the mean and a normal Monte Carlo interval `mean ± 1.96 × sd / sqrt(1000)`. Encounters within a sequence are not treated as independent observations. These intervals describe random simulation error under fixed rules, not uncertainty about human behavior. Sensitivities cross three retention rates with four history coefficients, using the first 200 seeds. They are parameter checks, not independent replications.

The joint check evaluates every wording and context with both initial histories under `beta = 0.8, gamma = 1.2`. It records 144 paired probabilities. Separate history-order checks compare older and more recent restrictions with the same count. The discrete process has no physical time step to refine. Tests instead compare against an analytic first-step log-odds difference, exact memory decay and the memory bound.

## Published evidence and exclusion rule

Published numbers are transcribed in [source_estimates.json](source_estimates.json), with citation, source page and scope. A coefficient `b` should correspond to an odds ratio `exp(b)`. The audit allows ±0.005 rounding in both displayed quantities. An incompatible interval excludes that contrast from the retained estimate plot. Approximate 95% intervals use `exp(b ± 1.96 × SE)`. They cannot replace a raw-data refit. Contrasts sharing a control group are not pooled without their covariance.

The wording audit covers every donation contrast from the three main experiments in [Juanchich, Sirota and Bonnefon](https://jfbonnefon.github.io/publication/jbdm19/jbdm19.pdf), not a selection based on significance. Two Experiment 2 entries fail the consistency check. Experiment 3 coefficients apply to the donation-first condition because its regression includes order interactions. The raw-data link printed in the paper returned HTTP 404. An interval containing one does not prove equivalence or an absent effect.

The history arithmetic uses rounded proportions reported by [Muchnik, Aral and Taylor](https://snap.stanford.edu/class/cs224w-readings/muchnik13bias.pdf). It computes differences and ratios without inventing participant counts, uncertainties or a new statistical test. That experiment concerns prior displayed ratings of a comment and subsequent viewers' ratings, not an author's treatment across later comments.

Sources were read during design. They are external evidence checks, **not untouched model-selection holdouts**, and the synthetic coefficients were not calibrated to them. Source consistency is one screening check, not certification of a study's validity. Full papers are not redistributed.

## Verification and next observational test

The runner writes its protocol and source hashes before the ensemble and refuses an existing output directory. Nineteen unit checks cover paired controls, slots, token matching, exact decay, a state reset, source arithmetic, reproducibility and bounds. [verify.py](verify.py) checks saved results and selected independent reruns. Source code, all aggregate input estimates, every authored wording case, seed summaries, example sequences and sensitivity results are supplied.

For a social test, independently assess whether paired expressions preserve the intended content for speakers and recipients. Then compare actual treatment under predeclared matching rules; record reasons, severity and consequences. For history, use time-ordered observations with an appropriate causal design and a history-blind comparison. Freeze decisions before examining new sequences, separate people or groups where needed, and retain refusals and corrections as possible outcomes. The current simulation cannot supply those missing observations.
