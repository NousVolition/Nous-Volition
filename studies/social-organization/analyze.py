"""Reanalyze saved arrays; bootstrap independent seeds, never agents or rounds."""
import argparse,csv,json,itertools,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from model import Config,run,network_metrics


def write_csv(path,rows):
    if not rows:return
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def interval(values,seed=49018):
    x=np.array(values,float);x=x[np.isfinite(x)]
    if not len(x):return dict(mean=None,lo=None,hi=None,seeds=0)
    rng=np.random.default_rng(seed)
    means=x[rng.integers(0,len(x),(10000,len(x)))].mean(1)
    return dict(mean=float(x.mean()),lo=float(np.quantile(means,.025)),hi=float(np.quantile(means,.975)),seeds=len(x))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,default=Path('data'));ap.add_argument('--out',type=Path,default=Path('analysis'))
    args=ap.parse_args();args.out.mkdir(exist_ok=True,parents=True)
    tasks=json.loads((args.data/'tasks.json').read_text());schema=json.loads((args.data/'schema.json').read_text())
    from restore_data import restore
    restore(args.data)
    with np.load(args.data/'arrays.npz') as packed:
        arr={k:packed[k] for k in packed.files}
    meta=[dict(id=t['id'],suite=t['suite'],split=t['split'],**t['config']) for t in tasks]
    phase_idx={k:i for i,k in enumerate(schema['phases'])};trace_idx={k:i for i,k in enumerate(schema['trace'])}
    def select(**filters):return [i for i,m in enumerate(meta) if all(m[k]==v for k,v in filters.items())]
    def seed_means(indices,metric,phase):
        seeds=sorted({meta[i]['seed'] for i in indices})
        return {seed:float(np.nanmean([arr['phases'][i,phase,phase_idx[metric]] for i in indices if meta[i]['seed']==seed])) for seed in seeds}
    def contrast(metric,phase,factor,high,low,**filters):
        a=seed_means(select(**filters,**{factor:high}),metric,phase)
        b=seed_means(select(**filters,**{factor:low}),metric,phase)
        seeds=sorted(a.keys()&b.keys())
        return interval([a[s]-b[s] for s in seeds])
    contrasts=[]
    for split,phase,factor,metric in itertools.product(('discovery','replication'),(1,2),('identity','behavior','memory','stress','transitions'),('choice_excess','coop_gap','cooperation','window_excluded','rigid','switching','influence_gini','assortativity','fragmentation')):
        high=.7 if factor=='identity' else 1
        v=contrast(metric,phase,factor,high,0,suite='factorial',split=split)
        contrasts.append(dict(split=split,phase=phase,factor=factor,metric=metric,**v))
    write_csv(args.out/'factorial_contrasts.csv',contrasts)
    interactions=[]
    for split,phase,other,metric in itertools.product(('discovery','replication'),(1,2),('memory','identity','transitions'),('choice_excess','coop_gap','rigid','cooperation')):
        high=.7 if other=='identity' else 1
        means={}
        for stress,x in itertools.product((0,1),(0,high)):
            means[stress,x]=seed_means(select(suite='factorial',split=split,stress=stress,**{other:x}),metric,phase)
        seeds=sorted(means[0,0])
        values=[means[1,high][s]-means[0,high][s]-means[1,0][s]+means[0,0][s] for s in seeds]
        interactions.append(dict(split=split,phase=phase,interaction='stress x '+other,metric=metric,**interval(values)))
    write_csv(args.out/'interactions.csv',interactions)
    # Export complete phase-level data, with no averaging over independent units.
    rows=[]
    for i,m in enumerate(meta):
        for p in range(3):rows.append(dict(**m,**dict(zip(schema['phases'],arr['phases'][i,p].tolist()))))
    write_csv(args.out/'run_phase_metrics.csv',rows)
    label_checks=[]
    for seed,topo,balance in itertools.product(sorted({m['seed'] for m in meta}),('ring','random','hub'),('equal','unequal')):
        idx=select(suite='labels',seed=seed,topology=topo,balance=balance)
        equal=len(set(arr['digests'][idx]))==1
        error=float(np.nanmax(abs(arr['phases'][idx]-arr['phases'][idx[0]])))
        label_checks.append(dict(seed=seed,topology=topo,balance=balance,exact=bool(equal),max_metric_difference=error))
    write_csv(args.out/'label_invariance.csv',label_checks)
    # Full-model recovery paired on seed, topology, balance and all other rules.
    recovery=[]
    for memory in (0,1):
        for i in select(suite='factorial',split='replication',stress=1,behavior=1,memory=memory,transitions=1,identity=.7):
            m=meta[i];j=select(suite='factorial',seed=m['seed'],topology=m['topology'],balance=m['balance'],stress=0,behavior=1,memory=memory,transitions=1,identity=.7)[0]
            d=arr['trace'][i]-arr['trace'][j]
            end=None
            windows=[]
            for start in range(80,120,10):
                windows.append(all(abs(d[start:start+10,trace_idx[k]].mean())<=.03 for k in ('rigid','choice_excess')))
            for k in range(1,len(windows)):
                if windows[k-1] and windows[k]:end=10*(k+1);break
            recovery.append(dict(seed=m['seed'],topology=m['topology'],balance=m['balance'],memory=memory,
                recovered=end is not None,time_or_censor=end if end else 40,
                late_rigidity_difference=float(d[110:120,trace_idx['rigid']].mean()),
                late_choice_difference=float(d[110:120,trace_idx['choice_excess']].mean())))
    write_csv(args.out/'recovery.csv',recovery)
    recovery_summary=[]
    for memory in (0,1):
        rr=[r for r in recovery if r['memory']==memory]
        for metric in ('recovered','time_or_censor','late_rigidity_difference','late_choice_difference'):
            v=[np.mean([r[metric] for r in rr if r['seed']==s]) for s in sorted({r['seed'] for r in rr})]
            recovery_summary.append(dict(memory=memory,metric=metric,**interval(v)))
    write_csv(args.out/'recovery_summary.csv',recovery_summary)
    # Replication strata: population, topology, balance; no pooling agents.
    sensitivity=[]
    for n,topo,balance,metric in itertools.product((30,60,120),('ring','random','hub'),('equal','unequal'),('choice_excess','cooperation','rigid','window_excluded')):
        suite='factorial' if n==60 else 'population'
        v=contrast(metric,1,'stress',1,0,suite=suite,split='replication',n=n,topology=topo,balance=balance,behavior=1,memory=1,transitions=1,identity=.7)
        sensitivity.append(dict(n=n,topology=topo,balance=balance,metric=metric,**v))
    write_csv(args.out/'population_topology_sensitivity.csv',sensitivity)
    sweep=[]
    for decay,scarcity,metric in itertools.product((.85,.97,.995),(.35,.55,.85),('choice_excess','cooperation','rigid','window_excluded')):
        a=seed_means(select(suite='sweep',stress=1,decay=decay,scarcity=scarcity),metric,1)
        b=seed_means(select(suite='sweep',stress=0,decay=decay),metric,1)
        sweep.append(dict(decay=decay,scarcity=scarcity,metric=metric,**interval([a[s]-b[s] for s in sorted(a)])))
    write_csv(args.out/'parameter_sweep.csv',sweep)
    components=[]
    for kind,metric in itertools.product(('scarcity','time','information','combined'),('choice_excess','cooperation','rigid','window_excluded')):
        a=seed_means(select(suite='factorial' if kind=='combined' else 'stress_component',split='replication',stress=1,stress_kind=kind,behavior=1,memory=1,transitions=1,identity=.7),metric,1)
        b=seed_means(select(suite='factorial',split='replication',stress=0,behavior=1,memory=1,transitions=1,identity=.7),metric,1)
        components.append(dict(component=kind,metric=metric,**interval([a[s]-b[s] for s in sorted(a)])))
    write_csv(args.out/'stress_components.csv',components)
    # Explicit semantic sensitivity: target-label incoming nominations, per member.
    gi={k:i for i,k in enumerate(schema['groups'])};sem=[]
    for target in range(6):
        byseed={}
        for i in select(suite='semantics',semantic=-.7,semantic_target=target,label_shift=0):
            m=meta[i];j=select(suite='semantics',seed=m['seed'],topology=m['topology'],semantic=0.)[0]
            def outcome(ix):
                gr=arr['groups'][ix];mask=(gr[:,gi['label_id']]==target)&(gr[:,gi['phase']]==1)
                return float(gr[mask,gi['incoming_per_member']][0])
            byseed.setdefault(m['seed'],[]).append(outcome(i)-outcome(j))
        sem.append(dict(target=target,**interval([np.mean(v) for v in byseed.values()])))
    write_csv(args.out/'semantic_targets.csv',sem)
    # Descriptive alliance proxy: top three reciprocal, opportunity-adjusted
    # cross-group ties. No intention or coalition agreement is represented.
    pi={k:i for i,k in enumerate(schema['pairs'])};alliances=[]
    for i in select(suite='factorial',split='replication',behavior=1,memory=1,transitions=1,identity=.7):
        tops=[];strengths=[]
        for p in range(3):
            vals=arr['pairs'][i,p*36:(p+1)*36]
            rates=np.divide(vals[:,pi['cooperation']],vals[:,pi['opportunities']],out=np.full(36,np.nan),where=vals[:,pi['opportunities']]>0).reshape(6,6)
            weights=[((s,d),min(rates[s,d],rates[d,s])) for s in range(6) for d in range(s+1,6) if np.isfinite(rates[s,d]) and np.isfinite(rates[d,s])]
            ordered=sorted(weights,key=lambda x:x[1],reverse=True)[:3]
            tops.append(set(x[0] for x in ordered));strengths.append(float(np.mean([x[1] for x in ordered])))
        alliances.append(dict(seed=meta[i]['seed'],topology=meta[i]['topology'],balance=meta[i]['balance'],stress=meta[i]['stress'],
            baseline_to_stress_overlap=len(tops[0]&tops[1])/3,stress_to_recovery_overlap=len(tops[1]&tops[2])/3,
            baseline_strength=strengths[0],stress_strength=strengths[1],recovery_strength=strengths[2]))
    write_csv(args.out/'alliance_proxies.csv',alliances)
    # Random-choice negative control, opportunity-adjusted expectation zero.
    null_summary=[]
    for metric in ('choice_excess','coop_gap'):
        vals=seed_means(select(suite='random_null',split='replication'),metric,1)
        null_summary.append(dict(metric=metric,**interval(list(vals.values()))))
    # Full-model descriptive levels, useful for distinguishing relative effects.
    levels=[]
    for stress,phase,metric in itertools.product((0,1),(0,1,2),('choice_excess','cooperation','rigid','window_excluded','fragmentation','assortativity','influence_gini','switching')):
        vals=seed_means(select(suite='factorial',split='replication',behavior=1,memory=1,transitions=1,identity=.7,stress=stress),metric,phase)
        levels.append(dict(stress=stress,phase=phase,metric=metric,**interval(list(vals.values()))))
    write_csv(args.out/'full_model_levels.csv',levels)
    summary=dict(completed_ensemble_runs=len(tasks),label_comparisons=len(label_checks),label_all_exact=all(x['exact'] for x in label_checks),
        label_max_difference=max(x['max_metric_difference'] for x in label_checks),null_summary=null_summary,
        intervals='95% percentile bootstrap, 10,000 resamples of 12 independent seeds within split; unadjusted descriptive intervals; no p-value claims',
        suites={s:sum(m['suite']==s for m in meta) for s in sorted({m['suite'] for m in meta})},recovery=recovery_summary)
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2))
    plots(args.out,meta,arr,trace_idx,contrasts,components,sensitivity,sweep,sem)
    print(json.dumps(summary,indent=2))


