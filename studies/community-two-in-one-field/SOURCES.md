# Sources and measurement coverage

## Author equations

Plain_Language_Corpus_Math_and_Logic_Corrected.docx, supplied by the user. SHA256 01f9ab0942f9c88982863e2ffc1e3c495786b5e6b67a26ae77d18235e7058acf, checked against the original file for this study. Paragraph numbering follows the existing extraction including table text. Exact excerpts and implementation links are in corpus_trace.json. The original document is not republished here.

## Downloaded real measurements

Su, H., Li, X., Born, S., et al. (2025). Neural dynamics of spontaneous memory recall and future thinking in the continuous flow of thoughts. Nature Communications 16, 6433. [Article](https://doi.org/10.1038/s41467-025-61807-w). [Author repository](https://github.com/Lee-Memory-Cognition-Lab/thinkaloud_paper/tree/e8005a84122e208f1607064d897763d6cbddf25a). [Zenodo release](https://doi.org/10.5281/zenodo.15665444).

All 118 transcript spreadsheets, 118 numerical embedding files, participant metadata, the authors' behavioral notebook and README were retrieved at pinned commit e8005a84122e208f1607064d897763d6cbddf25a. The 239 files total 64,849,333 bytes. Every download was checked against its Git blob hash and recorded with SHA256 in source_manifest.json. The original notebook was read as source material, not executed. Only aggregate and per-file numeric coverage records are published. Raw narratives, demographics and embedding vectors remain outside this package.

The Zenodo API resolves the concept record to release record 15682059, version v1.0.1, with CC BY 4.0 metadata. The analysis here is a new coverage audit; it does not reproduce or challenge the paper's fMRI results. Its thoughtID grouping follows the authors' notebook. Session duration is calculated from the first and last available transcript timestamps, not assumed to equal exactly 600 seconds.

Zhang, M., Liu, P. R., Su, H., et al. (2026). An fMRI dataset of verbalized spontaneous thought with annotated transcripts and self-report trait measures. [Scientific Data](https://doi.org/10.1038/s41597-026-08414-6), early publication dated 29 September 2026. [OSF behavioral archive](https://osf.io/a56rm/). The archive's folder metadata were inspected. This extension contains finer timestamps, model-generated content ratings with human validation, and post-scan questionnaires. These are the same cohort, not an independent replication. The new ratings were not downloaded or used as utility input. An outside rating of emotional language does not by itself measure the person's inward listener or perceived balance.

## Additional sources screened

| Source | Useful measurements or method | Remaining limit for this model |
| --- | --- | --- |
| [Hurlburt and Heavey's DES codebook](https://hurlburt.faculty.unlv.edu/codebook.html) and [published repeated interviews](https://hurlburt.faculty.unlv.edu/ieo/ryan/ryan_sampling.html) | Descriptions of particular inward experiences and distinctions between speaking and hearing, with contextual clarification across sampling days | Sparse samples and interview times do not reconstruct continuous internal velocity or prehistory; inner hearing is not automatically the project's receptive Clay function |
| [Inner Life smartphone study](https://pmc.ncbi.nlm.nih.gov/articles/PMC4410513/) | Repeated reports of varieties of inner speech | Survey endorsements do not provide separate role dynamics or a measured semantic field; no participant records downloaded in this turn |
| [Nedergaard, Skewes and Wallentin inner-speech study](https://doi.org/10.1037/xhp0001112) | Previously downloaded within-person reports during an attention task | The earlier 0.2134 history-prediction result is a statistical comparator, not a fit of these PDEs |
| [Thinking out loud EEG dataset](https://doi.org/10.1038/s41597-022-01147-2) | Neural recordings for controlled imagined speech commands | Fixed commands do not supply the person's evolving idea, meaning and history |

SciSpace was used to discover literature, followed by primary articles and author-hosted data. A search result or a language model's summary was not treated as a measurement. The search found useful partial sources, not a verified dataset that already measures the complete author-defined two-in-one.

## Source issues retained

Named columns, not fixed positions, are used. One source file swaps category/topic order; two have extra unnamed columns, with eight populated text cells altogether. The initial schema check exposed these differences, and the parser was amended to report them. The extra fragments were not silently merged into timed sentences because no independent timestamps were assigned to them. The audit counts the source's named transcript and thought fields. Semantic-content analysis would need reconciliation of those eight fragments with the source before relying on completeness. No source text is quoted in the published results.
