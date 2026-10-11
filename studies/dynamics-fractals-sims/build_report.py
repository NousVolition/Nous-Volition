"""Build original scientific figures and an offline HTML report from saved results."""
from pathlib import Path
import os
import json
import math
import html
import unittest

ROOT = Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.plot-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from models import (integrate,logistic,logistic_exact,lorenz,pendulum,spring,threshold,
                    menger_cells,menger_graph,koch_vertices)
from bifurcations import (cusp_roots,bead_roots,budworm,budworm_fold,
                         pitchfork_roots,hoop,full_laser)
from oscillation_report import build_figures as build_oscillation_figures, html_section
from topology_report import build_figures as build_topology_figures, html_section as topology_section
from heteroclinic_report import build_figures as build_heteroclinic_figures, html_section as heteroclinic_section
from bridge_report import build_figures as build_bridge_figures, html_section as bridge_section
from sims_response_report import build_figures as build_response_figures, html_section as response_section
from hug_sims_report import build_figures as build_hug_figures, html_section as hug_section
from clay_sims_report import build_figures as build_clay_figures, html_section as clay_section
from orbit_report import build_figures as build_orbit_figures, html_section as orbit_section
from hug_orbit_report import build_figures as build_hug_orbit_figures, html_section as hug_orbit_section

BLUE, ORANGE, TEAL, INK = '#236783','#d36c37','#348b72','#1b2935'
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,
                     'axes.labelcolor':INK,'text.color':INK,'axes.titleweight':'bold',
                     'figure.facecolor':'white','savefig.facecolor':'white'})
FIG = ROOT/'figures'
FIG.mkdir(exist_ok=True)
data = json.loads((ROOT/'results.json').read_text(encoding='utf-8'))
bif = json.loads((ROOT/'bifurcation_results.json').read_text(encoding='utf-8'))


def save(fig,name):
    fig.savefig(FIG/(name+'.png'),dpi=135,bbox_inches='tight')
    plt.close(fig)


def dynamics():
    fig,axes = plt.subplots(2,4,figsize=(15,7.5),layout='constrained')
    ax=axes.flat[0]
    rows=np.array(integrate(lorenz,[1,1,1],40,0.005))
    ax.plot(rows[400:,1],rows[400:,3],color=BLUE,lw=0.35)
    ax.set(title='Lorenz: an orbit in state space',xlabel='x',ylabel='z')
    ax=axes.flat[1]
    for step,color in [(0.01,BLUE),(0.005,ORANGE)]:
        a=np.array(integrate(lorenz,[1,1,1],40,step))
        b=np.array(integrate(lorenz,[1+1e-8,1,1],40,step))
        ax.semilogy(a[:,0],np.linalg.norm(a[:,1:]-b[:,1:],axis=1),color=color,label=f'step {step}')
    ax.axhline(1,color=INK,lw=0.7,ls=':')
    ax.set(title='Tiny differences can grow',xlabel='Time',ylabel='Trajectory separation')
    ax.legend(fontsize=8)
    ax=axes.flat[2]
    for initial in ([1.4,0],[-2,0.5]):
        rows=np.array(integrate(pendulum,initial,30,0.02))
        ax.plot(rows[:,1],rows[:,2],lw=1)
    ax.set(title='Damped pendulum phase portrait',xlabel='Angle',ylabel='Angular velocity')
    ax=axes.flat[3]
    rows=np.array(integrate(spring,[1,0],20,0.02))
    ax.plot(rows[:,0],rows[:,1],color=BLUE,label='Full second-order model')
    ax.plot(rows[:,0],np.exp(-rows[:,0]/4),color=ORANGE,ls='--',label='Inertia neglected')
    ax.set(title='Overdamped spring: no overshoot',xlabel='Time',ylabel='Position')
    ax.legend(fontsize=7)
    ax=axes.flat[4]
    times=np.linspace(0,10,200)
    for initial in (0.1,0.5,1.5,2):
        ax.plot(times,[logistic_exact(t,initial) for t in times],lw=1.5,label=f'x₀={initial}')
    ax.set(title='Logistic flow approaches x = 1',xlabel='Time',ylabel='x')
    ax.legend(fontsize=7)
    ax=axes.flat[5]
    for method,color in [('euler',ORANGE),('rk4',BLUE)]:
        entries=[r for r in data['mathematics']['logistic_accuracy'] if r['method']==method]
        ax.loglog([r['step'] for r in entries],[r['max_error'] for r in entries],'o-',color=color,label=method)
    ax.set(title='Smaller steps reduce error',xlabel='Step size',ylabel='Maximum logistic error')
    ax.legend()
    ax=axes.flat[6]
    for pump in (0.5,1,1.5):
        rows=np.array(integrate(threshold(pump),[0.01],40,0.05))
        ax.plot(rows[:,0],rows[:,1],label=f'p={pump}')
    ax.set(title='Scalar laser-inspired onset',xlabel='Time',ylabel='n')
    ax.legend(fontsize=8)
    ax=axes.flat[7]
    pumps=np.linspace(0,2,200)
    ax.plot(pumps,np.maximum(pumps-1,0),color=BLUE,lw=2)
    ax.axvline(1,color=ORANGE,ls='--')
    ax.set(title='Positive-seed limiting state',xlabel='Pump p',ylabel='n*')
    fig.suptitle('Batch 1 · dynamics and numerical accuracy',fontsize=16)
    save(fig,'dynamics')


