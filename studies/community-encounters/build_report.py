from pathlib import Path
import csv,html,json,re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parent
D=ROOT/'data';A=ROOT/'analysis';A.mkdir(exist_ok=True)
R=json.loads((D/'results.json').read_text())
def csvread(n):return list(csv.DictReader((D/n).open(encoding='utf-8')))
timeline=csvread('memory_timeline.csv');joint=csvread('joint_wording_history.csv');sens=csvread('sensitivity.csv')
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(2,2,figsize=(12,9),layout='constrained')
ax[0,0].bar(['Wording blind','Chosen penalty','Reversed penalty'],[100*R['wording'][k]['mean'] for k in ('0','0.8','-0.8')],color=['#697c83','#c76335','#20758a'])
ax[0,0].axhline(0,color='#555',lw=.8);ax[0,0].set(ylabel='Restriction probability difference (pp)',title='Same authored offer: direct minus courteous')
colors={'history_blind':'#68787d','record_only_decay':'#cf9d30','reinforcing_feedback':'#c76335','corrective_feedback':'#20758a','reset_before_round_6':'#6e51a4'}
for name,col in colors.items():
    rows=[x for x in timeline if x['policy']==name];t=[int(x['round']) for x in rows]
    ax[0,1].plot(t,[100*float(x['mean']) for x in rows],label=name.replace('_',' '),color=col)
    ax[0,1].fill_between(t,[100*float(x['lower']) for x in rows],[100*float(x['upper']) for x in rows],color=col,alpha=.12)
ax[0,1].axhline(0,color='#555',lw=.8);ax[0,1].legend(fontsize=8);ax[0,1].set(xlabel='Later encounter',ylabel='Paired probability difference (pp)',title='Prior restriction minus prior permission')
forms=['courteous','formal','direct','forceful']
for key,label,shift,col in [('p_after_permission','Previously permitted',-.18,'#20758a'),('p_after_restriction','Previously restricted',.18,'#c76335')]:
    ax[1,0].bar(np.arange(4)+shift,[100*float(next(x[key] for x in joint if x['meaning_id']=='0' and x['variant']==f and float(x['context_offset'])==0)) for f in forms],width=.36,label=label,color=col)
ax[1,0].set_xticks(range(4),forms);ax[1,0].set(ylabel='Restriction probability (%)',title='Combined wording and record: chosen rule');ax[1,0].legend(fontsize=8)
for rho,col in [(0.5,'#20758a'),(.8,'#c76335'),(.95,'#6e51a4')]:
    rows=[x for x in sens if float(x['retention'])==rho]
    ax[1,1].plot([float(x['history_coefficient']) for x in rows],[100*float(x['mean']) for x in rows],'o-',label=f'retention {rho}',color=col)
ax[1,1].axhline(0,color='#555',lw=.8);ax[1,1].legend(fontsize=8);ax[1,1].set(xlabel='Chosen sensitivity to history',ylabel='Later restriction difference (pp)',title='Sensitivity over 30 later encounters')
fig.suptitle('Synthetic procedure audit — chosen rules, not measured human effects',fontsize=14)
for ext in ('png','svg'):fig.savefig(A/f'synthetic_checks.{ext}',dpi=150)
plt.close(fig)
audit=csvread('published_wording_audit.csv');keep=[x for x in audit if x['table_consistent']=='True']
fig,ax=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
for i,x in enumerate(keep):
    v=float(x['odds_ratio']);lo=float(x['lower']);hi=float(x['upper'])
    ax[0].errorbar(v,i,xerr=[[v-lo],[hi-v]],fmt='o',color='#20758a',capsize=4)
ax[0].set_yticks(range(len(keep)),['Exp '+x['experiment']+' '+x['contrast'].split(' versus')[0] for x in keep]);ax[0].invert_yaxis()
ax[0].set_xscale('log');ax[0].axvline(1,color='#777',ls='--');ax[0].set(xlabel='Donation odds ratio (approximate 95% interval)',title='Four internally consistent published contrasts')
history=csvread('published_history_arithmetic.csv');x=np.arange(2)
ax[1].bar(x-.18,[100*float(r['control']) for r in history],.36,label='No imposed prior vote',color='#20758a')
ax[1].bar(x+.18,[100*float(r['treated']) for r in history],.36,label='Imposed prior downvote',color='#c76335')
ax[1].set_xticks(x,['Next viewer upvotes','Next viewer downvotes']);ax[1].set(ylabel='Published probability (%)',title='Prior ratings altered later ratings');ax[1].legend(fontsize=8)
fig.suptitle('Published summary checks — no raw-data refit',fontsize=14)
for ext in ('png','svg'):fig.savefig(A/f'published_checks.{ext}',dpi=150)
plt.close(fig)

