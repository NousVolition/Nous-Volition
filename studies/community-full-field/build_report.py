from pathlib import Path
import html,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

P=Path(__file__).parent;R=P/'results';F=P/'figures';F.mkdir(exist_ok=True)
d=json.loads((R/'data_results.json').read_text());s=json.loads((R/'spatial_results.json').read_text());pat=json.loads((R/'input_patterns.json').read_text());c=json.loads((R/'data_accounting.json').read_text())
fields=np.load(R/'fields.npz');ev=d['evaluation']['models'];delta=d['paired_field_minus_last_mse'];p=d['parameters']
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(1,2,figsize=(12,4),layout='constrained')
names=['field','last','initial','instantaneous','training_mean'];labels=['Field + H','Last\nanswer','First\nanswer','Instantaneous\nsource','Training\nmean']
ax[0].bar(range(len(names)),[ev[n]['macro_mse'] for n in names],color=['#b65a36','#167c86','#8c979b','#8c979b','#8c979b']);ax[0].set(xticks=range(len(names)),xticklabels=labels,ylabel='Mean squared error, equal weight per group',title='455 comparisons in 127 evaluation groups')
for i,n in enumerate(names):ax[0].text(i,ev[n]['macro_mse']+.004,f"{ev[n]['macro_mse']:.3f}",ha='center')
for name,label,color in [('sharp48','Coupled force','#b65a36'),('no_force24','Force off','#167c86'),('tanh24','Signed tanh','#8b6ab0')]:
    rr=[r for r in s['pilot_records'] if r['pilot']==0 and r['run']==name]
    ax[1].plot([r['time'] for r in rr],[r['mass'] for r in rr],'-o',label=label,color=color,alpha=.7)
ax[1].plot(range(1,5),[0]*4,'k--',label='Observed next correctness')
ax[1].set(xlabel='Submission interval (not seconds)',ylabel='Total S / observed correctness under H',title='Different flows, indistinguishable totals');ax[1].legend(fontsize=9)
fig.savefig(F/'data_comparison.png',dpi=150);plt.close(fig)

