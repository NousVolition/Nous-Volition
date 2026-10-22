# Local soil and depth history: frozen comparison protocol

Recorded 2026-10-21 before running these candidate comparisons. This local protocol is not an external preregistration. Earlier analyses inspected the seven excluded piles and motivated this question. They are a previously inspected, fitting-excluded retrospective test set, not blind validation. This iteration must select using only the other 87 piles.

## Data and prediction task

Use the same official ISFOG2020 training_data.csv (SHA256 565f5cdd872ec98d2ec9dd73bf7493a5ecf2e2dc1e6751295c05af2de361ff17). Exclude EL, CB, AV, BV, EF, DL and BM before feature construction, fitting, preprocessing or selection. Keep the original notebook's complete cases and first missing integral increment so all models use the same rows. No missing-target interpolation, outlier deletion or prediction clipping. Score all seven piles after the selection artifact has been written and hashed.

Predict measured blowcount in blows/m at a given depth, conditional on supplied normalized transmitted energy, depth, diameter and bottom wall thickness. Energy is operating information; this is not a complete preinstallation forecast or a causal energy experiment. Do not use Number of blows, pile ID, final penetration, previous target values or deeper CPT readings as predictors. IDs are used only for grouped splits and accounting. Source resampling is 0.5 m. Preserve the supplied energy normalization, whose upstream fitting provenance is not established.

## Candidate families (33 fixed candidates)

1. Original: exactly the previous unweighted OLS with three fixed tanh transforms, including its cumulative cone-resistance proxy. This control already includes an accumulated soil signal; it is not a no-history model.
2. Operating: depth (m), normalized transmitted energy (dimensionless), diameter (m), bottom wall thickness (mm).
3. Local: Operating plus current qc, fs and u2 (each MPa).
4. History: Operating plus, for each of qc, fs and u2, the mean of all strictly shallower samples and exponentially weighted shallower-sample summaries with decay lengths 1 m and 5 m.
5. Local + history: union of Local and History.

For each of families 2-5, compare a linear additive basis and a continuous piecewise-linear additive basis with hinges at the fitting fold's 25th, 50th and 75th percentiles of each input. No cross-products or learned tree structure. For each basis, compare ridge penalties alpha = 0.001, 0.01, 0.1, 1.0. Total 1 + 4 x 2 x 4 = 33. No grid expansion after results.

Depth history: for i >= 1, the prefix mean is mean(x_0,...,x_(i-1)); H_i = exp(-(z_i-z_(i-1))/L) H_(i-1) + (1-exp(-(z_i-z_(i-1))/L)) x_(i-1). Initialize H_0=x_0 and prefix_0=x_0. First samples are excluded by the source eligibility rule, but retained to initialize later histories. Construct histories from all available shallower CPT samples, not just rows with target measurements. History is measured along depth, not elapsed time. These empirical summaries cannot identify soil recovery, damping, remoulding, causation or pause effects without further measurements.

Ridge objective: sum_i w_i (y_i-intercept-X_i beta)^2 + alpha ||beta||^2, with w_i=1/(G n_g), so each fitting pile has equal weight and weights sum to one. Preprocessing is fitted only on fitting folds: weighted centering/scaling of raw inputs, fitting-fold quantile hinges, then weighted centering/scaling of the expanded basis. Do not penalize the intercept. Constant columns use unit scale. Original control retains its original unweighted objective for faithful reproduction; its comparison with new models also changes fitting weights. Local-vs-history ablations share the same ridge procedure.

## Selection, nested assessment and sensitivity

Primary selection criterion: mean of whole-pile MAE values (blows/m), giving each pile equal weight. Sort pile IDs, shuffle with NumPy default_rng seed 20261021, split into five folds. Entire piles stay together. Select the smallest mean pile MAE across all 33 candidates. Resolve ties within 1e-10 using fewer raw inputs, linear before hinge basis, stronger ridge, then candidate name. Fit the chosen candidate on all 87 piles. Lock its identity, coefficients and preprocessing, plus the best candidate within each family for predeclared ablation reporting. Test outcomes never change these choices.

Estimate the selection procedure's performance by five outer whole-pile folds. Inside each outer training set, select from the same 33 candidates using four grouped folds (seed 20261021 + 100 + outer index). Score outer validation piles once. Also choose the best member of each family in the inner loop to compare family-level procedures. Nested estimates concern this fixed, retrospectively motivated candidate set; they cannot undo earlier knowledge of the data. Random grouping does not ensure independence across nearby piles or sites.

As a fixed training-only split sensitivity, repeat five-fold selection scores with seed 20261022. Report its winner and ranks without overriding the primary choice. No row-level random splitting. Preserve fold membership, every candidate's scores, per-pile scores and nested selections.

## Final seven-pile assessment and reproducibility

After saving the model lock, evaluate the selected model and each locked family winner on all eligible rows of EL, CB, AV, BV, EF, DL and BM. Report n, MAE, RMSE, bias (prediction minus measurement), R2, negative predictions, pooled scores and equal-pile averages. Show every pile, including regressions. Use identical rows for comparisons.

Compute descriptive paired whole-pile bootstrap intervals for changes in equal-pile MAE, pooling MAE and pooling RMSE (10,000 samples, seed 20261021). These condition on fitted models and these seven selected piles; they omit refitting and selection uncertainty and do not establish generalization to independent sites. No significance claim from treating depth rows as independent.

Check leakage safeguards (held-out target changes, strict-prefix history, fold disjointness, fit-only scalers), ridge against an independent augmented least-squares solution, original-model reproduction, metric arithmetic, complete row coverage, stored-model prediction identity and deterministic reruns. Run the selection command before the evaluation command; evaluation must verify hashes of source data, protocol and analysis code. Publish code, aggregate outcomes, figures, source provenance and limitations. Keep raw competition CSV and row-level predictions local. Physical pile tests do not validate social treatment or community-memory claims.