md=[];ht=[]
def inline(t):
    t=html.escape(str(t));t=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',t)
    return re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',t)
def heading(t,n=2):md.append('#'*n+' '+t);ht.append(f'<h{n}>{inline(t)}</h{n}>')
def para(t):md.append(t);ht.append('<p>'+inline(t)+'</p>')
def table(headers,rows):
    md.append('\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(r)+' |' for r in rows]))
    ht.append('<div class="scroll"><table><tr>'+''.join('<th>'+inline(h)+'</th>' for h in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+inline(c)+'</td>' for c in r)+'</tr>' for r in rows)+'</table></div>')
def figure(n,t):md.append(f'![{t}](analysis/{n}.png)');ht.append(f'<figure><img src="analysis/{n}.png" alt="{html.escape(t)}"><figcaption>{inline(t)}</figcaption></figure>')
heading('Wording and prior treatment in community encounters',1)
para('Streams and Rocks • completed computational tests and published evidence checks • 21 October 2026')
para('**The decision rule matters.** The new tests find identical treatment when wording is ignored, different treatment when a chosen wording penalty is active, and lingering effects when earlier restrictions enter later decisions. Reversing the rules reverses the effects. These are results for an explicit synthetic procedure; they do not establish how a family or platform treats people.')
para('The study ran 432 wording cases, 144 joint wording/history probability pairs, 6,000 paired history paths and 2,400 sensitivity pairs. Each history pair has 30 later encounters. Nineteen unit tests passed. Published numerical checks are reported separately below. [Methods](METHODS.md) · [Frozen protocol](data/protocol.json) · [Saved-result verification](verification.json).')
para('**Real-data follow-up now completed:** [content, judgment and later recognition](https://github.com/NousVolition/Nous-Volition/blob/main/studies/community-real-data/README.md) analyses human annotation records and exact randomized-study counts. It finds semantic failures, differing judgments among selected labeled matches, and a recognition effect in one Wikipedia experiment. These observations do not fit or validate the synthetic parameters below.')
heading('The same offer expressed four ways')
para('Each expression keeps the same authored task, offered duration and maximum duration. For example, one person offers twenty minutes and declines any larger commitment. Direct, courteous, formal and forceful versions retain that content. **Complete meaning is not proven identical:** wording can also communicate different relationship signals, urgency or tone. Independent speaker and recipient checks remain necessary.')
table(['Procedure','Direct minus courteous restriction probability','What the comparison establishes'],[
 ['Wording blind','0.0 percentage points','The same structured offer receives the same probability'],
 ['Chosen literal-marker penalty',f'+{100*R["wording"]["0.8"]["mean"]:.1f} points on average','Consequence of the specified wording rule'],
 ['Reversed marker penalty',f'{100*R["wording"]["-0.8"]["mean"]:.1f} points on average','The direction is supplied by the rule, not discovered in human data']])
para('The marker counts “will not” and “refuse” positively and “please” negatively. It is an intentionally limited stress test, not a politeness or harm detector. Direct and forceful versions receive identical probabilities because their marker values match. The positive-rule difference ranges from 15.2 to 35.3 points across the three chosen contexts. No interval is assigned to repeated templates as if they were independent observations. [Exact wording and probabilities](data/wording_cases.csv).')
heading('What one prior restriction changes')
para('Two copies begin with identical content and circumstances, but one receives permission and the other restriction at encounter zero. Thereafter their wording, context sequence and random numbers match. The table excludes that imposed first decision and measures only the next 30 encounters. Memory here is a stored decision record; this module contains no skill learning or measured emotion.')
rows=[]
for name,label in [('history_blind','History blind'),('record_only_decay','Initial record fades'),('reinforcing_feedback','Later restrictions reinforce the record'),('corrective_feedback','Prior restriction prompts correction'),('reset_before_round_6','Reset both records before encounter 6'),('zero_input','No decisions stored')]:
    q=R['memory'][name]['future_restriction_difference'];rows.append([label,f'{100*q["mean"]:+.3f} pp',f'[{100*q["lower"]:+.3f}, {100*q["upper"]:+.3f}]'])
