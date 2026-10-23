"""Read original records; publish numeric coverage only, no inferred inner roles."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import openpyxl

ROOT=Path(__file__).resolve().parent
RAW=ROOT.parents[1]/'work'/'twoinone-field-raw'
R=ROOT/'results'
HEADERS=(None,'Transcribed Sentence','Start Time','End Time','category','topic','thoughtID')

def audit_file(p):
    w=openpyxl.load_workbook(p,read_only=True,data_only=True)
    records=list(w.active.values);w.close()
    header=tuple(records[0])
    assert len(set(header))==len(header) and set(HEADERS).issubset(header), (p.name,header)
    extra=[j for j,k in enumerate(header) if k not in HEADERS]
    extra_populated=sum(r[j] is not None for r in records[1:] for j in extra)
    # A few source files swap topic and category. Bind by name, never position.
    columns=[header.index(k) for k in HEADERS]
    rows=[tuple(r[j] for j in columns) for r in records[1:]];groups=defaultdict(list)
    for r in rows: groups[r[6]].append(r)
    times=np.array([[r[2],r[3]] for r in rows],dtype=float)
    tid=np.array([r[6] for r in rows],dtype=float)
    embedding=RAW/'embeddings'/p.name.replace('_transcripts.xlsx','_embeddings.csv')
    E=np.loadtxt(embedding,delimiter=',',skiprows=1)
    dims=E.shape[1]-1
    anomalies=dict(nonfinite_times=int((~np.isfinite(times)).any(axis=1).sum()),
        nonpositive_duration=int((times[:,1]-times[:,0]<=1e-8).sum()),
        start_reversals=int((np.diff(times[:,0]) < -1e-8).sum()),
        overlapping_neighbor_rows=int((times[:-1,1]-times[1:,0]>1e-8).sum()),
        multi_category_thoughts=sum(len({r[4] for r in a})!=1 for a in groups.values()),
        missing_text=sum(not isinstance(r[1],str) or not r[1].strip() for r in rows),
        missing_topic=sum(r[5] is None for r in rows),
        thought_id_reversals=int((np.diff(tid)<0).sum()),
        thought_embedding_count_mismatch=int(len(groups)!=len(E)),
        bad_embedding_values=int((~np.isfinite(E[:,1:])).sum()),
        zero_embedding_rows=int((np.linalg.norm(E[:,1:],axis=1)==0).sum()))
    sequential=sorted(groups)==list(range(1,len(groups)+1))
    assert dims==768
    assert np.array_equal(E[:,0],np.arange(len(E)))
    counts=Counter()
    for a in groups.values(): counts[str(a[0][4])]+=1
    return dict(record=p.stem.replace('_transcripts',''),sentences=len(rows),thoughts=len(groups),embedding_rows=len(E),embedding_dimensions=dims,
        first_start=float(times[0,0]),last_end=float(times[-1,1]),span_seconds=float(times[-1,1]-times[0,0]),
        sequential_thought_ids=bool(sequential),source_header_reordered=header!=HEADERS,
        extra_columns=len(extra),populated_extra_cells=extra_populated,**anomalies),counts

def main():
    R.mkdir(exist_ok=True)
    manifest=json.loads((ROOT/'source_manifest.json').read_text())
    for f in manifest['files']:
        assert hashlib.sha256((RAW/f['path']).read_bytes()).hexdigest()==f['sha256'], f['path']
    rows=[];cat=Counter()
    for p in sorted((RAW/'behav_data').glob('*_transcripts.xlsx')):
        r,c=audit_file(p);rows.append(r);cat.update(c)
    assert len(rows)==118
    with (R/'record_coverage.csv').open('w',newline='',encoding='utf-8') as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
    aggregate_keys=['sentences','thoughts','embedding_rows','nonfinite_times','nonpositive_duration','start_reversals','overlapping_neighbor_rows','multi_category_thoughts','missing_text','missing_topic','thought_id_reversals','thought_embedding_count_mismatch','bad_embedding_values','zero_embedding_rows']
    s=dict(participants=len(rows),**{k:sum(r[k] for r in rows) for k in aggregate_keys},
        sequential_thought_ids_all=all(r['sequential_thought_ids'] for r in rows),
        source_files_with_reordered_columns=sum(r['source_header_reordered'] for r in rows),
        source_files_with_extra_columns=sum(r['extra_columns']>0 for r in rows),
        populated_extra_cells=sum(r['populated_extra_cells'] for r in rows),
        embedding_dimensions=768,thought_category_counts=dict(sorted(cat.items())),
        session_span_seconds=dict(min=min(r['span_seconds'] for r in rows),median=float(np.median([r['span_seconds'] for r in rows])),max=max(r['span_seconds'] for r in rows)),
        sentence_headers=[x for x in HEADERS if x],
        full_two_in_one_fit_performed=False,
        missing_observation_definitions=['Smoke inward-speaking observable','Clay inward-listening observable','S and u observation map in a continuous metric domain','Utility U and its comparison baseline','Recorded pre-session input or initial-state inference for history','Water perceived balance and other idea-form labels'],
        source_files_verified=len(manifest['files']))
    (R/'data_audit.json').write_text(json.dumps(s,indent=2)+'\n')
    print(json.dumps(s,indent=2))

if __name__=='__main__':main()
