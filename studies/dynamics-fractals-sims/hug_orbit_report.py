"""Direct Hug deformation plots from the orbit-loaded clay experiment."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from hug_orbits import protocol,outline
from orbits import protocol as orbit_protocol

ROOT=Path(__file__).resolve().parent
COLORS=['#7e3f8f','#d36c37','#348b72','#236783','#b69024','#565f77']


def data():return json.loads((ROOT/'hug_orbit_results.json').read_text())


def build_figures():
    d=data();mag=protocol()['display_magnification']
    base=next(r for r in d['runs'] if r['case']=='Circular control' and r['material_row_stress_Pa']==20)
    fig,axes=plt.subplots(2,3,figsize=(13,9),layout='constrained')
    for ax,m,color in zip(axes.flat,orbit_protocol()['moons'],COLORS):
        r=next(r for r in d['runs'] if r['case']==m['name'] and r['material_row_stress_Pa']==20)
        shapes=[(0,'Starting Hug','#b4b8ba',':'),
                (base['maximum_sampled_strain'],'Circular loaded peak','#5c656b','--'),
                (r['maximum_sampled_strain'],'Eccentric loaded peak',color,'-'),
                (r['final_total_strain'],'After recovery','#233e37','-.')]
        for gamma,label,c,style in shapes:
            arms=outline(gamma,mag)
            for i,arm in enumerate(arms):
                p=np.array(arm);ax.plot(p[:,0],p[:,1],color=c,ls=style,lw=2 if label=='Eccentric loaded peak' else 1.2,label=label if i==0 else None)
        arms=outline(r['maximum_sampled_strain'],mag)
        tips=np.array([arms[0][0],arms[0][-1]])
        ax.scatter(tips[:,0],tips[:,1],color=color,s=20,zorder=5)
        ax.set(aspect='equal',xlim=(-1.5,1.5),ylim=(-1.3,1.3),xlabel='Outline x (arbitrary length)',ylabel='Outline y (arbitrary length)',
               title=f"{m['name']} · e={m['e']:.3f}\nActual sampled peak {100*r['maximum_sampled_strain']:.4f}% · at 420 s {100*r['final_total_strain']:.4f}%")
        ax.legend(fontsize=7,loc='lower right');ax.grid(alpha=.1)
    fig.suptitle('The orbit input applied directly to the current clay Hug\n20 Pa coefficient row · shear displacement magnified ×200; both joins stay closed.',fontsize=14)
    fig.savefig(ROOT/'figures/orbit_hug_outline.png',dpi=125,bbox_inches='tight');plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(13,9),layout='constrained')
    rows=[r for r in d['runs'] if r['material_row_stress_Pa']==20]
    for ax,key,scale,label in [(axes[0,0],'total_strain',100,'Actual shear strain (%)'),(axes[0,1],'delayed_strain',100,'Recoverable Kelvin strain (%)')]:
        ax.plot(base['time'],scale*np.array(base[key]),color='#1b2935',ls='--',label='Circular control')
        for r,c in zip(rows[1:],COLORS):ax.plot(r['time'],scale*np.array(r[key]),color=c,label=r['case'])
        ax.set(xlabel='Time (s)',ylabel=label);ax.legend(fontsize=8);ax.grid(alpha=.15)
    axes[0,0].set_title('Direct Hug: load, deform, then recover')
    axes[0,1].set_title('Recovery timing depends on the orbit-shaped input')
    axes[0,1].set_xlim(120,420)
    ax=axes[1,0];names=['Circular control']+[m['name'] for m in orbit_protocol()['moons']]
    for stress,c in zip([10,20,30,40],['#236783','#d36c37','#348b72','#7e3f8f']):
        r=[next(x for x in d['runs'] if x['case']==name and x['material_row_stress_Pa']==stress) for name in names]
        ax.plot(range(7),[100*x['maximum_sampled_strain'] for x in r],marker='o',color=c,label=f'{stress} Pa fitted row')
    ax.set_xticks(range(7),['Circle','Pasiphae','Elara','Himalia','Europa','Callisto','Thebe'],rotation=25,ha='right')
    ax.set(title='Four frozen coefficient sets, each with its own circular control',ylabel='Maximum sampled actual strain (%)');ax.legend(fontsize=8);ax.grid(alpha=.15)
    ax=axes[1,1]
    for r,c in zip(rows[1:],COLORS):ax.plot(r['time'],100*np.array(r['retained_strain']),color=c,label=r['case'])
    ax.plot(base['time'],100*np.array(base['retained_strain']),color='#1b2935',ls='--',label='Circular control')
    ax.set(title='Equal loading impulse leaves equal retained strain',xlabel='Time (s)',ylabel='Retained viscous strain (%)');ax.legend(fontsize=8);ax.grid(alpha=.15)
    fig.suptitle('Direct orbital-load Hug test · 28 material trajectories and 28 independent solver controls\nCurves use actual strain; coefficient-set comparisons do not isolate stress alone.',fontsize=14)
    fig.savefig(ROOT/'figures/orbit_hug_recovery.png',dpi=125,bbox_inches='tight');plt.close(fig)


def html_section():
    d=data();rows=[r for r in d['runs'] if r['material_row_stress_Pa']==20]
    table=''.join(f"<tr><td>{r['case']}</td><td>{100*r['maximum_sampled_strain']:.5f}%</td><td>{100*r['final_total_strain']:.5f}%</td><td>{100*r['final_retained_strain']:.5f}%</td></tr>" for r in rows)
    max_solver=max(r['max_solver_strain_error'] for r in d['runs'])
    return f'''<section id="hug-orbits"><h2>Batch 11 · test the orbital input with the Hug itself</h2>
<p>The orbit-shaped pressure now acts directly on the current clay Hug. Seven inputs—one circular control and the six moon eccentricities—are tested with all four fitted clay coefficient sets, starting from zero strain. This adds <strong>28 direct Hug trajectories and 28 independent solver controls</strong>. The previously completed 672 orbit-driven SIMS runs remain separate.</p>
<figure><img src="figures/orbit_hug_outline.png" alt="Six direct Hug outline comparisons showing the starting shape, circular and eccentric loaded peaks, and the recovering closed arms"><figcaption>These are the original two closed Hug arms, sheared using the current clay formula. The deformation in this drawing is magnified 200 times; reported strain values remain at actual scale. Colored tip markers show the two joins, which stay closed under the chosen affine map. This geometric property does not establish physical contact strength.</figcaption></figure>
<div class="scroll"><table><tr><th>20 Pa coefficient row</th><th>Sampled peak strain</th><th>Total after recovery, 420 s</th><th>Retained component</th></tr>{table}</table></div>
<figure><img src="figures/orbit_hug_recovery.png" alt="Direct Hug strain, delayed recovery, fitted-row sampled peak comparisons and retained strain under orbital loading"><figcaption>Each coefficient set has a paired circular control with the same mean pressure and loading duration. The fits came from different stress steps, so differences between sets cannot be attributed to stress alone. One orbit remains compressed into 100 seconds.</figcaption></figure>
<p>Pasiphae's eccentric waveform produces the largest sampled deformation in each fitted row. Europa, Callisto and Thebe stay close to the circular case. Equal pressure impulse leaves the same retained strain within a coefficient row, while recoverable strain and peak deformation differ. After release, the elastic part disappears immediately and the delayed component decays exponentially.</p>
<p>All joins and enclosed areas pass at actual scale and at display magnification. Work includes both load jumps and continuous deformation; dissipation and final stored energy balance. Independent material solvers agree within {max_solver:.3g} strain. The current clay model deforms and recovers; it has no pressure-triggered opening rule. Sixteen new tests check the direct material response, original outline, recovery, display scaling and energy.</p>
<p><a href="HUG_ORBIT_METHODS.md">Direct Hug equations, controls and limitations</a> · <a href="hug_orbit_protocol.json">Fixed direct-Hug protocol</a> · <a href="hug_orbit_results.json">All direct Hug trajectories, shapes and checks</a></p></section>'''
