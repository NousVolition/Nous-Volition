"""Reproduce figures and summaries from saved energies, frames and flow slices.

No experimental values enter simulation forces or fitted material parameters.
Run after all numerical cases. --partial permits interim inspection only.
"""
from pathlib import Path
import argparse, csv, json, hashlib, sys
import numpy as np
from scipy.special import logsumexp
from scipy.optimize import curve_fit, brentq
from scipy.stats import t as student_t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

P=Path(__file__).resolve().parent
# Always prefer the bundled frozen classifier, even if its sibling later changes.
topology_dir=P/'topology'
if not (topology_dir/'water_topology.py').is_file():
    topology_dir=P.parent/'large_raindrop_tests/interface_topology'
sys.path.insert(0,str(topology_dir))
from water_topology import hydrogen_bonds, classify

RT=.008314462618*298.15
CONVERT=1.660539067  # kJ/mol/nm^2 -> mN/m
PRIMARY=['primary_seed101','primary_seed202','primary_seed303']
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                     'figure.dpi':150,'savefig.bbox':'tight'})


def save_csv(path,rows):
    if not rows:return
    with Path(path).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def gamma(rows,area,strain=.001):
    minus,plus=('U_minus001','U_plus001') if strain==.001 else ('U_minus002','U_plus002')
    def free(key):
        du=rows[key]-rows['U_zero']
        return -RT*(logsumexp(-du/RT)-np.log(len(du)))
    # dF/dA=2 gamma for two interfaces; central difference denominator 2*A*strain.
    return (free(plus)-free(minus))/(4*area*strain)*CONVERT


def load_water(folder):
    meta=json.loads((folder/'metadata.json').read_text())
    rows=np.genfromtxt(folder/'samples.csv',delimiter=',',names=True)
    sampled=folder/'analysis_frames.npz'
    if not sampled.exists():
        full=np.load(folder/'trajectory.npz');idx=np.arange(0,len(full['xyz_nm']),20)
        np.savez_compressed(sampled,xyz_nm=full['xyz_nm'][idx],box_nm=full['box_nm'],
                            original_frame_indices=idx)
    raw=np.load(sampled)
    return meta,rows,raw['xyz_nm']


def centered_z(xyz,box):
    z=xyz[:,0,2];angle=2*np.pi*z/box[2]
    center=np.angle(np.mean(np.exp(1j*angle)))*box[2]/(2*np.pi)
    return (z-center+box[2]/2)%box[2]-box[2]/2


def density_model(z,rho,half,width):
    return .5*rho*(np.tanh((z+half)/width)-np.tanh((z-half)/width))


