"""Original scientific plots of the fifth batch and its measured controls."""
import json
import os
from pathlib import Path
ROOT=Path(__file__).parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.plot-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
import numpy as np

COLORS=['#e6e6e6','#a51929','#dd3841','#f57c77','#205e37','#439f5f','#8bc66b','#222877','#444eb2','#8d9fe0']
BLUE,ORANGE,TEAL='#236783','#d36c37','#348b72'


def saved(name):return json.loads((ROOT/(name+'_results.json')).read_text())
def save(fig,name):
    fig.savefig(ROOT/'figures'/(name+'.png'),dpi=130,bbox_inches='tight');plt.close(fig)


def switching():
    d=saved('heteroclinic');three=d['three_state'];nine=d['nine_state']
    fig,axes=plt.subplots(2,2,figsize=(13,8),layout='constrained')
    ax=axes[0,0];xyz=np.array(three['cases'][0]['trajectory'])[:,1:]
    shares=xyz/xyz.sum(axis=1,keepdims=True)
    vertices=np.array([[0,0],[1,0],[.5,np.sqrt(3)/2]])
    p=shares@vertices;ax.plot(p[:,0],p[:,1],color=BLUE,lw=.8)
    ax.plot(*np.vstack([vertices,vertices[:1]]).T,':',color='gray')
    for i,(x,y) in enumerate(vertices):ax.text(x,y+(.03 if i==2 else -.06),f'State {i+1}',ha='center')
    ax.set_aspect('equal');ax.axis('off');ax.set_title('Approaching a three-saddle cycle')
    ax=axes[0,1]
    for case,color in zip(three['cases'],(BLUE,ORANGE,TEAL)):
        dwell=case['completed_dwells']
        ax.plot(range(1,len(dwell)+1),dwell,'o-',ms=3,color=color,label=f"Input = {case['drive']:g}")
    ax.set(xlabel='Completed visit number',ylabel='Time above dominance threshold',title='Small constant input limits the growing pauses')
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    ax=axes[1,0]
    for k,case in enumerate(nine['conditions']):
        values=[r['within_fraction'] for r in case['runs']]
        ax.scatter([k+(i-7.5)*.02 for i in range(len(values))],values,color=[BLUE,TEAL,ORANGE][k],s=18)
        mean=case['within_fraction_by_run'];a,b=mean['normal95']
        ax.errorbar(k,mean['mean'],yerr=[[mean['mean']-a],[b-mean['mean']]],fmt='ks',capsize=5)
    ax.set_xticks(range(3),['Within favored','Balanced','Between favored'])
    ax.set(ylim=(0,1),ylabel='Within-group share of classified transitions',title='Same 18 connections; different interaction rates')
    ax.text(.02,.05,'16 matched starts per setting; dots are individual runs',transform=ax.transAxes,fontsize=8)
    ax=axes[1,1];row=np.array(nine['conditions'][0]['runs'][0]['trajectory'])
    for i in range(9):ax.plot(row[:,0],row[:,i+1],color=COLORS[i+1],lw=.8)
    ax.set(xlabel='Time',ylabel='Activity',title='Nine activity states take turns')
    save(fig,'heteroclinic_switching')


def chain_patterns():
    d=saved('pacemaker');fig,axes=plt.subplots(2,2,figsize=(14,8),layout='constrained')
    cmap=ListedColormap(COLORS);norm=BoundaryNorm(np.arange(-.5,10.5),10)
    cases=d['representatives']+[d['controls'][0]]
    titles=['Selected within-group pattern','Selected between-group pattern','Control: all couplings removed']
    for ax,case,title in zip([axes[0,0],axes[0,1],axes[1,0]],cases,titles):
        labels=np.array(case['labels'])
        im=ax.imshow(labels,origin='lower',aspect='auto',extent=(0,d['duration'],.5,16.5),cmap=cmap,norm=norm,interpolation='nearest')
        ax.set(xlabel='Time',ylabel='Unit position',title=title,yticks=[1,4,8,12,16])
    colorbar=fig.colorbar(im,ax=[axes[0,0],axes[0,1],axes[1,0]],ticks=list(range(10)),shrink=.75,pad=.015)
    colorbar.set_label('Dominant item; 0 = no clear dominance')
    ax=axes[1,1]
    for case,label,color in zip(d['representatives']+d['controls'],
            ['Within pattern','Between pattern','Uncoupled','Open chain'],[BLUE,ORANGE,'#777777',TEAL]):
        ax.plot(range(1,17),case['same_time_agreement_by_unit'],'o-',ms=3,label=label,color=color)
    ax.set(xlabel='Unit position',ylabel='Same-time match to pacemaker',ylim=(-.03,1.03),title='Measure timing agreement, not just stripes')
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    save(fig,'pacemaker_patterns')


