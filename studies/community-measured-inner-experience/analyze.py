"""Analyze supplied measurements. Does not fit, replace, or run the field model."""
from pathlib import Path
import argparse, collections, csv, hashlib, json, platform, re
import numpy as np
import scipy
from scipy import stats
import openpyxl

HERE=Path(__file__).resolve().parent
SEED=20261023
SUBS=['Dialogic','Evaluative','Condensed','Other','Positive']

def write_json(path,data):
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')

def table(path,sheet=None):
    wb=openpyxl.load_workbook(path,read_only=True,data_only=True)
    ws=wb[sheet] if sheet else wb.active
    it=iter(ws.values); header=next(it)
    rows=[dict(zip(header,row)) for row in it]
    wb.close()
    return list(header),rows

def csv_out(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def paired(rows,name,seed=SEED):
    pairs=[(r[f'VISQ_{name}_RUM'],r[f'VISQ_{name}_DIS']) for r in rows
           if r[f'VISQ_{name}_RUM'] is not None and r[f'VISQ_{name}_DIS'] is not None]
    a=np.asarray(pairs,float);d=a[:,0]-a[:,1];n=len(d)
    se=float(stats.sem(d));mean=float(d.mean())
    tlo,thi=stats.t.interval(.95,n-1,loc=mean,scale=se)
    rng=np.random.default_rng(seed)
    boot=d[rng.integers(0,n,size=(20000,n))].mean(axis=1)
    lo,hi=np.quantile(boot,[.025,.975])
    return dict(subscale=name,n_pairs=n,rumination_mean=float(a[:,0].mean()),distraction_mean=float(a[:,1].mean()),
        mean_difference=mean,median_difference=float(np.median(d)),bootstrap_low=float(lo),bootstrap_high=float(hi),
        t_low=float(tlo),t_high=float(thi),positive=int((d>0).sum()),tied=int((d==0).sum()),negative=int((d<0).sum()),
        p_paired_t=float(stats.ttest_rel(a[:,0],a[:,1]).pvalue))

def holm(rows):
    order=sorted(range(len(rows)),key=lambda i:rows[i]['p_paired_t']);running=0
    for rank,i in enumerate(order):
        running=max(running,min(1.,(len(rows)-rank)*rows[i]['p_paired_t']))
        rows[i]['p_holm_five']=running

def audit_rum(path):
    headers,rows=table(path,'Data')
    assert len(rows)==31 and len({r['ID'] for r in rows})==31
    assert set(r['Order'] for r in rows)=={1,2}
    potential={r['ID'] for r in rows for n in ['Dialogic','Condensed']
               if (v:=r[f'VISQ_{n}_DIS']) is not None and not float(v).is_integer()}
    summaries=[]
    for cohort,rs in [('all_supplied',rows),('exclude_fractional_flag',[r for r in rows if r['ID'] not in potential])]:
        part=[dict(cohort=cohort,**paired(rs,n,SEED+i)) for i,n in enumerate(SUBS)];holm(part);summaries+=part
    order_rows=[dict(induction_order=order,**paired([r for r in rows if r['Order']==order],n,SEED+i))
                for order in [1,2] for i,n in enumerate(SUBS)]
    assert all(2<=r[f'VISQ_{n}_{c}']<=14 for r in rows for n in SUBS for c in ['RUM','DIS'] if r[f'VISQ_{n}_{c}'] is not None)
    audit=dict(participants=len(rows),order_counts=dict(collections.Counter(r['Order'] for r in rows)),
        missing_visq_sum_cells=sum(r[f'VISQ_{n}_{c}'] is None for r in rows for n in SUBS for c in ['RUM','DIS']),
        fractional_sum_flagged_people=len(potential),imputation_note='Source reports mean imputation of two distraction items in one person. Fractional-sum flag is inferential; raw item provenance is unavailable.',
        probe_level_rows_available=False,per_person_history_input_available=False,
        supplied_columns=headers,emg_complete_paired_people=sum(all(r[f'{c}_{m}_MAX_ln'] is not None for c in ['RUM','DIS'] for m in ['FRO','OOS','OOI']) for r in rows))
    return audit,summaries,order_rows

def audit_creativity(root):
    sh,all_subjects=table(root/'dataset_subject_level.xlsx')
    subjects=[s for s in all_subjects if s['sys_id'] is not None]
    ghosts=[s for s in all_subjects if s['sys_id'] is None]
    assert all(all(v is None or (k=='dt_fluency_score' and isinstance(v,(int,float))) for k,v in s.items()) for s in ghosts)
    ids={s['sys_id'] for s in subjects};assert len(ids)==len(subjects)==350
    rh,responses=table(root/'dataset_response_level.xlsx')
    counts=collections.Counter(r['ans_is_valid'] for r in responses)
    assert counts=={0:241,1:3108}
    unmatched=[r for r in responses if r['sys_id'] not in ids]
    joined=[r for r in responses if r['sys_id'] in ids]
    valid=[r for r in joined if r['ans_is_valid']==1]
    byseq=collections.defaultdict(list)
    for r in joined:byseq[r['sys_id'],r['prompt_order']].append(r)
    duplicates=len(joined)-len({(r['sys_id'],r['prompt_order'],r['ans_order']) for r in joined})
    gaps=sum(any(b-a!=1 for a,b in zip(sorted(r['ans_order'] for r in seq),sorted(r['ans_order'] for r in seq)[1:])) for seq in byseq.values())
    linked_pairs=[];same=0;known=0
    for seq in byseq.values():
        seq=sorted(seq,key=lambda r:r['ans_order'])
        for a,b in zip(seq,seq[1:]):
            if b['ans_order']-a['ans_order']==1 and a['ans_is_valid']==b['ans_is_valid']==1:
                linked_pairs.append((a,b))
                if a['ans_cat'] is not None and b['ans_cat'] is not None:
                    known+=1;same+=int(a['ans_cat']==b['ans_cat'])
    errors=[abs(np.mean([s[f'dial_state_{i}'] for i in range(1,5)])-s['dial_state_mean']) for s in subjects]
    assert max(errors)<1e-12
    missing_state=sum(s[f'dial_state_{i}'] is None for s in subjects for i in range(1,5))
    qsf=json.loads((root/'qualtrics_experiment.qsf').read_text(encoding='utf-8-sig'))
    state_questions=[];analogy_questions=[]
    for e in qsf['SurveyElements']:
        if e.get('Element')!='SQ':continue
        q=e['Payload'];tag=q.get('DataExportTag','').strip()
        if tag.startswith('state_f'):
            state_questions.append(dict(tag=tag,question_id=q['QuestionID'],
                recode_values=q.get('RecodeValues'),choices=list(q.get('Choices',{})),
                stored_mapping_to_dial_state_columns='Not specified in downloaded files; no guessed item-column match'))
        if tag.startswith('state_dt_analogy'):analogy_questions.append(tag)
    formulas=openpyxl.load_workbook(root/'dataset_subject_level.xlsx',read_only=True,data_only=False)
    ghost_formula_rows=0
    for row in list(formulas.active.values)[1:]:
        if row[0] is None and isinstance(row[48],str) and row[48].startswith('='):ghost_formula_rows+=1
    formulas.close()
    return dict(subject_rows=len(all_subjects),participants=len(subjects),nonparticipant_rows=len(ghosts),nonparticipant_formula_rows=ghost_formula_rows,
        responses=len(responses),response_people=len({r['sys_id'] for r in responses}),valid_responses_source=counts[1],invalid_responses_source=counts[0],
        unmatched_response_rows=len(unmatched),unmatched_response_people=len({r['sys_id'] for r in unmatched}),unmatched_valid_rows=sum(r['ans_is_valid']==1 for r in unmatched),
        joined_response_rows=len(joined),joined_valid_responses=len(valid),joined_sequences=len(byseq),duplicate_order_keys=duplicates,sequences_with_internal_gaps=gaps,
        people_with_two_ordered_prompts=sum(len({r['prompt_order'] for r in joined if r['sys_id']==pid})==2 for pid in ids),
        adjacent_valid_response_pairs=len(linked_pairs),adjacent_pairs_with_category=known,adjacent_equal_category_pairs=same,
        equal_category_note='Same supplied coding category; not verified preservation of a person\'s intended meaning or evidence of copying.',
        item_timestamp_columns=[h for h in rh if re.search(r'time|date|duration',h,re.I)],
        subject_total_duration_available='sys_duration' in sh,
        missing_state_item_cells=missing_state,state_mean_recalculation_max_error=float(max(errors)),
        state_question_recode_audit=state_questions,analogy_questions_present_in_survey=analogy_questions,
        analogy_response_columns_present=any('analogy' in h for h in sh+rh),
        recoding_warning='QSF choices display 1=Never to 5=Very often, but explicit recodes map 1 to 5 and 5 to 1. Published workbook means are retained without reversal; export-to-analysis mapping is unresolved. No directional dialogue/originality inference is made.',
        subject_columns=sh,response_columns=rh)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data-dir',type=Path,required=True);ap.add_argument('--output-dir',type=Path,default=HERE/'results');a=ap.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((HERE/'sources.json').read_text(encoding='utf-8'))
    for f in manifest['files']:
        p=a.data_dir/f['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'],f['file']+' source hash changed'
    rum,summary,order=audit_rum(a.data_dir/'RUM_master_data.xlsx');creative=audit_creativity(a.data_dir)
    csv_out(a.output_dir/'paired_visq.csv',summary);csv_out(a.output_dir/'order_sensitivity.csv',order)
    write_json(a.output_dir/'measurement_audit.json',dict(moffatt=rum,labrie=creative))
    write_json(a.output_dir/'run_status.json',dict(analysis='measured-data audit and paired descriptive inference',full_field_empirical_runs=0,
        simpler_predictive_models_fitted=0,synthetic_field_runs=0,imputed_by_this_analysis=0,individual_histories_fabricated=0,
        full_model_status='Not run: observation map and field/history inputs are not identified by these records.',
        bootstrap_seed=SEED,bootstrap_resamples=20000,python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,openpyxl=openpyxl.__version__))
    print(json.dumps(dict(paired_results=[r for r in summary if r['cohort']=='all_supplied'],moffatt_audit={k:v for k,v in rum.items() if k!='supplied_columns'},creativity_audit={k:v for k,v in creative.items() if k not in ['subject_columns','response_columns','state_question_recode_audit']}),indent=2))

if __name__=='__main__':main()
