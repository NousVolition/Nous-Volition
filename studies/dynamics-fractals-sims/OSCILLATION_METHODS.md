# Oscillations: equations, evidence, and scope

This third batch extends the supplied pages on limit cycles, gradient systems, Dulac's criterion, Poincaré–Bendixson, Sel’kov, Liénard systems, relaxation, averaging, and changes of stability. Plots are original computations. Parameters and time are dimensionless. The equations are independent mathematical experiments alongside the SIMS coordination study.

Run `python oscillations.py` to generate `oscillation_results.json`, or append `--check` to reproduce it without overwriting it. Run `python -m unittest -v` for the full test suite. `python build_report.py` rebuilds all figures and the report using the pinned plotting dependencies.

## Exact equations and chosen examples

| Topic | Implemented model | Provenance |
| --- | --- | --- |
| Stable unit cycle | r′=r(1−r²), θ′=1 | Standard realization of the supplied unit-circle example |
| Unstable unit cycle | r′=0.1r(r²−1), θ′=1 | Chosen illustration of the supplied classification |
| Half-stable unit cycle | r′=−r(1−r²)², θ′=1 | Chosen illustration, attracting from outside |
| Gradient example | x′=sin y, y′=x cos y | Supplied equations |
| First Dulac example | x′=x(2−x−y), y′=y(4x−x²−3) | Reconstructed by multiplying the displayed weighted components by xy |
| Second Dulac example | x′=y, y′=−x−y+x²+y² | Supplied equations |
| Sel’kov | x′=−x+ay+x²y, y′=b−ay−x²y | Supplied equations, a,b>0 |
| van der Pol | x″+μ(x²−1)x′+x=0 | Supplied equation |
| Duffing | x″+x+εx³=0 | Supplied unforced, undamped equation; ε=0.1 |
| Cubic velocity damping | x″+εx′³+x=0 | Cropped exercise continuation; x(0)=1, x′(0)=0, ε=2, t≤50, plus ε=0.1 comparison |
| Pendulum | x″+sin x=0 | Supplied undamped equation |
| Pumped swing | x″+(1+εγ+ε cos 2t) sin x=0 | Supplied nonautonomous equation |
| Planar pitchfork | x′=μx−x³, y′=−y | Chosen normal form; Figure 8.1.7 does not show its original equations |
| Supercritical Hopf | x′=(μ−r²)x−y, y′=x+(μ−r²)y | Chosen comparison, extending the unit-cycle example |

**Pending source:** Figure 7.3.3 / Example 7.3.1 shows a μ-dependent annulus and a μ=1 orbit, but its vector field is absent from the supplied crop. That specific example is not run. The chosen Hopf normal form is a separate, explicitly specified model and does not substitute for the missing equation.

## Why some trajectories repeat

For the radial examples, the sign of r′ on each side of r=1 gives stability directly. All have angular speed 1 and cycle period 2π. The stable model has exact radius

```text
r(t) = [1 + (r(0)^(-2) − 1) exp(−2t)]^(-1/2),  r(0)>0.
```

The origin remains a fixed point. The stable-cycle transverse multiplier is exp(−4π); the unstable example has multiplier exp(0.4π). The half-stable multiplier is 1, so its classification requires the nonlinear sign of r′. An outer unstable trajectory eventually diverges in finite time: integration stops just before its analytically known r=2 crossing, rather than clipping or continuing through escape. The outer half-stable trajectory approaches the circle slowly; a finite endpoint is not exactly on the cycle.

For Poincaré–Bendixson, the stable radial model has an explicit compact trapping annulus 0.5≤r≤1.5. Its radial rates at the boundaries are 0.375 and −1.875, both pointing into the annulus. Angular speed 1 excludes equilibria there. Smooth planar autonomous flow confined to this region has a periodic omega-limit orbit. In this example the orbit is also known explicitly as r=1. The theorem's hypotheses are checked analytically; plots illustrate them. Background for the radial models: [MIT Classical Mechanics III, section 7.4](https://live.ocw.mit.edu/courses/8-09-classical-mechanics-iii-fall-2014/d9bac33f6c60b304dc0398e99b327102_MIT8_09F14_full.pdf).

## Why some trajectories cannot repeat

For V=−x sin y, the supplied gradient field is −∇V and

```text
dV/dt = −sin²y − x²cos²y = −|F|².
```

A nonconstant periodic solution would integrate a strictly negative quantity over its period while returning V to its initial value, a contradiction. This potential is not coercive; the argument does not assert that every solution approaches the origin or remains bounded.

