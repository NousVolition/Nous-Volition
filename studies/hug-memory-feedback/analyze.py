import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
from model import Hug,protocol
ROOT=Path(__file__).resolve().parent
def load(cache,kind):
    p=cache/kind;return json.loads((p/'meta.json').read_text()),np.load(p/'time.npy'),np.load(p/'state.npy',mmap_mode='r')
def amplitude(t,q):
    a=np.empty_like(q)
    for i,x in enumerate(t):a[i]=np.ptp(q[np.searchsorted(t,x-57):i+1],axis=0)/2
    return a
def delay(t,ok,start):
    ii=np.flatnonzero((t>=start)&(t<=949.5));bad=ii[~ok[ii]];j=ii[0] if not len(bad) else bad[-1]+1
    return None if j>ii[-1] else float(t[j]-720)
def audit(p,meta,t,z):
    m=Hug(p,meta['nodes'],meta['rows']);S=z[:,:,7:7+m.n];amp=amplitude(t,z[:,:,0]*m.Q*1000)
    base=np.median(amp[(t>=350)&(t<=450)],axis=0);ot=np.arange(0,t[-1]+1e-8,p['orbit_period_s'])
    oi=np.searchsorted(t,np.round(ot,10));np.testing.assert_allclose(t[oi],ot,atol=1e-9)
    delta=np.abs(np.diff(z[oi,:,:4],axis=0)).max(axis=2);rep=np.full((len(ot),m.nr),np.nan)
    for i in range(10,len(ot)):rep[i]=delta[i-10:i].max(axis=0)
    w=z[:,:,-5:];net=w[:,:,0]+w[:,:,1]+w[:,:,2]-w[:,:,3]-w[:,:,4];E=m.energy(z);res=np.abs(E-E[0]-net+net[0]).max(axis=0)
    expected=np.zeros((len(t),3))
    for e in p['events']:expected[:,e['channel']]+=np.clip(t-e['start_s'],0,e['end_s']-e['start_s'])*e['rate_per_s']
    retained_error=float(np.max(np.abs(z[:,:,4:7]-expected[:,None,:])))
    summaries=[]
    for j,row in enumerate(m.rows):
        pause=m.scenarios[row['scenario']]['pause'];tail=t>=1600
        summaries.append(dict(**row,baseline_half_amplitude_mm=float(base[j]),tail_half_amplitude_mm=float(np.median(amp[tail,j])),minimum_braked_fraction=float(amp[(t>=600)&(t<=720),j].min()/base[j]),amplitude_confirmation_delay_s=delay(t,amp[:,j]>=.8*base[j],777) if pause else None,repeat_confirmation_delay_s=delay(ot,rep[:,j]<.01,782.7) if pause and row['condition'] else None,tail_repeat_error=None if row['condition']==0 else float(np.nanmax(rep[ot>=1700,j])),energy_residual_scaled=float(res[j]),max_abs_S=float(np.abs(S[:,j]).max())))
    comparisons=[]
    for c in range(3):
        for h in range(2):
            j=m.rows.index(dict(scenario='feedback',condition=c,history=h));k=m.rows.index(dict(scenario='frozen',condition=c,history=h));diff=S[:,j]-S[:,k];tail=t>=1600
            comparisons.append(dict(condition=c,history=h,max_field_difference=float(np.abs(diff).max()),tail_field_rms_difference=float(np.sqrt(np.mean(diff[tail]**2))),tail_field_relative_rms=float(np.sqrt(np.mean(diff[tail]**2)/np.mean(S[tail,k]**2))),max_field_mean_difference=float(np.abs(diff.mean(axis=1)).max()),max_displacement_difference_mm=float(np.abs(z[:,j,0]-z[:,k,0]).max()*m.Q*1000),new_amplitude_delay=summaries[j]['amplitude_confirmation_delay_s'],old_amplitude_delay=summaries[k]['amplitude_confirmation_delay_s'],new_repeat_delay=summaries[j]['repeat_confirmation_delay_s'],old_repeat_delay=summaries[k]['repeat_confirmation_delay_s']))
    checks=dict(all_finite=bool(np.isfinite(z).all()),retained_input_error=retained_error,max_energy_residual_scaled=float(res.max()),maximum_field=float(np.abs(S).max()),field_bound=m.bound(),maximum_physical_shear=float(np.abs(z[:,:,0]).max()*m.Q/m.L),maximum_mean_difference=float(np.max(np.abs(S.mean(axis=2)-S[:,0].mean(axis=1)[:,None]))),all_sources_match=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in meta['source_hashes'].items()))
    checks['passed']=bool(checks['all_finite'] and checks['all_sources_match'] and retained_error<1e-10 and res.max()<1e-5 and checks['maximum_field']<=m.bound() and checks['maximum_mean_difference']<1e-10)
    return m,summaries,comparisons,checks,amp,ot,rep
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache',required=True);args=ap.parse_args();cache=Path(args.cache);p=protocol();meta,t,z=load(cache,'main');m,summary,cmp,checks,amp,ot,rep=audit(p,meta,t,z)
    refinements={};provenance={'main':meta}
    for kind in ['fine','timefine','spatial']:
        if not (cache/kind/'meta.json').exists():continue
        mm,tt,zz=load(cache,kind);model,ss,cc,ch,aa,oo,rr=audit(p,mm,tt,zz);provenance[kind]=mm
        ids=[m.rows.index(x) for x in mm['rows']];SF=zz[:,:,7:7+model.n]
        projected=SF if model.n==m.n else SF.reshape(len(t),model.nr,m.n,model.n//m.n).mean(axis=3)
        contrast_errors=[]
        for c in range(3):
            for h in range(2):
                j=model.rows.index(dict(scenario='feedback',condition=c,history=h));k=model.rows.index(dict(scenario='frozen',condition=c,history=h));refdiff=projected[:,j]-projected[:,k];diff=z[:,ids[j],7:39]-z[:,ids[k],7:39]
                contrast_errors.append(dict(condition=c,history=h,max_field_contrast_difference=float(np.abs(refdiff-diff).max()),tail_rms_contrast_difference=float(np.sqrt(np.mean((refdiff[t>=1600]-diff[t>=1600])**2)))))
        item=dict(nodes=model.n,paths=model.nr,checks=ch,max_mechanical_difference=float(np.abs(zz[:,:,:4]-z[:,ids,:4]).max()),max_absolute_field_difference=float(np.abs(projected-z[:,ids,7:39]).max()),paired_field_refinement=contrast_errors,recovery_comparisons=[dict(row=x,main_amp=summary[ids[i]]['amplitude_confirmation_delay_s'],refined_amp=ss[i]['amplitude_confirmation_delay_s'],main_repeat=summary[ids[i]]['repeat_confirmation_delay_s'],refined_repeat=ss[i]['repeat_confirmation_delay_s']) for i,x in enumerate(mm['rows'])])
        if kind=='spatial':
            fm,ft,fz=load(cache,'fine');fj=[fm['rows'].index(x) for x in mm['rows']];project64=SF.reshape(len(t),model.nr,64,2).mean(axis=3);contrast=[]
            for c in range(3):
                for h in range(2):
                    j=model.rows.index(dict(scenario='feedback',condition=c,history=h));k=model.rows.index(dict(scenario='frozen',condition=c,history=h))
                    contrast.append(float(np.max(np.abs(project64[:,j]-project64[:,k]-fz[:,fj[j],7:71]+fz[:,fj[k],7:71]))))
            item['maximum_paired_field_difference_to_64']=max(contrast)
        refinements[kind]=item
    frozen_baseline_check=None;old=ROOT.parent.parent/'work/hug-memory-checked/main/states.npy'
    if old.exists():
        oldz=np.load(old,mmap_mode='r');frozen_baseline_check=dict(max_scaled_mechanical_difference=float(np.abs(z[:,6:12,:4]-oldz[:,:6,:4]).max()),max_field_difference=float(np.abs(z[:,6:12,7:39]-oldz[:,:6,7:39]).max()),reference='Previous retained-history main cache; independent rerun of its fixed operators')
    controls=dict(gradient_only_max_field_change=float(np.abs(z[:,18:24,7:39]-z[:,6:12,7:39]).max()),diffusion_only_max_field_change=float(np.abs(z[:,12:18,7:39]-z[:,6:12,7:39]).max()),full_vs_gradient_only_displacement_mm=float(np.abs(z[:,:6,0]-z[:,18:24,0]).max()*m.Q*1000),full_vs_diffusion_only_displacement_mm=float(np.abs(z[:,:6,0]-z[:,12:18,0]).max()*m.Q*1000))
    result=dict(status='Synthetic model test',main_paths=len(summary),refinement_paths=sum(x['paths'] for x in refinements.values()),physical_measurements=0,human_measurements=0,checks=checks,comparisons=cmp,paths=summary,refinements=refinements,controls=controls,frozen_baseline_check=frozen_baseline_check,data_precision={'mechanics_work_inputs':'float64','primary_field_display':'frozen field float32 plus paired difference computed in float64 then stored as float32; comparison metrics above precede quantization'},note='Bounded source and relaxation remain the prior declared extensions. A and event provenance are never reset. Field redistribution is conservative; source/relaxation can change its mean. Display exaggeration never enters equations.')
    (ROOT/'results.json').write_bytes((json.dumps(result,indent=2,allow_nan=False)+'\n').encode());(ROOT/'run_provenance.json').write_bytes((json.dumps(provenance,indent=2)+'\n').encode())
    with (ROOT/'summary.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
    np.savez_compressed(ROOT/'plot_data.npz',time=t,mechanics=z[:,:,:4],work=z[:,:,-5:],A=z[:,0,4:7],field_mean=z[:,:,7:39].mean(axis=2),field_frozen=z[:,6:12,7:39].astype(np.float32),field_delta=(z[:,:6,7:39]-z[:,6:12,7:39]).astype(np.float32),amplitude=amp,orbital_time=ot,repeat=rep)
    print(json.dumps(dict(checks=checks,comparisons=cmp,refinements={k:{x:y for x,y in v.items() if x not in ['recovery_comparisons','paired_field_refinement']} for k,v in refinements.items()},baseline=frozen_baseline_check),indent=2))
if __name__=='__main__':main()
