from pathlib import Path
import json,html
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from corpus_equations import response

p=Path(__file__).parent;r=p/'results';f=p/'figures';f.mkdir(exist_ok=True)
d=json.loads((r/'observed_results.json').read_text());e=json.loads((r/'equation_results.json').read_text());audit=json.loads((r/'audited_outcomes.json').read_text())
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
q=np.linspace(-2,3,501)
for name,label in [('sharp','Sharp'),('tanh','Original signed tanh'),('smooth_off','Smooth exact off')]:ax[0,0].plot(q,response(q,name),label=label)
ax[0,0].axhline(0,color='#777',lw=.6);ax[0,0].set(xlabel='q (epsilon = 1)',ylabel='a(q)',title='Your three laws retain their differences');ax[0,0].legend(fontsize=9)
g=e['grid_refinement'];ax[0,1].loglog([x['n'] for x in g],[x['l2_error'] for x in g],'o-',color='#227a91')
ax[0,1].set(xlabel='Periodic grid cells',ylabel='RMS error against exact transport',title='Exact corpus transport equation, chosen test domain')
a=d['deli']['candidate_uptake'];ax[1,0].bar(['Became\ncorrect','Became\nincorrect','Stayed\nincorrect'],[a['improved'],a['worsened'],a['unchanged_incorrect']],color=['#227a91','#b14e33','#8e9498'])
for i,n in enumerate([a['improved'],a['worsened'],a['unchanged_incorrect']]):ax[1,0].text(i,n+1,str(n),ha='center')
ax[1,0].set(ylabel='Observed changed submissions',title='162 candidate answer-uptake changes');ax[1,0].set_ylim(0,105)
keys=['primary.any','primary.reciprocal','fourgram.any','quotes.any'];labs=['Unquoted reuse','Reciprocal reuse','Four-token reuse','Including quotes']
for i,k in enumerate(keys):
    z=d['cga'][k];v=z['paired_difference']*100;lo,hi=np.array(z['cluster_bootstrap_interval'])*100
    ax[1,1].errorbar(v,i,xerr=[[v-lo],[hi-v]],fmt='o',capsize=4,color='#227a91' if i<3 else '#b14e33')