def memory_and_quench():
    d=saved('memory_inference');q=saved('quench');fig,axes=plt.subplots(2,2,figsize=(14,8),layout='constrained')
    ax=axes[0,0];rows=d['memory']['configurations']
    for name,color in zip(dict.fromkeys(x['name'] for x in rows),(BLUE,ORANGE,TEAL,'#9678a4')):
        points=[x for x in rows if x['name']==name]
        ax.semilogx([x['epsilon'] for x in points],[x['exact_conditional_gap'] for x in points],'-',color=color,label=name)
        ax.scatter([x['epsilon'] for x in points],[x['measured_conditional_gap'] for x in points],s=16,color=color)
    ax.set(xlabel='Noise scale at the final readout',ylabel='Difference between history-conditioned probabilities',ylim=(-.03,1.03),title='Local memory can survive or be erased')
    ax.legend(fontsize=7,loc='center right');ax.grid(alpha=.2)
    ax=axes[0,1];cases=d['inference']['cases'];x=np.arange(2)
    ax.bar(x-.18,[c['maximum_parameter_error'] for c in cases],width=.36,color=BLUE,label='Largest interaction-rate error')
    ax.bar(x+.18,[c['heldout_max_state_error'] for c in cases],width=.36,color=ORANGE,label='Largest held-out activity error')
    ax.set_xticks(x,['Exact activity observations','Log-measurement noise SD 0.0001'])
    ax.set(yscale='log',ylabel='Absolute error',title='Recover rules, then test an unseen trajectory')
    ax.legend(fontsize=8);ax.text(.03,.5,'Excited training data: rank 9\nEquilibrium-only data: rank 1 (not identifiable)',transform=ax.transAxes,fontsize=9,bbox=dict(facecolor='white',edgecolor='none',alpha=.9))
    ax=axes[1,0]
    for case,color in zip([c for c in q['cases'] if c['pre_quench_time']==50],(BLUE,TEAL,ORANGE,'#9678a4')):
        ax.plot(case['times'],case['first_component_relative_deviation'],label=f"After change: gamma = {case['gamma_after']}",color=color,lw=.9)
    ax.set(xlabel='Time since parameter change',ylabel='Activity 1 relative to its new equilibrium',xlim=(0,1000),ylim=(-1.05,1.05),title='Damped oscillations continue after the change')
    ax.legend(fontsize=8);ax.axhline(0,color='gray',lw=.5)
    ax=axes[1,1]
    gammas=sorted(set(c['gamma_after'] for c in q['cases']))
    for phase,marker,color in [(50,'o',BLUE),(150,'s',TEAL),(300,'^',ORANGE)]:
        cases=[c for c in q['cases'] if c['pre_quench_time']==phase]
        for i,c in enumerate(cases):
            t=c['relaxation_time'];ax.scatter(i,t if t is not None else 4000,marker=marker,color=color,label=f'State at t = {phase}' if i==0 else None)
            if t is None:ax.annotate('Not confirmed\nby t = 4,000',(i,4000),xytext=(18,-10),textcoords='offset points',fontsize=8)
    ax.set_xticks(range(4),[str(g) for g in gammas]);ax.set(yscale='log',xlabel='Gamma after the change',ylabel='Confirmed settling time',title='Quench depth and the starting state both matter')
    ax.legend(fontsize=8,loc='lower left');ax.grid(alpha=.2)
    save(fig,'memory_inference_quench')


def build_figures():switching();chain_patterns();memory_and_quench()


