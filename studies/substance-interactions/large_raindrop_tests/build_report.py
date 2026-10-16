from pathlib import Path
import json,csv,html
P=Path(__file__).resolve().parent
s=json.loads((P/'results/summary.json').read_text())
v=json.loads((P/'verification.json').read_text())
rows=list(csv.DictReader((P/'results/holdout_predictions.csv').open()))
tr=''.join(f"<tr><td>{r['long_axis_mm'][:4]}</td><td>{r['observable']}</td><td>{100*float(r['observed_E']):.1f}%</td><td>{100*float(r['predicted_E']):.2f}%</td><td>{1/float(r['ratio']):.2f}× low</td></tr>" for r in rows)
doc=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Large raindrops — revised model and new measurement test</title><style>
body{{font:17px/1.6 system-ui,sans-serif;max-width:1050px;margin:48px auto;padding:0 22px;color:#203343;background:#fafbfc}}
h1{{line-height:1.15;font-size:38px}}h2{{margin-top:42px}}.notice{{background:#fff0dd;padding:18px;border-left:5px solid #c47830}}
img{{width:100%;height:auto;background:white}}table{{border-collapse:collapse;width:100%;background:white}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #ccd4db}}
a{{color:#166489}}pre{{white-space:pre-wrap;font:14px/1.5 ui-monospace,monospace;background:#eef2f5;padding:22px}}.small{{font-size:14px;color:#526777}}
</style><body><p>STREAMS AND ROCKS · SUBSTANCE INTERACTIONS</p><h1>Better large-drop physics.<br>A new test still finds a large gap.</h1>
<p>The candidate adds particle inertia, finite-Reynolds-number collection correlations, wake capture within its published domain, ventilated heat balance, phoresis and size-distribution averaging. The physical model was frozen before extracting the new numerical outcomes.</p>
<div class="notice"><strong>Result: the new comparison does not validate the model.</strong> Four published averages are underpredicted by 5.08–14.62 times. The experiment used glycerol–water drops and coated silica, so this is a conditional transfer test. Pure-water/smoke validation remains open.</div>
<h2>What actually ran</h2><p>Four new aggregate efficiencies at two drop sizes; five additional speed diagnostics; eight earlier development rows at three distribution widths; 72 control/sensitivity records. All 12 unit tests and {v['checks']} saved-result checks pass. These checks verify the computation, not the material model.</p>
<img src="results/holdout.png" alt="Measured efficiencies exceed model predictions at both drop sizes">
<table><thead><tr><th>Long axis (mm)</th><th>Observable</th><th>Measured</th><th>Predicted</th><th>Discrepancy</th></tr></thead><tbody>{tr}</tbody></table>
<p class="small">Hong et al. (2025), section III p6. T=11±1°C; RH=56±2%; particles 1–5 µm. The primary calculation uses their arithmetic mean 2.92 µm as a monodisperse approximation. Therefore number and mass predictions coincide. Source aggregate uncertainties are unavailable; none is invented. All efficiencies use the source's projected-area convention.</p>
<h2>Where the previous model improved</h2><p>For the known 1.25 mm drop / 0.22 µm particle case, prediction changes from 0.00797% to 1.016%, versus measured 0.88–0.97%. Those observations helped identify the missing physics and are development data. Wider particle distributions strongly change the coarse-particle result; no width is selected because it gives a better fit.</p>
<img src="results/development.png" alt="Known measurements and old and new predictions, with distribution sensitivities">
<h2>Why the larger-drop test remains unresolved</h2><p>The new test has Reynolds numbers about 1466 and 2576. The published wake term supports only 20–800, so its larger-drop contribution is flagged as unresolved. The model also retains water properties rather than the experimental mixture, a spherical-flow approximation, unknown particle-size distribution and perfect sticking.</p>
<p>At nominal conditions, a scan over every particle size from 1 to 5 µm finds maximum model efficiencies of 6.87% and 23.86%. Every reported mean exceeds the corresponding maximum. Changing the size-distribution weights alone cannot close this gap within this fixed model.</p>
<img src="results/sensitivity.png" alt="Particle-size response and assumption sensitivity show the remaining disagreement">
<p>Distribution-grid refinement changed predictions by at most {v['max_distribution_refinement_relative']:.2g} relative. Exact analytic inventory bookkeeping conserves particles by construction. This is an algebraic closure, so no new random seeds or trajectory time steps are involved.</p>
<h2>Reproduce and inspect</h2><p><a href="README.txt">Full methods and source limitations</a> · <a href="frozen_protocol.json">Frozen protocol</a> · <a href="raindrop_model.py">Model</a> · <a href="holdout_measurements.csv">New measurements</a> · <a href="results/holdout_predictions.csv">Predictions</a> · <a href="verification.json">Verification</a></p>
<p><a href="https://doi.org/10.1063/5.0263346">Hong 2025 measurements</a> · <a href="https://doi.org/10.5194/acp-22-11381-2022">Jones 2022 correlations</a> · <a href="https://doi.org/10.5194/acp-21-6945-2021">Dépée 2021 forces</a></p>
<details><summary>Full reproducibility notes and source audit</summary><pre>{html.escape((P/'README.txt').read_text())}</pre></details>
<p class="small">Model SHA-256: {s['model_sha256']}. No coefficient was changed after the new outcomes were read. Target metadata and an abstract overview were available during screening; this was not a formally blinded experiment. Hong2025 is now development evidence for any future revision.</p></body></html>'''
(P/'report.html').write_text(doc,encoding='utf-8')
print('report.html written')
