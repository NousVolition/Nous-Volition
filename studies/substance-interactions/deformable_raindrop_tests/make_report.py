from pathlib import Path
import json,html
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from PIL import Image,ImageDraw
from shape_model import geometry

P=Path(__file__).resolve().parent;F=P/'figures';F.mkdir(exist_ok=True)
r=json.loads((P/'results.json').read_text());rows=json.loads((P/'flow_summary.json').read_text());by={x['name']:x for x in rows}
best=r['best_complete_library_D'];chosen=[p for p in r['predictions'] if p['gas_grid_D']==best]
status=r['study_status'];pending=status['unfinished']
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140})
colors=['#166e97','#bd5935','#5a4389','#4b8247']

fig,ax=plt.subplots(1,3,figsize=(14,4.2))
diam=[p['diameter_mm'] for p in chosen]
ax[0].errorbar(diam,[p['observed_mean'] for p in chosen],yerr=[p['observed_ci95'] for p in chosen],fmt='ko',capsize=4,label='Measured mean; reported 95% interval')
for j,d in enumerate(sorted(set(p['gas_grid_D'] for p in r['predictions']))):
    ps=[p for p in r['predictions'] if p['gas_grid_D']==d]
    ax[0].plot(diam,[p['aspect'] for p in ps],'o--',color=colors[j],label=f'Predicted equilibrium, D/{d} grid')
ax[0].set(xlabel='Drop diameter (mm)',ylabel='Vertical / horizontal size',title='New measurement comparison')
ax[0].legend(fontsize=7);ax[0].set_ylim(.69,.93)
for j,d in enumerate(sorted(set(p['gas_grid_D'] for p in r['predictions']))):
    ps=[p for p in r['predictions'] if p['gas_grid_D']==d]
    ax[1].plot(diam,[p['residual'] for p in ps],'o-',color=colors[j],label=f'{d} cells / diameter')
ax[1].axhline(0,color='k',lw=.8);ax[1].set(xlabel='Drop diameter (mm)',ylabel='Prediction minus measured mean',title='Errors are retained');ax[1].legend(fontsize=8)
ax[2].plot(diam,[p['speed_m_s'] for p in chosen],'o-',color=colors[0])
ax[2].set(xlabel='Drop diameter (mm)',ylabel='Predicted terminal speed (m/s)',title='Speed follows from force balance')
ax[2].text(.03,.92,'No independent measured-speed\nscore in this comparison.',transform=ax[2].transAxes,fontsize=9,va='top',bbox=dict(facecolor='white',alpha=.9,edgecolor='none'))
fig.tight_layout();fig.savefig(F/'measurement_comparison.png');plt.close(fig)

fig,ax=plt.subplots(2,3,figsize=(14,8))
grid=[by[n] for n in ['pilot_re1600_a075_d20','re1600_a075_d28','re1600_a075_d36'] if n in by]
for j,(key,label) in enumerate([('Cd','Drag coefficient'),('Cq','Deformation-load coefficient')]):
    ax[0,j].errorbar([x['D'] for x in grid],[x[key] for x in grid],yerr=[x[key+'_block_sd'] for x in grid],fmt='o-',capsize=4,color=colors[j],label='± SD of four time-block means')
    ax[0,j].set(xlabel='Cells across volume-equivalent diameter',ylabel=label,title='Same Re=1600, aspect=0.75')
    ax[0,j].legend(fontsize=7)
for d,x in zip([x['D'] for x in grid],grid):
    h=np.genfromtxt(P/'flow'/x['name']/'history.csv',delimiter=',',names=True)
    keep=h['tU_D']>=5;ax[0,2].plot(h['tU_D'][keep],h['Cd_projected'][keep],lw=.8,label=str(d)+' cells')