table(['Procedure','Difference in later restriction rate','95% Monte Carlo interval'],rows)
para('Under reinforcing feedback, the first later restriction probability increases by 5.08 points on average. Across all 30 later encounters, the realized rate difference is 1.28 points. A corrective rule produces a −0.62-point rate difference. With no history effect or no stored input, paired outcomes are exactly identical. Clearing both records before encounter 6 makes every subsequent paired outcome identical; the table retains differences from encounters 1–5. The intervals quantify simulation variability under chosen rules, not uncertainty about people.')
figure('synthetic_checks','Synthetic contrasts, joint wording/history probabilities, decay, reset and parameter sensitivity. Bands show Monte Carlo intervals across seeds.')
heading('What the published evidence checks show')
para('[Juanchich, Sirota and Bonnefon](https://jfbonnefon.github.io/publication/jbdm19/jbdm19.pdf) varied donation-request wording while retaining the requested donation. We checked all six main-experiment contrasts against the paper’s appendix. Four pass the coefficient-to-odds-ratio rounding check; all four reconstructed 95% intervals include 1. Two Experiment 2 entries disagree: 0.67 versus 0.45, and 0.87 versus 0.44. Those estimates are excluded from the retained plot. Experiment 3 contrasts apply to donation-first order. The raw-data link returned 404. This check does not establish equivalence or refit participant data.')
para('[Muchnik, Aral and Taylor](https://snap.stanford.edu/class/cs224w-readings/muchnik13bias.pdf) randomly altered prior comment ratings. Their reported later upvote probabilities after an imposed downvote were 9.9% versus 5.4% in the control; our arithmetic gives +4.5 percentage points. Later downvotes were 1.4% versus 0.7%, a +0.7-point difference. This includes correction as well as reinforcement. These are rounded published outcomes for later viewers of the same comment, not a new test of someone’s future treatment across different encounters. No counts or confidence intervals are reconstructed from the percentages.')
figure('published_checks','Published aggregate estimates checked separately from synthetic results. No new participant observations and no pooled effect estimate.')
para('These sources were read during design and are not untouched holdouts. They do not calibrate the synthetic rule. [Transcribed sources and scope](source_estimates.json) · [Wording consistency audit](data/published_wording_audit.csv) · [History arithmetic](data/published_history_arithmetic.csv).')
heading('What this adds to the community model')
para('Meaning, expression, context, treatment and memory now have an executable comparison in addition to the conceptual guide. A person can adapt an expression as Water, be partly understood as Fog, carry an earlier account as Smoke, or retain an impression as Clay. These descriptions can overlap or be rejected; they do not enter the decision score. Strong language remains attributable to its speaker, and a refusal is not automatically coded as wrongdoing.')
para('The missing social test is a comparison of actual treatment after independently checked equivalent expressions, followed by new time-ordered encounters with relevant context recorded. That requires observations and a causal design, not another large batch of fictional seeds. [Connections and evidence guide](https://github.com/NousVolition/Nous-Volition/blob/main/studies/community-power/CONNECTIONS.md).')
heading('Reproduce and inspect')
commands='python -m pip install -r requirements.txt\npython test_model.py\npython verify.py\npython run_study.py --out reproduced\n# Rebuild this report from delivered data:\npython build_report.py'
md.append('```sh\n'+commands+'\n```');ht.append('<pre>'+html.escape(commands)+'</pre>')
para('The runner refuses to overwrite an output directory. [Seed summaries](data/memory_seed_results.csv), [example encounters](data/example_encounters.csv), [joint comparisons](data/joint_wording_history.csv), [sensitivity results](data/sensitivity.csv) and [model](model.py) are included. Parameters are assumptions, recorded before execution; this local freeze is not public preregistration. The previous community and physical studies remain unchanged.')
(ROOT/'README.md').write_text('\n\n'.join(md)+'\n',encoding='utf-8')
css='body{font:17px/1.65 system-ui;color:#213544;background:#f1f5f5;margin:0}main{max-width:1160px;background:white;margin:24px auto;padding:36px}h1{line-height:1.2}h2{color:#17667b;margin-top:2em}a{color:#086e87}table{width:100%;border-collapse:collapse;font-size:.9em}td,th{padding:12px;text-align:left;border-bottom:1px solid #d7e1e1}.scroll{overflow:auto}img{width:100%;height:auto}figure{margin:28px 0}figcaption{font-size:.87em}pre{padding:20px;background:#eef4f5;overflow:auto}@media(max-width:700px){main{margin:0;padding:18px}}'
(ROOT/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wording and prior treatment</title><style>'+css+'</style><main>'+''.join(ht)+'</main></html>',encoding='utf-8')
print('Built report, README and figures')


# Preserve the source-chain audit when this historical report is rebuilt.
from audit_note import apply_notice
apply_notice(Path(__file__).resolve().parent)
