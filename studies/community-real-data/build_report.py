from pathlib import Path
import csv,html,json,re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parent
A=ROOT/'analysis';A.mkdir(exist_ok=True)
R=json.loads((ROOT/'data/results.json').read_text());F=R['flow'];P=R['paired_labels'];H=R['history']
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'community-real-data-v1'})
def save(fig,name):
    fig.savefig(A/f'{name}.png',dpi=160)
    fig.savefig(A/f'{name}.svg',metadata={'Date':None})
    plt.close(fig)
fig,ax=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
nums=[F['changed_match'],F['changed_mismatch']]
bars=ax[0].bar(['Close content\n(source label)','Content mismatch\n(source label)'],nums,color=['#267c84','#b75b35'])
for b,n in zip(bars,nums):ax[0].text(b.get_x()+b.get_width()/2,n+600,f'{n:,}\n{n/F["changed_pairs"]:.1%}',ha='center')
ax[0].set(ylim=(0,32000),ylabel='Unique changed pairs',title='Meaning was checked, not guaranteed')
values=[100*P['original_offensive_rate'],100*P['rewrite_offensive_rate']]
bars=ax[1].bar(['Original','Rewrite'],values,color=['#b75b35','#267c84'])
for b,v in zip(bars,values):ax[1].text(b.get_x()+b.get_width()/2,v+2,f'{v:.1f}%',ha='center')
ax[1].set(ylim=(0,108),ylabel='Marked offensive (%)',title='941 source-matched pairs with both labels')
fig.suptitle('Human annotation records • selected research rewrites, not moderation actions',fontsize=13)
save(fig,'wording_evidence')

fig,ax=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
for i,(label,key,col,k) in enumerate([('Initial award','treatment','#267c84',12),('No initial award','control','#b75b35',2)]):
    val=100*H[key+'_rate'];lo,hi=[100*x for x in H[key+'_wilson']]
    ax[0].bar(i,val,color=col,width=.55)
    ax[0].errorbar(i,val,yerr=[[val-lo],[hi-val]],fmt='none',color='#213544',capsize=5)
    ax[0].text(i,hi+1,f'{k}/100',ha='center')
ax[0].set_xticks([0,1],['Initial award','No initial award'])
ax[0].set(ylim=(0,24),ylabel='People receiving another award (%)',title='90-day randomized endpoint')
rows=list(csv.DictReader((ROOT/'data/award_chronology.csv').open()))
for group,label,col in [('1','Initial award','#267c84'),('0','Control','#b75b35')]:
    subset=[x for x in rows if x['group']==group]
    ax[1].step([0]+[int(x['day']) for x in subset],[0]+[int(x['cumulative_award_events']) for x in subset],where='post',label=label,color=col,lw=2)
ax[1].set(xlabel='Day after assignment',ylabel='Additional award events (not people)',title='Released group chronology • descriptive')
ax[1].legend();ax[1].set_ylim(0,16)
fig.suptitle('Prior recognition changed later recognition in this experiment',fontsize=14)
save(fig,'history_evidence')

md=[];ht=[]
def inline(t):
    t=html.escape(str(t));t=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',t)
    return re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',t)
def heading(t,n=2):md.append('#'*n+' '+t);ht.append(f'<h{n}>{inline(t)}</h{n}>')
def para(t):md.append(t);ht.append('<p>'+inline(t)+'</p>')
def table(headers,rows):
    md.append('\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(r)+' |' for r in rows]))
    ht.append('<div class="scroll"><table><tr>'+''.join('<th>'+inline(h)+'</th>' for h in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+inline(c)+'</td>' for c in r)+'</tr>' for r in rows)+'</table></div>')
def figure(name,caption):
    md.append(f'![{caption}](analysis/{name}.png)');ht.append(f'<figure><img src="analysis/{name}.png" alt="{html.escape(caption)}"><figcaption>{inline(caption)}</figcaption></figure>')
