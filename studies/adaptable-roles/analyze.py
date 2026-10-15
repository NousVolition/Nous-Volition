"""Summarize synthetic seed variation and draw exportable scientific figures."""
from pathlib import Path
import argparse,csv,json
import numpy as np
from scipy.stats import t as student_t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from model import LABELS,POLICIES
from run_study import write_csv
ROOT=Path(__file__).resolve().parent
NAMES=dict(shared='Shared from start',assigned='Assigned; continues',remove_label='Label removed only',
 target_stops='Target stops; no handoff',target_stops_handoff='Target stops; handoff',
 share_after='Share after round 30',all_stop='Everyone stops at 30',none='Nobody takes extra work')

def read(path):
    with path.open(encoding='utf-8') as f:return list(csv.DictReader(f))

def interval(v):
    v=np.asarray(v,float);mean=v.mean();err=student_t.ppf(.975,len(v)-1)*v.std(ddof=1)/np.sqrt(len(v))
    return dict(mean=float(mean),low=float(mean-err),high=float(mean+err),n_seeds=len(v))

def main(data,out):
    out.mkdir(exist_ok=True,parents=True);rows=read(data/'cases.csv');extra=read(data/'sensitivity.csv')
    metrics=list(rows[0])[6:];summary=[];contrasts=[]
    for split in ('discovery','replication'):
     for load in ('.8','3.6'):
      group=[r for r in rows if r['split']==split and float(r['load'])==float(load)]
      seeds=sorted({r['seed'] for r in group})
      for policy in POLICIES:
       for m in metrics:
        vals=[np.mean([float(r[m]) for r in group if r['seed']==s and r['policy']==policy]) for s in seeds]
        summary.append(dict(split=split,load=float(load),policy=policy,metric=m,**interval(vals)))
        if policy!='assigned':
         base=[np.mean([float(r[m]) for r in group if r['seed']==s and r['policy']=='assigned']) for s in seeds]
         contrasts.append(dict(split=split,load=float(load),policy=policy,reference='assigned',metric=m,**interval(np.array(vals)-base)))
    write_csv(out/'summary.csv',summary);write_csv(out/'paired_contrasts.csv',contrasts)
    roles=[]
    for label in LABELS:
     for policy in POLICIES:
      sub=[r for r in rows if r['split']=='replication' and r['load']=='3.6' and r['target']==label and r['policy']==policy]
      roles.append(dict(target=label,policy=policy,**{m:float(np.mean([float(r[m]) for r in sub])) for m in metrics}))
    write_csv(out/'all_seven_roles.csv',roles)
    sensitivities=[]
    for variant in sorted({r['variant'] for r in extra}):
     for policy in ('assigned','remove_label','target_stops_handoff'):
      sub=[r for r in extra if r['variant']==variant and r['policy']==policy]
      for m in metrics:
       vals=[np.mean([float(r[m]) for r in sub if r['seed']==seed]) for seed in sorted({r['seed'] for r in sub})]
       sensitivities.append(dict(variant=variant,policy=policy,metric=m,**interval(vals)))
    write_csv(out/'sensitivity_summary.csv',sensitivities)
    lookup={(r['policy'],r['metric']):r for r in summary if r['split']=='replication' and r['load']==3.6}
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':145})
    fig,axes=plt.subplots(2,2,figsize=(14,9),layout='constrained')
    for ax,m,title,factor in zip(axes.flat,['coordination_met','target_work','target_plans_met','others_work'],
        ['Coordination needs completed (%)','Target: extra work (time/round)',
         'Target: original plans completed (%)','Other members: extra work (time/person/round)'],[100,1,100,1]):
      means=np.array([lookup[p,m]['mean'] for p in POLICIES])*factor
      err=np.array([lookup[p,m]['high']-lookup[p,m]['mean'] for p in POLICIES])*factor
      y=np.arange(len(POLICIES));ax.barh(y,means,xerr=err,color=['#187d92','#cd7434','#9c7799','#566574','#3e9c84','#3e9c84','#a5afb5','#a5afb5'],capsize=2)
      ax.set_yticks(y,[NAMES[p] for p in POLICIES]);ax.invert_yaxis();ax.set_title(title)
    fig.suptitle('After round 30: both the work and the consequences move\nHigher demand; means and 95% intervals across 12 synthetic seeds',fontsize=14)
    fig.savefig(out/'outcomes.png');plt.close(fig)
    choices=['assigned','target_stops','target_stops_handoff','share_after']
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for ax,m,title in zip(axes,['target_work','coordination_met'],['Target extra work per round','Group coordination completed (%)']):
      factor=100 if m=='coordination_met' else 1
      matrix=np.array([[next(r[m] for r in roles if r['target']==label and r['policy']==p)*factor for p in choices] for label in LABELS])
      im=ax.imshow(matrix,cmap='YlGnBu',vmin=0,vmax=100 if factor==100 else .65)
      ax.set_xticks(range(4),['Continues','Stops','Stops +\nhandoff','Shares']);ax.set_yticks(range(7),LABELS);ax.set_title(title)
      for (i,j),v in np.ndenumerate(matrix):ax.text(j,i,f'{v:.1f}' if factor==100 else f'{v:.3f}',ha='center',va='center',color='white' if v>(50 if factor==100 else .325) else '#142b39')
      fig.colorbar(im,ax=ax,shrink=.8)
    fig.suptitle('Every member takes the role; names do not cause these differences')
    fig.savefig(out/'all_seven.png');plt.close(fig)
    times=np.load(data/'timelines.npz')['values'];fig,axes=plt.subplots(1,3,figsize=(14,4.7),layout='constrained')
    for p in ('assigned','remove_label','target_stops','target_stops_handoff','share_after'):
      ids=[int(r['case_id']) for r in rows if r['split']=='replication' and r['load']=='3.6' and r['policy']==p]
      v=times[ids].mean(0)
      for ax,col in zip(axes,(0,1,3)):ax.plot(np.arange(1,61),v[:,col],label=NAMES[p])
    for ax,title in zip(axes,('Coordination fraction completed','Target extra work per round','Initial request share sent to target')):
      ax.axvline(30.5,color='gray',ls='--');ax.set(xlabel='Round',title=title,ylim=(0,1.05))
    axes[0].legend(fontsize=8);fig.suptitle('A request can persist even when the person stops accepting it')
    fig.savefig(out/'timeline.png');plt.close(fig)
    result=dict(higher_demand_replication={p:{m:lookup[p,m] for m in metrics} for p in POLICIES},
      interpretation='Intervals quantify synthetic seed variation, not real people. All seven target rotations are averaged within seed before interval calculation.')
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({p:{m:round(lookup[p,m]['mean'],6) for m in ('coordination_met','target_work','target_plans_met','others_work','target_request_share')} for p in POLICIES},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=ROOT/'data');p.add_argument('--out',type=Path,default=ROOT/'analysis')
    a=p.parse_args();main(a.data,a.out)
