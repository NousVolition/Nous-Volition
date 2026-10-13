# Substance interactions and equation tests

Earlier completed work from the same research chat, now published in **Streams and Rocks**. This collection preserves the numerical data, figures, tests, conditions, references and explicit limitations. It complements [the switching and memory study](../mechanisms-switching-memory/README.md).

## Transport, kinetics and surface-data extensions

**[Read the six-item extension and evidence audit](advanced_tests/README.md)** or [open its illustrated report](advanced_tests/report.html). This batch adds 34 passing unit tests, 44 saved-result audits, resolved liquid diffusion, published reversible CO₂ kinetics, specific VOC surface data and a falling-droplet capture candidate. Across 18 measured settings, central capture predictions are 9–32% low rather than the earlier factors of 40–447 low. Finite-Reynolds-number flow and material-specific evidence are still needed before smoke validation.

The peroxide source fails a table-versus-figure audit, so its conditional curves are not accepted predictions. Matched fog uptake/evaporation validation, measured smoke charge distributions, sorption-aging rates and coalescence remain open. See the [six-item evidence register](advanced_tests/evidence_gaps.csv) and [methods](advanced_tests/METHODS.md).

The three substance batches now contain 137 unit tests, plus 8 historical water-data checks. Only the new 34 unit tests and 44 saved-result audits were run for this extension; older test counts remain historical.

## Completed follow-up tests

**[Evaporation, polarization and published capture measurements](followup_tests/README.md)** adds 29 passing unit tests, 108 main fog scenarios, 21,504 main Brownian paths, step refinements and 18 published measurement comparisons. Evaporating fog releases part of previously absorbed gas; the conducting-sphere model adds charged-neutral polarization attraction. The old diffusion-only capture kernel underpredicts the tested falling-droplet measurements by factors 40–447, exposing a model limitation.

[Read the full methods and remaining tests](followup_tests/METHODS.md), [inspect the 11 supplementary interaction cases](followup_tests/interaction_updates.csv), or [open the family/community guide](followup_tests/COMMUNITY.md). The guide proposes Water, Fog, Mist, Gas, Smoke, Clay and Ice roles and connects to the existing SIMS community work. A family-specific extension has not yet been simulated.

The counts below describe the earlier packages. That batch brought the substance collection to 103 unit tests, plus the earlier 8 saved-data checks; they do not turn the failed empirical capture comparison into a validation success.

## Start reading

| Study | Completed checks | Open |
| --- | --- | --- |
| Substance interactions | 27 unit tests; 114 matrix rows with separate evidence statuses | [Illustrated report](research_report.html), [interaction matrix](interaction_matrix.csv), [reproduction guide](README.txt) |
| Five equations and gas/fog transport | 20 equation tests + 8 transport tests; 12 saved transport runs | [Equation study](equation_tests/README.md) |
| Stability, energy, forces and water-figure audit | 19 unit tests + 8 separate saved-data consistency checks | [Stability study](stability_tests/README.md) |

**74 unit tests and 8 data-consistency checks** belong to these earlier packages. The separately published switching study has its own 18 tests and 168 seeded runs. Numerical verification is not environmental or experimental validation.

GitHub renders this README and the figures below. Download the repository to open the HTML reports in a browser; the GitHub file viewer shows HTML source.

## What the substance study actually ran

The 114-row matrix covers CO, CO₂, liquid water, vapor, fog, mist, ice, smoke, air, nitrogen, oxygen, acetone, isoprene and hydrogen peroxide. Fog/mist are droplets in air, and smoke is a heterogeneous aerosol plus gases. The labels overlap; they are not fourteen independent thermodynamic phases.

The completed calculations include 21 gas/liquid partition cases; two carbonate equilibrium solves; a reduced CO + OH kinetic benchmark; conservative 2-D prescribed-flow transport and refinement; 7,680 Brownian charged/neutral particle-pair trajectories; 28 vapor/interface cases; nine acetone/ice adsorption cases; and analytic scavenging, agglomeration, freezing and melting comparisons. **Not every matrix row was simulated**: evidence statuses identify numerical runs, analytic results, literature assessments and unavailable surface rates.

![Gas and water partitioning](results/partitioning.png)

At 25 °C and 1 atm in the specified closed 1 m³ gas/fog scenario containing 0.5 g liquid water, the calculated aqueous CO inventory at equilibrium is about 0.00000120% of total CO. This is weak physical dissolution, not conversion to CO₂. The separate unbuffered CO₂/bulk-water calculation gives pH 5.59465 under its stated inventory and alkalinity assumptions. These are scenario results, not drinking-water or exposure predictions.

![Charged droplet controls](results/charged_droplets.png)

Like-charge Coulomb motion is distinguished from neutral Brownian spreading and drag/transport. Opposite-charge cases stop before excluded near-contact physics becomes important. The chemical benchmark requires an explicit OH inventory and evaluated rate. No CO/water reaction is inferred from mixing. H₂O₂ catalytic decomposition remains a literature assessment, not a newly calibrated catalytic-rate simulation.

## Equations are supporting models with defined quantities

[Five equations](equation_tests/README.md) tests a limit cycle, Josephson/pendulum dynamics, clock alignment, saddle-node scaling and the harmonic oscillator. A constructed one-way coupling uses their signals to prescribe a divergence-free carrier flow. That transport benchmark preserves molecular identity and inventories; its chosen gains and timescales are not measured chemical or hardware connections.

[Stability and energy](stability_tests/README.md) adds nonlinear spirals, the corrected forward-time return map, population equilibria, conservative/damped dynamics, time reversal and direct gas-transfer/Coulomb checks. The water figures are reanalyses of bundled existing outputs; they are not new quantum chemistry or molecular-dynamics runs.

## Reproduce and inspect

Each package has its own pinned requirements and README.txt. Use Python 3.12 in a fresh environment. For the substance study, from this directory:

```text
python -m pip install -r requirements.txt
python -m unittest -v test_models.py
python run_study.py
python build_report.py
```

Use the separate instructions inside `equation_tests` and `stability_tests` for those supplements. Run them from their own directories so their local modules and logs resolve correctly. No network is required after dependency installation.

- [Saved numerical summary](results/summary.json), [configuration](config.json), [reference constants](references.json).
- [Publication verification](publication_verification.json), [publication record](publication.json), [original file hashes](source_hashes.json), [published file hashes](publication_manifest.json).
- Original test logs and numerical run logs are retained. Fresh publication-check logs are in `verification`.

All files are published individually. Duplicate ZIP bundles, installed environments and caches are omitted. The source manifest for the older water snapshot identifies its prior project; that is provenance, not this publication's destination.

## Limits

The carrier velocity is prescribed; these models do not solve a new Navier–Stokes law. Assumed geometry, diffusivities, transfer coefficients, sticking and surface laws remain explicit. Smoke is a surrogate where modeled. No complete atmospheric mechanism, collective charged cloud, turbulence, calibrated near-contact coalescence or general liquid-water quantum prediction is claimed. Calculations used no physical CO/smoke generation, vapor exposure or smell tests.

[Streams and Rocks](../../README.md) · [Switching and memory](../mechanisms-switching-memory/README.md)
