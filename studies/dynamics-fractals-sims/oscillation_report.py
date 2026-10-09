"""Original figures and the batch-3 report section."""
import json
import math
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.plot-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from models import integrate
from oscillations import (radial_trajectory,gradient,potential,radial_rate,
    selkov,selkov_equilibrium,selkov_hopf_bounds,selkov_trap,planar_pitchfork,hopf_normal_form,
    vdp,vdp_lienard,cubic,duffing,duffing_energy,pendulum_period,cubic_damping,
    cubic_damping_approx,swing,swing_averaged)
BLUE,ORANGE,TEAL,INK='#236783','#d36c37','#348b72','#1b2935'


def save(fig,name):
    (ROOT/'figures').mkdir(exist_ok=True)
    fig.savefig(ROOT/'figures'/f'{name}.png',dpi=125,bbox_inches='tight')
    plt.close(fig)


def cycles():
    fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained')
    theta=np.linspace(0,2*math.pi,300)
    specs=[('stable',(.25,1.5),'Stable: both sides approach'),
           ('unstable',(.98,1.02),'Unstable: both sides leave'),
           ('half_stable',(.8,1.5),'Half-stable: outside approaches')]
    for ax,(kind,starts,title) in zip(axes[0],specs):
        ax.plot(np.cos(theta),np.sin(theta),'--',color=INK,lw=1,label='Unit cycle')
        for initial,color in zip(starts,(BLUE,ORANGE)):
            rows,stop=radial_trajectory(kind,initial); arr=np.array(rows)
            ax.plot(arr[:,1],arr[:,2],color=color,lw=.8,label=f'r₀={initial}')
            ax.scatter([arr[0,1]],[0],color=color,s=20)
            at=min(300,len(rows)-10)
            ax.annotate('',xy=arr[at+8,1:],xytext=arr[at,1:],arrowprops={'arrowstyle':'->','color':color})
        ax.set(title=title,xlabel='x',ylabel='y'); ax.set_aspect('equal');ax.legend(fontsize=7)
    ax=axes[1,0]
    rows=np.array(radial_trajectory('stable',1.5)[0])
    ax.plot(rows[:,0],rows[:,1],color=BLUE,label='x(t), starting outside')
    ax.plot(rows[:,0],np.cos(rows[:,0]),'--',color=ORANGE,lw=.8,label='cos(t)')
    ax.set(title='Steady amplitude, period 2π',xlabel='Time',ylabel='x');ax.legend(fontsize=8)
    ax=axes[1,1]
    for initial in ([.5,.7],[-.5,-.7]):
        rows=integrate(gradient,initial,10,.01)
        ax.plot([r[0] for r in rows],[potential(*r[1:]) for r in rows],lw=1.4,label=str(initial))
    ax.set(title='Gradient example: V keeps decreasing',xlabel='Time',ylabel='V = −x sin y')
    ax.text(.04,.12,'dV/dt = −sin²y − x²cos²y',transform=ax.transAxes)
    ax=axes[1,2]
    r=np.linspace(.2,1.65,300);ax.plot(r,r*(1-r*r),color=BLUE)
    ax.axhline(0,color=INK,lw=.7)
    for radius,color in [(.5,TEAL),(1.5,ORANGE)]:
        ax.scatter([radius],[radial_rate(radius,'stable')],c=color)
        ax.axvline(radius,color=color,ls=':',label=f'Boundary r={radius}')
    ax.set(title='A trapping annulus: 0.5 ≤ r ≤ 1.5',xlabel='Radius r',ylabel='Radial rate');ax.legend(fontsize=8)
    fig.suptitle('Cycles and exclusion arguments · equations and domains matter',fontsize=16)
    save(fig,'cycles')


