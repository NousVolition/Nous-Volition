# Switching, synchronization, memory, and stopping

The supplied pages are used as model specifications and prompts for executable controls. This fifth batch adds 48 isolated nine-state trajectories, 64 starting states for a ring of 16 units, 12 quenches, and separate local-memory and inference diagnostics. The previous 12,800 SIMS coordination runs remain unchanged. A nine-state activity vector describes a dynamical unit; its nine components are not nine SIMS seats.

## Models and definitions

`heteroclinic.py` implements generalized Lotka–Volterra activity dynamics:

```text
x_i' = x_i (1 - sum_j B_ij x_j)
B_ii = gamma
```

The off-diagonal matrix follows equations 1–2 of [Voit and Meyer-Ortmanns (2018)](https://arxiv.org/abs/1806.11039). Label a component by `(g,k)`, with group and within-group index each in `{0,1,2}`. For source `j` and destination `i`, B_ij is e for the forward within-group cycle, c for its reverse, f for the forward between-group cycle at fixed k, d for its reverse, and r for the remaining pairs. Thus row i is the effect on component i; arrows are not reversed to follow the inhibiting component.

An axis equilibrium has x_i=1/gamma and all other components zero. Its eigenvalues are -1 radially and `1-B_ji/gamma` toward each other component j. In the nine-state baseline, gamma=1.05, c=d=2, e=0.2, f=0.3, and r=1.25. Each saddle has two positive eigenvalues. The 18 intended directed connections form a strongly connected graph.

The final definition screenshot specifies stable and unstable sets through forward and backward limits. A genuine connection is a **nonconstant** orbit in the source's unstable set and the target's stable set. An equilibrium belongs to both its own stable and unstable sets, so the nonempty-intersection shorthand alone must not be used to invent a homoclinic orbit. Self-loops are excluded from our connection graph.

For each intended edge, its two-coordinate plane is invariant. Writing u for the source and v for the target gives `u'=u(1-gamma*u-beta*v)` and `v'=v(1-alpha*u-gamma*v)`, with `alpha<gamma<beta`. The source has a positive invasion direction; the target attracts within this plane. The two nullclines have no positive coexistence equilibrium, since their intersection coordinates have opposite signs. The Dulac weight 1/(uv) gives divergence `-gamma/v-gamma/u<0`, and trajectories are bounded by the logistic inequality for each component. These facts establish the intended positive-quadrant connection. Finite forward arrivals near its target are numerical checks of this construction, not a replacement for backward/forward limit definitions or a classification of every invariant set in nine dimensions.

## Isolated switching experiments

The three-state restriction uses gamma=1, c=2, e=0.2, initial state (0.8,0.12,0.03), and time horizon 600. The contracting/expanding eigenvalue ratio is 1/0.8=1.25. Its 16 completed dominance visits lengthen from 6.956855 to 104.947710 time units. Separate deterministic controls add a constant input of 10^-6 or 10^-4 to every equation. Their last three mean dwell times are approximately 16.579859 and 10.585004. Adding input destroys boundary invariance; it does not simulate noise or preserve an exact heteroclinic connection.

For nine states, compare `(e,f)=(0.2,0.3),(0.25,0.25),(0.3,0.2)` with all other baseline parameters fixed. Use 16 matched initial states, Python random seeds 20261011–20261026, independent uniform components in [0.01,0.1], duration 400, and step 0.05. Every setting retains the same 18 intended connections. Mean within-group shares among classified transitions are 0.838322, 0.518667, and 0.103628. The first-minus-last paired difference is 0.734694, approximate normal 95% interval [0.626047,0.843342], over 16 independent starts. This measures initial-condition sampling in these settings, not a universal network probability.

A visit begins when the largest component exceeds half the axis-equilibrium activity. Crossing times are linearly interpolated. Initial and terminal incomplete intervals are censored from completed-dwell summaries. Consecutive repeated labels are merged for transition counts. The three settings have 24, 18, and 21 threshold-detected transitions outside the intended two edge families, respectively. They remain recorded as unclassified rather than being silently forced onto edges; finite-threshold observations can skip an intermediate visit.

The isolated solver integrates logarithmic activity with RK4 and imposes no numerical floor. Zero initial components are rejected by that solver; invariant-plane tests use the original equations to preserve exact zeros. Underflow is checked. Halving the step preserves the three-state and two selected nine-state sequences; maximum activity differences are 5.22e-9, 2.40e-7, and 9.22e-8.

## Pacemaker and 15 driven units

`pacemaker.py` implements equation 1 and section 4.3 of [Thakur and Meyer-Ortmanns (2022)](https://arxiv.org/html/2112.12642v2#S4.SS3), without noise:

```text
x_(k,i)' = local_GLV_(k,i) + sum_l K_(k,l) (x_(l,i) - x_(k,i))
K_(k,k-1) = 1.5 for k=2,...,16
K_(1,16) = 0.01
gamma_1 = 1.05; gamma_2,...,gamma_16 = 1.47
```

The source underlying the review's Figure 5 closes the directed chain into a ring with a weak return connection. All activity interactions use the nine-state baseline. NumPy `default_rng` seeds 20261012–20261075 generate 64 independent starts with all 144 components uniform in [0.01,0.1]. Integrate to 2,000 with RK4 step 0.05; record at unit time intervals and analyze t=1,000–2,000. Stage positivity is checked; values are never clipped.

To avoid interpreting tiny numerical differences at coexistence as dominant states, require largest activity share >=0.25 and a gap from the runner-up >=0.01. Otherwise the label is zero (gray). Classify a run by whether more than half its classified pacemaker transitions are within-group. We obtain 57 within-group and 7 between-group runs, with none tied or unresolved. This is a finite-time classification under our chosen initial distribution, not a basin-volume estimate for arbitrary starts or an infinite-time attractor proof.

The displayed examples select the largest and smallest within-group fractions, seeds 20261031 and 20261024. Last-unit same-time matches to the pacemaker are 95.6871% and 96.5863%, conditioned on a clear pacemaker label. Both have preserved pacemaker sequences at step 0.025. Maximum activity differences are 1.27e-6 and 0.001017; last-unit agreement changes by 0 and 0.0971 percentage points. These are timing measures, not claims of identical amplitudes. Lag-adjusted scores are descriptive searches over 0–50 sampled time units and are stored separately.

Two matched controls use the first displayed initial state. Removing every spatial coupling leaves the driven units without qualified dominant activity in the measurement window. Removing only the weak return link still gives strong finite-time synchronization. Thus this test does not establish that ring closure is necessary for entrainment.

## Local memory control

`memory_inference.py` tests an explicit local linear saddle map motivated by the lift-off mechanism in [Ashwin and Postlethwaite, section 4.3](https://arxiv.org/html/1302.0984v2#S4.SS3). For `x'=lambda*x`, `y'=-c*y`, entering at x=epsilon and leaving at x=1 yields `T=log(1/epsilon)/lambda` and `y_out=y_in*epsilon^(c/lambda)`. This formula is checked against numerical integration.

The declared diagnostic represents two histories by y_in=+1 or -1. At each successive saddle, x resets to epsilon; the y offsets acquire the product of the contraction factors. A standard Gaussian perturbation times epsilon is added **only at the final binary readout**. For total exponent nu, the conditional branch-probability gap is exactly `erf(epsilon^(nu-1)/sqrt(2))`. The Monte Carlo check uses 4,096 Gaussian samples per history per case with common random numbers, seed 20261013, five epsilon values, and exponents 0.5, 1.5, 0.4+0.4, and 0.4+0.9. Resetting the history coordinate gives an exact zero-gap control.

This demonstrates retention relative to readout noise when nu<1 and erasure when nu>1, including erasure at a later saddle. It is not an integration of continuous stochastic forcing over an entire heteroclinic network. Positive saddle quantity is a local condition; global transport and subsequent contraction also matter. Conditional probabilities, rather than a visually recurring sequence, are the memory diagnostic.

## Recovering interactions from observed activity

The supplied teacher-learning paragraph motivates an identifiable baseline, distinct from the adaptive algorithm of [Voit and Meyer-Ortmanns (2019)](https://www.frontiersin.org/journals/applied-mathematics-and-statistics/articles/10.3389/fams.2019.00063/full). For our GLV model, `1-d(log(x_i))/dt=sum_j B_ij*x_j`. Estimate log derivatives by central differences and fit each matrix row by least squares. The true vector field is not fed to the regression.

Training uses six independent initial states, seeds 20261014–20261019, to t=40 at step 0.02. Select every tenth interior sample for regression. Test a new initial state, seed 20262014, to t=100. Compare clean measurements with independent Gaussian log-measurement noise of standard deviation 0.0001. Both designs have rank 9 and recover the intended transition-edge signs. Largest parameter errors are 9.68e-6 and 0.00617; held-out maximum activity errors are 1.84e-5 and 0.00812.

These results assume complete component observations, a known GLV functional form, and fixed growth rate 1. They do not demonstrate inference from only winning labels. A counterexample holds the system at uniform coexistence: the design has rank 1, and two distinct rate matrices produce the same observation. The delay-learning system mentioned in the review is not implemented in this batch.

## Quench and settling tests

`quench.py` tests the sudden-parameter-change idea from [Aravind and Meyer-Ortmanns (2023)](https://doi.org/10.1063/5.0166803) using the explicit baseline GLV matrix above. Take three states from the first isolated nine-state trajectory, at t=50,150,300. Change gamma from 1.05 to 1.47,1.55,1.8,2.5, retaining the other rates, and integrate each case for 4,000 time units. These are 12 selected deterministic quenches; they do not reproduce the paper's entire noise/coupling study.

The new uniform equilibrium is `x*=1/(gamma+c+e+d+f+4r)`. Its Jacobian is `-x*B`. All four settings have negative-real-part spectra and complex modes. Slow linear envelope times are derived from the largest real part; they are local asymptotic estimates, not the full nonlinear settling time.

Settling requires the largest componentwise relative error to stay <=5% through the remaining sampled horizon, including at least 100 units of confirmation. Results, by the three pre-quench states:

| New gamma | From t=50 | From t=150 | From t=300 |
|---|---:|---:|---:|
| 1.47 | 953 | 3,113 | Not confirmed by 4,000 |
| 1.55 | 217 | 638.5 | 1,019 |
| 1.8 | 86.5 | 200 | 371 |
| 2.5 | 34.5 | 82 | 180 |

Time is dimensionless. The state from t=300 has highly suppressed components that need time to recover. Four selected step-halving checks retain the same sampled settling times and have maximum activity differences below 4.7e-9. The application to disease in the source passage is a speculation in that paper; these calculations test mathematical relaxation only.

## Reproduce

Install the existing pinned requirements, then run from this directory:

```sh
python -m unittest -v
python heteroclinic.py --check
python pacemaker.py --check
python memory_inference.py --check
python quench.py --check
```

Remove `--check` to regenerate data, in the displayed order (quench initial states depend on saved heteroclinic data). NumPy is required for the coupled ensemble, inference, quenches, and their tests. The isolated heteroclinic calculations and earlier four batches use the standard library. `python heteroclinic_report.py` regenerates the three new scientific figures; `python build_report.py` rebuilds all fourteen figures and the combined report. Every screenshot remains a reference rather than an embedded asset.
