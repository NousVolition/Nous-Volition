"""Build the editable protocol and readable HTML from one content specification."""
from pathlib import Path
import json, html
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

R=Path(__file__).resolve().parent
s=json.loads((R/'results/summary.json').read_text());inner=s['inner'];mem=s['memory']
fig=R/'figures';fig.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
f,ax=plt.subplots(figsize=(7,2.5)); ax.set(xlim=(0,10),ylim=(0,4));ax.axis('off')
ax.add_patch(FancyBboxPatch((.1,.2),9.8,3.6,boxstyle='round,pad=0.03',edgecolor='#666666',facecolor='#f7f7f7'))
ax.text(5,3.45,'ONE PERSON · THEIR OWN HISTORY',ha='center',weight='bold',color='#222222')
for x,label,colour in [(1.6,'SMOKE\nInward speaking','#e2e8ed'),(5,'MOVING IDEA\nReceived and\nreformulated','#e9efe4'),(8.4,'CLAY\nInward listening','#f0e8df')]:
    ax.add_patch(FancyBboxPatch((x-1.3,1.3),2.6,1.1,boxstyle='round,pad=0.08',edgecolor='#999999',facecolor=colour))
    ax.text(x,1.85,label,ha='center',va='center',fontsize=10)
for a,b in [(2.98,3.62),(6.38,7.02)]: ax.annotate('',xy=(b,1.85),xytext=(a,1.85),arrowprops={'arrowstyle':'<->','color':'#333333'})
ax.text(5,.65,'Proposed conceptual links · not measured material forces',ha='center',fontsize=10)
f.savefig(fig/'within_person.png',dpi=180,bbox_inches='tight');plt.close(f)
f,ax=plt.subplots(figsize=(6.5,2.8));names=['Population estimate','Last answer','Personal history'];vals=[inner['brier'][m] for m in ['population','last','history']]
bars=ax.barh(names,vals,color=['#9dabb4','#b9a899','#3c7067']);ax.invert_yaxis();ax.set_xlim(0,.39);ax.set_xlabel('Participant-mean Brier error · lower is better')
for b,v in zip(bars,vals):ax.text(v+.007,b.get_y()+b.get_height()/2,f'{v:.3f}',va='center')
f.tight_layout();f.savefig(fig/'history.png',dpi=180);plt.close(f)
f,ax=plt.subplots(figsize=(6.5,2.8));p=mem['remote_greater_fraction']['mean'];tie=mem['tie_fraction'];vals=[100*p,100*tie,100*(1-p-tie)]
bars=ax.barh(['Older has more content','Equal content','Newer has more content'],vals,color=['#3c7067','#b4b4b4','#70869b']);ax.invert_yaxis();ax.set_xlim(0,72);ax.set_xlabel('Mean within-person pair fraction (%)')
for b,v in zip(bars,vals):ax.text(v+1,b.get_y()+b.get_height()/2,f'{v:.1f}%',va='center')
f.tight_layout();f.savefig(fig/'memory.png',dpi=180);plt.close(f)

pages=[]
def page(title,subtitle):
    x={'title':title,'subtitle':subtitle,'blocks':[]};pages.append(x);return x['blocks']
def p(b,t):b.append(('p',t))
def h(b,t):b.append(('h',t))
def table(b,headers,rows):b.append(('table',(headers,rows)))
def image(b,path,caption):b.append(('image',(path,caption)))

b=page('Testing the two in one','Streams and Rocks  |  Research protocol and completed public data checks  |  22 October 2026')
p(b,'Purpose: test how an idea moves within one person, how inward speaking and listening affect it, and how that person’s history enters the process. This document fixes the current interpretation, reports two completed measurement probes, and supplies forms for the observations still missing.')
image(b,'figures/within_person.png','The arrows express the author’s proposed relationship. They do not establish a physical or psychological mechanism.')
h(b,'The working interpretation')
p(b,'Smoke is the inward speaking position. Clay is the inward listening position. The middle is the idea moving between them. Both positions can change what is retained, questioned, reformulated or refused. These are functions within one person, not two people or permanent personality classes.')
p(b,'Each person has a distinct history. Keep recorded events, remembered versions and what is recalled now separate. Missing history stays unknown. A clear childhood memory and a dreamlike recent memory are both admissible observations.')
h(b,'What this document establishes')
p(b,'The completed checks use real public records of inner experience and recalled memory content. They support narrowly stated associations. They do not measure the full Smoke–Clay–idea exchange or validate the corpus field equations as a model of thinking. The proposed diary study has not been run.')
p(b,'Arendt’s two-in-one provides a philosophical connection, while Smoke, Clay and the moving middle are this project’s interpretation. Her gadfly, midwife and electric-ray images describe different effects of thought. Peace can contain active thought; disturbance is not automatically failure. [1]')

