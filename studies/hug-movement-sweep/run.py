import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
from model import ROOT,configured,simulate,protocol
def main():
    a=argparse.ArgumentParser();a.add_argument('--kind',choices=['main','fine','timefine','spatial'],required=True);a.add_argument('--scales',nargs='+',type=float);a.add_argument('--orbit-policy',choices=['scaled','fixed'],default='scaled');a.add_argument('--cache',required=True);args=a.parse_args()
    scales=args.scales or protocol()['sweep']['scales']
    for scale in scales:
        out=Path(args.cache)/args.orbit_policy/f'{scale:g}'/args.kind;out.mkdir(parents=True,exist_ok=False)
        p=configured(scale,args.orbit_policy);n={'main':32,'fine':64,'timefine':32,'spatial':128}[args.kind];started=time.perf_counter()
        m,t,z=simulate(p,n,'main' if args.kind=='main' else 'fine')
        np.save(out/'time.npy',t);np.save(out/'state.npy',z)
        meta=dict(scale=scale,orbit_policy=args.orbit_policy,kind=args.kind,nodes=n,rows=m.rows,seconds=time.perf_counter()-started,source_hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['model.py','baseline.py','feedback.py','protocol.json','source_protocol.json','history_ledger.json']})
        (out/'meta.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(scale=scale,kind=args.kind,seconds=meta['seconds'],max_shear=float(np.abs(z[:,:,0]).max()*m.Q/m.L))),flush=True)
if __name__=='__main__':main()
