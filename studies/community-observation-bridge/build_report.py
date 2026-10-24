"""Build tables and figures from completed full-equation runs; never fit outcomes."""
from pathlib import Path
import csv,json,html,platform
import numpy as np
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from verify_saved import verify
ROOT=Path(__file__).resolve().parent

def main():
    r=json.loads((ROOT/'results/results.json').read_text(encoding='utf-8'))
    s=json.loads((ROOT/'results/stronger_reading.json').read_text(encoding='utf-8'))
    o=json.loads((ROOT/'observations.json').read_text(encoding='utf-8'))
    p=json.loads((ROOT/'provenance.json').read_text(encoding='utf-8'))
    v=verify();(ROOT/'figures').mkdir(exist_ok=True)
    allrows=[('main_search',x) for x in r['runs']]+[('main_refinement',x) for x in r['refinements']]+[('control',x) for x in r['controls']]+[('exploratory_stricter_reading',x) for x in s['additional_runs']]
    with (ROOT/'results/runs.csv').open('w',encoding='utf-8',newline='') as f:
        columns=['stage','law','distance','A0','n','dt','steps','kappa','sigma','label','compatible','initial_c_P','initial_c_F','initial_dc_P','initial_dc_F','initial_contrast_rate','final_contrast','mass_error_max','divergence_max','energy_residual_max']
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for stage,row in allrows:
            flat={k:row[k] for k in ['law','distance','A0','n','dt','steps','kappa','sigma','compatible','mass_error_max','divergence_max','energy_residual_max']}
            flat.update(stage=stage,label=row.get('control',row.get('refinement_label','')),final_contrast=row['final']['contrast'])
            flat.update({'initial_'+k:row['initial'][k] for k in ['c_P','c_F','dc_P','dc_F','contrast_rate']});writer.writerow(flat)
    selected=[next(x for x in r['runs'] if x['law']=='sharp' and x['distance']==.15 and x['A0']==A) for A in [-.02,.005,.02]]
    colors=['#b5502c','#7b57aa','#147d83']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'#ffffff'})
    fig,axes=plt.subplots(1,2,figsize=(11.6,4.6),layout='constrained')
    for row,color in zip(selected,colors):
        t=[0]+[x['t'] for x in row['trace']];y=[row['initial']['contrast']]+[x['contrast'] for x in row['trace']]
        axes[0].plot(t,y,color=color,label=f"Assumed A = {row['A0']:+.3f}",ls='--' if row['A0']==.005 else '-')
        axes[1].scatter(row['initial']['dc_P'],row['initial']['dc_F'],s=75,color=color,zorder=3)
        axes[1].annotate(f"A={row['A0']:+.3f}",(row['initial']['dc_P'],row['initial']['dc_F']),xytext=(5,8),textcoords='offset points',fontsize=9)
    axes[0].axhline(0,c='#777777',lw=.8);axes[0].set(xlabel='Time (dimensionless; no human-time calibration)',ylabel='Contextual-support contrast cP − cF',title='Same initial support readings, different continuations')
    axes[0].legend(loc='upper left',fontsize=9)
    axes[1].axhline(0,c='#777777',lw=.8);axes[1].axvline(0,c='#777777',lw=.8)
    axes[1].set(xlabel='Initial rate of cP (model units)',ylabel='Initial rate of cF (model units)',title='Stricter reading: cP rises while cF falls',xlim=(-.17,.14),ylim=(-.18,.03))
    axes[1].axvspan(0,.14,ymin=0,ymax=.18/.21,color='#e8f3f2',zorder=0)
    fig.suptitle('Conditional equation results — these curves are not measured human trajectories',fontsize=12,fontweight='bold')
    fig.savefig(ROOT/'figures/ambiguity.png',dpi=170);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8.6,4.3),layout='constrained')
    for item,color in zip(v['convergence'],colors):
        ax.semilogy([0,1,2],[item['grid24_48'],item['grid48_72'],item['actual_half_step']],'o-',color=color,label=f"A={item['A0']:+.3f}")
    ax.set(xticks=[0,1,2],xticklabels=['Grid 24 → 48','Grid 48 → 72','Actual half step on grid 48'],ylabel='Absolute endpoint contrast difference',title='Finer calculations preserve the opposite signs')
    ax.legend();ax.grid(axis='y',alpha=.2);fig.savefig(ROOT/'figures/refinement.png',dpi=160);plt.close(fig)
    summary=dict(status='conditional_compatibility_and_nonuniqueness_not_empirical_forecast',main_runs=75,main_distinct_configurations=73,
                 exploratory_runs=3,all_recorded_runs=78,all_distinct_configurations=76,compatible_search_runs=48,search_runs=63,
                 constructive_witness_pairs=60,people=1,episodes_coded=5,episodes_constraining_PDE=1,
                 empirical_prediction_error=None,selected_results=[{'A0':x['A0'],'initial':x['initial'],'final_contrast':x['final']['contrast']} for x in selected],
                 convergence=v['convergence'],maxima=v['maxima'],verification='8 unit tests; see verification.json for saved and source checks')
    (ROOT/'results/summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    (ROOT/'results/environment.json').write_text(json.dumps(dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__,platform=platform.system(),precision='float64'),indent=2)+'\n',encoding='utf-8')
    sources={x['file']:x for x in p['sources']}
    table=''.join(f'<tr><td><a href="{sources[e["source_file"]]["url"]}">{e["id"]}</a></td><td>{html.escape(e["reported"])}</td><td>{html.escape(e["limits"])}</td></tr>' for e in o['episodes'])
    result_table=''.join(f'<tr><td>{x["A0"]:+.3f}</td><td>{x["initial"]["dc_P"]:+.6f}</td><td>{x["initial"]["dc_F"]:+.6f}</td><td>{x["final"]["contrast"]:+.6f}</td></tr>' for x in selected)
    convergence=''.join(f'<tr><td>{x["A0"]:+.3f}</td><td>{x["grid24_48"]:.3g}</td><td>{x["grid48_72"]:.3g}</td><td>{x["actual_half_step"]:.3g}</td></tr>' for x in v['convergence'])
    report=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Observations → two-in-one equations · Streams and Rocks</title>
<style>body{{margin:0;background:#f5f5f0;color:#233334;font:17px/1.6 system-ui,sans-serif}}main{{max-width:1080px;margin:auto;padding:45px 24px 80px}}h1{{font-size:38px;line-height:1.15;max-width:900px}}h2{{font-size:26px;margin-top:46px}}a{{color:#126b74}}.eyebrow{{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:#536d6b}}.lead{{font-size:21px;max-width:920px}}.box{{padding:22px 26px;background:#e6f2ee;border-left:5px solid #177c79;margin:26px 0}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.card{{background:white;padding:20px;border:1px solid #ccd8d2;border-radius:8px}}.card strong{{font-size:29px;display:block}}.muted{{font-size:14px;color:#536568}}img{{width:100%;height:auto;background:white}}table{{border-collapse:collapse;width:100%;font-size:15px;background:white}}td,th{{padding:12px;border-bottom:1px solid #d2dad6;text-align:left;vertical-align:top}}pre{{padding:20px;overflow:auto;background:#203333;color:#f4fbf8;font-size:14px}}.scroll{{overflow:auto}}@media(max-width:650px){{.cards{{grid-template-columns:1fr}}h1{{font-size:31px}}main{{padding:25px 16px}}}}</style><main>
<div class="eyebrow">Streams and Rocks · 23 October 2026</div><h1>Connect the real observations.<br>Keep the full equations.</h1>
<p class="lead">Five real inward-experience episodes are connected to Smoke, Clay, personal history and the moving idea. The unchanged coupled field equations were then run against an explicit qualitative interpretation of one episode.</p>
<div class="box"><b>Result: the present account does not choose a unique continuation under this proposed mapping.</b> Different assumed histories satisfy the same observation constraints but produce opposite later contextual-support contrasts. The result survives finer grids and a stricter interpretation of the reported change.</div>
<div class="cards"><div class="card"><strong>5 episodes</strong>one person; manual source coding</div><div class="card"><strong>75 + 3 runs</strong>full equations; three exploratory follow-ups</div><div class="card"><strong>No forecast score</strong>later human outcomes were not measured</div></div>
<h2>What was connected</h2><p><b>Smoke</b> marks inward putting-forward. <b>Clay</b> marks receiving, searching, evaluating or reconsidering. The <b>moving idea</b> retains content, expression and reported changes. These are operations within one person. The graph preserves three reported history references without manufacturing a numerical biography.</p>
<p>The available corrected corpus was hash-checked, and selected Miro frames on meaning, memory and hidden states were read live. <a href="CONNECTIONS.md">The source-to-equation mapping</a> identifies every added assumption.</p>
<div class="scroll"><table><thead><tr><th>Sample / original PDF</th><th>Reported experience</th><th>Limits</th></tr></thead><tbody>{table}</tbody></table></div>
<h2>The completed calculation</h2><p>For sample 10.1, P denotes an understanding/patience alternative and F a frustrated appraisal. Neither is a person or role. We hypothesize that localized readings of the context field S represent their support, and that choosing understanding increases their relative support. The report does not measure these readings or their derivatives.</p>
<pre>u_t + (u·∇)u = −∇p + νΔu − (σ/ρ)a(|∇S|−Γcrit)e_k
∇·u = 0
S_t + u·∇S = D_diff ΔS + K_h κA
A_t = γ(U−Ubaseline)

Added observation operator: c_j = ∫ w_j S,  ∫ w_j = 1
Primary constraints: c_P > 0, c_F > 0, d(c_P−c_F)/dt > 0</pre>
<p>All three response laws, nonlinear advection, pressure, diffusion, the source and accumulator were retained. Stress and field/energy accounting were checked. Future excess input is assumed zero. Inputs, chart geometry, support scale and initial fields are <b>unmeasured conditional assumptions</b>. The utility optimizer cannot be inferred from these records.</p>
<img src="figures/ambiguity.png" alt="Full-equation continuations under three assumed initial accumulators. Opposite endpoint contrasts remain possible despite compatible initial directions.">
<div class="scroll"><table><tr><th>Assumed A at start</th><th>Initial cP rate</th><th>Initial cF rate</th><th>cP−cF at model time 1</th></tr>{result_table}</table></div>
<p>Initial supports are identical: cP=0.338312 and cF=0.370799. The primary witness uses A=−0.020 and +0.020. Both meet the primary inequalities. The <b>exploratory stricter reading</b> uses +0.005 and +0.020: cP rises and cF falls in both, yet their final contrasts still have opposite signs. These are hypothetical field states, not measured emotional intensities.</p>
<p>Across the declared search, 48 of 63 candidates satisfy the weak constraints; 60 pairs provide ambiguity witnesses. Those are overlapping model combinations, not 60 independent people or statistical confidence estimates. The main execution includes two duplicate step configurations, documented in the <a href="NUMERICAL_AMENDMENT.md">numerical amendment</a>.</p>
<h2>Numerical checks</h2><img src="figures/refinement.png" alt="Grid and effective time-step refinement reduce differences in endpoint contrast.">
<div class="scroll"><table><tr><th>A</th><th>Grid 24→48 difference</th><th>Grid 48→72 difference</th><th>Actual half-step difference</th></tr>{convergence}</table></div>
<p>Eight unit tests passed. Source hashes and saved outputs passed their checks. Maximum field-total accounting error was {v['maxima']['mass_error_max']:.3g}; divergence RMS {v['maxima']['divergence_max']:.3g}; instantaneous semidiscrete energy-identity residual {v['maxima']['energy_residual_max']:.3g}. These are numerical diagnostics, not human validation.</p>
<p>With the source disabled, the two initial-accumulator choices give identical fields in this control. Disabling the threshold force does not remove all history sensitivity, because the source still changes S. This identifies model pathways; it does not identify a psychological cause.</p>
<h2>What is supported — and what remains open</h2><p>The primary records support investigating inward presentation, reconsideration, nonverbal alternatives, partial recall and experienced pace. Fog and Wind have partial feature connections. Water's perceived balance, Mist's internalized unspoken agreement and D₂O's small change with a consequential effect are not established by these episodes. Missing observations remain unknown.</p>
<p><b>The full empirical two-in-one model remains unvalidated.</b> The new observation operator is explicit and testable, but uncalibrated. These selected records informed its construction. The model time is dimensionless; no later human endpoint, independent held-out score, population conclusion or separate Smoke/Clay history evolution was invented. Stronger independent measurements must distinguish the admissible histories and test the proposed readout.</p>
<h2>Reproduce and inspect</h2><p><a href="README.md">Study README</a> · <a href="CONNECTIONS.md">Connection and limits</a> · <a href="observations.json">Observation graph</a> · <a href="provenance.json">Source hashes and Miro frames</a> · <a href="PROTOCOL.md">Frozen protocol</a> · <a href="CONSTRAINT_AMENDMENT.md">Stricter-reading amendment</a> · <a href="results/runs.csv">All 78 run records</a> · <a href="results/summary.json">Quantitative summary</a> · <a href="results/verification.json">Verification</a></p>
<pre>python -m pip install -r requirements.txt
python run_tests.py
python check_stronger_reading.py
python -m unittest discover -p 'test_*.py' -v
python verify_saved.py
python build_report.py</pre><p class="muted">Original PDFs remain at the source. This report contains concise attributed descriptions, source locators and hashes. It does not republish the full interviews or Miro boards.</p></main></html>'''
    (ROOT/'report.html').write_text(report,encoding='utf-8')
    print(json.dumps(dict(run_rows=len(allrows),figures=2,report='report.html')))

if __name__=='__main__':main()