Dulac's criterion requires a simply connected domain, a continuously differentiable vector field and weight there, and a strictly one-sign weighted divergence. The first example has g=1/(xy) and div(gF)=−1/y on the open positive quadrant. Its weight is singular on the axes, which are excluded. The second has g=exp(−2x) and div(gF)=−exp(−2x) on the entire plane. These identities exclude nonconstant periodic orbits contained in their respective domains. Finite-difference divergence tests guard against transcription mistakes; grid samples alone would not prove the criterion. An annulus has a hole, so a Dulac argument requiring simple connectivity cannot be applied to it directly.

## Sel’kov: repeller plus trapping

Setting x′+y′=b−x to zero gives the unique equilibrium (b,b/(a+b²)). With s=a+b², its Jacobian determinant is s>0 and trace is

```text
τ = −1 + 2b²/s − s = [b² − a − (a+b²)²]/(a+b²).
```

For 0<a<1/8, τ>0 between the two bounds

```text
b_± = sqrt((1−2a ± sqrt(1−8a))/2).
```

At a=0.1 these are 0.4199919074 and 0.7896877850. They mark trace-zero boundaries with nonzero imaginary eigenvalues and transverse crossings as b changes. Establishing the detailed local Hopf criticality would require a nonlinear coefficient calculation; none is inferred merely from the trace. At a=1/8 the boundaries meet and the crossing degenerates.

Here is an explicit outer trap for every a,b>0. Set Y=b/a+1 and L=Y+b+1, and intersect x≥0, y≥0, y≤Y, x+y≤L. On the axes the flow points into the nonnegative quadrant. On y=Y, y′≤−a<0. On the sloped boundary, x≥L−Y=b+1, hence x′+y′=b−x≤−1. The polygon is compact and forward invariant. When τ>0 the unique equilibrium is a hyperbolic repeller; remove a sufficiently small local repelling neighborhood. The remaining compact region traps forward flow and contains no equilibria. Poincaré–Bendixson establishes at least one periodic orbit. This argument alone does not prove uniqueness or attraction from every initial condition.

