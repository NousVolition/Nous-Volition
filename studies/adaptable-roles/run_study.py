"""Freeze the synthetic protocol, execute paired cases, retain accounting."""
from pathlib import Path
import argparse,csv,hashlib,json,time,sys,subprocess,platform
import numpy as np
from model import LABELS,POLICIES,make_community,run,metrics,audit
ROOT=Path(__file__).resolve().parent

def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main(out):
    out.mkdir(parents=True,exist_ok=True)
    if (out/'protocol.json').exists():raise FileExistsError('Use a new output directory')
    test=subprocess.run([sys.executable,str(ROOT/'test_model.py')],capture_output=True,text=True)
    (out/'test_log.txt').write_text(test.stdout+test.stderr,encoding='utf-8')
    if test.returncode:raise RuntimeError(test.stderr)
    protocol=dict(date='2026-10-15',rounds=60,switch=30,loads=[.8,3.6],
      discovery_seeds=list(range(51000,51012)),replication_seeds=list(range(61000,61012)),
      targets=list(LABELS),policies=list(POLICIES),bias=.75,memory=.25,learning=.1,gain=.6,handoff_cost=.05,
      source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('model.py','test_model.py','run_study.py')},
      note='Exploratory synthetic protocol saved after unit tests and before ensemble execution. '
           'All mechanisms and numerical parameters are assumptions. No human or chemical observations fitted. '
           'Replication seeds test numerical scenario variability, not external human validity.',
      sensitivity={'no_memory':{'memory':0},'no_learning':{'gain':0},'no_bias':{'bias':0},'costly_handoff':{'handoff_cost':.2}},
      sensitivity_policies=['assigned','remove_label','target_stops_handoff'])
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n',encoding='utf-8')
    tic=time.perf_counter();cases=[];members=[];traces={};inputs=[];maxima={};extra=[];refine=[]
    timeline=[]
    for split in ('discovery','replication'):
      for seed in protocol[split+'_seeds']:
        raw=make_community(seed)
        inputs.append(dict(seed=seed,skill=raw.skill.tolist(),willing=raw.willing.tolist(),planned=raw.planned.tolist(),unit_load_demand=raw.demand.tolist()))
        for load in protocol['loads']:
          c=make_community(seed,load)
          for target in range(7):
            for policy in POLICIES:
              h=run(c,target,policy);a=audit(h)
              for k,v in a.items():maxima[k]=max(maxima.get(k,0.),v)
              if max(a.values())>1e-8:raise AssertionError(a)
              row=dict(case_id=len(cases),split=split,seed=seed,load=load,target=LABELS[target],policy=policy)
              row.update(metrics(h,target));cases.append(row)
              for j,label in enumerate(LABELS):
                members.append(dict(case_id=row['case_id'],member=label,initial_skill=c.skill[j],
                  willing_time=c.willing[j],post_work=h['work'][30:,j].mean(),
                  post_plans_met=h['planned_done'][30:,j].sum()/c.planned[30:,j].sum(),
                  post_output=h['done'][30:,j].sum(),final_skill=h['final_skill'][j]))
              timeline.append(np.column_stack((h['done'].sum(1)/h['demand'],h['work'][:,target],
                  np.delete(h['work'],target,axis=1).mean(1),h['request'][:,target]/h['demand'],
                  h['planned_done'][:,target]/h['planned'][:,target])))
              if seed==61000 and target==0:
                for k,v in h.items():traces[f'{load}_{policy}_{k}']=v
        print(split,seed,'complete',flush=True)
    for seed in protocol['replication_seeds']:
      c=make_community(seed,3.6)
      for target in range(7):
       for label,options in protocol['sensitivity'].items():
        for policy in protocol['sensitivity_policies']:
          h=run(c,target,policy,**options);a=audit(h)
          if max(a.values())>1e-8:raise AssertionError(a)
          for k,v in a.items():maxima[k]=max(maxima.get(k,0.),v)
          extra.append(dict(seed=seed,target=LABELS[target],variant=label,policy=policy,**metrics(h,target)))
    for seed in protocol['replication_seeds'][:6]:
      for policy in ('shared','target_stops_handoff','share_after'):
        c=make_community(seed,3.6);a=run(c,0,policy);b=run(c,0,policy,tolerance=1e-13)
        refine.append(dict(seed=seed,policy=policy,max_work_difference=float(abs(a['work']-b['work']).max()),
                          max_output_difference=float(abs(a['done']-b['done']).max())))
    write_csv(out/'cases.csv',cases);write_csv(out/'members.csv',members)
    write_csv(out/'sensitivity.csv',extra);write_csv(out/'refinement.csv',refine)
    np.savez_compressed(out/'timelines.npz',values=np.array(timeline))
    np.savez_compressed(out/'example_traces.npz',**traces)
    (out/'inputs.json').write_text(json.dumps(inputs,separators=(',',':')),encoding='utf-8')
    execution=dict(main_cases=len(cases),member_rows=len(members),sensitivity_cases=len(extra),
       refinement_pairs=len(refine),rounds_per_case=60,unit_tests=19,
       accounting_maxima=maxima,elapsed_seconds=time.perf_counter()-tic,
       python=platform.python_version(),numpy=np.__version__,
       timeline_columns=['coordination_met','target_work','others_work','target_request_share','target_plans_met'])
    (out/'execution.json').write_text(json.dumps(execution,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(execution,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'data')
    main(parser.parse_args().out)
