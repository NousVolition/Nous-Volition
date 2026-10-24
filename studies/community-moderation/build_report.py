from pathlib import Path
import json,html,re,csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parent
b=json.loads((ROOT/'data/block_results.json').read_text());w=json.loads((ROOT/'data/wording_results.json').read_text());c=json.loads((ROOT/'data/cmv_history_coverage.json').read_text())
s=b['windows']['180'];f=s['finite_pairs'];a=ROOT/'analysis';a.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'community-moderation-20261021'})
fig,ax=plt.subplots(1,2,figsize=(11.8,4.5),layout='constrained')
values=[f['longer'],f['equal'],f['shorter']];labels=['Longer second block','Same duration','Shorter second block']
ax[0].barh(labels,100*np.array(values)/f['n'],color=['#a54930','#8b9797','#267b83']);ax[0].invert_yaxis();ax[0].set_xlim(0,100);ax[0].set_xlabel('Share of accounts with two finite assignments (%)')
for i,n in enumerate(values):ax[0].text(100*n/f['n']+1,i,f'{n:,}',va='center')
ax[0].set_title(f'Actual assigned penalties: {f["n"]:,} accounts')
labs=['All finite pairs','Same moderator','Disruption-keyword subset'];ys=[]
for k in ('finite_pairs','same_moderator','disruption_subset'):
    r=s[k];ys.append(r['median_ratio']);ci=2**np.array(r['median_log2_ratio_ci95']);i=len(ys)-1
    ax[1].errorbar(r['median_ratio'],i,xerr=[[r['median_ratio']-ci[0]],[ci[1]-r['median_ratio']]],fmt='o',color='#267b83',capsize=5)
    ax[1].text(3.2,i,f'n = {r["n"]:,}',va='center',fontsize=10)
ax[1].set_yticks(range(3),labs);ax[1].invert_yaxis();ax[1].axvline(1,color='#777',linestyle=':');ax[1].set_xlim(.8,4.1);ax[1].set_xlabel('Median paired ratio: second / first duration');ax[1].set_title('Narrower subsets')
fig.suptitle('Observed escalation does not isolate the effect of remembered history',fontsize=14)
for ext in ('png','svg'):fig.savefig(a/f'penalty_comparison.{ext}',dpi=155,metadata={'Date':None} if ext=='svg' else {})
plt.close(fig)
fig,ax=plt.subplots(1,2,figsize=(11.8,4.3),layout='constrained')
ax[0].barh(['Audited closest wording pairs','Accepted as same meaning'],[12,0],color=['#267b83','#a54930']);ax[0].invert_yaxis();ax[0].set_xlim(0,14);ax[0].set_xticks([0,4,8,12]);ax[0].set_title('Meaning check: 12 closest topic pairs');ax[0].set_xlabel('Single-assistant screening decisions')
ax[0].text(.3,1,'0; all changed substantive content',va='center',fontsize=10)
designs=list(c['matched_designs'].values());known=[sum(x['0']+x['1'] for x in d['field_counts'])/(4*d['matched_pairs'])*100 for d in designs]
ax[1].barh(['Outside original discussion','Inside original discussion'],known,color='#267b83',label='Known outcomes');ax[1].barh(['Outside original discussion','Inside original discussion'],100-np.array(known),left=known,color='#d9dedc',label='Missing outcomes')
ax[1].invert_yaxis();ax[1].set_xlim(0,100);ax[1].set_xlabel('Outcome cells recovered from public releases (%)');ax[1].set_title('Most later outcomes are missing');ax[1].legend(loc='lower right',fontsize=9)
fig.suptitle('These checks prevent unsupported wording and history claims',fontsize=14)
for ext in ('png','svg'):fig.savefig(a/f'evidence_gaps.{ext}',dpi=155,metadata={'Date':None} if ext=='svg' else {})
plt.close(fig)