ax[0,2].set(xlabel='Time U/D',ylabel='Instantaneous drag coefficient',title='Wake variation and drift');ax[0,2].legend(fontsize=8)
for j,x in enumerate(grid):
    z=np.load(P/'flow'/x['name']/'slices.npz');field=z['mean'];D=z['D'];speed=z['speed'];nx,ny=z['solid'].shape
    extent=[-z['center'][0]/D,(nx-z['center'][0])/D,-ny/2/D,ny/2/D]
    v=np.ma.array(field[1]/speed,mask=z['solid'])
    im=ax[1,j].imshow(v.T,origin='lower',extent=extent,cmap='RdBu_r',vmin=-.4,vmax=1.4,aspect='equal')
    ax[1,j].contour(z['solid'].T,[.5],extent=extent,origin='lower',colors='k',linewidths=.6)
    ax[1,j].set(xlim=(-1.5,7),ylim=(-1.7,1.7),xlabel='Downstream position / D',ylabel='Transverse position / D',title=f'{x["D"]} cells: mean axial air speed / U')
    fig.colorbar(im,ax=ax[1,j],shrink=.62)
fig.tight_layout();fig.savefig(F/'grid_and_flow.png');plt.close(fig)

trace=np.load(P/'deformation_traces.npz')
fig,ax=plt.subplots(2,2,figsize=(12,8))
for j,p in enumerate(chosen):
    name=f'D{p["diameter_mm"]:g}';v=trace[name]
    ax[0,0].plot(v[:,0],v[:,3],color=colors[j],label=f'{p["diameter_mm"]:g} mm')
ax[0,0].set(xlabel='Time (s)',ylabel='Axis ratio',title='Shape responds to airflow and surface tension');ax[0,0].legend(ncol=2)
for name,label in [('D4','Nominal damping'),('double_damping','Double liquid viscosity'),('no_damping','Zero liquid viscosity')]:
    v=trace[name];ax[0,1].plot(v[:,0],v[:,3],lw=1,label=label)
ax[0,1].set(xlabel='Time (s)',ylabel='Axis ratio',title='Controls change the response');ax[0,1].legend(fontsize=8)
v=trace['larger_initial'];ids=[0,int(np.argmin(v[:,3])),len(v)-1]
for j,k in enumerate(ids):
    a,b=geometry(v[k,1],.004);offset=(j-1)*5
    ax[1,0].add_patch(Ellipse((offset,0),2*b*1000,2*a*1000,fc=colors[j],alpha=.2,ec=colors[j],lw=2))
    ax[1,0].text(offset,-2.7,f't={v[k,0]:.3f} s\nratio={v[k,3]:.3f}',ha='center',fontsize=9)
ax[1,0].set(xlim=(-8,8),ylim=(-3.5,3.2),xlabel='Horizontal position (mm)',ylabel='Vertical position (mm)',title='Computed 4 mm drop outlines; equal volume');ax[1,0].set_aspect('equal')
v=trace['D4'];E=v[:,4]-v[0,4];work=v[:,5];loss=v[:,6]
ax[1,1].plot(v[:,0],E*1e9,label='Change in liquid energy');ax[1,1].plot(v[:,0],(work-loss)*1e9,'--',label='Air work minus viscous loss')
ax[1,1].set(xlabel='Time (s)',ylabel='Energy (nJ)',title='Reduced-model energy accounting');ax[1,1].legend(fontsize=8)
fig.tight_layout();fig.savefig(F/'deforming_drops.png');plt.close(fig)

# Animation uses the actual larger-initial-disturbance trace. It is explicitly
# labelled a reduced shape calculation, never a fully moving-interface CFD.
v=trace['larger_initial'];frames=[]
for k in np.linspace(0,len(v)-1,90).astype(int):
    im=Image.new('RGB',(620,420),'#f4f8fa');draw=ImageDraw.Draw(im);a,b=geometry(v[k,1],.004);scale=65000
    draw.ellipse((310-b*scale,220-a*scale,310+b*scale,220+a*scale),fill='#92c9e2',outline='#166e97',width=4)
    draw.text((22,18),'4 mm water drop - reduced shape simulation',fill='#142d3e')
    draw.text((22,42),f'Time {v[k,0]:.3f} s | aspect {v[k,3]:.3f} | constant water volume',fill='#142d3e')
    draw.text((22,390),'Airflow loads are interpolated from separate stationary 3D solves.',fill='#142d3e')
    frames.append(im)
