"""Complete a second gas table, keeping the physical model unchanged."""
from pathlib import Path
import json,subprocess,sys
P=Path(__file__).resolve().parent
jobs=[]
for re in [800,1600,2600]:
    for aspect in [.55,.75,1.]:
        jobs.append((f're{re}_a{round(100*aspect):03d}_d28',dict(diameter=28,reynolds=re,aspect=aspect)))
jobs.append(('re1600_a075_d28_long',dict(diameter=28,duration=80)))
jobs.append(('midpoint_re1200_a0875_d28',dict(diameter=28,reynolds=1200,aspect=.875)))
jobs.append(('midpoint_re2100_a065_d28',dict(diameter=28,reynolds=2100,aspect=.65)))
jobs.append(('re2600_a075_d36',dict(diameter=36,reynolds=2600,aspect=.75)))
(P/'refined_run_design.json').write_text(json.dumps(jobs,indent=2))
for name,args in jobs:
    if (P/'flow'/name/'metadata.json').exists():continue
    cmd=[sys.executable,str(P/'flow_lbm.py'),'--name',name]
    for k,v in args.items():cmd += ['--'+k,str(v)]
    subprocess.run(cmd,check=True)
