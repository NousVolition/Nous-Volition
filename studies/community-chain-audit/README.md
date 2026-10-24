# Source-chain audit: exact corpus, Miro, implementation and observations

Streams and Rocks · 23 October 2026

**Yes: earlier shortcuts and unsupported bridges existed. They must not become the foundation of a claimed full empirical two-in-one result.** This audit repairs the documentation and future numerical entry point, preserves the historical evidence, and identifies what still has no valid real-data test. It does not replace the full equations with a simpler predictor.

[Readable report](report.html) · [33 connections examined](CONNECTION_AUDIT.md) · [Connection ledger](connection_ledger.csv) · [Corrections and remaining tests](CORRECTIONS.md) · [Equation register](equation_register.csv) · [Exact corpus passages](exact_corpus_passages.json) · [Study chain](study_chain.csv) · [Source coverage](source_versions.json) · [Requested tool checks](APP_SOURCE_CHECK.md)

**The audit must not create false closure.** Implementing the full coupled field subsystem does not supply the still-missing connection to measured Smoke, Clay, moving-idea forms and individual history. A scalar accumulated input is not a person's whole history; role labels are not separate role dynamics. [Open logical connections](LOGICAL_BOUNDARIES.md) identifies exactly where one result does not imply the next. Applying AI Psychiatry reviews the assistant's work process; it is not independent scientific validation.

## What was checked

The corrected DOCX was read in full: 624 nonempty body paragraphs plus its footer; the fresh extraction matches the prior source. All 37 pages of the later PDF board export were visually inspected. Eight owned Miro boards were inventoried: 1,747 indexed items, with 1,745 represented in retrieved SVG and eight interactive prototype HTML sources read separately. Text, tables, diagrams and source relationships were inspected, including material previously skipped as foreign objects. [Board-level coverage](board_coverage.csv) and [item-level coverage](miro_item_coverage.csv) record the limits: two AI connectors did not expose their content, 47 template image pixels were not separately transcribed, and two source image previews were too small for independent transcription. Matching tables/charts were read as structured content. External works mentioned on boards are mapped sources, not automatically re-audited studies.

The local study chain contains 1,042 baseline artifacts and 183 Python programs; all parsed. The audit records 139 local Python import edges and 26 study/package entries. This is a whole-chain dependency, source, claim and available-test audit, with detailed term-by-term review of the community field and observation bridges. It is not a fresh line-by-line certification of every physical solver or every external linked project.

## Repairs that change how results must be used

- Restore the corpus's transmit/I, receive/Self, buffer and perimeter roles. Smoke and Clay have architectural anchors; their dynamic observation link is still missing. The original external-input description and the later within-person interpretation stay distinct.
- Quarantine DeliData and OneCommon scores as conditional on analyst mappings and observation-start history resets. Unknown earlier history is not zero. The original scores remain visible and were independently recomputed from saved records.
- Mark the DES spatial centers, Gaussian readouts and support zero as analyst choices. Five episodes from one person constrain a proposed mapping; they do not validate future inward trajectories.
- Preserve the actual time-step correction and reject duplicated capped steps as new refinement evidence. Keep original failed attempts and amendments.
- Distinguish the author's moving-idea forms from added operational interpretations, especially Mist as unspoken agreement. Preserve Water as perceived balance and D2O as a specified small change with a potentially large consequence.
- Correct the Miro prototype's two false long-time claims for proposed forgetting laws. Do not insert those alternative laws into the exact corpus.
- Require explicit stress coefficient, finite states/inputs, real-valued fields and observation-start provenance in the new complete PDE runner. Earlier mu0=rho*nu was already disclosed as a closure; it is now configurable rather than silently assumed by future use.

Prominent notices are added to all 13 community study entry points, and report generators preserve those notices. Model definitions, inverse translation, Miro reconciliation and form provenance are corrected in place. Earlier numerical files and the pinned legacy solver retain their historical role; the complete new runner is [audited_field.py](audited_field.py).

## Equations retained

```text
u_t + (u·grad)u = -grad(p) + nu Lap(u) - (sigma/rho) a(q) e_k
div(u) = 0; q = |grad(S)| - Gamma
S_t + u·grad(S) = D_diff Lap(S) + K_h kappa A
A(t) = A(t0) + integral_t0^t gamma [U(s)-Ubaseline] ds
T = mu0 [grad(u) + grad(u)^T]
```

The original A(0)=0 remains at the declared integral origin. The observation-start decomposition is the same equation, not a replacement. Sharp, signed tanh and one-sided smooth exact-off laws remain separate. Optional uncalibrated and calibrated gradient regularizations are exposed as different corpus alternatives. W equality, exact-margin utility optimization and reciprocal scalar rescaling are retained in the equation register; inventing a dynamic coupling for them would change the supplied theory.

**The shared-field connection is an assumption, not an automatic consequence of exact transcription.** The momentum and scalar/source laws appear in separate corpus sections. Identifying their S and u on one domain is the declared coupling used here, also proposed on the Miro memory diagram. “Full coupled field” means this specified subsystem, not an empirically established coupling of every corpus relation. The [connection audit](CONNECTION_AUDIT.md) traces this and 32 other links, separating author definitions, analogies, mathematical consequences, added hypotheses and unsupported empirical transfers.