heading('Real data: wording, meaning and later encounters',1)
para('Streams and Rocks • completed reanalysis • 21 October 2026')
para('**Wording can change how a statement is judged, but preserving its meaning is a separate test. Prior recognition can also change later recognition.** These findings come from human annotation records and a randomized Wikipedia experiment. They do not establish the complete community model or a universal rule for how people remember treatment.')
table(['Question','Completed finding','Evidence boundary'],[
 ['Does changed wording preserve content?',f'{F["changed_match"]:,} of {F["changed_pairs"]:,} changed pairs were labeled close in content; {F["changed_mismatch"]:,} ({F["changed_mismatch"]/F["changed_pairs"]:.1%}) were not.','Publisher labels are fallible; close content is narrower than identical meaning or force.'],
 ['Do judgments change within labeled matches?',f'Among {P["n"]} pairs with both labels, {P["offensive_to_nonoffensive"]} changed from offensive to nonoffensive and {P["nonoffensive_to_offensive"]} changed in the opposite direction.','A selected annotation contrast, not observed punishment or exclusion.'],
 ['Does earlier treatment affect later recognition?',f'12/100 initially awarded contributors received a further award, versus 2/100 controls: +10.0 percentage points.','Randomized evidence in one selected Wikipedia population; mechanism and negative treatment remain open.']])
para('[Methods and limits](METHODS.md) · [Exact results](data/results.json) · [Data provenance](sources.json) · [Verification](verification.json) · [Community connections](../community-power/CONNECTIONS.md)')
heading('Check the meaning before interpreting a wording effect')
para('The [ParaDetox project](https://github.com/s-nlp/paradetox) releases human-written alternatives and separate content/offensiveness judgments. We read 32,317 content rows and 26,507 toxicity rows, removed duplicate records, and excluded 8 pair keys and 41 text keys with conflicting labels. These counts are records and texts, not numbers of independent raters.')
para('There are 30,072 unique changed pairs with an unambiguous content label. The 4,544 rejected matches remain visible. Another 1,556 pairs have identical strings; eight of those nevertheless carry a mismatch label. That discrepancy is recorded as a label-quality concern, not silently repaired.')
para('**A closer review found substantive changes even among accepted matches.** In a predetermined 24-pair sample, my single-assistant audit found 9 content changes, 3 uncertain cases and 12 with no clear core-content loss. For example, one rewrite drops an accusation that a number was fabricated; another changes criticism of a person into criticism of an action. These are reasons for independent human review, not a validated error rate for the whole dataset. The sample comes from the broader matched pool, not only the fully joined subset.')
para('[All 24 audit decisions and reasons](data/meaning_audit.csv) are traceable to the pinned text files using pair hashes. The review preserves disagreements with the original labels. No new human raters were recruited.')
figure('wording_evidence','Left: released content judgments for changed pairs. Right: only the selected 941 pairs with labels for both versions. The figures measure annotation outcomes, not real moderation actions.')
heading('What the paired judgment comparison shows')
table(['Original label','Rewrite label','Pairs'],[['Nonoffensive','Nonoffensive',str(P['both_nonoffensive'])],['Nonoffensive','Offensive',str(P['nonoffensive_to_offensive'])],['Offensive','Nonoffensive',str(P['offensive_to_nonoffensive'])],['Offensive','Offensive',str(P['both_offensive'])]])
ci=P['rewrite_minus_original'];eq=P['equal_weight_originals']
para(f'The fraction marked offensive falls from {P["original_offensive_rate"]:.1%} to {P["rewrite_offensive_rate"]:.1%}: a {abs(ci["estimate"])*100:.1f}-percentage-point reduction. Resampling the {P["originals"]} original-text clusters gives a conditional 95% interval of {abs(ci["high"])*100:.1f}–{abs(ci["low"])*100:.1f} points. Giving each original equal weight yields {abs(eq["estimate"])*100:.1f} points. These intervals describe this selected corpus and fixed labels; they do not correct semantic errors or selection bias.')
para('**Coverage is only 3.69% of accepted changed pairs.** We did not assume an original was offensive because its column was named “toxic.” Both labels had to exist in the released pool and agree across duplicate keys. Selection for the detoxification task also makes this an unsuitable estimate of ordinary language reception. The evidence supports different judgments under the dataset’s content criterion; it cannot establish a wording-only causal effect with complete meaning held constant.')
para('**Preserve semantic force.** Criticism, anger, refusal and accusations need not be softened automatically. An offensiveness label does not establish that a claim is false, unwarranted or deserving of punishment. A rewrite that removes the point should be recorded as a changed statement, even if readers prefer it.')
heading('Earlier recognition and later encounters')
para('The [original randomized study](https://doi.org/10.1371/journal.pone.0034358) compared 100 Wikipedia contributors given an initial award with 100 controls over 90 days. It selected highly productive contributors who had not previously received such an award. The endpoint here is receiving any further award from other community members.')
para(f'**The later-award rate was 12% versus 2%.** The difference is +10.0 percentage points, with a Newcombe–Wilson 95% interval of +{H["risk_difference_ci"][0]*100:.1f} to +{H["risk_difference_ci"][1]*100:.1f} points. Our two-sided Fisher exact test gives p = {H["fisher_two_sided_p"]:.4f}. The risk ratio is 6.0, with a wide approximate interval of {H["risk_ratio_log_ci"][0]:.2f}–{H["risk_ratio_log_ci"][1]:.2f}. Small endpoint counts make the magnitude uncertain.')
figure('history_evidence','Left: person-level endpoint counts from the paper, with Wilson intervals. Right: aggregate award events from the author-attributed daily file. Multiple awards can go to one person; event totals are not participant counts.')
para('This is evidence that initial recognition affected later recognition in that experiment. It does not distinguish public reputation, motivation, changed contribution or remembered experience. It does not establish that prior punishment has the same effect, or that every subsequent encounter changed.')
para('**The data levels are explicit.** The statistical test uses the exact published 2×2 table, not newly recovered individual trajectories. The downloadable researcher-attributed file contains 242 group-day summaries. Its 14 versus 3 additional award events match the paper, while the endpoint concerns 12 versus 2 people. Its first control award is dated day 7 and its first treated award day 8. The article’s day-8 discussion concerns experimental recipients; these dates can coexist. Individual event-time trajectories remain unavailable. [Provenance of the aggregate file](https://learningds.org/data_sources.html).')
heading('How this changes the community model')
table(['Connection','Support now','Still needs testing'],[
 ['Meaning → expression','Real content labels and a transparent audit show both preserved content and substantive alterations.','Independent speakers and reviewers must assess intended meaning, target, commitment and pragmatic force.'],
 ['Expression → judgment','Selected content-matched pairs receive different offensiveness labels.','Actual comparable institutional or interpersonal treatment; context, policy and semantic equivalence.'],
 ['Past treatment → later encounter','Randomized recognition increased the chance of later recognition in the Wikipedia study.','Negative treatment, other populations, mediation and complete longitudinal encounters.'],
 ['Memory → decision','A plausible interpretation, still separated from the observed endpoint.','Whose memory or record changed; causal mechanism, retention and reset effects.'],
 ['Water, fog, smoke, clay','Situational metaphors for adapting expression, partial understanding, circulating accounts and lasting impressions.','No dataset here measures these as fixed human types or validates material names as predictors.']])
