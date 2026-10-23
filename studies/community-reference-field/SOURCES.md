# What the new source measures

The search compared three primary research resources. [OneCommon's reference-resolution annotations](https://github.com/Alab-NII/onecommon/tree/master/aaai2020) provide object-level reference interpretations, speaker views and dialogue histories. [CoDraw](https://github.com/facebookresearch/CoDraw) provides a target scene, wording and successive drawings. [Minecraft collaborative dialogue](https://aclanthology.org/P19-1537/) provides a target construction, instructions and building actions. OneCommon was selected for its independent human reference judgements and explicit spatial referents, not for its eventual model scores.

Primary paper: Udagawa & Aizawa (2020), *An Annotated Corpus of Reference Resolution for Interpreting Common Grounding*, [DOI 10.1609/aaai.v34i05.6442](https://doi.org/10.1609/aaai.v34i05.6442), [author manuscript](https://arxiv.org/html/1911.07588). It describes interpretations of referents, annotations of ambiguity, successful-dialogue selection, and access to context during annotation. This is evidence about a component of meaning, not direct measurement of all private intent. We use the pinned repository version, which need not have exactly the same markable totals as the paper's earlier version.

[source_manifest.json](source_manifest.json) pins commit `19125f2edc38c20341bfbb1756154aacdaa4f149`, tree `64c789cd8551315729e6725a0ff9061fdb580108`, all input URLs, Git blob hashes and SHA256 hashes. Files were checked against the resolved commit's actual tree. The initial branch-name tree response returned a different SHA; the downloader resolved the commit and verified each file instead of treating that response as a correct tree identity. No original conversation text, participant/annotator identifiers or raw archives are republished. No explicit dataset redistribution license was found in the repository inventory; the package contains code, aggregate results and transformed numeric records, not a mirror of the dataset.

## Meaning and expression are measured differently

* **Reference interpretation:** human annotators select the visible entities referred to by a minimal noun phrase. Aggregate labels are interpretations, not readings of a participant's mind. Majority/consensus can still be wrong.
* **Expression:** the actual reference phrase in the authors' spelling/grammar-normalized dialogue. It is not an unedited record of spelling variation. Full sentences can contain distinctions that a noun-phrase referent set does not encode.
* **Interaction and time:** original message speaker order and send timestamps, linked to the annotated lines. Same-speaker trajectories retain that speaker's view; cross-speaker overlap uses underlying object IDs rather than comparing differently shifted screen coordinates.
* **Interpretation agreement:** proportion of worker pairs that select exactly the same referent set, with unidentifiable judgements counted as disagreements. This measures agreement among annotators, not demonstrated understanding by the conversational partner.

For example, the fixed-hash inspection sample contains “top one” followed by “it”, and “two black dots” followed by “those two”, with the same annotated objects. Such references can remain stable while words change. This does **not** prove equality of full meaning, descriptive content or social force: the pronoun needs prior context. These eight quoted words are from the pinned corpus; the rest of the inspection is summarized without reproducing dialogue.

## Exact equations and explicit observation assumptions

The mathematical source remains the user's corrected corpus, SHA256 `01f9ab0942f9c88982863e2ffc1e3c495786b5e6b67a26ae77d18235e7058acf`. See the [exact extracted paragraphs](../community-mimesis/corpus_extract.json) and [earlier traceability audit](../community-mimesis/CORPUS_AUDIT.md). The imported, previously checked [single-case solver](../community-full-field/field.py) has SHA256 `00b50a93ae413d46109327ccf0c08e8e07d00028313eaa0da87d765e58705f35`. Batched trajectories are tested against it. Batching is computational scheduling, not an extra physical dimension.

| Corpus relation | New implementation | Added measurement or numerical assumption |
|---|---|---|
| P229/P549: momentum, pressure, div(u)=0 | `BatchField.terms/project/step` | Periodic 2D unit domain; latent u0=0; fixed e=(1,0) |
| P230/P548: f=-(sigma/rho)a(abs(grad S)-Gamma)e | `BatchField.terms`, imported activation | Actual referent positions become a chosen smooth field; coefficients selected only on training data |
| P261–264: distinct sharp/tanh/exact-off responses | Imported `activation` | Sharp primary; alternatives evaluated without refitting; no norm regularization silently introduced |
| P517: scalar transport with K_h*kappa*A | `BatchField.terms` | One unit mass per distinct annotated referent; h=.12 and a fixed initial-centroid source |
| P518–519: accumulated input, no forgetting | `BatchField.step`, analytic mass fit | U is proposed annotation-recoverability utility, gamma=1; A0=0 at first included utterance |
| P545: symmetric stress | Diagnostics | mu0=mu=rho*nu; stress is computed, not observed |

Length is one chosen unit of 430 source position coordinates; time is one measured minute. S has referent-count per unit area; K has inverse area; the integral is a referent count. Nu and D have squared-domain-length/minute. Gamma and epsilon have S/length units. U is dimensionless agreement; gamma sets the storage units and kappa converts stored input to count/minute. No measured human fluid density, force or pressure is asserted.

The source's full Cartesian initial field is not reconstructed; measured reference-density initial conditions and latent zero velocity define a new explicit initial-value test of the same governing equations. This is not a claim that every equation in the corpus (including the separate W consistency or action-boundary optimization rules) has a supplied connection to this field.

## Comparison limits that materially affect interpretation

The field predictor runs through both intervals without resetting its state. The initial-field control uses the same initial spatial observation. The last-observation control gets the middle spatial observation for its second prediction; that is an information advantage over the open-loop field, although the field receives that observation's agreement score as its next input. Report both controls rather than calling this one interchangeable comparison.

Annotation authors had whole-dialogue context; current-state annotations may therefore contain information inferred from later utterances. This is a retrospective oracle-state test, not a real-time natural-language system. It does not demonstrate that the model itself understands the wording. Whole-scenario splitting avoids sharing a repeated visual scenario between train and evaluation. Bootstrap intervals cluster by dialogue/scenario, but repeated workers or annotators can introduce residual dependence.

The periodized geometry, kernel width, zero initial velocity, utility proxy, fixed source and coefficient search range are explicit hypotheses. Predictions can fail because of these choices, because the dynamics are inadequate, or both. There are still no observed social velocity, pressure, physical boundary fluxes, personal utility or actual moderation decisions. Agreement among annotators does not establish semantic equivalence, fairness, causal wording effects, penalty memory, rivalry or literal fluid dynamics in people.

The numerical scheme uses a 2/3 Fourier cutoff for quadratic advection and RK4 time integration. Non-polynomial activation is sampled on the grid and is not exactly dealiased by that cutoff; grid refinement checks the resulting numerical error. All input/source kernels are normalized on their respective grids. No clipping of the signed field, decaying memory, logistic outcome law or velocity-aligned drag was added.

During schema inspection, automatically generated aggregate annotations were found to omit optional ambiguity fields. The extractor treats absent flags as false and still requires three actual worker judgements for primary inclusion. This correction did not change the frozen inclusion rule or use outcome scores.