def water_analysis(partial=False):
    summary=[];blocks=[];profiles=[];structures=[];all_layer=[]
    fig,axs=plt.subplots(2,2,figsize=(11,8),layout='constrained')
    examples=None
    for folder in sorted((P/'water').iterdir()):
        if not folder.is_dir() or folder.name.endswith('_extension') or not (folder/'metadata.json').exists():continue
        meta,rows,frames=load_water(folder)
        extension=folder.with_name(folder.name+'_extension')
        if (extension/'metadata.json').exists():
            ext_meta,er,ef=load_water(extension)
            er=er.copy();er['time_ps']+=rows['time_ps'][-1]
            rows=np.concatenate([rows,er]);frames=np.concatenate([frames,ef])
        if not partial and folder.name in PRIMARY and len(rows)!=1000:
            raise RuntimeError('Primary extension incomplete: '+folder.name)
        box=np.array(meta['box_nm']);area=box[0]*box[1]
        result=dict(name=folder.name,seed=meta['seed'],N=meta['N'],production_ps=len(rows),
                    lateral_nm=box[0],dt_fs=meta['dt_ps']*1000,
                    mean_temperature_K=float(rows['temperature_K'].mean()),
                    gamma_mN_m=gamma(rows,area),gamma_strain002_mN_m=gamma(rows,area,.002),
                    gamma_first300_mN_m=gamma(rows[:300],area),
                    gamma_first_half_mN_m=gamma(rows[:len(rows)//2],area),
                    gamma_last_half_mN_m=gamma(rows[len(rows)//2:],area))
        for block in (50,100,200):
            vals=[]
            for start in range(0,len(rows)-block+1,block):
                value=gamma(rows[start:start+block],area);vals.append(value)
                blocks.append(dict(name=folder.name,block_ps=block,start_ps=start,
                                   gamma_mN_m=value))
            result[f'block{block}_SD_mN_m']=float(np.std(vals,ddof=1)) if len(vals)>1 else None
        summary.append(result)
        if folder.name in PRIMARY:
            vals=[r for r in blocks if r['name']==folder.name and r['block_ps']==100]
            axs[0,0].plot([r['start_ps']+50 for r in vals],[r['gamma_mN_m'] for r in vals],'o-',label=folder.name.replace('primary_',''))
        bins=np.linspace(-4,4,161);centers=.5*(bins[1:]+bins[:-1])
        zs=np.array([centered_z(f,box) for f in frames])
        hist=np.histogram(zs,bins)[0]/len(frames)
        density=hist/(area*np.diff(bins))*18.015324/602.214076
        params,_=curve_fit(density_model,centers,density,p0=[1,1.2,.2],bounds=([.5,.5,.03],[1.5,2.5,1]))
        result.update(fitted_bulk_density_g_cm3=float(params[0]),half_density_depth_nm=float(params[1]),density_width_nm=float(params[2]),topology_frames=len(frames))
        for z,d in zip(centers,density):profiles.append(dict(name=folder.name,z_nm=z,density_g_cm3=d))
        if folder.name in PRIMARY:axs[0,1].plot(centers,density,label=folder.name.replace('primary_',''))
        layer_counts={k:np.zeros(3,dtype=int) for k in ['bulk','interface','other']}
        psi_bins=np.linspace(2,12,51);psi_hist=np.zeros(50,dtype=int)
        # Whole periodic network is built before selecting planar layers.
        for fi,(frame,zs_frame) in enumerate(zip(frames,zs)):
            oxygen=frame[:,0]*10;hydrogens=frame[:,1:]*10
            edges=hydrogen_bonds(oxygen,hydrogens,box*10,(True,True,True))
            records=classify(oxygen,edges,box*10,(True,True,True))
            labels=np.array([r['label'] for r in records])
            psi=np.array([r['psi_A'] if r['psi_A'] is not None else np.nan for r in records])
            masks={'bulk':np.abs(zs_frame)<.5,
                   'interface':np.abs(np.abs(zs_frame)-params[1])<.25}
            masks['other']=~(masks['bulk']|masks['interface'])
            for layer,mask in masks.items():
                counts=np.array([np.sum(labels[mask]==v) for v in ['HDL-like','LDL-like','unclassified']])
                layer_counts[layer]+=counts
                all_layer.append(dict(name=folder.name,frame=fi,layer=layer,HDL=int(counts[0]),LDL=int(counts[1]),unclassified=int(counts[2])))
            psi_hist+=np.histogram(psi[np.isfinite(psi)],psi_bins)[0]
            if folder.name=='primary_seed101' and fi==len(frames)//2:examples=(frame,zs_frame,psi,box)
        for layer,counts in layer_counts.items():
            structures.append(dict(name=folder.name,layer=layer,HDL=int(counts[0]),LDL=int(counts[1]),unclassified=int(counts[2]),
                coverage=float(sum(counts[:2])/sum(counts)),HDL_fraction_classified=float(counts[0]/sum(counts[:2]))))
        if folder.name in PRIMARY:
            axs[1,0].plot(.5*(psi_bins[1:]+psi_bins[:-1]),psi_hist/psi_hist.sum(),label=folder.name.replace('primary_',''))
    axs[0,0].axhspan(71.92-.4,71.93+.4,color='gray',alpha=.2,label='Vinš 2015 ±0.4 comparison band')
    axs[0,0].set(xlabel='Production time (ps)',ylabel='Surface tension (mN/m)',title='Independent seeds; 100 ps blocks')
    axs[0,1].set(xlabel='Distance from slab center (nm)',ylabel='Density (g/cm³)',title='Actual liquid–vapor slab');axs[0,1].set_xlim(-2.2,2.2)
    axs[1,0].axvline(5,color='gray',ls=':');axs[1,0].set(xlabel='Fourth topological shell distance ψ (Å)',ylabel='Fraction per 0.2 Å bin',title='Network descriptor; no direct experimental target')
    if examples:
        frame,z,psi,box=examples
        sc=axs[1,1].scatter(frame[:,0,0]%box[0],z,c=psi,cmap='viridis',vmin=3,vmax=8,s=12)
        fig.colorbar(sc,ax=axs[1,1],label='ψ (Å)')
    axs[1,1].set(xlabel='x (nm)',ylabel='z from slab center (nm)',title='One saved molecular configuration')
    for ax in axs.flat[:3]:ax.legend(fontsize=7)
    fig.savefig(P/'figures/water.png');plt.close(fig)
    save_csv(P/'water_summary.csv',summary);save_csv(P/'water_blocks.csv',blocks)
    save_csv(P/'density_profiles.csv',profiles);save_csv(P/'topology_summary.csv',structures)
    save_csv(P/'topology_frames.csv',all_layer)
    primary=[r for r in summary if r['name'] in PRIMARY]
    vals=np.array([r['gamma_mN_m'] for r in primary]);n=len(vals)
    aggregate=dict(n_seeds=n,gamma_mean_mN_m=float(vals.mean()),
        seed_SD_mN_m=float(vals.std(ddof=1)) if n>1 else None,
        seed_t95_halfwidth_mN_m=float(student_t.ppf(.975,n-1)*vals.std(ddof=1)/np.sqrt(n)) if n>1 else None,
        uncertainty_note='Three-seed t interval is approximate; does not include force-field, finite-cell, electrostatic-image or equilibration error.',
        measurement_reference_mN_m=71.92333333333333)
    aggregate['difference_mN_m']=aggregate['gamma_mean_mN_m']-aggregate['measurement_reference_mN_m']
    for size in [50,100,200]:
        variances=[]
        for name in PRIMARY:
            values=[b['gamma_mN_m'] for b in blocks if b['name']==name and b['block_ps']==size]
            if len(values)>1:variances.append(float(np.var(values,ddof=1)/len(values)))
        aggregate[f'block{size}_SE_assuming_independent_blocks_mN_m']=float(np.sqrt(sum(variances))/len(variances)) if variances else None
    aggregate['block_SE_caution']='Approximate delta-method diagnostic from block free energies; remaining inter-block correlation and equilibration error are not corrected. Not an additional independent measurement.'
    paired=[]
    for name in PRIMARY:
        layers={r['layer']:r for r in structures if r['name']==name}
        if 'bulk' in layers and 'interface' in layers:
            paired.append(layers['interface']['HDL_fraction_classified']-layers['bulk']['HDL_fraction_classified'])
    aggregate['interface_minus_bulk_HDL_fraction_mean']=float(np.mean(paired))
    aggregate['interface_minus_bulk_HDL_seed_t95_halfwidth']=float(student_t.ppf(.975,len(paired)-1)*np.std(paired,ddof=1)/np.sqrt(len(paired))) if len(paired)>1 else None
    matched=float(np.mean([r['gamma_first300_mN_m'] for r in primary]))
    controls=[dict(name=r['name'],gamma_mN_m=r['gamma_mN_m'],matched_primary300_mean_mN_m=matched,
                   difference_mN_m=r['gamma_mN_m']-matched,
                   difference_percent=100*(r['gamma_mN_m']/matched-1),
                   note='Single short control; difference confounded by sampling. Larger cell also changes liquid-film thickness.')
              for r in summary if r['name'] not in PRIMARY]
    save_csv(P/'water_sensitivity.csv',controls)
    return dict(summary=summary,aggregate=aggregate,structure=structures,controls=controls)


def flow_analysis():
    summaries=[];byname={};fields={}
    for meta_path in sorted((P/'flow').glob('*/metadata.json')):
        m=json.loads(meta_path.read_text());name=m['name']
        h=np.genfromtxt(meta_path.parent/'history.csv',delimiter=',',names=True)
        # Equal sample cadence except possibly the last substep; negligible for means.
        selection=h['tU_D']>=m['duration_requested']/2;last=h[selection]
        r=dict(name=name,Re=m['Re_D'],D_cells=m['D_lattice'],aspect=m['aspect'],width_D=m['width_D'],
            U_lattice=m['speed'],Cs=m['cs'],status=m['status'],
            Cd_mean=float(last['Cd_projected'].mean()) if m['status']=='completed' else None,
            partial_Cd_mean=float(last['Cd_projected'].mean()),Cd_time_SD=float(last['Cd_projected'].std(ddof=1)),
            Cd_first_window=float(last['Cd_projected'][:len(last)//2].mean()),
            Cd_last_window=float(last['Cd_projected'][len(last)//2:].mean()),
            rho_min=float(h['rho_min'].min()),rho_max=float(h['rho_max'].max()),
            max_local_Mach=float(h['max_speed_lattice'].max()*np.sqrt(3)),
            open_domain_mass_deviation_max=float(np.abs(h['mass_relative']).max()),
            voxel_volume_error_percent=100*(m['body_volume_voxels']/m['exact_body_volume']-1))
        f=np.load(meta_path.parent/'slices.npz');D=int(f['D']);cx,cy,cz=f['center'];mean=f['mean']
        downstream=np.arange(mean.shape[1])>cx+D*.5*m['aspect']**(2/3)
        wake=downstream & (mean[1,:,int(cy)]<0)
        r['last_reverse_flow_x_from_center_D']=float((np.where(wake)[0].max()-cx)/D) if wake.any() else 0.
        summaries.append(r);byname[name]=r;fields[name]=(f,h)
    save_csv(P/'flow_summary.csv',summaries)
    sensitivities=[]
    for base,alt,kind in [('re1500_d20','re1500_d28','grid 20 to 28'),('re2500_d20','re2500_d28','grid 20 to 28'),
                          ('re1500_d20','re1500_wide','transverse 5D to 7D; length 12D to 16D'),
                          ('re1500_d20','re1500_slow','lattice speed 0.06 to 0.03'),
                          ('re1500_d20','re1500_seed97','wake seed 31 to 97'),
                          ('re1500_d20','re1500_no_sgs','Cs 0.1 to 0'),
                          ('re1500_d20','re1500_sphere','aspect 0.7 to 1'),
                          ('micev_dvs','micev_dvs_aspect084','aspect 0.7 to 0.84')]:
        if base in byname and alt in byname and byname[base]['status']==byname[alt]['status']=='completed':
            sensitivities.append(dict(base=base,alternative=alt,change=kind,
                relative_Cd_change_percent=100*(byname[alt]['Cd_mean']/byname[base]['Cd_mean']-1)))
    save_csv(P/'flow_sensitivity.csv',sensitivities)
    rhoa=1.204;rhow=998.2;grav=9.80665;nu=1.5e-5;D=.0025
    comparisons=[]
    for name,velocity,u_velocity in [('micev_dvs',7.8,.5),('micev_parsivel',6.4,None),('micev_dvs_aspect084',7.8,.5)]:
        if name not in byname:continue
        r=byname[name];shape=r['aspect'];needed=4*(rhow-rhoa)*grav*D/(3*rhoa*velocity**2)*shape**(2/3)
        comparisons.append(dict(name=name,measured_speed_m_s=velocity,speed_combined_uncertainty_m_s=u_velocity,
             assumed_D_mm=D*1000,assumed_aspect=shape,Re=r['Re'],computed_Cd=r['Cd_mean'],
             terminal_still_air_required_Cd=needed,drag_over_weight_minus_buoyancy=r['Cd_mean']/needed,
             comparison='Conditional force balance; measured speed sets Re, not an independent velocity prediction'))
    save_csv(P/'flow_measurement_comparison.csv',comparisons)
    terminal={}
    names=['terminal_re800','terminal_re1000','micev_parsivel','micev_dvs','re1500_d20','re2500_d20']
    if all(n in byname for n in names):
        re=np.array([byname[n]['Re'] for n in names]);cd=np.array([byname[n]['Cd_mean'] for n in names])
        def force_ratio(speed):
            drag=.5*rhoa*speed**2*(np.pi*D**2/4*.7**(-2/3))*np.interp(speed*D/nu,re,cd)
            return drag/((rhow-rhoa)*grav*np.pi*D**3/6)
        lo,hi=re[0]*nu/D,re[-1]*nu/D
        if (force_ratio(lo)-1)*(force_ratio(hi)-1)<0:
            speed=brentq(lambda u:force_ratio(u)-1,lo,hi)
            terminal=dict(predicted_speed_m_s=speed,Re=speed*D/nu,
                delta_DVS_m_s=speed-7.8,delta_PARSIVEL_m_s=speed-6.4,
                note='Conditional fixed-body terminal-speed prediction; linear interpolation of computed Cd(Re), no fitting to measured velocities. Diameter, shape and still-air assumptions remain unmatched.')
    fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for i,name in enumerate(['re1500_d20','re2500_d20']):
        if name not in fields:continue
        f,h=fields[name];Dg=int(f['D']);cx,cy,_=f['center'];U=float(f['speed']);vel=f['mean'];mask=f['solid'].astype(bool)
        x=(np.arange(mask.shape[0])-cx)/Dg;y=(np.arange(mask.shape[1])-cy)/Dg
        ux=np.ma.masked_where(mask,vel[1]/U);uy=np.ma.masked_where(mask,vel[2]/U)
        im=axs[0,i].pcolormesh(x,y,ux.T,cmap='RdBu_r',vmin=-.3,vmax=1.5,shading='auto')
        axs[0,i].contourf(x,y,mask.T,levels=[.5,1.5],colors=['#303744'])
        axs[0,i].streamplot(x,y,ux.T,uy.T,color='#172b3b',density=.8,linewidth=.5,arrowsize=.6)
        axs[0,i].set(xlabel='x/D',ylabel='y/D',title=f"Mean external flow, Re={byname[name]['Re']:g}",xlim=(-1.5,5),ylim=(-2,2),aspect='equal')
        fig.colorbar(im,ax=axs[0,i],label='Streamwise velocity / U')
    for name in ['re1500_d20','re1500_d28','re2500_d20','re2500_d28']:
        if name in fields:
            _,h=fields[name];axs[1,0].plot(h['tU_D'],h['Cd_projected'],label=name)
    axs[1,0].set(xlabel='Time × U/D',ylabel='Drag coefficient (projected area)',title='Grid comparison; view after initial impulse',xlim=(5,40),ylim=(-.3,1.1));axs[1,0].legend(fontsize=7)
    selected=sensitivities[:6]
    short={'grid 20 to 28':'grid 20 → 28','transverse 5D to 7D; length 12D to 16D':'wider / longer domain',
           'lattice speed 0.06 to 0.03':'half lattice speed','wake seed 31 to 97':'new wake seed',
           'aspect 0.7 to 1':'sphere control','Cs 0.1 to 0':'zero subgrid viscosity'}
    axs[1,1].barh([('Re 2500: ' if r['base']=='re2500_d20' else 'Re 1500: ')+short.get(r['change'],r['change']) for r in selected],[r['relative_Cd_change_percent'] for r in selected],color='#357c9e')
    axs[1,1].axvline(0,color='gray',lw=.7);axs[1,1].set(xlabel='Change in mean drag coefficient (%)',title='Numerical sensitivity remains visible')
    axs[1,1].tick_params(axis='y',labelsize=8)
    fig.savefig(P/'figures/flow.png');plt.close(fig)
    return dict(summary=summaries,sensitivity=sensitivities,comparisons=comparisons,terminal=terminal)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');ap.add_argument('--flow-only',action='store_true');a=ap.parse_args()
    (P/'figures').mkdir(exist_ok=True)
    result=dict(flow=flow_analysis())
    if not a.flow_only:result['water']=water_analysis(a.partial)
    if 'water' in result and result['flow']['terminal']:
        fig,ax=plt.subplots(1,2,figsize=(11,4.4),layout='constrained')
        wa=result['water']['aggregate']
        ax[0].errorbar([0],[wa['gamma_mean_mN_m']],yerr=[wa['seed_t95_halfwidth_mN_m'] or 0],fmt='o',capsize=5,label='3-seed approximate 95% interval')
        ax[0].errorbar([1],[wa['measurement_reference_mN_m']],yerr=[.4],fmt='s',capsize=5,color='#c57532',label='Measurement comparison ±0.4')
        ax[0].set(xticks=[0,1],xticklabels=['Water simulation','Vinš 2015'],ylabel='Surface tension (mN/m)',title='Water: sampling error is not total error')
        ax[0].legend(fontsize=8,loc='lower right')
        values=[result['flow']['terminal']['predicted_speed_m_s'],7.8,6.4]
        ax[1].bar([0,1,2],values,color=['#3c8098','#c57532','#c57532'],width=.55)
        ax[1].errorbar([1],[7.8],yerr=[.5],color='black',capsize=5,fmt='none')
        ax[1].set(xticks=[0,1,2],xticklabels=['Fixed body','DVS','PARSIVEL'],ylabel='Speed (m/s)',title='2.5 mm: conditional flow comparison',ylim=(0,9.5))
        ax[1].text(.02,.96,'Unmatched shape / air conditions\nNo bar = uncertainty not quantified',transform=ax[1].transAxes,va='top',fontsize=8)
        fig.savefig(P/'figures/comparisons.png');plt.close(fig)
    (P/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({k:v.get('aggregate',v.get('terminal')) for k,v in result.items()},indent=2))

if __name__=='__main__':main()
