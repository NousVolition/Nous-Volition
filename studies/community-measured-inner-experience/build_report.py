from pathlib import Path
import csv,json,html
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
P=Path(__file__).resolve().parent
R=P/'results'
rows=list(csv.DictReader((R/'paired_visq.csv').open(encoding='utf-8')))
main=[r for r in rows if r['cohort']=='all_supplied']
sensitivity=[r for r in rows if r['cohort']=='exclude_fractional_flag']
audit=json.loads((R/'measurement_audit.json').read_text(encoding='utf-8'))
mapping=json.loads((P/'measurement_map.json').read_text(encoding='utf-8'))
fig,axes=plt.subplots(1,2,figsize=(12,5.6),layout='constrained')
for entries,offset,color,label in [(main,-.09,'#17638b','31 supplied participant records'),(sensitivity,.09,'#b65f28','30 excluding fractional-sum flag')]:
    y=np.arange(len(entries))+offset;m=np.array([float(r['mean_difference']) for r in entries]);lo=np.array([float(r['bootstrap_low']) for r in entries]);hi=np.array([float(r['bootstrap_high']) for r in entries])
    axes[0].errorbar(m,y,xerr=[m-lo,hi-m],fmt='o',color=color,capsize=3,label=label)
axes[0].axvline(0,color='#555',lw=.8);axes[0].set_yticks(np.arange(5),[r['subscale'] for r in main]);axes[0].invert_yaxis();axes[0].set_xlabel('Rumination minus distraction (sum-score points)');axes[0].set_title('Measured inner-speech differences\n95% participant bootstrap intervals');axes[0].legend(fontsize=8,loc='lower right')
left=np.zeros(5)
for key,label,color in [('positive','Higher in rumination','#17638b'),('tied','Same score','#b4b4b4'),('negative','Lower in rumination','#b65f28')]:
    values=np.array([int(r[key]) for r in main]);axes[1].barh(np.arange(5),values,left=left,color=color,label=label)
    for i,(x,v) in enumerate(zip(left,values)):
        if v:axes[1].text(x+v/2,i,str(v),ha='center',va='center',color='white' if key!='tied' else 'black',fontsize=9)
    left+=values
