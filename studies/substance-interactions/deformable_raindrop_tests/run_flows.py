"""Reproduce the gas library and controls, one GPU calculation at a time."""
from pathlib import Path
import subprocess,sys,json,hashlib
P=Path(__file__).resolve().parent
jobs=[]
for re in [800,1600,2600]:
    for aspect in [.55,.75,1.0]:
        name=f're{re}_a{round(aspect*100):03d}_d20'
        if re==1600 and aspect==.75:name='pilot_re1600_a075_d20'
        jobs.append((name,dict(reynolds=re,aspect=aspect)))
for d in [28,36]:jobs.append((f're1600_a075_d{d}',dict(diameter=d)))
jobs.extend([
 ('re1600_a075_d20_halfway',dict(interpolated=0)),
 ('re1600_a075_d20_slow',dict(speed=.03)),
 ('re1600_a075_d20_wide',dict(width=7,length=16)),
 ('re1600_a075_d20_seed97',dict(seed=97)),
 ('re20_sphere_d20',dict(reynolds=20,aspect=1,cs=0,duration=30))])
(P/'run_design.json').write_text(json.dumps(jobs,indent=2))
(P/'source_freeze.json').write_text(json.dumps({f:hashlib.sha256((P/f).read_bytes()).hexdigest()
     for f in ['protocol.json','flow_lbm.py','shape_model.py','run_flows.py']},indent=2))
for name,kwargs in jobs:
    meta=P/'flow'/name/'metadata.json'
    if meta.exists():
        print('Already recorded:',name,flush=True);continue
    cmd=[sys.executable,str(P/'flow_lbm.py'),'--name',name]
    for key,value in kwargs.items():cmd += ['--'+key,str(value)]
    subprocess.run(cmd,check=True)
print('All planned gas cases recorded.',flush=True)