fig,ax=plt.subplots(2,3,figsize=(13,8),layout='constrained')
speed_limit=max(np.hypot(fields['p0_'+a][0],fields['p0_'+a][1]).max() for a in ['sharp48','no_force24','tanh24'])
for j,(name,title) in enumerate([('sharp48','Coupled sharp force, 48²'),('no_force24','Force off, 24²'),('tanh24','Signed tanh, 24²')]):
    z=fields['p0_'+name];n=z.shape[-1];grid=np.arange(n)/n
    im=ax[0,j].imshow(z[2].T,origin='lower',extent=[0,1,0,1],cmap='viridis',vmin=min(fields['p0_'+a][2].min() for a in ['sharp48','no_force24','tanh24']),vmax=max(fields['p0_'+a][2].max() for a in ['sharp48','no_force24','tanh24']));fig.colorbar(im,ax=ax[0,j],label='S (assumed units)');ax[0,j].set(title=title,xlabel='x (chosen domain)',ylabel='y (chosen domain)')
    speed=np.hypot(z[0],z[1]);im=ax[1,j].imshow(speed.T,origin='lower',extent=[0,1,0,1],cmap='magma',vmin=0,vmax=speed_limit);fig.colorbar(im,ax=ax[1,j],label='Speed (common scale, assumed units)')
    step=max(1,n//8);xx,yy=np.meshgrid(grid,grid,indexing='ij');ax[1,j].quiver(xx[::step,::step],yy[::step,::step],z[0,::step,::step],z[1,::step,::step],color='white',scale=.7)
    ax[1,j].set(xlabel='x (chosen domain)',ylabel='y (chosen domain)')
fig.suptitle('Computed fields at interval 4 — these are not measured maps of people',fontsize=14)
fig.savefig(F/'fields.png',dpi=150);plt.close(fig)

fp=np.load(R/'input_pattern_fields.npz');fig,axes=plt.subplots(2,4,figsize=(13,7),layout='constrained');axes=axes.ravel()
lo=min(z[2].min() for z in fp.values());hi=max(z[2].max() for z in fp.values())
for ax,(key,z) in zip(axes,fp.items()):
    im=ax.imshow(z[2].T,origin='lower',extent=[0,1,0,1],vmin=lo,vmax=hi,cmap='coolwarm');ax.set(title='Recorded input '+key.removeprefix('input_'),xlabel='x',ylabel='y')
for ax in axes[len(fp.files):]:ax.axis('off')
fig.colorbar(im,ax=list(axes[:len(fp.files)]),label='S after four intervals, common scale',shrink=.7)
fig.suptitle('All seven observed four-input patterns in eligible training sequences\nPost-protocol numerical coverage, not extra held-out validation',fontsize=13)
fig.savefig(F/'input_patterns.png',dpi=150);plt.close(fig)

ref=s['refinement'][0];checks=json.loads((R/'verification.json').read_text())
md=f'''# Full coupled corpus field with real submission records

Completed 22 October 2026 for Streams and Rocks. **The coupled equations have now been run. The proposed link from those fields to task correctness did not outperform a simple last-answer control. Full empirical validation remains open because the records do not measure the spatial fields.**

[Illustrated report](report.html) · [Frozen protocol](PROTOCOL.md) · [Equations, sources and units](SOURCES.md) · [All comparison results](results/data_results.json) · [Spatial diagnostics](results/spatial_results.json)

## What used your exact equations

The solver couples your momentum balance and incompressibility to your signed S transport and accumulated source:

```text
u_t + (u·grad)u = -grad(p) + nu Lap(u) - (sigma/rho) a(q) e
div(u) = 0; q = |grad(S)| - Gamma
S_t + u·grad(S) = D Lap(S) + K_h kappa A
A_t = gamma (U - Ubaseline), A(0) = 0
T = mu0 (grad(u) + grad(u)^T)
```

Source: P229–230, P517–519 and P545–550 of your [pinned corrected corpus](../community-mimesis/corpus_extract.json). Sharp, original signed tanh and smooth exact-off responses are tested separately. The tanh response retains its negative tail. There is no added forgetting, logistic moderation score or replacement of the fixed-direction force with drag. Pressure enforces incompressibility; mean velocity is allowed to change. These are numerical approximations to your equations, not exact arithmetic or a proof of global regularity.

We supply a **specified 2D periodic computational domain** and explicit initial/boundary conditions; we do not claim to reconstruct an unspecified 3D social field or the full Cartesian initial-field construction absent from this attachment. All parameter values and kernel normalization are in the protocol. The corpus's separate consistency W and boundary-utility rules have no supplied coupling to this field system and are not silently turned into decision equations.

## The added observation hypothesis is visible

**H:** use the most recent recorded task correctness (0 or 1) as U for the next interval, and compare the integral of S with the next recorded correctness. This is a proposed measurement link, **not your definition of Sens, Sin or personal utility**. A time unit is one submission interval, not a measured second. Initial total S equals the first recorded correctness; A starts at zero at that observation. Missing earlier history is unknown. The field remains signed; it is never clipped into a probability.

This choice permits a real-data check without inventing unmeasured beliefs, velocities or pressures. It also makes the test conditional: a failure concerns H and its timing, boundary and initialization choices. It does not refute every interpretation of your field equations. **Preserves Sens while adjusting Sin** remains distinct from succeeding at a card task. Water, Fog, Smoke and Clay remain situational descriptions, not measured permanent kinds of person.

## Real measurements and training separation

We used actual explicit card submissions in [DeliData](https://convokit.cornell.edu/documentation/deli.html), from the same pinned public archive used in the earlier study. This is a retrospective internal split, **not a new untouched external dataset**. All {c['records']:,} records lack timestamps. Seven of {c['submissions']:,} submissions are unparsed; 677 sequences have only one valid observation. The remaining **916 participant-within-group sequences yield 1,507 successive comparisons**. Unchanged submissions are retained. We do not use approximate state-of-mind trackers.

All 500 groups were assigned by a fixed hash rule: 350 training, 150 evaluation. After eligibility filtering, **280 training groups provide 1,052 comparisons**, and **127 evaluation groups provide 455 comparisons**. No group crosses the split. Animal aliases are scoped to their group. The earlier use of this archive means the evaluation set cannot be described as pristine model-selection data.

Only the observable accumulated-source coefficient is fitted. Training-only Ubaseline={p['baseline']:.6f}, gamma=1 and **kappa={p['kappa']:.6f}**. The negative coefficient is reported because the corpus does not specify its sign. If nonnegative kappa is imposed as an extra assumption, the training optimum is zero: the total stays at its initial value. No spatial coefficient was fitted to correctness, since these observations cannot identify them.

The recorded previous responses drive the model causally in observation order. The next response is not used in its own prediction. This is a retrospective, observation-driven one-step comparison; it is not an autonomous prediction of all future submissions from the first response alone.

| Method | Evaluation group-macro MSE | Evaluation group-macro MAE |
|---|---:|---:|
| Corpus accumulated source + H | {ev['field']['macro_mse']:.6f} | {ev['field']['macro_mae']:.6f} |
| Last observed answer | {ev['last']['macro_mse']:.6f} | {ev['last']['macro_mae']:.6f} |
| Initial observed answer / nonnegative-kappa fit | {ev['initial']['macro_mse']:.6f} | {ev['initial']['macro_mae']:.6f} |
| Separately assumed instantaneous-source control | {ev['instantaneous']['macro_mse']:.6f} | {ev['instantaneous']['macro_mae']:.6f} |
| Training-target-mean control | {ev['training_mean']['macro_mse']:.6f} | {ev['training_mean']['macro_mae']:.6f} |

Each group receives equal weight, then errors are averaged within group. Accumulated-source MSE minus last-answer MSE is **{delta['estimate']:.5f}**, with a 2,000-resample whole-group 95% bootstrap interval **[{delta['interval95'][0]:.5f}, {delta['interval95'][1]:.5f}]**. Smaller errors are better. The interval is conditional on this mapping and independent-group resampling; stable cross-group worker identities are unavailable. It is not a causal estimate or a test of Girardian rivalry.

**{ev['field']['outside_unit_interval']} of 455 field predictions fall outside [0,1]**, reaching {ev['field']['minimum']:.3f}. This is allowed for signed S, but is a failure of treating its raw integral as bounded correctness. We do not fix it by secretly inserting a sigmoid. The instantaneous control is a different equation and is labelled as such.

![Real-record comparison](figures/data_comparison.png)

## All records use an exact consequence of the full model

For periodic incompressible flow with normalized K, integrating your scalar equation yields **M'=kappa A**. Advection and diffusion integrate to zero. We therefore evaluate all 1,507 comparisons using this exact integral identity; we do not claim to have simulated 1,507 observed spatial fields. It is a consequence of the coupled system, not a substitute differential equation invented for fitting.

This same identity exposes a structural limit: changing viscosity, diffusion, force strength, activation, threshold, kernel width or zero-mean spatial texture cannot change M. Gamma and kappa also appear only as a product in M. More correctness records alone cannot identify these quantities. A good aggregate fit would not validate the full field model either.

## Coupled spatial calculations actually completed

Eighteen primary runs cover two fixed-rule evaluation pilots, three spatial grids (24², 48², 72²), all three response laws, force-off, source-off, uniform initial S and a halved-step control. Both independently selected sequences happen to begin with the same four zeros, so these are **one unique forcing history**, not two independent spatial validations. The choices and that duplication remain in the results.

The declared post-protocol supplement adds **{pat['runs']} runs**, covering every distinct four-input pattern found in eligible training sequences. It changes no coefficients or evaluation outcomes and is numerical coverage, not additional held-out validation.

Maximum mass-identity error is **{s['max_mass_error']:.2e}**; maximum discrete divergence is **{s['max_divergence']:.2e}**; maximum instantaneous energy work/dissipation residual is **{s['max_energy_identity_residual']:.2e}** in the primary runs. These check conserved material, incompressibility and the kinetic-energy identity. They do not claim energy is conserved in this forced viscous system. The force can supply energy, and viscous loss is accounted for.

Taylor–Green analytic velocity and pressure RMS errors are {s['benchmarks']['taylor_green']['velocity_rms_error']:.2e} and {s['benchmarks']['taylor_green']['pressure_rms_error']:.2e}. Halving time steps in that analytic check reduces errors about sixteenfold before roundoff. In the coupled sharp-force pilot, final combined field/velocity Fourier L2 differences are **{ref['n24_vs_n48']:.3e}** (24² versus 48²) and **{ref['n48_vs_n72']:.3e}** (48² versus 72²); halving the 24² time step gives **{ref['n24_dt_vs_half']:.3e}**. Adjacent-grid differences are estimates, not error against an exact coupled solution, and unequal refinement ratios do not establish an order of accuracy. Non-polynomial activation can retain aliasing; see the method clarification.

![Computed fields with different forces](figures/fields.png)

Turning off the force changes final spatial S by RMS **{s['identifiability_examples'][2]['spatial_S_rms_difference']:.6f}** and velocity components by RMS **{s['identifiability_examples'][2]['velocity_rms_difference']:.6f}**, while the total-field difference is {s['identifiability_examples'][2]['mean_S_difference']:.1e}. This is an explicit example of different internal dynamics fitting the same measured total. The displayed coordinates and velocities are computational assumptions, not maps of social actors.

![Coverage of actual training input patterns](figures/input_patterns.png)

## What is supported, and what remains untested

* **Supported numerically:** the coupled implementation preserves your accumulated source, fixed-direction force, distinct responses, incompressibility and stress relation under the declared domain and numerical approximation. The integrated equation agrees with the spatial solver.
* **Supported by these observations:** under H, the accumulated field is less accurate than last-answer persistence. Negative fitted kappa, out-of-range totals and unidentifiable spatial parameters are reported, not repaired through unacknowledged changes.
* **Still untested:** whether a defensible measurement of S and U corresponds to human meaning, reciprocal copying, personal utility, treatment or penalties; whether a spatial metric and measured transitions support this continuum representation; and whether independently collected observations validate it. There is no supplied field-to-W or penalty-to-U equation. The prior public-record moderation findings remain separate.

The next empirical requirement is an observation specification and data that can distinguish spatial predictions: repeated observations at declared positions, a defined field quantity, measured inputs and time, initial/boundary information, and any proposed observation-to-decision link. The units and comparison must be fixed before fitting. A smoother plot alone cannot supply this evidence.

## Reproduce and inspect

**17 unit tests and {checks['saved_checks']:,} independent saved-result checks passed.** [Verification receipt](results/verification.json). All individual predictions are in [forecasts.csv](results/forecasts.csv); [group scores](results/group_scores.csv) and [derived observation sequences](results/sequences.json) support independent arithmetic. No source conversation text or aliases are published.

```bash
python -m pip install -r requirements.txt
python -m unittest -q
python verify_saved.py
python data_test.py
python run_spatial.py
python run_input_patterns.py
python verify_saved.py
python build_report.py
# To repeat extraction from the pinned raw archive:
python data_test.py --raw /your/local/deli-corpus.zip
```

Run from this study directory inside the repository; the existing community-mimesis study supplies the unchanged card parser. The local NumPy version is pinned; CI also checks compatibility with the repository's installed NumPy. Figures use Matplotlib. Inspect [field.py](field.py), [data_test.py](data_test.py), [the full sources and limitations](SOURCES.md), and the [protocol](PROTOCOL.md). Numerical domain parameters are reproducible choices, not fitted human constants.
'''
(P/'README.md').write_text(md,encoding='utf-8')

def inline(t):
    import re
    t=html.escape(t);t=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',t)
    t=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',t);t=re.sub(r'`([^`]+)`',r'<code>\1</code>',t);return t
parts=[];in_code=False;table=[]
def flush_table():
    if table:
        parts.append('<div class="scroll"><table>'+''.join('<tr>'+''.join(('<th>' if i==0 else '<td>')+inline(v.strip())+('</th>' if i==0 else '</td>') for v in line.strip('|').split('|'))+'</tr>' for i,line in enumerate(table) if i!=1)+'</table></div>');table.clear()
for line in md.splitlines():
    if line.startswith('```'):
        flush_table();parts.append('</pre>' if in_code else '<pre>');in_code=not in_code;continue
    if in_code:parts.append(html.escape(line)+'\n');continue
    if line.startswith('|'):table.append(line);continue
    flush_table()
    if not line:continue
    if line.startswith('#'):
        level=len(line)-len(line.lstrip('#'));parts.append(f'<h{level}>'+inline(line[level:].strip())+f'</h{level}>')
    elif line.startswith('!['):
        alt,url=line[2:].split('](');parts.append('<img alt="'+html.escape(alt)+'" src="'+html.escape(url[:-1])+'">')
    elif line.startswith('* '):parts.append('<p class="item">'+inline(line[2:])+'</p>')
    else:parts.append('<p>'+inline(line)+'</p>')
flush_table()
(P/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Full corpus field and real records</title><style>body{font:17px/1.6 system-ui;color:#20343d;max-width:1150px;margin:auto;padding:35px 25px}h1{line-height:1.2}h2{margin-top:2.2em}a{color:#096b89}img{width:100%;height:auto;margin:22px 0}pre{background:#edf3f5;padding:18px;overflow:auto}table{border-collapse:collapse;width:100%;font-size:15px}th,td{padding:10px;border-bottom:1px solid #bbc8ce;text-align:left}.scroll{overflow:auto}.item{padding-left:16px;border-left:3px solid #177c86}</style><main>'+''.join(parts)+'</main></html>',encoding='utf-8')
print('Built README, report and three figures.')


# Preserve the source-chain audit when this historical report is rebuilt.
from audit_note import apply_notice
apply_notice(Path(__file__).resolve().parent)
