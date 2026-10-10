"""Original plots and report section for the tested Hug/SIMS connection."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent


def data():return json.loads((ROOT/'hug_sims_results.json').read_text())


def build_figures():
    d=data();fig,axes=plt.subplots(2,2,figsize=(13,9),layout='constrained')
    conditions=['Memory off','Memory on','Opening load','Buckling']
    colors=['#547282','#d06b35','#9266a2','#348b72']
    ax=axes[0,0]
    for name,color in zip(conditions,colors):
        r=next(x for x in d['representative_traces'] if x['graph']=='Menger L1' and x['condition']==name)
        ax.plot(r['time'],r['mean_preference'],label=name,color=color)
    ax.set(title='Same start, four Hug response rules',xlabel='Model time',ylabel='Mean lean · Menger network')
    ax.axhline(0,color='#aaaaaa',lw=.5);ax.legend(fontsize=9);ax.grid(alpha=.15)
    ax=axes[0,1]
    r=next(x for x in d['representative_traces'] if x['graph']=='Menger L1' and x['condition']=='Memory on')
    ax.plot(r['time'],r['pressure'],label='Applied pressure',color='#547282')
    ax.plot(r['time'],r['memory'],label='Fading memory',color='#d06b35')
    ax.plot(r['time'],r['effective_stiffness'],label='r + memory coupling × memory',color='#9266a2',ls='--')
    ax.axhline(0,color='#999999',lw=.6)
    ax.set(title='Memory briefly changes the local stability',xlabel='Model time',ylabel='Chosen model units')
    ax.legend(fontsize=9);ax.grid(alpha=.15)
    ax=axes[1,0];graphs=['Menger L1','Ring 20','Complete 20'];gc=['#236783','#d36c37','#348b72']
    for offset,g,color in zip([-.25,0,.25],graphs,gc):
        vals=[next(x['mean_final_spread'] for x in d['aggregates'] if x['graph']==g and x['condition']==c) for c in conditions]
        ax.bar(np.arange(4)+offset,vals,width=.24,label=g,color=color)
    ax.set_xticks(range(4),conditions);ax.set(yscale='log',ylabel='Mean final RMS spread in lean and velocity',title='Participant differences at time 24')
    ax.legend(fontsize=9);ax.grid(axis='y',alpha=.15)
    ax=axes[1,1]
    vals=np.array([[next(x['unanimous_final_runs'] for x in d['aggregates'] if x['graph']==g and x['condition']==c) for g in graphs] for c in conditions])
    ax.imshow(vals,cmap='Blues',vmin=0,vmax=32,aspect='auto')
    for i in range(4):
        for j in range(3):ax.text(j,i,f'{vals[i,j]}/32',ha='center',va='center',color='white' if vals[i,j]>18 else '#1b2935')
    ax.set_xticks(range(3),graphs);ax.set_yticks(range(4),conditions);ax.set_title('Final unanimous choices across matched starts')
    ax.text(.5,-.16,'All lean values must be > 0.02 or all < −0.02; near zero is undecided.',transform=ax.transAxes,ha='center',fontsize=8)
    fig.suptitle('Your Hug equations inside the SIMS test · 384 main trajectories',fontsize=16)
    fig.savefig(ROOT/'figures/hug_sims.png',dpi=125,bbox_inches='tight');plt.close(fig)


def html_section():
    d=data();c=d['controls'];pulse=d['short_pulse_control']
    error=max(x['max_rk4_dop853_difference'] for x in c)
    return f'''<section id="hug"><h2>Batch 8 · test your Hug model here</h2>
<p>Your Hug geometry, pressure-memory extension, fluid initialization, and later stress work were located in <a href="https://github.com/NousVolition/My-Sources-Project-ALL/tree/b20d1dcf25fb7e97bcceb9a09d0883d30bf08e8c/reports/hug-dynamics">My-Sources-Project-ALL</a>. Five source files are preserved byte for byte here, including the nine original geometry and pressure tests. This batch uses the reduced lean-and-memory equations; the fluid and Lorenz extensions remain separately identified in the <a href="hug_sources.json">source inventory</a>.</p>
<p>Each SIM has lean q, velocity v, and fading memory m. We add reciprocal neighbor attraction to the original lean acceleration: <code>q′=v; v′=(r+c m)q−q³−d v−2Lq</code>. The original loading/recovery times and pressure pulse remain intact. Four conditions reuse 32 starts on each of three networks, producing <strong>384 main trajectories</strong> plus 72 numerical and reflection controls.</p>
<figure><img src="figures/hug_sims.png" alt="Hug-driven SIMS mean lean, pressure memory and local stability, participant spread, and final unanimous choices"><figcaption>Top-left traces use the first predefined starting seed. Bottom panels summarize all 32 starts in each condition. The cubic term limits growth; convergence near zero is counted as undecided. These are explicit participant response rules.</figcaption></figure>
<p>The maximum RK4-versus-adaptive discrepancy is {error:.3g}; independent DOP853/Radau, half-step, reflection, and energy-budget controls pass the thresholds fixed in the <a href="hug_sims_protocol.json">protocol</a>. Opening preserves your original irreversible geometry rule. It does not change contacts or reduce the prescribed pressure.</p>
<h3>A control that catches a known failure</h3><p>A pressure pulse lasting 0.001 is missed entirely by the original steps 0.02 and 0.01. Both report zero memory. Splitting at the pulse boundary gives a sampled peak memory of {pulse['resolved_peak_memory']:.7f}; two independent adaptive methods agree within {pulse['independent_max_state_difference']:.2g}. Agreement between two coarse steps alone would have hidden this error. The main experiment uses a resolved four-unit pulse.</p>
<p><a href="HUG_SIMS_METHODS.md">Located files, equations, results and scope</a> · <a href="hug_sims_results.json">Every outcome and control</a> · <a href="test_hug_sims.py">Executable checks</a></p></section>'''
