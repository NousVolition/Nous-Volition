# Reversal symmetry, attraction, and fluid decay

This sixth batch uses the three supplied images as test specifications. It adds 22 unit tests, two original figures, seven linear reference cases, and independent checks of 36 previously saved channel results. It adds no SIMS runs. The images themselves are not repository assets.

Run `python -m unittest -v test_bridge_checks` and `python bridge_checks.py --check` from this folder. The latter compares saved results with tight numerical tolerances (relative 1e-9, absolute 2e-12) to allow platform roundoff. Run `python bridge_checks.py` to regenerate the data and `python build_report.py` to regenerate the complete report.

## The reversible textbook example

The crop starts after the original equation. Its nullclines, Jacobian, and stated equilibria determine the implemented field:

```text
x′ = −2 cos x − cos y
y′ = −cos x − 2 cos y
R(x,y) = (−x,−y)
```

The reversal condition is f(Rz)=−R f(z). Here R=−I and cosine is even, so the condition is exact. Thus if z(t) is a solution, −z(−t) is also a solution. Merely negating a forward trajectory without reversing its time would reverse its arrows and would not preserve the forward motion.

The equilibrium equations imply cos x=cos y=0. There are four equilibria in the cell (−π,π)², repeated every 2π in both coordinates; there are infinitely many in the full plane.

| Point | Eigenvalues | Classification |
| --- | --- | --- |
| (−π/2,−π/2) | −3, −1 | Attracting node |
| (π/2,π/2) | 1, 3 | Repelling node |
| (−π/2,π/2) | −√3, √3 | Saddle |
| (π/2,−π/2) | −√3, √3 | Saddle |

An additional analytic check connects this example with the earlier gradient-system tests. Put V=sin x+sin y and M=[[2,1],[1,2]]. Then f=−M∇V. M has positive eigenvalues 1 and 3, and

```text
V′ = −2(cos²x + cos x cos y + cos²y)
   = −(cos x + cos y)² − cos²x − cos²y.
```

This is strictly negative away from the equilibria. A nonconstant periodic orbit would return to the same V after V had strictly decreased, a contradiction. This is a gradient flow with a constant positive mobility matrix; it is not generally a Euclidean gradient field, since the cross derivatives sin x and sin y need not match. The attracting equilibrium and nonzero divergence show why the reversal symmetry does not imply conservative dynamics. Local area contracts at rate −4 at the sink and expands at rate 4 at its reversed partner.

On the invariant diagonal x=y=s, s′=−3 cos s. For an initial value strictly between −π/2 and π/2:

```text
s(t) = 2 arctan[tan(π/4+s(0)/2) exp(−3t)] − π/2.
```

At s(0)=0.3, the maximum RK4 errors over t∈[0,2] are approximately 7.32e-7, 4.47e-8, 2.76e-9, and 1.72e-10 for steps 0.04, 0.02, 0.01, and 0.005. The factor of about 16 on step halving checks fourth-order convergence. Three additional initial states test trajectory reversal over one time unit and step refinement. Three perturbations of the sink test attraction and monotonic decrease of V over eight time units. These finite checks supplement the exact identities and local eigenvalue argument.

## Linear reference systems and a transient-growth control

The matrices behind the supplied linear-phase-portrait report were found in its saved `data/textbook_checks.json`. Seven matrices are included in [the reference extract](bridge_references.json), including the six displayed cases and the neutral boundary b=1. Source SHA-256 hashes and local source paths relative to the shared Codex directory are recorded there. These are existing mathematical reference cases, not newly fitted gas trajectories.

For a real 2×2 matrix A, eigenvalues have sum tr(A) and product det(A). Negative determinant gives a saddle. Positive determinant with negative trace gives asymptotic stability; a negative discriminant gives a complex pair. At zero trace with positive determinant the exact linear system has a center. A zero eigenvalue requires examination of the neutral direction. The implementation uses scale-relative tolerances near algebraic boundaries; numerically near-degenerate cases should not be treated as exact parameter proofs.

