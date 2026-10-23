"""Verify published paths, effects and diagnostics without a simulation rerun."""
import hashlib,json
from pathlib import Path
import numpy as np
from model import Hug,protocol
ROOT=Path(__file__).resolve().parent
def main():
    p=protocol();m=Hug(p,32);r=json.loads((ROOT/'results.json').read_text());d=np.load(ROOT/'plot_data.npz');prov=json.loads((ROOT/'run_provenance.json').read_text())
    assert r['main_paths']==30 and r['refinement_paths']==72
    for run in prov.values():
        for f,sha in run['source_hashes'].items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==sha,f
    t=d['time'];z=d['mechanics'];assert z.shape==(3853,30,4) and np.all(np.diff(t)>0)
    for key in d.files:
        if key!='repeat':assert np.isfinite(d[key]).all(),key
    expected=np.zeros_like(d['A'])
    for e in p['events']:expected[:,e['channel']]+=np.clip(t-e['start_s'],0,e['end_s']-e['start_s'])*e['rate_per_s']
    np.testing.assert_allclose(d['A'],expected,atol=1e-12,rtol=0)
    assert all(not x['erase'] for x in p['scenarios'])
    assert r['checks']['passed'] and all(v['checks']['passed'] for v in r['refinements'].values())
    E=m.energy(z);w=d['work'];net=w[:,:,0]+w[:,:,1]+w[:,:,2]-w[:,:,3]-w[:,:,4]
    residual=np.abs(E-E[0]-net+net[0]).max(axis=0)
    np.testing.assert_allclose(residual,[x['energy_residual_scaled'] for x in r['paths']],atol=1e-11,rtol=0)
    assert residual.max()<1e-5 and np.diff(w[:,:,3:],axis=0).min()>-1e-10
    amp=np.stack([np.ptp(z[(t>=x-57)&(t<=x),:,0],axis=0)*m.Q*500 for x in t])
    np.testing.assert_allclose(amp,d['amplitude'],atol=1e-12)
    baseline=np.median(amp[(t>=350)&(t<=450)],axis=0)
    ot=d['orbital_time'];ii=np.searchsorted(t,np.round(ot,10));np.testing.assert_allclose(t[ii],ot,atol=1e-9)
    dx=np.abs(np.diff(z[ii],axis=0)).max(axis=2);repeat=np.full(d['repeat'].shape,np.nan)
    for i in range(10,len(ot)):repeat[i]=dx[i-10:i].max(axis=0)
    np.testing.assert_allclose(repeat,d['repeat'],equal_nan=True)
    def confirmed(time,ok,start):
        idx=np.flatnonzero((time>=start)&(time<=949.5));bad=idx[~ok[idx]];j=idx[0] if not len(bad) else bad[-1]+1
        return None if j>idx[-1] else float(time[j]-720)
    for j,row in enumerate(r['paths']):
        assert row['scenario']==m.rows[j]['scenario']
        assert row['condition']==m.rows[j]['condition'] and row['history']==m.rows[j]['history']
        np.testing.assert_allclose(row['baseline_half_amplitude_mm'],baseline[j],atol=1e-12)
        pause=m.has_pause[j]
        assert row['amplitude_confirmation_delay_s']==(confirmed(t,amp[:,j]>=.8*baseline[j],777) if pause else None)
        assert row['repeat_confirmation_delay_s']==(confirmed(ot,repeat[:,j]<.01,782.7) if pause and row['condition'] else None)
    delta=d['field_delta'].astype(float);old=d['field_frozen'].astype(float);new=old+delta
    assert np.abs(new).max()<m.bound()
    assert np.abs(delta.mean(axis=2)).max()<1e-12
    assert np.abs(d['field_mean']-d['field_mean'][:,0,None]).max()<1e-10
    tail=t>=1600
    for j,c in enumerate(r['comparisons']):
        assert c['condition']==j//2 and c['history']==j%2
        np.testing.assert_allclose(np.abs(delta[:,j]).max(),c['max_field_difference'],rtol=2e-7)
        np.testing.assert_allclose(np.sqrt(np.mean(delta[tail,j]**2)),c['tail_field_rms_difference'],rtol=2e-7)
        np.testing.assert_allclose(np.max(np.abs(z[:,j,0]-z[:,j+6,0]))*m.Q*1000,c['max_displacement_difference_mm'],rtol=1e-12)
        assert c['max_field_difference']>1e-7,'must resolve a nonzero spatial change'
    assert r['controls']['gradient_only_max_field_change']<1e-12
    assert r['controls']['diffusion_only_max_field_change']>1e-7
    assert r['frozen_baseline_check']['max_scaled_mechanical_difference']<1e-5
    assert r['refinements']['timefine']['max_mechanical_difference']<1e-5
    assert r['refinements']['spatial']['maximum_paired_field_difference_to_64']<max(x['max_field_contrast_difference'] for x in r['refinements']['fine']['paired_field_refinement'])
    print(json.dumps(dict(passed=True,main_paths=30,refinement_paths=72,samples=len(t),scope='Saved provenance, retained input, energy, spatial contrasts, field means, amplitude and mechanical-repeat diagnostics; no empirical validation'),indent=2))
if __name__=='__main__':main()
