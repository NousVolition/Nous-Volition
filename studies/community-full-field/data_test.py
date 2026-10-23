"""Real submissions -> explicit candidate observation mapping, not corpus identity."""
import argparse,collections,hashlib,json,sys,zipfile
from pathlib import Path
import numpy as np

HERE=Path(__file__).parent
sys.path.insert(0,str(HERE.parent/('community_mimesis' if (HERE.parent/'community_mimesis').exists() else 'community-mimesis')))
from observations import card_set,correct,file_hash,DELI_SHA

def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def extract(path):
    if file_hash(path)!=DELI_SHA:raise ValueError('Source hash mismatch')
    with zipfile.ZipFile(path) as z:raw=[json.loads(l) for l in z.open('deli-corpus/utterances.jsonl')]
    groups=sorted({r['conversation_id'] for r in raw},key=lambda x:sha('full-field-v1|'+x))
    train=set(groups[:350]);seq=collections.defaultdict(list);counts=collections.Counter();seen=collections.defaultdict(set)
    for r in raw:
        g=r['conversation_id'];parent=r['reply-to']
        if parent is not None and parent not in seen[g]:raise ValueError('Unexpected order')
        seen[g].add(r['id'])
        counts['records']+=1;counts['missing_timestamps']+=int(r['timestamp'] is None)
        if r['meta']['message_type']!='SUBMIT':continue
        counts['submissions']+=1;c=card_set(r['meta']['original_text'])
        if c is None:counts['unparsed']+=1;continue
        seq[g,r['speaker']].append(int(correct(c)))
    data=[]
    for (g,s),ys in seq.items():
        if len(ys)<2:counts['singleton_sequences']+=1;continue
        data.append(dict(group=sha(g),sequence=sha(g+'|'+s),split='train' if g in train else 'evaluation',y=ys))
    data.sort(key=lambda x:x['sequence'])
    counts.update(groups=len(groups),eligible_sequences=len(data),forecasts=sum(len(s['y'])-1 for s in data))
    eligible={s['group'] for s in data}
    split_manifest=[dict(group=sha(g),rank_hash=sha('full-field-v1|'+g),split='train' if g in train else 'evaluation',eligible=sha(g) in eligible) for g in groups]
    return data,dict(counts),split_manifest

def design(data,baseline):
    rows=[]
    for s in data:
        A=B=C=0.;ys=s['y']
        for j in range(1,len(ys)):
            e=ys[j-1]-baseline;B+=A+.5*e;A+=e;C+=e
            rows.append(dict(group=s['group'],sequence=s['sequence'],split=s['split'],step=j,y0=ys[0],previous=ys[j-1],target=ys[j],B=B,C=C,A=A))
    return rows

def fit(rows,key):
    counts=collections.Counter(r['group'] for r in rows);num=den=0.
    for r in rows:
        w=1/counts[r['group']];num+=w*r[key]*(r['target']-r['y0']);den+=w*r[key]**2
    return num/den if den else 0.

def evaluate(data,baseline=None,kappa=None,instant=None):
    tr=[s for s in data if s['split']=='train']
    baseline=float(np.mean([s['y'][0] for s in tr])) if baseline is None else baseline
    rows=design(data,baseline);train=[r for r in rows if r['split']=='train']
    kappa=fit(train,'B') if kappa is None else kappa;instant=fit(train,'C') if instant is None else instant
    mean=float(np.mean([r['target'] for r in train]))
    for r in rows:
        r['field']=r['y0']+kappa*r['B'];r['nonnegative']=r['y0']+max(0.,kappa)*r['B']
        r['instantaneous']=r['y0']+instant*r['C'];r['initial']=r['y0'];r['last']=r['previous'];r['training_mean']=mean
    metrics={};group_scores=[]
    for split in ['train','evaluation']:
        sub=[r for r in rows if r['split']==split];by=collections.defaultdict(list)
        for r in sub:by[r['group']].append(r)
        metrics[split]=dict(groups=len(by),sequences=len({r['sequence'] for r in sub}),forecasts=len(sub),models={})
        for name in ['field','nonnegative','instantaneous','initial','last','training_mean']:
            ms=[];ma=[]
            for g,rr in sorted(by.items()):
                err=np.array([r[name]-r['target'] for r in rr]);mse=float(np.mean(err**2));mae=float(np.mean(abs(err)))
                ms.append(mse);ma.append(mae);group_scores.append(dict(group=g,split=split,model=name,mse=mse,mae=mae,n=len(rr)))
            vals=np.array([r[name] for r in sub])
            metrics[split]['models'][name]=dict(macro_mse=float(np.mean(ms)),macro_mae=float(np.mean(ma)),outside_unit_interval=int(np.sum((vals<0)|(vals>1))),minimum=float(vals.min()),maximum=float(vals.max()))
    gs=collections.defaultdict(dict)
    for r in group_scores:
        if r['split']=='evaluation':gs[r['group']][r['model']]=r['mse']
    diff=np.array([v['field']-v['last'] for _,v in sorted(gs.items())]);rng=np.random.default_rng(20261022)
    boots=[float(rng.choice(diff,len(diff),replace=True).mean()) for _ in range(2000)]
    metrics['paired_field_minus_last_mse']=dict(estimate=float(diff.mean()),interval95=np.quantile(boots,[.025,.975]).tolist(),bootstrap_groups=len(diff),replicates=2000,seed=20261022)
    metrics['parameters']=dict(baseline=baseline,gamma=1.,kappa=kappa,nonnegative_kappa=max(0.,kappa),instantaneous_coefficient=instant,training_target_mean=mean)
    return rows,group_scores,metrics

def main():
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path);args=p.parse_args();out=HERE/'results';out.mkdir(exist_ok=True)
    if args.raw:
        data,counts,split_manifest=extract(args.raw)
        (out/'sequences.json').write_text(json.dumps(data,separators=(',',':'))+'\n')
        (out/'data_accounting.json').write_text(json.dumps(counts,indent=2)+'\n')
        (out/'split_manifest.json').write_text(json.dumps(split_manifest,separators=(',',':'))+'\n')
    else:data=json.loads((out/'sequences.json').read_text())
    rows,groups,metrics=evaluate(data)
    import csv
    for name,rr in [('forecasts',rows),('group_scores',groups)]:
        with (out/(name+'.csv')).open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
    pilots=[s for s in data if s['split']=='evaluation' and len(s['y'])>=5][:2]
    (out/'pilot_selection.json').write_text(json.dumps(pilots,indent=2)+'\n')
    (out/'data_results.json').write_text(json.dumps(metrics,indent=2)+'\n')
    print(json.dumps(metrics,indent=2))
if __name__=='__main__':main()
