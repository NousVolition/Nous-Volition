"""Additional diagnostics explicitly added after the main ensemble analysis."""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from model import Config,run,initialize,network_metrics,LABELS
from analyze import write_csv,interval


def main():
    rows=[]
    # New diagnostic runs: frozen affiliations prevent mixing state and name nulls.
    for seed in range(9100,9112):
        for topology in ('ring','random','hub'):
            for identity in (0.,.7):
                c=Config(seed=seed,topology=topology,identity=identity,memory=1)
                r=run(c,True);w=np.zeros((60,60));g=np.array(r['initial_groups'])
                for ev in r['events'][80:]:np.add.at(w,(np.arange(60),ev[:,0]),ev[:,1])
                def q(groups):
                    total=w.sum();s=w.sum(1);d=w.sum(0)
                    return float((w*(groups[:,None]==groups[None,:])).sum()/total - np.dot(np.bincount(groups,weights=s,minlength=6),np.bincount(groups,weights=d,minlength=6))/total**2)
                observed=q(g);rng=np.random.default_rng(seed+18000)
                null=np.array([q(rng.permutation(g)) for _ in range(499)])
                rows.append(dict(seed=seed,topology=topology,identity=identity,observed_q=observed,
                    null_mean=float(null.mean()),null_lo=float(np.quantile(null,.025)),null_hi=float(np.quantile(null,.975)),
                    excess=observed-float(null.mean()),upper_tail_fraction=float((1+(null>=observed).sum())/500)))
    write_csv(Path('analysis/group_permutation_null.csv'),rows)
    leader=json.loads(Path('data/leadership.json').read_text())
    summary=[]
    for topo in ('ring','random','hub'):
        for heterogeneity in (0,1):
            rr=[r for r in leader if r['topology']==topo and r['heterogeneity']==heterogeneity and r['seed']>=9000]
            summary.append(dict(topology=topo,heterogeneity=heterogeneity,
                high_site_mean_shift=float(np.mean([r['original_high_site_effect'] for r in rr])),
                old_high_identity_mean_shift=float(np.mean([r['old_high_identity_effect'] for r in rr])),
                max_min_ratio=float(np.mean([r['max_min_ratio'] for r in rr])),
                max_site_difference=max(r['site_max_difference'] for r in rr)))
    write_csv(Path('analysis/leadership_summary.csv'),summary)
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for j,topo in enumerate(('ring','random','hub')):
        rr=[r for r in rows if r['topology']==topo]
        for h,off in ((0.,-.12),(.7,.12)):
            vals=[r['excess'] for r in rr if r['identity']==h];v=interval(vals)
            axes[0].errorbar(j+off,v['mean'],yerr=[[v['mean']-v['lo']],[v['hi']-v['mean']]],fmt='o',color='#187c7d' if h==0 else '#c16a27',label=f'Identity preference {h}' if j==0 else None,capsize=3)
    axes[0].set_xticks(range(3),['ring','random','hub']);axes[0].set_ylabel('Observed Q minus shuffled-group mean');axes[0].axhline(0,color='grey',lw=.8);axes[0].legend(fontsize=8);axes[0].set_title('Fixed-affiliation permutation diagnostic')
    for h,off,color in ((0,-.18,'#187c7d'),(1,.18,'#c16a27')):
        rr=[r for r in summary if r['heterogeneity']==h]
        axes[1].bar(np.arange(3)+off,[r['max_min_ratio'] for r in rr],width=.35,color=color,label='Identical agents' if h==0 else 'Assumed individual attraction')
    axes[1].set_xticks(range(3),['ring','random','hub']);axes[1].set_ylabel('Largest / smallest copying-response score');axes[1].set_title('Arrangement can create unequal influence');axes[1].legend(fontsize=8)
    fig.savefig('analysis/network_diagnostics.png',dpi=180,bbox_inches='tight');fig.savefig('analysis/network_diagnostics.svg',bbox_inches='tight');plt.close(fig)
    attribution=json.loads(Path('data/synthetic_attribution.json').read_text());blame=[]
    for target in range(6):
        a={r['seed']:r['share'] for r in attribution if r['target']==target and r['bias']==.7 and r['seed']>=9000}
        b={r['seed']:r['share'] for r in attribution if r['target']==target and r['bias']==0 and r['seed']>=9000}
        blame.append(dict(label=LABELS[target],**interval([a[s]-b[s] for s in a])))
    write_csv(Path('analysis/synthetic_attribution.csv'),blame)
    Path('analysis/diagnostics_execution.json').write_text(json.dumps(dict(status='executed after main analysis; exploratory diagnostic',additional_runs=len(rows),permutations_per_run=499,leadership_source='data/leadership.json',attribution_source='data/synthetic_attribution.json'),indent=2))
    print('Completed 72 additional trajectories and 35,928 group permutations.')


if __name__=='__main__':main()
