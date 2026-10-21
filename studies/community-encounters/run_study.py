"""Run paired synthetic audits and arithmetic checks of published summaries."""
from pathlib import Path
from dataclasses import asdict,replace
import argparse,csv,hashlib,json,platform,subprocess,sys,time
import numpy as np
from model import *
ROOT=Path(__file__).resolve().parent

def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def stats(x):
    x=np.asarray(x,float);m=float(x.mean());se=float(x.std(ddof=1)/np.sqrt(len(x)))
    return dict(mean=m,lower=m-1.96*se,upper=m+1.96*se,n=len(x))

def main(out):
    if out.exists():raise FileExistsError('Use a new output directory to preserve results')
    out.mkdir(parents=True)
    protocol=dict(date='2026-10-21',scope='Synthetic audit plus published aggregate arithmetic; no human validation',
      base_rule=asdict(Rule()),wording_coefficients=[0,.8,-.8],contexts=[-.8,0,.8],
      minutes=[10,20,30],meaning_groups=12,variants=['direct','courteous','formal','forceful'],
      memory_seeds=list(range(71000,72000)),rounds=30,history_coefficient=1.2,
      sensitivities=dict(retention=[.5,.8,.95],history=[-1.2,0,1.2,2.4]),
      note='All synthetic parameters are chosen, not estimated. Freeze precedes calculations, but is not a public preregistration. Published results were seen during design, so they are not holdouts. New seeds assess computational variation only.',
      source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('model.py','test_model.py','run_study.py','source_estimates.json')})
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    test=subprocess.run([sys.executable,str(ROOT/'test_model.py')],capture_output=True,text=True)
    (out/'test_log.txt').write_text(test.stdout+test.stderr,encoding='utf-8')
    if test.returncode:raise RuntimeError(test.stderr)
    start=time.perf_counter();wording=[];pairs=[]
    for i,task in enumerate(TASKS):
      minute=protocol['minutes'][i%3]
      for beta in protocol['wording_coefficients']:
       for ctx in protocol['contexts']:
        values={}
        for form,text in variants(task,minute).items():
          p=float(probability(text,ctx,0,Rule(wording=beta)));values[form]=p
          wording.append(dict(meaning_id=i,task=task,offer_minutes=minute,maximum_minutes=minute,variant=form,text=text,
             wording_coefficient=beta,context_offset=ctx,lexical_marker=lexical_marker(text),restriction_probability=p,
             evidence='synthetic authored meaning slots; no independent equivalence judgment'))
        pairs.append(dict(meaning_id=i,wording_coefficient=beta,context_offset=ctx,
                          direct_minus_courteous=values['direct']-values['courteous'],
                          formal_minus_courteous=values['formal']-values['courteous']))
    write_csv(out/'wording_cases.csv',wording);write_csv(out/'wording_contrasts.csv',pairs)
    joint=[]
    for i,task in enumerate(TASKS):
      for ctx in protocol['contexts']:
       for form,text in variants(task,protocol['minutes'][i%3]).items():
        rule=Rule(wording=.8,history=1.2)
        p0=float(probability(text,ctx,0,rule));p1=float(probability(text,ctx,.25,rule))
        joint.append(dict(meaning_id=i,context_offset=ctx,variant=form,p_after_permission=p0,p_after_restriction=p1,history_difference=p1-p0))
    write_csv(out/'joint_wording_history.csv',joint)
    policies={
      'history_blind':(Rule(history=0),None,False),
      'record_only_decay':(Rule(history=1.2),None,True),
      'reinforcing_feedback':(Rule(history=1.2),None,False),
      'corrective_feedback':(Rule(history=-1.2),None,False),
      'reset_before_round_6':(Rule(history=1.2),6,False),
      'zero_input':(Rule(history=1.2,input_gain=0),None,False)}
    summaries={};per_seed=[];timeline=[];examples=[]
    for name,(rule,reset,record) in policies.items():
      runs=np.stack([twin_history(seed,rule,reset_at=reset,record_only=record) for seed in protocol['memory_seeds']])
      # Excludes the forced treatment at t=0; each row is one later encounter.
      deltas=runs[:,:,6]-runs[:,:,5];pd=runs[:,:,4]-runs[:,:,3]
      summaries[name]=dict(future_restriction_difference=stats(deltas.mean(1)),
                          probability_difference=stats(pd.mean(1)),first_probability_difference=stats(pd[:,0]),
                          last_probability_difference=stats(pd[:,-1]))
      for idx,seed in enumerate(protocol['memory_seeds']):
        per_seed.append(dict(policy=name,seed=seed,decision_difference=deltas[idx].mean(),probability_difference=pd[idx].mean()))
        if idx==0:
          for row in runs[idx]:
            examples.append(dict(policy=name,seed=seed,round=int(row[0]),state_permitted=row[1],state_restricted=row[2],
              p_permitted=row[3],p_restricted=row[4],w_permitted=int(row[5]),w_restricted=int(row[6])))
      for t in range(protocol['rounds']):
        timeline.append(dict(policy=name,round=t+1,**stats(pd[:,t])))
      if name in ('history_blind','zero_input'):assert np.array_equal(deltas,np.zeros_like(deltas))
      if name=='reset_before_round_6':assert not pd[:,5:].any()
      if name=='record_only_decay':np.testing.assert_allclose(runs[:,:,2]-runs[:,:,1],np.broadcast_to(.25*.8**np.arange(30),(1000,30)),atol=1e-14)
    write_csv(out/'memory_seed_results.csv',per_seed);write_csv(out/'memory_timeline.csv',timeline)
    write_csv(out/'example_encounters.csv',examples)
    sensitivity=[]
    for rho in protocol['sensitivities']['retention']:
      for gamma in protocol['sensitivities']['history']:
        vals=[]
        for seed in protocol['memory_seeds'][:200]:
          a=twin_history(seed,Rule(retention=rho,history=gamma))
          vals.append((a[:,6]-a[:,5]).mean())
        sensitivity.append(dict(retention=rho,history_coefficient=gamma,**stats(vals)))
    write_csv(out/'sensitivity.csv',sensitivity)
    src=json.loads((ROOT/'source_estimates.json').read_text());audit=[];history=[]
    for row in src['wording']['rows']:audit.append(dict(**row,**coefficient_audit(row['coef'],row['se'],row['appendix_or'])))
    for row in src['history']['rows']:
      history.append(dict(**row,percentage_point_difference=100*(row['treated']-row['control']),risk_ratio=row['treated']/row['control']))
    write_csv(out/'published_wording_audit.csv',audit);write_csv(out/'published_history_arithmetic.csv',history)
    result=dict(wording={str(beta):dict(mean=float(np.mean([r['direct_minus_courteous'] for r in pairs if r['wording_coefficient']==beta])),
        minimum=float(min(r['direct_minus_courteous'] for r in pairs if r['wording_coefficient']==beta)),
        maximum=float(max(r['direct_minus_courteous'] for r in pairs if r['wording_coefficient']==beta)),
        interpretation='Exact descriptive contrast over repeated authored cases; no sampling interval') for beta in protocol['wording_coefficients']},
      memory=summaries,source_audit=dict(consistent=sum(r['table_consistent'] for r in audit),excluded=sum(not r['table_consistent'] for r in audit),
      retained_intervals_include_one=all(r['lower']<=1<=r['upper'] for r in audit if r['table_consistent'])),
      counts=dict(wording_cases=len(wording),paired_wording_contrasts=len(pairs),joint_probability_pairs=len(joint),paired_memory_paths=6000,sensitivity_pairs=2400,
                  later_encounters_main=6000*2*30,unit_tests=19),
      seconds=time.perf_counter()-start,python=sys.version,numpy=np.__version__,platform=platform.platform())
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'data');main(p.parse_args().out)