axes[1].set_yticks(np.arange(5),[r['subscale'] for r in main]);axes[1].invert_yaxis();axes[1].set_xlabel('Participants (n = 31)');axes[1].set_title('People did not all change the same way');axes[1].legend(fontsize=8,loc='lower right')
for ax in axes:ax.spines[['top','right']].set_visible(False)
for ax in axes:ax.legend(fontsize=8,loc='upper left',bbox_to_anchor=(0,-.18),frameon=False)
fig.savefig(R/'inner_experience.png',dpi=160);plt.close(fig)
table='\n'.join(f"| {r['subscale']} | {float(r['mean_difference']):+.3f} | [{float(r['bootstrap_low']):.3f}, {float(r['bootstrap_high']):.3f}] | {r['positive']} / {r['tied']} / {r['negative']} | {float(r['p_holm_five']):.4g} |" for r in main)
text=f'''# Real inner-experience measurements for the two-in-one

**New public data were analyzed. The full empirical corpus-equation test remains unperformed.** These files do not identify inward Smoke, Clay, the moving idea and personal history well enough to initialize and score the coupled field model. No simpler predictive model was fitted and no missing history was set to zero. This is new measurement evidence and a specific account of what prevents the requested full test, not a claim of completion.

## What was actually measured and calculated

In [Moffatt et al. (2020)](https://doi.org/10.1371/journal.pone.0238920), the public workbook links the same 31 people across rumination and distraction. We recomputed all five supplied inner-speech subscale contrasts. Values are two-item sum-score points (possible 2–14), not field values or measurements of the author's roles. These are retrospective self-reports with measurement error.

| Subscale | Mean difference | 95% bootstrap interval | Higher / same / lower | Holm p (five contrasts) |
|---|---:|---|---:|---:|
{table}

![Measured inner-experience differences](results/inner_experience.png)

Dialogic and evaluative differences survive excluding the one record flagged by fractional distraction sums: +2.467 and +2.100 points (n=30). The source reports two mean-imputed items. Raw item flags are unavailable, so this exclusion is a sensitivity check, not an authenticated reconstruction of the original missing data. This analysis adds no imputation. Condition-order results are saved separately; order is limited experimental context, not each person's life history. The other three overall intervals include zero; that does not prove equality.

Bootstrap resamples whole people within each comparison (20,000; seed 20261023). Paired t intervals and Holm-corrected tests are also saved. Sum-score arithmetic is descriptive, and the sample is small. The articles' findings were read before analysis: this is exploratory reproduction, not a new holdout validation of the corpus model.

## Ordered ideas: a second real dataset

[Labrie and de Chantal (2026)](https://doi.org/10.1177/02762366261446941) provides 350 identified participants, retrospective inner-dialogue ratings and 3,349 response records. Our join audit finds:

- 3,108 author-coded valid responses, all linked to those 350 participants. Three invalid responses belong to one unmatched ID and remain excluded from person-linked results.
- 201 additional subject-sheet rows contain only a fluency value and no participant ID. They are isolated numeric values, not extra participants or formula cells. Their origin is unresolved. Fluency is not analyzed here.
- 694 observed person/prompt sequences; 344 people have records for both prompt orders. Four sequences have internal order gaps. No missing ideas are interpolated.
- 2,375 consecutive valid response pairs; 169 share a supplied content category. Category equality is not verified same intended meaning, an inward encounter, or copying.
- No per-idea timestamps. Total survey duration cannot supply the spacing between ideas or felt time.
- All 350 saved four-item state means reproduce exactly from the supplied item values. However, survey display labels and explicit recodes run in opposite directions; the export-to-analysis transformation is unresolved. We do not reverse scores or infer the direction of a dialogue/originality association.
- Four survey questions concern links between ideas, but their response columns are absent from these workbooks. A question being asked in an instrument is not evidence that its answers are available.

## Connection to the author's model

The [measurement ledger](measurement_map.json) preserves Smoke as inward putting-forward, Clay as inward receiving/holding/questioning/reshaping/refusing, and the moving idea within the same person. Water is perceived balance; Fog concerns clarity; Wind concerns experienced time; Mist concerns internalized agreement; D₂O denotes the consequential small change. These forms are not inferred from unrelated questionnaire names. H₂O₂ remains separately unspecified.

The [corpus and Miro reconciliation](CORPUS_AND_MIRO.md) records the exact equations, source hashes and inspected frames/pages. In particular, S means the signed status/context field, not Sens. The Miro arrows require an operational connection between measurements and the field. The model's accumulated A cannot be reconstructed from age, a trait score or the number of prior answers.

An empirical test can estimate latent states; it need not observe every mathematical variable directly. What is missing here is an identifiable observation model with a shared domain/metric, time scale, personal prehistory/initial state, utility input/baseline, boundary/source specification and independently evaluable outcomes. Making those numbers up would recreate the shortcut the user rejected. The exact equations are retained; no new synthetic run is presented as evidence for them.

**Status:** measurement comparisons completed; full two-in-one empirical test not completed. The data neither validate nor falsify the full model. The next necessary evidence is a linked within-person record of idea content/expression, inward proposal and reception, relevant individual history and the defined forms, followed by identification of how those observations read out the unchanged field. That observation layer must be declared and tested rather than silently built into a fit.

## Reproduce and inspect

Python 3.12; versions in [requirements.txt](requirements.txt) and [run status](results/run_status.json).

```sh
python -m pip install -r requirements.txt
python fetch_data.py --data-dir raw-data
python analyze.py --data-dir raw-data
python build_report.py
python -m unittest test_measurements.py -v
python verify.py
```

Raw files remain at their public sources; the repository contains hashes and a downloader, aggregates and code. No participant narratives are republished. [Source manifest](sources.json), [analysis plan](ANALYSIS_PLAN.md), [all contrasts](results/paired_visq.csv), [order sensitivity](results/order_sensitivity.csv), [measurement audit](results/measurement_audit.json).

The earlier [observation-bridge study](https://github.com/NousVolition/Nous-Volition/tree/main/studies/community-observation-bridge) remains a conditional numerical study with assumed inputs. These new data do not retroactively turn its trajectories into empirical forecasts.
'''
(P/'README.md').write_text(text,encoding='utf-8')
# Simple self-contained HTML; prose mirrors the reviewed Markdown source.
parts=[];in_code=False;table_open=False;list_open=False
for line in text.splitlines():
    if line.startswith('```'):
        parts.append('</code></pre>' if in_code else '<pre><code>');in_code=not in_code;continue
    if in_code:parts.append(html.escape(line)+'\n');continue
    if line.startswith('|'):
        if not table_open:parts.append('<div class="scroll"><table>');table_open=True
        if set(line.replace('|','').replace('-','').replace(':','').strip())==set():continue
        parts.append('<tr>'+''.join('<td>'+html.escape(c.strip())+'</td>' for c in line.strip('|').split('|'))+'</tr>');continue
    if table_open:parts.append('</table></div>');table_open=False
    if not line.startswith('- ') and list_open:parts.append('</ul>');list_open=False
    def fmt(s):
        import re
        s=html.escape(s)
        s=re.sub(r'!\[([^]]*)\]\(([^)]+)\)',r'<img alt="\1" src="\2">',s)
        s=re.sub(r'\[([^]]*)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
        s=re.sub(r'\*\*(.*?)\*\*',r'<strong>\1</strong>',s)
        return s
    if line.startswith('# '):parts.append('<h1>'+fmt(line[2:])+'</h1>')
    elif line.startswith('## '):parts.append('<h2>'+fmt(line[3:])+'</h2>')
    elif line.startswith('- '):
        if not list_open:parts.append('<ul>');list_open=True
        parts.append('<li>'+fmt(line[2:])+'</li>')
    elif line:parts.append('<p>'+fmt(line)+'</p>')
(P/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Measured inner experience — Streams and Rocks</title><style>body{max-width:1080px;margin:40px auto;padding:0 24px;font:17px/1.6 system-ui;color:#21323a}h1{font-size:34px;line-height:1.2}h2{margin-top:36px;color:#164b65}a{color:#12658a}img{width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:15px}td{padding:10px;border-bottom:1px solid #ddd}tr:first-child{font-weight:bold;background:#edf3f5}.scroll{overflow-x:auto}pre{padding:18px;background:#f3f5f6;overflow-x:auto}</style><main>'+''.join(parts)+'</main></html>',encoding='utf-8')
print('Report and figure written')
