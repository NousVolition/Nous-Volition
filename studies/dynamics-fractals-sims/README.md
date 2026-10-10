# Dynamics, fractals, and SIMS

Can the same local choices produce different group outcomes when connections change? This study connects that human-coordination question to the dynamics and topology in the supplied images. **SIMS** are the simulated participants. The local package contains five batches of mathematical experiments, two matched SIMS experiments totaling 12,800 runs, fourteen original figures, and 116 automated tests.

Open [report.html](report.html) locally for the illustrated report. Figures and numerical results are saved with the code. The images supplied in the conversation are references; the plots here are newly computed.

## Run

From this folder, use Python 3.12:

```sh
python -m pip install -r requirements.txt
python -m unittest -v
python run_study.py --check
python bifurcations.py --check
python oscillations.py --check
python topology.py --check
python heteroclinic.py --check
python pacemaker.py --check
python memory_inference.py --check
python quench.py --check
```

The tests check analytic formulas, numerical accuracy, graph construction, stability, and identity/geometry invariance. The study command reruns 10,240 SIMS rounds plus the first mathematical batch. The topology command includes 2,560 additional SIMS runs and 39,056 bounded algebraic equalities. The oscillation run also checks period convergence across step sizes and initial states. The fifth batch checks saddle connections, 48 isolated nine-state trajectories, 64 starts for a 16-unit pacemaker ring, local memory, interaction inference, and 12 quenches. NumPy is required for the coupled ensemble, inference, quenches, and their tests; the earlier calculations and isolated heteroclinic solver use the standard library.

To regenerate the saved data and figures:

```sh
python run_study.py
python bifurcations.py
python oscillations.py
python topology.py
python -m pip install -r requirements.txt
python heteroclinic.py
python pacemaker.py
python memory_inference.py
python quench.py
python build_report.py
```

The default seed is `20261009`. Alternative samples can be generated with `--rounds`, `--sensitivity-rounds`, and `--seed`; these replace `results.json`, so keep a separate copy of the defaults for comparison. Saved mathematical times are dimensionless except where explicitly identified as SIMS seconds.

## Batch 1: flow, sensitivity, and finite fractals

| Supplied idea | Implemented equation or construction | Check |
| --- | --- | --- |
| Lorenz attractor | x′=10(y−x), y′=x(28−z)−y, z′=xy−(8/3)z | Equilibria, step refinement at t=1, sensitivity to an initial displacement of 10⁻⁸ |
| Phase-space trajectory | θ′=v, v′=−sin θ−0.2v | A chosen damped pendulum example; energy decreases |
| Overdamped spring | x′=v, v′=−4v−x | Exact two-exponential solution; compare to reduced x′=−x/4 |
| Euler's method and logistic growth | x′=x(1−x) | Exact logistic solution, first-order Euler error and fourth-order Runge–Kutta error |
| Laser-inspired scalar threshold | n′=(p−1)n−n² | Chosen dimensionless growth/saturation model; exact solution and positive-seed equilibrium |
| Menger sponge, “Menger cheese” | Retain 20 of 27 subcubes recursively | Counts, face contacts, volume, exposed surface, connectivity |
| Koch snowflake | Replace each segment by four segments of one-third length | Segment counts, perimeter, polygon area, cyclic neighbor graph |

