"""Reproduce fixed-model development comparison and conditional holdout test."""
from pathlib import Path
import csv,json,hashlib,datetime,platform
import numpy as np
import scipy
from scipy.optimize import brentq, minimize_scalar
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from raindrop_model import *

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
read=lambda name:list(csv.DictReader((ROOT/name).open()))
def write(name,rows):
    with (OUT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def plain(x):
    if isinstance(x,np.generic):return x.item()
    raise TypeError(type(x).__name__)
def score(rows):
    r=np.array([x['predicted_E']/x['observed_E'] for x in rows])
    return dict(n_observables=len(r),geometric_bias=float(np.exp(np.mean(np.log(r)))),
        median_absolute_factor=float(np.median(np.maximum(r,1/r))),within_factor2=int(np.sum((r>=.5)&(r<=2))),
        note='Four aggregate observables at two drop conditions, not four independent experiments; conditional inputs.')

def main():
    protocol=json.loads((ROOT/'frozen_protocol.json').read_text())
    h=hashlib.sha256((ROOT/'raindrop_model.py').read_bytes()).hexdigest()
    assert h==protocol['model_sha256'],'Frozen model changed after holdout reveal'
    results=[];sens=[];bounds=[];quadchecks=[];grid=[]
    for row in read('holdout_measurements.csv'):
        D=float(row['drop_equiv_mm'])*1e-3;l=float(row['drop_long_axis_mm'])*1e-3
        d=float(row['particle_mean_um'])*1e-6;area=(D/l)**2
        kw=dict(T=float(row['T_K']),RH=float(row['RH']),rho_p=float(row['rho_particle_kg_m3']),U=float(row['speed_m_s']))
        z=efficiency(D,d,**kw)
        pred=z['total']*area;obs=float(row['observed_E'])
        result=dict(id=row['id'],observable=row['observable'],drop_equiv_mm=D*1e3,long_axis_mm=l*1e3,
                    observed_E=obs,predicted_E=pred,ratio=pred/obs,area_conversion=area,
                    Re_D=z['Re_D'],rear_in_domain=z['rear_in_domain'],St=z['St'],
                    surface_T_K=z['surface_T_K'],heat_residual_W_m2=z['heat_residual_W_m2'],
                    **{k+'_projected':z[k]*area for k in COMPONENTS[:-1]})
        results.append(result)
        scenarios=[('primary',{}),('no_phoresis',{'phoresis':False}),('no_impaction',{'impaction':False}),
                   ('no_rear',{'rear':False}),('uncorrected_Slinn',{'correction':False}),
                   ('T_low',{'T':kw['T']-1}),('T_high',{'T':kw['T']+1}),
                   ('RH_low',{'RH':.54}),('RH_high',{'RH':.58}),
                   ('speed_low',{'U':kw['U']*.9}),('speed_high',{'U':kw['U']*1.1}),
                   ('rho_low',{'rho_p':1710}),('rho_high',{'rho_p':2090}),
                   ('k_low',{'k_p':.1}),('k_mid',{'k_p':1.}),('k_high',{'k_p':3.})]
        for label,changes in scenarios:
            zz=efficiency(D,d,**(kw|changes))
            sens.append(dict(id=row['id'],scenario=label,predicted_E=zz['total']*area,observed_E=obs))
        # Input-distribution sensitivity, constrained to source's 1--5 um range.
        # No fitted outcome: median determined solely by reported arithmetic mean.
        for gsd in [1.3,1.5]:
            for n in [501,1001]:
                ds=np.linspace(1e-6,5e-6,n);sig=np.log(gsd)
                def density(m):return np.exp(-.5*(np.log(ds/m)/sig)**2)/ds
                med=brentq(lambda m:np.trapezoid(ds*density(m),ds)/np.trapezoid(density(m),ds)-d,1e-6,6e-6,xtol=1e-15)
                w=density(med);w/=np.trapezoid(w,ds)
                moment=0 if row['observable']=='number' else 3
                w=w*ds**moment;w/=np.trapezoid(w,ds)
                ee=np.array([efficiency(D,x,**kw)['total'] for x in ds])*area
                avg=np.trapezoid(ee*w,ds)
                quadchecks.append(dict(id=row['id'],gsd=gsd,n=n,predicted_E=avg,median_um=med*1e6))
                if n==1001:sens.append(dict(id=row['id'],scenario=f'truncated_GSD_{gsd}',predicted_E=avg,observed_E=obs))
        # Any number OR mass-weighted average must lie between pointwise extremes.
        # This does not assume an unavailable input histogram or optimize the model.
        for n in [501,1001]:
            ds=np.linspace(1e-6,5e-6,n)
            ee=np.array([efficiency(D,x,**kw)['total'] for x in ds])*area
            idx=int(np.argmax(ee));lo=ds[max(idx-1,0)];hi=ds[min(idx+1,n-1)]
            opt=minimize_scalar(lambda x:-efficiency(D,x*1e-6,**kw)['total']*area,
                                bounds=(lo*1e6,hi*1e6),method='bounded')
            mx=max(float(ee.max()),float(-opt.fun))
            bounds.append(dict(id=row['id'],n=n,minimum_E=float(ee.min()),maximum_E=mx,
                               observed_E=obs,observed_above_maximum=bool(obs>mx),
                               qualification='Numerical support envelope at nominal conditions; not experimental uncertainty.'))
            if n==1001 and row['observable']=='number':
                grid.extend(dict(drop_equiv_mm=D*1e3,particle_um=x*1e6,E=y) for x,y in zip(ds,ee))
    write('holdout_predictions.csv',results);write('sensitivities.csv',sens)
    write('distribution_refinement.csv',quadchecks);write('distribution_bounds.csv',bounds)
    write('size_response.csv',grid)
    development=[]
    for r in read('development_measurements.csv'):
        dp=float(r['dphysical_um'])*1e-6
        for gsd in [1.,1.3,1.5]:
            z=distribution(.00125,dp,gsd=gsd,moment=3,U=4.7)
            development.append(dict(row=r['row'],dphysical_um=dp*1e6,gsd=gsd,
                observed_E=float(r['CE']),predicted_E=z['total'],aggregate_eligible=r['aggregate_eligible']))
    write('development_predictions.csv',development)
    speeds=[]
    for r in read('drop_measurements.csv'):
        D=float(r['drop_equiv_mm'])*1e-3;u=terminal_speed(D,284.15)
        speeds.append(dict(D_mm=D*1e3,observed_glycerol_speed=float(r['speed_m_s']),
                           predicted_water_speed=u,ratio=u/float(r['speed_m_s'])))
    write('speed_transfer.csv',speeds)
    tt=np.linspace(0,300,301);a,c,rate=inventory(.01,.00125,4.7,100,1e8,tt)
    write('inventory.csv',[dict(t_s=t,airborne_m3=x,collected_per_initial_m3=y,total=x+y) for t,x,y in zip(tt,a,c)])
    stats=score(results)
    stats.update(model_sha256=h,freeze_utc=protocol['frozen_utc'],run_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        holdout_status='New outcomes; frozen model. Conditional out-of-domain transfer test, NOT matched pure-water/smoke validation.',
        source_counts=dict(aggregate_efficiencies=4,unique_drop_conditions_for_efficiency=2,drop_speed_table_rows=5,
            figure_only_intermediate_efficiencies='not extracted; source PDF graphics unavailable; no numeric values invented'),
        max_mass_balance_absolute=float(np.max(abs(a+c-1e8))),python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__)
    (OUT/'summary.json').write_text(json.dumps(stats,indent=2,default=plain))
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(9,4.6),layout='constrained')
    x=np.arange(4);obs=np.array([r['observed_E'] for r in results])*100;pred=np.array([r['predicted_E'] for r in results])*100
    ax.bar(x-.18,obs,.36,label='Measured: glycerol–water + coated silica',color='#385b77')
    ax.bar(x+.18,pred,.36,label='Frozen water-model transfer prediction',color='#d07936')
    ax.set_xticks(x,[f"{r['long_axis_mm']:.2f} mm\n{r['observable']}" for r in results]);ax.set_ylabel('Collection efficiency (%)')
    ax.set_title('New measurement test: all four extracted means are underpredicted')
    ax.legend(loc='upper left',fontsize=9);ax.set_ylim(0,100)
    for xx,yy in zip(x+.18,pred):ax.text(xx,yy+1,f'{yy:.1f}',ha='center')
    fig.savefig(OUT/'holdout.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for D in sorted(set(g['drop_equiv_mm'] for g in grid)):
        rr=[g for g in grid if g['drop_equiv_mm']==D]
        axs[0].plot([g['particle_um'] for g in rr],np.array([g['E'] for g in rr])*100,label=f'{D:g} mm equivalent')
    axs[0].set(xlabel='Physical particle diameter (µm)',ylabel='Collection efficiency (%)',title='Unresolved wake at Re > 800');axs[0].legend()
    for i,r in enumerate(results):
        rr=[s['predicted_E']*100 for s in sens if s['id']==r['id'] and not s['scenario'].startswith('no_') and s['scenario']!='uncorrected_Slinn']
        axs[1].plot([i,i],[min(rr),max(rr)],lw=6,color='#d07936')
        axs[1].plot(i,r['observed_E']*100,'o',color='#385b77')
    axs[1].set(xticks=x,xticklabels=['large N','large M','small N','small M'],ylabel='Collection efficiency (%)',title='Assumption sensitivity, not confidence intervals')
    fig.savefig(OUT/'sensitivity.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.7),layout='constrained')
    rr=[r for r in development if r['gsd']==1]
    ax.scatter([r['dphysical_um'] for r in rr],[r['observed_E'] for r in rr],label='Known 2017 measurements',color='#385b77')
    for gsd in [1,1.3,1.5]:
        rr=sorted([r for r in development if r['gsd']==gsd],key=lambda r:r['dphysical_um'])
        ax.plot([r['dphysical_um'] for r in rr],[r['predicted_E'] for r in rr],'-o',label=f'Revised, GSD {gsd:g}')
    ax.plot([.22,.6248,2.2352],[7.96616e-5,3.9831e-5,1.9915e-5],'x--',label='Earlier creeping-flow diagnostic')
    ax.set(xscale='log',yscale='log',xlabel='Physical particle diameter (µm)',ylabel='Collection efficiency',title='Development data: improvement at small particle sizes, unresolved coarse end')
    ax.legend(fontsize=8);fig.savefig(OUT/'development.png',dpi=180);plt.close(fig)
    print(json.dumps(stats,indent=2,default=plain))

if __name__=='__main__':main()
