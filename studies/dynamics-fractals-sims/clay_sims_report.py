"""Show the active clay experiment and identify the prior Hug model as historical."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
GRAPHS=['Menger L1','Ring 20','Complete 20']
COLORS=['#236783','#d36c37','#348b72']


def data():return json.loads((ROOT/'clay_sims_results.json').read_text())


def build_figures():
    d=data();fig,axes=plt.subplots(2,2,figsize=(13,9),layout='constrained')
    r=next(x for x in d['representative_traces'] if x['graph']=='Menger L1' and x['stress_Pa']==20)
    ax=axes[0,0]
    for key,label,color in [('mean_total','Total','#243846'),('mean_elastic','Immediate elastic','#236783'),('mean_kelvin','Delayed recovery','#d36c37'),('mean_retained','Retained strain','#348b72')]:
        ax.plot(r['time'],100*np.array(r[key]),label=label,color=color,lw=2 if key=='mean_total' else 1.5)
    ax.axvspan(20,120,alpha=.07,color='#236783');ax.set(title='The clay formula now drives SIMS · 20 Pa row',xlabel='Time (s)',ylabel='Population mean strain (%)')
    ax.legend(fontsize=9);ax.grid(alpha=.15)
    ax=axes[0,1]
    for g,c in zip(GRAPHS,COLORS):
        r=next(x for x in d['representative_traces'] if x['graph']==g and x['stress_Pa']==20)
        ax.plot(r['time'],100*np.array(r['absolute_spread']),label=g,color=c)
    ax.set(title='Connections redistribute the initial retained pattern',xlabel='Time (s)',ylabel='Strain standard deviation (%)')
    ax.legend(fontsize=9);ax.grid(alpha=.15)
    ax=axes[1,0];stress=[10,20,30,40]
    for offset,g,c in zip([-.25,0,.25],GRAPHS,COLORS):
        vals=[next(x['mean_final_spread_ratio_to_uncoupled'] for x in d['aggregates'] if x['graph']==g and x['stress_Pa']==s) for s in stress]
        ax.bar(np.arange(4)+offset,100*np.array(vals),width=.24,label=g,color=c)
    ax.set_xticks(range(4),['10 Pa','20 Pa','30 Pa','40 Pa']);ax.set(title='Remaining differences relative to uncoupled SIMS',ylabel='Mean paired spread ratio at 420 s (%)',ylim=(0,100))
    ax.axhline(100,color='#777777',ls=':',lw=1);ax.legend(fontsize=9);ax.grid(axis='y',alpha=.15)
    ax=axes[1,1]
    vals=np.array([[next(x['final_response_sign_unanimous'] for x in d['aggregates'] if x['graph']==g and x['stress_Pa']==s) for g in GRAPHS] for s in stress])
    ax.imshow(vals,cmap='Blues',vmin=0,vmax=32,aspect='auto')
    for i in range(4):
        for j in range(3):ax.text(j,i,f'{vals[i,j]}/32',ha='center',va='center',color='white' if vals[i,j]>18 else '#1b2935')
    ax.set_xticks(range(3),GRAPHS);ax.set_yticks(range(4),['10 Pa row','20 Pa row','30 Pa row','40 Pa row']);ax.set_title('All response signs agree at the end?')
    ax.text(.5,-.16,'Every participant receives the same positive load; this measures response signs.',transform=ax.transAxes,ha='center',fontsize=8)
    fig.suptitle('Updated Hug/SIMS · Burgers clay deformation, recovery and retained strain',fontsize=16)
    fig.savefig(ROOT/'figures/clay_sims.png',dpi=125,bbox_inches='tight');plt.close(fig)


def html_section():
    d=data();error=max(s['max_strain_error'] for c in d['controls'] for s in c['independent_solvers'])
    return f'''<section id="clay"><h2>Current Hug/SIMS · the clay formula</h2>
<p>The Hug now uses the located wet-kaolin Burgers formula: immediate elastic deformation, delayed recovery, and retained viscous strain. This replaces the pressure-threshold rule for current SIMS work. The earlier 384 Hug runs remain labeled as historical below.</p>
<p><strong>384 clay-based SIMS trajectories</strong> compare four published coefficient rows, three networks, and 32 matched initial retained patterns. Another 128 uncoupled runs isolate the effect of connections; 24 independent solver runs check the new calculation. Loading lasts from 20 to 120 seconds, followed by recovery through 420 seconds. Both limits of the loading and release jumps are retained.</p>
<figure><img src="figures/clay_sims.png" alt="Clay response components, network-dependent retained-pattern relaxation, comparison with uncoupled participants and final response signs"><figcaption>The mean response follows the original clay formula on every graph. Connections affect differences between SIMS. Top-right curves use the first predefined seed; bottom panels summarize all 32 starts. The four coefficient sets come from different fitted stress steps; their differences cannot be attributed to stress alone.</figcaption></figure>
<p>For the 20 Pa coefficient row, final spread is 24.6% of the uncoupled comparison on Menger, 30.7% on the ring, and 10.0% on the complete graph. Mean retained strain remains after release. Shared positive loading makes positive response signs expected; this measure does not establish voluntary agreement.</p>
<p>The new law has no opening-at-1 trigger. The original closed Hug outline remains joined under the shear display. The coupling is a stated SIMS modeling choice, and the material coefficients do not validate that interaction as a physical clay network. The maximum independent-solver discrepancy is {error:.3g} strain. Twenty-four added tests check source reproduction, load jumps, retained memory, graph symmetry, energy accounting and numerical agreement.</p>
<p><a href="CLAY_SIMS_METHODS.md">Current equations, assumptions and results</a> · <a href="clay_sims_protocol.json">Fixed protocol</a> · <a href="clay_sims_results.json">All clay runs and controls</a> · <a href="clay_sources.json">Located source files and hashes</a></p></section>'''
