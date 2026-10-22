# Moderation wording and penalty methods

The two questions have different identification requirements. A wording contrast needs meaning-equivalent messages and comparable moderation opportunities. A history effect needs a later outcome and a credible account of what would have happened without the earlier penalty. These public archives supply actual recorded actions, but do not jointly identify either causal effect.

## Meaning and wording

The CGA-CMV archive contains 6,842 selected conversations, paired within original posts. Its label records whether the final comment was removed for Rule 2. We use only the unique final leaf as an outcome-bearing comment. Earlier comments are context, not silently assigned negative outcomes. “Comparison” means no recorded Rule-2 removal in this sample; it does not establish explicit moderator approval or absence of every possible sanction.

The dataset deliberately balances removed and comparison conversations. Every supplied pair has opposite outcomes by construction. Reporting those pairs as 100% wording discrimination would be invalid.

We exclude empty and deletion/replacement texts, compute token-set Jaccard overlap, and inspect the 12 most overlapping same-post endpoint pairs, breaking ties by SHA256 of sorted IDs. One assistant reviewed assertions, referents, scope, stance and interpersonal force with outcome labels visible. This is an auditable screening review, not independent human adjudication. It found substantive differences in all 12. Full context can be reconstructed locally with `inspect_meaning.py`. The audit notes contain paraphrased reasons, not republished removed messages or account names.

A secondary search checks all endpoints for identical text and for changed texts with Jaccard at least 0.8 and at least eight word tokens each. It finds neither. Lexical retrieval can miss paraphrases; no conclusion that the corpus has no equivalent meanings follows. Original message intent, moderator exposure, and the exact message version at moderation are not independently observed. No causal wording estimate is reported.

## Recorded block episodes

The Cornell legacy Wikipedia log has 5,227,809 events spanning 23 December 2004 to 4 June 2018. We exclude IP/range targets and suppressed targets, then group the remaining events by a SHA256 account key. This is a broad named-account cohort, not the published paper’s established-editor cohort. It includes accounts with varying purposes and activity.

Events are sorted by timestamp and log ID. A new `block` starts an episode when no block is active. `reblock` and a `block` while active update the existing episode; an `unblock` closes it. Automatic expiry also ends the episode. Accounts with orphan unblocks/reblocks, unknown durations or nonpositive expiry are excluded conservatively. This complete-log exclusion can itself select the sample. No duplicated log IDs were accepted: the SQLite primary key would fail on duplication.

Explicit expiry timestamps take priority. Documented indefinite values, including `never`, are infinite. Unambiguous second/minute/hour/day/week durations supply a fallback; other strings remain unknown. The official [MediaWiki documentation](https://www.mediawiki.org/wiki/API:Block) supports the expiry and reblock interpretation. Modern multiple-block features are not inferred for this historical log.

For the primary cohort, the first observed episode must start in 2006 or later, initially receive a finite duration, and have a known end at least 180 days before the log endpoint. The next distinct episode must start strictly after that end and within 180 days. An account’s first observed episode is not guaranteed to be its first-ever sanction: the archive starts in 2004 and hidden records, renamed accounts and other omissions remain possible.

The duration comparison concerns **initially assigned restriction length**, not actual time served. We compare first versus second assignments only where both are finite; indefinite second assignments are counted separately. Each account contributes one pair. We report longer/equal/shorter counts, medians, paired log2 ratios, a sign test excluding ties, and 2,000 paired percentile bootstrap draws with seed 20261021. Sorted pairs make the aggregate-count reproduction deterministic. Extremely small probabilities are stored on a logarithmic scale instead of claiming p = 0. Bootstrap intervals quantify resampling of this selected cohort, not uncertainty from missing history, policy, dependent moderators or confounding.

Sensitivity analyses use 30 and 90 day windows, the same blocking moderator, and a subset with disruption-related words in both reasons. The latter is a transparent keyword filter, not validated coding of equivalent conduct or equal severity. No new offence-severity labels are invented. Equal median bootstrap endpoints can arise from the discrete standard durations and do not imply absence of uncertainty.

No second block means no recorded block in the window. It does not establish that an account stayed active, behaved better, or escaped scrutiny. A larger second assignment does not isolate memory: conduct, visibility, policy and moderator choice may change. “Institutional memory causes harsher treatment of the same conduct” remains untested.

## Reddit penalty-history coverage

The Srinivasan et al. release identifies 775 matched comparisons outside the original discussion and 1,139 inside it. It supplies matching IDs, first-removal IDs, and first/second-removal IDs, not complete subsequent removal outcomes or sanction timestamps. We join positive IDs and the independently recorded CGA-CMV endpoint labels. Absence from the first/second list stays unknown because third and later removals are not listed. A missing outcome is never converted to approval.

For each matched row we require treatment before/after and control before/after outcomes. None has all four. We calculate worst-case bounds for `(T_after − T_before) − (C_after − C_before)` by letting every unknown binary outcome vary over 0–1. These are conservative logical bounds, not confidence intervals or identified causal effects. Shared unknown IDs could narrow the bounds if linked jointly; the broad reported bounds do not identify a direction.

The published paper reports a reduction in immediate subsequent removals under a delayed-feedback quasi-experimental design. That is a literature finding under its assumptions, **not a numerical replication completed here**. Its outcome also combines later behaviour with moderation; it does not by itself show that identical later conduct received a different decision because of past penalties.

## Reproduction and provenance

`data/protocol.json` and `data/protocol_amendments.json` retain the analysis plan and parser corrections. This is exploratory reanalysis after seeing source findings, not preregistration, an independent model-validation holdout, or a new participant experiment. `sources.json` pins six downloaded files by SHA256. Raw messages, IPs and accounts remain outside the published study. The 1.67 GB block log is downloaded only with the explicit large-file option. Additional disk space is needed for the local SQLite cache.

Quick reproduction of all nine finite-duration summaries uses published aggregate counts. Full reproduction additionally reconstructs the cohorts from the raw log and reruns retrieval and coverage. Meaning judgments are supplied review annotations; their validity requires further independent review, not just passing code tests.

Sources: [CGA-CMV documentation](https://convokit.cornell.edu/documentation/awry_cmv.html), [Chang and Danescu-Niculescu-Mizil, Trouble on the Horizon](https://aclanthology.org/D19-1481/), [Cornell dataset catalog](https://convokit.cornell.edu/datasets.html), [Trajectories of Blocked Community Members](https://arxiv.org/abs/1902.08628), [Srinivasan et al., Content Removal as a Moderation Strategy](https://doi.org/10.1145/3359265), [authors’ released data](https://github.com/BoulderDS/effect_of_comment_deletion_cmv_dataset).
