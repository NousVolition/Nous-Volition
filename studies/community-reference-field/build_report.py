from pathlib import Path
import html,json,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).parent;R=P/'results';F=P/'figures';F.mkdir(exist_ok=True)
r=json.loads((R/'field_results.json').read_text());d=json.loads((R/'descriptive.json').read_text());a=json.loads((R/'accounting.json').read_text());lock=json.loads((R/'fit_lock.json').read_text());v=json.loads((R/'verification.json').read_text());e=json.loads((R/'episodes.json').read_text());test=[x for x in e if x['split']=='evaluation'];z=np.load(R/'fields.npz');p=r['parameters']
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
names=['coupled','force_off','source_off','initial','last'];labels=['Corpus\ncoupled','Force\noff','Source\noff','Initial\nfield','Last observed\nfield']
values=[r['runs'][n]['mse'] for n in names];ax[0].bar(range(5),values,color=['#127a87','#88a5aa','#8c979b','#b8b9ac','#c16e42']);ax[0].set(xticks=range(5),xticklabels=labels,ylabel='Spatial field MSE (not correctness error)',title='64 evaluation episodes, 128 intervals');ax[0].set_ylim(0,max(values)*1.15)
for i,x in enumerate(values):ax[0].text(i,x+.18,f'{x:.3f}',ha='center')
for i,name in enumerate(['initial','last','force_off']):
    item=r['paired_mse_differences'][name];mu=item['mean'];lo,hi=item['interval95'];ax[1].errorbar(mu,i,xerr=[[mu-lo],[hi-mu]],fmt='o',capsize=4,color='#127a87')
ax[1].axvline(0,color='#777',lw=1);ax[1].set(yticks=range(3),yticklabels=['Minus initial field','Minus last observed','Minus force off'],xlabel='Paired MSE difference with 95% interval',title='Negative values favor the coupled prediction');ax[1].invert_yaxis()
fig.savefig(F/'field_comparison.png',dpi=160);plt.close(fig)

fig,ax=plt.subplots(2,3,figsize=(12,8),layout='constrained')
case=test[0];points0=np.array(case['points'][0]);fields=[z['targets'][0,0],z['targets'][0,1],z['targets'][0,2],z['coupled'][0,2,0],z['coupled'][1,2,0],z['force_off'][1,2,0]]
titles=['Initial annotated reference','Next annotated reference','Following annotated reference','Predicted next reference','Predicted following reference','Following prediction: force off'];hi=max(x.max() for x in fields);lo=min(0,min(x.min() for x in fields))
for i,(aa,field,title) in enumerate(zip(ax.flat,fields,titles)):
    im=aa.imshow(field.T,origin='lower',extent=[0,1,0,1],vmin=lo,vmax=hi,cmap='viridis');aa.set(title=title,xlabel='x / 430',ylabel='y / 430')
    if i<3:
        pts=np.array(case['points'][i]);aa.scatter(pts[:,0],pts[:,1],marker='x',color='white',s=45)
fig.colorbar(im,ax=list(ax.flat),label='Smoothed reference count per unit area',shrink=.8)
fig.suptitle('First evaluation case in the fixed hash order — dots remain stationary; references change',fontsize=13)
fig.savefig(F/'reference_fields.png',dpi=160);plt.close(fig)

fig,ax=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
for i,(key,lab) in enumerate([('changed_wording','Changed wording'),('unchanged_wording','Unchanged wording')]):
    q=d[key];mu=100*q['mean'];lo,hi=np.array(q['interval95'])*100;ax[0].errorbar(mu,i,xerr=[[mu-lo],[hi-mu]],fmt='o',capsize=4,label=lab)
ax[0].axvline(0,color='#777',lw=.8);ax[0].set(yticks=[0,1],yticklabels=['Changed wording','Unchanged wording'],xlabel='Later minus earlier annotation agreement (pp)',title='Same annotated objects, later expressions');ax[0].invert_yaxis()
ax[1].bar(['Same referent set','Different referent set'],[a['repeated_wording_comparisons']-a['repeated_wording_changed_referent'],a['repeated_wording_changed_referent']],color=['#127a87','#c16e42']);ax[1].set(ylabel='Repeated-wording comparisons',title='Identical words can refer to different objects')
fig.savefig(F/'wording.png',dpi=160);plt.close(fig)

