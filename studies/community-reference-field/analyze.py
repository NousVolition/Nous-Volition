from dataclasses import replace,asdict
from pathlib import Path
import argparse,collections,csv,gzip,hashlib,json,time
import numpy as np
from batch_field import BatchField,Parameters
P=Path(__file__).parent;R=P/'results'
def bootstrap_group(rows,value,group='dialogue'):
    by=collections.defaultdict(list)
    for r in rows:by[r[group]].append(float(r[value]))
    means=np.array([np.mean(v) for k,v in sorted(by.items())]);rng=np.random.default_rng(20261023)
    boot=[float(rng.choice(means,len(means),replace=True).mean()) for _ in range(2000)]
    return dict(mean=float(means.mean()),interval95=np.quantile(boot,[.025,.975]).tolist(),groups=len(means),records=len(rows))
def fit_memory(train):
    baseline=float(np.mean([e['U'][0] for e in train]));num=den=0.
    for e in train:
        A=B=0.
        for j,dt in enumerate(e['dt']):
            v=e['U'][j]-baseline;B+=A*dt+.5*v*dt**2;A+=v*dt
            num+=B*(e['counts'][j+1]-e['counts'][0]);den+=B*B
    return baseline,num/den if den else 0.
def mse(rows):return float(np.mean([r['mse'] for r in rows]))
def simulate(episodes,p,dt=.005):
    allrows=[];states=[];targets=[];used_dt=dt
    for start in range(0,len(episodes),16):
        b=BatchField(episodes[start:start+16],p);attempt=dt
        while True:
            try:rr,ss,tt=b.run(attempt);break
            except FloatingPointError:
                attempt/=2
                if attempt<.0003125:raise
        used_dt=min(used_dt,attempt);allrows.extend(rr);states.append(ss);targets.append(tt)
    return allrows,np.concatenate(states,axis=2),np.concatenate(targets,axis=0),used_dt
def main():
    start=time.perf_counter();episodes=json.loads((R/'episodes.json').read_text());train=[e for e in episodes if e['split']=='train'];test=[e for e in episodes if e['split']=='evaluation']
    base,kappa=fit_memory(train);p=Parameters(n=16,h=.12,threshold=1.,epsilon=1.,baseline=base,kappa=kappa)
    candidates=[];index=0
    for sigma in [.0001,.001,.01,0.]:
        for D in [0.,.001,.01]:
            pp=replace(p,sigma=sigma,diffusivity=D);print('FIT',index,sigma,D,flush=True)
            rows,_,_,dt=simulate(train,pp);candidates.append(dict(index=index,sigma=sigma,D=D,train_mse=mse(rows),max_dt_used=dt));index+=1
    best=min((r for r in candidates if r['sigma']>0),key=lambda r:(r['train_mse'],r['index']));off=min((r for r in candidates if r['sigma']==0),key=lambda r:(r['train_mse'],r['index']))
    selected=replace(p,sigma=best['sigma'],diffusivity=best['D']);freeze=dict(candidates=candidates,selected=best,force_off=off,parameters=asdict(selected),protocol_sha256=hashlib.sha256((P/'PROTOCOL.md').read_bytes()).hexdigest(),selection='Training only; fixed before running evaluation fields')
    (R/'fit_lock.json').write_text(json.dumps(freeze,indent=2)+'\n');print('LOCKED',best,flush=True)
    runs={};saved={};preds=[];all_scalar={}
    for name,pp in [('coupled',selected),('force_off',replace(selected,sigma=0.,diffusivity=off['D'])),('source_off',replace(selected,kappa=0.)),('nonnegative_kappa',replace(selected,kappa=max(0.,kappa))),('signed_tanh',replace(selected,law='tanh')),('smooth_off',replace(selected,law='smooth_off'))]:
        print('EVALUATE',name,flush=True);rows,states,targets,dt=simulate(test,pp)
        for r in rows:r['model']=name
        preds+=rows;runs[name]=dict(mse=mse(rows),shape_mse=float(np.mean([r['shape_mse'] for r in rows])),max_mass_error=max(abs(r['mass_error']) for r in rows),max_divergence=max(r['divergence'] for r in rows),max_energy_identity=max(abs(r['energy_identity']) for r in rows),max_dt_used=dt)
        all_scalar[name]=states[:,2]
        if name in ['coupled','force_off','signed_tanh']:saved[name]=states[:,:,:4]
        if name=='coupled':coupled_states=states;target_fields=targets;saved['targets']=targets[:4]
    for name in ['initial','last']:
        rows=[]
        for i,e in enumerate(test):
            for j in range(2):
                err=target_fields[i,0 if name=='initial' else j]-target_fields[i,j+1]
                rows.append(dict(case=e['case'],scenario=e['scenario'],split='evaluation',step=j+1,mse=float(np.mean(err**2)),shape_mse=float(np.mean((err-err.mean())**2)),model=name))
        preds+=rows;runs[name]=dict(mse=mse(rows),shape_mse=float(np.mean([r['shape_mse'] for r in rows])))
    refinements=[]
    for name,pp,dt in [('fine32',replace(selected,n=32),.005),('half_step',selected,.0025)]:
        print('REFINE',name,flush=True);rr,ss,tt,used=simulate(test[:4],pp,dt)
        if name=='fine32':
            # Compare all Fourier modes by embedding the coarse field in the fine grid.
            from run_spatial import l2_low_difference
            # run_spatial is supplied by the pinned previous full-field study.
            dif=[l2_low_difference(np.fft.fft2(coupled_states[-1,:,i]),np.fft.fft2(ss[-1,:,i])) for i in range(4)]
        else:dif=[float(np.sqrt(np.mean((coupled_states[-1,:,i]-ss[-1,:,i])**2))) for i in range(4)]
        refinements.append(dict(name=name,mse=mse(rr),differences=dif,max_dt=used));saved[name]=ss
    # Paired differences use one mean of both horizons per scenario.
    by=collections.defaultdict(dict)
    for r in preds:by[r['case'],r['step']][r['model']]=r['mse']
    differences={}
    for control in ['initial','last','force_off']:
        dr=[dict(dialogue=case,value=v['coupled']-v[control]) for (case,step),v in by.items()];differences[control]=bootstrap_group(dr,'value')
    with (R/'predictions.csv').open('w',newline='') as f:
        keys=list(dict.fromkeys(k for r in preds for k in r));w=csv.DictWriter(f,keys);w.writeheader();w.writerows(preds)
    result=dict(parameters=asdict(selected),training_candidates=len(candidates),evaluation_episodes=len(test),evaluation_intervals=2*len(test),runs=runs,paired_mse_differences=differences,refinement=refinements,elapsed_seconds=time.perf_counter()-start)
    (R/'field_results.json').write_text(json.dumps(result,indent=2)+'\n');np.savez_compressed(R/'fields.npz',**saved)
    np.savez_compressed(R/'scalar_predictions.npz',targets=target_fields,**all_scalar)
    pairs=json.loads(gzip.decompress((R/'wording_pairs.json.gz').read_bytes()));overlap=json.loads(gzip.decompress((R/'interaction_overlaps.json.gz').read_bytes()))
    desc=dict(changed_wording=bootstrap_group([r for r in pairs if r['changed_wording']],'delta'),unchanged_wording=bootstrap_group([r for r in pairs if not r['changed_wording']],'delta'),cross_speaker_jaccard=bootstrap_group(overlap,'jaccard'))
    (R/'descriptive.json').write_text(json.dumps(desc,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
