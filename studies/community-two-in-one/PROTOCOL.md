# Analysis protocol before outcome calculation

Frozen on 22 October 2026 after inspecting schemas and published descriptions, before calculating the following results. This is a transparent analysis plan, not a registered preregistration. Published results and dataset descriptions have already been consulted; the replication is reserved for parameter selection in this analysis, not an untouched source for model selection.

## Inner dialogue and personal recorded history

Source: Nedergaard, Skewes and Wallentin (2023), public OSF jgx7m, original and replication processed experiment data. Predict reported dialogic inner speech conditional on a valid inner-voice report. Agree and Partiallyagree are positive; Neitheragree nordisagree, Partiallydisagree and Disagree are negative. Structural NA is missing, never a negative report. Retain only chronological qualifying reports with at least one previous qualifying report from the same participant. Report missingness and sample sizes.

Compare a fixed population probability, the last qualifying answer, and a shrinkage estimate from that person's earlier qualifying answers. Population probability gives each original-experiment participant equal weight. History probability is (earlier positive count + lambda * population probability) / (earlier count + lambda). Choose lambda from 1, 2, 4, 8, 16 by lowest participant-mean sequential Brier score on the original experiment, choosing the smaller lambda for a tie. Evaluate the fixed choice on the replication. Within a replication participant, predict before updating with the current answer. No future answer or other evaluation participant enters a prediction. Absolute task time is used for ordering; no unmeasured biography or decay law is inferred.

Report mean Brier score giving each eligible participant equal weight; smaller is better. Paired uncertainty uses 2,000 participant bootstrap draws, seed 20261022. Report history minus population and history minus last with 95 percent percentile intervals. Do not treat a predictive association as a causal effect of history. Add a sensitivity coding where only Agree counts as positive, reselecting lambda using only original data. Report it whether favorable or unfavorable. No multiple outcomes are searched for a winning result.

## Recalled content across life periods

Source: public CRAM v4, Figshare 10246958. A youth bin indexes age at the remembered event as a fraction of current age: 0 is most remote, 9 most recent. Include complete nonnegative integer counts for all eight content categories, with their sum equal to the recorded total, one assigned integer bin 0 through 9, and a valid current age greater than zero and at most 120. Report exclusions rather than silently repairing them.

Use the source's descriptive split: recent bins 8 to 9, remote bins 0 to 7. For people with at least one scored memory in each range, compare each person's recent mean with their remote mean. Bootstrap people 2,000 times for the mean difference. Also calculate for each person the proportion of all their remote/recent pairs in which the remote memory has more counted content, and average these proportions equally across people. Ties are reported separately. Repeat the mean difference restricting to people with at least two memories in each group. This is a within-person cross-sectional comparison, not observation of the same memory fading. Counted content is neither verified accuracy nor felt vividness nor subjective temporal distance. Do not join this dataset to the inner-speech participants.

## Scope and checks

These are observational measurement probes, not a numerical test of the full corpus PDE. Keep the corpus and existing field solver unchanged. Confirm source hashes, chronology, person isolation, future-answer invariance, structural missingness, probability bounds, group-weighting and saved-result reproduction. Export only derived numeric fields with newly assigned dataset-local identifiers; omit free text, original participant identifiers, demographics and exact dates. The original files stay outside the publication folder.

The larger model remains unvalidated until within-person speaking/listening positions, idea transitions, perceived calm and unresolved tension, histories and subjective time are actually measured. A failed or null probe must not be rewritten as confirmation of the whole model.
