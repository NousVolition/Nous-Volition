"""Audit real records without assigning unobserved two-in-one constructs.

Reserved response values are parsed with the files but never analyzed or summarized.
"""
from pathlib import Path
import csv,hashlib,json,math,collections
ROOT=Path(__file__).resolve().parent
RAW=ROOT.parent.parent/'work'/'twoinone-application-raw'
RESULT=ROOT/'results'
ITEMS=['aff','arou','att','conf','delib','eng','fut','image','ling','mvmt','past','ppl','self']

def split(ids):
    order=sorted(ids,key=lambda s:hashlib.sha256(('two-in-one-2026-v1:'+s).encode()).hexdigest())
    return set(order[:8]),order[8:]

def main():
    RESULT.mkdir(exist_ok=True)
    files=sorted(RAW.rglob('*events.tsv'))
    ids={p.parts[-4] for p in files};reserved,dev=split(ids)
    counts=collections.Counter();runs=[];issues=[];headers=collections.Counter();dictionaries=set()
    development_values=collections.defaultdict(list);missing=collections.Counter()
    for path in files:
        person,session=path.parts[-4:-2]
        with path.open(encoding='utf-8-sig',newline='') as h:rows=list(csv.DictReader(h,delimiter='\t'))
        headers[tuple(rows[0])]+=1
        dictionary=json.loads(path.with_suffix('.json').read_text())
        dictionaries.add(json.dumps(dictionary,sort_keys=True))
        groups=collections.defaultdict(list)
        for row in rows:groups[int(float(row['trial']))].append(row)
        for trial,gg in groups.items():
            cc=collections.Counter(r['item'] for r in gg)
            if cc!=collections.Counter(ITEMS):issues.append(dict(file=path.relative_to(RAW).as_posix(),trial=trial,issue='item coverage',items=dict(cc)))
        times=[float(r['onset']) for r in rows];offset=[float(r['offset']) for r in rows]
        if not all(math.isfinite(t) for t in times+offset):raise ValueError('Nonfinite time')
        if any(b<a for a,b in zip(times,offset)):issues.append(dict(file=path.relative_to(RAW).as_posix(),issue='offset before onset'))
        if any(b<a for a,b in zip(times,times[1:])):issues.append(dict(file=path.relative_to(RAW).as_posix(),issue='unordered onset'))
        # Never pool personal time across unobserved run/day gaps.
        for row in rows:
            counts[row['item']]+=1
            if person not in reserved:
                try:v=float(row['response'])
                except ValueError:
                    missing[(row['item'],row['response'])]+=1;continue
                if math.isfinite(v):development_values[row['item']].append(v)
                else:missing[(row['item'],'nonfinite')]+=1
        runs.append(dict(person=person,session=session,run=path.stem.split('_run-')[1].split('_')[0],split='reserved' if person in reserved else 'development',probes=len(groups),item_rows=len(rows),first_probe_onset_s=min(times),last_item_offset_s=max(offset),history_probes=len(groups)//2,future_probes=len(groups)-len(groups)//2,source_file=path.relative_to(RAW).as_posix()))
    with (RESULT/'run_coverage.csv').open('w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=list(runs[0]));w.writeheader();w.writerows(runs)
    findings=dict(participants=len(ids),sessions=len({(x['person'],x['session']) for x in runs}),runs=len(runs),probes=sum(x['probes'] for x in runs),item_rows=sum(x['item_rows'] for x in runs),item_counts=dict(counts),reserved_participants=sorted(reserved),development_participants=dev,reserved_response_values_used=False,header_variants=[dict(columns=list(k),files=v) for k,v in headers.items()],dictionary_variants=len(dictionaries),issues=issues,development_response_ranges={k:[min(v),max(v),len(v)] for k,v in development_values.items()},full_model_fit_performed=False,reason='No independent observations of inward receiving, meaning, utility, form labels or their observation functions. A movement-only mapping would not test the requested full model.')
    findings['development_nonnumeric_or_nonfinite']=[dict(item=k[0],source_token=k[1],count=v) for k,v in missing.items()]
    (RESULT/'data_audit.json').write_text(json.dumps(findings,indent=2)+'\n',encoding='utf-8')
    # Preserve the source codebook verbatim as metadata, not participant narratives.
    (ROOT/'source_codebook.json').write_text(next(iter(dictionaries))+'\n',encoding='utf-8')
    (RESULT/'split.json').write_text(json.dumps(dict(reserved=sorted(reserved),development=dev,rule="SHA256('two-in-one-2026-v1:'+ID)",reserved_responses_analyzed=False),indent=2)+'\n')
    print(json.dumps({k:findings[k] for k in ['participants','sessions','runs','probes','item_rows','dictionary_variants','reserved_response_values_used','full_model_fit_performed']}))
    print('Issues:',len(issues));print('Development ranges:',findings['development_response_ranges'])
if __name__=='__main__':main()
