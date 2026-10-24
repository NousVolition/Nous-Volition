# From source observations to the two-in-one field

This connection is an explicit analytical proposal. The corpus equations are retained; the observation operator is new. It is not a recovered fact about what the author originally intended each mathematical symbol to mean.

## Three levels of evidence

1. **Reported experience:** an episode, its person, expression, content, temporal ordering and history references, with source qualifications. DES reports are interviews about sampled experience, not direct instruments measuring an inward field.
2. **Operational interpretation:** using the author's definitions, code inward putting-forward as Smoke and receiving/reconsideration as Clay. One operation can contain both functions. These labels belong to operations in one person's experience, not to two people, fixed spatial regions or a speaker/listener conversation.
3. **Added numerical hypothesis:** locate two content alternatives in a declared chart and read their contextual support from the full S field. This step is needed to compare an equation with a report, and remains contestable. It is not in the corpus verbatim and has not been calibrated by independent observations.

The [observation ledger](observations.json) contains five episodes, ten content/operation nodes and three source-attributed history references. All belong to one person. Empty history references mean that a history was not recorded here. They do not mean a person or inward function has no history.

## Smoke, Clay and the moving idea

| Element | Source connection | What remains unresolved |
|---|---|---|
| Smoke | Reported inward presentation of an appraisal, retrieved content or alternative image | Exact timing and numerical strength; verbalness alone does not measure this function |
| Clay | Reported reconsideration, search for missing content or evaluation of alternatives | Receiving, holding, questioning, refusing and reshaping are not separately measured state variables |
| Moving idea | Preserve content, expression mode and reported transitions together | Neither u nor S alone decodes the idea; a coordinate distance does not prove equivalent meaning |
| Personal history | Keep the earlier event/reference, current retrieval and interpretation distinct, owned by their person | Reports do not supply U(t), its baseline, A at window start or the preceding fields |
| Sens / Sin | Content/intended meaning, where reported, stays distinct from words, imagery or other expression | No matched-wording semantic-equivalence score is available here |

For sample 10.1, two contents anchor the chart: P = understanding/patience, F = frustration. This assigns coordinates to alternatives, not to Smoke and Clay. The fixed separation is a numerical assumption. The schema retains the inward functions as operations on these alternatives. It does not add two new role-state differential equations.

## Exact dynamics and the explicit observation operator

```text
u_t + (u·∇)u = −∇p + νΔu − (σ/ρ) a(q) e_k
∇·u = 0
q = |∇S| − Γcrit
S_t + u·∇S = D_diff ΔS + K_h(x−x0) κ A(t)
A(t) = ∫[model origin to t] γ[U(s)−Ubaseline] ds
T = μ0(∇u + ∇uᵀ), with μ0 = ρν in this implementation

Added observations, not extra dynamics:
c_j(t) = ∫ w_j(x) S(x,t) dx,  ∫ w_j = 1
V_j(t) = ∫ w_j(x) u(x,t) dx
Δc(t) = c_P(t) − c_F(t)
```

All field terms above are computed together. Pressure is recovered by the incompressibility projection, not omitted. The nonlinear advection, diffusion, threshold response, source, accumulator, stress and energy accounting remain active. The three corpus responses are run separately: max(q,0); q/[1+exp(−2q/ε)]; and zero for q≤0 with q exp[−(ε/q)²] for q>0. Negative values of the tanh response are retained. No forgetting or friction proportional to velocity is substituted for the fixed-direction force.

The component equations come from corpus paragraphs 229–230, 516–532 and 545. Joining them on a shared periodic unit square is a declared numerical coupling. The chart, kernels, dimensionless scales, parameters and initial conditions are assumptions recorded in [PROTOCOL.md](PROTOCOL.md), not measured psychological geometry. S retains a signed status/context interpretation; it is not renamed Sens. u is movement in the assumed chart, not a literal measured thought speed.

The corpus's exact-margin utility optimization (paragraphs 105–107) is not solved from these reports: there is no measured feasible set, objective or margin to solve it. U−Ubaseline=0 is a **declared future input condition**, not an inferred optimum. The corpus's scalar reciprocal-invariance statements and optional alternative regularizations are not silently promoted to additional evolution laws. Thus this is a full coupled field calculation under specified inputs, **not a completed empirical implementation of every corpus statement**.