b=page('1 Define what is being observed','Use participant descriptions first and distinguish interpretation from measurement')
table(b,['Term','Working description','Record separately'],[
 ['Smoke','Inward speaking','The proposition put forward and its wording, image or nonverbal form'],
 ['Clay','Inward listening','What is received, held, challenged, revised or refused'],
 ['Moving idea','Content changing between positions','Before and after accounts; which claim, target, implication or force changed'],
 ['Mist','Internalized or unspoken agreement','Agreement, assumptions and freedom to reconsider'],
 ['Fog','Remembered past with variable clarity','Content, vividness, certainty and independently checkable accuracy'],
 ['Wind','Space between memories and experienced time','Actual event age, recall duration and felt temporal distance'],
 ['Perceived balance','Calm or agreement may coexist with disturbance','Calm, agreement and unresolved tension as separate ratings'],
 ['Water','Adaptation where this word fits','What changed, what persisted and what that change cost']])
p(b,'D₂O is the author’s image for perceived balance. H₂O₂ is a different substance; its specific role in this interpretation remains undefined. Leave peroxide unassigned until the author supplies its intended relationship. No chemical properties become psychological causes by analogy.')
h(b,'Keep the semantic force')
p(b,'Retain coercion, resistance, refusal, pressure and conflict when they express the reported experience. Attribute the account and state the comparison still needed. Do not automatically soften strong language or infer a diagnosis from it. Participants may reject any material description or report no distinguishable inner positions.')
p(b,'Do not score calm as healthy or disagreement as compromised. A peaceful exchange can change an idea; agreement can leave tension unresolved. These possibilities must be recorded rather than decided by the labels.')

b=page('2 Completed check of recorded personal history','Public inner experience reports  |  Observational prediction  |  Not a causal memory test')
p(b,'Nedergaard, Skewes and Wallentin’s original and replication experiments repeatedly sampled experience during a task. The processed files contain 1,696 reports from 212 people and 2,664 reports from 222 people. Among reports of an inner voice, people rated whether it was dialogic. Other experience reports are structurally missing for this outcome, not negative answers. [2]')
p(b,'The original experiment alone selected the history weight from five declared choices. The replication supplied 632 later qualifying predictions from 142 people with sufficient reports. Each prediction used only that person’s earlier qualifying answers. Every eligible person receives equal weight in the error summary.')
image(b,'figures/history.png','Agree or partly agree counts as dialogic endorsement. Error is squared probability error, averaged first within people and then across people.')
table(b,['Comparison','Mean difference','95 percent participant bootstrap interval'],[
 ['History minus population','−0.043','−0.070 to −0.015'],
 ['History minus last answer','−0.115','−0.151 to −0.081']])
p(b,'The stricter “Agree only” sensitivity also favored history: 0.145 error versus 0.178 population and 0.209 last answer. These intervals condition on the selected predictor; they do not include uncertainty from every earlier modeling choice.')
p(b,'Interpretation: recorded personal history improved this prediction. Stable response habits or personal differences could produce the advantage without a causal effect of earlier thought on later thought. No lifelong biography, separate internal roles or idea content was observed. The replication was reserved for tuning in this analysis, but the published study was consulted; it is not an untouched model-selection holdout.')

