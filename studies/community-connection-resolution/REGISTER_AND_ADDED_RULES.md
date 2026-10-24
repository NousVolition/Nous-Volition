# Equation register and every added rule in this work

Accounting checkpoint: 24 October 2026, immediately after the first study-1 sequence analysis. This document describes the code actually present at this checkpoint. A planned run is not an executed run. The source is the ten-row [equation register](../community-chain-audit/equation_register.csv). Row numbers below count data rows, excluding the header; these numbers are locators added here, not original corpus equation numbers.

**The new `analyze.py` executes no registered field equation.** Its permutation tests describe real response order and session similarity. The existing `audited_field.py` plus `legacy_field.py` implement five register rows, with numerical approximations and additional choices below. A complete empirical Smoke/Clay/moving-idea model has not been implemented or validated.

## Register rows

| Row | Register source and relation | Existing field solver | New real-data analysis at this checkpoint |
|---|---|---|---|
| 1 | P22; P603–605: Sens and Sin, preserving intended meaning while changing expression | No numerical implementation. Conceptual distinction only. | No intent observation function or meaning-equivalence test. |
| 2 | P72–97: architecture a, b, c, d and rY=V[:,1]−3 | No evolution or feedback law for these nodes; not coupled into PDE. | Not computed or measured. |
| 3 | P104; P615: within-context equality W(i,alpha;c)=W(j,alpha;c) | Not part of this solver. | No moderation/decision observations tested here. |
| 4 | P105–107; P616: maximize U on A intersect Omega with exact margin m=epsilon | No optimizer, action space or boundary metric implemented here. The `utility` input is supplied from outside; this row does not calculate it. | Valence is not calculated utility. No margin optimization executed. |
| 5 | P229–230: momentum and div(u)=0 | Implemented in `terms`, Fourier pressure projection and `step`; existing numerical fixtures executed. | Not invoked by `analyze.py`; new measurement-driven PDE runs only proposed. |
| 6 | P261–264: sharp, signed tanh and one-sided exponential responses | All three coded and previously exercised separately. The signed negative tanh tail is retained. | Not invoked. |
| 7 | P263–264: raw, regularized and calibrated gradient excess | All three coded in `excess_gradient`. Previous coupled runs use raw; optional cutoff identities have unit tests. All options are not interchangeable or all jointly exercised. | Not invoked. |
| 8 | P498–506: reciprocal scalar transform and SR invariant | Not part of field evolution. Scalar S here is not automatically the field S(x,t). | Not invoked. |
| 9 | P517–532: advection–diffusion, localized source, A integral and J=kappa A | Implemented using explicit observation-start A and piecewise-constant U. Existing numerical fixtures executed. | No measured A, U, S or u identified. Nonzero valence is counted, not silently integrated as observed utility. |
| 10 | P545–557: T=mu0(grad u+grad u transpose) | Computed as a stress diagnostic. It is not separately used to update momentum. | Not invoked. |

For row 10, the existing audit deliberately sets mu0=.07 while rho*nu=.02 to test that the two coefficients are not silently equated. If T is to be interpreted as the same viscous stress that supplies momentum diffusion, the extra constitutive identification nu=mu0/rho is needed. Without that identification, the code computes the registered diagnostic, but does not establish that particular stress-to-momentum interpretation.

## Added model assembly and numerical rules

These are not supplied as required choices by the register. Some are defensible implementation choices; others are unvalidated interpretive hypotheses. Listing them does not turn them into evidence.