The exact matrix exponential is evaluated using Cayley–Hamilton, including the repeated-eigenvalue limit. Tests compare it with rotations, exponential mode solutions, a Jordan block, and independently integrated trajectories. Positive rescaling of time and invertible changes of coordinates preserve the tested classifications.

For reciprocal equal coupling A=[[a,b],[b,a]], the eigenvectors (1,1) and (1,−1) have real eigenvalues a+b and a−b. For a=−1, increasing b through 1 changes a stable node into a line of equilibria and then a saddle. It cannot create a spiral in this model.

Negative eigenvalues do not require every displacement norm to decrease at every instant. The selected control A=[[-1,10],[0,−2]], z(0)=(0,1), has the exact solution

```text
x(t)=10(exp(−t)−exp(−2t)),  y(t)=exp(−2t).
```

Its distance from zero rises above 2.5 before decaying to zero. This is temporary amplification at an asymptotically stable node, not an unstable eigenvalue. Its size depends on the chosen coordinates and norm. Separately, x′=−y+σxr², y′=x+σyr² for σ=−1,0,1 has the same imaginary linearized eigenvalues but inward, closed, and outward nonlinear paths. Their radial solution r(t)=r(0)/√[1−2σr(0)²t] supplies an independent test on a finite interval before any blow-up.

## Independent checks using the water report's data

The screenshot comes from the separate [quantum-water pilot](https://github.com/NousVolition/My-Sources-Project-ALL/tree/main/reports/quantum-water-pilot). The small reference extract records material properties at 10, 25, and 40 °C and selected columns of all 36 channel cases: four property combinations × three temperatures × three pressure gradients. It records hashes of the complete original source files. The source solver and its screenshots are not copied, and those prior runs are not counted again as new runs here.

The source uses IAPWS density and dynamic-viscosity correlations at 0.101325 MPa, through its recorded iapws 1.5.5 dependency. These are measurement-based material inputs. The primary viscosity formulations are [ordinary water, IAPWS R12-08](https://iapws.org/technical-guidance/release/viscosity) and [heavy water, IAPWS R17-20](https://www.iapws.org/relguide/D2Ovisc.html). This batch reuses the saved numerical property values; it does not independently reimplement those correlations or produce molecular transport predictions.

For full channel gap H, pressure-gradient magnitude G, no-slip walls, and fluid initially at rest:

```text
ρ ∂u/∂t = G + μ ∂²u/∂y²
u(0,t)=u(H,t)=0
steady mean speed = G H²/(12μ)
slowest decay time τ = ρ H²/(π² μ)
initial interior acceleration = G/ρ
```

An odd-sine Fourier series supplies the exact startup profile and its integrated mean. The saved steady speeds, decay times, and analytic perturbation amplitudes agree with independently evaluated formulas to floating-point accuracy. The Fourier startup mean also matches the saved finite-difference mean at one second within the 1e-6 relative acceptance threshold. All 36 comparisons, including their residuals, are retained in [bridge_results.json](bridge_results.json).

At 25 °C the saved viscosities give a D₂O/H₂O steady-speed ratio about 0.8145: an 18.55% decrease under the same G and H. Changing density alone leaves the steady speed unchanged and increases the decay time. Changing viscosity alone reduces both steady speed and decay time. Combining both properties gives a decay-time ratio about 0.9022. These time scales describe the restricted streamwise channel model, not arbitrary three-dimensional disturbances.

A new independent numerical implementation evolves the discrete sine modes of the centered second-difference operator with Crank–Nicolson time stepping. It uses 32, 64, and 128 across-gap intervals, dt=0.00025 s, and final time 0.1 s. Comparison with the continuous Fourier solution checks spatial convergence. A separate fixed-grid comparison to exact discrete-mode evolution checks second-order time convergence. Boundary conditions, the channel PDE, pressure-gradient linearity, zero pressure, and density/viscosity controls are also tested.

These checks verify formulas and numerical implementation. They do not supply an independent experimental comparison of matched H₂O and D₂O velocity fields. They do not rerun the source's molecular calculations or three-dimensional vortices, convert calibration agreement into held-out validation, or resolve the Navier–Stokes existence and smoothness problem.
