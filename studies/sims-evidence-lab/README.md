# SIMS evidence lab

Nine participants interact through a ring or star. An investigator named **Feynman** records predictions, compares claims with actions, presents the evidence, and revisits participants' responses over repeated rounds.

## Live site and first-load repair

**[Open the live SIMS model](https://sims-evidence-lab.itswaffles88.chatgpt.site/).** The October 17 update includes the model directly in each page, preserves existing saved settings, and bundles its display helpers. It no longer needs an embedded-frame startup or external script downloads.

The current live site's [portable source and browser pages](web/) are included. Open [web/dist/index.html](web/dist/index.html) locally, or rebuild and check startup from this collection folder:

```sh
python web/build.py
node web/tests/startup.cjs
```

All six public page routes passed fresh-visit checks without refreshing. The startup suite passed 48 checks covering saved/default state, corrupt or denied storage, direct rendering, and script syntax. The original participant algorithms and eight-round saved-run snapshot are unchanged. [Startup implementation notes](web/STARTUP.txt).

## Phone usability


The live pages provide larger tap targets, 16px form text, a numeric seed keyboard, single-column phone forms, and labeled scrolling regions for wide tables. The history keeps participant labels visible while scrolling. Claim weight also has a tap-to-open explanation. Zoom remains enabled.

All six routes were checked in Chromium viewports at 320×568, 375×812, 390×844, 430×932, and 844×390. Control checks cover all dropdown options, participants, stages, playback, sliders, trial seeds, checkboxes, persistence, and navigation. These are responsive browser checks; physical iPhone/Android touch devices and their browser engines have not been tested. The original model algorithms remain unchanged. See [mobile implementation notes](web/MOBILE.txt).

```sh
node web/tests/mobile.cjs
```

The mobile support suite passes 33 checks in addition to the 48 startup checks.

## Original standalone exports

Download this folder or clone the repository, then open a file from `site/` in a browser. Each exported HTML document includes its styling, controls, and simulation. GitHub's file view displays HTML source; download the file to run it. Browser storage remembers interactions when available.

**Start with [your latest saved run](site/latest-run.html)**: eight rounds, seed `20261011`, ring network, SIM 0 claiming majority and SIM 1 claiming opposition while both initially hold. The selected participant is SIM 1. This saved run contains no claim changes, behavior-rule changes, or promise-only responses across its eight rounds. The absence of a change can reflect the configured response policy or insufficiently distinguishing evidence.

| Model | Browser document | Editable source |
| --- | --- | --- |
| Network choices, holding and opposing | [Network](site/sims-network.html) | [Fragment](fragments/sims-network.html) |
| Predictions and claim support | [Claim testing](site/sims-claim-testing.html) | [Fragment](fragments/sims-claim-testing.html) |
| Evidence, participant reply and fresh actions | [Evidence and response](site/sims-evidence-and-response.html) | [Fragment](fragments/sims-evidence-and-response.html) |
| Repeated exchanges and promise history | [Repeated rounds](site/sims-repeated-rounds.html) | [Fragment](fragments/sims-repeated-rounds.html) |

In **Repeated rounds**, choose **Contrasting replies · controlled probes** to see the default five-round example: SIM 0 revises its claim, SIM 3 changes its behavior rule, and SIM 6 promises in every round while retaining its behavior rule. These outcomes follow the explicit, editable response policies. The unmodified demo starts at seed `20261008`; the saved-run document starts with the later settings above.

The history records changes from the previous round: **C** = claim, **B** = behavior rule, **C+B** = both, **P** = promise without a change to the unaligned behavior rule, **—** = no such change. Select a participant and round, then use **Read exchange** to see the evidence and reply. The behavior-rule column exposes simulator state; the investigator independently scores subsequent actions.

## Reproduce and edit

Python 3.10+ and Node.js 18+ are sufficient; no package installation is needed.

From this folder:

```sh
python tools/build.py
node tools/run-latest.cjs
node tools/run-repeated-rounds.cjs
node tools/run-evidence-response.cjs
```

`build.py` regenerates the four standalone documents and the latest-run document from the preserved fragments and [saved settings](snapshots/latest-run.json). Edit a fragment and rebuild to change a model. The standalone shell supplies local state storage; only `widgetState` and `setWidgetState` are used by the model fragments.

Saved numerical outputs:

- [Latest eight-round run](results/latest-run.json)
- [Five-round current/contrasting examples](results/repeated-round-examples.json)
- [Single-exchange examples](results/evidence-response-examples.json)

## Methods and provenance

Read [METHODS.md](METHODS.md) for decision rules, likelihood scoring, response thresholds, promise assessments, and differences between model versions. The investigator's name labels the procedure. Participant replies are generated by declared response rules. These are synthetic simulations with chosen assumptions.

The network mechanism extends the repository's [one-resisting-position study](../one-resisting-position/README.md), inspected at commit `ce3547bd03947bf893d13fb065df4d65f083c40f`. Browser runs use their own deterministic pseudorandom generator and preserve the source study's activation, refusal, and optional initiative parameters.

All five original fragments are retained. [The early Feynman-named copy](fragments/archive/sims-feynman-network.html) is byte-identical to `sims-network.html`; it is archived as an intermediate copy, not counted as an additional model. The substantive investigator models appear in the later versions.

[The file manifest](manifest.json) records SHA-256 hashes and sizes. Standalone export support in `assets/` and `tools/render.py` comes from the bundled Codex Visualize exporter, version `1.0.49`.

## Existing checks

[check-sims.cjs](tools/check-sims.cjs) and [check-claims.cjs](tools/check-claims.cjs) preserve the checks written earlier for the network and claim-testing models, with portable paths. They can be invoked with Node. They do not cover every later response or repeated-round feature.

The original October 15 publication built the standalone documents and generated the saved simulation outputs. On October 17, both existing model suites were rerun successfully: 960 network cases and 144 claim-testing cases, plus 2,096 probability contexts and 180,000 sampled actions. The browser interaction review and subsequent first-load repair are separate checks.
