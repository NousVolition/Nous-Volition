"""Inspect the audited original texts locally, with preceding context if desired."""
from pathlib import Path
import argparse,json
from analyze_wording import load_endpoints,pairkey
ROOT=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--raw-dir',type=Path,required=True);ap.add_argument('--pair-hash',required=True);ap.add_argument('--context',action='store_true');a=ap.parse_args()
end,context=load_endpoints(a.raw_dir);by={r['conversation_id']:r for r in end}
for x in end:
    y=by[x['pair_id']]
    if x['conversation_id']<y['conversation_id'] and pairkey(x,y).startswith(a.pair_hash):
        for r in (x,y):
            print('\nRecorded Rule-2 removal:',r['removed'])
            if a.context:
                for q in sorted(context[r['conversation_id']],key=lambda z:z['timestamp']):print('\n',q['text'])
            else:print(r['text'])
