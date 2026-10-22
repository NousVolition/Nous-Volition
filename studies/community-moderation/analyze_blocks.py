from pathlib import Path
import argparse,sqlite3,json,math,itertools,collections,csv
from analysis_core import episodes,epoch,DAY,paired_duration

ROOT=Path(__file__).resolve().parent
def analyze(raw,out):
    meta=json.loads((raw/'block_cache_meta.json').read_text());end=meta['latest'];con=sqlite3.connect(raw/'blocks_v2.sqlite')
    windows={w:{'eligible':0,'repeat':0,'infinite_second':0,'finite_pairs':[],'same_moderator':[],'disruption_subset':[]} for w in (30,90,180)}
    counters=collections.Counter();paired=[]
    it=con.execute('SELECT account,t,logid,action,expiry,moderator,reason FROM events ORDER BY account,t,logid')
    for account,group in itertools.groupby(it,key=lambda r:r[0]):
        events=[tuple(r[1:]) for r in group];eps,issues=episodes(events);counters['accounts']+=1
        if issues:
            counters['accounts_excluded_reconstruction']+=1
            for s in issues:counters[s]+=1
            continue
        if not eps:continue
        first=eps[0]
        if first['start']<epoch('2006-01-01T00:00:00Z'):counters['first_before_2006']+=1;continue
        if not math.isfinite(first['initial_duration']):counters['initial_indefinite']+=1;continue
        if not math.isfinite(first['end']):counters['first_never_observed_end']+=1;continue
        second=eps[1] if len(eps)>1 else None
        for w,stat in windows.items():
            if first['end']+w*DAY>end:continue
            stat['eligible']+=1
            if second is None or not (0<second['start']-first['end']<=w*DAY):continue
            stat['repeat']+=1
            if not math.isfinite(second['initial_duration']):stat['infinite_second']+=1;continue
            pair=(first['initial_duration'],second['initial_duration']);stat['finite_pairs'].append(pair)
            same=first['moderator'] is not None and first['moderator']==second['moderator'];dis=first['disruption'] and second['disruption']
            if same:stat['same_moderator'].append(pair)
            if dis:stat['disruption_subset'].append(pair)
            if w==180:paired.append({'account_hash':account,'first_hours':pair[0]/3600,'second_hours':pair[1]/3600,'gap_days':(second['start']-first['end'])/DAY,'same_moderator':same,'both_disruption_keywords':dis})
    out.mkdir(parents=True,exist_ok=True)
    with (out/'duration_histogram.csv').open('w',newline='') as f:
        wr=csv.writer(f);wr.writerow(['window_days','subset','first_seconds','second_seconds','count'])
        for w,s in windows.items():
            for k in ('finite_pairs','same_moderator','disruption_subset'):
                for (x,y),n in sorted(collections.Counter(s[k]).items()):wr.writerow([w,k,x,y,n])
    result={'log':meta,'exclusions':dict(counters),'windows':{}}
    for w,s in windows.items():
        result['windows'][str(w)]={k:v for k,v in s.items() if not isinstance(v,list)}
        for k in ('finite_pairs','same_moderator','disruption_subset'):result['windows'][str(w)][k]=paired_duration(s[k])
    out.mkdir(parents=True,exist_ok=True);(out/'block_results.json').write_text(json.dumps(result,indent=2))
    # Aggregate sufficient statistics only; raw and account-level comparisons stay local.
    (raw/'block_pairs_private.json').write_text(json.dumps(paired));print(json.dumps({k:v for k,v in result.items() if k!='log'},indent=2))
    return result
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--raw-dir',type=Path,required=True);ap.add_argument('--out-dir',type=Path,default=ROOT/'data');a=ap.parse_args();analyze(a.raw_dir,a.out_dir)