def selkov_and_transitions():
    fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained')
    ax=axes[0,0]; bs=np.linspace(.05,1.1,400)
    traces=[selkov_equilibrium(.1,b)['trace'] for b in bs]
    ax.plot(bs,traces,color=BLUE);ax.axhline(0,color=INK,lw=.8)
    lo,hi=selkov_hopf_bounds(.1);ax.axvspan(lo,hi,color=ORANGE,alpha=.15,label='Repelling equilibrium')
    ax.set(title='Sel’kov stability window · a=0.1',xlabel='b',ylabel='Jacobian trace');ax.legend(fontsize=8)
    ax=axes[0,1]
    for initial,color in [([.4,1.5],BLUE),([1.2,.3],ORANGE)]:
        rows=np.array(integrate(selkov(.1,.5),initial,100,.02))
        ax.plot(rows[:,1],rows[:,2],color=color,lw=.9,label=f'Start {initial}')
    ax.scatter([.5],[.5/.35],c=INK,s=25,label='Repeller')
    ax.set(title='Two starts approach the same orbit',xlabel='x',ylabel='y');ax.legend(fontsize=7)
    ax=axes[0,2]
    for b,color in [(.2,TEAL),(.5,BLUE),(1,ORANGE)]:
        rows=np.array(integrate(selkov(.1,b),[.4,1.5],100,.02))
        ax.plot(rows[:,0],rows[:,1],color=color,lw=1,label=f'b={b}')
    ax.set(title='Settling versus sustained oscillation',xlabel='Time',ylabel='x');ax.legend(fontsize=8)
    ax=axes[1,0]
    trap=selkov_trap(.1,.5);Y,L=trap['Y'],trap['L']
    ax.fill([0,L,L-Y,0],[0,0,Y,Y],color='#e7eff2')
    xs=np.linspace(0,L,18);ys=np.linspace(0,Y,15);X,Z=np.meshgrid(xs,ys)
    U=-X+(.1+X*X)*Z;V=.5-(.1+X*X)*Z;norm=np.hypot(U,V); mask=X+Z>L
    ax.quiver(np.ma.masked_where(mask,X),np.ma.masked_where(mask,Z),U/(norm+1e-12),V/(norm+1e-12),color='#8b9fa7',scale=24,width=.003)
    rows=np.array(integrate(selkov(.1,.5),[.4,1.5],100,.02))
    ax.plot(rows[:,1],rows[:,2],color=BLUE,lw=1);ax.scatter([.5],[.5/.35],color=ORANGE,s=20)
    ax.set(title='Explicit outer trapping polygon',xlabel='x',ylabel='y',xlim=(-.1,7.7),ylim=(-.1,6.2))
    for ax,field,title in [(axes[1,1],planar_pitchfork(.5),'Chosen pitchfork: two stable points'),
                            (axes[1,2],hopf_normal_form(.5),'Chosen Hopf: one stable cycle')]:
        for initial,color in [([.1,.8],BLUE),([-.1,-.8],ORANGE),([.15,0],TEAL)]:
            rows=np.array(integrate(field,initial,30,.02));ax.plot(rows[:,1],rows[:,2],lw=.8,color=color)
        ax.set(title=title,xlabel='x',ylabel='y');ax.set_aspect('equal')
    axes[1,1].scatter([-math.sqrt(.5),math.sqrt(.5)],[0,0],c=INK,s=22)
    fig.suptitle('Sel’kov and changes of stability · equilibrium splitting versus a new cycle',fontsize=15)
    save(fig,'selkov')