| ID | Added rule or choice | Actual status and consequence |
|---|---|---|
| N01 | Identify the transport S/u with the momentum S/u across separate corpus sections. | Proposed in Miro frame 13 as a dashed coupling; implemented in the solver. It is a model assembly choice, not an empirically established link. |
| N02 | Periodic two-dimensional unit square, uniform grid, unit area. | Implemented. These are mathematical coordinates, not measured mental locations; no three-dimensional generality is claimed. Mean S equals integral S only because the area is one. |
| N03 | Constant coefficients and fixed source location x0=(.5,.5). Default forcing direction e_k=(1,0). | Implemented. No observed role/source location or direction was calibrated. |
| N04 | Specific kernel K proportional to exp{[cos(2pi(x−.5))+cos(2pi(y−.5))−2]/(2pi h)^2}, normalized by its grid mean. | Implemented. The register specifies a normalized localized kernel, not this functional shape. The Fourier representation then truncates this kernel. |
| N05 | State represented by two velocity components and one signed scalar field; pressure reconstructed with mean zero. | Implemented. Pressure's zero mean is a gauge choice. No independent Smoke or Clay state is present. |
| N06 | Fourier spatial differentiation and Galerkin truncation, retaining only modes with 3|m_x|<n and 3|m_y|<n. | Implemented to control aliasing. This changes the finite numerical representation, not the written continuum equations. |
| N07 | Helmholtz projection of velocity right-hand side and post-step projection to remove roundoff divergence. Preserve velocity zero mode. | Implemented incompressibility treatment. |
| N08 | Classical fourth-order Runge–Kutta time integration. U is constant on each supplied interval; A advances at every intermediate stage. | Implemented. Piecewise-constant input is an interpolation assumption, not a corpus requirement. |
| N09 | Time-step cap .45/[max(nu,D)*max(1,max retained k²)]. Steps=ceil(duration/min(requested_dt,cap)); actual_dt=duration/steps. | Implemented numerical choice. Requested halving is not necessarily actual halving; actual steps must be checked. This diffusion cap is not a general proof of nonlinear stability. |
| N10 | Initial u=v[sin(2pi x)cos(2pi y),−cos(2pi x)sin(2pi y)]; S=M0+b cos(2pi x)cos(2pi y). | Implemented initializer. Shape, texture b and speed v are synthetic assumptions, not measured person states. |
| N11 | Default numerical coefficients: n=24, nu=.02, D=.01, rho=1, sigma=.1, Gamma=.05, epsilon=.1, h=.12, gamma=kappa=1, Ubaseline=0, raw gradient, delta=.01. Default texture=.04, speed=.1 and total S=0. | Code defaults; actual runners override some. mu0 has no accepted implicit default in the audited wrapper. None is a measured psychological constant. |
| N12 | Explicit person ID, event reference, initial-history basis, Astart, start time and requested step required. Role must be Smoke/Clay/both/unattributed. | Added provenance contract. Role membership changes metadata only; swapping Smoke/Clay leaves equations unchanged. |
| N13 | Refuse cross-person joins, interval gaps/overlaps, missing/nonfinite U or time and nonpositive duration/step. Contiguity tolerance 1e−12. | Added input policy. Missing history is not set to zero. The policy rejects unknown intervals; it does not reconstruct their history. |
| N14 | Even integer grid n>=12; finite coefficients; nu>0, D>=0, rho>0, sigma>=0, Gamma>=0, h>0, mu0>0, epsilon>0, delta>0; two-component finite direction with approximately unit norm. | Implemented parameter-domain restrictions. Unit norm uses NumPy `isclose` defaults (rtol=1e−5, atol=1e−8), not exact symbolic equality. Gamma here means threshold; gamma input-gain remains finite without a positivity guard. |
| N15 | Initial spectral shape (3,n,n), resolved modes, real physical field and divergence-free velocity checked to 1e−10. | Added finite precision acceptance policy. Finite output is checked during evolution. |
| N16 | Mass, pressure/stress/velocity RMS, kinetic energy, force work, viscous dissipation and divergence are diagnostics. Mass uses the exact interval integral kappa[Astart dt + gamma DeltaU dt²/2]. | Derived diagnostic consequences, not independent empirical measurements. Energy is .5 mean|u|²; work=mean(u·f), viscous loss=nu mean|grad u|². |
| N17 | Grid comparison uses Fourier coefficients normalized by n², retaining common modes; RMS discrepancy is sqrt(sum|difference|²). | Existing audit comparison rule; does not itself measure unresolved high-frequency error. |
| N18 | Actual refinement requires same observation times and strictly smaller actual steps with more steps in each interval. | Added verification rule. |
| N19 | Existing synthetic audit: grids24,48,72; requested dt=.001 plus an actual-half-step run; all three activations; M0=.3,Astart=.2,mu0=.07; U=+1 then−1 over two .125 intervals; swapped role labels; S+10 offset. | Already executed earlier. These inputs are numerical fixtures, not real people. Test acceptance includes <1e−12 conservation/energy/divergence checks, analytic solution atol=1e−11 and decreasing successive grid discrepancy. |
| N20 | Separate Miro alternatives: A'=gamma DeltaU−lambda A and/or S relaxation −mu S, checked through [A,M,1] matrix exponentials with lambda or mu=1 and finite ±1 pulses. | Already checked as alternatives in the previous audit. These added equations are not inserted into the unchanged corpus solver and are not validated forgetting laws. |