Numerical tests use a=0.1 and b=0.2,0.5,1. The middle value yields a cycle with period about 10.648653. Two different starts produce matching late periods and amplitudes. The other two tested trajectories converge to their stable equilibrium. These are model computations, not a fit to biochemical measurements. The exact polynomial system is also studied by [Llibre and Nabavi (2022)](https://www.aimsciences.org/article/doi/10.3934/dcdsb.2022056).

## Liénard and two kinds of nonlinear oscillator

The supplied Liénard equation x″+f(x)x′+g(x)=0 is equivalent to x′=v, v′=−g(x)−f(x)v. For van der Pol with μ>0, f=μ(x²−1) is even and smooth; g=x is odd, smooth, and positive for x>0. Its odd primitive F=μ(x³/3−x) has exactly one positive zero √3, is negative before it, positive and increasing afterward, and tends to infinity. Thus all the supplied sufficient hypotheses for a unique stable limit cycle hold. For μ=0 the model is a linear center with a family of periodic orbits, so that conclusion does not apply.

The relaxation coordinates are y=v/μ+x³/3−x, giving x′=μ[y−(x³/3−x)] and y′=−x/μ. Here y is a transformed variable, not velocity. The illustrated μ=10 trajectory starts at (x,y)=(2,0), as in the supplied figure. The independent period comparisons start at (x,v)=(2,0). The leading large-μ period is μ(3−2 ln 2), derived from slow travel between x=1 and x=2 on each branch; see [MIT's derivation](https://math.mit.edu/classes/18.385/Lectures/Lecture14/Trapping_for_vdP_and_LCperiod.pdf). At μ=10 it underestimates the computed period: 16.1371 versus 19.0784. It is an asymptotic leading term, not an exact finite-μ formula.

For weak van der Pol, div(F)=ε(1−x²). Approximating the orbit by a circle of radius R, Green's theorem gives 0=επR²(1−R²/4), hence nonzero R≈2. The numerical μ=0.1 orbit has maximum x≈2.000103. The circular approximation is justified only in the weak regime.

The unforced Duffing equation conserves E=v²/2+x²/2+εx⁴/4. For ε≥0 its nonzero energy curves are a continuous family of periodic orbits, with no isolated attracting limit cycle. For initial amplitude A and v(0)=0, an independent period check uses

```text
T = 4 integral_0^(pi/2) [1 + (εA²/2)(1+sin²θ)]^(-1/2) dθ.
```

Composite Simpson quadrature with 2,000 panels evaluates this smooth integral. With ε=0.1, amplitude increases from 0.5 to 2 while period decreases from about 6.22514 to 5.51685. Energy drift in the saved numerical runs is below 3.5e−8.

## Averaging, damping, and the swing

For cubic velocity damping, E′=−εv⁴≤0. Averaging gives r′=−3εr³/8 in physical time and no leading phase correction, hence x(t)≈A cos t / sqrt(1+3εA²t/4). The ε=2, A=1, 0≤t≤50 test in the image has maximum position error about 0.2533 and RMS error 0.0745. The early discrepancy is visible; the calculation does not silently interpret “impressive agreement” as exact agreement. At ε=0.1 the maximum error is about 0.0236. Neither finite ε=2 accuracy nor late decay provides a general small-parameter error bound.

The undamped pendulum has exact period 4K(sin²(A/2)) for 0<A<π, evaluated with the corresponding smooth energy integral. Expanding yields ω=1−A²/16+O(A⁴). Tests check the numerical period independently and the fourth-order scaling of the frequency approximation error.

For the pumped swing, small angles give x″+(1+εγ+ε cos 2t)x=0. With x≈r(T)cos(t+φ(T)), T=εt, the supplied averaged equations are

```text
dr/dT = r sin(2φ)/4,
dφ/dT = [γ + cos(2φ)/2]/2.
```

The code uses regular quadratures A=r cos φ, B=−r sin φ, which are defined even at rest. In physical time, A′=ε(γ/2−1/4)B and B′=−ε(γ/2+1/4)A. Their leading instability band is |γ|<1/2, with exponential growth rate ε sqrt(1−4γ²)/4 along the growing direction. Outside the band the leading averaged growth rate is zero; finite-ε boundaries can shift. Specific initial phase also matters.

The full nonlinear equation, its linearization, and its averaged approximation are compared for ε=0.1, γ=0 and 1, starting at x=0.005,v=0 through t=160. At γ=0 the maximum angle reaches 0.1909; at γ=1 it stays below 0.00865. Exactly x=v=0 remains zero for every parameter value, so this idealized model requires a nonzero seed to grow. Real perturbations would supply one. This is a mathematical swing model, not an instruction for a physical experiment.

## Zero eigenvalues versus Hopf

The chosen planar pitchfork has origin eigenvalues μ,−1. At positive μ it has stable equilibria (±√μ,0) and the origin becomes a saddle. The chosen Hopf model has origin eigenvalues μ±i, radial equation r′=r(μ−r²), and a stable cycle r=√μ for μ>0. It demonstrates how a complex pair crossing the imaginary axis differs from a real eigenvalue passing through zero. These exact normal forms illustrate local mechanisms; their diagrams do not establish the global behavior of an unspecified system behind Figure 8.1.7.

## Numerical protocol and interpretation

- All trajectories use fixed-step fourth-order Runge–Kutta. Radial and gradient examples use step 0.01. Sel’kov uses steps 0.02 and 0.01 over 500 time units. van der Pol μ=0.1,1,10 uses durations 600,240,400 and coarse steps 0.02,0.02,0.004, each checked at half that step. Fast relaxation requires the smaller step.
- Periods use linearly interpolated upward x crossings: x=b for Sel’kov and x=0 for van der Pol/Duffing. Five complete late cycles are measured after at least half the total run (Sel’kov after t=300). Return-coordinate spread, period spread, and sampled extrema are saved. Extrema have finite sampling error. Two starts test attraction without confusing a phase shift with a different orbit.
- Same-time coarse/fine state differences are also saved. For μ=10 the maximum is about 0.00586 despite period agreement within 0.000002; steep jumps amplify small timing shifts. Step refinement is an accuracy diagnostic, not a rigorous global numerical error bound.
- Cubic damping uses steps 0.01/0.005. The pumped swing uses 0.01/0.005. Their approximation errors are separated from integration differences. Pendulum and Duffing periods are checked against independent energy integrals.
- Reproduction compares floating-point values with relative tolerance 1e−8 and absolute tolerance 1e−10. This allows minor platform math differences without accepting material result changes. No random sampling enters this third batch.

Planar autonomous theorems apply only where their hypotheses hold. They do not by themselves govern Lorenz's three-dimensional system, the time-dependent pumped swing, or stochastic discrete SIMS choices. The connection to coordination is a question to test: does repeated switching decay, settle into a persistent pattern, or depend on the starting state? A specific oscillatory SIMS mechanism would require an explicit behavioral rule and a fresh matched experiment. Nothing in these oscillator calculations estimates identity effects or establishes a claim about Freud.
