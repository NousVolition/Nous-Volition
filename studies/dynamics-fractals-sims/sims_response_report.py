"""Show the new dynamics operating inside the matched SIMS experiment."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
COLORS={'Menger L1':'#236783','Ring 20':'#d36c37','Complete 20':'#348b72'}
RATE_COLORS=['#236783','#d36c37','#348b72','#9266a2']


def data():return json.loads((ROOT/'sims_response_results.json').read_text())


def save(fig,name):
    fig.savefig(ROOT/'figures'/f'{name}.png',dpi=130,bbox_inches='tight');plt.close(fig)


def stability_figure(d):
    fig,axes=plt.subplots(2,2,figsize=(13,8.7),layout='constrained')
    ax=axes[0,0]
    for graph,color in COLORS.items():
        r=next(r for r in d['representative_traces'] if r['family']=='linear' and r['graph']==graph and r['condition']=='unstable spiral')
        ax.semilogy(r['time'],r['spread'],color=color,label=graph)
    ax.semilogy(r['time'],r['mean_norm'],':',color='#1b2935',lw=2,label='Collective displacement (all graphs)')
    ax.set(title='SIMS can align while their shared state grows',xlabel='Model time',ylabel='RMS spread or collective displacement')
    ax.legend(fontsize=8);ax.grid(alpha=.15)
    ax=axes[0,1]
    names=['center','stable spiral','unstable spiral','5.1.3','symmetric a=-1,b=0.5','symmetric a=-1,b=1','symmetric a=-1,b=1.5']
    values=np.array([[next(r['final_choice_unanimity_fraction'] for r in d['aggregates'] if r['family']=='linear' and r['graph']==g and r['condition']==c) for g in COLORS] for c in names])
    im=ax.imshow(values,vmin=0,vmax=1,cmap='Blues',aspect='auto')
    ax.set_xticks(range(3),list(COLORS));ax.set_yticks(range(7),['Center','Stable spiral','Unstable spiral','Saddle (5.1.3)','Reciprocal b = 0.5','Reciprocal b = 1','Reciprocal b = 1.5'])
    for i in range(7):
        for j in range(3):ax.text(j,i,f'{100*values[i,j]:.1f}%',ha='center',va='center',color='white' if values[i,j]>.55 else '#1b2935',fontsize=9)
    ax.set_title('Same choices at final time? · 32 matched starts')
    ax.text(.5,-.16,'All preferences must exceed +0.02 or fall below −0.02',transform=ax.transAxes,ha='center',fontsize=8)
    ax=axes[1,0]
    for condition,style in [('forward','-'),('reverse rule from 2 to 4','--')]:
        r=next(r for r in d['representative_traces'] if r['family']=='reversal' and r['graph']=='Menger L1' and r['condition']==condition)
        ax.plot(r['time'],r['mean_potential'],style,label=condition,color='#236783' if style=='-' else '#d36c37')
    ax.axvspan(2,4,color='#d36c37',alpha=.1)
    ax.set(title='Reversing the SIMS rule retraces the earlier motion',xlabel='Model time',ylabel='Mean sin(preference)');ax.legend(fontsize=8);ax.grid(alpha=.15)
    ax=axes[1,1]
    for i,(graph,color) in enumerate(COLORS.items()):
        rows=[r for r in d['runs'] if r['family']=='reversal' and r['graph']==graph and r['condition']!='forward']
        ax.scatter([i+(j-15.5)*.015 for j in range(len(rows))],[r['return_error_at_4'] for r in rows],color=color,s=17)
    ax.set_xticks(range(3),list(COLORS));ax.set(yscale='log',title='Measure the return error across all starts',ylabel='Largest participant return error at time 4')
    ax.text(.03,.97,'Step = 0.02\nSmaller-step controls saved separately',transform=ax.transAxes,fontsize=8,va='top');ax.grid(axis='y',alpha=.15)
    fig.suptitle('The supplied dynamics now act on 20 interacting SIMS',fontsize=16)
    save(fig,'sims_response_stability')


def rates_figure(d):
    fig,axes=plt.subplots(1,3,figsize=(15,4.7),layout='constrained')
    names=['H2O reference','density change','viscosity change','both changes']
    for ax,control in zip(axes[:2],['fixed input','same target']):
        for name,color in zip(names,RATE_COLORS):
            r=next(r for r in d['representative_traces'] if r['family']=='rate' and r['graph']=='Menger L1' and r['condition']==name+' / '+control)
            ax.plot(r['time'],r['mean_preference'],color=color,label=name.replace('H2O reference','Reference'))
        ax.axvline(4,color='#777777',ls=':',lw=1);ax.axhline(0,color='#cccccc',lw=.5)
        ax.set(title='Same input, different final targets' if control=='fixed input' else 'Hold the final target fixed',xlabel='Model time',ylabel='Population mean preference')
        ax.legend(fontsize=8);ax.grid(alpha=.15)
    ax=axes[2];x=np.arange(4)
    for offset,(graph,color) in zip([-.25,0,.25],COLORS.items()):
        rows=[next(r for r in d['aggregates'] if r['family']=='rate' and r['graph']==graph and r['condition']==name+' / same target') for name in names]
        values=[r['settling_among_confirmed']['mean'] for r in rows]
        ax.bar(x+offset,values,width=.24,color=color,label=graph)
    ax.set_xticks(x,['Reference','Density','Viscosity','Both']);ax.set(title='Response speed after the input reverses',ylabel='Time to remain within 5% of final target',ylim=(0,4.7))
    ax.legend(fontsize=8);ax.grid(axis='y',alpha=.15)
    fig.suptitle('Water-property ratios supply explicit response controls for SIMS · dimensionless time',fontsize=14)
    save(fig,'sims_response_rates')


def build_figures():
    d=data();stability_figure(d);rates_figure(d)


def html_section():
    d=data()
    return f'''<section id="sims-response"><h2>Batch 7 · the ideas operate inside the SIMS test</h2>
<p>Twenty SIMS now follow explicit continuous response rules derived from the supplied linear, reversible, and water-response examples. There are <strong>{d['total_new_sims_trajectories']:,} new matched trajectories</strong>: 672 linear-response runs, 192 reversal runs, and 768 response-rate runs. Each condition reuses 32 starting states across Menger, ring, and complete networks. The original 12,800 binary-choice runs retain their earlier rules.</p>
<p>A SIM has an expressed preference coordinate and, in the linear cases, a second response coordinate. Neighbor exchange reduces differences while the local dynamics can attract, rotate, or repel. These are stated modeling choices, recorded in the <a href="sims_response_protocol.json">protocol</a>. Agreement of choices, alignment of coordinates, and settling to a bounded state are measured separately.</p>
<figure><img src="figures/sims_response_stability.png" alt="SIMS alignment during collective growth, final choice agreement, reversal intervention and measured return errors"><figcaption>For the unstable-spiral rule, the collective displacement grows by exp(2.4), about 11 times, over the run. Strong enough neighbor exchange still makes the SIMS align. A group moving together need not be settling down.</figcaption></figure>
<h3>Reverse the rule and test whether the participants retrace</h3><p>The reversible network has the textbook two-participant system as an exact special case. It also has a strictly decreasing population potential under forward evolution. Reversing the sign of the rule from time 2 to 4 retraces the earlier motion; restoring it resumes attraction. Across all 96 reversal interventions, the largest return error is below 7.1×10⁻⁸. Eighteen smaller-step comparisons check the numerical accuracy.</p>
<h3>Change response speed and steady preference separately</h3><p>The saved 25 °C water-property ratios select four dimensionless SIMS response settings. Every SIM receives the same signal, which switches from positive to negative at time 4. A fixed-input comparison permits the final preference to change. A second comparison adjusts the input so that every setting has the same final target, isolating response speed.</p>
<figure><img src="figures/sims_response_rates.png" alt="SIMS responses with fixed input or a matched target, and measured settling times across networks"><figcaption>For Menger SIMS, the target-matched settings settle after about 3.7, 4.1, 3.1, and 3.4 model-time units. Settling uses a 5% tolerance and requires at least one unit of confirmation; it is measured on a 0.1 time grid.</figcaption></figure>
<p>The expansion adds 24 mathematical and participant-level tests. They check coupled equations against an independent integrator, exact collective modes, graph relabeling, the two-participant reduction, reversal convergence, target matching, and agreement measurements. Rates are experimental SIMS rules rather than measurements of participant behavior.</p>
<p><a href="SIMS_RESPONSE_METHODS.md">Rules, measurements, outcomes, and interpretation</a> · <a href="sims_response_results.json">All runs and controls</a> · <a href="test_sims_response.py">Executable tests</a></p></section>'''
