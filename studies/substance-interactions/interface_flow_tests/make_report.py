"""Build the human-readable report directly from saved numerical results."""
from pathlib import Path
import json, html

P=Path(__file__).resolve().parent


def table(rows,columns):
    head=''.join('<th>'+html.escape(label)+'</th>' for key,label in columns)
    body=[]
    for row in rows:
        cells=[]
        for key,label in columns:
            value=row.get(key,'')
            if isinstance(value,float):value=f'{value:.4g}'
            cells.append('<td>'+html.escape(str(value))+'</td>')
        body.append('<tr>'+''.join(cells)+'</tr>')
    return '<div class="tablewrap"><table><thead><tr>'+head+'</tr></thead><tbody>'+''.join(body)+'</tbody></table></div>'


def main():
    r=json.loads((P/'results.json').read_text());w=r['water'];f=r['flow'];a=w['aggregate']
    verify=json.loads((P/'runtime_verification.json').read_text())
    audit=json.loads((P/'saved_data_audit.json').read_text())
    sources=json.loads((P/'source_audit.json').read_text())['sources']
    terminal=f['terminal'];v=terminal.get('predicted_speed_m_s')
    speed=f'{v:.2f} m/s' if v is not None else 'not bracketed'
    gamma=f"{a['gamma_mean_mN_m']:.2f} ± {a['seed_t95_halfwidth_mN_m']:.2f} mN/m"
    cols=[('name','Run'),('gamma_mN_m','Surface tension, mN/m'),('mean_temperature_K','Mean T, K'),('production_ps','Production, ps'),('gamma_first300_mN_m','First 300 ps'),('gamma_strain002_mN_m','Double area strain')]
    flowcols=[('name','Run'),('status','Status'),('Re','Re'),('D_cells','Cells / D'),('Cd_mean','Mean drag coefficient'),('Cd_first_window','First averaging half'),('Cd_last_window','Second averaging half')]
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Water interfaces and large-drop flow — completed pilot</title>
<style>body{{font:17px/1.65 system-ui,sans-serif;color:#192b37;background:#f5f7f8;margin:0}}main{{max-width:1150px;margin:auto;padding:42px 24px 80px}}h1{{font-size:42px;line-height:1.15;max-width:850px}}h2{{margin-top:44px;color:#165d72}}h3{{color:#165d72}}a{{color:#075f93}}.intro{{font-size:21px;max-width:950px}}.card{{background:white;border:1px solid #dce4e8;border-left:5px solid #237f95;border-radius:7px;padding:18px 22px;margin:24px 0}}.caution{{border-left-color:#ae702f}}img{{width:100%;height:auto;background:white;margin:12px 0}}table{{border-collapse:collapse;background:white;font-size:14px;min-width:650px;width:100%}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #dce4e8}}th{{background:#e7f0f3}}.tablewrap{{overflow-x:auto}}code{{font-size:14px}}.small{{font-size:14px;color:#50616b}}li{{margin:9px 0}}footer{{border-top:1px solid #ccd8de;margin-top:40px;padding-top:20px}}</style>
<main><p class="small">STREAMS AND ROCKS · COMPUTATIONAL SUBSTANCE STUDY · 17 OCTOBER 2026</p>
<h1>Water interfaces and the air around large drops</h1>
<p class="intro">Completed molecular simulations and three-dimensional flow calculations, with new published measurement comparisons. These two studies resolve different scales and have separate evidence limits. The molecular calculation does not supply viscosity or shape to the flow model.</p>
<div class="card"><strong>What the runs found</strong><p>The three primary water seeds give <strong>{gamma}</strong> (approximate 95% interval from three seed means), compared with <strong>71.92–71.93 mN/m</strong> in the selected measurements. The difference of central estimates is <strong>{a['difference_mN_m']:+.2f} mN/m</strong>. This interval covers sampling only, not all model errors. The 100 ps block estimate of the standard error is {a["block100_SE_assuming_independent_blocks_mN_m"]:.2f} mN/m if blocks are independent; residual correlation can make that estimate too small.</p>
<p>The fixed oblate-body flow calculation gives a conditional terminal speed of <strong>{speed}</strong> for a volume-equivalent 2.5 mm body. The new study reports approximately <strong>7.8 m/s</strong> by DVS and <strong>6.4 m/s</strong> by PARSIVEL. The shape, interface mobility, airflow and numerical resolution remain important limitations; the drag result is not a validated falling-liquid-drop prediction.</p></div>
<img src="figures/comparisons.png" alt="Computed surface tension and conditional falling speed compared with new published measurements"><p class="small">Error bars have different meanings, stated in the plot: water simulation sampling interval; water measurement comparison uncertainty; DVS combined instrument uncertainty. A missing bar does not mean zero uncertainty.</p><h2>1. Water: actual liquid–vapor interfaces</h2>
<p>OpenMM integrates rigid TIP4P/2005 molecules at a thermostat setting of 298.15 K. Three independent starts each contain 501 water molecules in a 2.5 × 2.5 × 8 nm periodic cell and have 1,000 ps production after 100 ps bulk and 200 ps slab equilibration. The two additional controls use a 1 fs step and a 3 nm lateral cell, each with 300 ps production. Continuations are grouped with their original seed. There is no atmospheric gas, imposed 1 atm slab pressure, solute, bond breaking or chemical reaction in these runs.</p>
<img src="figures/water.png" alt="Block surface tensions, slab density, topological distance distribution and a saved water configuration">
{table(w['summary'],cols)}
<p>Surface tension is the free-energy cost of changing area at fixed volume: ΔF = −RT log⟨exp(−ΔU/RT)⟩. Molecular centers move while bonds remain rigid. With two interfaces, γ = (ΔF<sub>+</sub> − ΔF<sub>−</sub>)/(4Aε), with energy/area converted to mN/m. Both ±0.1% and ±0.2% area perturbations are evaluated from the same frames. Their differences are a numerical sensitivity, not a fitted correction.</p>
<p>Finite-size and time-step comparisons use the first 300 ps of the primary cases as a duration-matched reference; the longer primary results are also retained. The 50, 100 and 200 ps block spreads, first/last halves and three-seed variation are available in the CSV files. A few short trajectories cannot establish a precise converged interfacial free energy. Three-dimensional PME periodic-image effects and the LJPME dispersion treatment remain part of the model specification.</p>
{table(w['controls'],[('name','Control'),('gamma_mN_m','Surface tension, mN/m'),('matched_primary300_mean_mN_m','Primary mean over matching 300 ps'),('difference_mN_m','Difference, mN/m'),('difference_percent','Difference, %')])}
<p>Each control is a single short trajectory; its difference cannot cleanly separate numerical bias from sampling noise. Increasing the lateral size also adds water and increases liquid-film thickness. These controls do not yet establish a converged infinite-system result.</p>
<h3>The fourth topological neighbor at the surface</h3>
<p>The full hydrogen-bond network is constructed before any surface grouping. ψ is the smallest oxygen distance to a molecule whose shortest hydrogen-bond path has exactly four links. Below 5 Å is labelled “HDL-like”; otherwise “LDL-like”. A missing fourth shell is unclassified. HDL and LDL refer to high-density and low-density liquid; here they are labels assigned by the distance threshold. They are not different substances or proof of separate liquid phases. Each group's fractions below are descriptive pooled molecule-frames, not independent molecular replicates.</p>
{table([x for x in w['structure'] if x['name'].startswith('primary') and x['layer']!='other'],[('name','Seed'),('layer','Planar group'),('HDL_fraction_classified','HDL-like fraction'),('coverage','Classifiable fraction'),('unclassified','Unclassified molecule-frames')])}
<p>Bulk means |z| &lt; 0.5 nm from the recentered slab middle. Interface means within 0.25 nm of the fitted half-density position on either side. These are <strong>planar groups, not intrinsic ITIM surface layers</strong>. All stored analysis frames are spaced 20 ps apart. Surface tension measurements do not validate these particular ψ populations; no matching direct experimental population measurement was found.</p>
<h3>New water measurements and independence</h3>
<p><a href="https://doi.org/10.1021/acs.jpcb.5b00545">Vinš et al. (2015)</a>, Tables 1–2, supplies every row within 0.3 K of the chosen thermostat: 25.23, 25.22 and 25.22 °C. The tables were inspected visually. Their absolute tensions inherit an IAPWS calibration reference, with reported uncertainty around 0.36–0.41 mN/m; the plotted ±0.4 band is a comparison guide. The three rows share calibration and are not three independent experiments. The simulation's mean kinetic temperatures are reported above; no correction was fitted to erase a difference.</p>
<h2>2. Large-drop flow: external air resolved in three dimensions</h2>
<p>The GPU solver advances a D3Q19 lattice-Boltzmann flow around a <strong>fixed, no-slip spheroid</strong>. The main volume-equivalent Reynolds numbers are 1,500 and 2,500, with axis ratio 0.7. A sphere, axis ratio 0.84, finer grid, wider/longer domain, half lattice speed, different perturbation seed and zero subgrid-viscosity cases test assumptions. The main grids have 20 or 28 cells across D. The requested duration is 40 D/U; completed-run means use the final half. At the 2.5 mm comparison conditions, the complete run spans only about 13–16 ms; longer wake averaging remains necessary.</p>
<img src="figures/flow.png" alt="Computed wakes behind oblate bodies, force histories and numerical sensitivities">
<p class="small">The wake images are actual time-averaged central slices. Curves are streamlines of that mean slice, not full particle trajectories. The force plot starts at tU/D = 5 to show later dynamics; all initial startup impulses, including negative transients, remain in the saved histories.</p>
{table(f['summary'],flowcols)}
<p>The projected area is π(D/2)<sup>2</sup> a<sup>−2/3</sup>, where a is the streamwise/transverse axis ratio and D is volume-equivalent diameter. Drag uses this area, not the sphere area. Air properties used for physical comparisons are explicit assumptions: density 1.204 kg/m³ and kinematic viscosity 1.5 × 10<sup>−5</sup> m²/s; water density 998.2 kg/m³ and gravity 9.80665 m/s². The 2.5 mm comparisons have Reynolds numbers around 1,067 and 1,300. Re = 2,500 can instead represent, for example, D = 4.5 mm at 8.33 m/s under the same viscosity; that case has no matched new measurement here.</p>
{table(f['sensitivity'],[('base','Reference'),('change','Control'),('relative_Cd_change_percent','Drag change, %')])}
<p>A change with grid, domain or elapsed time is numerical uncertainty, not experimental evidence. The 20→28 cell comparison is only two grids; it does not establish an asymptotic convergence order. Mean-drag time variability is not an independent-sample confidence interval. Regularization and a fixed Cs = 0.1 viscosity closure stabilize unresolved scales; this is not a fully resolved turbulence calculation. The transverse boundaries are periodic, so the wider-domain control matters.</p>
<p><strong>Failed control retained:</strong> at Re = 1,500 with Cs = 0, the density guard stopped the coarse run at tU/D = 25.8 (minimum density 0.796). Its partial force averages are diagnostic only and are excluded from physical drag comparisons. Numerical stability with Cs = 0.1 does not by itself establish correct turbulence or drag.</p>
<h3>New falling-drop measurements</h3>
<p><a href="https://doi.org/10.5194/amt-17-335-2024">Micev et al. (2024)</a> reports actual DVS and PARSIVEL measurements. Its approximately 7.8 and 6.4 m/s values are retained separately. The paper's 7.4 m/s “ground truth” comes from an older model and is <strong>not counted as new measured evidence</strong>. Figure 6, Figure 7 and Table 3 were checked visually. DVS has a reported combined velocity uncertainty of about 0.5 m/s; this is not a standard error of its mean. PARSIVEL used a different stairwell with wind, and its distribution has a slow tail.</p>
{table(f['comparisons'],[('name','Case'),('measured_speed_m_s','Reported speed, m/s'),('assumed_aspect','Assumed axis ratio'),('computed_Cd','Computed drag coefficient'),('terminal_still_air_required_Cd','Required if terminal in still air'),('drag_over_weight_minus_buoyancy','Computed drag / effective weight')])}
<p>These rows use the measured speed to set Reynolds number and then test conditional force balance. They are not independent predictions of that speed. Separately, solving force balance with the computed Cd(Re) curve gives <strong>{speed}</strong>, by interpolation between computed cases, without fitting to either measurement. This result still assumes a fixed shape and still air. Missing matched shape, relative airflow and precise thermodynamic conditions prevent attributing the discrepancy to any single mechanism.</p>
<div class="card caution"><strong>What this does not yet resolve</strong><p>A real liquid drop can deform, oscillate and circulate internally. A fixed no-slip wall does not reproduce that interface. These tests add resolved external-flow fields; they do not yet replace the earlier collection model, simulate smoke-particle capture, or validate collision/coalescence. Humidity-driven phoresis, particle trajectories and retention are not added to this particular flow solver.</p></div>
<h2>Checks, provenance and reproduction</h2>
<p>Analytical shear-wave decay, uniform flow, lattice symmetries, molecular pair energy, and rigid area changes test the implementation. The first shear-wave mass test exposed a float-accumulation error; the original failure and the conservative correction are preserved. Additional analytical tests check two-interface normalization and force balance. Saved-data checks audit every completed run, molecular geometry, finite fields, source hashes and descriptor totals. Passing these checks verifies the stated computation; it does not certify physical validity.</p>
<p>The short unthermostatted energy control is in <a href="nve_check.json">nve_check.json</a>. Production water runs exchange energy with a thermostat; the flow has open inlet/outlet boundaries. Neither production energy nor total open-domain mass is expected to be constant. Closed periodic mass conservation is tested separately. An independent <a href="boundary_budget.json">inlet/outlet budget control</a> also compares mass change against the mass supplied by the boundary rule; full boundary-population fluxes were not saved for the large production runs.</p>
<p><strong>Holdout status:</strong> these are new-to-project comparisons, not formally blinded model-selection holdouts. Measurement values were visible during implementation. No physical parameters were adjusted to match them. Any later model change informed by these outcomes must treat these data as development evidence and seek another independent test.</p>
<ul><li><a href="README.txt">Reproduction guide</a> and <a href="protocol.json">original protocol</a> / <a href="amendments.json">amendments</a></li>
<li><a href="results.json">Full numerical results</a>, <a href="water_summary.csv">water CSV</a>, <a href="flow_summary.csv">flow CSV</a>, <a href="measurements.csv">transcribed measurements</a></li>
<li><a href="runtime_verification.json">Runtime verification</a>, <a href="runtime_verification_initial.json">initial failure</a>, <a href="saved_data_audit.json">saved-data audit</a></li>
<li><a href="source_audit.json">Source eligibility and limitations</a>, <a href="manifest.json">file hashes</a></li></ul>
<h3>Primary references</h3><ul>'''
    for s in sources:
        page+=f'<li><a href="{html.escape(s["url"])}">{html.escape(s["id"])}</a> · DOI {html.escape(s["doi"])} · {html.escape(s["status"])}</li>'
    page+='</ul><footer>Completed on an RTX 3080 with OpenMM 8.6.1, CuPy 14.2.0 and Python. Molecular structure and continuum flow remain distinct scales. No new Navier–Stokes law is asserted.</footer></main></html>'
    (P/'report.html').write_text(page,encoding='utf-8')
    print('Report created')

if __name__=='__main__':main()
