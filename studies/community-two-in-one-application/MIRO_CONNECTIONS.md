# Updated corpus and Miro reconciliation

Reviewed 23 October 2026. This update uses the available corrected corpus and live Miro content to strengthen the two-in-one study. It adds 12 full coupled numerical runs and 69 checks. It does not replace the model with a simpler predictor or claim a completed empirical test of the whole inward process.

## Which version was used

The Desktop file **Plain_Language_Corpus_Math_and_Logic_Corrected.docx**, modified 21 October, has SHA-256 `01f9ab0942f9c88982863e2ffc1e3c495786b5e6b67a26ae77d18235e7058acf`. A fresh extraction recovered 624 nonempty paragraphs. The bytes match the source already used in the latest field tests. This is the most recent relevant corrected document identified in the checked local locations; a different newer document has not been identified.

The [corrected corpus board](https://miro.com/app/board/uXjVEXBJz3k=/), [AI comparison testing strategy](https://miro.com/app/board/uXjVEW8HkiQ=/), and [codebase architecture board](https://miro.com/app/board/uXjVEXlaw6E=/) were read live in selected relevant areas. Eight owned boards were inventoried; the remaining boards were empty or showed playground/template content in their overviews. This is not a claim to have read every board widget, embedded image, table or prototype. The tool reported foreign/skipped content; the source register preserves those limitations. Local retrieval snapshots are retained outside the publication directory. Only relevant source descriptions and links are published.

## What the boards contribute

| Source | Connection used here | Status |
| --- | --- | --- |
| [Meaning and field connections, frame 10](https://miro.com/app/board/uXjVEXBJz3k=/?moveToWidget=3458764687915993860) | Keep Sens, Sin, context, utility, permitted region, decision and observations distinct. The dashed links require an operational mapping. | Source distinctions retained. The within-person interpretation follows the author's chat clarification; it is not automatically supplied by the interpersonal diagram. |
| [Memory coupling, frame 13](https://miro.com/app/board/uXjVEXBJz3k=/?moveToWidget=3458764687916065203) | Accumulated input drives S; its gradient activates a force; u transports S. | Exact component equations are retained. Identifying the S and u in these components on one shared periodic domain is an explicit coupling choice. The board marks the return path as proposed. |
| [Persistent input, frame 16](https://miro.com/app/board/uXjVEXBJz3k=/?moveToWidget=3458764687918055185) | Total field depends on when input occurred, not just its final sum. | Derived and numerically checked under normalized source and zero net boundary flux. Not an observed law of human remembering. |
| [Hidden states, frame 18](https://miro.com/app/board/uXjVEXBJz3k=/?moveToWidget=3458764687918055187) | Equal readings need not identify equal underlying states. | Used to require separating measurements and test field-scale and sign ambiguity. |
| [Response probes, frame 20](https://miro.com/app/board/uXjVEXBJz3k=/?moveToWidget=3458764687918055189) | Probe negative tanh values, tiny positive exact-off values, and mirrored gradients. | Added executable checks and full coupled sign-reversal runs. |
| [Grounding the core loop](https://miro.com/app/board/uXjVEXBJz3k=/?moveToWidget=3458764688169288636) and [Theory map](https://miro.com/app/board/uXjVEXBJz3k=/?moveToWidget=3458764688184818696) | Compare persistence, fading and retention floors using earlier/later observations. | Proposed alternatives registered; no decay or relaxation silently inserted into the exact equations. |
| [AI comparison protocol](https://miro.com/app/board/uXjVEW8HkiQ=/?moveToWidget=3458764688184078595) | Preserve meaning and force; distinguish a correct number from a correct expression; record protocols and failures. | Used as review criteria, not as new human observations or an instruction to run the board's AI prompts. |

## New numerical findings

The unchanged full coupled solver was run for three response laws, two grids (24 and 48), and two signs: **12 additional synthetic runs**. The plan was saved before execution. These supplement the original 36 runs; the study now contains 48 coupled synthetic runs, not 48 human trials.

At every recorded interval endpoint, simultaneously reversing the initial signed S and excess-input history reverses S and A but preserves u. Final gradient magnitude, response force and pressure also agree within the declared tolerance. This follows the symmetry of the full equations: advection and diffusion are linear in S for a given u, while the response depends on the magnitude of its gradient. It is stronger than checking one isolated force value. It does not say different human meanings are equivalent.

The tanh response minimum occurs at `q/epsilon = -0.639232271380537`, with `a/epsilon = -0.139232271380537`. Negative excess therefore is not necessarily an inactive response. With the smooth exact-off law at `q=0.01, epsilon=1`, `log(a)=-10004.605170185989`: a is mathematically positive, although float64 returns zero. All three laws pass the fixed-direction work test: reversing the velocity reverses the force's energy contribution, so this force is not automatically drag.

The [69 checks and recorded diagnostics](results/miro_checks.json), [endpoint states](results/miro_states.npz), [test plan](MIRO_TEST_PLAN.md) and [executable test](check_miro_connections.py) preserve the calculations. These results identify mathematical distinctions an empirical observation scheme must be able to detect.

## Persistence is not yet a calibrated forgetting model

The exact accumulator remains `A' = gamma (U-Ubaseline)`, with `J=kappa A`. There is no added decay. A nonzero A after a pulse continues to supply S. Diffusion can smooth spatial variation while total S grows; absence of accumulator decay does not mean every spatial detail stays unchanged forever.

The board's retention curves `R(t)=c+(1-c)exp(-lambda t)` and `R(t)=exp(-t/S)` are proposed alternatives. Their R is a retention response, and the S in the latter is a time scale; neither is automatically the corpus's reciprocal-scaling R or the status/context field S(x,t). A curve alone does not specify where forgetting belongs in the coupled model. Decay in A and relaxation of S have different effects and would be explicitly new dynamical assumptions.

The board recommends agreement between AIC, BIC and cross-validation. That is a proposed decision rule, not evidence that a model is correct. A future comparison needs a declared observation likelihood, parameter accounting, temporal split and primary prediction criterion. Failure to outperform another model does not by itself prove the field is static. Second-coder agreement also cannot substitute for observed inward histories or prove an interpretation true.

## Source differences and remaining observations

The architecture board still describes the older reported total of 83 selected terms. The corrected DOCX paragraph 273 and the current corpus board report a recount of **90: 70 body and 20 reference-title occurrences**. This reconciliation follows the newer source and attributes that count; it does not claim to have performed a new manuscript recount. The separate broader-vocabulary count on the board is a different selection and must not be combined with 90.

The current source links strengthen traceability, but do not turn the audited 840 thought probes into measurements of all required constructs. The [measurement record](MEASUREMENT_RECORD.md) still requires inward receiving, intended meaning, recalled-event contents, perceived balance, felt time, unspoken agreement and consequences of small changes. The boards provide proposed tests and mathematical relationships, not those missing participant records. The reserved participants remain unused for response analysis or model selection.

The author's current definitions govern the inward interpretation: Smoke and Clay are within one person; the named forms belong to the moving idea; Water is perceived balance; D2O names a small compositional change with potentially large consequences. No automatic form classifier, harm threshold or extra role force is inferred from these names.
