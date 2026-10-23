from pathlib import Path
import csv,json,hashlib
import numpy as np
from corpus_field import Field,Parameters
from run_exact_tests import compare
ROOT=Path(__file__).resolve().parent

def main():
    r=json.loads((ROOT/'results/equation_results.json').read_text());d=json.loads((ROOT/'results/data_audit.json').read_text());z=np.load(ROOT/'results/states.npz');checks=[]
    def check(label,ok):
        checks.append(dict(check=label,passed=bool(ok)))
        if not ok:raise AssertionError(label)
    for name,key in [('corpus_field.py','solver_sha256'),('PROTOCOL.md','protocol_sha256'),('NUMERICAL_PLAN.md','numerical_plan_sha256')]:
        check(name+' preserved',hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==r[key])
    check('36 complete coupled synthetic runs',r['coupled_runs']==36 and r['synthetic_inputs'] and not r['empirical_model_fit'])
    check('Taylor Green analytic solution',r['analytic_taylor_green_max_error']<1e-10)
    activity=[]
    for x in r['runs']:
        law=x['law'];f=Field(Parameters(**x['parameters']));a=z[law+'_history'];b=z[law+'_reversed']
        check(law+' history retained',compare(a,b)['S_rms']>.03)
        check(law+' exact history mass',abs(f.real(a[2]).mean()-.012)<1e-12 and abs(f.real(b[2]).mean()+.012)<1e-12)
        check(law+' same final accumulator',max(abs(t) for t in x['history_A'])<1e-12)
        check(law+' missing role dynamics identified',x['role_relabel_difference']['state_rms']==0)
        scaled=z[law+'_rescaled'].copy();scaled[2]/=2
        check(law+' full state scaling',compare(a,scaled)['state_rms']<1e-12)
        for suffix in ['plus1pct','minus1pct','prior_plus','prior_minus','grid48','grid72','halfdt','history','reversed','rescaled']:
            check(law+' '+suffix+' finite',np.isfinite(z[law+'_'+suffix]).all())
        for key,left,right in [('grid24_48','history','grid48'),('grid48_72','grid48','grid72'),('time_refinement','history','halfdt'),('perturbation_comparison','plus1pct','minus1pct'),('unknown_prior_comparison','prior_plus','prior_minus')]:
            actual=compare(z[law+'_'+left],z[law+'_'+right])
            check(law+' archived '+key,all(abs(actual[k]-x[key][k])<1e-13 for k in actual))
        check(law+' grid refinement',x['grid48_72']['state_rms']<x['grid24_48']['state_rms'])
        check(law+' small time error',x['time_refinement']['state_rms']<1e-9)
        check(law+' mass conservation accounting',x['max_mass_error']<1e-12)
        check(law+' incompressibility',x['max_divergence']<1e-12)
        check(law+' energy identity',x['max_energy_identity']<1e-12)
        for suffix in ['plus1pct','minus1pct']:
            gs=f.gradient(z[law+'_'+suffix][2]);q=np.sqrt(np.sum(gs*gs,axis=0))-f.p.threshold
            activity.append(dict(law=law,condition=suffix,above_threshold_fraction=float(np.mean(q>0))))
    rows=list(csv.DictReader((ROOT/'results/run_coverage.csv').open()))
    check('24 real participants',len({x['person'] for x in rows})==d['participants']==24)
    check('47 separate sessions',len({(x['person'],x['session']) for x in rows})==d['sessions']==47)
    check('140 runs',len(rows)==d['runs']==140)
    check('840 real probes',sum(int(x['probes']) for x in rows)==d['probes']==840)
    check('10920 item rows',sum(int(x['item_rows']) for x in rows)==d['item_rows']==10920)
    check('all question groups complete',not d['issues'])
    check('reserved responses not analyzed',d['reserved_response_values_used'] is False)
    check('no invented full fit',d['full_model_fit_performed'] is False)
    check('missing ratings reported',sum(x['count'] for x in d['development_nonnumeric_or_nonfinite'])==19)
    out=dict(passed=True,count=len(checks),checks=checks,threshold_activity=activity)
    (ROOT/'results/verification.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(passed=True,checks=len(checks))))
if __name__=='__main__':main()
