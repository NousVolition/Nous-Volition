"""Predeclared paired rhythm metrics; all measured before display rounding."""
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicHermiteSpline
from model import ROOT,Hug,configured,protocol

def amplitude(t,q):
    return np.stack([np.ptp(q[np.searchsorted(t,x-57):i+1],axis=0)/2 for i,x in enumerate(t)])

def confirmation(t,ok,start):
    ids=np.flatnonzero((t>=start)&(t<=949.5));bad=ids[~ok[ids]]
    j=ids[0] if not len(bad) else bad[-1]+1
    return None if j>ids[-1] else float(t[j]-720)

def cycle_period(t,q,v):
    mask=(t>=1600)&(t<=1800);tt=t[mask];yy=q[mask]-np.mean(q[mask]);vv=v[mask]
    spline=CubicHermiteSpline(tt,yy,vv);roots=spline.roots(extrapolate=False)
    roots=roots[(roots>=tt[0])&(roots<=tt[-1])];roots=roots[spline(roots,1)>0]
    if len(roots)<3:return None
    return float((roots[-1]-roots[0])/(len(roots)-1))

def audit(meta,t,z):
    scale=meta['scale'];p=configured(scale,meta['orbit_policy']);m=Hug(p,meta['nodes'],meta['rows']);S=z[:,:,7:7+m.n];amp=amplitude(t,z[:,:,0]*m.Q*1000)
    base=np.median(amp[(t>=350)&(t<=450)],axis=0);tail=t>=1600
    ot=np.round(np.arange(0,t[-1]+1e-8,p['orbit_period_s']),10);oi=np.searchsorted(t,ot)
    np.testing.assert_allclose(t[oi],ot,atol=1e-9)
    dx=np.abs(np.diff(z[oi,:,:4],axis=0)/scale).max(axis=2);rep=np.full((len(ot),m.nr),np.nan)
    for i in range(10,len(ot)):rep[i]=dx[i-10:i].max(axis=0)
    w=z[:,:,-5:];net=w[:,:,0]+w[:,:,1]+w[:,:,2]-w[:,:,3]-w[:,:,4];E=m.energy(z)
    res=np.abs(E-E[0]-net+net[0]).max(axis=0)/scale**2
    expected=np.zeros((len(t),3))
    for e in p['events']:expected[:,e['channel']]+=np.clip(t-e['start_s'],0,e['end_s']-e['start_s'])*e['rate_per_s']
    paths=[]
    for j,row in enumerate(m.rows):
        paths.append(dict(**row,baseline_half_amplitude_mm=float(base[j]),late_half_amplitude_mm=float(np.median(amp[tail,j])),period_s=cycle_period(t,z[:,j,0],z[:,j,1]),max_shear=float(np.abs(z[:,j,0]).max()*m.Q/m.L),minimum_braked_fraction=float(amp[(t>=600)&(t<=720),j].min()/base[j]),amplitude_delay_s=confirmation(t,amp[:,j]>=.8*base[j],777),repeat_delay_s=confirmation(ot,rep[:,j]<.01,782.7) if row['condition'] else None,late_repeat_error=float(np.max(rep[ot>=1700,j])) if row['condition'] else None,late_repeats=bool(np.max(rep[ot>=1700,j])<.01) if row['condition'] else None,energy_residual_per_scale_squared=float(res[j])))
    pairs=[]
    for j in range(6):
        k=j+6;new=paths[j];old=paths[k];period=old['period_s'];omega=2*np.pi/period if period else 1
        phase1=np.arctan2(-z[tail,j,1]/omega,z[tail,j,0]-z[tail,j,0].mean())
        phase0=np.arctan2(-z[tail,k,1]/omega,z[tail,k,0]-z[tail,k,0].mean())
        phase=np.angle(np.exp(1j*(phase1-phase0)))/(2*np.pi)
        delta=S[:,j]-S[:,k]
        def dd(key):return None if new[key] is None or old[key] is None else new[key]-old[key]
        relative_amp=(new['late_half_amplitude_mm']-old['late_half_amplitude_mm'])/old['late_half_amplitude_mm']
        relative_period=None if not period or new['period_s'] is None else (new['period_s']-period)/period
        flags=[];criteria=p['sweep']['effect_criteria']
        if abs(relative_amp)>=criteria['relative_amplitude']:flags.append('amplitude')
        if relative_period is None:flags.append('period_unresolved')
        elif abs(relative_period)>=criteria['relative_period']:flags.append('period')
        if np.abs(phase).max()>=criteria['phase_cycles']:flags.append('phase_offset')
        for key in ['amplitude_delay_s','repeat_delay_s']:
            if (new[key] is None)!=(old[key] is None) or (dd(key) is not None and abs(dd(key))>=criteria['recovery_delay_s']-1e-8):flags.append(key)
        if new['late_repeats']!=old['late_repeats']:flags.append('orbit_repeat')
        pairs.append(dict(condition=j//2,history=j%2,relative_amplitude_change=float(relative_amp),relative_period_change=relative_period,max_phase_offset_cycles=float(np.abs(phase).max()),amplitude_delay_change_s=dd('amplitude_delay_s'),repeat_delay_change_s=dd('repeat_delay_s'),flags=flags,max_field_difference=float(np.abs(delta).max()),late_field_rms_difference=float(np.sqrt(np.mean(delta[tail]**2))),late_field_relative_rms=float(np.sqrt(np.mean(delta[tail]**2)/np.mean(S[tail,k]**2))),max_mean_difference=float(np.abs(delta.mean(axis=1)).max()),max_displacement_difference_mm=float(np.abs(z[:,j,0]-z[:,k,0]).max()*m.Q*1000)))
    checks=dict(finite=bool(np.isfinite(z).all()),retained_error=float(np.abs(z[:,:,4:7]-expected[:,None,:]).max()),max_energy_residual=float(res.max()),max_field=float(np.abs(S).max()),field_bound=m.bound(),max_mean_difference=float(np.abs(S.mean(axis=2)-S[:,0,:].mean(axis=1)[:,None]).max()),source_hashes_match=all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==sha for f,sha in meta['source_hashes'].items()))
    checks['passed']=bool(checks['finite'] and checks['retained_error']<1e-10 and checks['max_energy_residual']<1e-5 and checks['max_field']<checks['field_bound'] and checks['max_mean_difference']<1e-10 and checks['source_hashes_match'])
    return dict(paths=paths,pairs=pairs,checks=checks),amp,ot,rep

def load(folder):
    return json.loads((folder/'meta.json').read_text()),np.load(folder/'time.npy'),np.load(folder/'state.npy',mmap_mode='r')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache',required=True);args=ap.parse_args();cache=Path(args.cache)
    results=[];provenance={};out=ROOT/'data';out.mkdir(exist_ok=True)
    for policy,scales in [('scaled',protocol()['sweep']['scales']),('fixed',protocol()['sweep']['fixed_orbit_scales'])]:
        for scale in scales:
            folder=cache/policy/str(scale);meta,t,z=load(folder/'main');r,amp,ot,rep=audit(meta,t,z);r.update(scale=scale,orbit_policy=policy,refinements={});provenance[f'{policy}/{scale}/main']=meta
            for kind in ['fine','timefine','spatial']:
                if not (folder/kind/'meta.json').exists():continue
                rm,rt,rz=load(folder/kind);rr,_,_,_=audit(rm,rt,rz);provenance[f'{policy}/{scale}/{kind}']=rm
                n=rm['nodes'];SF=rz[:,:,7:7+n];proj=SF if n==32 else SF.reshape(len(t),12,32,n//32).mean(axis=3)
                field_err=float(np.abs((proj[:,:6]-proj[:,6:])-(z[:,:6,7:39]-z[:,6:,7:39])).max())
                r['refinements'][kind]=dict(nodes=n,checks=rr['checks'],pairs=rr['pairs'],paths=rr['paths'],max_paired_field_error=field_err,max_mechanics_error_per_scale=float(np.abs(rz[:,:,:4]-z[:,:,:4]).max()/scale),max_paired_mechanics_error_per_scale=float(np.abs((rz[:,:6,:4]-rz[:,6:,:4])-(z[:,:6,:4]-z[:,6:,:4])).max()/scale),screen_agrees=all(x['flags']==y['flags'] for x,y in zip(r['pairs'],rr['pairs'])))
                if kind=='spatial' and (folder/'fine/meta.json').exists():
                    _,_,fz=load(folder/'fine');p64=SF.reshape(len(t),12,64,2).mean(axis=3)
                    r['refinements'][kind]['paired_field_error_to_64']=float(np.abs(p64[:,:6]-p64[:,6:]-fz[:,:6,7:71]+fz[:,6:,7:71]).max())
            # Store mechanics/work for all starts and fields for start 1, all conditions.
            ids=[0,2,4];np.savez_compressed(out/f'{policy}-{scale}.npz',time=t,mechanics=z[:,:,:4],work=z[:,:,-5:],A=z[:,0,4:7],field_mean=z[:,:,7:39].mean(axis=2),field_frozen=z[:,[j+6 for j in ids],7:39].astype(np.float32),field_delta=(z[:,ids,7:39]-z[:,[j+6 for j in ids],7:39]).astype(np.float32),amplitude=amp,orbital_time=ot,repeat=rep)
            results.append(r);print(json.dumps(dict(scale=scale,policy=policy,passed=r['checks']['passed'],flags=[x['flags'] for x in r['pairs']],max_shear=max(x['max_shear'] for x in r['paths']),amp=max(abs(x['relative_amplitude_change']) for x in r['pairs']),period=max(abs(x['relative_period_change']) for x in r['pairs']))),flush=True)
    result=dict(status='Synthetic reduced-model stress test',physical_measurements=0,studies=results,main_paths=12*len(results),refinement_paths=12*sum(len(x['refinements']) for x in results),all_checks_pass=all(x['checks']['passed'] and all(y['checks']['passed'] and y['screen_agrees'] for y in x['refinements'].values()) for x in results))
    (ROOT/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8');(ROOT/'run_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    with (ROOT/'summary.csv').open('w',newline='',encoding='utf-8') as f:
        records=[dict(scale=r['scale'],orbit_policy=r['orbit_policy'],**{**x,'flags':';'.join(x['flags'])}) for r in results for x in r['pairs']];w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
if __name__=='__main__':main()
