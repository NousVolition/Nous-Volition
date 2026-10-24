# Two-in-one connection work: implementation accounting checkpoint

24 October 2026. **This is not a completed empirical test of the full two-in-one model.** The [register and added-rule inventory](REGISTER_AND_ADDED_RULES.md) answers which equations are implemented and exactly what was added. It records 20 numerical/assembly rules, 15 executed data-analysis rules and 8 proposed or unfinished choices.

The existing field solver implements the momentum, activation, gradient, transport/history and stress rows with declared approximations. The new analysis here does not invoke that solver. Smoke, Clay, the moving idea's forms and personal history have not been assigned validated numerical observation operators. A labelled input is not a separately evolved inward role.

## Completed real-data calculations

The [Lux et al. data archive, version10445890](https://zenodo.org/records/10445890) supplies ordered ratings for valence, self-relevance and temporal reference. These ratings do not directly measure intended meaning, experienced time, perceived balance or Clay. The original source's density-map predictor was not used. No simpler predictive estimator was substituted for the corpus model.

| Analysis | Observed squared distance | Shuffled expectation | Difference (bootstrap95% interval) |
|---|---:|---:|---|
| Adjacent ratings,117training people |0.259630|0.420058|0.160428 [0.149369,0.172973]|
| Adjacent ratings,49retest sessions |0.238025|0.385620|0.147595 [0.127789,0.166893]|
| Session means,49correct person pairs |0.015524|0.062111|0.046587 [0.029225,0.064008]|

All three one-sided permutation tests return p=.001 with999permutations, the smallest reportable value at that permutation count. No multiplicity adjustment was applied. These are secondary analyses of public records under a locally fixed specification, not an externally registered confirmatory study. The49first sessions in the paired analysis all overlap the117training people; retest is not an independent sample of49new people.

The selected records contain26,560complete rating vectors and25,896eligible within-chain adjacent pairs. Each sequence has four chains of40; between-chain links were excluded. The unused20source rows and selected indices remain traceable through [results](study1_results.json). The20rows were excluded by the archive's inherited training selection, not by a new outcome-based rule here.

The observations show order dependence under the specified within-chain exchangeability null and person-specific similarity across sessions. Task instructions, semantic association and response style remain alternative explanations. Neither result identifies a causal history mechanism, accumulated utility A or a field trajectory. Six [analysis unit tests](test_analysis.py) passed locally. No new measurement-driven PDE calculation has run at this checkpoint. Study2 has not been downloaded or tested.

## Source and implementation trail

- [Equation and added-rule inventory](REGISTER_AND_ADDED_RULES.md): all ten register rows, actual status, every substantive added rule in the inspected files, and omissions.
- [Protocol](PROTOCOL.md): written before opening numerical responses. It promised per-coordinate results that the current implementation has not produced. Bootstrap choices were fixed in code before execution but not enumerated in that prose protocol.
- [Analysis code](analyze.py), [per-person training metrics](study1_training_people.csv), [per-person retest metrics](study1_retest_people.csv), [paired-session distances](paired_sessions.csv).
- [Sources](sources.json): exact download URLs, hashes and license. Public data remain at the source; this package contains derived metrics and original analysis code.
- [Previous exact-equation audit](../community-chain-audit/README.md) and [register](../community-chain-audit/equation_register.csv).
- [Miro frame13: proposed shared field](https://miro.com/app/board/uXjVEXBJz3k=/?moveToWidget=3458764687916065203), [frame16: persistent history](https://miro.com/app/board/uXjVEXBJz3k=/?moveToWidget=3458764687918055185), [frame18: hidden states](https://miro.com/app/board/uXjVEXBJz3k=/?moveToWidget=3458764687918055187). These sections were refreshed. The fresh corpus document SHA256 still matches the previous audit. No source-board edit was made.

The proposed mapping S=normalized occupancy density and excess utility=valence is an assistant-added candidate for falsification, not a connection supplied by the corpus or user. Its mass contradiction must not be advertised as testing a validated two-in-one observation map. Form definitions remain the user's definitions; no new numeric form classification was performed.

## Reproduce this checkpoint

Python3.12 with NumPy and SciPy; recorded versions are in [provenance](provenance.json). From this directory:

```sh
python fetch.py --raw raw
python -m unittest discover -s . -p test_analysis.py
python analyze.py --raw raw --stage study1 --out reproduced
```

Compare `reproduced/study1_results.json` and the three CSVs with the saved values. The code preserves complete response vectors and participant/chain membership during permutation. It neither fills unknown biography with zero nor links separated sessions into a continuous observed history. The [full requested model test remains open](REGISTER_AND_ADDED_RULES.md#interpretive-connections-and-remaining-absence).