b=page('3 Completed check of memories from different life periods','Public CRAM records  |  Counted recalled content  |  Not verified vividness or accuracy')
p(b,'The CRAM dataset dates memories to ten fractions of a person’s life and counts content in eight categories. Bin 0 is most remote and bin 9 most recent. This analysis retained 12,982 complete, single-bin scored memories from 4,115 people. Of these, 1,052 people had both remote memories (bins 0–7) and recent memories (bins 8–9). [3, 4]')
image(b,'figures/memory.png','All older/newer pairs are compared within each person; each person’s pair fraction then receives equal weight. These are different memories recalled at one assessment.')
p(b,'Recent memories contained 7.02 more counted elements on average within people, with a 95 percent participant bootstrap interval of 5.63 to 8.65. Requiring at least two memories in each range retained 703 people and gave a difference of 6.16 elements, interval 4.94 to 7.34.')
p(b,'Nevertheless, older memories had more counted content in 31.25 percent of within-person pairs on average, interval 29.57 to 32.90 percent. Equal content accounted for 6.16 percent. An average age association therefore does not justify making every older memory less detailed by definition.')
h(b,'What remains unknown')
p(b,'Content counts do not establish how clear, truthful or dreamlike a memory feels. The data do not follow the same memory changing over months and do not measure the author’s Wind construct. Rehearsal, event importance and recall selection could explain differences. The inner-speech and CRAM datasets contain different people and were not joined.')
p(b,'Exclusions were explicit: 23,390 rows lacked scored content; 1,258 had a non-single or invalid bin; two had invalid content values. The source’s 14,242 scored memories are broader than this declared single-bin complete-case sample. No values were silently repaired.')

b=page('4 Study the moving idea directly','Proposed feasibility study  |  Not yet recruited or run')
h(b,'Collect episodes within each person')
p(b,'A practical starting design is 20 consenting adults, three brief prompts per day for 14 days, plus optional event entries. This is a feasibility target, not a power calculation or a representative population claim. Keep random-prompt and self-selected entries distinct. Allow skipping and “no inner exchange” without treating either as failure.')
p(b,'Ask about the experience immediately before the prompt, then allow a brief follow-up at the next prompt. Record the delay between the experience and the report. Do not require people to create a dialogue, force a metaphor, or disclose private events. The act of reporting may itself change thought; measure that perceived effect.')
h(b,'Predeclare four questions')
table(b,['Question','Comparison and observation','What could challenge it'],[
 ['Does the idea move?','Pair before/after formulations of the same episode; code preservation, revision, rejection or uncertainty','Reports lack identifiable transitions, or coders cannot distinguish content change from rephrasing'],
 ['Does personal history help?','Predict later episode outcomes from earlier reports; compare population, last answer and personal-history baselines','No held-out gain, or gain disappears when stable person differences are controlled'],
 ['Can balance conceal tension?','Measure calm, agreement and unresolved tension independently in the same episode','Ratings fail to separate these constructs, or agreement consistently coincides with low tension'],
 ['Is felt distance different from age?','Record dated event age and felt temporal distance alongside vividness and rehearsal','Felt distance adds no repeatable information beyond measured event age and context']])
p(b,'Meaning check: the participant first identifies the intended claim and any change. Two independent reviewers then code claim, target, implication and force, blinded to the outcome being tested. Preserve disagreements. Similar words, matching embeddings or a shared topic alone do not establish the same meaning.')
p(b,'Select analysis choices using only a development group. Reserve whole participants for generalization and later time blocks for within-person forecasting; report these as different tests. Choose the final sample size after estimating feasible completion and within-person dependence, before opening confirmatory outcomes.')

b=page('5 Episode recording sheet','Copy one sheet per episode  |  Use a private participant code  |  A blank is not a zero')
table(b,['Field','Entry'],[
 ['Participant code and episode ID','________________________________________________'],
 ['Report time and estimated experience time','________________________________________________'],
 ['Context and prompt type','Random prompt / self-selected entry / follow-up\n________________________________________________'],
 ['Experience before the prompt','Words / images / nonverbal / no exchange / uncertain\n________________________________________________'],
 ['Smoke and the initial idea','What was put forward? Preserve wording or describe the image.\n________________________________________________\n________________________________________________'],
 ['Clay and the inward response','What was heard, held, challenged, reshaped or refused?\n________________________________________________\n________________________________________________'],
 ['Idea after the response','What changed or remained? Same claim / rephrased / revised / rejected / uncertain\n________________________________________________\n________________________________________________'],
 ['History recalled now','Private event ID(s), remembered account and relevance\n________________________________________________'],
 ['Independent ratings from 0 to 4','Calm __  Agreement __  Unresolved tension __\nVividness __  Certainty __  Freedom to reconsider __'],
 ['Time measures','Estimated event date or age __  Felt distance 0 near to 4 far __\nRecall duration __  Date certainty __'],
 ['Reporting and follow-up','Did the prompt change the thought? __\nSame idea at next prompt? __  Linked episode ID __']])
