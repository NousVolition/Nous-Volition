"""Run the fixed exploratory comparison. Refuses to replace delivered results."""
from pathlib import Path
from dataclasses import asdict
import csv,json,hashlib,platform,time,argparse
import numpy as np
import scipy
from scipy.stats import t as student_t
from model import make_community,solve,POLICIES,LABELS
ROOT=Path(__file__).resolve().parent
SEEDS={'discovery':list(range(31000,31012)),'replication':list(range(41000,41012))}
METRICS=('mean_needs_met','minimum_needs_met','leader_needs_met','others_needs_met',
         'total_useful_work','total_excess_over_requests','fraction_members_over_request','needs_spread')
def writecsv(path,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)
def interval(x):
    x=np.array(x,float);h=student_t.ppf(.975,len(x)-1)*np.std(x,ddof=1)/np.sqrt(len(x))
    return dict(mean=float(x.mean()),low=float(x.mean()-h),high=float(x.mean()+h),seeds=len(x))
def run(out):
    if (out/'protocol.json').exists():raise FileExistsError('Use a new --out directory; delivered results are preserved.')
    out.mkdir(parents=True,exist_ok=True);start=time.perf_counter()
    protocol=dict(title='Community allocation, boundaries and unequal decision priority',
      source='User-supplied Foucault passage; operational definitions are new modeling assumptions.',
      seeds=SEEDS,members=7,services=2,heterogeneity=[0.,.55],scarcity=[1.,1.4],policies=POLICIES,
      units=dict(time='one available-time unit per fictional member',service='synthetic service units per time unit',
                 met='fraction of a two-service needs bundle, 0 to 1'),
      main_cases=768,additional_cases=576,solver_calls_per_case=2,
      interpretation='Ideal allocation oracle with perfect information; not a simulation of negotiations, learning or actual family behavior.',
      source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('model.py','run_study.py','test_model.py')},
      exploratory=True,externally_preregistered=False,
      caution='Feasible-set monotonicities and imposed priorities are assumptions/consequences, not discovered social laws. Seed intervals do not include model uncertainty.')
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    runs=[];people=[];flows=[];efforts=[];needs=[];inputs=[];configs=[]
    for split,seeds in SEEDS.items():
        for seed in seeds:
            for heterogeneity in (0.,.55):
                for scarcity in (1.,1.4):
                    c=make_community(seed,heterogeneity,scarcity)
                    inputs.append(dict(split=split,seed=seed,heterogeneity=heterogeneity,scarcity=scarcity,
                        **{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in asdict(c).items()}))
                    for policy,options in POLICIES.items():
                        config=dict(case_id=len(runs),split=split,seed=seed,heterogeneity=heterogeneity,scarcity=scarcity,policy=policy,leader=0)
                        z=solve(c,**options);runs.append(dict(**config,**z['metrics']));configs.append(config)
                        flows.append(z['flow']);efforts.append(z['effort']);needs.append(z['met'])
                        for i in range(7):
                            people.append(dict(**config,member=i,label=LABELS[i],skill0=c.skills[i,0],skill1=c.skills[i,1],
                              demand0=c.demand[i,0],demand1=c.demand[i,1],capacity=c.capacity[i],requested=c.requested[i],
                              actual_work=z['effort'][i].sum(),assessment_time=z['assessment_time'][i],
                              needs_met=z['met'][i],excess_over_request=z['excess'][i]))
    writecsv(out/'cases.csv',runs);writecsv(out/'members.csv',people)
    (out/'inputs.json').write_text(json.dumps(inputs),encoding='utf-8')
    (out/'case_order.json').write_text(json.dumps(configs,indent=2),encoding='utf-8')
    np.savez_compressed(out/'allocations.npz',flow=flows,effort=efforts,needs_met=needs)
    summaries=[];contrasts=[]
    for split,seeds in SEEDS.items():
        for heterogeneity in (0.,.55):
            for scarcity in (1.,1.4):
                for policy in POLICIES:
                    sub=[r for r in runs if r['split']==split and r['heterogeneity']==heterogeneity and r['scarcity']==scarcity and r['policy']==policy]
                    base=[r for r in runs if r['split']==split and r['heterogeneity']==heterogeneity and r['scarcity']==scarcity and r['policy']=='reciprocal']
                    for metric in METRICS:
                        key=dict(split=split,heterogeneity=heterogeneity,scarcity=scarcity,policy=policy,metric=metric)
                        summaries.append(dict(**key,**interval([r[metric] for r in sub])))
                        diff=[r[metric]-next(b[metric] for b in base if b['seed']==r['seed']) for r in sub]
                        contrasts.append(dict(**key,reference='reciprocal',**interval(diff)))
    writecsv(out/'summary.csv',summaries);writecsv(out/'paired_contrasts.csv',contrasts)
    extra=[]
    for split,seeds in SEEDS.items():
        for seed in seeds:
            c=make_community(seed,.55,1.4)
            for leader in range(7):
                for respect in (True,False):
                    z=solve(c,priority=3.,leader=leader,respect=respect)
                    extra.append(dict(split=split,seed=seed,kind='leader_rotation',parameter=leader,respect=respect,**z['metrics']))
            for cost in (0.,.05,.1,.15,.2):
                extra.append(dict(split=split,seed=seed,kind='assessment_cost',parameter=cost,respect=True,**solve(c,assessment=cost)['metrics']))
            for priority in (1.,1.5,2.,3.,5.):
                extra.append(dict(split=split,seed=seed,kind='priority_strength',parameter=priority,respect=True,**solve(c,priority=priority)['metrics']))
    writecsv(out/'sensitivity.csv',extra)
    refinement=[]
    for seed in SEEDS['replication']:
        c=make_community(seed,.55,1.4)
        for name in ('reciprocal','priority_hierarchy','override_budgets'):
            a=solve(c,**POLICIES[name]);b=solve(c,**POLICIES[name],tolerance=1e-10)
            refinement.append(dict(seed=seed,policy=name,mean_needs_difference=b['metrics']['mean_needs_met']-a['metrics']['mean_needs_met'],
                maximum_member_difference=float(np.max(abs(a['met']-b['met']))),base_residual=a['metrics']['constraint_residual'],fine_residual=b['metrics']['constraint_residual']))
    writecsv(out/'refinement.csv',refinement)
    execution=dict(main_cases=len(runs),member_rows=len(people),additional_cases=len(extra),
                   refinement_pairs=len(refinement),extra_refinement_solves=2*len(refinement),
                   seconds=time.perf_counter()-start,python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,
                   max_constraint_residual=max(r['constraint_residual'] for r in runs+extra),
                   max_refinement_mean_difference=max(abs(r['mean_needs_difference']) for r in refinement),
                   max_refinement_member_difference=max(r['maximum_member_difference'] for r in refinement))
    (out/'execution.json').write_text(json.dumps(execution,indent=2),encoding='utf-8')
    print(json.dumps(execution,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'data');args=parser.parse_args();run(args.out)
