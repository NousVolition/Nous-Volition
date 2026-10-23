from pathlib import Path
import csv,html,json,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from corpus_field import Field,Parameters

ROOT=Path(__file__).resolve().parent;R=ROOT/'results';F=ROOT/'figures';F.mkdir(exist_ok=True)
e=json.loads((R/'equation_results.json').read_text());d=json.loads((R/'data_audit.json').read_text());v=json.loads((R/'verification.json').read_text())
fields=np.load(R/'final_fields.npz');f=Field(Parameters())
a=f.real(fields['sharp_24'][2]);b=f.real(fields['different_spatial_parameters'][2])
fig,ax=plt.subplots(1,3,figsize=(11.5,3.4),layout='constrained')
for axis,s,title in zip(ax,[a,b,b-a],['Original spatial parameters','Changed force and diffusion','Difference between fields']):
    lim=max(np.max(abs(a)),np.max(abs(b))) if axis is not ax[2] else np.max(abs(b-a))
    im=axis.imshow(s.T,origin='lower',extent=[0,1,0,1],cmap='RdBu_r',vmin=-lim,vmax=lim)
    axis.set(title=title,xlabel='Declared model x',ylabel='Declared model y');fig.colorbar(im,ax=axis,shrink=.8,label='Signed S')
fig.suptitle('Full equation check: different fields have the same total\nSynthetic inputs; these are not measured thought maps',fontsize=12)
fig.savefig(F/'field_identification.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(7.4,4),layout='constrained')
for rr in e['refinement']:
    ax.plot([1,2],[rr['grid24_48'],rr['grid48_72']],marker='o',label=rr['law'].replace('_',' '))
ax.set_xticks([1,2],['24 versus 48 cells per axis','48 versus 72 cells per axis']);ax.set_yscale('log')
ax.set(ylabel='L2 difference, all field and velocity modes',title='Finer grids give smaller differences in these trials')
ax.legend();ax.grid(axis='y',alpha=.2);fig.savefig(F/'refinement.png',dpi=180);plt.close(fig)
coverage=[
 ['Person and within-session order','Observed','118 people; separate recorded streams','Do not concatenate different people into one history'],
 ['Expression and elapsed time','Observed','12,104 timed sentence/clause records','Verbalizing thought can change it; clock time is not felt time'],
 ['Thought topics and categories','Observer annotation','6,434 groups with aligned numeric embeddings','Classification of expressed content is not a direct measure of personal intent'],
 ['Smoke and Clay functions','Unmeasured in this release','No separate role columns','A spoken sentence does not reveal what was inwardly received or refused'],
 ['Sens and utility U','Unmeasured as model inputs','No participant-rated intended-meaning trajectory or utility scale','Do not replace these with emotion or semantic similarity'],
 ['Spatial S and u','Mapping unresolved','768-dimensional language-model vectors are available','A declared continuous domain, metric and observation equation are required'],
 ['Personal pre-session history','Unobserved','Short current session, not lifetime input','Missing history is not zero'],
 ['Water Fog Mist Wind forms','Unmeasured as author-defined forms','No reports of the stated distinctions','Perceived balance, agreement, tension and felt time remain separate'],
]
with (ROOT/'measurement_coverage.csv').open('w',newline='',encoding='utf-8') as out:
    w=csv.writer(out);w.writerow(['quantity','evidence_status','available_record','limitation']);w.writerows(coverage)
trace=[
 ['229','u_t + (u dot grad)u = -grad(p) + nu Laplacian(u) + f; div(u)=0','Field.terms; Field.project','Momentum, convection, pressure and incompressibility retained'],
 ['230;548','q=abs(grad(S))-Gamma; f=-(sigma/rho)*a(q)*e','Field.terms; activation','Fixed unit direction; not drag'],
 ['261;262;264','sharp; signed tanh; smooth exact-off alternatives','activation','Three distinct laws; no clipping of the signed tanh tail'],
 ['517','S_t + u dot grad(S) = D Laplacian(S) + K_h*kappa*A','Field.terms','Signed scalar; source kernel normalized; no per-step renormalization of S'],
 ['518;532','A_t=gamma*(U-Ubaseline); A(0)=0','Field.initial; Field.step','Accumulated source; no forgetting term'],
 ['545','T=mu0*(grad(u)+transpose(grad(u)))','Field.diagnostics','Symmetric stress; mu0=rho*nu is explicit for these trials'],
]
with (ROOT/'equation_trace.csv').open('w',newline='',encoding='utf-8') as out:
    w=csv.writer(out);w.writerow(['corpus_paragraph','equation','implementation','fidelity']);w.writerows(trace)

md=[];ht=[]
def inline(t):
    t=html.escape(str(t));t=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',t)
    return re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',t)
def h(t,n=2):md.append('#'*n+' '+t);ht.append(f'<h{n}>{inline(t)}</h{n}>')
def p(t):md.append(t);ht.append('<p>'+inline(t)+'</p>')
def code(t):md.append('```text\n'+t+'\n```');ht.append('<pre>'+html.escape(t)+'</pre>')
def table(headers,rows):
    md.append('\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows]))
    ht.append('<div class="scroll"><table><thead><tr>'+''.join('<th>'+inline(s)+'</th>' for s in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+inline(s)+'</td>' for s in r)+'</tr>' for r in rows)+'</tbody></table></div>')
def image(name,caption):md.append(f'![{caption}](figures/{name}.png)');ht.append(f'<figure><img src="figures/{name}.png" alt="{html.escape(caption)}"><figcaption>{inline(caption)}</figcaption></figure>')

h('Exact corpus equations and the two in one data audit',1)
p('Streams and Rocks · 22 October 2026')
p('**The coupled corpus equations were run and checked. A full empirical two-in-one fit remains unresolved.** The new public source contains 6,434 annotated thoughts from 118 people, but does not separately measure the inward speaker, inward listener, perceived balance or utility. The corpus supplies the field dynamics; it does not yet specify the observation link from those dynamics to these inward roles. No simpler predictor was fitted or substituted in this study.')
p('Within one person, Smoke is inward speaking and Clay is inward listening. Wind, Fog, Water and Mist describe the moving idea itself. Water is perceived balance. Heavy water is D₂O, whose distinct role still needs definition. Each person has their own history; the new measurements do not erase unrecorded history.')
table(['Completed work','Result','What it establishes'],[
 ['Full coupled equations',str(e['completed_coupled_runs'])+' runs and 2 analytic special cases','Numerical behavior under declared dimensionless inputs'],
 ['Real published records','118 people; 12,104 timed records; 6,434 thoughts','Availability and alignment of within-person expression sequences'],
 ['Software and saved results','12 unit tests; '+str(v['count'])+' saved-result checks','Implementation and reproducibility checks'],
 ['Full empirical two-in-one prediction','Not performed','No invented role, geometry, utility or meaning mapping'],
])
h('The equations used')
code('u_t + (u · ∇)u = −∇p + νΔu − (σ/ρ)a(q)e;  ∇·u = 0\nq = |∇S| − Γ\nS_t + u·∇S = DΔS + K_h κ A\nA_t = γ(U − Ubaseline);  A(0) = 0\nT = μ0(∇u + ∇uᵀ)')
p('These come from corpus paragraphs 229–230, 517–519 and 545–550. The [exact source trace](corpus_trace.json) and [equation-to-code table](equation_trace.csv) identify the terms. The solver is byte-identical to the audited earlier full-field implementation. Sharp, signed tanh and smooth exact-off responses remain separate; S remains signed and A has no automatic forgetting. The full system uses a numerical spatial and time discretization, whose errors are checked below.')
p('The corpus also retains the W consistency condition, exact-margin utility optimization and static reciprocal rescaling of S and R. Those formulas are included in the source trace. They have no specified coupling to inward Smoke and Clay in the supplied document, so they have not been silently relabeled or inserted as new dynamics. Running the complete coupled field system is consequently not the same as completing the entire proposed two-in-one application.')
h('A specific limitation found in the full equations')
p('Multiplying γ by four and dividing κ by four multiplied A by four but left every computed S and velocity value, and pressure, unchanged in all three response laws. The numerical difference was exactly zero in these paired calculations. Analytically this follows because only the product κA enters the source: A changes scale while κA does not. Even perfect observations of S and u would not distinguish these two rates separately without an additional scale constraint or an observation of A. Fixing one calibrated rate is a way to resolve this ambiguity without altering the equations.')
p('A second check changed the force strength and diffusion coefficient. The spatial S fields differed by RMS 0.018199 in experiment units and the velocities by RMS 0.004523, while their mean S values were equal. Under these periodic boundaries, the exact total-field identity is M′=κA and M″=κγ(U−Ubaseline). A single total or questionnaire score therefore cannot identify all spatial mechanisms. This identity is derived from the full PDE, not fitted as a replacement predictor.')
image('field_identification','Full coupled numerical trials with synthetic inputs. Equal global totals can hide different spatial fields. No coordinates in this figure have been calibrated to a person’s experience.')
h('Numerical accuracy')
table(['Response law','24 versus 48 grid L2','48 versus 72 grid L2','Time step versus half step L2'],[[r['law'],f"{r['grid24_48']:.3g}",f"{r['grid48_72']:.3g}",f"{r['time_dt_half']:.3g}"] for r in e['refinement']])
p(f"All three trials had smaller successive grid differences. Maximum scalar-total error was {e['max_mass_error']:.2g}; divergence RMS {e['max_divergence']:.2g}; and the energy-balance residual {e['max_energy_identity_residual']:.2g}. Analytic Taylor–Green velocity error was {e['analytic_checks']['taylor_green_velocity_max_error']:.2g}, and advected/diffusing scalar error {e['analytic_checks']['advected_diffusing_scalar_max_error']:.2g}. These finite numerical checks establish neither a general existence theorem nor empirical support for an inner experience model.")
image('refinement','All modes are included in the comparison, including fine-grid modes absent from the coarse calculation. Values describe these runs only.')
h('What the real records contain')
p('The [Su and colleagues think-aloud study](https://doi.org/10.1038/s41467-025-61807-w) provides continuous verbalized thought in a scanner. All 239 selected upstream files were downloaded and hash-checked. Grouping the original timed records by the authors’ thought IDs yields 6,434 thoughts and exactly 6,434 aligned 768-dimensional embedding rows. The audit found no reversed start times, nonpositive durations, overlapping neighboring intervals or missing named transcript fields. Median first-to-last recorded span is 597.735 seconds. These are observations of expressed thought, with an experimental setting that may affect what people say and think.')
p('Three files differ from the usual header layout. Two include eight populated text fragments in extra unnamed columns. Those fragments have not been silently assigned timestamps or merged into thoughts. The [per-file coverage table](results/record_coverage.csv) retains these issues. Before a semantic-content fit, those fragments need reconciliation with the source. The matching row counts alone do not establish that an embedding faithfully preserves a person’s meaning.')
table(['Quantity','Evidence status','Available record','Limit'],coverage)
p('The [2026 data extension](https://doi.org/10.1038/s41597-026-08414-6) adds finer timestamps, externally generated content ratings and questionnaires from the same cohort. Its archive metadata were checked; its ratings were not used as utility. [Descriptive Experience Sampling](https://hurlburt.faculty.unlv.edu/codebook.html) offers more precise reports of inward speaking and hearing, but such labels cannot automatically be equated with Smoke and Clay. The [source review](SOURCES.md) records what was inspected or downloaded.')
h('What would permit the requested full test')
p('The missing step is to define how the recorded observations arise from the full mathematical states. The [measurement contract](MEASUREMENT_CONTRACT.md) lists the exact unresolved connections: the inward roles, the moving idea and intended meaning, the continuous domain, utility, history and idea forms. The question is not whether every hidden field can be measured directly. It is whether a declared observation model makes the full equations distinguishable from alternatives using noisy, partial records.')
p('Once that connection is supplied, reserve people and later episodes before selecting parameters, estimate states from their past only, and propagate the full PDE to predict reserved observations. Compare its force and accumulated-source mechanisms with explicit ablations. The present 118 records are development data because they have now been inspected. A successful numerical run or a good match to a chosen text representation would not by itself establish that the representation measures the inward two-in-one.')
p('This study therefore supplies completed equation tests and a real-data suitability audit. It does not report an invented empirical prediction score. The prior 0.2134 questionnaire-history result remains a separately labeled statistical comparator in the earlier study.')
h('Reproduce and inspect')
code('python -m pip install -r requirements.txt\npython fetch_data.py\npython audit_data.py\npython run_equations.py\npython -m unittest discover -p "test_*.py" -v\npython verify_saved.py\npython build_report.py')
p('Run inside this study directory. Source retrieval needs internet access; raw data go to a sibling work directory outside the publication package. Unit tests and saved-result verification need no network. The [frozen protocol](PROTOCOL.md), [source manifest](source_manifest.json), [equation results](results/equation_results.json), [data audit](results/data_audit.json) and [verification record](results/verification.json) support reproduction. The original corpus SHA256 and solver SHA256 are recorded in the source review and numerical results. The package does not contain participant narratives or demographics.')
p('[Current two-in-one definitions](https://github.com/NousVolition/Nous-Volition/blob/main/studies/community-two-in-one/MODEL.md) · [Streams and Rocks community model](https://github.com/NousVolition/Nous-Volition/blob/main/studies/community-power/README.md)')
(ROOT/'README.md').write_text('\n\n'.join(md)+'\n',encoding='utf-8')
css='body{margin:0;background:#f3f5f4;color:#18332e;font:17px/1.65 system-ui,sans-serif}main{max-width:1100px;margin:30px auto;background:white;padding:36px 44px}h1{font-size:2rem;line-height:1.2}h2{margin-top:2.2rem}a{color:#096b79}pre{white-space:pre-wrap;background:#edf4f2;padding:22px;font-size:.85rem}table{width:100%;border-collapse:collapse;font-size:.9rem}th,td{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #d8e5df}th{background:#eaf4ef}.scroll{overflow:auto}figure{margin:26px 0}img{width:100%;height:auto}figcaption{color:#49645d;font-size:.88rem}@media(max-width:700px){main{padding:20px;margin:0}body{font-size:16px}}'
(ROOT/'report.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Exact corpus equations and two in one data audit</title><style>'+css+'</style></head><body><main>'+''.join(ht)+'</main></body></html>',encoding='utf-8')
print('Built figures, equation and measurement tables, README and HTML report.')