def nonlinear():
    fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained')
    ax=axes[0,0]
    rows=np.array(integrate(vdp(.1),[.1,0],160,.02))
    ax.plot(rows[:,1],rows[:,2],color=BLUE,lw=.45)
    ax.set(title='Weak van der Pol · μ=0.1',xlabel='x',ylabel='Velocity');ax.set_aspect('equal')
    ax=axes[0,1]
    rows=np.array(integrate(vdp_lienard(10),[2,0],90,.002));late=rows[rows[:,0]>=50]
    x=np.linspace(-2.3,2.3,200)
    ax.plot(x,x**3/3-x,'--',color=INK,lw=1,label='Cubic y=F(x)')
    ax.plot(late[:,1],late[:,2],color=BLUE,lw=1.2,label='Late orbit')
    ax.set(title='Relaxation · μ=10 · Liénard coordinates',xlabel='x',ylabel='y = velocity/μ + F(x)');ax.legend(fontsize=7)
    ax=axes[0,2]
    ax.plot(rows[:,0],rows[:,1],color=BLUE,lw=1)
    ax.set(title='Slow drift and fast jumps',xlabel='Time',ylabel='x')
    ax=axes[1,0]
    for amplitude,color in [(.5,TEAL),(1.5,BLUE),(2,ORANGE)]:
        r=np.array(integrate(duffing(.1),[amplitude,0],20,.01))
        ax.plot(r[:,1],r[:,2],color=color,lw=1,label=f'Initial amplitude {amplitude}')
    ax.set(title='Duffing: a family of closed orbits',xlabel='x',ylabel='Velocity');ax.legend(fontsize=7)
    ax=axes[1,1]
    for mu,color in [(.1,BLUE),(10,ORANGE)]:
        duration=160 if mu==.1 else 60;step=.02 if mu==.1 else .002
        initial=[.1,0] if mu==.1 else [2,0]
        r=np.array(integrate(vdp(mu),initial,duration,step))
        ax.plot(r[:,0],(r[:,1]**2+r[:,2]**2)/2,color=color,lw=.6,label=f'μ={mu}')
    ax.set(title='Van der Pol trades energy each cycle',xlabel='Time',ylabel='(x² + velocity²)/2');ax.legend(fontsize=8)
    ax=axes[1,2]
    r=np.array(integrate(duffing(.1),[1.5,0],100,.02));energy=duffing_energy(1.5,0,.1)
    ax.plot(r[:,0],[duffing_energy(*p[1:],.1)-energy for p in r],color=BLUE)
    ax.ticklabel_format(axis='y',style='sci',scilimits=(0,0))
    ax.set(title='Duffing energy: numerical drift only',xlabel='Time',ylabel='Computed E(t) − E(0)')
    fig.suptitle('Nonlinear oscillators · self-selected amplitude versus conserved energy',fontsize=16)
    save(fig,'nonlinear_oscillators')


def averaging():
    fig,axes=plt.subplots(2,2,figsize=(13,8),layout='constrained')
    ax=axes[0,0];rows=np.array(integrate(cubic_damping(2),[1,0],50,.01))
    ax.plot(rows[:,0],rows[:,1],color=BLUE,label='Numerical, ε=2')
    ax.plot(rows[:,0],[cubic_damping_approx(t,1,2) for t in rows[:,0]],'--',color=ORANGE,label='Leading averaged prediction')
    ax.set(title='Cubic velocity damping: approximation checked',xlabel='Time',ylabel='x');ax.legend(fontsize=8)
    ax=axes[0,1];amplitudes=np.linspace(.02,1,100)
    ax.plot(amplitudes,[2*math.pi/pendulum_period(a,400) for a in amplitudes],color=BLUE,label='Energy integral')
    ax.plot(amplitudes,1-amplitudes**2/16,'--',color=ORANGE,label='1 − amplitude²/16')
    ax.set(title='Pendulum: larger swings run slower',xlabel='Initial angle amplitude',ylabel='Frequency');ax.legend(fontsize=8)
    ax=axes[1,0]
    rows=np.array(integrate(swing(.1,0),[.005,0],160,.01))
    averaged=np.array(integrate(swing_averaged(.1,0),[.005,0],160,.01))
    envelope=np.hypot(averaged[:,1],averaged[:,2])
    ax.plot(rows[:,0],rows[:,1],color=BLUE,lw=.75,label='Full nonlinear swing')
    ax.plot(averaged[:,0],envelope,color=ORANGE,label='Averaged envelope')
    ax.plot(averaged[:,0],-envelope,color=ORANGE)
    ax.set(title='Resonant pumping grows a small push',xlabel='Time',ylabel='Angle');ax.legend(fontsize=8)
    ax=axes[1,1]
    for gamma,color in [(0,BLUE),(1,ORANGE)]:
        rows=np.array(integrate(swing(.1,gamma),[.005,0],160,.01))
        ax.plot(rows[:,0],np.hypot(rows[:,1],rows[:,2]),color=color,lw=1,label=f'γ={gamma}, small push')
    ax.axhline(0,color=INK,ls='--',label='Exactly at rest')
    ax.set(title='Starting state and detuning matter',xlabel='Time',ylabel='√(angle² + velocity²)');ax.legend(fontsize=8)
    fig.suptitle('Averaging tests · measured errors and the need for a seed',fontsize=16)
    save(fig,'averaging')