def html_section():
    d=saved('heteroclinic');p=saved('pacemaker');m=saved('memory_inference');q=saved('quench')
    within,between=p['representatives'];pair=d['nine_state']['paired_within_preferred_minus_between_preferred']
    return f'''<section id="heteroclinic"><h2>Batch 5 · switching, synchronization, memory, and stopping</h2>
<p>The new pages become four executable experiments: saddle-to-saddle switching, a pacemaker with 15 driven units, a local memory diagnostic with an inference baseline, and a sudden parameter change that stops oscillations. These are activity-state models; the earlier 12,800 SIMS coordination runs remain a separate experiment.</p>
<div class="equation">xᵢ′ = xᵢ (1 − Σⱼ Bᵢⱼ xⱼ)</div>
<p>In the three-state case, the completed pauses grow from {d['three_state']['cases'][0]['completed_dwells'][0]:.2f} to {d['three_state']['cases'][0]['completed_dwells'][-1]:.2f} time units. A constant positive input limits this growth in the tested window. The input changes the equations; it is not a numerical floor or a noise simulation.</p>
<figure><img src="figures/heteroclinic_switching.png" alt="Three-saddle trajectory, growing dwell times, and nine-state transition preferences"><figcaption>Sixteen matched starts per nine-state rate setting. Swapping e and f changes the mean within-group transition fraction by {100*pair['mean']:.1f} percentage points, with a paired approximate 95% interval of {100*pair['normal95'][0]:.1f}–{100*pair['normal95'][1]:.1f} points. Some threshold-detected jumps are unclassified and are retained in the data.</figcaption></figure>
<h3>The sixteen-unit synchronization figure</h3>
<p>The primary source uses a directed chain closed by a weak return connection: forward strength 1.5, closure strength 0.01, pacemaker γ=1.05, driven γ=1.47. The same settings produced within-group-dominated paths in {p['within_path_seeds']} of {p['seeds']} starts and between-group-dominated paths in {p['between_path_seeds']}. These counts describe our selected initial-state distribution and observation window.</p>
<figure><img src="figures/pacemaker_patterns.png" alt="Two sixteen-unit synchronization patterns, an uncoupled control, and measured timing agreement"><figcaption>Colors show the strongest of nine activity components when its share is at least 25% and its lead is at least 1 percentage point. Gray means no clear dominance. The two panels are selected examples, not average trajectories.</figcaption></figure>
<p>For the selected within-group and between-group patterns, the last unit matches the pacemaker at the same sampled time in {within['same_time_agreement_by_unit'][-1]:.1%} and {between['same_time_agreement_by_unit'][-1]:.1%} of qualified observations after t=1,000. Their amplitudes differ. Removing every coupling leaves the driven units without clear dominance; the open-chain control also synchronizes over this finite window. Weak closure is therefore part of the source configuration, not a demonstrated requirement for all entrainment.</p>
<h3>What carries memory, and what can be learned?</h3>
<p>The linear saddle diagnostic checks x′=λx and y′=−cy. At exit, y retains a factor ε<sup>c/λ</sup>. Relative to readout noise of size ε, the retained offset grows when c/λ&lt;1 and shrinks when c/λ&gt;1. A later saddle can erase it. We verify the formula and the resulting history-conditioned branch probabilities; this is a declared local model, not a full noisy-network or delay-learning reconstruction.</p>
<p>A separate least-squares baseline recovers the nine-state interaction matrix from complete activity observations and predicts an unseen starting state. The maximum interaction-rate error is {m['inference']['cases'][0]['maximum_parameter_error']:.2g} with clean observations and {m['inference']['cases'][1]['maximum_parameter_error']:.2g} with added measurement noise. Equilibrium-only observations have rank 1 and cannot determine the matrix uniquely. The review's adaptive teacher algorithm is distinct from this transparent baseline.</p>
<figure><img src="figures/memory_inference_quench.png" alt="Memory retention and erasure, interaction inference errors, damped quench dynamics, and settling times"><figcaption>Derived controls make the observation requirements explicit. Quench tests change γ from 1.05 to four stable-coexistence settings, each from three different points along a switching trajectory.</figcaption></figure>
<h3>Stopping has its own time scale</h3>
<p>After changing γ to 1.47, the three tested starting states settle in 953 and 3,113 time units, or fail to confirm settling by t=4,000. At γ=2.5, their times are 34.5, 82, and 180. Settling means every component stays within 5% of its new equilibrium through the remaining observation window, with at least 100 time units of confirmation. This is a finite-horizon measurement. The complex stable eigenvalues explain damped oscillations in these selected models.</p>
<details><summary>Validation and source boundaries</summary><p>The 18 intended nine-state connections are checked in invariant coordinate planes. A connection is a nonconstant orbit approaching its source in backward time and its target in forward time; staying at an equilibrium is not counted as a self-connection. The plane restrictions give one unstable source direction, a stable target, no positive interior equilibrium, and negative Dulac divergence. Numerical arrivals support this analytic construction. Jacobians are compared with finite differences; an isolated component is checked against the logistic solution. Smaller steps preserve the selected transition sequences. The worst selected pacemaker trajectory difference is about 0.00102, while same-time agreement changes by under 0.1 percentage point. The 12 quench runs have four step-refinement controls. No source screenshots are report assets.</p>
<p>Sources, equations, parameter choices, qualifications, and commands are in <a href="HETEROCLINIC_METHODS.md">HETEROCLINIC_METHODS.md</a>. Data: <a href="heteroclinic_results.json">switching</a>, <a href="pacemaker_results.json">pacemaker</a>, <a href="memory_inference_results.json">memory and inference</a>, <a href="quench_results.json">quenches</a>. The work uses the primary papers by <a href="https://arxiv.org/abs/1806.11039">Voit and Meyer-Ortmanns</a>, <a href="https://arxiv.org/html/2112.12642v2#S4.SS3">Thakur and Meyer-Ortmanns</a>, <a href="https://arxiv.org/html/1302.0984v2#S4.SS3">Ashwin and Postlethwaite</a>, and <a href="https://doi.org/10.1063/5.0166803">Aravind and Meyer-Ortmanns</a>.</p></details></section>'''


if __name__=='__main__':build_figures();print('Built three original heteroclinic figures.')
