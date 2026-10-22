"""Stream the public JSONL log into a local SQLite cache; exclude IP targets."""
from pathlib import Path
import argparse,sqlite3,json,ipaddress,collections,hashlib
from block_episodes import epoch,expiry,disruption,digest

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw-dir',type=Path,required=True);a=ap.parse_args()
    source=a.raw_dir/'blocks.json';db=a.raw_dir/'blocks_v2.sqlite'
    if db.exists():raise RuntimeError('Cache already exists. Use the verified existing cache or choose a fresh raw directory.')
    con=sqlite3.connect(db);con.execute('CREATE TABLE events(account TEXT,t REAL,logid INTEGER PRIMARY KEY,action TEXT,expiry REAL,moderator TEXT,reason INTEGER)')
    c=collections.Counter();h=hashlib.sha256();latest=0;earliest=float('inf');batch=[];types=collections.Counter();unknown=collections.Counter()
    with source.open('rb') as f:
        for line in f:
            h.update(line);r=json.loads(line);c['raw_events']+=1;t=epoch(r['timestamp']);latest=max(t,latest);earliest=min(t,earliest)
            if 'title' not in r or r.get('actionhidden') is not None:c['hidden_target_events']+=1;continue
            title=r['title']
            if not title.startswith('User:'):c['non_user_namespace']+=1;continue
            name=title[5:]
            try:ipaddress.ip_network(name,strict=False);c['ip_target_events']+=1;continue
            except ValueError:pass
            params=r.get('params',{});types[type(params).__name__]+=1;e=expiry(params,t)
            if e is None and r['action']!='unblock':unknown[str(params.get('duration','')) if isinstance(params,dict) else str(params)[:60]]+=1
            batch.append((digest(name),t,r['logid'],r['action'],e,digest(r.get('user','')) if 'user' in r else None,int(disruption(r.get('comment','')))))
            c['named_events']+=1
            if len(batch)>=10000:
                con.executemany('INSERT INTO events VALUES(?,?,?,?,?,?,?)',batch);con.commit();batch=[]
    con.executemany('INSERT INTO events VALUES(?,?,?,?,?,?,?)',batch);con.execute('CREATE INDEX by_account ON events(account,t,logid)');con.commit()
    c['unique_accounts']=con.execute('SELECT COUNT(DISTINCT account) FROM events').fetchone()[0]
    expected=next(s['sha256'] for s in json.loads((Path(__file__).resolve().parent/'sources.json').read_text())['files'] if s['file']=='blocks.json')
    if h.hexdigest()!=expected:raise RuntimeError('Block-log source hash mismatch; do not analyze this cache')
    meta={'counts':dict(c),'sha256':h.hexdigest(),'bytes':source.stat().st_size,'latest':latest,'earliest':earliest,'params_types':dict(types),'unknown_durations':unknown.most_common(30)}
    (a.raw_dir/'block_cache_meta.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
