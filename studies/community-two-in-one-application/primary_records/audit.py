"""Reproduce primary-source inventory, selected-case provenance and workbook coverage.

No text embeddings, predictors, invented field inputs, automatic form assignments,
or inferred thought timestamps. Source PDFs/workbook remain outside publication.
"""
from pathlib import Path
import argparse, hashlib, json, re
from collections import Counter
from pypdf import PdfReader
import openpyxl

ROOT = Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def audit(raw):
    sources=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))
    checked=[]
    for f in sources:
        p=raw/f['file']
        if not p.exists() or sha(p)!=f['sha256']:
            raise ValueError('Missing or changed source: '+f['file'])
        checked.append(f['file'])
    inventory=[];all_pages={};pdf_pages=0
    for f in sources:
        if not f['file'].endswith('.pdf'):continue
        p=raw/f['file'];pages=[x.extract_text() or '' for x in PdfReader(p).pages]
        pdf_pages+=len(pages);all_pages[f['file']]=pages
        if not re.search(r'lena_interview_\d+_sampling',f['file']):continue
        interview=int(re.search(r'interview_(\d+)_',f['file'])[1])
        for page,t in enumerate(pages,1):
            for m in re.finditer(r'SAMPLE\s+(\d+\.\d+)\s+DISCUSSION STARTS HERE',t):
                sample=m[1];day=int(sample.split('.')[0])
                tail=t[m.end():]
                time=re.search(r'\b(\d{1,2}:\d{2})\b',tail)
                inventory.append(dict(sample=sample,day=day,interview=interview,file=f['file'],page=page,
                    interview_offset=time[1] if time else None,
                    original_thought_time=None,training=day==1,
                    original_url=f['url'],review_scope='marker indexed; complete episode read only if in annotations.json'))
    inventory.sort(key=lambda x:tuple(map(int,x['sample'].split('.'))))
    keys=[x['sample'] for x in inventory]
    if len(set(keys))!=len(keys):raise ValueError('Duplicate sample marker')
    annotations=json.loads((ROOT/'annotations.json').read_text(encoding='utf-8'))
    for a in annotations:
        rec=next(x for x in inventory if x['sample']==a['sample'])
        if rec['interview']!=a['interview']:raise ValueError('Wrong interview')
        pages=all_pages[rec['file']]
        if not all(1<=p<=len(pages) for p in a['pages_reviewed']):raise ValueError('Invalid page locator')
        if a['form_status'].lower() in {'water','fog','mist','wind','d2o'}:raise ValueError('Unwarranted form label')
    # Only schema/counts, no clinical association or outcome model.
    w=openpyxl.load_workbook(raw/'aphasia_workbook.xlsx',read_only=True,data_only=True)
    sheets={}
    for name,key in [('QuantWide','ID'),('GISQ_Full','RC_Number')]:
        it=iter(w[name].values);header=list(next(it));k=header.index(key)
        rows=[dict(zip(header,r)) for r in it if str(r[k]).isdigit()]
        sheets[name]=dict(keyed_rows=len(rows),people=len({str(r[key]) for r in rows}),columns=header)
        if name=='GISQ_Full':sheets[name]['waves']=dict(sorted(Counter(r['GISQ_Number'] for r in rows).items()))
    training=sum(x['training'] for x in inventory)
    out=dict(source_files_verified=len(checked),pdf_pages_downloaded=pdf_pages,
        people_in_DES_case=1,des_samples_indexed=len(inventory),training_samples=training,
        post_training_samples=len(inventory)-training,days=dict(sorted(Counter(str(x['day']) for x in inventory).items(),key=lambda z:int(z[0]))),
        fully_read_selected_episodes=len(annotations),annotation_method='one assistant; exploratory; no independent second coder',
        workbook=sheets,source_eligibility='partial construct records; full predictive observation mapping unspecified',
        full_empirical_fit_completed=False,prediction_score=None,forms_classified=0,
        new_coupled_simulations=0,corpus_solver_sha256=sha(ROOT.parent/'corpus_field.py'),
        plan_sha256=sha(ROOT.parent/'PRIMARY_RECORD_PLAN.md'),inventory=inventory)
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--check',action='store_true');a=p.parse_args()
    result=audit(a.raw);target=ROOT/'results.json'
    if a.check:
        assert result==json.loads(target.read_text(encoding='utf-8')),'Saved result differs'
    else:target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['source_files_verified','pdf_pages_downloaded','des_samples_indexed','training_samples','post_training_samples','fully_read_selected_episodes','full_empirical_fit_completed','prediction_score']}))
if __name__=='__main__':main()
