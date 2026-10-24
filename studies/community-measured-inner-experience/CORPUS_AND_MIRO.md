# Exact corpus and Miro reconciliation

## Source versions inspected

- Corrected DOCX: `Plain_Language_Corpus_Math_and_Logic_Corrected.docx`; SHA256 `01f9ab0942f9c88982863e2ffc1e3c495786b5e6b67a26ae77d18235e7058acf`. Paragraph numbers below are zero-based in the existing 624-paragraph extraction. Its file hash was checked again in this work.
- Later PDF: `Plain Language Corpus _ Corrected Math and Logic.pdf`; SHA256 `ae1017c4224fb2b24799cc77c51f7657ad0b5fe62f24784c3ed1a85f8b6ae64c`. The 37-page visual contact sheet identifies a board export, not an automatically superseding equation manuscript. PDF pages 21 and 27 were inspected enlarged. Page 21 explicitly treats the shared S–u return path as proposed; page 27 derives persistent accumulated input and time weighting. This is a scoped reconciliation, not a claim that every graphic was transcribed or that the two documents are identical.
- Live [corpus board](https://miro.com/app/board/uXjVEXBJz3k=/): inspected frames `3458764687915993860` (connections) and `3458764687918055187` (identical readings and different states). The tool reported 39 managed items and 89 skipped/foreign items in that read; skipped material was not fully inspected. Literal searches for Smoke, Clay, two-in-one and D₂O returned no matches among 808 indexed items. Image-only content is not ruled out by a text search.
- Live [second board](https://miro.com/app/board/uXjVEW8HkiQ=/): literal searches for Smoke, Clay, two-in-one and history returned no matches among 541 indexed items; no claim of complete visual coverage.
- Live [research map](https://miro.com/app/board/uXjVEXlaw6E=/): searches returned material-Clay/history links. Inspected frame `3458764687905878576`, frame `3458764687905981992` and item `3458764687905806888` (25 managed, 10 skipped/foreign items). These map Burgers/material mechanics and study repositories; they do not specify a measured inward-listening variable. A material-clay implementation is not automatically the user's inward Clay.

## Equations retained without substitution

DOCX paragraphs 229–230:

```text
∂u/∂t + (u · ∇)u = −∇p + ν∇²u + f
∇ · u = 0
f = −(σ/ρ) a(q) eₖ
q = |∇S| − Γcrit
```

DOCX paragraphs 516–532:

```text
∂S/∂t + u · ∇S = D_diff ∇²S + Kₕ(x − x₀) J(t)
A(t) = ∫₀ᵗ γ[U(s) − Ubaseline] ds
J(t) = κ A(t)
∫ Kₕ dx = 1
```

S is the signed status/context field over a specified continuous embedding. It is not automatically Sens, word count, dialogue score, or an idea. A network alone does not define the derivatives. The corpus starts A(0)=0 at its declared origin. Moving that origin to a late observation session would silently discard history. At a session starting at t₀, the exact decomposition is A(t)=A(t₀)+∫ₜ₀ᵗγ[U(s)−Ubaseline]ds. A(t₀) must be identified or retained as uncertain, not fabricated. There is no added forgetting term.

DOCX paragraph 545 retains the stress relation:

```text
T = μ₀[∇u + (∇u)ᵀ], μ₀ > 0
```

The alternatives are a₀(q)=max(q,0); aₜ(q)=q[1+tanh(q/ε)]/2; and aε(q)=0 for q≤0, otherwise q exp[−(ε/q)²]. The signed tanh law must not be silently clipped. The original solver file is unchanged in this work (SHA256 `00b50a93ae413d46109327ccf0c08e8e07d00028313eaa0da87d765e58705f35`). It is not invoked on these data. The optional smooth gradient regularization in the corpus is also a declared alternative, not an inferred property of these observations.

DOCX paragraphs 104–107 also retain the separate consistency and boundary models: equal W outcomes for a declared same action/context, and maximize U over the specified feasible action set with exact margin m=ε. Replacing equality with m≥ε changes that model. The new datasets contain neither actual permission/restriction decisions nor a measured permitted-region boundary. Those equations were not tested here.

## What the Miro connections require

Sens (intended meaning), Sin (expression) and context remain distinct. A supplied text is an observed expression; its author's intended meaning needs independent evidence. A category grouping by research coders is useful evidence about content similarity, not proof that the person meant the same thing on two occasions.

The board separates a chosen utility model, permitted region, treatment decision and evidence. Its operational arrows are proposed mappings. It also warns that identical outputs can hide different states. Consequently, fitting a dialogue score does not by itself distinguish inward proposing, receiving and reshaping.

Smoke, Clay and idea forms retain the user's definitions within one person. There is no reassignment to two people, no fake speaker/listener coordinates and no imposed relation such as Clay = evaluative score. Combining the supplied component equations on a common domain is still a modeling specification; it is not itself an empirically identified inward system.

## What can make an empirical run possible

Not every field value must be directly observed. A specified observation operator with justified error, identifiable latent-state/parameter inference, known or inferred initial/prehistory conditions and an independently scored future measurement could test the full model. At present these new records lack that identified bridge. This is a limitation of this attempted test, not a proof that the theory is false or forever untestable.
