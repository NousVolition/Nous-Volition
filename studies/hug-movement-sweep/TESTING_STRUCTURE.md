# A testing structure for the Hug

The question is whether movement changes the expression of retained history enough to change the Hug's rhythm. A changing colored pattern is evidence about the field; it is not, by itself, evidence about rhythm or real clay.

This structure was prepared with literature discovery through SciSpace. The test choices and thresholds below are ours, not prescriptions taken from those papers. The immediate numerical study occupies stages 1–4; the material measurements in stage 5 remain future work.

**Before a full field simulation:** complete the [specification register](SPECIFICATION_STATUS.md). It distinguishes corpus laws, the user's graded upper-region design intent, and the assistant-added surrogate. The completed study's fixed formulation includes a capped source, relaxation, pair exchange and Burgers mechanics; those additions are not supplied by the corpus. Its Newtonian analogy does not derive the Burgers law. The full field domain, boundaries, meaning and units of S, input/kernel normalization, branch choices and fluid/body coupling still require explicit specifications.

| Stage | Question | Evidence required | What it cannot establish |
|---|---|---|---|
| 1. Equation fidelity | Which corpus laws are retained, modified or augmented, and is the stated surrogate implemented correctly? | Separate corpus-law and extension audits; pinned files; zero-deformation limit; exact lower-half exclusion; retained input; conservative redistribution | Equivalence of the surrogate to the full corpus system, or physical validity |
| 2. Numerical trust | Does the answer persist with finer calculations? | 32/64/128 spatial cells, tighter time accuracy, energy balance, finite fields, matched-effect convergence | Experimental validation |
| 3. Mechanism | Is a change caused by movement feedback? | Paired moving/fixed spatial operators at identical parameters and histories; a second family with orbit force held fixed | A causal conclusion about people or inherited memory |
| 4. Rhythm | Is it a change in size, timing, phase, or orbit repetition? | Separate amplitude, cycle period, phase offset, pause/recovery and full mechanical repeat diagnostics | A proof of an asymptotic limit cycle, chaos, or universal critical threshold |
| 5. Material identification | Does the clay support the proposed mechanics? | Independent load/recovery measurements; repeatability; varied amplitudes, rates and waiting times; held-out predictions | Identifying the abstract S field from ruler measurements alone |

## Fixed before the numerical sweep

Run movement settings r=1, 3, 10, 30, 100, 300. Reduce the active saturation coefficient to b0/r², multiply the two starting displacements by r, and multiply orbital force RMS by r. This changes the simulated motion without changing the memory-feedback equations. It is an intervention on the active mechanism, not a measurement or a claim that the user specified these parameter values. Keep the spring, inertia, clay coefficients, memory parameters, source history and orbital period fixed.

For every setting compare the full movement feedback with fixed spatial operators, under no orbit, circular forcing, and eccentric forcing with e=.212. Run both mechanical starts: 72 primary trajectories. At r=100 and 300 also keep orbital RMS fixed at its original value: 24 secondary trajectories. This detects changes caused by a weakening relative external drive rather than by memory feedback. Initial conditions reset only between independent experiments; no history or mechanical state is reset during a trajectory.

Keep the prior 480–720 s braking interval and the separate 950–970 s source event. Measure recovery before that later event; if it has not been confirmed by 949.5 s, report it as unconfirmed within that window. Do not convert a missing observation into infinite recovery time. All paths run to 1800 s.

## Outcomes and operational decision bands

Report raw effects even when they are below a decision band. The bands make the screen readable; they are not p-values, validated physical tolerances, or proof of no effect.

| Outcome | Measurement | Screen for a noticeable paired change |
|---|---|---|
| Actual movement | Maximum and late half-amplitude of d; shear d/L | Report the achieved value, not just the input multiplier |
| Rhythm size | Median trailing 57 s half-range, late window 1600–1800 s | At least 1% change versus the matched fixed-operator case |
| Rhythm pace | Mean upward-crossing period, using displacement and velocity in cubic Hermite interpolation | At least 1% relative period change |
| Rhythm timing | Wrapped phase offset atan2(-v/omega,d-centre), compared at equal late times | At least .05 cycle offset; shape harmonics can also affect this phase measure |
| Recovery | Sustained 80% amplitude return and mechanical orbit-repeat confirmation | At least one orbital period (5.7 s) delay change, or a confirmed/unconfirmed difference |
| Orbit repetition | Maximum change in all four mechanical states across ten one-orbit comparisons | Different late repeat status at tolerance .01 after normalizing states by r |
| Field restructuring | Matched spatial RMS difference and its spatial mean | Report separately; not a rhythm criterion |
| Retention | A equals integrated inputs; event catalog hash unchanged | No resetting or decay of accumulated A |

The circular load has a strong twice-per-orbit component. One-orbit mechanical repetition is reported without calling it one oscillator cycle per orbit. No-orbit paths have no orbital synchronization label. Short windows, phase portraits and numerical diagnostics accompany animations, so apparent visual overlap is never the sole test.

Every primary setting is repeated at 64 cells and with tighter time accuracy at 32 cells. The largest primary setting and both fixed-force controls are also checked at 128 cells. Any additional primary setting that crosses a rhythm band must be checked at 128 cells before its crossing is described as resolved. A finite sweep brackets sampled behavior; it cannot locate an exact transition by itself.

## How SciSpace informed the structure

- [Ewoldt et al., *Large amplitude oscillatory shear of pseudoplastic and elastoviscoplastic materials*](https://link.springer.com/article/10.1007/s00397-009-0403-7), Rheologica Acta 49, 191–212 (2010). The publisher abstract describes varying strain amplitude and frequency and using stress–strain/rate loops. This motivates a future amplitude-by-frequency material study. The Hug sweep here is an active-oscillator intervention, not their strain-controlled LAOS experiment.
- [Agarwal et al., *Distinguishing thixotropy from viscoelasticity*](https://arxiv.org/abs/2106.13452), Journal of Rheology 65, 663 (2021), DOI 10.1122/8.0000262. Their experiments show why superficially similar recovery can have different causes. Waiting-time-dependent step tests after preshear are useful discriminants for their tested materials. This motivates independent material tests before calling S a measured clay structure variable. No coefficients are transferred from their samples.
- [Lucas, Newman and Stefanovska, *Stabilisation of dynamics of oscillatory systems by non-autonomous perturbation*](https://arxiv.org/abs/1803.11392), Physical Review E 97, 042209 (2018). Their study separates time-local behavior from long-term stability and finds intermittent synchronization in its systems. This motivates displaying time windows and reporting finite-horizon conclusions; it does not establish the Hug's stability.

SciSpace supplied discovery results and a methods column. The statements above were checked against primary publisher/author sources. Only an abstract was available for the first paper; the second abstract and third full paper were available. Unverified extraction details were not used as a protocol. This is a targeted starting literature set, not a systematic review.

## Future clay measurements

Record material identity, water content or preparation, dimensions, rest time, load, displacement versus time, and temperature where possible. Repeat a small load/recovery test before varying load, rate and waiting time. Compression and shear remain separate protocols. Keep raw observations, model fitting data and held-out prediction data separate. A kitchen-scale compression test cannot directly identify all Burgers shear coefficients, an abstract memory field, or finite-strain damage.

The current linear Burgers element has no identified yielding, hydration, fracture, or evolving microstructure law. Larger synthetic shears test the reduced equations; they do not establish that a real clay sample would survive or follow them. Human social-memory analogies and adoption reference material are not physical calibration data.