p(b,'Rating anchors: 0 = not at all, 1 = slightly, 2 = moderately, 3 = strongly, 4 = very strongly. Use “unknown” and “not applicable” explicitly. These are proposed items, not a validated scale. Ask participants whether the wording captures their experience before a confirmatory study.')

b=page('6 Record history without inventing it','Link each episode to the person’s own records and remembered accounts')
table(b,['History field','What belongs here'],[
 ['Private history ID','A local code connecting reports of the same event; no public name or identifying narrative'],
 ['Event and estimated date','Participant account, date range and confidence; distinguish event date from report date'],
 ['Independent record','Whether a contemporaneous record exists; unavailable is not false'],
 ['Earlier remembered version','What was reported before, when, and by whom; keep the original version'],
 ['Current retrieval','What is recalled now and what changed; do not overwrite earlier accounts'],
 ['Importance and rehearsal','Current importance, frequency of recall and recent reminders, each separately recorded'],
 ['Position-specific connection','Does the person connect this history to inward speaking, listening, both or neither?'],
 ['Missingness and consent','Skipped, forgotten, unclear or not shared; permission for storage and analysis']])
h(b,'Comparison rules')
p(b,'Predict before updating. At each episode, use only information recorded earlier. Keep the same person’s history separate from everyone else’s. Fit scaling, coding decisions and model parameters on development data only. Compare with a personal intercept or baseline to distinguish stable differences from changing history.')
p(b,'For a time-order claim, add a declared within-person order-shuffle control and a model using actual time gaps. A shuffled order may retain stable personal tendencies; if it predicts equally well, do not call the advantage evidence for temporal accumulation. Account for repeated observations by resampling people, not treating all episodes as independent.')
p(b,'A forecasting advantage is not a causal history effect. To test whether a specific reminder changes the next response, a separate consented randomized reminder design would need matched content, measured uptake, alternatives and a declared outcome. That experiment is proposed, not authorized or run here.')
h(b,'Keep records usable and limited')
p(b,'Store personal narratives privately, use local pseudonyms in analysis, and publish only consented de-identified derivatives. Keep participant accounts, researcher codes and model outputs in separate columns. Report refusals, missing entries and coding disagreement. Do not use the model to assign a diagnosis, moral rank or fixed material identity.')

b=page('7 Preserve the corpus and define a fair test','Exact equations remain intact  |  Observation links must be stated separately')
p(b,'The corrected corpus remains the mathematical source. Relevant equation groups are at paragraphs 229–230, 517–519 and 545–550. The accompanying MODEL.md reproduces the coupled momentum, incompressibility, field transport, threshold, accumulated-input and stress equations. The existing full-field solver has not been altered for these measurement probes.')
table(b,['Fidelity requirement','Decision before a full-field test'],[
 ['Person-specific application','Define each person’s domain, units, inputs and observed boundary conditions; indexing by person is an application choice'],
 ['Initial accumulated input','Preserve the corpus’s zero initial A; represent earlier history by an explicit pre-observation evolution or separately justified mapping'],
 ['Direction and threshold','Retain the fixed direction e and the stated threshold law; do not replace it with damping or erase the tanh negative tail'],
 ['Signed field and accumulation','Do not clip S or introduce automatic forgetting without declaring an added model'],
 ['Observation model','Specify how recorded expressions, listening responses and idea changes map to fields and uncertainty'],
 ['Identifiability','Test whether different parameter settings or omitted mechanisms make indistinguishable predictions']])
h(b,'Evidence gates')
p(b,'Gate 1: participants understand the terms and can report the episode without being forced into the metaphor. Gate 2: content coding is repeatable and distinguishes rephrasing from changed meaning. Gate 3: the chosen model improves a declared outcome on reserved data against simple baselines. Gate 4: removing its distinctive mechanisms reduces performance. Gate 5: the result replicates in a new source or prospectively collected sample.')
p(b,'If a gate fails, report the failure and revise the relevant definition or measurement link. Once results have informed a revision, they become development evidence. New confirmatory data must then be collected or reserved elsewhere. Numerical convergence checks alone do not establish that a psychological mapping is correct.')
p(b,'Current status: public-data probes passed their numerical checks, but the full within-person field model has not passed these empirical gates. Earlier external-dialogue and moderation results remain useful historical comparisons; they do not observe this inner exchange.')

