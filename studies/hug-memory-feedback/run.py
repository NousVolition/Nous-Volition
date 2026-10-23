import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
from model import protocol,simulate
ROOT=Path(__file__).resolve().parent
def main():
    a=argparse.ArgumentParser();a.add_argument('--kind',choices=['main','fine','timefine','spatial'],default='main');a.add_argument('--cache',required=True);args=a.parse_args();p=protocol()
    n={'main':32,'fine':64,'timefine':32,'spatial':128}[args.kind]
    selected=None if args.kind!='spatial' else [dict(scenario=s,condition=c,history=h) for s in ['feedback','frozen'] for c in range(3) for h in range(2)]
    folder=Path(args.cache)/args.kind;folder.mkdir(parents=True,exist_ok=False);start=time.perf_counter()
    m,t,z=simulate(p,n,'main' if args.kind=='main' else 'fine',selected)
    np.save(folder/'time.npy',t);np.save(folder/'state.npy',z)
    meta=dict(kind=args.kind,nodes=n,rows=m.rows,seconds=time.perf_counter()-start,source_hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['model.py','baseline.py','protocol.json','history_ledger.json']})
    (folder/'meta.json').write_bytes((json.dumps(meta,indent=2)+'\n').encode())
    print(json.dumps(dict(kind=args.kind,seconds=meta['seconds'],paths=m.nr,max_abs_S=float(np.abs(z[:,:,7:7+n]).max()),field_bound=m.bound())))
if __name__=='__main__':main()