mean=d['changed_wording'];ci=r['paired_mse_differences'];ref=r['refinement'];allpred=np.load(R/'scalar_predictions.npz');coarse4=float(np.mean((allpred['coupled'][:,:4]-allpred['targets'][:4,1:].transpose(1,0,2,3))**2))
md=f'''# Real reference, expression and interaction over time

**Completed 22 October 2026 for Streams and Rocks.** We acquired OneCommon, a new public source with human reference interpretations, actual expressions, message timestamps and object coordinates. We ran the coupled corpus equations against observed spatial reference fields under an explicit measurement hypothesis. The model improves over keeping the initial field fixed, but its advantage over the last observed field is uncertain, and switching off its added force gives almost the same performance.

[Illustrated report](report.html) · [Frozen protocol](PROTOCOL.md) · [Sources, equation traceability and limitations](SOURCES.md) · [Field results](results/field_results.json) · [All episode predictions](results/predictions.csv)

## What changed from the earlier correctness test

The previous comparison used correct/incorrect task answers as an assumed field observable. Here the reference labels are made by multiple human annotators, linked to actual visible objects and dialogue times. This measures **a specific part of meaning: what an expression refers to**. It does not measure all intended meaning, the speaker's private utility or every social implication.

The source is [Udagawa and Aizawa's OneCommon reference-resolution corpus](https://doi.org/10.1609/aaai.v34i05.6442), pinned to [repository commit 19125f2](https://github.com/Alab-NII/onecommon/tree/19125f2edc38c20341bfbb1756154aacdaa4f149). We searched CoDraw and Minecraft dialogue resources as alternatives; the [source comparison](SOURCES.md) explains the selection. Original dialogue text and worker identities are not republished.

**The earlier 0.140 versus 0.104 result meant the proposed correctness mapping added complexity without improving prediction.** The new errors below have different units—spatial reference-field error—and must not be compared numerically with those correctness errors.

## Meaning, wording and interaction: actual observations

The downloaded source contains **6,760 dialogues**, with reference annotations for 5,191. The original project annotated successful dialogues only. After excluding 129 dialogues with administrative adjudication, this analysis uses **5,062 dialogues**. It retains **32,795 expressions** with concrete, non-ambiguous aggregate referents and at least three worker judgements. It excludes 3,259 expressions lacking concrete/confident reference under this rule and 4,330 lacking the required worker votes. These are counts from the pinned repository version, not an asserted reproduction of every earlier paper total.

All 5,191 annotated dialogues matched original message counts and speaker order during schema inspection; original message times were strictly increasing. The expression text has the authors' spelling/grammar normalization. Annotators had access to full conversations, so their current-reference labels may reflect later context. This is a retrospective annotation test, not a live language-understanding evaluation.

There are **5,358 within-speaker pairs** referring to the same annotated object set in different utterances: **5,045 use changed wording** and 313 use unchanged wording. Among changed-wording pairs, later interpretation agreement is **{100*mean['mean']:.2f} percentage points higher**, with a whole-dialogue bootstrap interval of **[{100*mean['interval95'][0]:.2f}, {100*mean['interval95'][1]:.2f}] points**. The unchanged-wording change is {100*d['unchanged_wording']['mean']:.2f} points, with interval [{100*d['unchanged_wording']['interval95'][0]:.2f}, {100*d['unchanged_wording']['interval95'][1]:.2f}]. These are separate within-group changes, not a randomized changed-versus-unchanged effect.

**Same referent is narrower than same meaning.** An abbreviated reference can identify the same dot while dropping descriptive content and relying more on context. Later context also changes. The result does not establish that changing wording caused better understanding, nor does annotation agreement directly measure the other participant's understanding.

Conversely, **195 of 524 repeated-wording comparisons refer to different object sets**. Identical words do not guarantee identical reference. Across **12,188 consecutive cross-speaker eligible transitions**, mean within-dialogue referent-set Jaccard overlap is {d['cross_speaker_jaccard']['mean']:.3f} [{d['cross_speaker_jaccard']['interval95'][0]:.3f}, {d['cross_speaker_jaccard']['interval95'][1]:.3f}]. This records shared/different reference through interaction; it does not establish copying, rivalry or a causal memory effect.

![Wording and reference](figures/wording.png)

## Your governing equations remain the specification

```text
u_t + (u·grad)u = -grad(p) + nu Lap(u) - (sigma/rho) a(q)e
div(u)=0; q=|grad(S)|-Gamma
S_t + u·grad(S) = D Lap(S) + K_h kappa A
A_t=gamma(U-Ubaseline); A(0)=0
T=mu0 (grad(u)+grad(u)^T)
```

These are the coupled momentum, incompressibility, field transport, accumulated input and stress relations from P229–230, P517–519 and P545–550 of your [exact corpus excerpts](../community-mimesis/corpus_extract.json). Sharp, original signed tanh and smooth exact-off responses remain separate laws. We retain the signed tanh tail, the fixed force direction and the velocity zero mode. There is no added decay, logistic decision score, clipping of S or substitution of drag for the corpus force. The batched implementation is tested against the unchanged [single-case solver](../community-full-field/field.py).

**H_ref is the added measurement hypothesis:** each utterance's distinct annotated referents become a smooth spatial S field, with one unit integral per object. U is the mean agreement of human interpreters for that utterance, used as an explicit recoverability-utility proxy. The model receives annotated states and agreement values; it does not infer these from raw language. Personal utility and Sens are not thereby measured.

Positions come from each speaker's own view, scaled by 430 coordinate units. Actual elapsed time is measured in minutes. Objects stay stationary; the location of reference changes. The unit-square periodic topology, kernel width .12, initial u=0, initial A=0 and fixed source at the initial referent centroid are explicit assumptions. The source does not measure those latent flows or supply physical periodic social boundaries. These choices are detailed in the protocol.

## Training-only selection and reserved evaluation

There are **1,657 eligible speaker episodes**, each containing the first three retained referential utterances with positive intervals no longer than 120 seconds. A fixed hash rule assigned entire visual scenarios to training or evaluation. The numerical pilot selects **64 independent scenario episodes in each split** in hash order, with no error-based selection. The 128 numerical episodes are a tractable subset; descriptive analyses above use all retained records.

On the 64 training episodes, the integrated mass identity fits Ubaseline={p['baseline']:.6f}, gamma=1 and **kappa={p['kappa']:.6f}**. Nine coupled candidates and three force-off controls were evaluated on training fields only. The selected coupled candidate has **sigma={p['sigma']}, D={p['diffusivity']}**, nu=.02 and Gamma=1. This is the smallest tested positive force and largest tested diffusion; it is not a unique measured human constant or a demonstrated global optimum. The [selection lock](results/fit_lock.json) was written before evaluation.

The coupled system evolves across both measured intervals without a middle-state reset. Its next source input uses only the previous observed annotation agreement. The last-observed-field control receives the actual middle spatial field for its second prediction, an information advantage; the initial-field control uses the same initial spatial observation as the model. Both are shown.

| Evaluation method | Spatial MSE | Spatial MSE after removing field-mean error |
|---|---:|---:|
| Coupled corpus field | {r['runs']['coupled']['mse']:.6f} | {r['runs']['coupled']['shape_mse']:.6f} |
| Force off, training-selected diffusion | {r['runs']['force_off']['mse']:.6f} | {r['runs']['force_off']['shape_mse']:.6f} |
| Accumulated source off | {r['runs']['source_off']['mse']:.6f} | {r['runs']['source_off']['shape_mse']:.6f} |
| Keep initial reference field | {r['runs']['initial']['mse']:.6f} | {r['runs']['initial']['shape_mse']:.6f} |
| Keep last observed reference field | {r['runs']['last']['mse']:.6f} | {r['runs']['last']['shape_mse']:.6f} |

Each episode contributes the mean of two interval errors, each averaged over the observation grid. There are **128 evaluation intervals**. The coupled-minus-control paired MSE differences, with 2,000-resample scenario bootstrap intervals, are:

* Initial-field control: **{ci['initial']['mean']:.4f} [{ci['initial']['interval95'][0]:.4f}, {ci['initial']['interval95'][1]:.4f}]**.
* Last-observed-field control: **{ci['last']['mean']:.4f} [{ci['last']['interval95'][0]:.4f}, {ci['last']['interval95'][1]:.4f}]**.
* Force-off control: **{ci['force_off']['mean']:.5f} [{ci['force_off']['interval95'][0]:.5f}, {ci['force_off']['interval95'][1]:.5f}]**.

Negative values favor the coupled prediction. **The pilot supports improvement over a frozen initial field, but does not establish an advantage over the last observed field or over force-off diffusion.** Removing the accumulated source barely changes the score. Most of the improvement is also available without the proposed field-dependent force. The alternative tanh and smooth-off scores are {r['runs']['signed_tanh']['mse']:.6f} and {r['runs']['smooth_off']['mse']:.6f}; they are sensitivities at fixed parameters, not independently tuned winners. Kappa is positive here, so the nonnegative-kappa control is identical.

![Field prediction comparisons](figures/field_comparison.png)

## What was actually simulated and checked

The run completed **768 training episode simulations** (12 candidates × 64), **384 evaluation episode simulations** (six settings × 64), and **eight refinement simulations**. The two persistence controls are computed directly from observations. Every numerical episode solves the coupled PDE system; this study does not assess only its total-field identity.

The selected model's maximum mass-identity error is {r['runs']['coupled']['max_mass_error']:.2e}, divergence RMS is at most {r['runs']['coupled']['max_divergence']:.2e}, and instantaneous energy work/dissipation residual is at most {r['runs']['coupled']['max_energy_identity']:.2e}. The latter checks accounting of forcing and viscous loss, not energy conservation in a driven dissipative model. Pressure and symmetric stress diagnostics are saved; neither was measured in the conversations.

For the first four evaluation cases, final combined field/velocity differences between 16² and 32² grids range from {min(ref[0]['differences']):.2e} to {max(ref[0]['differences']):.2e}. Halving the 16² time step changes final component-RMS values by at most {max(ref[1]['differences']):.2e}. On those **same four cases**, coarse-grid MSE is {coarse4:.6f} and finer-grid MSE is {ref[0]['mse']:.6f}; these subset scores are not the all-64 score. Grid differences are not exact-solution error estimates, and only four cases were refined.

![Actual annotated reference and model predictions](figures/reference_fields.png)

**12 unit tests and {v['saved_checks']:,} saved-result checks pass.** They cover source/selection provenance, batch-versus-single-case dynamics, analytical accumulated mass, pixelwise errors, bootstrap intervals, incompressibility and energy accounting. All candidate scores and all failures/limits are retained.

## What the new evidence supports

The same annotated object set can persist while expression changes, and the same words can point to different objects. That is a concrete, observable connection between reference, expression and context over time. It is compatible with **preserves Sens while adjusting Sin**, but it tests only the referential component of that distinction.

The field model can now be compared against spatially grounded reference trajectories. This is a stronger test than the earlier correctness mapping, yet **the distinctive force and accumulated source have not earned a demonstrated predictive advantage here**. Diffusion-like smoothing accounts for much of the apparent gain. Numerical precision cannot resolve missing empirical definitions of social velocity, pressure, utility or decision coupling.

This source has no matched moderation decisions, penalty histories or unsuccessful annotated dialogues suitable for testing rivalry outcomes. Water, Fog, Smoke and Clay remain situational descriptions; we do not assign those types from reference agreement. A successful reference task is not proof of a helpful double, and a shifted referent is not proof of a rival.

## Reproduce

```bash
python -m pip install -r requirements.txt
python -m unittest -q
python verify_saved.py
python download_data.py --raw /your/local/onecommon
python extract.py --raw /your/local/onecommon
python analyze.py
python verify_saved.py
python build_report.py
```

Run inside this study in the repository; it imports the pinned community-full-field solver. [Source and units](SOURCES.md), [protocol](PROTOCOL.md), [verification receipt](results/verification.json), [numeric episodes](results/episodes.json), [field arrays](results/scalar_predictions.npz), and [compressed wording-pair records](results/wording_pairs.json.gz) make the calculation inspectable. The gzip files contain JSON and are losslessly readable with Python's standard gzip module. Source texts and worker IDs remain outside the published package.
'''
(P/'README.md').write_text(md,encoding='utf-8')
def inline(s):
    s=html.escape(s);s=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s);s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s);return re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