b=page('8 Sources and reproduction','SciSpace assisted discovery  |  Primary sources checked  |  No new human observations collected')
p(b,'[1] Arendt, H. (1971). Thinking and Moral Considerations. Social Research, 38, 417–446. Relevant discussion: 431–434 and 441–445. https://jonudell.net/h/arendt.pdf')
p(b,'[2] Nedergaard, J., Skewes, J., and Wallentin, M. (2023). “Stay Focused!” The Role of Inner Speech in Maintaining Attention During a Boring Task. DOI: 10.1037/xhp0001112. Data and analysis materials: https://osf.io/jgx7m/')
p(b,'[3] Autobiographical Memory Content and Recollection Frequency: Public Release of Quantitative Datasets and Representative Classification Analysis (2020). DOI: 10.5334/joc.105. CRAM dataset version 4: https://doi.org/10.6084/m9.figshare.10246958.v4. Public data license: CC0.')
p(b,'[4] Gardner and colleagues (2012). Quantitative Measurements of Autobiographical Memory Content. DOI: 10.1371/journal.pone.0044809. This source defines temporal youth bins and content scoring.')
p(b,'SciSpace located the CRAM sources and candidate measures of dialogical activity. The EEG dataset Thinking out loud (10.1038/s41597-022-01147-2) was screened out for this question: fixed commands do not track a moving autobiographical idea. IDAS-R (10.1080/10720537.2024.2446756) is a candidate instrument, not longitudinal evidence used here. Search summaries were not treated as completed validation.')
h(b,'Reproduce the completed checks')
p(b,'The study folder contains PROTOCOL.md, protocol_freeze.json, sources.json, derived numeric data, analysis code, predictions, person-level summaries and figures. Raw free-text responses and original participant IDs are omitted. Source download URLs and SHA256 hashes are recorded. Install requirements.txt, then run:')
for line in ['python analyze.py','python -m unittest -q','python verify_saved.py','python build_document.py']:b.append(('code',line))
p(b,'Twelve unit tests and 23,604 saved-result checks passed. Bootstrap uncertainty uses 2,000 participant resamples and a fixed seed. The frozen protocol predates outcome calculation but follows source and schema inspection; it is not a registered preregistration. All script and source hashes are available in the published package.')
p(b,'The latest author corrections determine the interpretation. The original corpus and notes are preserved as source material. The testing document distinguishes author definitions, philosophical connections, added statistical comparators and empirical results.')

doc=Document();sec=doc.sections[0];sec.page_width=Inches(8.5);sec.page_height=Inches(11)
for style in doc.styles:
    for border in style.element.findall('.//'+qn('w:pBdr')):
        border.getparent().remove(border)
doc.settings.odd_and_even_pages_header_footer=False
sec.different_first_page_header_footer=False
sec.top_margin=Inches(.65);sec.bottom_margin=Inches(.6);sec.left_margin=sec.right_margin=Inches(.7)
sec.header_distance=Inches(.25);sec.footer_distance=Inches(.25)
for n in ['Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3']:
    st=doc.styles[n];st.font.name='Calibri';st.font.color.rgb=RGBColor(0,0,0)