def fractals():
    fig=plt.figure(figsize=(12,9),layout='constrained')
    ax=fig.add_subplot(221,projection='3d')
    occupied=np.zeros((9,9,9),dtype=bool)
    for point in menger_cells(2):
        occupied[point]=True
    ax.voxels(occupied,facecolors=BLUE,edgecolors='white',linewidth=0.12)
    ax.set(title='Menger sponge · level 2 · 400 cubes',xlabel='x cell',ylabel='y cell',zlabel='z cell')
    ax.set_box_aspect((1,1,1))
    ax=fig.add_subplot(222)
    pts=koch_vertices(3)
    ax.fill([z.real for z in pts],[z.imag for z in pts],color='#edf4f6')
    ax.plot([z.real for z in pts+[pts[0]]],[z.imag for z in pts+[pts[0]]],color=BLUE,lw=1)
    ax.axis('equal')
    ax.set(title='Koch snowflake · level 3 · 192 segments',xlabel='x',ylabel='y')
    ax=fig.add_subplot(223,projection='3d')
    cells=np.array(menger_cells(1)); graph=menger_graph(1)
    for i,adj in enumerate(graph):
        for j in adj:
            if i<j:
                line=cells[[i,j]]
                ax.plot(line[:,0],line[:,1],line[:,2],color='#adb9be',lw=2)
    colors=[ORANGE if len(adj)==3 else BLUE for adj in graph]
    ax.scatter(cells[:,0],cells[:,1],cells[:,2],c=colors,s=50,depthshade=False)
    ax.set(title='SIMS network · 20 cubes with face contacts\nOrange corners: degree 3 · Blue edges: degree 2',xlabel='x',ylabel='y',zlabel='z')
    ax.set_xticks([0,1,2]);ax.set_yticks([0,1,2]);ax.set_zticks([0,1,2])
    ax=fig.add_subplot(224)
    pts=koch_vertices(2)
    ax.plot([z.real for z in pts+[pts[0]]],[z.imag for z in pts+[pts[0]]],color=BLUE,lw=1)
    ax.scatter([z.real for z in pts],[z.imag for z in pts],s=13,color=ORANGE)
    ax.axis('equal')
    ax.set(title='SIMS network · 48 boundary neighbors',xlabel='x',ylabel='y')
    ax.text(0.02,0.02,'Same adjacency as a 48-SIMS ring',transform=ax.transAxes,fontsize=9)
    fig.suptitle('Finite geometry and the contacts actually used by SIMS',fontsize=16)
    save(fig,'fractals')