The unwrapped legacy initializer/run can still create A=0 automatically. The audited `evolve` route requires an explicit A and overrides `run` to reject that shortcut. The old path is preserved for reproducibility, not endorsed for missing personal history.

## Added rules already executed on the new real data

All of these belong to `analyze.py`. They are not equation-register rows.

| ID | Rule | Scope |
|---|---|---|
| D01 | Select the pinned Lux archive, Study1 `trainid`117 rows and49 paired retest rows. Use exact author `testid`↔`subj_j_2` pairs; convert MATLAB one-based indices to Python zero-based. | All49 first sessions overlap training. The remaining20 source rows are unused by the inherited selection, not newly selected exclusions. Retest is not49 new people. |
| D02 | Treat axes as valence, self-relevance and temporal reference, with source ranges[-1,1],[0,1],[-1,1]. Reject out-of-range finite entries beyond1e−12. | Based on source scripts/methods, not inferred from corpus labels. No axis measures full intended meaning. |
| D03 | Scale first/third axes by(x+1)/2; leave self-relevance unchanged. | Added equal-range metric choice. It is not a demonstrated psychological metric. |
| D04 | Split each160-response sequence into4chains of40. Exclude the3between-chain links. | Follows the author's boundary treatment; no continuous sequence across seeds is assumed. |
| D05 | Keep adjacent pairs only when all3coordinates are finite. Leave missing positions fixed during shuffling; shuffle only complete vectors. | No zero imputation. There are no missing vectors in the executed selected data. |
| D06 | Squared Euclidean3-coordinate displacement, averaged over eligible adjacent pairs per person; then average equally across people. | Added distance and aggregation rules. These are descriptive statistics, not Navier–Stokes velocities. |
| D07 | Null: independently permute whole response vectors inside each person's chain999times, preserving cross-coordinate pairing. | Added exchangeability assumption. Rejecting it does not distinguish task-driven association from autobiographical memory or prove causation. |
| D08 | One-sided smaller-displacement test, p=(1+number null<=observed)/1000. | Added inferential rule; .001 is the minimum attainable p, not a zero probability. No familywise multiplicity adjustment is implemented. |
| D09 | Analytic shuffled expectation per chain=2m/(m−1) times summed population coordinate variances; combine by eligible pair counts. | Independently unit-tested against exhaustive permutations. Added analysis formula, not an empirical field equation. |
| D10 | Report shuffle expectation−ordered displacement. Person bootstrap:1999resamples, percentile95% interval. Seeds are261023/261024 for permutations and seed+10 for this bootstrap. | Added uncertainty method. Bootstrap count and percentile rule were specified in code before its first execution, but were not spelled out in the prose protocol. |
| D11 | For paired sessions use each person's3coordinate means; squared Euclidean distance between sessions. Shuffle second-session person labels999times. | Added observation summary and null. No within-gap trajectory inferred. `nanmean` is coordinate-wise here, unlike complete-vector treatment in D05; irrelevant to these complete selected records but a future-data policy difference. |
| D12 | Paired null expectation averages all first×second centroid distances. Bootstrap1999paired people, recomputing both matched distance and the null expectation; percentile95% interval. RNG seed261024, bootstrap follows permutation draws. | Added summary and resampling rules. A person-specific response style is an alternative explanation. |
| D13 | Count exact nonzero valence and people whose maximum valence exceeds their minimum; no epsilon threshold for either count. | Counts only. No substitution of valence for measured utility in executed field evolution. |
| D14 | Validate index uniqueness/range, equal paired lengths and disjoint second-session indices; retain unused-row list and source SHA256; output per-person metrics and JSON. | Added reproducibility/input checks. They do not validate constructs. |
| D15 | No predictive estimator, parameter fitting, questionnaire-derived utility, decay fitting or model-selection step. | Actual scope. Sequence statistics are not a simpler predictor substituted for the field, but they also are not a test of the field. |

