"""Prespecified paired contrasts and diagnostic figures; run after the ensemble."""
import argparse,csv,json
from pathlib import Path
import numpy as np
from oscillators import drift_period,triangle
from run_experiments import FIELDS


def interval(values):
    values=np.asarray(values,float)
    rng=np.random.default_rng(72411)
    boot=values[rng.integers(0,len(values),(10000,len(values)))].mean(1)
    lo,hi=np.quantile(boot,[.025,.975],axis=0)
    return dict(mean=float(values.mean()),lo=float(lo),hi=float(hi),seeds=len(values))


def recovery_time(differences,stop,threshold=.03):
    within=np.all(abs(differences[stop:,[1,2]])<=threshold,axis=1)
    hits=np.flatnonzero(within[:-1]&within[1:])
    horizon=len(within)*10
    return dict(first_attainment=int((hits[0]+2)*10) if len(hits) else None,
                horizon=horizon,last_40_all_within=bool(within[-4:].all()))


def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def summarize(data,out):
    tasks=json.loads((data/'tasks.json').read_text());x=np.load(data/'recovery.npz')['blocks']
    lookup={(t['config']['seed'],t['config']['topology'],t['config']['balance'],t['config']['memory'],t['schedule']):i for i,t in enumerate(tasks)}
    seeds=sorted({key[0] for key in lookup});contrasts=[];recovery=[];per_seed=[]
    for split in ('discovery','replication'):
        split_seeds=[s for s in seeds if (s<20000)==(split=='discovery')]
        for memory in (0,1):
            for contrast,window in [('early_minus_never',slice(-4,None)),('repeated_minus_late',slice(-4,None)),('second_pulse_history_interaction',slice(20,24))]:
                values=[]
                for seed in split_seeds:
                    pairs=[]
                    for topology in ('ring','random','hub'):
                        for balance in ('equal','unequal'):
                            runs={s:x[lookup[(seed,topology,balance,memory,s)]] for s in ('never','early','late','repeated')}
                            diff=(runs['early']-runs['never'] if contrast=='early_minus_never' else
                                  runs['repeated']-runs['late'] if contrast=='repeated_minus_late' else
                                  (runs['repeated']-runs['early'])-(runs['late']-runs['never']))
                            pairs.append(diff[window].mean(0))
                    values.append(np.mean(pairs,axis=0))
                values=np.array(values)
                for j,metric in enumerate(FIELDS[:3]):
                    row=dict(split=split,memory=memory,contrast=contrast,metric=metric,**interval(values[:,j]))
                    contrasts.append(row)
                    per_seed.extend(dict(split=split,seed=s,memory=memory,contrast=contrast,metric=metric,value=float(v)) for s,v in zip(split_seeds,values[:,j]))
    for seed,topology,balance,memory,schedule in lookup:
        if schedule=='never':continue
        control='early' if schedule=='repeated' else 'never';stop=8 if schedule=='early' else 24
        diff=x[lookup[(seed,topology,balance,memory,schedule)]]-x[lookup[(seed,topology,balance,memory,control)]]
        recovery.append(dict(seed=seed,split='discovery' if seed<20000 else 'replication',topology=topology,balance=balance,
                             memory=memory,schedule=schedule,**recovery_time(diff,stop)))
    rates=[]
    for split in ('discovery','replication'):
        for memory in (0,1):
            for schedule in ('early','late','repeated'):
                selected=[r for r in recovery if r['split']==split and r['memory']==memory and r['schedule']==schedule]
                byseed=sorted({r['seed'] for r in selected})
                for endpoint in ('first_attainment','last_40_all_within'):
                    vals=[np.mean([(r[endpoint] is not None if endpoint=='first_attainment' else r[endpoint]) for r in selected if r['seed']==s]) for s in byseed]
                    rates.append(dict(split=split,memory=memory,schedule=schedule,endpoint=endpoint,**interval(vals)))
    network=json.loads((data/'network.json').read_text());network_contrasts=[];network_levels=[]
    for split in ('discovery','replication'):
        ss=[s for s in seeds if (s<20000)==(split=='discovery')]
        for topology in ('ring','random','hub'):
            for metric in ('coherence','locked_fraction','mean_drift'):
                arrays={mode:np.array([np.mean([r[metric] for r in network if r['seed']==s and r['topology']==topology and r['driver']==mode]) for s in ss]) for mode in ('none','high_degree','low_degree','distributed')}
                for mode,vals in arrays.items():network_levels.append(dict(split=split,topology=topology,driver=mode,metric=metric,**interval(vals)))
                for a,b in [('high_degree','low_degree'),('distributed','none')]:
                    network_contrasts.append(dict(split=split,topology=topology,contrast=a+'_minus_'+b,metric=metric,**interval(arrays[a]-arrays[b])))
    phase=np.load(data/'phase.npz');phase_rows=[]
    for response in ('sine','triangle','triangle_normalized'):
        theoretical=drift_period(phase[response+'_deltas'],response=response)
        for j,d in enumerate(phase[response+'_deltas']):
            measured=float(phase[response+'_measured_period'][j]);fine=float(phase[response+'_fine_measured_period'][j]);exact=float(theoretical[j])
            phase_rows.append(dict(response=response,delta=float(d),theory_period=exact,numerical_period=measured,refined_period=fine,
                relative_error=abs(measured-exact)/exact if np.isfinite(measured) and np.isfinite(exact) else None,
                measured_cycles=int(phase[response+'_crossings'][j])))
    for name,rows in [('recovery_contrasts',contrasts),('seed_contrasts',per_seed),('recovery_endpoints',recovery),('recovery_rates',rates),('network_contrasts',network_contrasts),('network_levels',network_levels),('phase_periods',phase_rows)]:write_csv(out/(name+'.csv'),rows)
    summary=dict(recovery_contrasts=contrasts,recovery_rates=rates,network_contrasts=network_contrasts,
                 network_levels=network_levels,maximum_phase_period_relative_error=max(r['relative_error'] for r in phase_rows if r['relative_error'] is not None),
                 uncertainty='Descriptive seed-bootstrap intervals; no multiplicity adjustment, empirical calibration or population claims.')
    (out/'summary.json').write_text(json.dumps(summary,indent=2));return summary,tasks,x


