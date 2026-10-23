from pathlib import Path
import collections,csv,gzip,hashlib,json,math
import numpy as np
P=Path(__file__).parent;R=P/'results';checks=[]
def read(n):return json.loads((R/n).read_text())
def compressed(n):return json.loads(gzip.decompress((R/n).read_bytes()))
def check(name,ok):
    if not ok:raise AssertionError(name)
    checks.append(name)
def close(a,b):return math.isclose(float(a),float(b),rel_tol=2e-10,abs_tol=1e-10)
def main():
    e=read('episodes.json');f=read('fit_lock.json');r=read('field_results.json');a=read('accounting.json');d=read('descriptive.json')
    check('Frozen protocol',hashlib.sha256((P/'PROTOCOL.md').read_bytes()).hexdigest()=='488413f9ee5ee9d497302159164203e4a4afbb2f11fcb26d98dfca7f41206821')
    previous=P.parent/('community_full_field' if (P.parent/'community_full_field').exists() else 'community-full-field')
    check('Unchanged imported corpus solver',hashlib.sha256((previous/'field.py').read_bytes()).hexdigest()=='00b50a93ae413d46109327ccf0c08e8e07d00028313eaa0da87d765e58705f35')
    train=[x for x in e if x['split']=='train'];test=[x for x in e if x['split']=='evaluation']
    check('64 distinct scenarios each split',len(train)==len(test)==64 and len({x['scenario'] for x in e})==128)
    eligible=compressed('eligible_selection.json.gz');chosen=[]
    for split in ['train','evaluation']:
        seen=set()
        for x in sorted([x for x in eligible if x['split']==split],key=lambda x:x['case']):
            if x['scenario'] in seen:continue
            chosen.append(x['case']);seen.add(x['scenario'])
            if len(seen)==64:break
    check('Fixed selection reproduced',chosen==[x['case'] for x in e])
    check('Measured intervals and counts valid',all(len(x['dt'])==2 and all(0<t<=2 for t in x['dt']) and x['counts']==[len(p) for p in x['points']] and all(0<=u<=1 for u in x['U']) for x in e))
    base=sum(x['U'][0] for x in train)/64;num=den=0.
    for x in train:
        A=B=0.
        for j,t in enumerate(x['dt']):
            u=x['U'][j]-base;B+=A*t+u*t*t/2;A+=u*t;num+=B*(x['counts'][j+1]-x['counts'][0]);den+=B*B
    check('Training-only utility baseline',close(base,f['parameters']['baseline']))
    check('Training-only memory coefficient',close(num/den,f['parameters']['kappa']))
    cand=f['candidates'];check('Best coupled candidate only from training',f['selected']==min([x for x in cand if x['sigma']>0],key=lambda x:(x['train_mse'],x['index'])))
    check('Best no-force control from training',f['force_off']==min([x for x in cand if x['sigma']==0],key=lambda x:(x['train_mse'],x['index'])))
    with (R/'predictions.csv').open(newline='') as src:rows=list(csv.DictReader(src))
    z=np.load(R/'scalar_predictions.npz');bycase={x['case']:(i,x) for i,x in enumerate(test)};scores=collections.defaultdict(list)
    for row in rows:
        i,x=bycase[row['case']];j=int(row['step'])-1;name=row['model'];target=z['targets'][i,j+1]
        pred=z[name][j,i] if name not in ['initial','last'] else z['targets'][i,0 if name=='initial' else j]
        diff=pred-target;value=float(np.mean(diff*diff))
        check('Pixelwise MSE '+name+' '+x['case'][:8]+' '+str(j),close(value,row['mse']))
        check('Demeaned field MSE '+name+' '+x['case'][:8]+' '+str(j),close(np.mean((diff-diff.mean())**2),row['shape_mse']))
        scores[name].append(value)
        if name in ['initial','last']:continue
        A=0.;M=x['counts'][0];kap=f['parameters']['kappa']
        if name=='source_off':kap=0.
        if name=='nonnegative_kappa':kap=max(0.,kap)
        for k in range(j+1):
            t=x['dt'][k];u=x['U'][k]-base;M+=kap*(A*t+.5*u*t*t);A+=u*t
        check('Full-system mass '+name+' '+x['case'][:8]+' '+str(j),abs(M-pred.mean())<1e-9 and close(M,row['mass_exact']))
    check('All eight comparisons and cases present',len(rows)==8*128 and all(len(v)==128 for v in scores.values()))
    for name,v in scores.items():check('Aggregated MSE '+name,close(np.mean(v),r['runs'][name]['mse']))
    by=collections.defaultdict(lambda:collections.defaultdict(list))
    for row in rows:by[row['case']][row['model']].append(float(row['mse']))
    for control in ['initial','last','force_off']:
        delta=np.array([np.mean(v['coupled'])-np.mean(v[control]) for case,v in sorted(by.items())]);rng=np.random.default_rng(20261023)
        boot=[rng.choice(delta,len(delta),replace=True).mean() for _ in range(2000)]
        check('Paired field estimate '+control,close(delta.mean(),r['paired_mse_differences'][control]['mean']))
        check('Paired field interval '+control,np.allclose(np.quantile(boot,[.025,.975]),r['paired_mse_differences'][control]['interval95'],atol=1e-10))
    check('Finite outputs',all(np.isfinite(v).all() for v in z.values()))
    check('Conservation/energy diagnostics',all(v.get('max_mass_error',0)<1e-9 and v.get('max_divergence',0)<1e-9 and v.get('max_energy_identity',0)<1e-8 for v in r['runs'].values()))
    pairs=compressed('wording_pairs.json.gz');overlap=compressed('interaction_overlaps.json.gz')
    check('All descriptive records counted',len(pairs)==a['wording_pairs'] and len(overlap)==a['cross_speaker_transitions'])
    check('Pair changes correct',all(close(x['after']-x['before'],x['delta']) and x['gap_seconds']>0 for x in pairs))
    # Independently rebuild whole-dialogue bootstrap, including its ordering.
    for name,records,value in [('changed_wording',[x for x in pairs if x['changed_wording']],'delta'),('unchanged_wording',[x for x in pairs if not x['changed_wording']],'delta'),('cross_speaker_jaccard',overlap,'jaccard')]:
        by=collections.defaultdict(list)
        for x in records:by[x['dialogue']].append(x[value])
        m=np.array([np.mean(v) for _,v in sorted(by.items())]);rng=np.random.default_rng(20261023);boot=[rng.choice(m,len(m),replace=True).mean() for _ in range(2000)]
        check('Descriptive estimate '+name,close(m.mean(),d[name]['mean']))
        check('Descriptive interval '+name,np.allclose(np.quantile(boot,[.025,.975]),d[name]['interval95'],atol=1e-11))
    check('Accounting exclusions',a['markables_considered']==a['retained_markables']+a['fewer_than_three_votes_excluded']+a['nonconcrete_or_uncertain_excluded'])
    print(json.dumps(dict(passed=len(checks),scope='Source/selection, fit, full pixel errors, mass identities, diagnostics and descriptive bootstrap'),indent=2))
if __name__=='__main__':main()