Lorenz parameters follow the [classical equations illustrated by Prof. Swift](https://ac.nau.edu/~jws8/classes/667.2023.1/lorenz.html) and [Lorenz's original paper](https://journals.ametsoc.org/doi/pdf/10.1175/1520-0469%281963%29020%3C0130%3ADNF%3E2.0.CO%3B2). The numerical displacement reaches order-one separation after about 28 time units, but its precise crossing time changes when the step is halved. This is a sensitivity demonstration; local error checks do not certify a long chaotic trajectory or establish a Lyapunov exponent.

The first laser example tests onset in a scalar intensity-like variable. It has no optical phase variable, so its threshold is not a measurement of phase coherence. A positive seed is required: zero stays zero even above threshold in this deterministic model. The supplied two-variable laser equations are implemented separately in batch 2.

For unit initial side length, the finite Menger stage has 20ⁿ cubes, volume (20/27)ⁿ, and surface area 2(20/9)ⁿ+4(8/9)ⁿ. The Koch stage has 3·4ⁿ segments, perimeter 3(4/3)ⁿ, and area (√3/4)[8/5−(3/5)(4/9)ⁿ]. Tests compare these formulas with explicit cell/edge counts and polygon areas. We render finite stages; zero volume and infinite perimeter/surface describe limiting constructions. Background: [Caltech Menger construction notes](https://www.its.caltech.edu/~matilde/FractalsUToronto7.pdf) and [Reed's snowflake area derivation](https://people.reed.edu/~mayer/math111.html/header/node12.html).

## SIMS experiment: geometry versus connections

The Menger level-1 network contains 20 SIMS, one per retained cube, connected only when cubes share a face. Corner seats have degree 3; edge seats have degree 2. Its control is a ring of 20 SIMS. The Koch level-2 boundary contains 48 SIMS, one per vertex, connected along the boundary; its control is a ring of 48 SIMS. Euclidean proximity does not create extra links. Menger levels 2–3 and additional Koch levels are used for geometry checks, not additional SIMS population trials.

For each one-second tick, seats are randomly ordered and independently active with probability 0.25. An active ordinary SIM copies a uniformly selected neighbor, refusing a differing proposal with probability 0.15. Main runs have zero spontaneous initiative, so an ordinary consensus is absorbing. The sensitivity sample allows a spontaneous color flip with probability 0.02 before considering copying.

The focal position either behaves ordinarily, **holds** its starting color, or **opposes** its neighbors' current majority (holds on a tie). The Menger corner and edge roles are separately tested and use matching seat indices in the ring control. Every round continues for 120 seconds, even after first agreement. We measure first consensus, endpoint unanimity, end-of-second agreement snapshots, agreement breaks, switches, refusals, and direct copying credits. Snapshot fraction is not continuous agreement duration: within-second events can briefly form or break consensus.

There are 16 scenarios, each with 512 main rounds and 128 initiative-sensitivity rounds: 10,240 runs total. Within a population size, scenarios reuse starting colors, randomized identity assignments, and random opportunity streams. Scenario order is shuffled within each block. Four random draws are reserved per seat even when inactive, keeping opportunities aligned across policies. No learning or fatigue carries between runs. First unanimity includes time zero; capped time assigns 120 seconds to unsuccessful rounds.

| Main comparison, no initiative | Ever unanimous | Unanimous at 120 s |
| --- | ---: | ---: |
| Menger, ordinary | 71.48% | 71.48% |
| Matched ring of 20, ordinary | 52.54% | 52.54% |
| Menger, corner opposes | 38.48% | 1.95% |
| Menger, edge opposes | 28.52% | 1.37% |
| Koch boundary, ordinary | 6.45% | 6.45% |
| Matched ring of 48, ordinary | 6.45% | 6.45% |

The Koch and ring outcomes are identical in every matched scenario because their adjacency lists are identical. Bending the drawing changes no rule input. Menger changes adjacency, and its ordinary runs reached consensus more often than their equal-sized ring control. This compares whole graph structures; degree, paths, and other connectivity properties change together, so it does not isolate a uniquely “fractal” cause. Comparing Menger directly to Koch would also change population size.

Identity labels have no behavioral effect in this experiment, verified by a permutation test. Consequently, these results can show positional effects within the model but cannot estimate personality effects. Copying credit measures successful direct copying, not authority. A held color matching a final consensus is built into the holding rule. An opposing SIM can break consensus whenever it becomes active, so first agreement is not lasting agreement.

`results.json` includes Wilson intervals for first-consensus proportions and paired Monte Carlo differences against each ring control. Those intervals describe finite simulation sampling, not uncertainty about real populations or the assumptions. Only initiative is varied in this follow-up: activation, refusal, update order, graph contact rules, and the horizon remain choices. These larger-network experiments extend the earlier nine-SIMS study and use a different, explicitly matched random-number schedule.

## Batch 2: tipping points and multiple stable states

**Cusp and hysteresis.** x′=h+r x−x³ has three equilibria when r>0 and |h|<2(r/3)³ᐟ². At r=1 the folds are h=±0.384900. The plotted up/down paths follow the nearest stable equilibrium until that branch disappears. They are quasistatic equilibrium continuation, not finite-speed parameter sweeps; dynamic delay would require a sweep-rate study.

**Bead on horizontal or tilted wire.** The last supplied image fixes the equilibrium equation:

```text
mg sin(θ) = k x [1 − L₀/√(x²+a²)]
```

With positive viscous drag b, use b x′=mg sin(θ)−k x[1−L₀/√(x²+a²)]. We choose a=1, L₀=1.4, and mg/k=1. Horizontal equilibria are x=0 (unstable) and x=±0.979796 (stable). The fold load magnitude is 0.126100, corresponding to |θ|≈7.2443°. These values depend on the selected geometry and force scale. With L₀<a there is one stable horizontal equilibrium. See also [MIT's bead-on-wire notes](https://ocw.mit.edu/courses/18-385j-nonlinear-dynamics-and-chaos-fall-2004/resources/bead_on_wire/).

**Budworm outbreak.** The cropped population equation specifies logistic growth minus predation; we supply the standard saturating predation choice p(N)=B N²/(A²+N²). With x=N/A, τ=Bt/A, r=RA/B, and k=K/A, it becomes x′=r x(1−x/k)−x²/(1+x²), as used in [Boston University's budworm lab](https://math.bu.edu/people/bob/MA226/spruce-budworm-lab.html). At r=0.5, k=10, stable positive levels are x≈0.683375 and 7.316625, separated by unstable x=2. Initial conditions select the basin. The fold curve is k=2x³/(x²−1), r=2x³/(1+x²)² for x>1; the cusp occurs at k=3√3, r=3√3/8. This mathematical example does not fit a specific forest or management intervention.

**Subcritical pitchfork.** The supplied equation x′=r x+x³−x⁵ has saddle-node folds at r=−1/4, and x=0 changes stability at r=0. Between those values there are three stable equilibria separated by two unstable equilibria. For the crop that mentions a parameter a without showing its equation, we additionally examine the clearly specified extension x′=r x+a x³−x⁵ at a=−1,0,1. This choice produces supercritical, degenerate, and subcritical onsets respectively; it is an added parameter study, not a recovered missing formula. [MIT's normal-form notes](https://ocw.mit.edu/courses/18-385j-nonlinear-dynamics-and-chaos-fall-2004/resources/babynormalforms/) provide background on local bifurcation models.

**Overdamped rotating hoop.** In dimensionless time, φ′=sin φ(γ cos φ−1), γ=Ω²R/g. For γ>1 the new stable equilibria are φ=±arccos(1/γ), within ±π/2. Near zero, φ′=(γ−1)φ−[(4γ−1)/6]φ³+O(φ⁵). At γ=2 the stable angles are ±π/3. This uses the friction-dominated approximation and γ≥0.

**Improved laser.** The supplied equations are n′=G nN−κn and N′=−G nN−fN+p. We use G=κ=1, f=0.2 and positive n(0)=0.01. The off equilibrium is (0,p/f); the on equilibrium is (p/κ−f/G,κ/G), physically available above pₜₕ=κf/G=0.2. At p=0.8 the on state is (0.6,1), with eigenvalues −0.4±0.663325i: perturbations spiral inward and the integrated trajectory exhibits decaying relaxation oscillations. At threshold a zero eigenvalue means slow convergence, so the finite-time endpoint is not treated as an exact equilibrium. Rate-equation context: [MIT photonics, Lasers](https://www.ocw.mit.edu/courses/6-974-fundamentals-of-photonics-quantum-electronics-spring-2006/18f30fad63a62ef4dd894d3752b55a60_chapter7.pdf). Neither laser model contains optical phase, and both omit spontaneous-emission noise.

## Batch 3: cycles, exclusion arguments, and nonlinear oscillators

The latest screenshots are implemented in `oscillations.py`, with full equations, analytic arguments, numerical settings, and source distinctions in [OSCILLATION_METHODS.md](OSCILLATION_METHODS.md). Saved measurements are in [oscillation_results.json](oscillation_results.json).

The tests cover stable/unstable/half-stable cycles; the exact supplied gradient and Dulac examples; Poincaré–Bendixson trapping; the Sel’kov glycolytic oscillator; Liénard's hypotheses for van der Pol; weak and relaxation oscillations; unforced Duffing energy families; pendulum frequency corrections; cubic velocity damping; and the parametrically pumped swing. A chosen planar pitchfork and Hopf comparison illustrates the final stability-change page.

At a=0.1, b=0.5, the Sel’kov cycle has period about 10.648653, with agreement across two starting states and smaller steps. van der Pol has near-2 amplitude at μ=0.1 and slow/fast motion at μ=10. Duffing preserves a family of amplitudes. An exactly resting swing stays at rest in the deterministic model, while a small seed grows under resonant pumping. Approximation errors and finite-step differences are reported separately.

One source item remains pending: the vector field for the μ-dependent annulus in Figure 7.3.3 was not supplied. It is explicitly marked as not run. Figure 8.1.7 also omits its equations; its mechanism is illustrated using labelled normal forms, without claiming to reconstruct that exact system.

## Batch 5: switching, synchronization, memory, and stopping

The latest references drive executable experiments documented in [HETEROCLINIC_METHODS.md](HETEROCLINIC_METHODS.md). A three-saddle cycle develops longer pauses; the nine-state model changes its transition preferences when rates change while connections remain fixed. The 16-unit model produces two different synchronized patterns at the same parameter settings, selected by initial conditions. An uncoupled control removes collective switching. Smaller-step comparisons preserve the selected patterns.

The local memory diagnostic tests how a hidden offset survives or is erased while passing saddles. A least-squares inference baseline recovers interactions from full activity observations and tests them on a new trajectory; equilibrium-only data fail identifiability. Twelve sudden parameter changes measure damped relaxation toward coexistence and record a case that does not confirm settling within the horizon. These mathematical activity-state experiments do not add to the SIMS round count.

## How the batches connect

The newest [topology tests](TOPOLOGY_TESTS.md) use graph projections, lifting, gluing, category nerves, and cubical identities as executable specifications. They also test two concrete ways that topology interacts with the SIMS model: changing filled faces while holding pairwise contacts fixed, and changing contacts by taking transitive closure. An exact counterexample shows that matching group totals can conceal different next-step dynamics. Full outcomes are in [topology_results.json](topology_results.json).

The shared tools are state, local change rules, equilibria, sensitivity, and stability. The ODE examples test continuous dynamics; the SIMS experiment tests discrete stochastic coordination on specified graphs. We have not inserted a Lorenz trajectory, laser equation, or bead force into a SIM's decision rule. Doing so would require another behavioral assumption and an explicit experiment. Here the meaningful connection is testable: distinguish first arrival from persistence, compare alternative basins, and hold the rules fixed when changing connections.

For volunteer work, start with the earlier [resisting-position protocol](https://github.com/NousVolition/Nous-Volition/tree/main/studies/one-resisting-position), rotate occupants through positions, separate an assigned role from personal behavior, and obtain voluntary consent with an unrestricted option to stop. The 20- and 48-SIMS simulations do not require recruiting those group sizes immediately.
