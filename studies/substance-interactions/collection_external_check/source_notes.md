# Measurement provenance and eligibility

Retrieved 15 October 2026. The physical model was frozen in the preceding search; `protocol.json` and all three model files retain their original contents. `continuation_protocol.json` was written after source inspection, before predictions. This is a retrospective literature comparison, not a blinded test or independently registered protocol.

## Lemaitre et al. (2017): eight new outcome rows

[Experimental evidence of the rear capture of aerosol particles by raindrops](https://doi.org/10.5194/acp-17-4159-2017), Atmospheric Chemistry and Physics 17, 4159–4176. [Publisher PDF](https://acp.copernicus.org/articles/17/4159/2017/acp-17-4159-2017.pdf), CC BY 3.0. PDF SHA256: `6ec65ed19af4500f59a497ceea34f054e428009d35b51cb232203bcad46fc980`.

The eight rows were transcribed from Table 2 (printed p.4168, PDF p.10), checked against its rendered page, and retained in publication order. Figure 10 visually agrees with the reported collection-efficiency column, including row 6; that visual check is not an independent experiment. The two measurements at 0.25 micrometres aerodynamic diameter remain separate observations, but share a single predicted physical condition. Reusing the prediction does not double the simulated path count.

Diameter conversion uses the authors' Eq.11, physical diameter = 0.88 aerodynamic diameter. These are in-chamber particle sizes; no second hygroscopic growth multiplier is applied. The wet radius input is half that physical diameter. Drop diameter is 1.25 mm. The Fig.5 measurement near 1.25 mm gives approximately 4.7 m/s; its graph, not the model curve, sets this approximate input. We do not assign the graph reading spurious precision.

Table 2 reports RH 77 +/-5% and collection efficiency expanded relative uncertainty 16%; Appendix A uses expansion factor two. The separate RH sensitivity uses 72% and 82% as a conservative absolute-percentage-point bracket. No numerical temperature for these collection rows was recovered, despite the paper describing temperature measurement. We assume 20 C and test 15/25 C; these are assumed scenarios, not measured uncertainty bounds. Pressure is assumed 101325 Pa. Thus these rows fail the original fully specified eligibility criterion.

The source describes X-ray neutralization of particles and monitoring drops with a 10 fC detection limit. A neutralized population can still contain charged particles. Neither exact zero charges nor negligible image forces are established. The frozen calculation omits all electrostatics.

The measured efficiency is a mass-based ratio over a finite size distribution (number-size GSD up to 1.5). The simulation approximates that distribution by its median diameter and counts identical particles. It does not perform a mass-weighted distribution integral. The drops have finite-Re wakes and mild deformation, whereas the frozen field is a rigid no-slip sphere in creeping flow. These are material limitations, not numerical errors.

### Internal arithmetic check

Recompute the source Eq.8 using the source chamber height 1.3 m and both concentration columns: E = 2 D/(3 H) * concentration_drop / concentration_chamber. Seven rows agree with the E column to within 5%. Row 6 gives about 0.138 rather than 0.0029 (roughly 48 times larger). Both values are preserved in `results/source_audit.csv`; we cannot identify which entry is wrong without additional source information. The reported E remains visible and is simulated; row 6 is excluded from the seven-row aggregate by a decision recorded before predictions. This does not invalidate the other seven rows or prove that the underlying experiment failed. No correction was invented. No corrigendum was located in the targeted search.

### Independence from revision

These eight outcome values were not used to revise or fit the falling-droplet model. Searches of the existing advanced/followup code and provenance records found no stored use of this dataset. However, the papers share authors, apparatus history, material characterization and citations. This is new-to-our-model outcome evidence, not an independent laboratory replication or proof of complete isolation from the source's ideas. Any future model changes prompted by these results make these observations development data for that version.

## Other sources examined

* [Lemaitre et al. 2020](https://doi.org/10.3390/atmos11101028): recovered the full 19-page PDF and Table 1, inspected the table visually. It contains 23 rows with two particle diameters (0.49 and 0.30 micrometres), 2.5 mm drops, and nonzero drop surface charge in every listed row. Mean aerosol charge near zero does not establish zero charge for every aerosol. The 20 C mentioned in the text belongs to a separate PIV example at RH49%, not the collection table. These rows are not treated as neutral, fully specified collection holdouts. PDF SHA256 `f4b9464e0799eb4afb9a07c594adcab08a6b8c64ca8918e0c46b1aedcf577fef`. Public copy: https://mdpi-res.com/d_attachment/atmosphere/atmosphere-11-01028/article_deploy/atmosphere-11-01028.pdf . This resolves the previous search's inability to recover the full table.
* [Querel et al. 2014](https://doi.org/10.5194/amt-7-1321-2014): full paper recovered; reports 163 events, largely as plots. Chamber temperature is 21 +/-3 C, RH spans 23–80%, with 2/2.6 mm drops and measured speeds. Individual event rows with paired RH are not tabulated. We did not manufacture per-event conditions or mistake plotted theory for measurements. The material growth data from this research lineage already enter later papers; that is distinct from independently reserved collection outcomes.
* [Depee et al. 2021 I](https://doi.org/10.5194/acp-21-6945-2021) and [II](https://doi.org/10.5194/acp-21-6963-2021): already consulted; excluded as fresh outcomes.
* [Ladino et al. 2011](https://doi.org/10.1175/JAS-D-11-012.1): lithium metaborate and substantial evaporation; different material/geometry history.
* [Ardon-Dryer et al. 2015](https://doi.org/10.5194/acp-15-9159-2015): polystyrene, ammonium-sulfate droplets and residual charge; different material/charge conditions.
* [Xu et al. 2024](https://doi.org/10.1007/s41365-024-01401-9): new search candidate, publisher methods inspected. ZrO2 particles, nozzle sprays and mist agglomeration in a vessel; its calculated single-drop efficiencies are not direct single-drop measurements. Material and collective geometry do not match the frozen model. No values used to change it.
* [Hong et al. 2025](https://doi.org/10.1063/5.0263346): candidate identified, but a usable primary full text was not recovered in this search. No quantitative comparison or eligibility claim was made from a secondary preview.

No hazardous experiment, exposure or outside-author contact was performed. No raw observations were obtained from authors. Full papers are linked, not redistributed here.