frames[0].save(F/'drop_shape.gif',save_all=True,append_images=frames[1:],duration=45,loop=0)

fig,ax=plt.subplots(1,2,figsize=(12,4.6))
loadcheck=json.loads((P/'surface_load_verification.json').read_text())['rows']
for aspect in [1.,.75]:
    data=[x for x in loadcheck if x['aspect']==aspect]
    ax[0].plot([x['D'] for x in data],[100*abs(x['relative_error']) for x in data],'o-',label=f'Aspect {aspect:g}')
ax[0].set(xlabel='Cells per diameter',ylabel='Surface-load error (%)',title='Independent analytic pressure-load test');ax[0].legend()
sens=json.loads((P/'sensitivity.json').read_text());base4=chosen[-1]['aspect']
labels={'surface_tension_N_m':'Surface tension ±3%','rho_air_kg_m3':'Air density ±5%',
 'nu_air_m2_s':'Air kinematic viscosity ±5%','rho_water_kg_m3':'Water density ±0.2%',
 'drop_diameter':'Diameter ±2%','cd_10percent_diagnostic':'Gas drag coefficient ±10%',
 'cq_10percent_diagnostic':'Gas shape load ±10%'}
for i,(key,label) in enumerate(labels.items()):
    data=[x for x in sens if x['parameter']==key and (x['diameter_mm']>3.8)]
    lo,hi=sorted(x['aspect']-base4 for x in data)
    ax[1].plot([lo,hi],[i,i],'o-',lw=3,color=colors[i%4])
ax[1].axvline(0,color='k',lw=.7);ax[1].set_yticks(range(len(labels)),labels.values());ax[1].invert_yaxis()
ax[1].set(xlabel='Change in predicted 4 mm axis ratio',title='What-if ranges, not confidence intervals')
fig.tight_layout();fig.savefig(F/'numerical_and_input_limits.png');plt.close(fig)

def table(headers,data):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+html.escape(str(h))+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in data)+'</tbody></table></div>'
comparison=table(['Diameter','Measured ratio','Predicted ratio', 'Difference','Predicted speed'],[
  [f'{p["diameter_mm"]:g} mm',f'{p["observed_mean"]:.3f} ± {p["observed_ci95"]:.3f}',f'{p["aspect"]:.4f}',f'{p["residual"]:+.4f}',f'{p["speed_m_s"]:.3f} m/s'] for p in chosen])
gridtable=table(['Cells / D','3D lattice sites','Mean drag coefficient','Mean shape-load coefficient'],[
 [x['D'],f'{round(12*5*5*x["D"]**3):,}',f'{x["Cd"]:.6f}',f'{x["Cq"]:.6f}'] for x in grid])
checks=[]
for f in ['shape_verification.json','gas_verification.json','surface_load_verification.json','mass_budget_verification.json']:
    data=json.loads((P/f).read_text());checks.append([f,data['status']])
gridchange='Pending reference-grid result.'
if len(grid)==3:
    d28,d36=grid[1:];gridchange=f'From 28 to 36 cells, drag changes by {100*(d36["Cd"]/d28["Cd"]-1):+.1f}% and the deformation load by {100*(d36["Cq"]/d28["Cq"]-1):+.1f}% in the reference case.'
finechange=''
comparison_note=''
if best==28:
    old=[p for p in r['predictions'] if p['gas_grid_D']==20]
    finechange=f'The complete 20-to-28-cell comparison changes the predicted axis ratio by as much as {max(abs(a["aspect"]-b["aspect"]) for a,b in zip(chosen,old)):.4f}.'
    old_error=np.mean([abs(p['residual']) for p in old])
    comparison_note=f'Refinement changes the mean absolute ratio error from {old_error:.4f} to {r["mean_absolute_axis_error"]:.4f}; it does not improve agreement with these measured means. The largest drop remains too flat in the model. The measured 4 mm mean is slightly rounder than the 3.6 mm mean, whereas this equilibrium-spheroid model predicts continued flattening. Missing oscillation modes are a plausible limitation, not an experimentally isolated explanation of the discrepancy.'
