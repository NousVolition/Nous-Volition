"""Run the screenshot stability examples and direct audits of the substance model."""
import base64,hashlib,html,json,platform,zipfile
from pathlib import Path
import numpy as np
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from models import *

ROOT=Path(__file__).resolve().parent
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})


def run():
    log=(ROOT/'test_log.txt').read_text(encoding='utf-8-sig')
    assert 'Ran 19 tests' in log and log.rstrip().endswith('OK'),'Run verification first.'
    data=dict(scope='Eight screenshot interpretations, with direct stability and energy audits of the earlier substance model',
        tests_passed=19,versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__))
    arrays={};fig,ax=plt.subplots(2,3,figsize=(15,9),layout='constrained')
    colors=['#007f73','#777777','#c25225'];cubic=[]
    for a,col in zip([-1,0,1],colors):
        t,z,row=cubic_case(a);cubic.append(row)
        arrays[f'cubic_a{a}']=np.vstack([t,z])
        ax[0,0].plot(*z,color=col,label=f'a={a:+d}',lw=1.8)
        ax[0,0].scatter(*z[:,-1],color=col,s=22)
    ax[0,0].scatter(.2,0,c='black',s=25,label='common start')
    ax[0,0].set(title='Real spirals missed by linearization',xlabel='x (state coordinate)',ylabel='y (state coordinate)',aspect='equal')
    ax[0,0].legend(fontsize=9)
    data['cubic_spiral']=cubic
    data['cubic_tolerance_check']=[dict(rtol=rtol,max_step=1,error=cubic_case(1,rtol=rtol,max_step=1)[2]['max_state_error']) for rtol in [1e-7,1e-9,1e-11]]

    returns=[]
    for r0 in [.2,.8,1,1.5,3]:
        t,r=numerical_return(r0)
        returns.append(dict(r0=r0,return_time=t,return_radius=r,
            exact_return_radius=float(cycle_radius(2*np.pi,r0)),time_error=abs(t-2*np.pi)))
    monodromy=cycle_monodromy()
    data['poincare']=dict(returns=returns,monodromy=monodromy.tolist(),
        numerical_multipliers=np.sort(np.real_if_close(np.linalg.eigvals(monodromy))).tolist(),
        exact_radial_multiplier=float(np.exp(-4*np.pi)),
        backward_radius_from_08_after_one_turn=float(cycle_radius(-2*np.pi,.8)),
        lower_time_boundary_for_r0_15=float(.5*np.log(1-1/1.5**2)),
        correction='Attraction is forward in time. For 0<r0<1, backward trajectories tend to the origin; for r0>1, backward flow blows up in finite time. The origin is excluded from the transverse section.')

    competition=competition_examples();data['competition_fixed_points']=competition_fixed_points()
    data['competition_runs']=[r for t,z,r in competition]
    data['linearization_refinement']=[linearization_error(eps) for eps in [.04,.02,.01,.005]]
    gridx=np.linspace(0,3.4,19);gridy=np.linspace(0,2.6,17)
    X,Y=np.meshgrid(gridx,gridy);F=X*(3-X-2*Y);G=Y*(2-X-Y)
    norm=np.hypot(F,G);norm=np.where(norm>0,norm,1)
    ax[0,1].quiver(X,Y,F/norm,G/norm,color='#c5ced6',width=.003)
    for k,(t,z,row) in enumerate(competition):
        ax[0,1].plot(*z,lw=1.1)
        arrays[f'competition_{k}']=np.vstack([t,z])
    for k,z in enumerate(stable_manifold()):
        ax[0,1].plot(*z,color='#18273d',ls='--',lw=2,label='basin boundary' if k==0 else None)
        arrays[f'stable_manifold_{k}']=z
    for x,y in [(0,0),(0,2),(3,0),(1,1)]:ax[0,1].scatter(x,y,color='black',s=23,zorder=4)
    ax[0,1].set(title='Population outcomes, not object positions',xlabel='Rabbit population x (scaled)',ylabel='Sheep population y (scaled)',xlim=(0,3.4),ylim=(0,2.6))
    ax[0,1].legend(fontsize=8,loc='upper right')

    xx=np.linspace(-1.8,1.8,301);vv=np.linspace(-1.25,1.25,281)
    X,V=np.meshgrid(xx,vv);EE=V*V/2+potential(X)
    ax[0,2].contour(X,V,EE,levels=[-.23,-.17,-.08,0,.12,.245],colors=['#578090'],linewidths=.8)
    tau=np.linspace(-7,7,1001);hx=np.sqrt(2)/np.cosh(tau);hv=-hx*np.tanh(tau)
    ax[0,2].plot(hx,hv,color='#b56830',lw=1.5,label='E=0 separatrix')
    ax[0,2].plot(-hx,-hv,color='#b56830',lw=1.5)
    ax[0,2].scatter([-1,0,1],[0,0,0],c='black',s=24)
    ax[0,2].set(title='Conserved energy gives contours',xlabel='Position x (dimensionless)',ylabel='Velocity v (dimensionless)',xlim=(-1.8,1.8),ylim=(-1.25,1.25))
    ax[0,2].legend(fontsize=8)
    wellrows=[]
    for gamma,col in [(0,'#3465a4'),(.2,'#b55b37')]:
        t,z,en,row=well_case(gamma=gamma);wellrows.append(row)
        arrays[f'well_gamma{gamma}']=np.vstack([t,z,en])
        ax[1,0].plot(t,en,color=col,label=f'E, damping={gamma:g}')
        if gamma:
            ax[1,0].plot(t,en+z[2],ls='--',color=col,label='E + heat, damping=0.2')
    ax[1,0].set(title='Damping transfers energy to the surroundings',xlabel='Time (dimensionless)',ylabel='Energy (dimensionless)')
    ax[1,0].legend(fontsize=8)
    data['double_well']=dict(potential='V=x^4/4-x^2/2, illustrative dimensionless choice, not specified in screenshot',
        runs=wellrows,above_barrier=well_case((0,.7))[3],time_reversal=[reversal_case(g) for g in [0,.2]])

    exch=[]
    for name,H in [('CO',9.7e-6),('acetone',.27),('H2O2',860)]:
        t,z,row=exchange_case(name,H);exch.append(row)
        eq=row['equilibrium_aqueous_percent']/100
        ax[1,1].plot(t,z[1]/eq,label=name,lw=1.7)
        arrays['exchange_'+name]=np.vstack([t,z])
    ax[1,1].set(title='Gas/water equilibrium: a stable state',xlabel='Time (s)',ylabel='Liquid uptake / equilibrium uptake',xscale='log',xlim=(.001,20),ylim=(0,1.03))
    ax[1,1].legend(fontsize=8)
    data['gas_water_stability']=exch

    charged=[]
    for sign,label,col in [(1,'Like charges','#ba5727'),(0,'Neutral control','#6d7480'),(-1,'Opposite charges','#18776c')]:
        t,s,U,Q,row=charged_drag_case(sign);charged.append(row)
        ax[1,2].plot(t,s*1e6,color=col,label=label,lw=1.8)
        arrays[f'charged_sign{sign}']=np.vstack([t,s,U,Q])
    ax[1,2].axhline(6,color='#aaa',lw=.8,ls='--')
    ax[1,2].set(title='Actual separation driven by Coulomb force',xlabel='Time (s)',ylabel='Particle separation (µm)')
    ax[1,2].legend(fontsize=8)
    data['charged_drag_energy']=charged
    fig.suptitle('Stability, energy and physical forces answer different questions',fontsize=17)
    fig.savefig(ROOT/'stability_and_energy.png',dpi=180,bbox_inches='tight')
    fig.savefig(ROOT/'stability_and_energy.svg',bbox_inches='tight');plt.close(fig)
    np.savez_compressed(ROOT/'trajectories.npz',**arrays)
    (ROOT/'results.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    write_report(data)
    files=sorted(p for p in ROOT.rglob('*') if p.is_file() and p.suffix!='.zip' and p.name!='manifest.json' and '__pycache__' not in p.parts)
    (ROOT/'manifest.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2),encoding='utf-8')
    with zipfile.ZipFile(ROOT/'stability_tests.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files+[ROOT/'manifest.json']:z.write(p,arcname='stability_tests/'+p.relative_to(ROOT).as_posix())
    print(json.dumps(data,indent=2))


def write_report(d):
    def table(heads,rows):
        return '<div class="scroll"><table><tr>'+''.join('<th>'+html.escape(h)+'</th>' for h in heads)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</table></div>'
    fig=base64.b64encode((ROOT/'stability_and_energy.png').read_bytes()).decode()
    pc=d['poincare'];dw=d['double_well'];gd=d['gas_water_stability'];el=d['charged_drag_energy']
    body=f'''<p><a href="../README.md">Substance interaction study</a> · <a href="README.md">This supplement</a> · <a href="../../mechanisms-switching-memory/README.md">Switching and memory</a></p><h1>What these pages add to your research</h1>
    <p class="sub">Eight mathematical pages and three water figures · NousVolition / My-Sources-Project-ALL</p>
    <p class="lead">They tell us how to decide whether a state settles, oscillates or moves away, and how to check that a numerical calculation respects energy and conserved amounts. Those are useful tests of a substance model. They do not, by themselves, identify the force between two substances.</p>
    <p><strong>Completed: all 19 new verification tests pass.</strong> They cover the cubic spiral, return map, population equilibria, a conservative potential, time reversal, gas–water equilibration and deterministic Coulomb motion with drag. These are additional to the previous 28 equation/transport checks. No new arbitrary coupling to airflow was added: the new methods directly audit existing physical mechanisms.</p>
    {water_section(table)}
    <figure><img src="data:image/png;base64,{fig}" alt="Six numerical comparisons of genuine spirals, population dynamics, conserved energy, dissipation, dissolution and Coulomb separation"><figcaption>The first four panels use dimensionless mathematical examples. The last two use the earlier gas–water and charged-particle assumptions with explicit SI units. Each panel states what its axes mean.</figcaption></figure>
    <h2>Image 1: zoom in near an equilibrium</h2>
    <p>A fixed point is a state where both rates of change vanish. It can mean a resting object, steady concentrations, or unchanging populations. Subtract that state and call the small displacement δ. The approximation is δ̇≈Jδ, where J is the matrix of derivatives evaluated at the fixed point. This replaces the curved local rate field with its first-order approximation.</p>
    <p>Negative real parts of both eigenvalues give local asymptotic stability; a positive real part gives instability. Eigenvalues with zero real part require additional analysis. For a nonlinear system, purely imaginary eigenvalues alone do not establish a center. This distinction is also illustrated in <a href="https://ocw.mit.edu/courses/es-1803-differential-equations-spring-2024/mites_1803_s24_topic_full.pdf#page=261">MIT ES.1803 notes, §29.4</a>.</p>
    <p>For the supplied population system, I checked the analytic Jacobian against finite differences. Near (1,1), halving the displacement reduces the vector-field remainder by a factor of four, as the Taylor expansion predicts. This is a local, finite-time approximation: a small omitted term may still decide the long-term outcome.</p>
    {table(['Initial displacement ε','Vector-field remainder','Maximum state error over t=0…1'],[[r['epsilon'],f"{r['vector_field_remainder']:.6g}",f"{r['max_trajectory_error']:.6g}"] for r in d['linearization_refinement']])}
    <h2>Image 3: a genuine spiral that linearization misses</h2>
    <div class="eq">ẋ=−y+ax(x²+y²), &nbsp; ẏ=x+ay(x²+y²)<br>ṙ=ar³, &nbsp; θ̇=1</div>
    <p>At the origin, every value of a gives the same linear matrix [[0,−1],[1,0]], with eigenvalues ±i. That linear system has circular orbits. The full nonlinear system has three different behaviors: a&lt;0 spirals inward, a=0 stays on a circle, and a&gt;0 spirals outward. Linearization is inconclusive here; the cubic terms supply the missing decision.</p>
    <div class="eq">r(t)=r₀/√(1−2ar₀²t).</div>
    <p>The runs use r₀=0.2 and t=0…10. Exact solutions independently verify the numerical trajectories:</p>
    {table(['a','Behavior','Radius at t=10','Maximum state error'],[[r['a'],{-1:'Inward spiral',0:'Circle',1:'Outward spiral'}[r['a']],f"{r['final_radius']:.9f}",f"{r['max_state_error']:.3g}"] for r in d['cubic_spiral']])}
    <p>For a=1 this polynomial model blows up at t=12.5; it is not continued beyond that singularity. For a=−1, attraction is algebraic rather than exponential. For the illustrative state function E=r²/2, Ė=ar⁴: changing amplitude is built into the equation. E is not automatically an energy in joules. The outward spiral here differs from the earlier Euler artifact: it persists in the exact solution. To call it molecular repulsion, x and y would still need a physical meaning and a force model.</p>
    <h2>Image 2: the return-map statement needs a correction</h2>
    <p>For θ̇=1 and ṙ=(1−r²)r, a nonzero trajectory returns to the positive horizontal axis once every 2π time units. The return map is the radius measured once per revolution:</p>
    <div class="eq">P(r)=r/√[r²+(1−r²)e<sup>−4π</sup>].</div>
    <p>The fixed point r=1 of this map represents a periodic orbit of the continuous system. Its radial multiplier is P′(1)=e<sup>−4π</sup>={pc['exact_radial_multiplier']:.10g}. A small radial perturbation is reduced by that factor per turn. The full orbit also has a neutral phase multiplier of 1: shifting where you start along the circle is not a radial instability. Integrating the variational equations gives multipliers {pc['numerical_multipliers'][0]:.10g} and {pc['numerical_multipliers'][1]:.10g}.</p>
    {table(['Initial r','Computed return time','Computed return r','Exact return r'],[[r['r0'],f"{r['return_time']:.10f}",f"{r['return_radius']:.10f}",f"{r['exact_return_radius']:.10f}"] for r in pc['returns']])}
    <p><strong>The screenshot’s claim of convergence to 1 as n→±∞ is incorrect for this example.</strong> Forward iterates approach 1 for every r&gt;0. Backward trajectories with 0&lt;r&lt;1 approach 0. Starting at r=0.8, one backward revolution gives r={pc['backward_radius_from_08_after_one_turn']:.9f}. If r&gt;1, backward flow instead encounters a finite-time blow-up: for r₀=1.5 its lower time boundary is {pc['lower_time_boundary_for_r0_15']:.9f}, so a whole backward revolution is not even defined. The origin itself stays fixed and is excluded from a transverse positive-axis section.</p>
    <h2>Images 4–5: two population outcomes, separated by a boundary</h2>
    <div class="eq">ẋ=x(3−x−2y), &nbsp; ẏ=y(2−x−y).</div>
    <p>Here x and y are scaled rabbit and sheep populations. The four fixed points and classifications in the screenshots are confirmed:</p>
    {table(['Fixed point','Eigenvalues','Classification'],[[str(r['point']),', '.join(f'{v:.8g}' for v in r['eigenvalues']),r['classification']] for r in d['competition_fixed_points']])}
    <p>The two attracting states correspond to one population surviving and the other tending to zero. The stable manifold of the saddle at (1,1) separates their basins of attraction. I traced its two branches by integrating backward from small displacements along the stable eigenvector. Starting only 0.001 from the saddle on opposite sides along its unstable direction leads to opposite outcomes by t=60:</p>
    {table(['Initial (x,y)','Final (x,y)'],[[', '.join(f'{v:.9g}' for v in r['initial']),', '.join(f'{v:.9g}' for v in r['final'])] for r in d['competition_runs'][-2:]])}
    <p>These curves track populations, not where individual animals stand. Competition changes growth rates; no distance-dependent repulsive force is present. Replacing “rabbit” with “CO” and “sheep” with “water” would not produce a justified chemical model. The equations do not conserve x+y and contain population growth terms. A chemical interpretation would need explicit reactions, stoichiometry, reservoirs and measured rates.</p>
    <h2>Images 6–7: an energy well does not imply settling without damping</h2>
    <p>For m ẍ=F(x)=−dV/dx, mechanical energy E=½mv²+V(x) is constant. In a phase portrait, the motion stays on a constant-energy contour. It does not descend the energy surface while energy is conserved. A center is stable in the sense that sufficiently nearby motion stays nearby; it is not an attracting state that all nearby trajectories approach.</p>
    <p>The energy-surface image gives no explicit potential formula. For a reproducible illustration I chose the dimensionless double well V(x)=x⁴/4−x²/2 with m=1. It has minima at x=±1 with E=−¼ and a saddle at (x,v)=(0,0) with E=0. Negative-energy orbits remain in one well; positive-energy orbits can cross between wells. The E=0 homoclinic curves are independently checked using x(t)=±√2 sech(t), v(t)=∓√2 sech(t)tanh(t).</p>
    <p>Starting at (x,v)=(1,0.4) gives E=−0.17. Without damping, that energy stays constant. With damping ẍ=x−x³−γẋ and γ=0.2, Ė=−γv². The lost mechanical energy is tracked as heat Q, so E+Q stays constant:</p>
    {table(['Damping γ','Initial E','E at t=40','Heat Q at t=40','Maximum |E+Q−E₀|'],[[r['gamma'],f"{r['initial_energy']:.8f}",f"{r['final_energy']:.8f}",f"{r['dissipated_energy']:.8f}",f"{r['max_energy_balance_error']:.3g}"] for r in dw['runs']])}
    <h2>Image 8: reversing velocity tests time-reversal symmetry</h2>
    <p>For the position-only conservative force, taking a trajectory backward in time and reversing velocity gives another solution. I integrated from (0.8,0.35) for 12 time units, reversed velocity, and integrated for another 12. The conservative case retraces the path. With the same positive damping on both legs, reversing velocity alone does not undo the energy already transferred to the surroundings.</p>
    {table(['Damping γ','Maximum retracing error','Error returning to (0.8,−0.35)'],[[r['gamma'],f"{r['max_retrace_error']:.6g}",f"{r['end_error']:.6g}"] for r in dw['time_reversal']])}
    <p>This is a symmetry test, not a claim that a damped differential equation cannot be integrated backward mathematically. Damping breaks the same-law velocity-flip symmetry; full time reversal would also have to reverse the energy exchange with the surroundings.</p>
    <h2>Direct application: stability of gas–water partitioning</h2>
    <p>Let G and Q denote gas and dissolved solute inventories in common normalized units. The previous closed-compartment model is Ġ=−k(bG−Q), Q̇=k(bG−Q), where b=εH<sup>cp</sup>RT and k is the liquid-volume mass-transfer coefficient. Its Jacobian is constant:</p>
    <div class="eq">J = [[−kb, k], [kb, −k]], &nbsp; eigenvalues 0 and −k(1+b).</div>
    <p>The zero eigenvalue records conservation of total solute: different total inventories give a line of equilibria. Once the total amount is fixed, the remaining mode decays toward the partition equilibrium. A zero eigenvalue here does not mean droplets repel or that the solution is unstable. The linear model can be solved exactly, so its conserved mode is understood rather than guessed from eigenvalues alone.</p>
    <p>Conditions match the earlier fog pilot: 298.15 K, 101,325 Pa, fixed water volume fraction 5×10⁻⁷, droplet radius 10 µm, no reaction, no evaporation, D<sub>g</sub>=2×10⁻⁵ m²/s and D<sub>l</sub>=2×10⁻⁹ m²/s. Geometry and diffusivities are assumptions. The selected Henry coefficients come from <a href="https://doi.org/10.5194/acp-23-10901-2023">Sander (2023)</a>, with individual source links in references.json. Transfer coefficients use k<sub>l</sub>=D<sub>l</sub>/a, k<sub>g</sub>=D<sub>g</sub>/a and k=3/[a(1/k<sub>l</sub>+HRT/k<sub>g</sub>)].</p>
    {table(['Species','Equilibrium fraction in liquid (%)','Relaxation time 1/rate (s)','Time to 95% of equilibrium (s)','Maximum total-inventory error'],[[r['species'],f"{r['equilibrium_aqueous_percent']:.8g}",f"{r['time_constant_s']:.8g}",f"{r['time_to_95_percent_of_equilibrium_s']:.8g}",f"{r['max_mass_error']:.3g}"] for r in gd])}
    <p>CO rapidly reaches a very small equilibrium uptake in this model. A short relaxation time does not mean a large amount dissolves. None of this converts CO to CO₂. H₂O₂ remains an unreactive comparison tracer for this audit; a catalyst or reaction would require additional terms and an updated balance.</p>
    <h2>Direct application: real Coulomb force with energy lost to drag</h2>
    <p>For two equal particles separated by s, define C=kₑq₁q₂. The far-field pair potential is U=C/s. In the overdamped limit with single-particle mobility μ, ṡ=2μC/s². Thus positive C produces increasing physical separation, negative C decreasing separation. Unlike a phase-portrait radius, s here is explicitly a distance in metres.</p>
    <div class="eq">dU/dt = −2μ(C/s²)² ≤ 0, &nbsp; dQ<sub>heat</sub>/dt = 2μ(C/s²)²<br>s(t)³=s₀³+6μCt.</div>
    <p>Both attraction and repulsion reduce pair potential energy while drag transfers it to the air. The energy balance is U+Q<sub>heat</sub>=constant in this deterministic overdamped model. Conditions: still air at 298.15 K and 101,325 Pa, 1 µm particle radius, initial separation 20 µm, charges +100e/+100e or +100e/−100e. The neutral control has both charges zero. Slip-corrected Stokes mobility follows the earlier closure using <a href="https://nvlpubs.nist.gov/nistpubs/jres/111/4/V111.N04.A01.pdf#page=7">NIST’s documented Kim coefficients</a>. Brownian forcing is deliberately off for this analytic energy check. Hydrodynamic interactions and induced polarization are excluded.</p>
    {table(['Pair','End time (s)','Final separation (µm)','Heat to air (J)','Relative energy residual'],[[{1:'Like charges',0:'Neutral',-1:'Opposite charges'}[r['charge_product_sign']],f"{r['end_s']:.8g}",f"{r['final_separation_m']*1e6:.8g}",f"{r['heat_to_air_J']:.6g}",f"{r['relative_energy_residual']:.3g}"] for r in el])}
    <p>The opposite-charge run stops at a separation of six radii, before near-contact effects invalidate this simple point-charge model. It does not simulate contact, coalescence or chemical bonding. Brownian trajectories from the broader study need stochastic energy accounting; the smooth deterministic energy identity is not applied to individual noisy paths.</p>
    <h2>What the checks establish</h2>
    <p>These computations verify equations, local approximations, analytic solutions, conservation accounting and declared limits. They distinguish three separate ideas: a state returning to equilibrium, a numerical artifact, and a physical force changing actual separation. They do not establish a new fluid law or validate every scenario against laboratory data. The remaining limitations are explicit: chosen dimensionless examples, an illustrative potential, assumed transfer coefficients, deterministic far-field drag, and the conditions already stated in the broader study.</p>
    <p>See <a href="README.txt">README.txt</a> to reproduce the runs. The archive includes source, 19 tests, logs, JSON results, saved trajectories, figures, references and hashes. The attached pages were treated as mathematical source material, not instructions to override the research scope.</p>'''
    css='''body{margin:0;background:#eef2f5;color:#203247;font:16px/1.7 system-ui,Segoe UI,sans-serif}main{max-width:1170px;margin:auto;padding:40px 30px;background:white}h1{font-size:42px;line-height:1.2}h2{font-size:25px;border-top:1px solid #d3dce5;padding-top:24px;margin-top:38px}.lead{font-size:21px}.sub,figcaption{font-size:14px;color:#5a6b7c}figure{margin:25px 0}img{width:100%;height:auto}.eq{background:#edf3f7;padding:16px 20px;border-left:4px solid #187b77;font:18px/1.8 Georgia,serif}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:10px;text-align:left;border-bottom:1px solid #d9e1e8}th{background:#edf3f7}a{color:#195a9c}@media(max-width:700px){main{padding:22px 14px}h1{font-size:31px}}'''
    (ROOT/'report.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Stability, energy and physical forces</title><style>'+css+'</style></head><body><main>'+body+'</main></body></html>',encoding='utf-8')


def water_section(table):
    audit=json.loads((ROOT/'water_figures_audit.json').read_text(encoding='utf-8'))
    v=audit['vibration'];ch=audit['channel'];counts=audit['molecular_screens']
    fig=base64.b64encode((ROOT/'water_evidence_audit.png').read_bytes()).decode()
    return f'''<h2>How your three water figures connect to these methods</h2>
    <p>I located the completed quantum-water study behind your screenshots and independently recalculated its frequency residuals, liquid group statistics, quality-check counts and channel identities. All {len(audit['consistency_checks'])} data-consistency checks passed. This is a reanalysis of existing saved outputs, not a new xTB, molecular-dynamics or Navier–Stokes run. A hashed copy of the relevant inputs is included in prior_water_data/ so these checks can be reproduced independently of the other chat.</p>
    <figure><img src="data:image/png;base64,{fig}" alt="Reanalysis of molecular frequency errors, bond-length shifts and bulk-flow property controls"><figcaption>Values recalculated from the saved study. Liquid error bars are 95% Student-t intervals across three independent runs per condition; they do not include model error or every source of sampling bias.</figcaption></figure>
    <p><strong>1. The vibration chart separates a model/reference mismatch from numerical sensitivity.</strong> All six predicted band positions lie below the measured reference values. Their absolute mismatches range from {v['minimum_absolute_mismatch_cm1']:.3f} to {v['maximum_absolute_mismatch_cm1']:.3f} cm⁻¹; RMSE is {v['RMSE_cm1']:.3f} cm⁻¹. The reported largest numerical spread is {v['reported_max_numerical_spread_cm1']:.6f} cm⁻¹. The largest mismatch is about {v['max_mismatch_over_reported_spread']:.0f} times that tested spread. Smaller numerical steps will not by themselves remove a mismatch of that size.</p>
    <p>The frequencies are unscaled GFN2-xTB harmonic normal modes, whereas the main reference is observed fundamental IR bands. The difference therefore mixes electronic-model error with the harmonic/anharmonic comparison; the bars do not isolate a single cause. The source study also records a separate H₂O harmonic-reference maximum error of {v['harmonic_reference_max_error_percent']:.3f}%. A tested numerical spread is not a rigorous bound on all numerical error.</p>
    <p>This is a direct use of the linearization pages: near a molecular energy minimum, the Hessian K gives the curvature of the potential and M contains nuclear masses. Small displacements obey Mδq̈=−Kδq, with normal modes satisfying Kv=ω²Mv. Changing isotope mass changes the frequencies even with an unchanged potential. A frequency isotope shift alone therefore does not prove that nuclear quantum statistics are required to explain that shift.</p>
    <p><strong>2. The liquid figures show a local structural change, with limits on collective claims.</strong> The 300 K mean covalent bond length changes from about 0.96334 to 0.97903 Å for H₂O, and from 0.96399 to 0.97433 Å for D₂O when switching from classical to 32-bead sampling in this particular q-TIP4P/F calculation. These results concern an equilibrium structural estimator. They do not directly measure viscosity, a physical transport rate, or force-driven repulsion.</p>
    <p>At fixed potential, volume and temperature, classical equilibrium positions have normalized density p(q)∝exp[−V(q)/(k<sub>B</sub>T)]. Integrating out momenta cancels the mass factors, so changing masses alone cannot change that classical equilibrium positional distribution. Residual classical H₂O/D₂O structural differences in these short runs expose finite-sampling, incomplete-equilibration or algorithmic limitations; they are not an equilibrium isotope effect of that classical model. Mass still affects the dynamics.</p>
    <p>The source used 64 molecules, three independent runs per principal condition, 5 ps equilibration and 5 ps structural sampling. Only {counts['diffusion_window_passes']}/{counts['main_runs']} main runs passed its diffusion-window screen and {counts['energy_drift_passes']}/{counts['main_runs']} passed its unthermostatted energy-drift screen. {counts['structural_control_passes']}/{counts['structural_controls']} structural numerical controls passed. These failures concern the relevant diagnostics; they do not erase every measured structural shift, but they prevent a converged bulk-transport claim. The saved summary explicitly says that bulk diffusion is not validated and viscosity was not computed.</p>
    <p>The mean covalent bond length in the top-left panel and the intramolecular radial-distribution peak in the bottom-middle panel are different statistics. A broad, asymmetric distribution can change its mean without moving its peak by the same amount. Comparison to neutron-derived distances also depends on the experimental estimator. Nuclear quantum sampling represents nuclei with a discretized imaginary-time path; 32 beads means 32 computational copies per nucleus, not 32 extra water molecules. This is an equilibrium sampling construction, with approximate real-time dynamics treated separately. The unchanged force field is documented in the <a href="https://arxiv.org/abs/1011.1047">q-TIP4P/F paper</a>.</p>
    <p><strong>3. The bulk-flow figures use an established material-property connection.</strong> They supply density and viscosity from measurement-based IAPWS correlations, including the <a href="https://iapws.org/public/documents/OM7f5/D2Ovisc.pdf">heavy-water viscosity formulation</a>. The molecular simulations did not calculate those inputs. At 25°C, full channel gap h=1 mm and pressure gradient G=10 Pa/m, the steady plane-channel mean is Ū=Gh²/(12μ):</p>
    {table(['Properties supplied','Density (kg/m³)','Viscosity (mPa·s)','Steady mean (mm/s)','Slow relaxation time (s)'],[[r['material'],f"{r['rho_kg_m3']:.4f}",f"{r['mu_Pa_s']*1000:.7f}",f"{r['steady_mean_mm_s']:.7f}",f"{r['tau_s']:.7f}"] for r in ch['properties']])}
    <p>D₂O’s steady mean is {ch['D_over_H_steady_velocity']:.7f} of H₂O’s, or {ch['D_velocity_reduction_percent']:.3f}% lower in this matched pressure-driven channel. Replacing density alone leaves the steady mean unchanged. Replacing viscosity produces the full steady difference. Density does affect startup: for the restricted streamwise channel perturbations used here, δu<sub>t</sub>=νδu<sub>yy</sub>, and λₙ=−ν(nπ/h)² with ν=μ/ρ. These negative rates are the continuum counterpart of a stable linearized mode. The slow time is τ=ρh²/(μπ²). This does not establish stability of arbitrary three-dimensional flows.</p>
    <p>The corresponding energy accounting is dK/dt=pressure work−viscous dissipation. A driven viscous channel is not a conservative oscillator. A numerical energy check must include both terms. Agreement with an analytic channel solution verifies the solver under those assumptions; agreement with viscosity data checks the supplied material properties. Historical measurements used in a correlation's calibration are not independent validation data.</p>
    <p>The archived channel-error budget also shows a useful numerical subtlety: spatial and temporal errors partly cancel. At a fixed spatial grid, reducing the timestep can make the total error slightly larger even while the temporal component becomes smaller. The actual reported time-component errors decrease by about four per halving, consistent with the scheme's second-order time accuracy. Convergence should be assessed component by component, with an analytic reference where available.</p>
    <p><strong>The justified connection is: molecular energy curvature → local vibrational modes; molecular statistical sampling → structural averages; independently supplied viscosity and density → continuum flow.</strong> The step “this molecular simulation predicts the correct viscosity, which predicts the observed flow” has not been established by these figures. The stability and conservation tools help check every link, but they cannot fill a missing measured or derived link.</p>'''


if __name__=='__main__':run()
