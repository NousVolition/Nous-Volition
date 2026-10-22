"""Reanalyse real public annotations and exact randomized-study counts."""
from pathlib import Path
import argparse, collections, csv, hashlib, json, platform
import numpy as np
import scipy
from analysis_core import label_index, pair_id, cluster_interval, randomized_counts

ROOT=Path(__file__).resolve().parent
def read_csv(p, delimiter=','):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f,delimiter=delimiter))
def write_csv(p,rows):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main(raw, out):
    out.mkdir(parents=True,exist_ok=True)
    sources=json.loads((ROOT/'sources.json').read_text())
    for s in sources['files']:
        assert hashlib.sha256((raw/s['file']).read_bytes()).hexdigest()==s['sha256'],s['id']
    content=read_csv(raw/'content.tsv','\t');toxic=read_csv(raw/'toxicity.tsv','\t')
    cm,cc,cd=label_index(content,['toxic','neutral'],'match')
    tm,tc,td=label_index(toxic,['comment'],'toxic')
    flow=dict(content_rows=len(content),toxicity_rows=len(toxic),content_exact_duplicate_rows=cd,
              toxicity_exact_duplicate_rows=td,unique_pair_keys=len(cm)+len(cc),conflicting_pair_keys=len(cc),
              unique_comment_keys=len(tm)+len(tc),conflicting_comment_keys=len(tc),
              unambiguous_pairs=len(cm),meaning_match=sum(cm.values()),meaning_mismatch=sum(not v for v in cm.values()))
    changed={k:v for k,v in cm.items() if k[0]!=k[1]}
    flow.update(identical_pairs=len(cm)-len(changed),changed_pairs=len(changed),
                changed_match=sum(changed.values()),changed_mismatch=sum(not v for v in changed.values()))
    joined=[]; one_sided=[];statuses=collections.Counter();missing_matrix=collections.Counter()
    for (a,b),m in changed.items():
        if not m:continue
        sa='conflict' if (a,) in tc else 'available' if (a,) in tm else 'missing'
        sb='conflict' if (b,) in tc else 'available' if (b,) in tm else 'missing'
        missing_matrix[(sa,sb)]+=1
        if (b,) in tm:one_sided.append(tm[b,])
        if sa!='available' or sb!='available':continue
        oa,ob=tm[a,],tm[b,];statuses[(oa,ob)]+=1
        joined.append(dict(pair_id=pair_id(a,b),original_id=hashlib.sha256(a.encode()).hexdigest(),
                           original_label=int(oa),rewrite_label=int(ob),delta=int(ob)-int(oa)))
    joined.sort(key=lambda r:r['pair_id']);write_csv(out/'paired_labels.csv',joined)
    write_csv(out/'join_coverage.csv',[dict(original_status=a,rewrite_status=b,pairs=n) for (a,b),n in sorted(missing_matrix.items())])
    clusters=collections.defaultdict(list)
    for r in joined:clusters[r['original_id']].append(r['delta'])
    ci=cluster_interval([len(v) for v in clusters.values()],[sum(v) for v in clusters.values()])
    equal_original=cluster_interval([1 for v in clusters.values()],[float(np.mean(v)) for v in clusters.values()])
    pairs=dict(n=len(joined),originals=len(clusters),both_nonoffensive=statuses[(False,False)],
               nonoffensive_to_offensive=statuses[(False,True)],offensive_to_nonoffensive=statuses[(True,False)],
               both_offensive=statuses[(True,True)],original_offensive_rate=float(np.mean([r['original_label'] for r in joined])),
               rewrite_offensive_rate=float(np.mean([r['rewrite_label'] for r in joined])),
               rewrite_minus_original=ci,equal_weight_originals=equal_original,
               inference='Descriptive selected-pair label contrast; no causal test of moderation, no population prevalence estimate')
    flow.update(matched_changed_with_rewrite_label=len(one_sided),rewrite_label_offensive=sum(one_sided),
                matched_changed_two_labels=len(joined),two_label_coverage=len(joined)/sum(changed.values()))
    identical=[k for k,v in cm.items() if k[0]==k[1] and v and (k[0],) in tm]
    controls=dict(identical_with_label=len(identical),identical_label_changes=0,
                  note='The exact join reuses the same released label for identical strings; this is a data-integrity control, not an independent rater reliability test.')
    sample=sorted((pair_id(a,b),a,b) for (a,b),v in changed.items() if v)[:24]
    audit=read_csv(ROOT/'data/meaning_audit.csv')
    assert [r['pair_id'] for r in audit]==[x[0] for x in sample]
    audit_summary=dict(n=len(audit),verdicts=dict(collections.Counter(r['core_content_review'] for r in audit)),
                       reviewer='Single assistant qualitative audit, no independent new human ratings',
                       sampling='24 lowest SHA-256 pair IDs among changed pairs with unambiguous match=True; not selected by toxicity outcome')
    counts=json.loads((ROOT/'data/wiki_counts.json').read_text());t=counts['treatment'];c=counts['control']
    history=randomized_counts(t['any_later_award'],t['n'],c['any_later_award'],c['n'])
    daily=read_csv(raw/'WikipediaExp.csv');checks={}
    chronology=[]
    for group,expected in [('0',c),('1',t)]:
        rows=sorted([r for r in daily if r['experiment']==group],key=lambda r:int(r['timestamp']))
        assert len(rows)==121 and [int(r['timestamp']) for r in rows]==list(range(-30,91))
        events=sum(int(r['awardreceived']) for r in rows if int(r['timestamp'])>0)
        assert events==expected['total_later_awards']
        checks[group]=dict(group_day_rows=len(rows),additional_award_events=events,
                           day0=float(rows[30]['cumulativeproductivity']),day90=float(rows[-1]['cumulativeproductivity']),
                           first_award_day=min(int(r['timestamp']) for r in rows if int(r['awardreceived'])))
        cum=0
        for r in rows:
            if int(r['timestamp'])<=0:continue
            cum+=int(r['awardreceived']);chronology.append(dict(group=int(group),day=int(r['timestamp']),cumulative_award_events=cum))
    write_csv(out/'award_chronology.csv',chronology)
    history['daily_file_checks']=checks
    history['timing_scope_check']='The paper discusses day 8 in a productivity comparison of experimental recipients. The group-day file records the first treated award on day 8 and a control award on day 7. These can coexist; no table-versus-figure failure is asserted. Individual event-time models remain unavailable.'
    history['daily_file_unit']='242 group-day summaries, not 242 independent people. Award events 14/3 differ from people with any award 12/2.'
    history['productivity_baseline_check']=dict(raw_endpoint_ratio=checks['1']['day90']/checks['0']['day90'],
        baseline_subtracted_ratio=(checks['1']['day90']-1)/(checks['0']['day90']-1),
        note='Day 0 is 1 in both groups. About 60% applies to gains beyond that baseline, not raw endpoint ratio. Productivity is ancillary and no individual-level significance test is reconstructed.')
    results=dict(date='2026-10-21',data_kind='Reanalysis of real human annotations and a published randomized experiment',
                  flow=flow,paired_labels=pairs,controls=controls,meaning_audit=audit_summary,history=history,
                  software=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__),
                  protocol_sha256=hashlib.sha256((ROOT/'data/protocol.json').read_bytes()).hexdigest(),
                  sources_sha256=hashlib.sha256((ROOT/'sources.json').read_bytes()).hexdigest())
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(flow=flow,paired=pairs,audit=audit_summary,history=history),indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--raw-dir',type=Path,default=ROOT/'raw');parser.add_argument('--out-dir',type=Path,default=ROOT/'data')
    args=parser.parse_args();main(args.raw_dir,args.out_dir)
