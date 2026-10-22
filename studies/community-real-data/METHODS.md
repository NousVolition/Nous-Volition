# Real encounters: analysis methods

This study reanalyses public observations. It does not generate fictional people or use the earlier synthetic decision rule to create outcomes. The analysis plan is in [protocol.json](data/protocol.json); the changes after inspecting file structure are in [protocol_amendments.json](data/protocol_amendments.json). Source publications and previews informed selection. This is an exploratory reanalysis, not a preregistration, a new experiment, or an untouched validation set for the community model.

## Wording, content and judgment

Inputs are the released content and toxicity task files from [ParaDetox](https://github.com/s-nlp/paradetox), pinned to immutable Hugging Face revisions in [sources.json](sources.json). Original comments came from social-media corpora; crowd workers wrote the alternatives. These are human-generated research rewrites and human annotations, not naturally observed before-and-after moderation decisions.

The [primary paper](https://aclanthology.org/2022.acl-long.469/) describes separate content and offensiveness tasks, with 3–5 annotators and Dawid–Skene aggregation. Its collection process selects candidates and filters them in stages. Released Boolean labels are treated as publisher judgments; individual votes and their uncertainty are unavailable here. We do not call a `match=True` label proof of identical meaning. In particular, intended meaning, propositional content, evaluative commitment and pragmatic force are different questions.

1. Parse only explicit `True`/`False` values. Collapse exact duplicate rows. Duplicates are not additional people or votes.
2. Group content by the exact ordered original/rewrite pair. Exclude pairs with conflicting released labels. Group toxicity by exact text and exclude conflicting text labels.
3. Report content acceptance and rejection for all unique unambiguous pairs, then for pairs with changed strings. Keep identical-text controls separate.
4. For the primary paired judgment comparison, require changed text, `match=True`, and an unambiguous toxicity label for **both** versions. Join exact strings, without lowercase, punctuation normalization, fuzzy matching or an assumed positive label based on the column name `toxic`.
5. Report all four possible label combinations and the change in the fraction marked offensive. Missing joins remain missing; a rewritten comment marked nonoffensive does not by itself establish a change from its original.
6. Resample original-text clusters 2,000 times with seed 20261021. Each cluster brings all its alternatives together. The main estimate weights pairs; the sensitivity estimate gives each original equal weight. Percentile intervals describe resampling of this selected corpus, conditional on its fixed labels. They do not cover unknown annotator error, crossed dependence through shared rewrite text, selection bias or population generalization. No causal significance test is attached to this selected wording contrast.

Only 3.69% of the matched changed pairs have both labels available through this exact join. Original strings can obtain labels because the same string occurs in the released toxicity-task pool; the release does not supply a fresh paired rating experiment for every original. That selection is a major limitation. Its direction cannot be corrected from these files.

### Meaning audit and strong language

Select the 24 lowest SHA-256 hashes of `original + NUL + rewrite` among changed pairs with unambiguous `match=True`. This rule was specified before generating the sample. The sample spans the broader matched pool, not only the 941 fully joined pairs. The assistant reviews target, proposition, negation, evaluation and speech act. Results are in [meaning_audit.csv](data/meaning_audit.csv). This is **one AI review**, not new independent human validation or a measured population error rate.

The audit uses three judgments: a substantive change, no clear loss of core content, or uncertain. Even the second category does not imply identical force. Reasons remain visible, including disagreements with the released label. Pair hashes let a reader recover exact examples from the pinned download without republishing the comments. `inspect_audit.py` prints that review packet locally for a human check.

Strong criticism, anger, accusations and refusal are not automatically errors to remove. An offensiveness label does not establish that a statement is false, unjustified, or deserving of a penalty. Removing an accusation or converting a judgment of a person into a judgment of an action can alter the substance. The present work checks such alterations; it does not prescribe universal softening.

## Prior treatment and later recognition

The [Restivo–van de Rijt randomized experiment](https://doi.org/10.1371/journal.pone.0034358) assigned an initial Wikipedia award to 100 contributors and withheld it from 100 controls. Participants were sampled from highly productive, previously unawarded nonadministrators. The follow-up was 90 days. The primary endpoint here is whether a person received any further award from other contributors: 12 versus 2 people. These are **exact published endpoint counts**, transcribed in [wiki_counts.json](data/wiki_counts.json), not invented individual records.

The table is `[[12, 88], [2, 98]]`. We calculate a two-sided Fisher exact test, risk difference with a Newcombe interval formed from Wilson limits, and risk ratio with an approximate log interval. The primary interval is the risk-difference interval. Fisher's result is checked by direct hypergeometric enumeration. Pearson's uncorrected test is computed only to check the published rounded p-value; it is not a second discovery. No adjustment for post-treatment productivity is made: that would change the causal question and could condition on a mediator.

The randomized contrast supports a total effect of initial recognition on later recognition in this setting, subject to the experiment's design and possible interference. It does not isolate psychological memory, public reputation, changes in contribution or visibility. It supplies no estimate for negative treatment, every later interaction, or arbitrary communities. It does not fit the earlier model's memory coefficient or decay rate.

### Aggregate chronology check

The [Learning Data Science provenance page](https://learningds.org/data_sources.html) attributes `WikipediaExp.csv` to van de Rijt. The pinned file has 242 **group-day summaries**: 121 days for each group. It is not a release of 200 individual trajectories. Its award events total 14 versus 3, consistent with the paper; events and people are different denominators. The chronology is descriptive, with no confidence band obtained by treating days as independent people.

The file marks a control award on day 7 and the first treated award on day 8. The paper's day-8 statement occurs in a comparison of experimental recipients, so these dates can coexist; we do not label this a source inconsistency. Individual event-time trajectories are unavailable. The 90-day person-level endpoint counts come from the paper rather than the group-day file.

The file's productivity series is 1 at day 0. Its raw day-90 ratio is 1.327; subtracting the baseline before taking the ratio gives 1.595. This explains how an approximately 60% difference in post-baseline gains can coexist with a 33% raw endpoint difference. This is a scale check, not a reconstruction of individual productivity tests.

## Scope, access and reproducibility

No human participants were recruited, contacted or experimentally manipulated. The annotation files and the author-attributed aggregate file were downloaded. They are not redistributed in this repository; the downloader records URLs, immutable revisions and SHA-256 hashes. Exact published endpoint counts and derived label counts are included with attribution. This report does not convert dataset labels into judgments about named people.

Other searches did not yield usable individual randomized Reddit records: the old author index timed out, its successor returned an access error, and a current `/data/` URL redirected to a teaching page. Bitcoin reputation snapshots were downloaded during discovery but not analysed: complete encounter history and visibility provenance were not established, and the randomized recognition endpoint answers the narrower causal question more directly. These sources supply no results in the present report.

These two datasets do not jointly observe meaning, wording, context, treatment and memory in the same encounters. The next direct test needs independently rated semantic equivalence, recorded decisions under a fixed policy, and longitudinal outcomes with an identified history intervention or a defensible causal design. Retain both forceful and softened wording, failed equivalence cases, and participants' own accounts of intent.