normal=doc.styles['Normal'];normal.font.size=Pt(11);normal.paragraph_format.space_after=Pt(6);normal.paragraph_format.line_spacing=1.04
doc.styles['Title'].font.size=Pt(25);doc.styles['Heading 1'].font.size=Pt(21);doc.styles['Heading 2'].font.size=Pt(13)
doc.styles['Subtitle'].font.size=Pt(10)
header=sec.header.paragraphs[0];header.text='STREAMS AND ROCKS     /     TWO IN ONE TESTING PROTOCOL';header.runs[0].font.size=Pt(8)
foot=sec.footer.paragraphs[0];foot.alignment=2;run=foot.add_run('22 October 2026  ·  ');run.font.size=Pt(8)
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');foot._p.append(fld)
def put_table(headers,rows):
    t=doc.add_table(rows=1,cols=len(headers));t.autofit=False
    widths=[2.05,5.05] if len(headers)==2 else [1.35,2.85,2.9]
    for col,w in zip(t.columns,widths):col.width=Inches(w)
    for c,x in zip(t.rows[0].cells,headers):c.text=x
    repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
    for row in rows:
        for c,x in zip(t.add_row().cells,row):c.text=x
    for i,row in enumerate(t.rows):
        trpr=row._tr.get_or_add_trPr();no=OxmlElement('w:cantSplit');trpr.append(no)
        for c,w in zip(row.cells,widths):
            c.width=Inches(w);pr=c._tc.get_or_add_tcPr();m=OxmlElement('w:tcMar')
            for tag in ['top','left','bottom','right']:
                z=OxmlElement('w:'+tag);z.set(qn('w:w'),'75');z.set(qn('w:type'),'dxa');m.append(z)
            pr.append(m);borders=OxmlElement('w:tcBorders')
            for edge in ['top','left','bottom','right']:
                z=OxmlElement('w:'+edge);z.set(qn('w:val'),'single');z.set(qn('w:sz'),'4');z.set(qn('w:color'),'D9D9D9');borders.append(z)
            pr.append(borders)
            if i==0:
                shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E9EFF3');pr.append(shade)
            for p0 in c.paragraphs:
                p0.paragraph_format.space_after=Pt(3);p0.paragraph_format.line_spacing=1
                for r0 in p0.runs:r0.font.size=Pt(10);r0.bold=i==0
    doc.add_paragraph().paragraph_format.space_after=Pt(0)
htmlpages=[]
for i,pg in enumerate(pages):
    if i:doc.add_page_break()
    doc.add_paragraph(pg['title'],'Title' if i==0 else 'Heading 1');doc.add_paragraph(pg['subtitle'],'Subtitle')
    ht=[f'<h1>{html.escape(pg["title"])}</h1><p class="subtitle">{html.escape(pg["subtitle"])}</p>']
    for kind,v in pg['blocks']:
        if kind in ['p','h','code']:
            dp=doc.add_paragraph(v,'Heading 2' if kind=='h' else 'Normal')
            if kind=='code':
                for rr in dp.runs:rr.font.name='Consolas';rr.font.size=Pt(10)
            tag={'p':'p','h':'h2','code':'pre'}[kind];ht.append(f'<{tag}>{html.escape(v)}</{tag}>')
        elif kind=='image':
            path,cap=v;doc.add_picture(str(R/path),width=Inches(6.6));dp=doc.add_paragraph(cap)
            for rr in dp.runs:rr.font.size=Pt(9);rr.italic=True
            ht.append(f'<figure><img src="{path}"><figcaption>{html.escape(cap)}</figcaption></figure>')
        else:
            headers,rows=v;put_table(headers,rows)
            ht.append('<table><thead><tr>'+''.join('<th>'+html.escape(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(x).replace('\n','<br>')+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>')
    htmlpages.append('<section>'+''.join(ht)+f'<footer>Streams and Rocks · section {i+1} of {len(pages)}</footer></section>')
doc.core_properties.title='Testing the two in one';doc.core_properties.subject='Within-person meaning, internal dialogue and personal history';doc.core_properties.author='Nous Volition research project'
doc.save(R/'Two_in_one_testing_protocol.docx')
style='''body{margin:0;background:#eceff1;color:#171717;font:16px/1.45 Calibri,Arial,sans-serif}section{background:white;max-width:900px;margin:25px auto;padding:55px;box-sizing:border-box}h1{font-size:30px;margin:0 0 8px}h2{font-size:19px;margin:24px 0 8px}.subtitle,figcaption,footer{font-size:13px;color:#454545}table{border-collapse:collapse;width:100%;font-size:14px;margin:15px 0}th,td{border:1px solid #d9d9d9;padding:9px;vertical-align:top}th{background:#e9eff3;text-align:left}figure{margin:20px 0}img{max-width:100%}footer{border-top:1px solid #ddd;padding-top:15px;margin-top:25px}pre{white-space:pre-wrap;background:#f5f5f5;padding:6px}@media print{body{background:white}section{margin:0;padding:0;page-break-after:always;max-width:none}}'''
(R/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Testing the two in one</title><style>'+style+'</style><body>'+''.join(htmlpages)+'</body></html>',encoding='utf-8')
(R/'document_content.json').write_text(json.dumps(pages,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('Built editable DOCX, HTML testing document and three figures.')
