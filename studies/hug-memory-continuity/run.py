import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
from model import protocol,simulate,Hug
ROOT=Path(__file__).resolve().parent
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--kind',choices=['main','fine','timefine','spatial'],default='main');ap.add_argument('--cache',required=True);a=ap.parse_args();p=protocol()
    kind='main' if a.kind=='main' else 'fine'
    n=p['numerics']['main_nodes'] if a.kind in ('main','timefine') else p['numerics']['fine_nodes']
    selected=None
    if a.kind=='spatial':
        n=128;selected=[dict(scenario=s,condition=c,history=0) for s in ['retained','opposing','persistent'] for c in range(3)]
    folder=Path(a.cache)/a.kind;folder.mkdir(parents=True,exist_ok=False)
    ledger=dict(events=p['events'],scenario_routes=[dict(id=s['id'],generation=s['generation'],transmission=s['transmission'],caregiver=s['caregiver'],neighbor=s['neighbor']) for s in p['scenarios']],ancestry=p['ancestry_channel'])
    ledgertext=json.dumps(ledger,sort_keys=True,indent=2)+'\n';(ROOT/'history_ledger.json').write_bytes(ledgertext.encode('utf-8'))
    t0=time.perf_counter();m,t,z,jumps=simulate(p,n,kind,selected)
    np.save(folder/'times.npy',t);np.save(folder/'states.npy',z)
    meta=dict(kind=a.kind,nodes=n,rows=m.rows,width=m.width,elapsed_s=time.perf_counter()-t0,jumps=jumps,ledger_sha256=hashlib.sha256(ledgertext.encode()).hexdigest(),source_hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['model.py','protocol.json']})
    (folder/'meta.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(kind=a.kind,seconds=meta['elapsed_s'],paths=m.nr,samples=len(t),max_S=float(np.max(np.abs(z[:,:,7:7+n]))),bound=m.bound())),flush=True)
if __name__=='__main__':main()