def coordination():
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    rows=[r for r in data['sims']['cases'] if r['initiative']==0]
    for ax,names,labels in [(axes[0],['Menger L1','Ring 20'],['Ordinary','Hold\ncorner','Hold\nedge','Oppose\ncorner','Oppose\nedge']),
                           (axes[1],['Koch L2','Ring 48'],['Ordinary','Hold','Oppose'])]:
        for offset,name,color in [(-0.19,names[0],BLUE),(0.19,names[1],ORANGE)]:
            entries=[r for r in rows if r['network']==name]
            x=np.arange(len(entries))+offset
            y=np.array([r['first_consensus_fraction']*100 for r in entries])
            ci=np.array([r['first_consensus_wilson95'] for r in entries]).T*100
            ax.bar(x,y,width=.36,color=color,label=name,alpha=.9)
            ax.errorbar(x,y,yerr=np.maximum(0,np.vstack((y-ci[0],ci[1]-y))),fmt='none',ecolor=INK,capsize=3,lw=.8)
            ax.scatter(x,[r['unanimous_at_120_fraction']*100 for r in entries],color=INK,marker='_',s=150,zorder=4)
        ax.set_xticks(range(len(labels)),labels)
        ax.set(ylabel='Rounds reaching first consensus (%)',ylim=(0,100),title=' vs '.join(names))
        ax.legend(fontsize=8)
        ax.grid(axis='y',alpha=.15)
    fig.suptitle(f"{rows[0]['rounds']} matched starts per scenario · black marks show unanimity at 120 s\nWhiskers: 95% Wilson simulation-sampling intervals",fontsize=13)
    save(fig,'coordination')


def scatter_branches(ax,values,rootfn,xlabel):
    for status,color,marker in [('stable',BLUE,'.'),('unstable',ORANGE,'.'),('nonhyperbolic',INK,'x')]:
        pairs=[(p,row['x']) for p in values for row in rootfn(p) if row['stability']==status]
        if pairs:
            x,y=zip(*pairs)
            ax.scatter(x,y,s=5,color=color,marker=marker,label=status)
    ax.set_xlabel(xlabel)
    ax.set_ylabel('Equilibrium x*')


def tipping():
    fig=plt.figure(figsize=(14,8.5),layout='constrained')
    ax=fig.add_subplot(231,projection='3d')
    r,x=np.meshgrid(np.linspace(-.25,1.5,45),np.linspace(-1.5,1.5,70))
    h=x**3-r*x
    h=np.where(abs(h)<=0.85,h,np.nan)
    ax.plot_surface(r,h,x,cmap='Blues',alpha=.8,linewidth=0,rstride=2,cstride=2)
    ax.set(title='Cusp surface · height = x*',xlabel='r',ylabel='h',ylim=(-.85,.85))
    ax=fig.add_subplot(232)
    scatter_branches(ax,np.linspace(-.6,.6,250),lambda h:cusp_roots(1,h),'Bias h')
    for key,color in [('up_sweep',TEAL),('down_sweep',ORANGE)]:
        rows=np.array(bif['cusp'][key]);ax.plot(rows[:,0],rows[:,1],color=color,lw=1.5,label=key.replace('_',' '))
    ax.set_title('Cusp hysteresis at r = 1')
    ax.legend(fontsize=7)
    ax=fig.add_subplot(233)
    scatter_branches(ax,np.linspace(-.25,.25,250),bead_roots,'Load mg sin(θ) / k')
    ax.set_title('Tilted bead · a=1, L₀=1.4')
    ax.legend(fontsize=8)
    ax=fig.add_subplot(234)
    for xs in (np.linspace(1.026,math.sqrt(3),200),np.linspace(math.sqrt(3),20,250)):
        rows=[budworm_fold(x) for x in xs]
        ax.plot([r['capacity'] for r in rows],[r['r'] for r in rows],color=BLUE)
    ax.set(xlim=(0,40),ylim=(0,.8),title='Budworm fold boundaries',xlabel='Capacity k',ylabel='Growth r')
    ax.text(18,.35,'multiple positive equilibria',fontsize=8)
    ax=fig.add_subplot(235)
    xs=np.linspace(0,9,400)
    ax.plot(xs,[budworm(x) for x in xs],color=BLUE)
    ax.axhline(0,color=INK,lw=.6)
    for row in bif['budworm']['equilibria']:
        ax.scatter(row['x'],0,color=BLUE if row['stability']=='stable' else ORANGE,s=35)
    ax.set(title='Budworm basins · r=0.5, k=10',xlabel='Population x',ylabel='Rate x′')
    ax=fig.add_subplot(236)
    scatter_branches(ax,np.linspace(-.4,.2,300),pitchfork_roots,'r')
    ax.axvline(-.25,color=INK,ls=':',lw=.8)
    ax.axvline(0,color=INK,ls=':',lw=.8)
    ax.set_title('Subcritical pitchfork · a=1')
    ax.legend(fontsize=8)
    fig.suptitle('Batch 2 · stable branches, loss of stability, and tipping points',fontsize=16)
    save(fig,'tipping')