def figures(data,out,summary,tasks,x):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
    colors=['#167d8d','#cc623b','#785cb4','#578846']
    def save(fig,name):
        fig.savefig(out/(name+'.png'),bbox_inches='tight');fig.savefig(out/(name+'.svg'),bbox_inches='tight');plt.close(fig)
    lookup={(t['config']['seed'],t['config']['topology'],t['config']['balance'],t['config']['memory'],t['schedule']):i for i,t in enumerate(tasks)}
    seeds=sorted({key[0] for key in lookup if key[0]>=20000});time=np.arange(5,480,10)
    fig,axs=plt.subplots(2,2,figsize=(11,6.5),sharex=True)
    for memory in (0,1):
        for col,metric in enumerate(('rigid','choice_excess')):
            ax=axs[memory,col];j=FIELDS.index(metric)
            for schedule,color in zip(('early','late','repeated'),colors):
                v=np.array([np.mean([x[lookup[(s,t,b,memory,schedule)],:,j]-x[lookup[(s,t,b,memory,'never')],:,j] for t in ('ring','random','hub') for b in ('equal','unequal')],axis=0) for s in seeds])
                boot=v[np.random.default_rng(414).integers(0,len(v),(2000,len(v)))].mean(1);lo,hi=np.quantile(boot,[.025,.975],axis=0)
                ax.plot(time,v.mean(0),label=schedule,color=color);ax.fill_between(time,lo,hi,color=color,alpha=.13)
            ax.axhline(0,color='#777',lw=.7);ax.axvspan(40,80,color='#777',alpha=.1);ax.axvspan(200,240,color='#777',alpha=.1)
            ax.set_title(f'{metric.replace("_"," ")} · memory {"on" if memory else "off"}');ax.set_ylabel('Difference from no stress')
            if memory:ax.set_xlabel('SIMS round (10-round means)')
    axs[0,0].legend();fig.suptitle('Long recovery and a second stress pulse · independent replication');fig.tight_layout();save(fig,'recovery')
    fig,axs=plt.subplots(1,3,figsize=(12,3.7));theta=np.linspace(-np.pi,np.pi,501)
    axs[0].plot(theta,np.sin(theta),label='sine');axs[0].plot(theta,triangle(theta),label='triangle as supplied');axs[0].plot(theta,triangle(theta,True),'--',label='equal-peak triangle');axs[0].set(xlabel='Phase difference',ylabel='Response');axs[0].legend(fontsize=8)
    grid=np.linspace(1.001,3,400);phase=np.load(data/'phase.npz')
    for response,color in zip(('sine','triangle','triangle_normalized'),colors):
        period=drift_period(grid,response=response);axs[1].plot(grid,2*np.pi/period,color=color,label=response.replace('_',' '))
        d=phase[response+'_deltas'];p=phase[response+'_measured_period'];valid=np.isfinite(p);axs[1].scatter(d[valid],2*np.pi/p[valid],s=16,color=color)
    axs[1].set(xlabel='Frequency difference / A (A=1)',ylabel='Mean phase drift');axs[1].set_title('Lines: exact; dots: integrated cycles')
    for j in (2,4,7,10):axs[2].plot(phase['sine_times'],phase['sine_phase'][:,j],label=f"delta={phase['sine_deltas'][j]:g}")
    axs[2].set(xlabel='Dimensionless time',ylabel='Unwrapped phase');axs[2].legend(fontsize=8)
    fig.suptitle('Locking range depends on response shape and peak amplitude');fig.tight_layout();save(fig,'entrainment')
    rows=json.loads((data/'junction.json').read_text());fine=json.loads((data/'junction_refined.json').read_text())
    fig,axs=plt.subplots(1,3,figsize=(11,3.6),sharey=True)
    for ax,beta in zip(axs,(.2,2,10)):
        for direction,color in zip(('up','down'),colors):
            rr=[r for r in rows if r['beta']==beta and r['direction']==direction]
            rf=[r for r in fine if r['beta']==beta and r['direction']==direction]
            ax.plot([r['bias'] for r in rr],[r['voltage_ratio'] for r in rr],label=direction,color=color)
            ax.plot([r['bias'] for r in rf],[r['voltage_ratio'] for r in rf],':',color=color,alpha=.8)
        bias=np.linspace(0,1.5,300);ax.plot(bias,np.sqrt(np.maximum(bias*bias-1,0)),'--',color='#555',label='beta=0 exact');ax.set_title(f'beta = {beta:g}');ax.set_xlabel('Normalized current I / Ic')
    axs[0].set_ylabel('Mean phase speed = V / (Ic R)');axs[0].legend(fontsize=8)
    fig.suptitle('Josephson equation: inertia can separate upward and downward branches\nDotted curves: half step, twice the settling time');fig.tight_layout();save(fig,'junction')
    fig,axs=plt.subplots(1,2,figsize=(10,4));modes=('none','high_degree','low_degree','distributed');topologies=('ring','random','hub')
    for ax,metric in zip(axs,('coherence','locked_fraction')):
        for j,mode in enumerate(modes):
            rr=[next(r for r in summary['network_levels'] if r['split']=='replication' and r['topology']==t and r['driver']==mode and r['metric']==metric) for t in topologies]
            mean=np.array([r['mean'] for r in rr]);lo=np.array([r['lo'] for r in rr]);hi=np.array([r['hi'] for r in rr])
            ax.bar(np.arange(3)+(j-1.5)*.19,mean,.18,yerr=[np.maximum(0,mean-lo),np.maximum(0,hi-mean)],color=colors[j],label=mode.replace('_',' '),capsize=2)
        ax.set_xticks(range(3),topologies);ax.set_ylim(0,1.08);ax.set_title(metric.replace('_',' '))
    axs[0].legend(fontsize=8);fig.suptitle('30 oscillator SIMS · same total forcing across driven conditions\nCoherence and locking to an external rhythm are different measurements');fig.tight_layout();save(fig,'network')
    solutions=json.loads((data/'circle.json').read_text());functions=[lambda t:1+2*np.cos(t),lambda t:np.sin(2*t),lambda t:np.sin(t)**3,lambda t:np.sin(t)+np.cos(t),lambda t:3+np.cos(2*t),lambda t:np.sin(3*t)]
    fig,axs=plt.subplots(2,3,figsize=(10,6))
    for ax,row,f in zip(axs.ravel(),solutions,functions):
        tt=np.linspace(0,2*np.pi,301);ax.plot(np.cos(tt),np.sin(tt),color='#adb8bc');roots=row['roots']
        for root,stability in zip(roots,row['stability']):
            stable=stability.startswith('stable');ax.plot(np.cos(root),np.sin(root),'o',mfc=colors[0] if stable else 'white',mec=colors[0] if stable else colors[1],ms=8)
        for angle in ([(roots[i]+(roots[(i+1)%len(roots)]+(2*np.pi if i==len(roots)-1 else 0)))/2 for i in range(len(roots))] if roots else [0,np.pi/2,np.pi,3*np.pi/2]):
            sign=np.sign(f(angle));end=angle+sign*.22
            ax.annotate('',xy=(np.cos(end),np.sin(end)),xytext=(np.cos(angle),np.sin(angle)),arrowprops=dict(arrowstyle='->',color='#333'))
        ax.set(xlim=(-1.4,1.4),ylim=(-1.3,1.3),aspect='equal');ax.axis('off');ax.set_title(row['exercise']+'  '+row['equation'],fontsize=10)
    fig.suptitle('Flows on the circle · filled: stable; hollow: unstable\nThe final panel illustrates k=3; the formula holds for every positive integer k');fig.tight_layout();save(fig,'circle')


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=Path('data'));p.add_argument('--out',type=Path,default=Path('analysis'));a=p.parse_args();a.out.mkdir(exist_ok=True)
    summary,tasks,x=summarize(a.data,a.out);figures(a.data,a.out,summary,tasks,x)
    print(json.dumps(dict(recovery_contrasts=len(summary['recovery_contrasts']),period_relative_error=summary['maximum_phase_period_relative_error']),indent=2))


if __name__=='__main__':main()
