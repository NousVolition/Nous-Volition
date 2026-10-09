"""Audit recorded results and rerun matched trajectories without plotting tools."""
import hashlib,json,unittest,time
from dataclasses import asdict
from pathlib import Path
import numpy as np
from model import Config,run
import test_model


def main():
    from restore_data import restore
    data=Path('data');restore(data);a=np.load(data/'arrays.npz')
    arrays={k:a[k] for k in a.files}
    tasks=json.loads((data/'tasks.json').read_text());schema=json.loads((data/'schema.json').read_text())
    p=json.loads((data/'protocol.json').read_text());checks={}
    checks['frozen_source_hashes']=all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in p['source_hashes'].items())
    checks['complete_run_count']=all(len(arrays[k])==len(tasks)==p['task_count'] for k in arrays)
    ti={k:i for i,k in enumerate(schema['trace'])};pi={k:i for i,k in enumerate(schema['pairs'])};gi={k:i for i,k in enumerate(schema['groups'])}
    used=arrays['trace'][:,:,ti['pool_used']]
    checks['allocation_budget']=bool(np.all((used>=0)&(used<=1+1e-12)))
    checks['bounded_rigidity']=bool(np.all((arrays['trace'][:,:,ti['rigid']]>=0)&(arrays['trace'][:,:,ti['rigid']]<=1)))
    checks['all_influence_shares_sum_to_one']=bool(np.allclose(arrays['groups'][:,:,gi['influence_share']].reshape(-1,3,6).sum(2),1))
    max_error=0;max_opp=0
    for i,t in enumerate(tasks):
        n=t['config']['n'];length=t['config']['rounds']//3
        successes=arrays['trace'][i,:,ti['cooperation']].reshape(3,length).sum(1)*n
        pair_success=arrays['pairs'][i,:,pi['cooperation']].reshape(3,36).sum(1)
        opp=arrays['pairs'][i,:,pi['opportunities']].reshape(3,36).sum(1)
        max_error=max(max_error,float(abs(successes-pair_success).max()))
        max_opp=max(max_opp,float(abs(opp-length*n).max()))
    checks['independent_group_accounting']=max_error<1e-8 and max_opp<1e-8
    # Preselected evenly spaced trajectories exercise suites/topologies/populations.
    reruns=[]
    for i in np.linspace(0,len(tasks)-1,18,dtype=int):
        r=run(Config(**tasks[i]['config']))
        rr=np.array([[x[k] for k in schema['phases']] for x in r['phases']])
        reruns.append(dict(id=tasks[i]['id'],exact_digest=r['digest']==arrays['digests'][i],numeric_equal=bool(np.allclose(rr,arrays['phases'][i],equal_nan=True,atol=1e-12,rtol=0))))
    checks['independent_reruns']=all(x['exact_digest'] and x['numeric_equal'] for x in reruns)
    suite=unittest.defaultTestLoader.loadTestsFromModule(test_model)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    checks['unit_tests']=result.wasSuccessful()
    record=dict(all_passed=all(checks.values()),checks=checks,unit_tests_run=result.testsRun,
        reruns=reruns,max_group_success_accounting_error=max_error,max_opportunity_accounting_error=max_opp,
        scope='Implementation and saved-result consistency; not validation against humans.')
    Path('verification.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
    if not record['all_passed']:raise SystemExit(1)


if __name__=='__main__':main()