def build_figures():
    cycles();selkov_and_transitions();nonlinear();averaging()


def html_section():
    d=json.loads((ROOT/'oscillation_results.json').read_text(encoding='utf-8'))
    cycle=d['selkov'][1]['cycle'];lo,hi=d['selkov_hopf_b_at_a_0_1']
    rows=''.join(f"<tr><td>{r['mu']}</td><td>{r['cycle']['mean_period']:.6f}</td><td>{r['cycle']['x_max']:.6f}</td><td>{abs(r['cycle']['mean_period']-r['coarse_cycle']['mean_period']):.2g}</td></tr>" for r in d['van_der_pol'])
    return f'''<section id="oscillations"><h2>Batch 3 · when motion keeps repeating</h2>
<p>A stable limit cycle attracts nearby motion. An unstable cycle repels it. A half-stable cycle attracts from one side and repels from the other. We tested explicit radial examples on both sides of the unit circle; the unstable outer trajectory stops just before radius 2 to avoid its finite-time escape.</p>
<figure><img src="figures/cycles.png" alt="Stable, unstable and half-stable cycles, sinusoidal settling, decreasing gradient potential, and trapping annulus"><figcaption>The classification examples use stated equations. The stable example has r′=r(1−r²), θ′=1; its exact radius agrees with the numerical solution to {d['stable_radius_max_error']:.2g} over the tested interval.</figcaption></figure>
<h3>When a closed orbit is impossible</h3><p>For your gradient example, x′=sin y and y′=x cos y, the potential V=−x sin y satisfies dV/dt=−sin²y−x²cos²y. A nonconstant closed orbit would have to return to its original potential despite losing potential along the way, which is impossible.</p>
<div class="scroll"><table><tr><th>Dulac example</th><th>Weight g</th><th>div(gF)</th><th>Domain</th></tr><tr><td>x′=x(2−x−y), y′=y(4x−x²−3)</td><td>1/(xy)</td><td>−1/y</td><td>x&gt;0, y&gt;0</td></tr><tr><td>x′=y, y′=−x−y+x²+y²</td><td>e⁻²ˣ</td><td>−e⁻²ˣ</td><td>Entire plane</td></tr></table></div>
<p>Both divergences are strictly negative on their stated simply connected domains, excluding closed orbits there. The first vector field is reconstructed from the weighted expressions in your crop. The analytic identities establish these conclusions; sample trajectories and finite-difference tests check the implementation.</p>
<h3>When a closed orbit must exist</h3><p>For the stable radial example, flow points into the annulus 0.5≤r≤1.5 on both boundaries and never stops inside. This supplies the trapping and no-equilibrium conditions for Poincaré–Bendixson. The annulus has a hole; it does not meet Dulac's simply connected domain condition.</p>
<p>The earlier μ-dependent annulus image (Figure 7.3.3) still needs its equations. It is recorded as pending, rather than assigned a guessed vector field.</p>
<h3>Sel’kov: a stable state can give way to a rhythm</h3><div class="equation">x′=−x+ay+x²y &nbsp; · &nbsp; y′=b−ay−x²y</div>
<p>The equilibrium is (b,b/(a+b²)). Its determinant is a+b² and its trace is [b²−a−(a+b²)²]/(a+b²). At a=0.1 it is repelling for <strong>{lo:.6f}&lt;b&lt;{hi:.6f}</strong>. A compact trapping polygon and a small excluded neighborhood of that repeller establish existence of a periodic orbit. This argument alone does not establish uniqueness.</p>
<figure><img src="figures/selkov.png" alt="Selkov stability window, converging cycle trajectories, trapping polygon, and chosen pitchfork and Hopf comparisons"><figcaption>At a=0.1, b=0.5, two initial states approach numerically matching cycles with period {cycle['mean_period']:.6f}. At b=0.2 and b=1 the tested trajectories settle to the stable equilibrium. The bottom-right comparisons are chosen normal forms; Figure 8.1.7's original equations were not supplied.</figcaption></figure>
<h3>Liénard, van der Pol, and Duffing</h3><p>For van der Pol, x″+μ(x²−1)x′+x=0, the supplied Liénard hypotheses hold for μ&gt;0: f is even, g=x is odd and restoring, and F=μ(x³/3−x) changes sign once on the positive axis at √3 and then increases without bound. Thus there is a unique stable limit cycle. Weak damping gives an almost circular orbit of amplitude near 2; stronger damping gives slow drifts and fast jumps.</p>
<figure><img src="figures/nonlinear_oscillators.png" alt="Weak van der Pol, relaxation orbit in transformed coordinates, waveform, and Duffing energy and closed orbit families"><figcaption>The relaxation plot uses y=x′/μ+x³/3−x, so its vertical coordinate is not velocity. Its illustrated initial state is (x,y)=(2,0), matching the supplied figure; the period runs separately start at (x,velocity)=(2,0).</figcaption></figure>
<div class="scroll"><table><tr><th>van der Pol μ</th><th>Measured period</th><th>Maximum x</th><th>Period change on halving step</th></tr>{rows}</table></div>
<p>At μ=10 the leading large-μ period estimate is {d['van_der_pol'][-1]['large_mu_period_leading_term']:.4f}, compared with {d['van_der_pol'][-1]['cycle']['mean_period']:.4f} numerically. This asymptotic estimate is still approximate at μ=10. The maximum same-time state difference after halving the step is {d['van_der_pol'][-1]['max_step_refinement_difference']:.4g}, concentrated around fast jumps; period agreement does not imply equal accuracy for every state component.</p>
<p>The supplied unforced Duffing equation, x″+x+εx³=0, conserves E=x′²/2+x²/2+εx⁴/4. Its closed orbits form a family with different amplitudes and periods. They are not isolated attracting limit cycles. With ε=0.1, initial amplitudes 0.5, 1.5, and 2 give periods 6.225140, 5.814440, and 5.516852, checked against an independent energy integral.</p>
<h3>Averaging and the pumped swing</h3><figure><img src="figures/averaging.png" alt="Cubic damping approximation, pendulum frequency correction, resonant swing growth and detuning"><figcaption>The approximation is compared with the full equation and a smaller integration step. All examples use dimensionless time.</figcaption></figure>
<p>The pendulum frequency correction ω≈1−A²/16 agrees closely with its energy-integral frequency for the tested A=0.1, 0.4, 0.8. Green's theorem applied to a circular approximation of weak van der Pol gives επR²(1−R²/4)=0, selecting R≈2.</p>
<p>The cropped cubic-damping exercise uses x″+εx′³+x=0. Its leading averaged prediction is x≈cos(t)/√(1+3εt/4) for the supplied unit initial displacement. At ε=2 on 0≤t≤50, its maximum position error is {d['averaging']['cubic_velocity_damping'][1]['maximum_approximation_error']:.3f}; the test records the visible early discrepancy as well as the later decay.</p>
<p>For x″+(1+εγ+ε cos 2t) sin x=0, exact rest remains rest. A small initial angle of 0.005 grows to a maximum absolute angle of {d['averaging']['pumped_swing'][0]['max_absolute_angle']:.4f} by t=160 for ε=0.1, γ=0; the detuned γ=1 run stays below {d['averaging']['pumped_swing'][1]['max_absolute_angle']:.4f}. The leading small-angle instability band is |γ|&lt;1/2. This time-dependent model needs a seed and its averaging approximation has a stated small-angle range.</p>
<p><a href="oscillation_results.json">All third-batch measurements</a> · <a href="OSCILLATION_METHODS.md">Equations, proofs, numerical settings, and limitations</a></p></section>'''


if __name__=='__main__':
    build_figures()
    print('Built four oscillation figures.')
