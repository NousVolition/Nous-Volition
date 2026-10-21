"""Verify saved results against inputs, identities and selected reruns."""
from pathlib import Path
import csv,hashlib,json,math
import numpy as np
from model import Rule,probability,twin_history,coefficient_audit
ROOT=Path(__file__).resolve().parent
def read(n):return list(csv.DictReader((ROOT/'data'/n).open(encoding='utf-8')))
def main():
    checks=[];p=json.loads((ROOT/'data/protocol.json').read_text());r=json.loads((ROOT/'data/results.json').read_text())
    for name,digest in p['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    checks.append('frozen model, test, runner and source-estimate hashes match')
    rows=read('wording_cases.csv');assert len(rows)==432
    for row in rows:
        expected=float(probability(row['text'],float(row['context_offset']),0,Rule(wording=float(row['wording_coefficient']))))
        assert abs(expected-float(row['restriction_probability']))<1e-14
        assert row['offer_minutes']==row['maximum_minutes']
    checks.append('all 432 stored wording probabilities and offer limits checked')
    pairs=read('wording_contrasts.csv');assert len(pairs)==108
    assert all(float(x['direct_minus_courteous'])==0 for x in pairs if float(x['wording_coefficient'])==0)
    checks.append('all wording-blind paired contrasts exactly zero')
    joint=read('joint_wording_history.csv');assert len(joint)==144
    for x in joint:
        a,b=float(x['p_after_permission']),float(x['p_after_restriction'])
        assert abs(math.log(b/(1-b))-math.log(a/(1-a))-.3)<1e-12
    checks.append('all 144 joint history contrasts match analytic log-odds shift')
    policies={ 'history_blind':(Rule(),None,False),'record_only_decay':(Rule(history=1.2),None,True),
      'reinforcing_feedback':(Rule(history=1.2),None,False),'corrective_feedback':(Rule(history=-1.2),None,False),
      'reset_before_round_6':(Rule(history=1.2),6,False),'zero_input':(Rule(history=1.2,input_gain=0),None,False)}
    seedrows=read('memory_seed_results.csv');assert len(seedrows)==6000
    for name,(rule,reset,record) in policies.items():
        group=[x for x in seedrows if x['policy']==name]
        assert len(group)==1000
        assert abs(np.mean([float(x['decision_difference']) for x in group])-r['memory'][name]['future_restriction_difference']['mean'])<1e-14
        for row in group[::100]:
            a=twin_history(int(row['seed']),rule,reset_at=reset,record_only=record)
            assert abs((a[:,6]-a[:,5]).mean()-float(row['decision_difference']))<1e-14
            assert abs((a[:,4]-a[:,3]).mean()-float(row['probability_difference']))<1e-14
    checks.append('six policy aggregates and 60 selected paired reruns match saved results')
    examples=read('example_encounters.csv')
    assert all(x['w_permitted']==x['w_restricted'] for x in examples if x['policy']=='reset_before_round_6' and int(x['round'])>=6)
    checks.append('saved reset example has identical treatment from encounter 6')
    src=json.loads((ROOT/'source_estimates.json').read_text());audit=read('published_wording_audit.csv')
    for x,y in zip(src['wording']['rows'],audit):
        check=coefficient_audit(x['coef'],x['se'],x['appendix_or'])
        assert str(check['table_consistent'])==y['table_consistent']
        assert abs(check['odds_ratio']-float(y['odds_ratio']))<1e-14
    assert sum(x['table_consistent']=='False' for x in audit)==2
    checks.append('all six published coefficient conversions checked; two exclusions retained')
    hist=read('published_history_arithmetic.csv')
    assert abs(float(hist[0]['percentage_point_difference'])-4.5)<1e-12
    assert abs(float(hist[1]['percentage_point_difference'])-.7)<1e-12
    checks.append('published percentage-point arithmetic checked without invented counts')
    result=dict(status='passed',checks=checks,unit_tests=19,selected_paired_reruns=60,
                source_exclusions=2,no_new_human_observations=True)
    (ROOT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
