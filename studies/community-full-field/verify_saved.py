"""Independent arithmetic and provenance checks; no raw text or network required."""
import collections,csv,hashlib,json,math
from pathlib import Path
import numpy as np
P=Path(__file__).parent;R=P/'results';checks=[]
def check(name,ok):
    if not ok:raise AssertionError(name)
    checks.append(name)
def close(a,b):return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-11)
def read(n):return json.loads((R/n).read_text())
def main():
    d=read('sequences.json');out=read('data_results.json');counts=read('data_accounting.json');p=out['parameters']
    check('Frozen protocol unchanged',hashlib.sha256((P/'PROTOCOL.md').read_bytes()).hexdigest()=='8ef6b96534bcd1960d9b2d27e86d7389f571d36cfa0d5aca12dba1ac9802ee4e')
    check('No group split',not({s['group'] for s in d if s['split']=='train'}&{s['group'] for s in d if s['split']=='evaluation'}))
    split=read('split_manifest.json')
    check('All 500 groups split in fixed rank order',len(split)==500 and split==sorted(split,key=lambda r:r['rank_hash']) and all(r['split']==('train' if j<350 else 'evaluation') for j,r in enumerate(split)))
    sm={s['group']:s['split'] for s in split}
    check('Sequences agree with original group assignment',all(sm[s['group']]==s['split'] for s in d))
    check('Unique sequence hashes',len({s['sequence'] for s in d})==len(d))
    check('Valid binary observations',all(len(s['y'])>=2 and set(s['y'])<={0,1} for s in d))
    check('All valid submissions accounted',sum(len(s['y']) for s in d)+counts['singleton_sequences']+counts['unparsed']==counts['submissions'])
    check('All forecasts accounted',sum(len(s['y'])-1 for s in d)==counts['forecasts']==1507)
    baseline=sum(s['y'][0] for s in d if s['split']=='train')/sum(s['split']=='train' for s in d)
    check('Training-only baseline',close(baseline,p['baseline']))
    with (R/'forecasts.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    expected={};train_n=collections.Counter()
    for s in d:
        A=mass_basis=instant=0.
        for j in range(1,len(s['y'])):
            inp=s['y'][j-1]-baseline;mass_basis+=A+inp/2;A+=inp;instant+=inp
            key=(s['sequence'],j);expected[key]=(s,j,A,mass_basis,instant)
            if s['split']=='train':train_n[s['group']]+=1
    numerator=denominator=0.
    for s,j,A,B,C in expected.values():
        if s['split']=='train':
            w=1/train_n[s['group']];numerator+=w*B*(s['y'][j]-s['y'][0]);denominator+=w*B*B
    check('Independent fitted coefficient',close(numerator/denominator,p['kappa']))
    check('Every forecast has one row',len(rows)==len(expected)==len({(r['sequence'],int(r['step'])) for r in rows}))
    errors=collections.defaultdict(list);group_models=collections.defaultdict(dict)
    for r in rows:
        s,j,A,B,C=expected[r['sequence'],int(r['step'])]
        check('Sequence recurrence '+s['sequence'][:8]+' '+str(j),close(A,r['A']) and close(B,r['B']) and close(C,r['C']) and int(r['target'])==s['y'][j] and r['group']==s['group'] and r['split']==s['split'])
        values=dict(field=s['y'][0]+p['kappa']*B,nonnegative=s['y'][0]+max(0.,p['kappa'])*B,instantaneous=s['y'][0]+p['instantaneous_coefficient']*C,initial=s['y'][0],last=s['y'][j-1],training_mean=p['training_target_mean'])
        check('All predictions '+s['sequence'][:8]+' '+str(j),all(close(v,r[k]) for k,v in values.items()))
        for k,v in values.items():errors[s['split'],s['group'],k].append(v-s['y'][j])
    for (split,g,k),err in errors.items():group_models[split,k][g]=float(np.mean(np.square(err)))
    for (split,k),gm in group_models.items():check('Macro MSE '+split+' '+k,close(np.mean(list(gm.values())),out[split]['models'][k]['macro_mse']))
    dif=np.array([group_models['evaluation','field'][g]-group_models['evaluation','last'][g] for g in sorted(group_models['evaluation','field'])])
    check('Paired MSE estimate',close(dif.mean(),out['paired_field_minus_last_mse']['estimate']))
    rng=np.random.default_rng(20261022);boot=[rng.choice(dif,len(dif),replace=True).mean() for _ in range(2000)]
    check('Paired bootstrap interval',np.allclose(np.quantile(boot,[.025,.975]),out['paired_field_minus_last_mse']['interval95'],rtol=1e-10,atol=1e-11))
    selected=sorted((s for s in d if s['split']=='evaluation' and len(s['y'])>=5),key=lambda s:s['sequence'])[:2]
    check('Outcome-independent pilot selection',selected==read('pilot_selection.json'))
    sp=read('spatial_results.json')
    check('Spatial pilot count',sp['runs']==18 and len(sp['pilot_records'])==72)
    for r in sp['pilot_records']:
        s=selected[r['pilot']];A=M=0.;M=s['y'][0]
        kap=0. if r['run']=='no_source24' else p['kappa']
        for U in s['y'][:int(r['time'])]:M+=kap*(A+.5*(U-baseline));A+=U-baseline
        check('Spatial mass '+str(r['pilot'])+' '+r['run']+' '+str(r['time']),close(M,r['mass_exact']) and abs(M-r['mass'])<1e-10)
    check('Small discrete divergence',sp['max_divergence']<1e-10)
    check('Energy work-dissipation identity',sp['max_energy_identity_residual']<1e-10)
    check('Analytic vortex',sp['benchmarks']['taylor_green']['velocity_rms_error']<1e-8 and sp['benchmarks']['taylor_green']['pressure_rms_error']<1e-8)
    check('Time error decreases',all(a['velocity_rms_error']>b['velocity_rms_error'] for a,b in zip(sp['benchmarks']['taylor_green_time'],sp['benchmarks']['taylor_green_time'][1:])))
    check('Saved arrays finite',all(np.isfinite(v).all() for v in np.load(R/'fields.npz').values()))
    patterns=read('input_patterns.json');expected_patterns={}
    for seq in sorted(d,key=lambda x:x['sequence']):
        if seq['split']=='train' and len(seq['y'])>=5:expected_patterns.setdefault(tuple(seq['y'][:4]),seq['sequence'])
    check('Complete training-only input-pattern coverage',{tuple(r['pattern']):r['sequence'] for r in patterns['records']}==expected_patterns)
    check('Pattern mass and energy identities',all(abs(x['mass_error'])<1e-10 and abs(x['energy_identity_residual'])<1e-10 and x['divergence_rms']<1e-10 for r in patterns['records'] for x in r['diagnostics']))
    from run_spatial import l2_low_difference
    co=np.load(R/'final_coefficients.npz')
    for r in sp['refinement']:
        k='p'+str(r['pilot'])+'_'
        check('Full Fourier refinement '+k,close(r['n24_vs_n48'],l2_low_difference(co[k+'sharp24'],co[k+'sharp48'])) and close(r['n48_vs_n72'],l2_low_difference(co[k+'sharp48'],co[k+'sharp72'])) and close(r['n24_dt_vs_half'],l2_low_difference(co[k+'sharp24'],co[k+'sharp24_half_dt'])))
    print(json.dumps(dict(passed=len(checks),checks='Independent recurrence, fit, forecast, bootstrap, provenance and field identities'),indent=2))
if __name__=='__main__':main()