md=[];ht=[]
def inline(t):
    t=html.escape(str(t));t=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',t);t=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',t);return re.sub(r'`([^`]+)`',r'<code>\1</code>',t)
def h(t,n=2):md.append('#'*n+' '+t);ht.append(f'<h{n}>{inline(t)}</h{n}>')
def p(t):md.append(t);ht.append('<p>'+inline(t)+'</p>')
def table(head,rows):
    md.append('\n'.join(['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows]));ht.append('<div class="scroll"><table><tr>'+''.join('<th>'+inline(x)+'</th>' for x in head)+'</tr>'+''.join('<tr>'+''.join('<td>'+inline(x)+'</td>' for x in r)+'</tr>' for r in rows)+'</table></div>')
def image(name,caption):md.append(f'![{caption}](analysis/{name}.png)');p(caption);ht.append(f'<img src="analysis/{name}.png" alt="{html.escape(caption)}">')
def code(t):md.append('```sh\n'+t+'\n```');ht.append('<pre>'+html.escape(t)+'</pre>')
h('Actual moderation decisions and later penalties',1)
p('Streams and Rocks • completed public-data analyses • 21 October 2026')
p(f'**Second finite Wikipedia blocks were longer in {f["longer"]:,} of {f["n"]:,} paired accounts ({100*f["longer"]/f["n"]:.1f}%).** This documents escalating assigned penalties among accounts blocked again. The records do not establish that the earlier penalty caused harsher treatment for identical later conduct. The Reddit wording check found no acceptable same-meaning pair among the 12 closest topic pairs reviewed, so a wording effect remains unmeasured.')
table(['Question','Completed check','Conclusion'],[
 ['Same meaning, different wording, different moderation?',f'{w["text_available_pairs"]:,} topic pairs with both texts; the 12 closest were reviewed. All 12 changed substantive content.','Not established by this retrieval and audit; topic matches cannot stand in for paraphrases.'],
 ['Are later penalties different?',f'{f["longer"]:,} longer, {f["equal"]:,} equal, {f["shorter"]:,} shorter second finite assignments.','Observed escalation in this selected Wikipedia cohort.'],
 ['Does an earlier penalty itself change later treatment?','No controlled same-conduct history comparison. Reddit matching release has no complete four-outcome comparison after joins.','Causal memory effect remains open.']])
p('These are actual recorded Rule-2 removals and account blocks. The earlier [ParaDetox judgment study](../community-real-data/README.md) measured offensiveness labels, and the [synthetic encounter study](../community-encounters/README.md) used chosen decision rules. Their findings retain those narrower meanings.')
h('What changed in the second penalty')
p(f'The full log contains {b["log"]["counts"]["raw_events"]:,} actions. After reconstructing episodes and applying the declared criteria, {s["eligible"]:,} named accounts had a first observed finite block and 180 days of follow-up after that episode ended. {s["repeat"]:,} received another distinct block in that window. {s["infinite_second"]:,} second assignments were indefinite; {f["n"]:,} were finite and enter the paired duration comparison. The cohort is broader than established editors; it is not a replication of the published paper’s selected population.')
p(f'For the finite pairs, the median first assignment was {f["first_median_hours"]:g} hours and the median second was {f["second_median_hours"]:g} hours. The median account-level ratio was {f["median_ratio"]:.1f} times, with a paired bootstrap interval of {2**f["median_log2_ratio_ci95"][0]:.1f}–{2**f["median_log2_ratio_ci95"][1]:.1f} times. The sign test strongly favours more longer than shorter assignments (p < 0.001); this tests asymmetry, not a causal explanation.')
image('penalty_comparison','A block extension is counted within the existing episode, not as a new encounter. Durations describe initial assignments; early unblocking and later changes can alter time actually served. Right-hand intervals are 95% paired bootstrap intervals and can collapse at discrete standard durations. These are calculations from the public log, not findings copied from the source paper.')
table(['Follow-up','Eligible accounts','Another block','Finite pairs','Second finite assignment longer'],[[str(n)+' days',f'{d["eligible"]:,}',f'{d["repeat"]:,}',f'{d["finite_pairs"]["n"]:,}',f'{100*d["finite_pairs"]["longer"]/d["finite_pairs"]["n"]:.1f}%'] for n,d in b['windows'].items()])
p('The same-moderator and disruption-keyword checks also show escalation. Neither holds conduct severity, policy or exposure constant. The keyword subset is not a judgment that the two offences were equivalent. An account with no recorded second block may have stopped participating. Different window lengths also change which accounts have complete follow-up.')
h('Why the wording question is still open')
p(f'The [CGA-CMV dataset](https://convokit.cornell.edu/documentation/awry_cmv.html) provides {w["author_topic_pairs"]:,} pairs from the same original discussion topic. One endpoint is recorded as removed and one as a comparison by the dataset’s construction. Of these, {w["text_available_pairs"]:,} have available text on both sides; {w["unavailable_endpoint_texts"]} endpoints contain missing or replacement text. Treating the paired outcome difference as a wording effect would simply reproduce the sampling rule.')
p('The 12 closest pairs share words but change arguments, referents or interpersonal claims. One shares a paragraph about old video games while adding several new claims in its longer version. Another changes an argument about imperfect parenting into an accusation that the other person wants humanity to disappear. Neither is a controlled wording substitution. The review also rejects a deleted-message template as evidence about the original meaning.')
p('Across all available endpoints, there were no exact duplicate texts and no changed-text pairs meeting the declared high-overlap search threshold. That search can miss valid paraphrases. **The result is an unsuccessful search for a usable comparison, not proof that wording has no effect or that moderation is fair.** The [12 audit reasons](data/meaning_audit.json) are one assistant’s visible-outcome review, with a local text inspection tool for independent checking.')
h('What the Reddit penalty-history release can reproduce')
p('The authors’ [public matching records](https://github.com/BoulderDS/effect_of_comment_deletion_cmv_dataset) identify before/after comparisons for people whose comments were removed earlier versus later. The release does not include all subsequent removal outcomes. Joining it with the recorded endpoint labels and first/second removal lists recovers only a small fraction of the required outcome cells.')
table(['Matched setting','Comparisons','Known outcome cells','Complete four-outcome comparisons'],[[label,f'{d["matched_pairs"]:,}',f'{sum(z["0"]+z["1"] for z in d["field_counts"]):,} / {4*d["matched_pairs"]:,}',str(d['complete_outcome_quadruples'])] for label,d in zip(['Outside original discussion','Inside original discussion'],designs)])
p('Absence from a first/second removal list cannot mean “allowed”: a third removal is absent too. Leaving those cells unknown produces bounds spanning both positive and negative differences, so these joins cannot recover the direction of the effect. The published [delayed-feedback study](https://doi.org/10.1145/3359265) reports reduced immediate later removals under its design assumptions; this analysis has not independently replicated that estimate.')
image('evidence_gaps','Meaning was screened directly instead of assumed from shared vocabulary. Missing Reddit outcomes remain missing; they are not counted as favourable decisions.')
h('Connections to the community model')
table(['Connection','Status now','What would test the stronger claim'],[
 ['Meaning → expression','The audit detects substantive differences in candidate wording pairs.','Independent checks of proposition, referent, stance and force, plus the speaker’s account of intent where possible.'],
 ['Expression in context → treatment','Actual removals are recorded; a causal wording contrast is not identified.','Meaning-preserving variants under the same policy and conversational context, independently reviewed, with comparable moderator exposure.'],
 ['Past penalty → later assigned restriction','Observed escalation among repeated finite Wikipedia blocks.','Comparable current conduct with history visibility controlled or credibly varied.'],
 ['Treatment → memory → later encounter','No psychological or institutional memory mechanism isolated.','Record what prior history was visible to whom; distinguish changed behaviour, changed attention and changed decision rules.']])
p('**Keep strong language and test its treatment.** Refusal, accusation and resistance are not interchangeable with polite agreement. Removing an accusation to make a message sound calmer changes the test if that accusation is part of the meaning. A word count, a sanction or an algorithmic score does not settle whether a criticism is justified.')
p('Water can describe adaptation, fog an unclear boundary, smoke a trace of earlier treatment, and clay an impression that persists or changes. These remain situational descriptions chosen or contested by people. The new observations constrain claims about records and penalties; they do not turn those descriptions into fixed human types. Foucault’s questions about who records, classifies and applies sanctions guide the inquiry; this evidence does not validate the whole theory.')
h('Reproduce and inspect')
p('The [methods](METHODS.md), [source hashes](sources.json), [analysis plan](data/protocol.json), [amendments](data/protocol_amendments.json), [verification](verification.json) and aggregate tables accompany the results. No participant intervention or live moderation submission was performed. Raw messages and account identities are not republished.')
code('python -m pip install -r requirements.txt\npython -m unittest discover -p test_analysis.py -v\npython reproduce_aggregates.py\npython verify.py\n\n# Fetch and rerun the Reddit checks (~52 MB):\npython download_data.py --raw-dir raw\npython analyze_wording.py --raw-dir raw --out-dir reproduced\n\n# Full block reconstruction additionally downloads 1.67 GB:\npython download_data.py --raw-dir raw --include-blocks\npython prepare_blocks.py --raw-dir raw\npython analyze_blocks.py --raw-dir raw --out-dir reproduced\n\n# Rebuild the report from saved results:\npython build_report.py')
p('The full reconstruction needs additional space for its SQLite cache and refuses to replace an existing cache. Quick aggregate reproduction verifies all nine finite-duration summaries without that download. The supplied tests verify implementation and data accounting; they cannot supply missing meanings, behaviour measures or causal controls. This is exploratory reanalysis, not a fresh model-selection holdout.')
p('[Community connections](../community-power/CONNECTIONS.md) · [Earlier real-data results](../community-real-data/README.md) · [Cornell block-log catalog and study](https://convokit.cornell.edu/datasets.html) · [Associated block-trajectory paper](https://arxiv.org/abs/1902.08628)')
for old,new in [('../community-real-data/','https://github.com/NousVolition/Nous-Volition/blob/main/studies/community-real-data/'),('../community-encounters/','https://github.com/NousVolition/Nous-Volition/blob/main/studies/community-encounters/'),('../community-power/','https://github.com/NousVolition/Nous-Volition/blob/main/studies/community-power/')]:
    md=[x.replace(old,new) for x in md];ht=[x.replace(old,new) for x in ht]
(ROOT/'README.md').write_text('\n\n'.join(md)+'\n',encoding='utf-8')
css='body{margin:0;background:#edf2ef;color:#253830;font:17px/1.65 system-ui,sans-serif}main{max-width:1120px;margin:30px auto;padding:38px;background:white;border-radius:12px}h1{font-size:2.2rem;line-height:1.2}h2{color:#176c70;margin-top:2.2em}table{border-collapse:collapse;width:100%;font-size:.91rem}td,th{padding:12px;text-align:left;border-bottom:1px solid #d6e0dc;vertical-align:top}th{background:#edf4f0}a{color:#126e86}.scroll{overflow:auto}img{max-width:100%;height:auto}pre{background:#eef3f0;overflow:auto;padding:20px;font-size:.85em}@media(max-width:700px){main{margin:0;padding:18px}body{font-size:16px}}'
(ROOT/'report.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Actual moderation decisions and later penalties</title><style>'+css+'</style></head><body><main>'+''.join(ht)+'</main></body></html>',encoding='utf-8')
print('Built report and two figures.')


# Preserve the source-chain audit when this historical report is rebuilt.
from audit_note import apply_notice
apply_notice(Path(__file__).resolve().parent)
