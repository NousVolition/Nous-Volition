"""Measured sequence tests; no predictive surrogate and no inferred mental states."""
from pathlib import Path
import argparse,csv,hashlib,json
import numpy as np
from scipy.io import loadmat

ROOT=Path(__file__).resolve().parent

def scale(x):
    x=np.array(x,dtype=float,copy=True)
    if x.ndim!=3 or x.shape[2]!=3 or x.shape[1]%4: raise ValueError('Expected people x four equal chains x three ratings')
    valid=np.isfinite(x)
    lo=np.array([-1,0,-1]); hi=np.ones(3)
    if np.any(valid & ((x<lo-1e-12)|(x>hi+1e-12))): raise ValueError('Ratings outside source scales')
    x[:,:,[0,2]]=(x[:,:,[0,2]]+1)/2
    return x

def chains(x):
    p,t,k=x.shape
    return x.reshape(p,4,t//4,k)

def displacement(x):
    c=chains(x); ok=np.isfinite(c).all(-1)
    pair=ok[:,:,1:] & ok[:,:,:-1]
    d=np.sum(np.diff(c,axis=2)**2,axis=-1)
    count=pair.sum((1,2))
    return np.divide(np.where(pair,d,0).sum((1,2)),count,out=np.full(len(x),np.nan),where=count>0),count

def shuffled(x,rng):
    c=chains(x).copy()
    # Missing positions stay fixed. Whole vectors move together within each chain.
    if np.isfinite(c).all():
        order=np.argsort(rng.random(c.shape[:-1]),axis=-1)
        c=np.take_along_axis(c,order[...,None],axis=2)
    else:
        for row in c:
            for chain in row:
                idx=np.flatnonzero(np.isfinite(chain).all(-1))
                chain[idx]=chain[rng.permutation(idx)]
    return c.reshape(x.shape)

def expected_displacement(x):
    c=chains(x); out=[]
    for row in c:
        weighted=0.; n=0
        for chain in row:
            ok=np.isfinite(chain).all(-1); z=chain[ok]; m=len(z)
            pairs=int(np.sum(ok[1:]&ok[:-1]))
            if m>1 and pairs:
                e=2*m/(m-1)*np.sum(np.var(z,axis=0))
                weighted+=pairs*e;n+=pairs
        out.append(weighted/n if n else np.nan)
    return np.array(out)

def boot_ci(z,seed,n=1999):
    z=np.asarray(z);z=z[np.isfinite(z)]
    if len(z)<2: return [None,None]
    rng=np.random.default_rng(seed)
    b=np.mean(z[rng.integers(len(z),size=(n,len(z)))],axis=1)
    return np.quantile(b,[.025,.975]).tolist()

def order_test(raw,ids,seed=261023,reps=999):
    x=scale(raw);d,count=displacement(x);e=expected_displacement(x)
    valid=np.isfinite(d);rng=np.random.default_rng(seed)
    null=np.array([np.nanmean(displacement(shuffled(x,rng))[0]) for _ in range(reps)])
    obs=float(np.mean(d[valid]));effect=e-d
    s={'people':len(x),'eligible_people':int(valid.sum()),'response_slots':int(np.prod(x.shape[:2])),
       'complete_vectors':int(np.isfinite(x).all(-1).sum()),'missing_vectors':int((~np.isfinite(x).all(-1)).sum()),
       'within_chain_pairs':int(count.sum()),'excluded_chain_boundaries':int(len(x)*3),
       'observed_mean_squared_displacement':obs,'expected_shuffled_displacement':float(np.nanmean(e)),
       'difference_shuffled_minus_ordered':float(np.nanmean(effect)),
       'difference_person_bootstrap_95pct':boot_ci(effect,seed+10),
       'monte_carlo_p_one_sided':float((1+np.sum(null<=obs))/(reps+1)),
       'permutations':reps,'seed':seed,'permutation_mean':float(null.mean()),
       'nonzero_valence':int(np.sum(np.isfinite(raw[:,:,0]) & (raw[:,:,0]!=0))),
       'varying_valence_people':int(np.sum(np.nanmax(raw[:,:,0],axis=1)>np.nanmin(raw[:,:,0],axis=1)))}
    rows=[{'record_id':int(i),'valid_adjacent_pairs':int(n),'ordered_displacement':float(a),'shuffle_expectation':float(b),'difference':float(b-a)} for i,n,a,b in zip(ids,count,d,e)]
    return s,rows

def paired_test(raw,left,right,reps=999):
    x=scale(raw)
    a=np.nanmean(x[left],axis=1);b=np.nanmean(x[right],axis=1)
    if not np.isfinite(a).all() or not np.isfinite(b).all(): raise ValueError('Missing paired-session centroid')
    d=np.sum((a-b)**2,axis=1);rng=np.random.default_rng(261024)
    null=np.array([np.mean(np.sum((a-b[rng.permutation(len(b))])**2,axis=1)) for _ in range(reps)])
    # Exact null expectation and person-wise contrasts. CI is a paired bootstrap
    # of the two-session people, with independent-match expectation recalculated.
    def eff(aa,bb):
        return float(np.mean(np.sum((aa[:,None]-bb[None,:])**2,axis=-1))-np.mean(np.sum((aa-bb)**2,axis=1)))
    effect=eff(a,b);bs=[]
    for _ in range(1999):
        idx=rng.integers(len(a),size=len(a));bs.append(eff(a[idx],b[idx]))
    return {'pairs':len(a),'matched_mean_squared_centroid_distance':float(d.mean()),
       'random_pair_expectation':float(np.mean(np.sum((a[:,None]-b[None,:])**2,axis=-1))),
       'difference_random_minus_matched':effect,'paired_bootstrap_95pct':np.quantile(bs,[.025,.975]).tolist(),
       'monte_carlo_p_one_sided':float((1+np.sum(null<=d.mean()))/(reps+1)),'permutations':reps,'seed':261024},[
       {'first_record_id':int(i+1),'second_record_id':int(j+1),'squared_centroid_distance':float(v)} for i,j,v in zip(left,right,d)]

def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def run(rawdir,outdir,stage):
    outdir.mkdir(parents=True,exist_ok=True)
    if stage=='study1':
        p=rawdir/'fastweb_basedata.mat';m=loadmat(p)
        ids={k:m[k].ravel().astype(int)-1 for k in ['trainid','testid','subj_j_2']}
        for z in ids.values():
            if len(z)!=len(set(z)) or z.min()<0 or z.max()>=len(m['dat_all']):raise ValueError('Bad source indices')
        a=ids['trainid'];b=ids['testid'];c=ids['subj_j_2']
        if set(b)&set(c) or set(a)&set(c) or len(b)!=len(c):raise ValueError('Invalid retest separation')
        train,tr=order_test(m['dat_all'][a],a+1)
        retest,rr=order_test(m['dat_all'][c],c+1,261024)
        pair,pr=paired_test(m['dat_all'],b,c)
        r={'study1_training':train,'study1_retest_order':retest,'paired_sessions':pair,
           'training_retest_first_session_overlap':len(set(a)&set(b)),
           'unused_record_ids':sorted(set(range(1,len(m['dat_all'])+1))-set((a+1).tolist())-set((c+1).tolist()))}
        write_csv(outdir/'study1_training_people.csv',tr);write_csv(outdir/'study1_retest_people.csv',rr);write_csv(outdir/'paired_sessions.csv',pr)
    else:
        p=rawdir/'fastweb_basedata_study2.mat';m=loadmat(p);x=m['dat_study2']
        r,rows=order_test(x,np.arange(len(x))+1,261023)
        write_csv(outdir/'study2_people.csv',rows)
    r['source_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    (outdir/(stage+'_results.json')).write_text(json.dumps(r,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(r,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--out',type=Path,default=ROOT);p.add_argument('--stage',choices=['study1','study2'],required=True);a=p.parse_args();run(a.raw,a.out,a.stage)