The numerical domain is an explicitly chosen periodic unit square. The method is filtered pseudospectral spatial differentiation and RK4 time integration; nonlinear activation is approximated, not evaluated as an exact Galerkin integral. Constant coefficients, kernel location/width and abstract units are declared numerical fixtures. No physical viscosity, psychological geometry or new Navier–Stokes law is inferred.

## Completed numerical and real-data checks

**443 existing unit tests passed across 26 discovered suites.** Twenty saved-result/package verifiers were run; 17 passed initially. Two failures were caused by local mirror paths, and one by the raw-data-directory default. Correct target resolution and the existing source directory resolve all three; original failure logs are retained. Passing these checks does not erase the scientific limitations above.

**17 new tests and 18 full coupled PDE runs completed.** All three response laws show decreasing grid differences from 24→48→72. Actual half-step comparisons use smaller effective dt. The maximum scalar-total accounting error is 1.67e-16; maximum divergence RMS is 1.74e-17. Legacy and new raw-gradient PDE right-hand sides agree exactly in the tested fixtures. Changing mu0 changes stress independently of momentum; this makes the chosen closure visible.

| Law | Grid 24→48 difference | Grid 48→72 difference | Actual half-step difference |
|---|---:|---:|---:|
| sharp | 3.01834e-05 | 2.18261e-06 | 2.96446e-11 |
| tanh | 3.06464e-05 | 2.22295e-06 | 1.35363e-13 |
| smooth_off | 2.72034e-05 | 1.48242e-06 | 3.67082e-13 |

These differences are norms over the represented coarse Fourier modes; refinement alone does not bound every unresolved high-frequency component. Role relabeling alone produces no dynamical change, as expected from the equations. A constant S-offset leaves gradients and movement unchanged, exposing why an uncalibrated positive-support zero cannot establish psychological support.

The latest measured-inner-experience workbook analysis was rerun into a separate directory. All four result files reproduced byte-for-byte. The 31 paired observations retain differences of +2.345161 dialogic-score units and +2.032258 evaluative-score units. The 3,108 valid fluency responses and 2,375 adjacent valid pairs also reproduce. These outputs do not consume older field predictions. Their construct limitations remain: coder-category identity is not identity of intended meaning, and the source lacks the jointly identified inward observation model.

The earlier conditional field-versus-last-answer MSE remains 0.140318 versus 0.104279. It is a negative result for that measurement/initialization hypothesis, not a universal refutation or validation of the corpus. No coefficients were retuned on its evaluation data.

## What still needs testing

The full empirical two-in-one has not been validated. The remaining work is an identified observation model connecting real inward putting-forward, receiving, the moving idea's forms and each person's history to predicted quantities. Partial observations can be sufficient if latent states and parameters are identifiable with uncertainty; every field value need not be directly observed. Calibration, prehistory, measurement error, intended-meaning review and untouched future outcomes must be specified. See [measurement requirements](MEASUREMENT_REQUIREMENTS.md).

Physical/soil measurements, external conversations, hypothetical allocation policies and philosophical images can inform questions and tests. They do not automatically measure inward Smoke, Clay or a moving idea. Strong language is retained when the account supports it; missing evidence is stated precisely rather than weakening the author's terms.

## Reproduce

```text
python -m pip install -r requirements.txt
python verify.py
python -m unittest test_audit.py -v
python run_checks.py
```

Run in this directory. Verify original release hashes before regenerating results; the remaining commands rerun the new exact-equation checks and do not fit a human predictor. `python build_report.py` renders this README without changing its claims. Historical suite commands and logs are in [baseline_test_runs.json](baseline_test_runs.json), [saved_check_attempts.json](saved_check_attempts.json), and [verification_resolution.json](verification_resolution.json). Raw source data are not republished. [Measurement rerun](measurement_rerun.json), [new diagnostics](results.json), [code dependencies](code_dependencies.csv), and [baseline file hashes](baseline_file_inventory.json) retain the audit trail.

Development note: the first new continuation test compared different integration grids because decimal interval rounding changed `ceil` step counts. It was corrected to binary-exact intervals with an explicit equal-step-count assertion; the tolerance was not relaxed. Existing full-field code remains preserved as [legacy_field.py](legacy_field.py), SHA256 `00b50a93ae413d46109327ccf0c08e8e07d00028313eaa0da87d765e58705f35`.

## Publication check follow-up

All five focused audit/community CI jobs passed on the first publication. The broader repository job exposed an exact-float comparison failure in the existing Hug movement study. A diagnostic-only commit preserved the failing comparison and captured a phase difference of 7.07e-17 cycles. The phase-only verifier now uses an explicit 32-float64-epsilon absolute allowance, rejects non-finite values and preserves exact outcome flags; five regression checks exercise accepted roundoff and rejected larger changes. Its 25 unit tests and 96-path saved verification pass locally. No model equation, trajectory, protocol or scientific effect threshold was changed. See the [failure evidence, diagnostic limits and correction](https://github.com/NousVolition/Nous-Volition/blob/main/studies/hug-movement-sweep/VERIFICATION_NOTE.md). The audit does not hide this failed publication check or label it a failed empirical theory.
