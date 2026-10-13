"""Original scientific plots for the finite Hug robustness sweep."""
import json
from pathlib import Path
from collections import Counter
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
from matplotlib.patches import Patch

ROOT=Path(__file__).resolve().parent
COLORS=['#197c80','#a8adb2','#377eb8','#e39843','#915da3','#b9454a']
LABELS=['Self-sustained','Rest','Repeats with orbit','No 1–4 orbit repeat','Unsettled / start-dependent','Integration guard']


def read():return json.loads((ROOT/'hug_robustness_results.json').read_text())


def code(status):
    return {'self_sustained':0,'rest':1,'orbit_locked':2,'no_short_repeat':3,'unsettled':4,'mixed_or_unsettled':4,'repeat_start_dependent':4,'integration_guard':5}[status]


def build_figures():
    d=read();ss=d['settings'];cc=d['conditions'];pairs={(p['setting'],p['condition']):p for p in d['pairs']};rows={(c['setting'],c['condition'],c['start']):c for c in d['cases']}
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
    chosen=[i for i,s in enumerate(ss) if s['kind']!='joint'];yy=np.arange(len(chosen));fig,axes=plt.subplots(1,2,figsize=(12,9),constrained_layout=True)
    for y,i in zip(yy,chosen):
        p=pairs[i,0];color=COLORS[code(p['classification'])];cycle=d['cycles'][ss[i]['id']]
        values=[rows[i,0,k]['metrics'].get('mean_half_amplitude_mm',0) for k in (0,1)]
        axes[0].plot(values,[y,y],color=color,lw=3);axes[0].scatter(values,[y,y],c=color,s=32)
        if cycle.get('status')=='attracting_cycle':axes[1].scatter(cycle['period_s'],y,c=color,s=42)
        else:axes[1].text(.02,y,'No attracting cycle located',transform=axes[1].get_yaxis_transform(),fontsize=8,color='#5b6670',va='center')
    for ax in axes:
        ax.set_yticks(yy,[ss[i]['label'].replace(' x',' ×') for i in chosen]);ax.invert_yaxis();ax.grid(axis='x',alpha=.15)
    axes[0].set(xlabel='Late half amplitude (mm), both starts',title='How much does the Hug move?')
    axes[1].set(xlabel='Period of the located cycle (simulation s)',title='How fast is its unforced rhythm?')
    fig.suptitle('Hug robustness without an orbit\nOne parameter at a time; synthetic coefficients',fontsize=17)
    axes[0].legend(handles=[Patch(color=COLORS[i],label=LABELS[i]) for i in (0,1,4)],loc='upper left',fontsize=8)
    fig.savefig(ROOT/'figures/hug_robustness_autonomous.png',dpi=160);plt.close(fig)
    matrix=np.array([[code(pairs[i,j]['classification']) for j in range(8)] for i in range(len(ss))])
    fig,ax=plt.subplots(figsize=(13,13),constrained_layout=True)
    ax.imshow(matrix,cmap=ListedColormap(COLORS),norm=BoundaryNorm(np.arange(-.5,6.5),6),aspect='auto',interpolation='nearest')
    ax.set_xticks(range(8),[c['name'] for c in cc[:8]]);ax.xaxis.tick_top();ax.tick_params(axis='x',labelsize=11,length=0)
    ax.set_yticks(range(len(ss)),[s['label'].replace(' x',' ×') for s in ss],fontsize=9)
    ax.set_xticks(np.arange(-.5,8,1),minor=True);ax.set_yticks(np.arange(-.5,len(ss),1),minor=True);ax.grid(which='minor',color='white',linewidth=1.2);ax.tick_params(which='minor',length=0)
    ax.axhline(18.5,color='#243c4b',lw=2);ax.set_title('Does the rhythm survive — and does it follow the orbit?\n35 settings · two starts each · 6,000 simulation seconds',fontsize=17,pad=38)
    handles=[Patch(color=COLORS[i],label=LABELS[i]) for i in range(5)]
    ax.legend(handles=handles,loc='upper center',bbox_to_anchor=(.5,-.025),ncol=2,fontsize=10,frameon=False)
    fig.savefig(ROOT/'figures/hug_robustness_orbits.png',dpi=160);plt.close(fig)
    selections=['gain_N_s_m_0','parallel_stiffness_N_m_2'];fig,axes=plt.subplots(2,3,figsize=(14,7.5),constrained_layout=True)
    for ir,sid in enumerate(selections):
        i=next(i for i,s in enumerate(ss) if s['id']==sid)
        for ax,j in zip(axes[ir],(0,1,2)):
            c=rows[i,j,0];baseline=rows[0,j,0];a=c['trace'];b=baseline['trace'];status=LABELS[code(pairs[i,j]['classification'])]
            ax.plot(b['time_s'],b['displacement_mm'],color='#9faab0',ls='--',lw=1.1,label='Baseline')
            ax.plot(a['time_s'],a['displacement_mm'],color=COLORS[code(pairs[i,j]['classification'])],lw=1.5,label=ss[i]['label'].replace(' x',' ×'))
            ax.set(title=cc[j]['name']+' · '+status,xlabel='Time in final 20-second window (s)',ylabel='Displacement (mm)');ax.grid(alpha=.15);ax.legend(fontsize=8,loc='lower right')
    fig.suptitle('What changes when feedback is removed or stiffness doubles?\nCircular and Pasiphae-shaped inputs share a 5.7 s orbit and equal RMS force',fontsize=16)
    fig.savefig(ROOT/'figures/hug_robustness_examples.png',dpi=160);plt.close(fig)


