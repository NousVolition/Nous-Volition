from pathlib import Path
import csv,json,argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import t
from model import POLICIES,LABELS
ROOT=Path(__file__).resolve().parent
NAMES={'independent':'Independent','reciprocal':'Connected, total-focused','partitioned':'Partitioned','priority_hierarchy':'One member has priority',
       'override_budgets':'Requests can be exceeded','hierarchy_and_override':'Priority + overrides','recording_only':'Recording only','costly_assessment':'Assessment time cost'}
def read(path):
    with path.open(encoding='utf-8') as f:return list(csv.DictReader(f))
def ci(v):
    v=np.array(v,float);h=t.ppf(.975,len(v)-1)*v.std(ddof=1)/len(v)**.5
    return dict(mean=float(v.mean()),low=float(v.mean()-h),high=float(v.mean()+h))
def analyze(data,out):
    out.mkdir(parents=True,exist_ok=True);cases=read(data/'cases.csv');extra=read(data/'sensitivity.csv');people=read(data/'members.csv')
    sub=[r for r in cases if r['split']=='replication' and r['heterogeneity']=='0.55' and r['scarcity']=='1.4']
    result={p:{m:ci([float(r[m]) for r in sub if r['policy']==p]) for m in ('mean_needs_met','minimum_needs_met','total_excess_over_requests','leader_needs_met','others_needs_met')} for p in POLICIES}
    rows=read(data/'paired_contrasts.csv')
    contrasts=[r for r in rows if r['split']=='replication' and r['heterogeneity']=='0.55' and r['scarcity']=='1.4']
    # Position rotation: first average within each seed, then form intervals.
    arrays=np.load(data/'allocations.npz',allow_pickle=False)
    leader_effect=[];others_effect=[]
    for seed in range(41000,41012):
        base=next(r for r in sub if int(r['seed'])==seed and r['policy']=='reciprocal')
        met=arrays['needs_met'][int(base['case_id'])]
        rotations=[r for r in extra if r['kind']=='leader_rotation' and int(r['seed'])==seed and r['respect']=='True']
        leader_effect.append(np.mean([float(r['leader_needs_met'])-met[int(r['parameter'])] for r in rotations]))
        others_effect.append(np.mean([float(r['others_needs_met'])-np.delete(met,int(r['parameter'])).mean() for r in rotations]))
    summary=dict(representative_setting=dict(split='replication',seeds=12,heterogeneity=.55,scarcity=1.4),
        policies=result,paired_contrasts=contrasts,rotated_priority_leader_gain=ci(leader_effect),rotated_priority_others_change=ci(others_effect),
        unit_tests=19,observational_validation=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold'})
    def save(fig,name):
        fig.savefig(out/(name+'.png'),dpi=160,bbox_inches='tight');fig.savefig(out/(name+'.svg'),bbox_inches='tight');plt.close(fig)
    policies=list(POLICIES);y=np.arange(len(policies));colors=['#64748b','#087f8c','#e09538','#725ba8','#c45436','#b1597f','#459c83','#8c705e']
    fig,ax=plt.subplots(1,3,figsize=(14,5.5),sharey=True,constrained_layout=True)
    for k,(metric,title,scale) in enumerate([('mean_needs_met','Mean needs met',100),('minimum_needs_met','Least-served member',100),('total_excess_over_requests','Time beyond requests',1)]):
        vals=[result[p][metric]['mean']*scale for p in policies]
        ax[k].barh(y,vals,color=colors,alpha=.85,height=.6)
        for i,p in enumerate(policies):
            v=np.array([float(r[metric])*scale for r in sub if r['policy']==p]);jitter=np.linspace(-.15,.15,len(v))
            ax[k].scatter(v,y[i]+jitter,s=10,c='#18333e',alpha=.5,zorder=4)
        ax[k].set(title=title,xlabel='Percent of needs bundle' if scale==100 else 'Total time units (7 members)');ax[k].grid(axis='x',alpha=.15)
    ax[0].set_yticks(y,[NAMES[p] for p in policies]);ax[0].invert_yaxis()
    fig.suptitle('Same seven people; different organizational rules\nDifferentiated skills, higher demand, 12 replication seeds; dots are seed outcomes',fontsize=12)
    save(fig,'outcomes')
    chosen=['independent','reciprocal','priority_hierarchy','override_budgets'];matrix=[];work=[]
    for p in chosen:
        rr=sorted([r for r in people if r['seed']=='41000' and r['heterogeneity']=='0.55' and r['scarcity']=='1.4' and r['policy']==p],key=lambda r:int(r['member']))
        matrix.append([float(r['needs_met'])*100 for r in rr]);work.append([float(r['actual_work'])/float(r['requested']) for r in rr])
    fig,ax=plt.subplots(2,1,figsize=(11,7),constrained_layout=True)
    for axis,v,title,fmt,vm,cmap in [(ax[0],matrix,'Each member: percent of needs met','.0f',100,'YlGnBu'),(ax[1],work,'Each member: work / requested limit','.2f',2,'YlOrRd')]:
        im=axis.imshow(v,vmin=0,vmax=vm,cmap=cmap,aspect='auto');axis.set_xticks(range(7),LABELS);axis.set_yticks(range(4),[NAMES[p] for p in chosen]);axis.set_title(title)
        for i in range(4):
            for j in range(7):axis.text(j,i,format(0. if abs(v[i][j])<1e-8 else v[i][j],fmt),ha='center',va='center',color='white' if v[i][j]>vm*.6 else '#152e3a')
        fig.colorbar(im,ax=axis,shrink=.75)
    fig.suptitle('One fictional community, seed 41000\nWater is the arbitrary priority position here; rotation controls move priority through all seven names.',fontsize=12)
    save(fig,'members')
    fig,ax=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
    for metric,label in [('leader_needs_met','Priority member'),('others_needs_met','Other six members')]:
        xs=[1,1.5,2,3,5];av=[];err=[]
        for x in xs:
            v=[float(r[metric]) for r in extra if r['split']=='replication' and r['kind']=='priority_strength' and float(r['parameter'])==x]
            z=ci(v);av.append(z['mean']*100);err.append((z['high']-z['mean'])*100)
        ax[0].errorbar(xs,av,yerr=err,marker='o',label=label,capsize=3)
    ax[0].set(title='Unequal priority redistributes fulfillment',xlabel='Priority weight (everyone else = 1)',ylabel='Mean needs met (%)');ax[0].legend(fontsize=8)
    xs=[0,.05,.1,.15,.2];av=[];err=[]
    for x in xs:
        z=ci([float(r['mean_needs_met']) for r in extra if r['split']=='replication' and r['kind']=='assessment_cost' and float(r['parameter'])==x]);av.append(z['mean']*100);err.append((z['high']-z['mean'])*100)
    ax[1].errorbar(xs,av,yerr=err,marker='o',capsize=3,color='#087f8c');ax[1].set(title='Assessment modeled as time cost only',xlabel='Assessment time per member',ylabel='Mean needs met (%)')
    for a in ax:a.grid(alpha=.2)
    fig.suptitle('Assumption sensitivities; 95% seed-t intervals, not human-population estimates',fontsize=12)
    save(fig,'sensitivity')
    print(json.dumps({'representative_means':{p:result[p]['mean_needs_met']['mean'] for p in policies},'rotated_priority_leader_gain':summary['rotated_priority_leader_gain'],'rotated_priority_others_change':summary['rotated_priority_others_change']},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=ROOT/'data');p.add_argument('--out',type=Path,default=ROOT/'analysis');a=p.parse_args();analyze(a.data,a.out)