case_labels={'pilot_re1600_a075_d20':'Re 1600, 20 cells',
 're1600_a075_d28':'Re 1600, 28 cells','re1600_a075_d36':'36 cells',
 're1600_a075_d28_long':'Twice the simulation duration',
 're2600_a075_d28':'Re 2600, 28 cells','re2600_a075_d36':'Re 2600, 36 cells',
 're1600_a075_d20_slow':'Half the lattice speed / time step',
 're1600_a075_d20_wide':'Wider and longer domain',
 're1600_a075_d20_halfway':'Re 1600, old halfway wall'}
pairtable=table(['Reference calculation','Changed calculation','Drag change','Shape-load change'],[
 [case_labels.get(x['reference'],x['reference']),case_labels.get(x['changed'],x['changed']),f'{x["Cd_percent"]:+.2f}%',f'{x["Cq_percent"]:+.2f}%'] for x in r.get('paired_controls',[])])
interptable=table(['Independent computational point','Drag interpolation error','Shape-load interpolation error'],[
 [x['name'],f'{100*x["Cd_relative_error"]:+.2f}%',f'{100*x["Cq_relative_error"]:+.2f}%'] for x in r.get('interpolation_checks',[])])
if not r.get('interpolation_checks'):
    interptable='<p>The two independent lookup-interpolation checks have not been run. No interpolation-accuracy result is claimed.</p>'
