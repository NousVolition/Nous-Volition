"""Verify saved study, representative full reruns and publication manifest."""
from pathlib import Path
import csv,json,hashlib,re,sys
import numpy as np
from model import LABELS,make_community,run,metrics,audit
ROOT=Path(__file__).resolve().parent
checks=[]
def check(name,condition):
    checks.append(dict(name=name,passed=bool(condition)))
    if not condition:raise AssertionError(name)
def read(path):
    with path.open(encoding='utf-8') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    protocol=json.loads((ROOT/'data/protocol.json').read_text());execution=json.loads((ROOT/'data/execution.json').read_text())
    check('Frozen model/runner/test source hashes unchanged',all(sha(ROOT/k)==v for k,v in protocol['source_sha256'].items()))
    check('19 passing unit tests recorded',bool(re.search(r'Ran 19 tests.*\bOK\b',(ROOT/'data/test_log.txt').read_text(),re.S)))
    rows=read(ROOT/'data/cases.csv');members=read(ROOT/'data/members.csv');extra=read(ROOT/'data/sensitivity.csv')
    check('Main, member and sensitivity counts',len(rows)==2688 and len(members)==18816 and len(extra)==1008)
    check('All main and sensitivity paths passed full accounting during execution',max(execution['accounting_maxima'].values())<1e-12)
    timeline=np.load(ROOT/'data/timelines.npz',allow_pickle=False)['values']
    check('Complete finite main timeline archive',timeline.shape==(2688,60,5) and np.all(np.isfinite(timeline)))
    check('Timeline completion/plan fractions bounded',timeline[:,:,[0,4]].min()>=-1e-12 and timeline[:,:,[0,4]].max()<=1+1e-12)
    member_error=0.
    for row in rows:
        index=int(row['case_id']);target=LABELS.index(row['target']);m=members[index*7:(index+1)*7]
        member_error=max(member_error,abs(float(m[target]['post_work'])-float(row['target_work'])),
            abs(np.mean([float(r['post_work']) for j,r in enumerate(m) if j!=target])-float(row['others_work'])))
    check('Individual work agrees with case summary',member_error<1e-12)
    inputs=json.loads((ROOT/'data/inputs.json').read_text())
    check('All 24 underlying communities saved',len(inputs)==24)
    for d in inputs:
        c=make_community(d['seed'])
        for key,value in [('skill',c.skill),('willing',c.willing),('planned',c.planned),('unit_load_demand',c.demand)]:
            if not np.array_equal(value,np.array(d[key])):raise AssertionError('Input mismatch')
    check('Saved inputs exactly regenerate from seeds',True)
    example=np.load(ROOT/'data/example_traces.npz',allow_pickle=False)
    for index in (0,3,5,7,200,541,1000,1344,2003,2683,2684,2687):
        row=rows[index];target=LABELS.index(row['target']);c=make_community(int(row['seed']),float(row['load']))
        h=run(c,target,row['policy']);fresh=metrics(h,target)
        error=max(abs(fresh[k]-float(row[k])) for k in fresh)
        expected=np.column_stack((h['done'].sum(1)/h['demand'],h['work'][:,target],
            np.delete(h['work'],target,axis=1).mean(1),h['request'][:,target]/h['demand'],
            h['planned_done'][:,target]/h['planned'][:,target]))
        check(f'Selected case {index} reproduces metrics and every timeline entry',error<1e-12 and np.allclose(expected,timeline[index],atol=1e-12,rtol=0))
    for load in (.8,3.6):
      for policy in protocol['policies']:
        h={k[len(f'{load}_{policy}_'):]:example[k] for k in example.files if k.startswith(f'{load}_{policy}_')}
        # Long policy prefixes can contain a shorter policy name; keep model keys only.
        expected_keys=set(run(make_community(61000,load),0,policy))
        h={k:v for k,v in h.items() if k in expected_keys}
        fresh=run(make_community(61000,load),0,policy)
        check(f'Full illustrative path {load}/{policy} reproduces and conserves resources',
              h.keys()==fresh.keys() and max(audit(h).values())<1e-12 and all(np.allclose(h[k],fresh[k],atol=1e-12,rtol=0) for k in h))
    ref=read(ROOT/'data/refinement.csv')
    check('18 arithmetic refinements unchanged',len(ref)==18 and max(float(r[k]) for r in ref for k in ('max_work_difference','max_output_difference'))==0)
    summaries=read(ROOT/'analysis/summary.csv');worst=0.
    for s in summaries:
      subset=[r for r in rows if r['split']==s['split'] and r['load']==s['load'] and r['policy']==s['policy']]
      # Balanced target rotations permit the same mean; intervals use seed means.
      worst=max(worst,abs(np.mean([float(r[s['metric']]) for r in subset])-float(s['mean'])))
    check('All summary means agree with raw cases',worst<1e-12)
    report=(ROOT/'report.html').read_text(encoding='utf-8')
    check('Report local links resolve',all(x=='verification.json' or re.match(r'https?://',x) or (ROOT/x).exists() for x in re.findall(r'(?:href|src)="([^"]+)"',report)))
    for p in ROOT.glob('*.py'):compile(p.read_text(encoding='utf-8'),p.name,'exec')
    check('All packaged Python source compiles',True)
    files=[p for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name not in ('manifest.json','verification.json')]
    check('No private machine paths in shareable text',all(not re.search(r'[A-Za-z]:[\\/]+Users[\\/]',p.read_text(encoding='utf-8')) for p in files if p.suffix in ('.json','.md','.py','.txt','.html','.csv')))
    current={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    if '--refresh-manifest' in sys.argv:(ROOT/'manifest.json').write_text(json.dumps(current,indent=2)+'\n',encoding='utf-8')
    check('Files match published manifest',current==json.loads((ROOT/'manifest.json').read_text()))
    result=dict(status='passed',checks=checks,check_count=len(checks),unit_tests_recorded=19,selected_case_reruns=12,full_example_reruns=16,
      note='Numerical and saved-result checks, not empirical validation of a social theory.')
    (ROOT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
if __name__=='__main__':main()