def html_section():
    d=read();ss=d['settings'];core=[p for p in d['pairs'] if p['condition']<8];unforced=Counter(p['classification'] for p in core if p['condition']==0)
    counts=[]
    for j,c in enumerate(d['conditions'][:8]):
        counter=Counter(p['classification'] for p in core if p['condition']==j)
        counts.append('<tr><td>'+c['name']+'</td><td>'+'; '.join(f'{k.replace("_"," ")}: {v}' for k,v in sorted(counter.items()))+'</td></tr>')
    joint=[]
    for j,c in enumerate(d['conditions'][:8]):
        counter=Counter(p['classification'] for p in core if p['condition']==j and ss[p['setting']]['kind']=='joint')
        joint.append(c['name']+': '+', '.join(f'{v}/16 {k.replace("_"," ")}' for k,v in sorted(counter.items())))
    return f'''<section id="hug-robustness"><h2>Batch 15 · how robust is the Hug’s rhythm?</h2>
<p>We varied seven coefficients in the existing synthetic active Hug: the two clay stiffnesses, two viscosities, restoring stiffness, feedback gain and feedback saturation. Thirty-five settings, two starts and circular/six eccentric inputs produce <strong>568 trajectories</strong>, each repeated at a smaller step. Mass, geometry and controller delay remain fixed. These are sensitivity scenarios; they are not measured clay uncertainty.</p>
<p>The unforced outcomes across the 35 settings are {', '.join(f'{v} {k.replace("_"," ")}' for k,v in sorted(unforced.items()))}. A repeating forced response can persist with feedback switched off, so orbital repetition alone does not demonstrate a self-sustained Hug.</p>
<figure><img src="figures/hug_robustness_autonomous.png" alt="Amplitude and located cycle period under individual parameter changes without an orbit"><figcaption>Colors retain unsettled cases. Periodic shooting and transverse Floquet stability support the cycle checks; both starting trajectories must also meet the section tolerance.</figcaption></figure>
<figure><img src="figures/hug_robustness_orbits.png" alt="Outcome map for 35 settings without orbit and with circular and six eccentric inputs"><figcaption>Each cell summarizes two starts after 6,000 simulation seconds. The orbit stays at 5.7 seconds even when the natural rhythm changes. No 1–4 orbit repeat does not establish chaos.</figcaption></figure>
<div class="scroll"><table><thead><tr><th>Condition</th><th>Outcomes across 35 settings</th></tr></thead><tbody>{''.join(counts)}</tbody></table></div>
<p>For the 16 joint perturbations within ±25%: {'; '.join(joint)}. These fractions describe only the chosen scenarios.</p>
<figure><img src="figures/hug_robustness_examples.png" alt="Late waveforms with feedback removed or restoring stiffness doubled compared with baseline"><figcaption>Gray dashed lines show the unchanged baseline. Colored lines show actual integrated trajectories for the modified setting. Feedback off removes both the driving term and its nonlinear amplitude-limiting term; near-resonant orbital forcing can therefore produce a larger passive response. Panel vertical scales differ.</figcaption></figure>
<p>Numerical checks: <strong>{d['numerical_status']}</strong>. The complete 568-run sweep was repeated at half the time step, with 46 separate physical-unit Radau segment controls. Unsettled outcomes stay in the results. <a href="HUG_ROBUSTNESS_METHODS.md">Methods and limitations</a> · <a href="hug_robustness_protocol.json">Declared protocol</a> · <a href="hug_robustness_results.json">Saved results</a>.</p></section>'''


if __name__=='__main__':build_figures();print('Built three Hug robustness figures')
