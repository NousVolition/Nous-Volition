# Exact field equations and within person measurements

Protocol fixed before computing aggregate dataset results and the new numerical experiments, 22 October 2026. This is an equation-fidelity and measurement-identification study. It does not fit a replacement predictor. No empirical full two-in-one fit is defined while the correspondence between corpus fields and inward roles remains unresolved.

## Scope

Run all coupled momentum, pressure, incompressibility, signed-field transport and accumulated-source equations in the supplied corrected corpus. Test implementation against analytic special cases, conservation identities, time and grid refinement, and a parameter invariance that concerns the entire coupled system. Numerical experiments use declared dimensionless inputs. They are not human observations.

Independently inspect all 118 published think-aloud transcript and embedding files at Lee-Memory-Cognition-Lab/thinkaloud_paper commit e8005a84122e208f1607064d897763d6cbddf25a. Verify source hashes, schema, grouping, temporal order, embedding alignment and measurement coverage. Report actual record counts, timestamp defects, annotation coverage and missing model measurements. Do not invent role labels, utility ratings, spatial coordinates or autobiographical history. Do not treat text embeddings as measured intent.

## Equations and numerical specification

Use the byte-identical solver from the earlier full corpus-field study, SHA256 00b50a93ae413d46109327ccf0c08e8e07d00028313eaa0da87d765e58705f35. Fourier Galerkin on a periodic unit square, two-thirds mode filter, RK4, divergence-free Helmholtz projection and pressure mean zero. This is a numerical approximation to the corpus PDE, not an exact analytic solution. Keep fixed-direction force, signed S, accumulated A starting at zero, J=kappa*A, no clipping and no forgetting term. Run sharp, original signed tanh, and smooth exact-off laws separately. The latter uses original gradient magnitude, not the corpus's separately optional regularized magnitude.

Base parameters: rho=1, nu=0.02, D=0.01, sigma=0.1, Gamma=0.05, epsilon=0.1, h=0.12, gamma=1, kappa=0.3, Ubaseline=0, e=(1,0). Stress uses mu0=rho*nu, an explicit equality between the corpus's constitutive and momentum viscosity in this experiment. Initial S=0.04*cos(2*pi*x)*cos(2*pi*y), initial Taylor-Green velocity amplitude 0.1, A=0. Input sequence U=(1,-0.5,0) on intervals of duration 0.2; final time 0.6. All values use arbitrary dimensionless experiment units. None is calibrated to a person's mind or a chemical substance.

For each response law run n=24,48,72 at max dt=0.002, plus n=24 at max dt=0.001. Use the inherited diffusion stability cap and report actual steps. Compare all Fourier modes including fine-only modes. Add no-force and no-source controls only as explicitly labeled ablations; they never replace the coupled model. Require finite states and report conservation and energy residuals. Do not claim convergence if successive differences do not decrease.

## Structural identification tests

1. With A(0)=0, replace gamma by c*gamma and kappa by kappa/c, c=4. Then A is multiplied by c but J, S, u and pressure are unchanged. Verify numerically in the full coupled system for all three response laws. Even perfect S and u observations cannot separately identify gamma and kappa without another scale constraint or measurement of A. A known convention for one parameter can remove this scale ambiguity without changing the equations.
2. Under the chosen closed/periodic boundary conditions and integral(K)=1, M'=kappa*A and M''=kappa*gamma*(U-Ubaseline). Compare runs with different nonzero force strengths and diffusion values. Equal global scalar means do not identify spatial force or transport. This is a consequence of the full equations, not a substituted scalar predictor.
3. After U returns to its baseline, accumulated A remains constant and S's total can continue changing. Check the analytic integral. It would be a different model to replace accumulated memory with exponential fading.

## Real measurements and limits

Count all transcript rows as sentence/clause records, group by the source thoughtID as the authors' notebook does, retain category 0 fillers rather than silently changing source groupings. Check nonmissing positive-duration intervals, start order, overlaps, one category per thought, sequential thought IDs, nonzero finite 768-dimensional embedding vectors and matching thought/embedding counts. Timestamp checks use 1e-8-second tolerance. Record anomalies without repairing them.

The 118 participants are not a fresh confirmatory holdout for this study: source summaries informed dataset selection, and this audit examines all records. No parameter tuning, outcome prediction, significance claim or full two-in-one validation is made. If a later observation model is specified, reserve participants and later times before choosing model parameters. A model may be tested through partial noisy observations if its observation equation and identifiability are established; every latent field need not be directly measured.

The recordings cover a short session, not a lifetime. Recorded elapsed seconds do not measure felt temporal distance. Observer-generated categories, embeddings and LLM emotion scores do not by themselves measure Sens, inward roles, perceived Water balance or personal utility. Archived external conversation and questionnaire predictors remain different studies.

## Reproducibility and release

Keep raw narratives, person attributes and embeddings in work/twoinone-field-raw outside the publication package. Publish source URLs, hashes, code, numeric per-file coverage counts, numerical experiment fields and aggregate results. No raw narrative quotations are needed. Preserve the original corpus DOCX and its hash; publish only the equation excerpts needed for the trace. Run unit tests and saved-result checks before publishing. Report the empirical fit as unavailable rather than giving it an invented score.
