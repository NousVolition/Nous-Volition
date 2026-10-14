"""Verify delivered arrays, individual accounting, selected reruns and hashes."""
from pathlib import Path
import csv,json,hashlib,sys,re
import numpy as np
from model import make_community,solve,POLICIES
ROOT=Path(__file__).resolve().parent
checks=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(name,test):
    checks.append(dict(name=name,passed=bool(test)))
    if not test:raise AssertionError(name)
def read(p):
    with p.open(encoding='utf-8') as f:return list(csv.DictReader(f))
def packaged():
    return [p for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and
            (p.parent==ROOT or p.relative_to(ROOT).parts[0] in ('data','analysis')) and
            p.name not in ('manifest.json','verification.json') and p.suffix!='.pyc']
def run():
    protocol=json.loads((ROOT/'data/protocol.json').read_text())
    check('Frozen model, runner and test hashes match',all(sha(ROOT/n)==h for n,h in protocol['source_sha256'].items()))
    check('19 unit tests recorded as passed',bool(re.search(r'Ran 19 tests.*\bOK\b',(ROOT/'test_log.txt').read_text(),re.S)))
    rows=read(ROOT/'data/cases.csv');members=read(ROOT/'data/members.csv');extra=read(ROOT/'data/sensitivity.csv');ref=read(ROOT/'data/refinement.csv')
    check('Case and individual counts match protocol',len(rows)==768 and len(members)==5376 and len(extra)==576 and len(ref)==36)
    z=np.load(ROOT/'data/allocations.npz',allow_pickle=False)
    check('Allocation shapes and finite values',z['flow'].shape==(768,7,7,2) and z['effort'].shape==(768,7,2) and z['needs_met'].shape==(768,7) and all(np.all(np.isfinite(z[k])) for k in z.files))
    inputs=json.loads((ROOT/'data/inputs.json').read_text());lookup={(x['seed'],x['heterogeneity'],x['scarcity']):x for x in inputs}
    check('All 96 communities retained',len(lookup)==96)
    max_resource=max_needs=max_time=max_forbidden=max_metric=0.
    for index,row in enumerate(rows):
        config=lookup[(int(row['seed']),float(row['heterogeneity']),float(row['scarcity']))]
        skills=np.array(config['skills']);dem=np.array(config['demand']);requested=np.array(config['requested']);opts=POLICIES[row['policy']]
        flow=z['flow'][index];effort=z['effort'][index];met=z['needs_met'][index]
        max_resource=max(max_resource,float(np.max(flow.sum(1)-skills*effort)))
        max_needs=max(max_needs,float(np.max(dem*met[:,None]-flow.sum(0))))
        budget=(requested if opts.get('respect',True) else np.ones(7))-opts.get('assessment',0.)
        max_time=max(max_time,float(np.max(effort.sum(1)-np.maximum(budget,0))))
        graph=opts['graph'];adj=np.eye(7,dtype=bool) if graph=='self' else np.array(config[graph],bool)
        max_forbidden=max(max_forbidden,float(np.max(np.abs(flow[~adj]))))
        max_metric=max(max_metric,abs(met.mean()-float(row['mean_needs_met'])))
        per=members[index*7:(index+1)*7]
        max_metric=max(max_metric,float(np.max(abs(np.array([float(r['needs_met']) for r in per])-met))),float(np.max(abs(np.array([float(r['actual_work']) for r in per])-effort.sum(1)))))
    check('Saved production respects effort, every case',max_resource<1e-8)
    check('Credited bundles receive both services, every case',max_needs<1e-8)
    check('Policy time budgets obeyed, every case',max_time<1e-8)
    check('No transfers on forbidden edges, every case',max_forbidden<1e-12)
    check('Summary and per-member tables match arrays',max_metric<1e-12)
    check('Nonnegative flows/efforts and bounded fulfillment',min(z['flow'].min(),z['effort'].min(),z['needs_met'].min())>=-1e-9 and z['needs_met'].max()<=1+1e-9)
    check('Every solved primary optimum preserved',max(float(r['optimality_loss']) for r in rows+extra)<1e-7)
    lookupcase={(r['seed'],r['heterogeneity'],r['scarcity'],r['policy']):int(r['case_id']) for r in rows}
    check('Recording-only remains exactly inert across all 96 communities',all(np.array_equal(z['flow'][i],z['flow'][lookupcase[(seed,h,s,'recording_only')]]) for (seed,h,s,p),i in lookupcase.items() if p=='reciprocal'))
    check('Tighter tolerance changes fulfillment by less than 1e-7',max(float(r['maximum_member_difference']) for r in ref)<1e-7)
    for i in (0,5,8,23,255,383,384,389,391,500,650,767):
        r=rows[i];c=make_community(int(r['seed']),float(r['heterogeneity']),float(r['scarcity']));fresh=solve(c,**POLICIES[r['policy']])
        check('Selected case reproduces '+str(i),max(np.max(abs(fresh['flow']-z['flow'][i])),np.max(abs(fresh['met']-z['needs_met'][i])),np.max(abs(fresh['effort']-z['effort'][i])))<1e-10)
    text=(ROOT/'report.html').read_text(encoding='utf-8')
    targets=re.findall(r'(?:href|src)="([^"]+)"',text)
    check('Report local links and images resolve',all(x=='verification.json' or re.match(r'https?://',x) or (ROOT/x).exists() for x in targets))
    check('Shareable text has no private local paths',all(not re.search(r'[A-Za-z]:[\\/]+Users[\\/]',p.read_text(encoding='utf-8')) for p in packaged() if p.suffix in ('.py','.md','.json','.txt','.html','.csv')))
    current={p.relative_to(ROOT).as_posix():sha(p) for p in packaged()}
    if '--refresh-manifest' in sys.argv:(ROOT/'manifest.json').write_text(json.dumps(current,indent=2)+'\n',encoding='utf-8')
    check('Delivered files match manifest',json.loads((ROOT/'manifest.json').read_text())==current)
    return dict(status='passed',unit_tests_recorded=19,saved_result_checks=len(checks),selected_reproductions=12,
        max_supply_violation=max_resource,max_need_violation=max_needs,max_time_violation=max_time,
        note='Implementation and saved-result verification; not empirical validation of human behavior.',checks=checks)
if __name__=='__main__':
    try:result=run()
    except Exception as e:
        (ROOT/'verification.json').write_text(json.dumps(dict(status='failed',error=str(e),checks=checks),indent=2),encoding='utf-8');raise
    (ROOT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