## Added hypotheses and choices written into the new protocol but not executed as field tests

| ID | Added choice | Status |
|---|---|---|
| P01 | Candidate S=normalized occupancy density and DeltaU=recorded valence, with gamma*kappa>0 and closed boundaries. | My proposed **candidate to challenge**, absent from the register and not supplied by the user. Not an accepted observation model. Counts D13 are available; no full-field run on them has occurred. |
| P02 | Derive M'=kappa A and M''=kappa gamma DeltaU, then compare with constant normalized mass1. | Mathematically derived under N01/N02 and normalized kernel. A contradiction rejects P01's joint mapping, not the corpus. It would be wrong to portray testing this self-proposed mapping as validating the user's requested connection. |
| P03 | Alternative observation P=S/M, preserving hidden amplitude M. | Proposed readout, not measured. Quotient differentiation adds (kappa A/M)(K−P) to P transport for M nonzero; normalization without that term changes the model. Signed S does not automatically make P a probability. |
| P04 | Drive hypothetical simulations from first training person's first40valence values, held constant on intervals of .01 arbitrary time units. | Planned selection/interpolation/time scale; not measured time, felt time or utility. |
| P05 | Initial M1, texture.04,speed.1 and Astart−.2/0/+.2; grids24/48; requested steps.002/.001; all3activations; rho1,sigma.1,nu.02,D.01,Gamma.05,epsilon.1,h.12,gamma=kappa1,mu0.02,e_k=(1,0). | Planned sensitivity settings, not estimated person-specific states. Here mu0=rho*nu is a chosen equality, not mandatory register content. |
| P06 | Use Study2 only after executable specification/first-stage results fixed; apply same statistics/seeds. | Not downloaded or tested at this checkpoint. `analyze.py` contains an unexecuted Study2 path expecting `dat_study2` and four equal chains; metadata must be checked before use. |
| P07 | Select all5episodes11.1–11.5 from one DES day; distinguish participant/interviewer; no keywords as semantic evidence or population prevalence claim. | Planned purposive qualitative review. Not completed at this checkpoint;11.3 was previously reviewed. |
| P08 | Report separate coordinate results as well as joint displacement. | Promised by protocol but **not implemented or produced** in the present script. This is a remaining deliverable, not a completed check. |

## Interpretive connections and remaining absence

- Smoke as inward putting-forward and Clay as inward receiving/reconsidering are the user's definitions. Relating them to architecture a/b is an application hypothesis; original b also mentions external input. No role-specific update law or observation operator follows automatically.
- Water as perceived balance, Fog as variable clarity, Wind as experienced time, and D2O as small compositional change with potentially large consequences are user concepts. No numeric classification threshold has been added in this new analysis.
- Mist's earlier unspoken-agreement interpretation was assistant-added and remains provisional. Peroxide's inward measurement definition is unresolved. Neither is assigned from the new ratings.
- Valence≠perceived balance, self-relevance≠Clay, temporal reference≠felt distance, remembered background≠verified event or measured accumulated utility. These are distinctions preserving the user's meanings, not claims those concepts are unrelated.
- The person's initial S/u/A and biography remain unmeasured. Retest similarity and recorded response order constrain observations but do not identify those hidden states.

No actual full-model fit, held-out full-model forecast or smoke/clay/form classification has been performed in this new batch. Six analysis unit tests passed; the study1 statistics ran. The earlier solver's passing numerical tests belong to its explicitly stated fixtures. Neither fact closes the remaining empirical connections.

Code inspected: `analyze.py`, `test_analysis.py`, the new `PROTOCOL.md`, and the preceding audit's `equation_register.csv`, `audited_field.py`, `legacy_field.py`, `run_checks.py`, `test_audit.py`. This is a complete inventory of substantive model/observation/statistical/verification choices in those files at this checkpoint, not a claim to inventory every historical study in the repository.