def extended():
    fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained')
    ax=axes.flat[0]
    for pump in (.1,.2,.8):
        rows=np.array(integrate(full_laser(pump),[.01,pump/.2],40,.02))
        ax.plot(rows[:,0],rows[:,1],label=f'p={pump}')
    ax.set(title='Two-variable laser: photon population',xlabel='Time',ylabel='n')
    ax.legend()
    ax=axes.flat[1]
    rows=np.array(integrate(full_laser(.8),[.01,4],40,.02))
    ax.plot(rows[:,1],rows[:,2],color=BLUE)
    ax.scatter([.6],[1],color=ORANGE,s=40,label='On equilibrium')
    ax.set(title='Laser state-space relaxation · p=0.8',xlabel='Photons n',ylabel='Inversion N')
    ax.legend()
    ax=axes.flat[2]
    phis=np.linspace(-math.pi,math.pi,400)
    ax.plot(phis,[hoop(p,2) for p in phis],color=BLUE)
    ax.axhline(0,color=INK,lw=.7)
    ax.scatter([-math.pi/3,math.pi/3],[0,0],color=TEAL,s=30)
    ax.set(title='Overdamped rotating hoop · γ=2',xlabel='Angle φ',ylabel='Rate φ′')
    for ax,a in zip(axes[1],(-1,0,1)):
        scatter_branches(ax,np.linspace(-.4,.3,300),lambda r:pitchfork_roots(r,a),'r')
        ax.set_title(f'Parameter extension: a={a}')
        ax.legend(fontsize=8)
    fig.suptitle('Laser and hoop dynamics · a clearly specified parameter extension',fontsize=15)
    save(fig,'extended')


def make_html():
    test_count=unittest.defaultTestLoader.discover(str(ROOT),pattern='test_*.py').countTestCases()
    topology_data=json.loads((ROOT/'topology_results.json').read_text(encoding='utf-8'))
    response_data=json.loads((ROOT/'sims_response_results.json').read_text(encoding='utf-8'))
    orbit_data=json.loads((ROOT/'orbit_results.json').read_text(encoding='utf-8'))
    total_sims_runs=data['sims']['total_rounds']+topology_data['sims']['new_rounds']+response_data['total_new_sims_trajectories']+384+384+orbit_data['main_runs']
    cases=data['sims']['cases']
    def case(network,policy='ordinary',role='baseline'):
        return next(r for r in cases if r['network']==network and r['policy']==policy and r['focal_role']==role and r['initiative']==0)
    def table(initiative):
        header='<tr><th>Network</th><th>Rule / position</th><th>First agreement</th><th>At 120 s</th><th>Capped time</th><th>Switches</th></tr>'
        rows=[]
        for r in cases:
            if r['initiative']!=initiative: continue
            label=html.escape(r['policy']+' / '+r['focal_role'])
            rows.append(f"<tr><td>{r['network']}</td><td>{label}</td><td>{r['first_consensus_fraction']:.2%}</td><td>{r['unanimous_at_120_fraction']:.2%}</td><td>{r['mean_capped_seconds']:.1f} s</td><td>{r['mean_switches']:.1f}</td></tr>")
        return '<div class="scroll"><table>'+header+''.join(rows)+'</table></div>'
    document=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dynamics, fractals, and SIMS — Streams and Rocks</title>
