from pathlib import Path
import csv,json,hashlib
import numpy as np
P=Path(__file__).resolve().parent
read=lambda name:list(csv.DictReader((P/'results'/name).open()))
checks=[]
def check(name,ok):
    checks.append(dict(name=name,passed=bool(ok)))
    if not ok:raise AssertionError(name)
protocol=json.loads((P/'frozen_protocol.json').read_text())
check('frozen model byte identity',hashlib.sha256((P/'raindrop_model.py').read_bytes()).hexdigest()==protocol['model_sha256'])
r=read('holdout_predictions.csv');check('all four published prose means',len(r)==4)
observed=[.311,.184,.635,.779]
for i,z in enumerate(r):
    check(z['id']+' source mean',float(z['observed_E'])==observed[i])
    check(z['id']+' positive finite prediction',np.isfinite(float(z['predicted_E'])) and float(z['predicted_E'])>0)
    check(z['id']+' area conversion',abs(float(z['area_conversion'])-(float(z['drop_equiv_mm'])/float(z['long_axis_mm']))**2)<1e-14)
    check(z['id']+' ratio',abs(float(z['ratio'])-float(z['predicted_E'])/observed[i])<1e-14)
    check(z['id']+' heat balance',abs(float(z['heat_residual_W_m2']))<1e-6)
    check(z['id']+' outside rear domain flagged',float(z['Re_D'])>800 and z['rear_in_domain']=='False' and float(z['rear_projected'])==0)
    total=sum(float(v) for k,v in z.items() if k.endswith('_projected'))
    check(z['id']+' component accounting',abs(total-float(z['predicted_E']))<1e-12)
s=json.loads((P/'results/summary.json').read_text())
rat=np.array([float(z['ratio']) for z in r])
check('geometric score reproduced',abs(np.exp(np.log(rat).mean())-s['geometric_bias'])<1e-14)
check('median factor reproduced',abs(np.median(np.maximum(rat,1/rat))-s['median_absolute_factor'])<1e-12)
q=read('distribution_refinement.csv');errors=[]
for id in ['H1','H2','H3','H4']:
    for g in ['1.3','1.5']:
        a,b=[float(z['predicted_E']) for z in q if z['id']==id and z['gsd']==g]
        errors.append(abs(a-b)/b)
        check(id+' distribution refinement '+g,errors[-1]<1e-4)
b=read('distribution_bounds.csv')
for id in ['H1','H2','H3','H4']:
    a,c=[z for z in b if z['id']==id]
    check(id+' upper bound refinement',abs(float(a['maximum_E'])-float(c['maximum_E']))<1e-7)
    check(id+' nominal support cannot reach observed',float(c['maximum_E'])<float(c['observed_E']))
inv=read('inventory.csv')
check('closed particle inventory',max(abs(float(x['total'])-1e8) for x in inv)<1e-7)
check('four complete control/sensitivity sets',len(read('sensitivities.csv'))==72)
check('five independent source speed rows',len(read('speed_transfer.csv'))==5)
check('all eight development rows at all widths',len(read('development_predictions.csv'))==24)
report=dict(status='passed',checks=len(checks),max_distribution_refinement_relative=max(errors),items=checks)
(P/'verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='items'},indent=2))