parts=[];code=False;table=[]
def flush():
    if table:
        parts.append('<div class="scroll"><table>'+''.join('<tr>'+''.join(('<th>' if i==0 else '<td>')+inline(v.strip())+('</th>' if i==0 else '</td>') for v in line.strip('|').split('|'))+'</tr>' for i,line in enumerate(table) if i!=1)+'</table></div>');table.clear()
for line in md.splitlines():
    if line.startswith('```'):flush();parts.append('</pre>' if code else '<pre>');code=not code;continue
    if code:parts.append(html.escape(line)+'\n');continue
    if line.startswith('|'):table.append(line);continue
    flush()
    if not line:continue
    if line.startswith('#'):
        level=len(line)-len(line.lstrip('#'));parts.append(f'<h{level}>'+inline(line[level:].strip())+f'</h{level}>')
    elif line.startswith('!['):
        alt,url=line[2:].split('](');parts.append('<img src="'+html.escape(url[:-1])+'" alt="'+html.escape(alt)+'">')
    elif line.startswith('* '):parts.append('<p class="item">'+inline(line[2:])+'</p>')
    else:parts.append('<p>'+inline(line)+'</p>')
flush();(P/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reference, expression and field dynamics</title><style>body{font:17px/1.6 system-ui;max-width:1150px;padding:35px 25px;margin:auto;color:#20343d}h1{line-height:1.2}h2{margin-top:2.2em}a{color:#096b89}img{width:100%;height:auto;margin:20px 0}pre{overflow:auto;background:#edf3f5;padding:18px}table{border-collapse:collapse;width:100%;font-size:15px}td,th{padding:10px;border-bottom:1px solid #b8c8cf;text-align:left}.scroll{overflow:auto}.item{border-left:3px solid #127a87;padding-left:16px}</style><main>'+''.join(parts)+'</main></html>',encoding='utf-8');print('Built report, README and three figures.')
