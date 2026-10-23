"""Recompute published mechanical outcomes and field contrasts from saved data."""
import hashlib,json
import numpy as np
from model import ROOT,Hug,configured,protocol
from analyze import audit

def main():
    result=json.loads((ROOT/'results.json').read_text());prov=json.loads((ROOT/'run_provenance.json').read_text())
    assert result['main_paths']==96 and result['all_checks_pass']
    assert len(result['studies'])==8
    for run in prov.values():
        for f,sha in run['source_hashes'].items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==sha,f
    count=0
    for r in result['studies']:
        key=f"{r['orbit_policy']}/{r['scale']}/main";meta=prov[key];d=np.load(ROOT/'data'/f"{r['orbit_policy']}-{r['scale']}.npz");t=d['time']
        m=Hug(configured(r['scale'],r['orbit_policy']),32);z=np.zeros((len(t),12,m.width));z[:,:,:4]=d['mechanics'];z[:,:,-5:]=d['work'];z[:,:,4:7]=d['A'][:,None,:]
        # Fields for the first start only are published. Full-cache audits cover both.
        # Unpublished patterns get their saved mean here; no spatial claims use them.
        z[:,:,7:39]=d['field_mean'][:,:,None]
        for c,j in enumerate([0,2,4]):z[:,j+6,7:39]=d['field_frozen'][:,c];z[:,j,7:39]=d['field_frozen'][:,c].astype(float)+d['field_delta'][:,c]
        calculated,amp,ot,rep=audit(meta,t,z)
        for key in d.files:
            if key!='repeat':assert np.isfinite(d[key]).all(),key
        assert np.all(np.diff(t)>0)
        np.testing.assert_allclose(amp,d['amplitude'],atol=1e-12);np.testing.assert_allclose(rep,d['repeat'],equal_nan=True)
        for j,path in enumerate(r['paths']):
            got=calculated['paths'][j]
            for name,value in path.items():
                if isinstance(value,float):np.testing.assert_allclose(got[name],value,rtol=1e-12,atol=1e-12)
                else:assert got[name]==value,(name,got[name],value)
            count+=1
        expected=np.zeros_like(d['A'])
        for e in protocol()['events']:expected[:,e['channel']]+=np.clip(t-e['start_s'],0,e['end_s']-e['start_s'])*e['rate_per_s']
        np.testing.assert_allclose(d['A'],expected,atol=1e-12,rtol=0)
        assert np.diff(d['work'][:,:,3:],axis=0).min()>-1e-9*r['scale']**2
        assert np.abs(d['field_mean']-d['field_mean'][:,0,None]).max()<1e-10
        assert np.abs(d['field_delta'].astype(float).mean(axis=2)).max()<1e-9
        assert np.abs(d['field_frozen']+d['field_delta']).max()<m.bound()
        for j in range(6):
            a=calculated['pairs'][j];b=r['pairs'][j]
            for name in ['relative_amplitude_change','relative_period_change','max_phase_offset_cycles','amplitude_delay_change_s','repeat_delay_change_s','flags','max_displacement_difference_mm']:assert a[name]==b[name],(name,j)
            if j%2==0:
                for name in ['max_field_difference','late_field_rms_difference','late_field_relative_rms']:np.testing.assert_allclose(a[name],b[name],rtol=5e-7,atol=2e-12)
        assert set(r['refinements'])>=({'fine','timefine'} if r['orbit_policy']=='scaled' else {'fine','spatial'})
        for ref in r['refinements'].values():assert ref['checks']['passed'] and ref['screen_agrees']
        if r['scale']==300 or any(x['flags'] for x in r['pairs']):assert 'spatial' in r['refinements']
    print(json.dumps(dict(passed=True,paths_recomputed=count,refinement_paths=result['refinement_paths'],scope='Saved mechanics, energy, inputs, primary-start field differences and recorded refinement audits; no measured clay validation'),indent=2))
if __name__=='__main__':main()
