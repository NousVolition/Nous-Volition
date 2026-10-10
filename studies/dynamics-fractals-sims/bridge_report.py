"""Original plots connecting the latest three references to executable checks."""
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from models import integrate
from bridge_checks import reversible, potential, linear_flow, references, channel_tau

ROOT=Path(__file__).resolve().parent
BLUE,ORANGE,TEAL,INK='#236783','#d36c37','#348b72','#1b2935'


def save(fig,name):
    fig.savefig(ROOT/'figures'/f'{name}.png',dpi=135,bbox_inches='tight')
    plt.close(fig)


def linear_figure():
    cases=[r for r in references()['linear_reference'] if r['name']!='symmetric a=-1,b=1']
    fig,axes=plt.subplots(2,3,figsize=(13,8),layout='constrained')
    for ax,case in zip(axes.flat,cases):
        for initial,color in zip([[.28,0],[0,.42],[-.55,0],[0,-.7]],[BLUE,ORANGE,TEAL,'#9266a2']):
            times=np.linspace(0,8,401)
            path=np.array([linear_flow(case['matrix'],initial,t) for t in times])
            ax.plot(path[:,0],path[:,1],color=color,lw=1.2)
            visible=np.where(np.max(np.abs(path),axis=1)<1.12)[0]
            if len(visible)>10:
                i=visible[min(len(visible)-3,max(3,len(visible)//3))]
                ax.annotate('',xy=path[i+2],xytext=path[i-2],arrowprops=dict(arrowstyle='->',color=color,lw=1))
        ax.axhline(0,color='#dddddd',lw=.7);ax.axvline(0,color='#dddddd',lw=.7)
        ax.set(xlim=(-1.15,1.15),ylim=(-1.15,1.15),xlabel='x',ylabel='y',
               title=case['name']+'\n'+case['classification'])
        ax.set_aspect('equal')
    fig.suptitle('Exact linear flows from the supplied report · arrows follow increasing time',fontsize=15)
    save(fig,'linear_reference_checks')


def bridge_figure():
    data=json.loads((ROOT/'bridge_results.json').read_text())
    fig,axes=plt.subplots(2,3,figsize=(15,9),layout='constrained')
    ax=axes[0,0];coords=np.linspace(-math.pi,math.pi,41);x,y=np.meshgrid(coords,coords)
    ax.streamplot(coords,coords,-2*np.cos(x)-np.cos(y),-np.cos(x)-2*np.cos(y),color='#9babb1',density=.95,linewidth=.8,arrowsize=.8)
    ax.scatter([-math.pi/2],[-math.pi/2],s=60,color=BLUE,label='Attractor',zorder=5)
    ax.scatter([math.pi/2],[math.pi/2],s=60,facecolor='white',edgecolor=ORANGE,label='Repeller',zorder=5)
    ax.scatter([-math.pi/2,math.pi/2],[math.pi/2,-math.pi/2],s=48,color=INK,marker='x',label='Saddles',zorder=5)
    ax.set(title='Reversible, with an attracting state',xlabel='x',ylabel='y',xlim=(-math.pi,math.pi),ylim=(-math.pi,math.pi))
    ax.set_xticks([-math.pi,0,math.pi],['−π','0','π']);ax.set_yticks([-math.pi,0,math.pi],['−π','0','π'])
    ax.legend(fontsize=8,loc='upper left');ax.set_aspect('equal')
    ax=axes[0,1]
    for initial,color in zip([[.2,.4],[-1.2,-.8],[.6,-.5]],[BLUE,ORANGE,TEAL]):
        path=np.array(integrate(reversible,initial,5,.01))
        ax.plot(path[:,0],[potential(z) for z in path[:,1:]],color=color,label=str(initial))
    ax.axhline(-2,color=INK,ls=':',lw=1)
    ax.set(title='A decreasing function along each path',xlabel='Time',ylabel='V = sin(x) + sin(y)')
    ax.legend(title='Initial state',fontsize=8)
    ax=axes[0,2];times=np.linspace(0,10,500)
    norms=[np.linalg.norm(linear_flow([[-1,10],[0,-2]],[0,1],t)) for t in times]
    ax.plot(times,norms,color=ORANGE);ax.axhline(1,color=INK,ls=':',lw=.8)
    ax.set(title='Stable node: temporary growth is possible',xlabel='Time',ylabel='Distance from the equilibrium')
    ax.text(.97,.95,'Eigenvalues: −1, −2\nInitial state: (0, 1)',ha='right',va='top',transform=ax.transAxes,fontsize=9)
    ax=axes[1,0];p=references()['water_properties']['298.15'];h,d=p['H2O'],p['D2O']
    material=[h,dict(rho=d['rho'],mu=h['mu']),dict(rho=h['rho'],mu=d['mu']),d]
    x=np.arange(4)
    ax.bar(x-.18,[h['mu']/m['mu'] for m in material],width=.36,color=BLUE,label='Steady speed')
    ax.bar(x+.18,[channel_tau(m['rho'],m['mu'])/channel_tau(h['rho'],h['mu']) for m in material],width=.36,color=ORANGE,label='Slowest decay time')
    ax.set_xticks(x,['H₂O','D density','D viscosity','D₂O'])
    ax.axhline(1,color=INK,lw=.7,ls=':');ax.set(title='Property swaps at 25 °C',ylabel='Relative to H₂O',ylim=(0,1.3))
    ax.legend(fontsize=8)
    ax=axes[1,1]
    for name,color in [('H2O',BLUE),('D2O',ORANGE)]:
        rows=[r for r in data['water']['grid_convergence'] if r['material']==name]
        ax.loglog([r['intervals'] for r in rows],[r['relative_L2_error'] for r in rows],'o-',color=color,label=name)
    ax.set(title='Independent channel convergence check',xlabel='Across-gap intervals',ylabel='Relative error against exact startup')
    ax.legend(fontsize=8);ax.text(.03,.03,'t = 0.1 s; time step = 0.00025 s',transform=ax.transAxes,fontsize=8)
    ax=axes[1,2];rows=data['reversible']['diagonal_accuracy']
    ax.loglog([r['step'] for r in rows],[r['max_error'] for r in rows],'o-',color=TEAL,label='RK4 error')
    ax.set(title='Exact solution checks the nonlinear solver',xlabel='Time step',ylabel='Largest diagonal-trajectory error')
    ax.legend(fontsize=8)
    for ax in [axes[0,1],axes[0,2],*axes[1]]:ax.grid(alpha=.15)
    fig.suptitle('Reversal symmetry, attraction, and material-dependent decay',fontsize=16)
    save(fig,'reversibility_and_flow')


def build_figures():
    linear_figure();bridge_figure()


def html_section():
    d=json.loads((ROOT/'bridge_results.json').read_text())
    decrease=100*(1-d['water']['material_ratios'][1]['steady_D_over_H'])
    largest=max(r['startup_mean_relative_difference'] for r in d['water']['checks'])
    return f'''<section id="bridge"><h2>Batch 6 · reversing time does not imply conserved energy</h2>
<p>The textbook example is reconstructed from its displayed nullclines and Jacobian: x′=−2 cos x−cos y, y′=−cos x−2 cos y. It satisfies f(−z)=f(z), so negating a trajectory and reversing its time gives another trajectory. Nevertheless, (−π/2,−π/2) attracts nearby paths. The reversed partner at (π/2,π/2) repels them. Two other equilibria are saddles. These four repeat every 2π in each coordinate.</p>
<p>The function V=sin x+sin y strictly decreases away from equilibria: V′=−2(cos²x+cos x cos y+cos²y). This supplies an analytic exclusion of nonconstant closed orbits and explains why reversibility and conservation are different properties. The tests also compare a diagonal trajectory to its exact solution, reverse finite trajectories, and halve the integration step.</p>
<figure><img src="figures/reversibility_and_flow.png" alt="Reversible nonlinear phase portrait, decreasing potential, temporary growth at a stable node, water property controls, and solver convergence"><figcaption>22 new tests cover the latest references. Water values are checked against saved numerical tables from the separate study; the property swaps use that study's measured-property correlations.</figcaption></figure>
<h3>Stable does not mean every measurement decreases at every instant</h3><p>The added linear control has eigenvalues −1 and −2, yet an initial unit displacement reaches distance {d['transient_growth']['largest_sampled_norm']:.3f} before decaying. The two components temporarily transfer growth between directions. Reciprocal equal coupling has real eigenvalues a+b and a−b and cannot generate a spiral in this two-variable model. At a=−1, b=1, a neutral direction remains; treating that boundary as an attracting node would be wrong.</p>
<figure><img src="figures/linear_reference_checks.png" alt="Six exact linear phase portraits reproduced from the matrices behind the supplied report"><figcaption>These are mathematical reference systems. A nonlinear system with purely imaginary linearized eigenvalues requires further analysis; tests include inward, closed, and outward trajectories sharing the same linearization.</figcaption></figure>
<h3>What the water screenshot lets us check</h3><p>Independent formulas reproduce all 36 saved channel steady speeds and decay times. The largest difference between the Fourier startup mean and the saved finite-difference mean after one second is {largest:.2e} relative. At 25 °C, the stated pressure and geometry give D₂O a <strong>{decrease:.2f}% lower steady mean speed</strong>. Density changes the transient time scale; dynamic viscosity changes both steady speed and decay time.</p>
<p>A new implementation evolves discrete sine modes and converges toward the analytic channel solution as the spatial grid is refined. These checks do not rerun the molecular or three-dimensional vortex experiments, add an independent measured velocity field, or establish a quantum prediction of viscosity. The source correlations are documented by <a href="https://iapws.org/technical-guidance/release/viscosity">IAPWS for ordinary water</a> and <a href="https://www.iapws.org/relguide/D2Ovisc.html">IAPWS for heavy water</a>.</p>
<p><a href="BRIDGE_CHECKS.md">Equations, controls, provenance, and limits</a> · <a href="bridge_results.json">New results</a> · <a href="bridge_references.json">Reference table extracts and source hashes</a></p></section>'''
