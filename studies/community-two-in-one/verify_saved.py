from pathlib import Path
import json,hashlib,math
import analyze as a
R=Path(__file__).resolve().parent;s=json.loads((R/'results/summary.json').read_text());checks=0
def check(ok):
    global checks
    checks+=1
    if not ok:raise AssertionError(f'Check {checks} failed')
freeze=json.loads((R/'protocol_freeze.json').read_text())
check(hashlib.sha256((R/'PROTOCOL.md').read_bytes()).hexdigest()==freeze['protocol_sha256']==s['protocol_sha256'])
tr=a.read_csv(R/'data/inner_original.csv');te=a.read_csv(R/'data/inner_replication.csv');cr=a.read_csv(R/'data/memory_content.csv')
for rows in [tr,te]:
    for r in rows:
        check(set(r)=={'person','probe','elapsed_seconds','eligible','dialogic','strict_dialogic'})
        check((r['dialogic'] in ['0','1']) if int(r['eligible']) else r['dialogic']=='')
for outcome,key in [('dialogic','inner'),('strict_dialogic','strict_sensitivity')]:
    result,preds,scores=a.inner_analysis(tr,te,outcome)
    check(result==s[key])
    for p in preds:
        check(p['past_n']>=1 and all(0<=p[m]<=1 for m in ['population','last','history']))
    if outcome=='dialogic':
        saved=a.read_csv(R/'results/predictions.csv');check(len(saved)==len(preds))
        for p,q in zip(preds,saved):
            check(p['person']==q['person'] and all(math.isclose(float(p[k]),float(q[k]),abs_tol=1e-12) for k in p if k!='person'))
r,_=a.cram_analysis(cr);check(r==s['memory'])
check(len(cr)==s['audit']['cram']['included_rows'])
for r in cr:check(set(r)=={'person','probe','youth_bin','total_content'})
out=dict(passed=True,saved_checks=checks,protocol_sha256=s['protocol_sha256'])
(R/'results/verification.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))
