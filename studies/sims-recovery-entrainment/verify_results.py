"""Audit saved follow-up results, rerun selected cases, and check refinement."""
import hashlib,json,unittest
from pathlib import Path
import numpy as np
import test_experiments
from run_experiments import recovery_worker
from oscillators import network_block


def main():
    data=Path('data');p=json.loads((data/'protocol.json').read_text())
    tasks=json.loads((data/'tasks.json').read_text());a=np.load(data/'recovery.npz');x=a['blocks']
    check={}
    check['frozen_sources']=all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in p['source_hashes'].items())
    check['expected_shape']=x.shape==(p['recovery_runs'],48,8)
    check['finite_and_bounded']=bool(np.isfinite(x).all() and np.all((x[:,:,[0,1,3,4,5,6,7]]>=-1e-12)&(x[:,:,[0,1,3,4,5,6,7]]<=1+1e-12)))
    lookup={(t['config']['seed'],t['config']['topology'],t['config']['balance'],t['config']['memory'],t['schedule']):i for i,t in enumerate(tasks)}
    no_anticipation=[]
    for key,i in lookup.items():
        if key[-1]=='never':
            no_anticipation.append(np.array_equal(x[i,:20],x[lookup[(*key[:-1],'late')],:20]))
            no_anticipation.append(np.array_equal(x[i,:4],x[lookup[(*key[:-1],'early')],:4]))
        if key[-1]=='early':no_anticipation.append(np.array_equal(x[i,:20],x[lookup[(*key[:-1],'repeated')],:20]))
    check['no_anticipation_all_matched_cases']=bool(all(no_anticipation))
    reruns=[]
    for i in np.linspace(0,len(tasks)-1,12,dtype=int):
        values,digest,groups=recovery_worker(tasks[i])
        reruns.append(dict(id=int(i),exact=bool(np.array_equal(values,x[i]) and digest==a['digests'][i] and np.array_equal(groups,a['final_groups'][i]))))
    check['selected_exact_reruns']=all(r['exact'] for r in reruns)
    network=json.loads((data/'network.json').read_text());refinements=[]
    seed=next(s for s in p['seeds'] if s>=20000)
    for topology in ('ring','random','hub'):
        fine=network_block(seed,topology,dt=.02)
        for row in fine:
            old=next(r for r in network if all(r[k]==row[k] for k in ('seed','topology','mapping','driver')))
            refinements.append(dict(seed=seed,topology=topology,mapping=row['mapping'],driver=row['driver'],
                coherence_difference=abs(row['coherence']-old['coherence']),
                mean_drift_difference=abs(row['mean_drift']-old['mean_drift']),
                lock_fraction_difference=abs(row['locked_fraction']-old['locked_fraction'])))
    check['network_step_refinement']=all(r['coherence_difference']<.01 and r['mean_drift_difference']<.005 and r['lock_fraction_difference']==0 for r in refinements)
    result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(test_experiments))
    check['unit_tests']=result.wasSuccessful()
    coarse=json.loads((data/'junction.json').read_text());fine=json.loads((data/'junction_refined.json').read_text())
    junction=[]
    for beta in (.2,2,10):
        diffs=[abs(r['voltage_ratio']-s['voltage_ratio']) for r,s in zip(coarse,fine) if r['beta']==beta]
        row=dict(beta=beta,max_voltage_refinement_difference=max(diffs))
        for direction in ('up','down'):
            for prefix,records in [('coarse',coarse),('refined',fine)]:
                running=[r['bias'] for r in records if r['beta']==beta and r['direction']==direction and r['voltage_ratio']>.02]
                row[prefix+'_'+direction+'_lowest_running_grid_bias']=min(running) if running else None
        junction.append(row)
    record=dict(all_passed=all(check.values()),checks=check,unit_tests=result.testsRun,exact_reruns=reruns,
        network_refinement=refinements,junction_refinement=junction,
        scope='Finite-horizon implementation and numerical checks. The .02 junction threshold is a reporting convention, not an exact bifurcation value.')
    Path('verification.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
    if not record['all_passed']:raise SystemExit(1)


if __name__=='__main__':main()
