# A fresh measurement test: model frozen, matching data still needed

15 October 2026. No new experimental validation is claimed by this package.

The previous 18 collection measurements helped us decide to replace a diffusion-only approximation with a falling-droplet model. Although we did not fit coefficients to those observations, they influenced model selection. They are development checks, not an untouched final exam.

We can conduct a stronger test using measurements that did not influence that revision. Before the new literature search, `protocol.json` recorded the exact model hashes, eligibility criteria, sampling settings and comparison measures. The model remains unchanged. A local recorded freeze is not an independently registered or blinded experiment.

## What the search established

| Candidate | Why it was not used as a new matched test |
| --- | --- |
| [Dépée et al. 2021, Part I](https://doi.org/10.5194/acp-21-6945-2021) | The 18 humidity/size observations already used in development. A new random seed does not turn these into new measurements. |
| [Dépée et al. 2021, Part II](https://doi.org/10.5194/acp-21-6963-2021) | Already consulted for the charge model; its charged experiments also require electrostatic transport missing from the frozen neutral falling-droplet solver. |
| [Ladino et al. 2011](https://doi.org/10.1175/JAS-D-11-012.1) | Different aerosol material, lithium metaborate, and substantial droplet evaporation. The frozen phoresis code hardcodes sodium-fluorescein thermal conductivity and a constant droplet radius during an encounter. It is not a matched material/trajectory comparison. |
| [Ardon-Dryer et al. 2015](https://doi.org/10.5194/acp-15-9159-2015) | Polystyrene particles and ammonium-sulfate-containing droplets; residual droplet charge is reported. Material, evolving droplet conditions and charge differ from the frozen neutral model. |
| [Lemaitre et al. 2020](https://doi.org/10.3390/atmos11101028) | A potentially useful large-raindrop stress test. The available record concerns 2.5 mm drops, well outside the small-Reynolds-number flow approximation. Full matching numerical rows were not recovered during this search; it was not scored. |

The search has **not recovered an eligible, fully specified fresh measurement table**. No new measured-versus-predicted scores were computed. This is a documented data-eligibility result, not proof that suitable data do not exist. The publication years need not be recent: an older measurement can be new to model development.

## What would complete the test

Obtain a previously unused dataset giving measured collection efficiencies and uncertainty, wet particle size, droplet size, material, charge, air temperature, humidity and speed. Run the frozen version at those conditions without changing its physics or selecting rows by agreement. Retain every eligible result, including failures. The protocol states how to report sampling uncertainty and extrapolation.

If the available experiment requires adding different material properties, charge or evolving droplet dynamics, record that as a new model version and freeze it before evaluating its reserved outcomes. Once the results are used to make further changes, they become development data for that next version. A successful test covers only the tested materials and conditions; it does not validate every kind of smoke.

No experiment, exposure or message to an outside researcher was performed. Existing [advanced study results](../advanced_tests/README.md) are unchanged by this search.
