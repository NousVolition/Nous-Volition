import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.signal import find_peaks
from model import Hug,protocol,exposure_weights
ROOT=Path(__file__).resolve().parent
def load(cache,kind):
    f=cache/kind;meta=json.loads((f/'meta.json').read_text());return meta,np.load(f/'times.npy'),np.load(f/'states.npy',mmap_mode='r')
def amplitudes(t,q,window):
    out=np.empty_like(q)
    for i,x in enumerate(t):
        a=np.searchsorted(t,x-window);part=q[a:i+1];out[i]=(part.max(axis=0)-part.min(axis=0))/2
    return out
def sustained(t,ok,lower,upper):
    idx=np.where((t>=lower)&(t<=upper))[0]
    if len(idx)==0:return None
    bad=idx[~ok[idx]];start=idx[0] if len(bad)==0 else bad[-1]+1
    return None if start>idx[-1] else float(t[start]-720)
def summarize(p,m,t,z):
    amp=amplitudes(t,z[:,:,0]*m.Q*1000,p['diagnostics']['window_s']);base=np.median(amp[(t>=350)&(t<=450)],axis=0)
    out=[];diag=[];P=p['orbit_period_s'];orbitt=np.arange(0,t[-1]+1e-8,P)
    orbital=z[np.searchsorted(t,np.round(orbitt,10)),:,:4]
    difference=np.max(np.abs(np.diff(orbital,axis=0)),axis=2)
    repeat=np.full((len(orbitt),m.nr),np.nan);win=p['diagnostics']['repeat_window_orbits']
    for i in range(win,len(orbitt)):
        repeat[i]=np.max(difference[i-win:i],axis=0)
    for j,row in enumerate(m.rows):
        s=m.scenarios[row['scenario']];recovery=sustained(t,amp[:,j]>=.8*base[j],777,949.5) if s['pause'] else None
        repeat_recovery=None
        if row['condition']!=0 and s['pause']:
            repeat_recovery=sustained(orbitt,repeat[:,j]<p['diagnostics']['repeat_tolerance_scaled'],720+(win+1)*P,949.5)
        tail=(t>=1600);peaks,_=find_peaks(z[tail,j,0],prominence=max(base[j]/(m.Q*1000)*.3,1e-6),distance=int(2/p['sample_s']))
        periods=np.diff(t[tail][peaks]);energy=m.energy(z[:,j])
        work=z[:,j,-5]+z[:,j,-4]+z[:,j,-3]-z[:,j,-2]-z[:,j,-1]
        residual=np.max(np.abs(energy-energy[0]-work+work[0]))
        item={**row,'baseline_half_amplitude_mm':float(base[j]),'braked_min_fraction':float(np.min(amp[(t>=600)&(t<=720),j])/base[j]),'amplitude_recovery_delay_s':recovery,'mechanical_repeat_confirmation_delay_s':repeat_recovery,'tail_half_amplitude_mm':float(np.median(amp[tail,j])),'tail_period_s':float(np.median(periods)) if len(periods) else None,'tail_period_range_s':float(np.ptp(periods)) if len(periods) else None,'tail_repeat_error_scaled':None if row['condition']==0 else float(np.nanmax(repeat[orbitt>=1700,j])),'energy_residual_scaled':float(residual),'max_abs_S':float(np.max(np.abs(z[:,j,7:7+m.n]))),'A_at_pause_end':z[np.searchsorted(t,719.5),j,4:7].tolist(),'A_final':z[-1,j,4:7].tolist(),'S_rms_final':float(np.sqrt(np.mean(z[-1,j,7:7+m.n]**2))),'incoming_weights':exposure_weights(s).tolist()}
        out.append(item)
    return out,amp,orbitt,repeat
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache',required=True);a=ap.parse_args();cache=Path(a.cache);p=protocol();meta,t,z=load(cache,'main');m=Hug(p,meta['nodes'],meta['rows']);result,amp,ot,rep=summarize(p,m,t,z)
    checks={};expected=np.zeros((len(t),3))
    for e in p['events']:expected[:,e['channel']]+=np.clip(t-e['start_s'],0,e['end_s']-e['start_s'])*e['rate_per_s']
    retained=[i for i,r in enumerate(m.rows) if not m.scenarios[r['scenario']]['erase']]
    checks['retained_accumulator_max_error']=float(np.max(np.abs(z[:,retained,4:7]-expected[:,None,:])))
    checks['maximum_energy_residual_scaled']=max(x['energy_residual_scaled'] for x in result)
    checks['maximum_field_magnitude']=max(x['max_abs_S'] for x in result);checks['field_bound']=m.bound()
    checks['all_finite']=bool(np.isfinite(z).all());checks['ledger_sha256']=meta['ledger_sha256'];checks['model_source_hash_matches']=meta['source_hashes']['model.py']==hashlib.sha256((ROOT/'model.py').read_bytes()).hexdigest()
    refinements={}
    for kind in ['fine','timefine','spatial']:
        if not (cache/kind/'meta.json').exists():continue
        mm,tt,zz=load(cache,kind);model=Hug(p,mm['nodes'],mm['rows']);rr,aa,oo,rp=summarize(p,model,tt,zz)
        matches=[m.rows.index(r) for r in mm['rows']];basez=z[:,matches]
        field=zz[:,:,7:7+model.n]
        if model.n==m.n:projected=field
        else:projected=field.reshape(len(t),len(matches),m.n,model.n//m.n).mean(axis=3)
        item={'paths':len(matches),'nodes':model.n,'max_scaled_mechanical_path_difference':float(np.max(np.abs(zz[:,:,:4]-basez[:,:,:4]))),'max_field_difference_to_main_cells':float(np.max(np.abs(projected-basez[:,:,7:7+m.n]))),'max_amplitude_difference_mm':float(np.max(np.abs(aa-amp[:,matches]))),'max_energy_residual_scaled':max(x['energy_residual_scaled'] for x in rr),'recovery_comparisons':[]}
        for i,j in enumerate(matches):
            item['recovery_comparisons'].append(dict(row=m.rows[j],main_amplitude_delay=result[j]['amplitude_recovery_delay_s'],refined_amplitude_delay=rr[i]['amplitude_recovery_delay_s'],main_repeat_delay=result[j]['mechanical_repeat_confirmation_delay_s'],refined_repeat_delay=rr[i]['mechanical_repeat_confirmation_delay_s']))
        if kind=='spatial' and (cache/'fine/meta.json').exists():
            fm,ft,fz=load(cache,'fine');fj=[fm['rows'].index(r) for r in mm['rows']]
            item['max_field_difference_to_64']=float(np.max(np.abs(field.reshape(len(t),len(matches),64,2).mean(axis=3)-fz[:,fj,7:71])))
            item['max_mechanical_difference_to_64']=float(np.max(np.abs(zz[:,:,:4]-fz[:,fj,:4])))
        refinements[kind]=item
    checks['passed']=bool(checks['all_finite'] and checks['model_source_hash_matches'] and checks['retained_accumulator_max_error']<1e-9 and checks['maximum_energy_residual_scaled']<1e-5 and checks['maximum_field_magnitude']<=checks['field_bound']+1e-10)
    summary=dict(protocol_version=p['version'],paths=len(m.rows),nodes=m.n,physical_measurements=0,human_measurements=0,checks=checks,refinements=refinements,results=result,diagnostic_note='Mechanical repeat uses exact orbital checkpoints, one-orbit lag, ten comparisons and scaled tolerance .01; not the earlier full-state four-lag test. Amplitude recoveries confirmed only through 949.5 s before a separate reminder. No claim of human/genetic calibration.')
    (ROOT/'results.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    with (ROOT/'summary.csv').open('w',newline='',encoding='utf-8') as f:
        keys=[k for k,v in result[0].items() if not isinstance(v,list)];w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(result)
    np.savez_compressed(ROOT/'plot_data.npz',time=t,mechanics=z[:,:,:4],accumulators=z[:,:,4:7],field_rms=np.sqrt(np.mean(z[:,:,7:7+m.n]**2,axis=2)),amplitude=amp,orbital_time=ot,repeat=rep,field_time=t[::4],fields=z[::4,::6,7:7+m.n],work=z[:,:,-5:])
    print(json.dumps(dict(checks=checks,refinements={k:{n:v for n,v in x.items() if n!='recovery_comparisons'} for k,x in refinements.items()},retained=[x for x in result if x['scenario']=='retained' and x['history']==0]),indent=2))
if __name__=='__main__':main()
