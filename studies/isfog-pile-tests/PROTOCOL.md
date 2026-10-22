# Seven excluded piles: fixed retrospective protocol

Recorded on 2026-10-21 before computing the seven-pile outcomes in this analysis. This is a local analysis record, not an externally registered preregistration.

Use the user-supplied `isfog-2020-linear-model-demo.ipynb` and the official ISFOG2020 `training_data.csv`. Exclude entire locations EL, CB, AV, BV, EF, DL and BM from coefficient fitting. Fit on the remaining locations. Preserve the notebook's feature scales and complete-case rule. Do not tune on the seven test outcomes, clip predictions, remove outliers or choose a new model after seeing performance.

The primary model is ordinary least squares with an intercept and three predictors: `tanh(5 E - 0.5)`, `tanh(0.001 S - 1)` and `tanh(0.1 z - 0.5)`. E is the supplied normalized transmitted energy. S is the source's cumulative sum of pi times diameter times depth increment times cone resistance, calculated within each location in the original ascending depth order. Its first increment is missing, as in the notebook. S is an integrated cone-resistance proxy, with numeric units MPa m² (MN), not the kN label used in the notebook. No specified shaft friction factor is supplied.

Report all seven piles, including failures, using sample count, RMSE, MAE, signed bias (prediction minus observation), R², negative prediction count and row coverage. Report pooled metrics and equal-pile mean RMSE/MAE separately. Compare against a training-mean constant, the fixed transformed-depth-only model and the notebook's transformed-energy-only model on the same eligible rows. These comparisons do not select a replacement model. Reproduce the four saved training R² values and saved CB R². Record input and source hashes.

As a predeclared cleaning sensitivity, fit and evaluate the same three-predictor formula using only required nonmissing fields, and compare it with the notebook's all-column complete-case rule. Describe additional rows and changes explicitly. No interpolation of missing target values. No use of cumulative number of blows as a predictor.

Resample whole test piles (10,000 bootstrap samples; seed 20261021) for descriptive pooled RMSE and MAE intervals. Keep the fitted model fixed. Seven selected, potentially spatially correlated piles give weak coverage; these intervals are not certification or a random-sample population guarantee. Do not treat neighboring depth rows as independent replicates.

Check exact/duplicate row IDs, depth ordering, group isolation, missing-data accounting, dimensional conversion, OLS against an independent augmented-design solution, known synthetic metrics, and deterministic reruns. Compare with saved notebook outputs to expose reproduction errors.

Interpretation: these are actual measured pile-driving outcomes resampled by the source to 0.5 m. The seven piles are excluded from coefficient fitting, but the notebook inspected the whole dataset before the split and used it in feature exploration. CB was already evaluated in the notebook. They are not untouched model-selection holdouts, newly collected measurements or independent-site validation. Energy is recorded during driving; this is conditional prediction with supplied operating information, not a fully preinstallation forecast or a causal energy experiment.

Publish code, aggregate results, plots, source hashes and limitations to Streams and Rocks. Keep the competition CSV local and point readers to authorized Kaggle access. No competition submission. Physical pile measurements do not validate the separate community model.