para('The same person can occupy several of these situations and can reject the description. The two datasets support parts of the argument separately; they do not connect all five parts in one observed chain. The [earlier synthetic encounter model](../community-encounters/README.md) remains a demonstration of chosen rules. Its wording penalty and memory parameters have not been fitted or validated by these results.')
heading('Reproduce and inspect')
para('All 13 unit tests passed. Saved-data checks verify joins, counts, source hashes, audit selection and the exact history test. No downloaded raw comments or participant identities are republished. The report includes the source downloader, analysis, audit reasons, derived counts and figures. The audit can be expanded locally for independent review.')
commands='python -m pip install -r requirements.txt\npython download_data.py\npython -m unittest discover -p test_analysis.py -v\npython run_analysis.py\npython verify.py\npython build_report.py\npython inspect_audit.py'
md.append('```text\n'+commands+'\n```');ht.append('<pre>'+html.escape(commands)+'</pre>')
para('The protocol was recorded before these full-data summaries, after source findings and previews had been read. This is an exploratory reanalysis of existing evidence, not an untouched holdout or a newly conducted human experiment. [Analysis plan](data/protocol.json) · [Documented changes](data/protocol_amendments.json).')
(ROOT/'README.md').write_text('\n\n'.join(md)+'\n',encoding='utf8')
css='body{font:17px/1.65 system-ui;color:#213544;background:#eef4f3;margin:0}main{max-width:1100px;background:white;margin:24px auto;padding:38px}h1{font-size:2.2rem;line-height:1.2}h2{color:#176b74;margin-top:2em}a{color:#126a83}table{width:100%;border-collapse:collapse;font-size:.9em}th,td{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #d2dddd}th{background:#eaf4f2}.scroll{overflow:auto}img{width:100%;height:auto}figure{margin:28px 0}figcaption{font-size:.86em;color:#4a626d}pre{overflow:auto;background:#edf3f5;padding:20px}@media(max-width:700px){main{padding:18px;margin:0}h1{font-size:1.8rem}}'
(ROOT/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Real encounters — Streams and Rocks</title><style>'+css+'</style><main>'+''.join(ht)+'</main></html>',encoding='utf8')
print('Built real-data report and two figures')


# Preserve the source-chain audit when this historical report is rebuilt.
from audit_note import apply_notice
apply_notice(Path(__file__).resolve().parent)
