from pathlib import Path
import json,csv,sys,html,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_external import measurements,verify_model,nominal as inputs,phoretic_speeds,jobs
from uncertainty import flux_bounds
HERE=Path(__file__).resolve().parent
OUT=HERE/'results'

def main():
 verify_model()
 rows=measurements();cases=json.loads((OUT/'cases.json').read_text())
 meta=json.loads((OUT/'run_metadata.json').read_text())
 nominal=[x for x in cases if x['scenario']=='nominal']
 for r,tag,p in jobs(rows):
  z=next(x for x in cases if x['row']==r['row'] and x['scenario']==tag)
  v=phoretic_speeds(p['A'],p['a'],p['T'],p['RH'])
  ph=(v['vdf']+v['vth'])/p['U'] if p.get('phoresis',True) else 0.
  lo,hi=flux_bounds(z['hits'],z['paths'],p['bmax'],p['zmax'],ph)
  z.update(count_CI95_low=lo,count_CI95_high=hi)
 with (OUT/'sampling_bounds.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['row','scenario','hits','paths','mean_CE','count_CI95_low','count_CI95_high','censored_mean'],extrasaction='ignore')
  w.writeheader();w.writerows(cases)
 audit=[]
 for r in rows:
  e=2*(r['drop_diameter_mm']*.001)/(3*1.3)*r['fluo_drop_g_cm3']/r['fluo_chamber_g_cm3']
  audit.append(dict(row=r['row'],CE_reported=r['CE'],CE_from_concentrations=e,
                    reconstructed_over_reported=e/r['CE'],flag=r['flag']))
 with (OUT/'source_audit.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
 qualified=[x for x in nominal if x['row']!=6]
 ratios=np.array([x['predicted_over_observed'] for x in qualified])
 metrics=dict(qualified_rows=7,all_rows=8,unique_nominal_conditions=7,
   min_predicted_over_observed=float(min(ratios)),max_predicted_over_observed=float(max(ratios)),
   median_absolute_log10_ratio=(float(np.median(abs(np.log10(ratios)))) if np.all(ratios>0) else None),
   log_ratio_note='Undefined/infinite for zero point estimates; upper bounds reported separately.',
   Re_nominal=nominal[0]['Re'],nominal_hits=sum(x['hits'] for x in nominal if x['row']!=2),
   largest_censored_flux=max(x['censored_max'] for x in cases),
   matched_validation=False,model_unchanged=True)
 (OUT/'scores.json').write_text(json.dumps(metrics,indent=2,allow_nan=False))
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
 fig,ax=plt.subplots(1,2,figsize=(12,4.9),layout='constrained')
 for r,z in zip(rows,nominal):
  col='#b65339' if r['row']==6 else '#20628c'
  ax[0].errorbar(r['dphysical_um'],r['CE'],yerr=r['CE']*.16,fmt='o',color=col,capsize=3,
   label=('Reported experiment (±16%)' if r['row']==1 else 'Flagged source row 6' if r['row']==6 else None))
  if z['mean_CE']>0:
   ax[0].errorbar(r['dphysical_um'],z['mean_CE'],yerr=[[z['mean_CE']-z['count_CI95_low']],[z['count_CI95_high']-z['mean_CE']]],fmt='s',color='#222222',label='Model; conservative count interval' if r['row']==1 else None)
  else:
   ax[0].scatter(r['dphysical_um'],z['zero_hit_CE95_upper'],marker='v',color='#222222',label='Zero-hit 95% upper bound' if r['row']==1 else None)
  ax[0].annotate(str(r['row']),(r['dphysical_um'],r['CE']),xytext=(6,-12 if r['row']==1 else 7 if r['row']==2 else 4),textcoords='offset points',fontsize=8)
 ax[0].set(xscale='log',yscale='log',xlabel='Median physical aerosol diameter (µm)',ylabel='Collection efficiency (fraction)',title='Eight unused observations: conditional comparison')
 if nominal[0]['mean_CE']>0 and any(z['mean_CE']==0 for z in nominal):
  ax[0].scatter([],[],marker='v',color='#222222',label='Zero-hit one-sided 95% bound')
 ax[0].legend(fontsize=8,loc='lower right')
 tags=['nominal','dt_0.0125','dt_0.00625','long_time','wide_domain']
 for row,color in [(1,'#20628c'),(5,'#45945c'),(8,'#b65339')]:
  zs=[next(x for x in cases if x['row']==row and x['scenario']==tag) for tag in tags]
  vals=[x['mean_CE'] if x['mean_CE']>0 else x['zero_hit_CE95_upper'] for x in zs]
  ax[1].plot(range(len(tags)),vals,'o-',color=color,label=f'Row {row}: estimate or zero-hit bound')
  cens=[x['censored_mean'] for x in zs]
  ax[1].plot(range(len(tags)),cens,':',color=color,alpha=.7)
 ax[1].set_yscale('symlog',linthresh=1e-6)
 ax[1].set(ylabel='Collection efficiency / censored flux',title='Numerical checks; dotted = unresolved at stop')
 ax[1].set_xticks(range(len(tags)),['Base','Half dt','Quarter dt','Longer','Wider'],rotation=15)
 ax[1].legend(fontsize=8)
 fig.suptitle('Frozen creeping-flow model tested on 1.25 mm raindrops',fontsize=14)
 fig.savefig(OUT/'external_comparison.png',dpi=180);fig.savefig(OUT/'external_comparison.svg');plt.close(fig)
 # Each sensitivity plotted; no curve fitted to measurements.
 fig,axs=plt.subplots(1,3,figsize=(12,4.5),layout='constrained')
 for ax,row in zip(axs,[1,5,8]):
  zs=[x for x in cases if x['row']==row and (x['scenario']=='nominal' or x['scenario'].startswith(('T_','RH_','U_')))]
  for i,x in enumerate(zs):
   y=x['mean_CE'] if x['mean_CE']>0 else x['zero_hit_CE95_upper']
   ax.scatter(i,y,marker='o' if x['mean_CE']>0 else 'v',color='#20628c')
   if x['mean_CE']>0:
    ax.errorbar(i,y,yerr=[[y-x['count_CI95_low']],[x['count_CI95_high']-y]],color='#20628c',fmt='none',capsize=2)
  ax.axhline(zs[0]['observed_CE'],color='#b65339',label='Reported measurement')
  ax.axhspan(zs[0]['observed_CE']*.84,zs[0]['observed_CE']*1.16,color='#b65339',alpha=.12)
  labels={'nominal':'Base','T_288.15':'15 °C','T_298.15':'25 °C','RH_0.72':'RH 72%','RH_0.82':'RH 82%','U_4.5':'4.5 m/s','U_4.9':'4.9 m/s'}
  ax.set_xticks(range(len(zs)),[labels[x['scenario']] for x in zs],rotation=45,ha='right',fontsize=8)
  ax.set(yscale='log',title=f'Row {row}',ylabel='Collection efficiency')
  ax.legend(fontsize=8)
 fig.suptitle('Assumed temperature and reported-condition sensitivity; triangles are bounds')
 fig.savefig(OUT/'sensitivity.png',dpi=180);plt.close(fig)
 lines=['| Row | Physical diameter (µm) | Observed CE | Predicted CE | Zero-hit upper bound | Censored flux |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
 for r,z in zip(rows,nominal):
  ub='—' if z['zero_hit_CE95_upper'] is None else f"{z['zero_hit_CE95_upper']:.3g}"
  lines.append(f"| {r['row']}{'*' if r['row']==6 else ''} | {r['dphysical_um']:.4g} | {r['CE']:.4g} | {z['mean_CE']:.3g} | {ub} | {z['censored_mean']:.3g} |")
 table='\n'.join(lines)
 longrows=[]
 for row in [1,5,8]:
  d=next(x for x in cases if x['row']==row and x['scenario']=='wide_domain')
  longrows.append(f"| {row} | {d['observed_CE']:.5g} | {d['mean_CE']:.5g} | [{d['count_CI95_low']:.3g}, {d['count_CI95_high']:.3g}] | {d['censored_mean']:.3g} |")
 longtable='\n'.join(['| Row | Reported CE | Wider/longer estimate | Conservative sampling interval | Censored flux |','| --- | ---: | ---: | ---: | ---: |']+longrows)
 text=f'''# Falling-droplet model: new measurements tested, validation remains open

15 October 2026. The unchanged model was run against **eight previously unused collection measurements** from [Lemaitre et al. (2017)](https://doi.org/10.5194/acp-17-4159-2017). These are conditional large-raindrop stress tests. No fully specified matched smoke-validation dataset was recovered.

The model was frozen before this continued literature search. None of its coefficients, forces or flow equations was changed to match these outcomes. A source and numerical decision record precedes the predictions in [continuation_protocol.json](continuation_protocol.json); the earlier [protocol.json](protocol.json) remains unchanged.

## Completed comparison

{table}

*Row 6 has inconsistent source concentration entries; the reported efficiency agrees visually with the paper's figure. It remains visible but is excluded from the seven-row aggregate. The two smallest-size rows are replicate observations and share predictions. See [source audit](results/source_audit.csv) and [provenance](source_notes.md).

Nominal Reynolds number: **{metrics['Re_nominal']:.1f}**. Actual computation: **{meta['unique_simulations']} unique simulations, {meta['simulated_paths']:,} particle paths**, across four seeds and 47 row/scenario records. Nominal unique-condition captures: **{metrics['nominal_hits']}**. Reported CE is a dimensionless fraction; multiply by 100 for percent.

![Measurement comparison and numerical checks](results/external_comparison.png)

The wider-domain checks also extend the stopping time from 250 to 1000 dimensionless units. At the nominal inputs, one time unit is A/U = 0.000133 s, so these stops are about 0.033 s and 0.133 s. The original dt0.025 corresponds to about 3.32 microseconds. Three representative size comparisons are:

{longtable}

These point estimates still fall below the corresponding reported efficiencies. They are diagnostic discrepancies under the stated assumptions, not precise estimates of the true experimental error. Captures remain sparse; the model's exact rare-event rates are not demonstrated to be numerically converged.

Zero captured paths means the rare event was not resolved by that run, not that the true model rate is exactly zero. Downward triangles show one-sided 95% bounds for the sampled finite-time disk, using independent stratified paths and a conservative inlet-weight bound. They do not bound untested spatial tails or model error. Censored flux identifies trajectories still unresolved at the stopping time. Four-seed t intervals, measurement uncertainty and these bounds are different quantities.

The four seeds sometimes produce the same small capture count, making their t interval misleadingly narrow. A post-run reporting safeguard therefore adds conservative two-sided count bounds for every case in [sampling_bounds.csv](results/sampling_bounds.csv). They invert a Bernoulli exponential-moment bound, allow unequal probabilities across strata, and use bounds on inlet flux weights. These conservative intervals appear on nonzero model points in the comparison figure. The original seed intervals are retained for audit; this statistical addition does not change any trajectory or selected outcome.

The seven-row predicted/observed ratio range is {metrics['min_predicted_over_observed']:.4g} to {metrics['max_predicted_over_observed']:.4g}. A finite log-error score is not reported when zero point estimates make it undefined. Full values and all qualifications are in [scores.json](results/scores.json), [comparisons.csv](results/comparisons.csv), and [seed-level results](results/seeds.csv).

## What this establishes

The frozen model is being tested outside its physical approximation: 1.25 mm drops with wakes, compared with a prescribed creeping-flow sphere. It omits inertia, rear capture, deformation and electrostatics. It substitutes the measured median particle size for a distribution whose measured collection is mass-weighted. The source does not provide a numerical temperature for these rows; 20 C and 101325 Pa are explicit assumptions, and speed 4.7 m/s is read approximately from Figure 5. These mismatches preclude calling this a matched validation or attributing all disagreement to one missing mechanism.

The completed diagnostics halve and quarter the time step, extend integration time and enlarge the sampled domain at three sizes. They also switch off phoresis, Brownian motion or finite-particle interception separately. A zero-hit result repeated across time steps does not prove convergence of a rare-event rate. All results, including censored and unresolved cases, remain in the files.

![Sensitivity to assumed temperature, humidity and speed](results/sensitivity.png)

The temperature scenarios (15/20/25 C) are assumptions, not measured confidence limits. RH72/77/82% and speeds4.5/4.7/4.9 m/s probe sensitivity without selecting a best-fitting setting. No tuning followed the outcomes.

The sensitivity plots show sampling intervals and the source's 16% measurement band. Differences between point estimates can reflect Monte Carlo variation; this small capture sample does not establish a temperature, humidity or speed trend.

## Search outcome and next missing evidence

The search recovered the 2017 numerical table and the 2020 full paper. The latter has nonzero drop charge in every collection-table row and lacks a numerical temperature tied to those rows; its separate PIV conditions must not be substituted. The 2014 paper reports many measurements graphically without a complete event table. Earlier cloud-drop datasets either influenced model development or use different materials/charges. Details and source hashes are in [source_notes.md](source_notes.md).

A definitive fresh validation still needs unused measurements with temperature, speed, humidity, particle-size distribution and charge specified, in the model's applicable regime. Extending the physical model to finite-Re flow and inertia would create a new version. These eight outcomes would then be development evidence, requiring another reserved dataset for that new version. This completed comparison does not establish universal smoke collection or a new fluid law.

## Reproduce

Use Python with the packages in [requirements.txt](requirements.txt), keeping this folder beside [advanced_tests](../advanced_tests). The runner verifies SHA256 of all three frozen model files and aborts if they changed.

```sh
python test_external.py
python run_external.py
python build_report.py
python verify_results.py
```

No new experiment, exposure, message to authors, physical parameter fitting or model revision was performed. [Execution notes](execution_notes.json) record an initial output-wrapper error and its repair. The raw papers remain at publisher links.
'''
 (HERE/'README.md').write_text(text,encoding='utf-8')
 body='<h1>Falling-droplet model: eight unused measurements</h1><p>Conditional large-raindrop stress test; matched validation remains open.</p>'
 body+='<p><a href="README.md">Full methods, source qualifications and reproduction</a> · <a href="results/comparisons.csv">All results CSV</a></p>'
 body+=f'<p>Unchanged physical model. Reynolds number {metrics["Re_nominal"]:.1f}. {meta["unique_simulations"]} unique simulations and {meta["simulated_paths"]:,} paths.</p>'
 body+='<img src="results/external_comparison.png" alt="Measured and calculated collection efficiency"><img src="results/sensitivity.png" alt="Sensitivity tests">'
 body+='<p>Missing source temperature, median-size approximation and finite-Re flow mismatch prevent matched validation. Row 6 has a source arithmetic conflict. Zero captures are reported with sampling bounds, not treated as proof of zero collection.</p>'
 body+='<h2>Nominal results</h2><pre>'+html.escape(table)+'</pre>'
 (HERE/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Unused collection measurements</title><style>body{font:17px/1.6 system-ui;max-width:1160px;margin:40px auto;padding:20px;color:#183343}img{width:100%;height:auto}pre{font-size:13px;overflow:auto}a{color:#126790}</style>'+body+'</html>',encoding='utf-8')
 print(json.dumps(metrics,indent=2))
if __name__=='__main__':main()