ax[1,1].axvline(0,color='#777',lw=.8);ax[1,1].set(yticks=range(4),yticklabels=labs,xlabel='Removed minus control branches (percentage points)',title='Early phrase reuse and later attack removal');ax[1,1].invert_yaxis()
fig.savefig(f/'findings.png',dpi=160);plt.close(fig)
def table(headers,rows):return '<div class="table"><table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
dt=table(['Changed-answer group','n','Became correct','Became incorrect','Stayed incorrect'],[(k.replace('_',' '),v['transitions'],v['improved'],v['worsened'],v['unchanged_incorrect']) for k,v in d['deli'].items()])
ct=table(['Early feature','Removed','Control','Difference [95% interval], pp'],[(lab,d['cga'][k]['removed_feature'],d['cga'][k]['control_feature'],f"{100*d['cga'][k]['paired_difference']:.2f} [{100*d['cga'][k]['cluster_bootstrap_interval'][0]:.2f}, {100*d['cga'][k]['cluster_bootstrap_interval'][1]:.2f}]") for k,lab in zip(keys,labs)])
da=table(['Case hash','Interpretation','Correctness change','Review reason'],[(x['event_hash'][:12],x['category'],x['delta'],x['reason']) for x in audit['deli']])
ca=table(['Case hash','Interpretation','Later removal','Review reason'],[(x['conversation_hash'][:12],x['category'],x['removed'],x['reason']) for x in audit['cga']])
body='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Corpus equations and real uptake records</title><style>body{font:17px/1.6 system-ui,sans-serif;color:#20343d;background:#fff;max-width:1120px;margin:auto;padding:40px 24px}h1{font-size:2.2rem;line-height:1.2}h2{margin-top:2.4rem}a{color:#096b89}img{width:100%;height:auto}.table{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px;margin:24px 0}th,td{border-bottom:1px solid #ccd5d9;padding:10px;text-align:left;vertical-align:top}th{background:#edf3f5}code{font-size:.92em}details{margin:20px 0}summary{cursor:pointer;font-weight:bold}.meta{color:#52656d}</style><main>
<p class="meta">Streams and Rocks · completed 22 October 2026</p>
<h1>Your corpus equations and real records of uptake and conflict</h1>
<p><strong>Earlier community simulations included added equations. This extension makes that distinction explicit and implements the supplied corrected corpus.</strong> The empirical analyses below examine actual records; they do not identify a phrase match with Sens or fit your field equations to invented social coordinates.</p>
<p><a href="CORPUS_AUDIT.md">Equation-by-equation audit</a> · <a href="README.md">Full findings and limitations</a> · <a href="corpus_extract.json">Exact source paragraphs</a> · <a href="PROTOCOL.md">Frozen protocol</a></p>
<h2>What is now using your exact equations</h2>
<p>The checked implementation preserves coordinate alignment, reciprocal scaling, binary consistency, the exact-edge constraint, accumulated input A and source J=κA, all three threshold laws, both gradient regularizations, fixed-direction force, symmetric stress and the normalized momentum balance. The scalar transport equation was run on a stated periodic test domain. No fully coupled social Navier–Stokes solution is claimed.</p>
<p>The signed tanh law gives <strong>−0.119202922 at q=−ε with ε=1</strong>; both exact-off laws give zero. With unit constant excess input, the accumulated-source law gives A(1)=1 and total field increase 0.5. Source-integral error stays below 3×10<sup>−15</sup>. Grid refinement reduces transport error about fourfold per doubling. These verify the implementation, not a law of human behavior.</p>
<p>The earlier logistic wording score and decaying penalty memory remain documented alternatives. They are not your accumulated-source law. Your corrected corpus supplies a field memory equation; a mapping from real penalties to its utility input and later decisions remains unspecified.</p>
<img src="figures/findings.png" alt="Three threshold responses, transport convergence, observed answer changes, and paired phrase-reuse differences">
<h2>Taking up an answer can help or spread a mistake</h2>
<p>In 500 DeliData group discussions, the conversion retains 538 changed submissions with an observed earlier submission. Of these, 162 in 122 groups match a partner's intervening proposed answer: <strong>62 become correct, 8 become incorrect, and 92 remain incorrect.</strong> Mean correctness change is +33.3 percentage points, group-bootstrap interval +23.8 to +43.0. This selected before/after change is not a causal estimate of copying.</p>
'''+dt+'''
<p>Sixteen reviewed candidates include seven explicit acceptances, two jointly constructed answers, four sequence-only cases, one return to an earlier idea, one instance of deference and one response to a request for an answer. A participant can contribute the decisive reasoning before adopting a partner's final wording; calling that simple copying would erase their contribution.</p>
<p>Only one INITIAL event survives in this conversion. Missing starting states were not reconstructed. Submitted-card vocabularies can be incomplete; the strict complete-vocabulary subset gives fewer improvements. Review was by one assistant, not independent human validation. Answer text itself can reveal correctness.</p>
<h2>Repeated wording is often a rebuttal</h2>
<p>The forum test uses the first three comments in each of 2,259 matched conversation pairs, before the final labelled comment. The primary reuse difference is <strong>+2.30 percentage points [−0.49, +5.16]</strong>. Reciprocal reuse gives <strong>−1.02 [−2.23, +0.18]</strong>. Neither gives clear evidence of a difference in these records. Including quoted text changes the finding.</p>
'''+ct+'''
<p>The twelve reviewed matches include rebuttals, common phrases, partial agreement and a quote-filter failure. One conversation contains mirrored personal challenges. These observations distinguish what the words do; they do not establish shared desire, causal imitation or Girard's rival-double mechanism. A later attack removal is a recorded institutional action, not a diagnosis of a participant.</p>
<p>Shared-topic controls retain overlap. Source balancing prevents population prevalence estimates. Missing post identifiers limit clustering; edited source texts may include later edits. A Markdown quotation continuation survived the simple filter. All these limitations remain in the full report.</p>
<h2>Sens, Sin, context, treatment and memory</h2>
<p><strong>Preserves Sens while adjusting Sin</strong> remains your distinction. A phrase match is only a retrieval clue. Adoption, rejection, quotation, joint construction and deference are reviewed separately. No measured social metric, utility, pressure field or penalty-to-field coupling has been silently added. The corpus's binary consistency rule requires the same action in the same declared context; these different arguments do not satisfy that test.</p>
<p>Water, Fog, Smoke or Clay remain situational descriptions. Helpful uptake and mirrored conflict describe encounters, not permanent kinds of people. Strong language about refusal, force, exclusion and resistance stays connected to the observed action or attributed account.</p>
<details><summary>All sixteen answer-uptake reviews and joined outcomes</summary>'''+da+'''</details>
<details><summary>All twelve phrase-reuse reviews and joined outcomes</summary>'''+ca+'''</details>
<h2>Inspect and reproduce</h2>
<p><strong>37 unit tests and 87 saved-result checks passed.</strong> See <a href="results/checks.json">check receipt</a>, <a href="results/observed_results.json">quantitative results</a>, <a href="results/equation_results.json">equation checks</a>, <a href="results/functional_audit.json">frozen review</a> and <a href="SOURCES.md">data provenance</a>. The full README gives reproduction commands. Raw texts and identities remain local.</p>
<p>Sources: <a href="https://convokit.cornell.edu/documentation/deli.html">DeliData</a>, <a href="https://doi.org/10.1145/3610056">Karadzhov et al.</a>, <a href="https://convokit.cornell.edu/documentation/awry_cmv.html">CGA-CMV</a>, <a href="https://aclanthology.org/D19-1481/">Chang and Danescu-Niculescu-Mizil</a>, and the pinned user-supplied corrected corpus.</p>
</main></html>'''
(p/'report.html').write_text(body,encoding='utf-8')
print('Wrote report.html and figures/findings.png')