pendingtable=table(['Unfinished check','Status'],[[x['description'] or x['name'],x['status'].replace('_',' ')] for x in pending])
release_label='Interim results — four checks unfinished' if pending else 'All planned flow runs completed'
body=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Deformable raindrops · Streams and Rocks</title><style>
body{{margin:0;background:#f5f7f8;color:#183042;font:17px/1.6 system-ui,sans-serif}}main{{max-width:1120px;margin:auto;padding:36px 24px 80px}}h1{{font-size:2.2em;line-height:1.15}}h2{{margin-top:2.1em}}.tag{{text-transform:uppercase;font-size:12px;letter-spacing:.14em;color:#536a78}}.card{{background:white;border:1px solid #d9e1e5;border-radius:12px;padding:20px;margin:22px 0}}.limit{{border-left:5px solid #bd5935;background:#fff6ee;padding:18px}}img{{max-width:100%;height:auto;background:white;border-radius:8px}}a{{color:#00658a}}table{{border-collapse:collapse;width:100%;font-size:15px}}td,th{{padding:11px;text-align:left;border-bottom:1px solid #dbe2e6}}th{{background:#e9f0f4}}.scroll{{overflow:auto}}.caption{{font-size:14px;color:#536575}}code{{font-size:14px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}@media(max-width:700px){{.grid{{display:block}}main{{padding:24px 14px}}h1{{font-size:1.8em}}}}
</style><main><p class="tag">Streams and Rocks · {release_label} · 20 October 2026</p>
<h1>Raindrops that can change shape</h1>
<p>The model now predicts flattening and oscillation from airflow, surface tension and liquid inertia. The water volume stays constant. Airflow uses a curved-surface treatment and finer grids.</p>
<p><strong>{r['counts']['completed']} of {status['planned']} planned three-dimensional airflow runs are complete</strong>, including two complete prediction tables and comparisons with four new measured shape outcomes. Simulations remain paused. This release publishes the saved results and identifies the unfinished checks.</p>
<h2>Four checks remain unfinished</h2>{pendingtable}<p>The interrupted run produced no final numerical record. It is excluded from the averages and predictions. Unfinished checks are not treated as passing. See the <a href="study_status.json">case-by-case status</a>.</p>
<div class="limit"><strong>This is a reduced deformable-drop model, not a fully resolved two-fluid simulation.</strong> Gas loads come from separate stationary 3D flow calculations; a volume-preserving spheroid responds to those loads. The new measurement comparison is completed, but the model is not validated for real raindrops or smoke capture.</div>
<h2>What changed</h2><div class="grid"><div class="card"><strong>A responsive shape</strong><p>Surface tension pulls the drop toward a sphere. Airflow flattens it. Liquid inertia allows overshoot and oscillation; viscosity removes energy. The resulting shape also changes the calculated drag and air load.</p></div><div class="card"><strong>Finer airflow calculations</strong><p>Exact curved-surface intersections replace the old halfway staircase wall. The complete prediction tables use 20 and 28 cells across a drop. One completed 36-cell reference calculation checks further refinement at Re=1600. The Re=2600 refinement remains unrun.</p></div></div>
<img src="figures/drop_shape.gif" alt="Animated computed spheroidal shape changing while volume remains fixed"><p class="caption">Actual saved shape trajectory, shown slowly. This is the reduced liquid equation coupled to an airflow lookup, not a movie of a moving free-surface CFD calculation.</p>
<h2>A new measurement comparison</h2><p>All four preselected sizes are compared with <a href="https://people.hws.edu/laird/index_files/pubs/1999-Andsager-et-al-jas.pdf">Andsager, Beard and Laird’s laboratory measurements</a>. No model coefficient was fitted to these values. Model and source choices preceded table extraction; search previews had already exposed qualitative findings, so this was not a blinded test.</p>
{comparison}<p class="caption">Predictions use the complete {best}-cell airflow table. Measured intervals are the paper’s reported 95% intervals for the mean; they exclude our model uncertainty. The model predicts equilibrium spheroids, while the experiment measures mean chord ratios of oscillating drops. Predicted speeds are not scored against correlation-derived speeds.</p>
<p>Mean absolute shape-ratio error is <strong>{r['mean_absolute_axis_error']:.4f}</strong>. The 4 mm source mean is 0.808 in Table 2 and 0.807 in Table 3; both are preserved. That 0.001 discrepancy does not remove the larger modeling and resolution questions.</p>
<p>{comparison_note}</p>
<img src="figures/measurement_comparison.png" alt="All four measured drop-size outcomes compared with predictions, showing errors and predicted speeds">
<h2>Do finer grids agree?</h2>{gridtable}<p>{gridchange} {finechange} These changes are evidence about numerical uncertainty, not proof of convergence.</p>
<img src="figures/grid_and_flow.png" alt="Grid comparison of aerodynamic loads and resolved airflow fields">
<p class="caption">The three reference gas cases have Re=1600 and aspect=0.75. Error bars are the standard deviation of four time-block means, not confidence intervals. Colors show mean axial air velocity divided by inlet speed. All controls are retained in <a href="flow_summary.csv">the complete numerical table</a>.</p>
{pairtable}<p class="caption">These are direct differences between completed calculations, not uncertainty bounds. The longer-averaging control remains unfinished, so late-wake averaging has not been checked.</p>
{interptable}<p class="caption">The planned midpoint checks are separate from the experimental comparison and will not enter the prediction lookup.</p>
<img src="figures/numerical_and_input_limits.png" alt="Remaining surface-force discretization error and declared input sensitivity ranges">
<p>Within this model, larger drops flatten more because their weight grows faster relative to surface tension. Changing air density mostly changes the speed needed to support that weight. This helps explain the sensitivity pattern; it does not resolve the missing oscillation modes seen in real drops.</p>
<h2>Shape motion and controls</h2><img src="figures/deforming_drops.png" alt="Shape evolution, damping controls, equal-volume outlines and liquid energy accounting">
<p>The initial disturbances are declared test scenarios. Their amplitudes were not fitted to photographed drops. Removing air forcing lets the shape relax toward a sphere; changing viscosity changes the damping. With zero liquid viscosity, oscillations persist in this reduced model.</p>
<h2>Checks that passed—and what they establish</h2>{table(['Saved check','Status'],checks)}
<p>The small-amplitude 4 mm oscillation benchmark is 42.966 Hz. The damping check agrees with its analytic limit to about 0.009%. Exact spheroidal volume is preserved to floating-point precision. The independent manufactured surface-pressure test still has approximately 5.5% load error at 36 cells, so passing its 10% check is not high-accuracy validation.</p>
<p>The discrete gas ledger separates inlet/outlet mass transfer from small numerical leakage at interpolated walls. It closes to approximately 0.000029% of initial mass in the short verification case. Wall leakage itself is nonzero. Production mass offsets and this short ledger do not establish a full two-phase conservation test.</p>
<h2>What remains unresolved</h2><ul><li>The full liquid and gas interface is not advanced together. Internal circulation, surface mobility, non-spheroidal deformation, transverse modes and wake–shape locking remain absent.</li><li>The viscous boundary layer and turbulent wake are not fully resolved. Grid, domain, lookup spacing and averaging errors remain; a stable run is not a direct numerical simulation claim.</li><li>Individual measurement temperatures and local airflow were unavailable. The nominal material inputs are 20 °C; property and diameter sensitivity is reported separately.</li><li>There are no new particle-capture or retention calculations here. Improved drop shape alone cannot validate smoke scavenging.</li></ul>
<h2>Reproduce and inspect</h2><p><a href="README.txt">Run instructions</a> · <a href="METHODS.txt">Equations, units and limitations</a> · <a href="results.json">Numerical results</a> · <a href="comparison.csv">Measurement comparison</a> · <a href="measurements.csv">Transcribed measurements</a> · <a href="source_audit.json">Source audit</a> · <a href="protocol.json">Original protocol</a> · <a href="amendments.json">Recorded additions</a> · <a href="sensitivity.json">Sensitivity results</a> · <a href="saved_data_audit.json">Saved-data audit</a></p>
<p>Method references: <a href="https://doi.org/10.1063/1.1399290">curved-wall interpolation</a>, <a href="https://doi.org/10.1016/j.matcom.2006.05.017">regularized gas solver</a>, <a href="https://doi.org/10.1007/s10765-020-2608-z">drop oscillation and damping limits</a>, and <a href="https://iapws.org/technical-guidance/release/Surf-H2O">water surface tension</a>. Material properties are not inferred from the earlier molecular pilot.</p>
</main></html>'''
(P/'report.html').write_text(body,encoding='utf-8')
import re
rp=P/'README.txt';readme=rp.read_text(encoding='utf-8')
readme=re.sub(r'\nBEGIN RECORDED RESULTS\n.*?END RECORDED RESULTS\n','',readme,flags=re.S)
summary='\nBEGIN RECORDED RESULTS\n'
summary+=f'INTERIM RELEASE: {status["completed"]} of {status["planned"]} planned flow cases completed.\nFour numerical checks remain unfinished; simulations remain paused.\n'
for x in pending:
    summary+=f'  Unfinished: {x["name"]} — {x["status"]}.\n'
summary+=f'{r["counts"]["completed"]} completed gas-flow cases. Shape predictions below use the\ncomplete {best}-cell-per-diameter gas library. Axis ratio is vertical/horizontal.\n'
for p in chosen:
    summary+=f'  {p["diameter_mm"]:g} mm: predicted {p["aspect"]:.4f}; measured {p["observed_mean"]:.3f}; difference {p["residual"]:+.4f}.\n'
summary+=f'Mean absolute ratio error: {r["mean_absolute_axis_error"]:.4f}.\n{gridchange}\n'
summary+='The measured means were not fitted. These are conditional comparisons,\nnot validation of a fully moving liquid-air interface or smoke capture.\nEND RECORDED RESULTS\n'
readme=readme.replace('WHAT IS NEW',summary+'\nWHAT IS NEW',1);rp.write_text(readme,encoding='utf-8')
print('Figures and report written.')