def plots(out,meta,arr,ti,contrasts,components,sensitivity,sweep,sem):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':130,'savefig.dpi':180})
    def save(fig,name):
        fig.savefig(out/(name+'.png'),bbox_inches='tight');fig.savefig(out/(name+'.svg'),bbox_inches='tight');plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    for ax,metric,title in zip(axes,('choice_excess','cooperation','rigid'),('Choice above available same-group share','Cooperation per request','Modeled rigidity (0–1)')):
        for stress,color,label in ((0,'#187c7d','No stress'),(1,'#c16a27','Stress then recovery')):
            idx=[i for i,m in enumerate(meta) if m['suite']=='factorial' and m['split']=='replication' and m['behavior']==m['memory']==m['transitions']==1 and m['identity']==.7 and m['stress']==stress]
            seeds=sorted({meta[i]['seed'] for i in idx})
            curves=np.array([np.mean(arr['trace'][[i for i in idx if meta[i]['seed']==s],:,ti[metric]],axis=0) for s in seeds])
            boot=np.random.default_rng(89).integers(0,len(seeds),(2000,len(seeds)))
            means=curves[boot].mean(1);lo,hi=np.quantile(means,[.025,.975],axis=0)
            ax.plot(np.arange(120)+1,curves.mean(0),color=color,label=label,lw=1.5)
            ax.fill_between(np.arange(120)+1,lo,hi,color=color,alpha=.15)
        ax.axvspan(40.5,80.5,color='#999999',alpha=.14);ax.set_title(title);ax.set_xlabel('Round')
    axes[0].legend(fontsize=8);fig.suptitle('Explicit identity preference + behavior + memory + state change | 12 replication seeds',fontsize=12)
    save(fig,'recovery')
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    factors=('identity','behavior','memory','stress','transitions')
    for ax,metric,title in zip(axes,('choice_excess','cooperation'),('Effect on same-group choice excess','Effect on cooperation')):
        for offset,split,color in ((-.12,'discovery','#187c7d'),(.12,'replication','#c16a27')):
            for j,f in enumerate(factors):
                r=next(x for x in contrasts if x['split']==split and x['phase']==1 and x['metric']==metric and x['factor']==f)
                ax.errorbar(r['mean'],j+offset,xerr=[[r['mean']-r['lo']],[r['hi']-r['mean']]],fmt='o',color=color,label=split if j==0 else None,capsize=3)
        ax.set_yticks(range(5),['Identity preference 0 → 0.7','Small trait differences','Memory on','Stress on','State change on']);ax.axvline(0,color='grey',lw=.8);ax.set_title(title);ax.set_xlabel('Paired marginal effect; 95% seed interval')
    axes[1].legend();save(fig,'factorial_effects')
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for ax,metric,title in zip(axes,('choice_excess','cooperation'),('Effect of each stress component on choice','Effect of each stress component on cooperation')):
        rr=[x for x in components if x['metric']==metric]
        ax.bar(range(4),[x['mean'] for x in rr],color=['#77aaa8']*3+['#c16a27'])
        ax.errorbar(range(4),[x['mean'] for x in rr],yerr=[[x['mean']-x['lo'] for x in rr],[x['hi']-x['mean'] for x in rr]],fmt='none',color='black',capsize=3)
        ax.set_xticks(range(4),[x['component'] for x in rr]);ax.axhline(0,color='grey',lw=.8);ax.set_title(title)
    save(fig,'stress_components')
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    rr=[x for x in sweep if x['metric']=='cooperation']
    mat=np.array([x['mean'] for x in rr]).reshape(3,3)
    im=axes[0].imshow(mat,cmap='coolwarm',vmin=-.25,vmax=.25)
    for y,x in itertools.product(range(3),repeat=2):axes[0].text(x,y,f'{mat[y,x]:+.3f}',ha='center',va='center')
    axes[0].set_xticks(range(3),[.35,.55,.85]);axes[0].set_yticks(range(3),[.85,.97,.995]);axes[0].set_xlabel('Available resource pool');axes[0].set_ylabel('Memory retention per round');axes[0].set_title('Stress effect on cooperation');fig.colorbar(im,ax=axes[0],shrink=.8)
    axes[1].errorbar(range(6),[x['mean'] for x in sem],yerr=[[x['mean']-x['lo'] for x in sem],[x['hi']-x['mean'] for x in sem]],fmt='o',color='#c16a27',capsize=3)
    axes[1].set_xticks(range(6),['Ice','Water','Fog','Mist','Gas','Smoke']);axes[1].axhline(0,color='grey',lw=.8);axes[1].set_ylabel('Incoming choices per member, change');axes[1].set_title('Assumed dislike applied to each label in turn')
    save(fig,'sensitivity_semantics')
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for ax,metric in zip(axes,('choice_excess','cooperation')):
        for j,topo in enumerate(('ring','random','hub')):
            for bal,style in [('equal','-'),('unequal','--')]:
                rr=[next(x for x in sensitivity if x['n']==n and x['topology']==topo and x['balance']==bal and x['metric']==metric) for n in (30,60,120)]
                ax.errorbar([30,60,120],[x['mean'] for x in rr],yerr=[[x['mean']-x['lo'] for x in rr],[x['hi']-x['mean'] for x in rr]],fmt='o'+style,color=['#187c7d','#c16a27','#5b548e'][j],label=topo+' / '+bal,capsize=2)
        ax.axhline(0,color='grey',lw=.8);ax.set_title('Stress effect: '+metric.replace('_',' '));ax.set_xlabel('Agents')
    axes[1].legend(fontsize=7,ncol=2);save(fig,'population_topology')


if __name__=='__main__':main()