## What the observation constraints mean

The primary test translates coexisting operative alternatives to c_P>0, c_F>0 and choosing understanding to Δc′>0 at window start. These inequalities are hypotheses about the readout, not measured psychological numbers. The report does not establish a numerical ranking. In particular, adding a constant to S shifts both supports but leaves their contrast and the dynamics unchanged; positive support depends on the chosen zero. The unit tests expose this dependence.

The primary witness permits both absolute supports to fall while their difference increases. A clearly labelled [exploratory follow-up](CONSTRAINT_AMENDMENT.md) imposes c_P′>0 and c_F′<0 instead. Ambiguity survives that stronger directional reading. Neither version supplies a measured endpoint at dimensionless t=1.

V_j is retained as a proposed movement readout, but the source provides no matching vector measurement, so no vector error score is reported. The code does not turn these readouts into semantic labels or a decoder of a person's thought.

## History without invented biography

The original model has A=0 at its own origin. A nonzero A at observation start is compatible with a prior utility integral: with γ=1, a constant earlier excess utility A_start over a unit interval gives that accumulator. This demonstrates only accumulator compatibility. It does **not** reconstruct the person's utility, earlier S/u fields, or a complete earlier trajectory reaching the assumed window-start state.

The graph links reported earlier references to relevant operations. Numerical trials vary an unknown shared accumulator while holding the window-start fields fixed. The equations still do not provide separate Smoke-history and Clay-history state laws. Relabelling an otherwise identical numerical input as Smoke or Clay cannot change the field. That limitation remains visible rather than being disguised by a fitted predictor.

## Forms remain distinct

| Moving idea form | Required observation | Present evidence |
|---|---|---|
| Water | Perceived balance, separately from calm and disturbance | Not established; patience and frustration can coexist without a balance claim |
| Fog | Which content is remembered and which features are clear or missing | Partial feature connection in 8.5; memory accuracy is untested |
| Wind | Experienced time/spacing distinguished from clock time and memory age | Partial pace connection in 11.3; no measured time distortion |
| Mist | A specified unspoken assumption, its internalization and endorsement | Unknown; silence alone is insufficient |
| D₂O | A specified small change and a measured helpful or harmful consequence | Unknown; no harm boundary or chemical inference is introduced |
| H₂O₂ | A separately defined experiential role | Undefined in this observation model; not substituted for D₂O |

No form is forced onto the equations from a word such as storm, an image, a sentiment score or numerical equilibrium. Unknown fields are null. These are experiential metaphors; their physical chemistry does not validate the inward model.

## Miro connections actually used

Selected frames on the [Math + Logic board](https://miro.com/app/board/uXjVEXBJz3k=/) were read live on 23 October 2026:

- **10 — meaning connections** (`3458764687915993860`): preserve meaning/expression/context; identify proposed links and declare a shared representation before comparing decisions or distances.
- **13 — memory coupling** (`3458764687916065203`): use the proposed shared S/u loop and normalized source. On the periodic domain, mean S′=κA.
- **16 — past survives zero** (`3458764687918055185`): retain the nested history integral; current U=0 need not erase A or prior field effects.
- **18 — hidden states** (`3458764687918055187`): look for different admitted states consistent with current observations; test which additional observation would distinguish them.
- **Theory map** (`3458764688184818696`): trace claims to observations and declared tests rather than treating a diagram as empirical evidence.

Two selected-frame reads returned 46 and 77 items, with 86 and 79 items skipped. This is not an exhaustive board review. [provenance.json](provenance.json) records the source version, hashes and frame IDs. The available corrected DOCX was hash-checked; no different newer corpus is claimed.

## What would test the entire interpretation

Use independently coded, time-indexed episodes from multiple people with consented public release or suitable access: content and intended meaning, expression, inward putting-forward and receiving/reconsideration, relevant autobiographical references, repeated observations of each idea form, and later outcomes. Define the chart, time scale, support zero, utility/input measurement and history-to-state initialization using development records. Freeze them before examining later outcomes or held-out people. Confirm that different admissible initial histories no longer produce indistinguishable observations but conflicting predictions.

This study uses all selected episodes as development evidence. It neither fills gaps between interviews nor calls already inspected records holdouts. The next requirement is a measurement mapping that distinguishes the admissible histories, not a more elaborate numerical solver alone.