<style>body{{margin:0;background:#f5f3ee;color:#1b2935;font:17px/1.65 system-ui,sans-serif}}main{{max-width:1120px;margin:auto;padding:48px 24px 80px}}h1{{font-size:clamp(36px,6vw,64px);line-height:1.08;max-width:850px;margin:20px 0}}h2{{font-size:30px;line-height:1.25;margin-top:0}}h3{{font-size:21px}}p{{max-width:950px}}a{{color:#236783}}.eyebrow{{letter-spacing:.13em;font-size:12px;text-transform:uppercase;color:#236783}}.lead{{font-size:22px;max-width:850px}}section{{background:white;margin:32px 0;padding:30px;border-radius:15px}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}}.card{{padding:20px;background:#e7eef0;border-radius:12px}}.big{{font-size:34px;font-weight:700;display:block}}img{{width:100%;height:auto;border-radius:5px}}figure{{margin:25px 0}}figcaption{{font-size:14px;color:#52616a}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:10px 12px;border-bottom:1px solid #dde3e5;text-align:left}}th{{background:#edf2f3}}.scroll{{overflow:auto}}code{{background:#e9eff1;padding:3px 6px;border-radius:4px}}summary{{cursor:pointer;font-weight:650}}.equation{{font-size:20px;background:#eef3f4;padding:18px;border-radius:8px}}@media(max-width:650px){{.cards{{grid-template-columns:1fr}}section{{padding:20px}}}}@media print{{body{{background:white}}main{{padding:0}}section{{break-inside:avoid}}}}</style></head><body><main>
<div class="eyebrow">Streams and Rocks / Research notebook</div><h1>Dynamics, fractals,<br>and SIMS</h1>
<p class="lead">How do local rules, resistance, and the pattern of connections shape a group's path toward agreement?</p>
<p>SIMS are the simulated participants in the coordination tests. Eleven batches turn your references into explicit models, executable checks, and original plots. The current Hug/SIMS experiment uses your updated clay deformation formula, now tested with circular and eccentric orbital inputs in both SIMS and the Hug itself; its older threshold model is retained as historical.</p>
<div class="cards"><div class="card"><span class="big">{total_sims_runs:,}</span>12,800 binary + 1,632 continuous + 384 historical Hug + 384 clay + 672 orbit-driven clay SIMS</div><div class="card"><span class="big">{test_count}</span>automated tests</div><div class="card"><span class="big">11 batches</span>dynamics, topology, and participant response experiments</div></div>
<p><a href="#hug-orbits">New: apply the orbital input directly to the clay Hug</a></p>
<p><a href="#orbits">New: circular and eccentric orbits inside the clay-SIMS test</a></p>
<p><a href="#clay">Current: clay deformation, recovery and retained strain inside SIMS</a></p>
<p><a href="#sims-response">New: apply the dynamics inside the SIMS test</a></p>
<p><a href="#bridge">New: reversibility, stability, and water-flow checks</a></p>
<p><a href="#heteroclinic">New: switching, memory, and stopping</a> · <a href="#topology">Topology tests applied to SIMS</a> · <a href="#oscillations">Oscillation tests</a> · <a href="README.md">Full methods and instructions</a> · <a href="results.json">First-batch data</a> · <a href="bifurcation_results.json">Second-batch data</a> · <a href="oscillation_results.json">Third-batch data</a> · <a href="topology_results.json">Fourth-batch data</a></p>
{hug_orbit_section()}
{orbit_section()}
{clay_section()}
<details><summary>Historical: the earlier threshold-based Hug experiment</summary>{hug_section()}</details>
{response_section()}
{bridge_section()}
{heteroclinic_section()}
{topology_section()}
<section><h2>The first result: shape matters through connections</h2><p>The Koch boundary and a matching 48-SIMS ring produced identical outcomes. Each SIM has the same two neighbors in both drawings. The Menger network changes the contacts: ordinary agreement occurred in <strong>{case('Menger L1')['first_consensus_fraction']:.2%}</strong> of its 20-SIMS rounds, compared with <strong>{case('Ring 20')['first_consensus_fraction']:.2%}</strong> on a 20-SIMS ring.</p>
<p>These are the main runs with no spontaneous initiative. Whole-network connectivity changes in the Menger comparison; the experiment does not isolate a uniquely fractal cause. Menger-versus-Koch would also change group size.</p>
<figure><img src="figures/fractals.png" alt="Menger sponge, Koch snowflake, and the finite neighbor graphs used for SIMS"><figcaption>The rendered Menger level 2 has 400 cubes; SIMS trials use level 1 with 20 face-connected cubes. Koch trials use 48 boundary vertices.</figcaption></figure>
<figure><img src="figures/coordination.png" alt="First consensus and endpoint agreement in equal-size Menger/ring and Koch/ring comparisons"><figcaption>Same starting colors and random opportunity streams within population size. The black marks show endpoint agreement; whiskers show simulation-sampling uncertainty.</figcaption></figure>
<h3>A resisting position can change the path</h3><p>“Hold” keeps one SIM's starting color. “Oppose” chooses the opposite of its neighbors' majority when active. On Menger corner-opponent runs, {next(r['first_consensus_fraction'] for r in cases if r['network']=='Menger L1' and r['policy']=='oppose' and r['focal_role']=='Menger corner' and r['initiative']==0):.2%} reached agreement at least once, but only {case('Menger L1','oppose','Menger corner')['unanimous_at_120_fraction']:.2%} were unanimous at 120 seconds. First arrival and persistence answer different questions.</p>
<details><summary>Main results · {case('Menger L1')['rounds']} matched rounds per case</summary>{table(0)}</details>
<details><summary>Initiative sensitivity · {next(r['rounds'] for r in cases if r['initiative']==.02)} matched rounds per case</summary><p>Ordinary SIMS can spontaneously flip with probability 0.02 when active. All other behavioral parameters remain fixed.</p>{table(.02)}</details>
<p>Identity labels have no behavioral effect in this model. A permutation test confirms that renaming SIMS preserves seat outcomes. Testing personality requires an explicit identity-dependent rule or volunteer evidence. Direct copying credits are saved as a limited influence measure.</p></section>
<section><h2>Batch 1 · check the dynamics before interpreting them</h2><p>The first set covers the Lorenz orbit, phase space, damping, Euler's method, logistic growth, and a scalar laser-inspired threshold. Exact solutions and step refinement provide checks on numerical accuracy.</p>
<figure><img src="figures/dynamics.png" alt="Eight scientific plots of Lorenz sensitivity, damping, logistic numerical errors, and scalar threshold dynamics"><figcaption>The short-time Lorenz error decreases with smaller steps. Its long-time separation timing still shifts, illustrating the limits of pointwise prediction.</figcaption></figure>
<p>The scalar threshold uses the chosen equation n′=(p−1)n−n². It tracks an intensity-like quantity with growth and saturation. The improved laser in batch 2 includes a separate inversion variable. Optical phase is absent from both models.</p>
<p>Menger counts, volume, and exposed surface are checked through level 3. Koch counts, perimeter, and area are checked through level 5. Finite drawings approximate limiting fractal constructions. See <a href="https://www.its.caltech.edu/~matilde/FractalsUToronto7.pdf">Caltech's Menger notes</a> and <a href="https://people.reed.edu/~mayer/math111.html/header/node12.html">Reed's snowflake derivation</a>.</p></section>
<section><h2>Batch 2 · when a stable state disappears</h2><p>The new images describe folds, hysteresis, and competing stable states. Blue points below are stable equilibria; orange points are unstable. Up/down cusp paths follow equilibria quasistatically, so their jump points should not be read as a finite-speed switching experiment.</p>
<figure><img src="figures/tipping.png" alt="Cusp surface, cusp hysteresis, tilted bead branches, budworm fold boundaries and basins, and subcritical pitchfork"><figcaption>The cusp, bead, budworm, and pitchfork give distinct mathematical examples of multiple equilibria and loss of stability.</figcaption></figure>
<h3>Your exact bead equation</h3><div class="equation">mg sin θ = kx [1 − L₀ / √(x² + a²)]</div>
<p>For the selected a=1, L₀=1.4, and mg/k=1, the horizontal stable positions are ±0.979796. One stable branch disappears at a tilt magnitude of <strong>{bif['bead']['fold_angle_degrees']:.4f}°</strong>. Changing the spring geometry changes this value.</p>
<h3>Budworm refuge and outbreak</h3><p>Using standard saturating predation, r=0.5 and k=10 give stable population levels <strong>0.683375</strong> and <strong>7.316625</strong>, separated by unstable x=2. The tested starting populations below and above 2 reach different stable levels. The predation function missing from the crop is stated in the methods, following the <a href="https://math.bu.edu/people/bob/MA226/spruce-budworm-lab.html">standard budworm equation</a>.</p>
<figure><img src="figures/extended.png" alt="Two-variable laser dynamics, rotating hoop rate, and three parameter-a pitchfork diagrams"><figcaption>The supplied subcritical pitchfork uses a=1. The a=−1 and a=0 cases are an explicitly chosen extension of that equation because the final crop omitted its formula.</figcaption></figure>
<h3>The improved laser has a moving internal state</h3><p>With G=κ=1 and f=0.2, the threshold is p=0.2. At p=0.8 the solution approaches (n,N)=(0.6,1) through decaying oscillations; the equilibrium eigenvalues are −0.4 ± 0.663325i. Halving the time step changes the computed trajectory by at most {bif['two_variable_laser'][-1]['max_step_refinement_difference']:.2g} over the sampled interval. At the threshold, convergence is much slower.</p>
<p>The rotating-hoop test finds stable angles ±π/3 for γ=2 and checks the small-angle cubic expansion. The parameter-a extension compares x′=r x+a x³−x⁵ at a=−1,0,1. All choices and equations are recorded in the <a href="README.md">methods</a>.</p></section>
{html_section()}
<section><h2>What connects these tests?</h2><p>Each system has a state, a rule for changing it, and questions about where it settles. For SIMS, the practical lesson is to measure both agreement and its stability, and to distinguish a changed drawing from changed contacts.</p><p>Batch 7 puts the supplied reversal, linear-stability, and response-rate ideas into explicit SIMS rules. Its continuous-state assumptions, paired controls, and measurements are documented separately from the original binary-copying experiment. Repeated switching can decay or persist; alignment can coexist with collective growth. The current results concern the models and parameter choices tested here.</p>
<h3>Reproduce this notebook</h3><p><code>python -m pip install -r requirements.txt</code><br><code>python -m unittest -v</code><br><code>python run_study.py --check</code><br><code>python bifurcations.py --check</code><br><code>python oscillations.py --check</code><br><code>python topology.py --check</code><br><code>python heteroclinic.py --check</code><br><code>python pacemaker.py --check</code><br><code>python memory_inference.py --check</code><br><code>python quench.py --check</code><br><code>python bridge_checks.py --check</code><br><code>python sims_response.py --check</code><br><code>python clay_sims.py --check</code></p><p>Python 3.12. The coupled ensemble, inference, quenches, and their tests use NumPy. Requirements are pinned in <a href="requirements.txt">requirements.txt</a>. Read <a href="README.md">the methods</a> for limitations, sources, and the optional volunteer extension.</p></section>
</main></body></html>'''
    document=document.replace('<code>python clay_sims.py --check</code>','<code>python clay_sims.py --check</code><br><code>python orbits.py --check</code><br><code>python hug_orbits.py --check</code>')
    (ROOT/'report.html').write_text(document,encoding='utf-8',newline='\n')


if __name__=='__main__':
    dynamics();fractals();coordination();tipping();extended();build_oscillation_figures();build_topology_figures();build_heteroclinic_figures();build_bridge_figures();build_response_figures();build_hug_figures();build_clay_figures();build_orbit_figures();build_hug_orbit_figures();make_html()
    print('Built twenty-four original figures and report.html')
