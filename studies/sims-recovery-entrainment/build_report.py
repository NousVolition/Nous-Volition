"""Build two offline reading artifacts from executed results and worked derivations."""
import base64,html,json
from pathlib import Path

STYLE='''body{margin:0;background:#eef2f3;color:#23353e;font:17px/1.65 system-ui,Segoe UI,sans-serif}main{max-width:1050px;margin:auto;background:white;padding:42px 38px}h1{font-size:42px;line-height:1.12}h2{font-size:28px;line-height:1.3;margin-top:48px;color:#176977}h3{font-size:21px;margin-top:30px}p{max-width:960px}.eyebrow{letter-spacing:.12em;font-size:13px;color:#176977;text-transform:uppercase;font-weight:700}.lead{font-size:22px}.note{border-left:4px solid #198291;background:#edf6f5;padding:16px 22px}.equation{font:19px/1.7 Cambria,Georgia,serif;background:#f1f5f6;padding:14px 20px;overflow:auto}table{border-collapse:collapse;width:100%;font-size:15px;margin:22px 0}th,td{padding:10px;border-bottom:1px solid #d8e1e4;text-align:left;vertical-align:top}th{background:#edf4f5}a{color:#176977}figure{margin:34px 0}img{max-width:100%;height:auto}figcaption{font-size:14px;color:#587078}pre{padding:18px;background:#f1f5f6;overflow:auto}code{font-size:14px}nav{font-size:15px}footer{border-top:1px solid #ddd;margin-top:40px;padding-top:15px;font-size:14px}details{padding:15px;border:1px solid #d8e1e4;margin:20px 0}summary{font-weight:bold;cursor:pointer}@media(max-width:650px){main{padding:24px 18px}h1{font-size:34px}table{font-size:13px}}@media print{main{padding:0}figure{break-inside:avoid}}'''


def page(title,body):return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>'+STYLE+'</style><main>'+body+'</main></html>'
def figure(name,caption):
    b64=base64.b64encode(Path('analysis',name+'.png').read_bytes()).decode()
    return f'<figure><img alt="{html.escape(caption)}" src="data:image/png;base64,{b64}"><figcaption>{caption}</figcaption></figure>'
def fmt(row,scale=1,places=4):return f"{row['mean']*scale:+.{places}f} [{row['lo']*scale:+.{places}f}, {row['hi']*scale:+.{places}f}]"


def main():
    s=json.loads(Path('analysis/summary.json').read_text());e=json.loads(Path('data/execution.json').read_text());v=json.loads(Path('verification.json').read_text())
    def contrast(name,metric,memory=1,split='replication'):
        return next(r for r in s['recovery_contrasts'] if (r['contrast'],r['metric'],r['memory'],r['split'])==(name,metric,memory,split))
    def rate(endpoint):return next(r for r in s['recovery_rates'] if r['split']=='replication' and r['memory']==1 and r['schedule']=='early' and r['endpoint']==endpoint)
    levels=[]
    for topology in ('ring','random','hub'):
        values=[next(r for r in s['network_levels'] if r['split']=='replication' and r['metric']=='locked_fraction' and r['topology']==topology and r['driver']==mode) for mode in ('none','high_degree','low_degree','distributed')]
        levels.append('<tr><td>'+topology+'</td>'+''.join(f"<td>{100*r['mean']:.2f}%</td>" for r in values)+'</tr>')
    body=f'''<div class="eyebrow">Streams and Rocks · SIMS follow-up · Executed 9 October 2026 UTC</div>
<h1>Recovery, shared rhythms, and the arrangement</h1>
<p class="lead">Longer recovery reduced the average rigidity difference. A shared rhythm coordinated the oscillator SIMS very differently depending on where the signal entered the network.</p>
<nav><a href="worked_models.html">Worked equations and model atlas</a> · <a href="README.md">Reproduction guide</a> · <a href="data/protocol.json">Frozen main design</a> · <a href="verification.json">Verification</a></nav>
<p class="note">These are two distinct SIMS models: the original cooperation-and-memory model, and a new phase-oscillator model. The supplied firefly, Josephson, pendulum, and other equations are analyzed as mathematical models. Shared mathematical structures do not establish that social groups, water, electrical devices, or molecules obey one common physical law.</p>
<h2>What actually ran</h2>
<table><tr><th>Experiment</th><th>Executed scope</th></tr>
<tr><td>Long recovery and repeated stress</td><td>{e['recovery_runs']:,} matched trajectories; 60 SIMS; 480 rounds; 24 fresh seeds; ring/random/hub networks; equal/unequal group sizes; memory on/off; four stress schedules.</td></tr>
<tr><td>Signal placement</td><td>{e['network_runs']} trajectories; 30 oscillator SIMS; the same 24 seed identifiers; four signal placements; two mappings exchange selected occupants and their intrinsic frequencies.</td></tr>
<tr><td>Phase locking and circuits</td><td>96 phase trajectories, including half-step repeats; 732 circuit sweep segments, including a longer-settling repeat; 72 later fixed-bias checks from two initial states.</td></tr>
<tr><td>Worked model atlas</td><td>Circle flows, pendulum energy and damping, cylindrical phase space, vector-field index, gravitational balance, hypercycles, three-group flows, Hamiltonians, predator–prey cycles, and the additional visible index exercises.</td></tr></table>
<p>Main design and analysis code were hashed before the ensemble. Later screenshot-driven additions and the circuit critical-window diagnostic have separate dated records. These are exploratory computations, not an external preregistration. The optional volunteer activity has not been executed.</p>
<h2>1. Does stress leave permanent rigidity?</h2>
<p>We used no stress, an early pulse in rounds 41–80, a late pulse in rounds 201–240, and both pulses. The late-only condition matters: it separates an earlier history of stress from simply having had a more recent pulse.</p>
<p>With memory enabled, the average rigidity difference between early stress and no stress in rounds 441–480 was <strong>{fmt(contrast('early_minus_never','rigid'))}</strong>. The interval includes zero. Cooperation differed by {fmt(contrast('early_minus_never','cooperation'),100,3)} percentage points. This gives no clear evidence of a lasting average rigidity increase at this horizon.</p>
{figure('recovery','Differences from matched no-stress runs. Shading marks possible stress intervals, and colored bands show pointwise 95% intervals across 12 replication seeds. Curves average network and size-balance conditions within seed.')}
<p>That does not mean each run returns to its earlier organization. {100*rate('first_attainment')['mean']:.1f}% of the memory-enabled early-stress pairs reached the original two-block recovery threshold at least once within 400 recovery rounds; only {100*rate('last_40_all_within')['mean']:.1f}% stayed within it in all four final ten-round blocks. These are 72 matched pairs clustered within 12 seeds. First threshold attainment is not sustained recovery.</p>
<p>A second pulse had no clear replicated history effect on average cooperation or rigidity. The memory-enabled same-group-choice interaction was {fmt(contrast('second_pulse_history_interaction','choice_excess'),100,2)} percentage points in replication, but {fmt(contrast('second_pulse_history_interaction','choice_excess',split='discovery'),100,2)} in discovery. Its sign did not replicate; it is not a robust cumulative-stress finding.</p>
<h2>2. Does coordination belong to an individual or a position?</h2>
<p>The oscillator SIMS receive a fixed external rhythm. We put the same total signal strength at a high-degree site, at a low-degree site, or across every site. The comparison also swaps the two selected occupants, moving their intrinsic frequencies and starting phases with them.</p>
<table><tr><th>Arrangement</th><th>No signal</th><th>High-degree site</th><th>Low-degree site</th><th>Distributed signal</th></tr>{''.join(levels)}</table>
<p>Entries are the mean percentage of SIMS meeting the finite-window external-locking criterion in independent replication, averaged across the two occupant mappings. All ring sites have the same degree: its “high” and “low” sites are arbitrary distinct tie selections. The large placement advantage in random and hub graphs is conditional on this graph construction, coupling normalization, forcing strength, and observation window.</p>
{figure('network','Coherence measures alignment among SIMS. External locking measures stable phase relative to the imposed rhythm. High coherence can coexist with continuing collective drift. Error bars resample whole seeds.')}
<p><strong>The arrangement changes how effectively an imposed signal spreads.</strong> This experiment does not measure leadership selection, authority, persuasion, or human conformity. The signal is assigned by the experimenter. Moving only two occupants is a controlled local permutation, not a test of every possible assignment.</p>
<h2>3. What the supplied oscillator pages establish</h2>
<div class="equation">φ̇ = Δ − A sinφ, &nbsp; Δ = Ω − ω<br>Stable locking: |Δ| &lt; A; &nbsp; sinφ* = Δ/A, &nbsp; cosφ* &gt; 0<br>Drift period: T = 2π / √(Δ² − A²), &nbsp; |Δ| &gt; A</div>
<p>At the threshold |Δ|=A the equilibrium is nonhyperbolic and the approach is not ordinary exponential locking. Outside the locking range, phase slips repeat. Across the numerical cases with complete measured cycles, the maximum relative period error against the exact formulas was {s['maximum_phase_period_relative_error']:.2e}.</p>
{figure('entrainment','The supplied triangle response has peak π/2, whereas the sine response has peak 1. Equal-peak normalization restores the same threshold but preserves different drift periods. These are mathematical checks, not measured firefly behavior.')}
<p>The overdamped junction equation has this same form after nondimensionalization. Keeping its inertia term permits distinct responses to rising and falling drive. The undamped pendulum instead conserves energy; it has centers and separatrices, not damping-induced attractors. The <a href="worked_models.html">model atlas</a> gives the equations, deductions, checks, and diagrams.</p>
<h2>How far the evidence goes</h2>
<p>All uncertainty intervals use 10,000 bootstrap samples of 12 independent seed averages per discovery or replication split. They are descriptive and unadjusted for multiple comparisons. SIMS, rounds, network arrangements, and paired counterfactuals are not independent replicates. Mathematical integration error and uncertainty about the modeling assumptions are separate questions.</p>
<p>{v['unit_tests']} main unit tests passed; 12 selected recovery trajectories reran exactly; every matched prefix passed the no-anticipation check; sampled network results retained the same locking classifications at half the integration step. Supplemental checks cover energy balance, simplex invariance, exact solutions, eigenvalues, and vector-field winding.</p>
<p>One circuit value near the critical point was strongly sensitive to settling time: at β=10 and normalized current 1, mean voltage changed from 0.471 to 0.995. We preserve both outputs. The later fixed-bias diagnostic separates initial-state dependence from timestep error; no precise bifurcation location is inferred from that single finite-window value.</p>
<footer>The original six-group results remain in <a href="https://github.com/NousVolition/Nous-Volition/tree/main/studies/social-organization">social-organization</a>. Source material for the new mathematical examples is the user-supplied page extracts; the atlas identifies the visible figures and exercises. The cropped heteroclinic question remains pending its missing equations.</footer>'''
    Path('report.html').write_text(page('SIMS: recovery, shared rhythms, and arrangement',body),encoding='utf-8')
    atlas=ATLAS
    for name,caption in CAPTIONS.items():atlas=atlas.replace('{{'+name+'}}',figure(name,caption))
    Path('worked_models.html').write_text(page('Worked models: locking, energy, topology, and populations',atlas),encoding='utf-8')
    print('Built report.html and worked_models.html')


CAPTIONS={
 'averaging':'Averaging is an approximation whose error can be measured. Parametric instability amplifies perturbations, but exact rest remains an exact solution.',
 'weak_oscillators':'Weak Van der Pol dynamics approach a common amplitude from inside and outside. The supplied Duffing equation instead conserves energy and retains a family of distinct oscillations.',
 'circle':'Exact fixed points and flow directions for visible exercises 4.1.2–4.1.7; k=3 illustrates the general final case.',
 'junction':'Dimensionless Josephson sweep. Solid curves use the initial integration settings; dotted curves use half the step and twice the settling time. Critical-window voltage can remain sensitive to history and observation time.',
 'pendulum':'Conservative pendulum contours. The orange separatrix has energy 1; closed inner curves are librations; outer curves rotate.',
 'cylinder':'Wrapping θ modulo 2π identifies repeated angles. Velocity remains a real coordinate; cylinder height is velocity, not energy.',
 'damping':'Positive linear damping removes energy. The selected trajectories approach rest while total energy decreases.',
 'vector_index':'The supplied field (x²y, x²−y²) has an isolated equilibrium at the origin and index zero. The sampling circle is not a trajectory.',
 'hypercycle':'Three initial conditions were calculated for each n=2–6; these panels show the first realization for n=3–6. A conserved total fraction does not guarantee convergence to equal fractions.',
 'three_group':'Numerical solutions agree with the exact logistic reduction. The sign of r is an assumed interaction rule.',
 'mechanics':'Gravitational force balance is unstable, while a Hamiltonian minimum supports oscillations. The inverse-square panel uses h=k=1.',
 'predator_prey':'Positive Lotka–Volterra trajectories preserve an invariant and surround a center. They are not attracting limit cycles.',
 'complex_fields':'The visible complex-field exercise has index +k for zᵏ and −k for conjugate(z)ᵏ.',
 'index_counterexample':'A smooth polynomial counterexample has exactly two circular periodic orbits, rotating in opposite directions, and no equilibrium in the annulus between them.'}

ATLAS='''<div class="eyebrow">Streams and Rocks · Worked mathematical atlas</div>
<h1>Locking, energy, topology, and interacting populations</h1>
<p class="lead">Different equations can share a useful structure without describing the same kind of system.</p>
<nav><a href="report.html">SIMS results</a> · <a href="#circle">Circle flows</a> · <a href="#phase">Entrainment</a> · <a href="#pendulum">Pendulum</a> · <a href="#index">Index</a> · <a href="#populations">Population models</a> · <a href="#hamiltonian">Hamiltonians</a></nav>
<p class="note">Equations below were transcribed from the supplied extracts. This is an original worked explanation and computational companion, not a reconstruction of unseen textbook pages. Numerical examples use declared dimensionless parameters. Physical, biological, and social interpretations are kept separate.</p>
<h2 id="circle">Circle-flow exercises 4.1.2–4.1.7</h2>
<p>For θ̇=f(θ), roots of f are equilibria, modulo 2π. A negative derivative gives an attracting phase; a positive derivative gives a repelling phase. When the derivative vanishes, inspect the signs of f on both sides.</p>
<table><tr><th>Flow</th><th>Equilibria in [0,2π)</th><th>Classification</th></tr>
<tr><td>1+2cosθ</td><td>2π/3, 4π/3</td><td>Stable, unstable.</td></tr>
<tr><td>sin2θ</td><td>0, π/2, π, 3π/2</td><td>Unstable, stable, unstable, stable.</td></tr>
<tr><td>sin³θ</td><td>0, π</td><td>Unstable, stable; both nonhyperbolic. Cubic signs decide stability.</td></tr>
<tr><td>sinθ+cosθ</td><td>3π/4, 7π/4</td><td>Stable, unstable.</td></tr>
<tr><td>3+cos2θ</td><td>None</td><td>Always positive; continuous rotation. Full-turn period 2π/√8 = π/√2.</td></tr>
<tr><td>sinkθ, k positive integer</td><td>mπ/k, m=0,…,2k−1</td><td>Odd m stable; even m unstable, since f′=k(−1)ᵐ.</td></tr></table>
{{circle}}
<h2 id="phase">Firefly phase model and triangle-wave response</h2>
<p>For Θ̇=Ω and θ̇=ω+A f(Θ−θ), let φ=Θ−θ and Δ=Ω−ω. Then φ̇=Δ−A f(φ). We assume A&gt;0. A fixed phase difference is frequency locking; it need not mean zero phase lag.</p>
<div class="equation">f(φ)=sinφ: stable branch φ*=arcsin(Δ/A) modulo 2π, for |Δ|&lt;A.<br>T<sub>drift</sub>=2π/√(Δ²−A²), for |Δ|&gt;A.</div>
<p>The drift formula follows by integrating one turn, ∫dφ/(Δ−A sinφ), with the direction handled by |Δ|. At |Δ|=A the stable and unstable branches meet in a saddle-node on the circle. The threshold equilibrium is one-sided attracting in a local unwrapped coordinate, not exponentially stable.</p>
<p>Exercise 4.5.1 replaces the sine by a periodic triangle: f(φ)=φ on [−π/2,π/2], and f(φ)=π−φ on [π/2,3π/2]. It is continuous, with slope changes at its peaks.</p>
<div class="equation">Raw triangle: |Δ|&lt;Aπ/2; stable φ*=Δ/A.<br>T = (2/A) log[(|Δ|+Aπ/2)/(|Δ|−Aπ/2)] outside the range.<br>Equal-peak triangle g=(2/π)f: |Δ|&lt;A;<br>T = (π/A) log[(|Δ|+A)/(|Δ|−A)].</div>
<p>These periods follow by integrating the two linear pieces separately; each contributes the same logarithm. The equal-peak comparison has the same locking boundary as the sine but a different near-threshold slowing law. Only the visible triangle definition and part (a) are supplied; these further formulas are our derivations.</p>
<h2>Josephson junction and driven pendulum</h2>
<p>The supplied circuit has supercurrent I<sub>c</sub>sinφ, voltage V=(ℏ/2e)φ̇, resistance R and capacitance C in parallel. Current balance gives:</p>
<div class="equation">(ℏC/2e)φ̈ + (ℏ/2eR)φ̇ + I<sub>c</sub>sinφ = I.<br>τ=(2eI<sub>c</sub>R/ℏ)t, &nbsp; β=2eI<sub>c</sub>R²C/ℏ, &nbsp; i=I/I<sub>c</sub>.<br>βφ″ + φ′ + sinφ = i, &nbsp; V/(I<sub>c</sub>R)=φ′.</div>
<p>Primes here mean derivatives with respect to τ. The overdamped reduction is φ′=i−sinφ after the fast transient when neglecting the inertial term is justified. Its locked equilibria have zero voltage; for |i|&gt;1 the mean normalized voltage is sign(i)√(i²−1). These calculations do not verify the excerpt's example device dimensions or typical physical parameter ranges.</p>
<table><tr><th>Pendulum coefficient</th><th>Circuit coefficient</th></tr>
<tr><td>Moment of inertia mL²</td><td>ℏC/(2e)</td></tr><tr><td>Damping coefficient</td><td>ℏ/(2eR)</td></tr>
<tr><td>Maximum restoring torque mgL</td><td>Critical current I<sub>c</sub></td></tr><tr><td>Constant applied torque</td><td>Bias current I</td></tr></table>
<p>This is a coefficient correspondence between differential equations, not an equality of physical units. At finite β the model has a second state, phase velocity, so initial conditions and sweep history can matter.</p>
{{junction}}
<p>At β=10, i=0.5, the later fixed-bias calculation ended with mean phase speed 0 for the rest initial state and 0.45844 for the running initial state, measured over the final 200 of 600 time units. Across all 36 fixed-bias cases, halving the time step changed the mean speed by at most 9.52×10⁻⁹. These finite-time results support initial-state dependence in the specified model. The original sweep's β=10, i=1 point remains explicitly sensitive to settling time; its voltage is not presented as a converged threshold estimate.</p>
<h2 id="pendulum">Pendulum energy, a cylinder, and damping</h2>
<div class="equation">θ̇=v, &nbsp; v̇=−sinθ, &nbsp; E=v²/2−cosθ, &nbsp; Ė=0.</div>
<p>At (2kπ,0), the linear eigenvalues are ±i and the nonlinear energy contours prove a center. At ((2k+1)π,0), eigenvalues are ±1 with eigenvectors (1,±1): a saddle. Energies −1&lt;E&lt;1 produce libration; E=1 is the separatrix; E&gt;1 gives rotation. Centers are stable against small perturbations but do not attract nearby trajectories.</p>
{{pendulum}}
<p>The state space is S¹×ℝ because θ and θ+2π are the same angle, while v has no periodic identification. Wrapping the horizontal direction of the phase portrait makes a cylinder. It does not change the vector field or convert a conservative center into an attractor.</p>
{{cylinder}}
<div class="equation">With damping: θ̈+bθ̇+sinθ=0; &nbsp; Ė=−bv²≤0.<br>At the lower equilibrium: λ=(-b±√(b²−4))/2.</div>
<p>For 0&lt;b&lt;2 the lower equilibria are stable spirals; at b=2 they are critically damped; for b&gt;2 they are stable nodes. The upper equilibria remain saddles. Energy is nonincreasing; its instantaneous derivative can be zero at a turning point even when the state is not an equilibrium. For the driven junction, the corresponding energy balance is E′=iφ′−(φ′)² with E=β(φ′)²/2−cosφ: drive can replenish what damping removes.</p>
{{damping}}
<h2 id="index">What vector-field index does—and does not—say</h2>
<p>Along a counterclockwise closed contour on which a planar vector field never vanishes, index is the total change of the vector's direction divided by 2π. The contour is a sampling path, not necessarily a trajectory.</p>
<p>In supplied Figure 6.8.5, F=(x²y,x²−y²). At (1,0) it points up; at (1/√2,1/√2) it points right. Following all nine marked directions produces net winding zero. The origin is nevertheless an isolated equilibrium. Thus <strong>zero index does not imply an empty interior</strong>.</p>
{{vector_index}}
<p>The shrinking-contour proof in Figure 6.8.6 applies when a smooth field is nonzero throughout the disk: shrink without crossing a zero, and the direction becomes almost constant, giving index zero. Constant, rotational, and saddle fields were checked as controls, yielding 0, +1, and −1.</p>
<table><tr><th>Visible unusual fixed-point exercise</th><th>Fixed points</th><th>Index</th></tr><tr><td>6.8.2: (x²,y)</td><td>Origin only</td><td>0</td></tr><tr><td>6.8.3: (y−x,x²)</td><td>Origin only</td><td>0</td></tr><tr><td>6.8.4: (y³,x)</td><td>Origin only</td><td>−1</td></tr><tr><td>6.8.5: (xy,x+y)</td><td>Origin only</td><td>0</td></tr></table>
<p>The first two image fields are confined respectively to a right and an upper half-plane of vector directions, so have no full winding. The cubic field is continuously deformable on a nonzero contour to (y,x), a saddle. For (xy,x+y), deform its first component to −x²: where x+y=0, the first component remains −x², so no zero crosses the contour; the final field has no full winding. Numerical winding checks at radii 0.1 and 1 agree.</p>
<h3>6.8.6–6.8.10: periodic orbits and regions</h3>
<p>A simple periodic orbit that bounds a disk has index +1, regardless of whether the flow traverses it clockwise or counterclockwise. Usual nodes, foci and centers contribute +1; saddles contribute −1. Therefore N+F+C=1+S.</p>
<p>For 6.8.7, F=(x(4−y−x²), y(x−1)), the equilibria are (0,0) and (2,0), both saddles; (−2,0), a stable node; and (1,3), a stable focus. Index alone does not exclude a hypothetical orbit around that focus. The complete exclusion uses the invariant axes and B=1/(xy) in each open quadrant: ∇·(BF)=−2x/y has a fixed nonzero sign. Bendixson–Dulac rules out cycles in each quadrant; the axes themselves have one-dimensional flow.</p>
<p>For 6.8.8, draw C₁ and C₂ as disjoint loops inside C₃. The intervening region has index 1−1−1=−1, so it must contain a zero of the field. With usual isolated equilibria, its saddle count exceeds its +1 count by one.</p>
<svg viewBox="0 0 480 240" width="480" role="img" aria-label="Two disjoint loops C1 and C2 inside the larger loop C3; the region between them has net index minus one"><ellipse cx="240" cy="115" rx="215" ry="95" fill="#edf5f5" stroke="#176977" stroke-width="3"/><circle cx="145" cy="110" r="54" fill="white" stroke="#176977" stroke-width="2"/><circle cx="335" cy="110" r="54" fill="white" stroke="#176977" stroke-width="2"/><g font-family="system-ui" font-size="20" text-anchor="middle" fill="#23353e"><text x="145" y="117">C₁</text><text x="335" y="117">C₂</text><text x="240" y="47">C₃</text><text x="240" y="188">intervening index −1</text></g></svg>
<p>The assertion in 6.8.9 is false. An inner clockwise orbit and outer counterclockwise orbit do not require an equilibrium between them. A smooth polynomial counterexample is:</p>
<div class="equation">q=x²+y², &nbsp; g=(q−1)(4−q), &nbsp; w=q−5/2;<br>ẋ=gx−wy, &nbsp; ẏ=wx+gy.<br>ṙ=r(r²−1)(4−r²), &nbsp; θ̇=r²−5/2.</div>
<p>The only nonconstant periodic orbits are r=1 and r=2, with opposite rotations. For 1&lt;r&lt;2 the radial component is strictly positive, even where angular velocity vanishes, so there is no equilibrium there.</p>
{{index_counterexample}}
<p>For 6.8.10 the disk version remains valid on a surface. A noncontractible circle on a cylinder or torus need not bound a disk and can exist with no equilibrium: constant angular motion provides an example. A simple loop on a sphere bounds two disks; applying the disk argument to both sides is consistent with total index 2 for a smooth tangent field with isolated zeros. An “inside” must be specified before transferring a planar argument.</p>
<h3>6.8.11: complex vector fields</h3>
<div class="equation">ż=zᵏ: &nbsp; ṙ=rᵏcos((k−1)θ), &nbsp; θ̇=rᵏ⁻¹sin((k−1)θ), &nbsp; index +k.<br>ż=z̄ᵏ: &nbsp; ṙ=rᵏcos((k+1)θ), &nbsp; θ̇=−rᵏ⁻¹sin((k+1)θ), &nbsp; index −k.</div>
<p>For k=1,2,3, zᵏ has Cartesian components (x,y), (x²−y²,2xy), and (x³−3xy²,3x²y−y³). Conjugating reverses the sign of the second component. The origin is the only equilibrium. The formulas apply for r&gt;0; polar coordinates themselves are singular at the origin.</p>
{{complex_fields}}
<h2>Gravitational equilibrium between two fixed masses</h2>
<div class="equation">ẍ=Gm₂/(d−x)²−Gm₁/x², &nbsp; 0&lt;x&lt;d.<br>x*=d√m₁/(√m₁+√m₂).<br>F′(x*)=2Gm₂/(d−x*)³+2Gm₁/(x*)³ &gt; 0.</div>
<p>Linear perturbations satisfy δ̈=F′(x*)δ, so the eigenvalues are ±√F′(x*): the equilibrium is unstable. The particle is attracted more strongly toward whichever mass it has moved closer to. In the declared example G=d=m₁=1, m₂=4, the balance is x*=1/3 and the eigenvalues are ±9. Both small displacement tests move away, agreeing with the local cosh growth. The source masses are assumed fixed; this is not an orbit model.</p>
<h2 id="populations">Hypercycle and three-group equations</h2>
<div class="equation">Hypercycle: ẋᵢ=xᵢ(xᵢ₋₁−Q), &nbsp; Q=Σⱼxⱼxⱼ₋₁, &nbsp; x₀=xₙ.<br>S=Σxᵢ implies Ṡ=(1−S)Q.</div>
<p>Hence the simplex S=1 is invariant; each zero coordinate remains zero, and positive coordinates remain positive in the continuous equations. Equal fractions xᵢ=1/n form the positive equilibrium. On the simplex tangent space its eigenvalues are exp(−2πik/n)/n, k=1,…,n−1. It is locally asymptotically stable for n=2,3; linearization is inconclusive for n=4 because a pair is purely imaginary; and it is unstable for n≥5 because at least one eigenvalue has positive real part.</p>
<p>We ran three declared positive initial conditions for each n=2–6. Fractions remained nonnegative and summed to one within 3.9×10⁻¹⁵. The n=4 traces do not by themselves settle asymptotic stability; the n=5,6 traces do not constitute a proof of an attracting limit cycle. The mechanism is a cyclic replication rule supplied by the equation, not an empirical finding about real tribes or molecules.</p>
{{hypercycle}}
<div class="equation">Three-group model: ẋ=rxz, &nbsp; ẏ=ryz, &nbsp; ż=−r(x+y)z.<br>x+y+z=1; &nbsp; s=x+y gives ṡ=rs(1−s); &nbsp; x/y is constant when defined.<br>s(t)=s₀eʳᵗ/(1−s₀+s₀eʳᵗ), &nbsp; x=(x₀/s₀)s, &nbsp; y=(y₀/s₀)s.</div>
<p>For an interior mixture and r&gt;0, z→0, x→x₀/(x₀+y₀), y→y₀/(x₀+y₀). For r&lt;0, x,y→0 and z→1. At r=0 nothing changes. The all-z state and the entire z=0 edge are invariant even when these interior limits would suggest otherwise.</p>
<p>In the excerpt's left/right/center interpretation, positive r stipulates that encounters convert the center toward an extreme; negative r stipulates the reverse. Those rules determine the outcome by construction. The model cannot establish that a real ideology behaves that way. Both extreme categories have identical equations, and their relative ratio is preserved.</p>
{{three_group}}
<h2 id="hamiltonian">Hamiltonian exercises 6.5.8–6.5.10</h2>
<div class="equation">H=p²/(2m)+kx²/2 ⇒ ẋ=∂H/∂p=p/m, &nbsp; ṗ=−∂H/∂x=−kx.<br>Thus p=mẋ and mẍ=−kx, with angular frequency √(k/m).</div>
<p>For every differentiable autonomous H(x,p), the chain rule gives Ḣ=Hₓẋ+Hₚṗ=HₓHₚ−HₚHₓ=0. For explicitly time-dependent Hamiltonians, the remaining derivative is ∂H/∂t, so energy conservation is not automatic. This invariant is why trajectories lie along level contours.</p>
<div class="equation">H(r,p)=p²/2+h²/(2r²)−k/r, &nbsp; r&gt;0, h,k&gt;0.<br>ṙ=p, &nbsp; ṗ=h²/r³−k/r².<br>r*=h²/k, p*=0; &nbsp; H<sub>min</sub>=−k²/(2h²); &nbsp; λ=±i k²/h³.</div>
<p>The effective-potential minimum is a center, not an attractor. Negative energy above its minimum gives bounded radial oscillations; zero is the escape-energy threshold, and positive energy permits unbounded radius. The centrifugal term prevents reaching r=0 at finite energy when h&gt;0. Numerical energy drift was checked at two integration steps.</p>
{{mechanics}}
<h2>Predator–prey exercise 6.5.19</h2>
<p>In Ṙ=aR−bRF and Ḟ=−cF+dRF, aR represents unconstrained prey growth, −bRF prey removal through encounters, −cF predator loss without prey, and dRF predator increase from those encounters. The assumptions include mass-action encounters, no prey carrying capacity, no predator satiation, constant rates, and no demographic randomness or spatial structure.</p>
<div class="equation">x=dR/c, &nbsp; y=bF/a, &nbsp; τ=at, &nbsp; μ=c/a.<br>x′=x(1−y), &nbsp; y′=μy(x−1).<br>H=μ(x−log x)+y−log y is constant for x,y&gt;0.</div>
<p>Substituting the rescaling proves the displayed dimensionless equations. Differentiating H makes its two terms cancel. The positive equilibrium (1,1) has eigenvalues ±i√μ and surrounding positive trajectories follow closed level sets. The origin is a saddle. These closed curves are neutral cycles, not attracting periodic states or proof of ecological realism.</p>
{{predator_prey}}
<h2>Weakly nonlinear Van der Pol and Duffing equations</h2>
<div class="equation">Van der Pol: ẍ+x+ε(x²−1)ẋ=0.<br>For E=(ẋ²+x²)/2, Ė=ε(1−x²)ẋ².<br>First-order averaged amplitude: ṙ≈(ε/2)r(1−r²/4).</div>
<p>For positive small ε, the averaged model makes r=0 repelling and r=2 attracting. The full equation adds energy when |x|&lt;1 and removes it when |x|&gt;1; it is not ordinary positive damping everywhere. We ran ε=0.05, 0.1, 0.2 from amplitudes 0.1, 1 and 3. At ε=0.1 all three late half-ranges were approximately 2.000104. The full cycle need not be exactly circular, and the amplitude 2 is a first-order prediction, not an exact full-equation value.</p>
<div class="equation">Duffing as supplied: ẍ+x+εx³=0.<br>H=ẋ²/2+x²/2+εx⁴/4, &nbsp; Ḣ=0.<br>At small εa², frequency ω≈1+3εa²/8.<br>T(a)=4∫<sub>0</sub><sup>π/2</sup> [1+(εa²/2)(1+sin²ψ)]⁻¹ᐟ² dψ.</div>
<p>The period integral follows from energy conservation with x=a sinψ. At ε=0.1, amplitudes 0.2, 1 and 2 gave periods 6.273783, 6.060657 and 5.516852, matching independent quadrature. Larger amplitude means higher frequency for this positive cubic coefficient. No forcing or damping was included in this Duffing example, so its closed curves are not attracting limit cycles.</p>
{{weak_oscillators}}
<h2>Averaging, a swing, and local bifurcations</h2>
<p>The cropped exercise continuation shows cubic <em>velocity</em> damping: ẍ+εẋ³+x=0, with x(0)=a and ẋ(0)=0. This differs from the conservative cubic-displacement term in the Duffing equation above.</p>
<div class="equation">Averaged amplitude: ṙ≈−3εr³/8, &nbsp; phase correction ≈0.<br>x(t)≈a cos(t)/√(1+3εa²t/4).</div>
<p>For the requested a=1, ε=2, 0≤t≤50, the integrated and averaged curves have RMS displacement difference 0.07446 and maximum difference 0.25328. Half-step integration agrees closely, so this discrepancy is primarily an approximation issue. The envelope prediction is useful, but ε=2 is outside a small-ε guarantee.</p>
<p>For 7.6.15, sinx≈x−x³/6 gives the small-amplitude pendulum frequency ω≈1−a²/16. The exact energy integral is T=4∫₀^{π/2}[1−sin²(a/2)sin²ψ]⁻¹ᐟ²dψ. At a=0.3 the exact and approximate frequencies are 0.99437761 and 0.994375. Thus the expansion agrees with the exact small-amplitude limit.</p>
<p>For 7.6.16, the Van der Pol vector field is F=(v,−x−ε(x²−1)v). Its divergence is ε(1−x²). A periodic orbit has zero outward flux because F is tangent to it. Approximating its interior by a disk of radius a, Green's theorem gives 0=επa²(1−a²/4), hence the nonzero radius a≈2. The disk approximation is essential; it does not prove an exactly circular full-system cycle.</p>
<div class="equation">Swing: ẍ+[1+εγ+εcos(2t)]sinx=0.<br>For small x, slow time T=εt gives:<br>dr/dT=(r/4)sin2φ; &nbsp; dφ/dT=γ/2+(1/4)cos2φ.<br>Leading instability range: |γ|&lt;1/2;<br>maximum growth rate in t: (ε/4)√(1−4γ²).</div>
<p>These averaged equations follow by averaging over the fast angle θ=t+φ. The nonzero identities used are ⟨cos(2t)sin2θ⟩=½sin2φ and ⟨cos(2t)cos2θ⟩=½cos2φ. The exact rest state x=ẋ=0 stays at rest: the child needs a perturbation, even inside a parametric-instability range. A generic small perturbation can grow; the leading boundary can shift at higher order. Direct Floquet calculations at ε=0.1 were repeated at twice the resolution, and a full nonlinear run compared exact rest against initial displacement 0.001.</p>
{{averaging}}
<p>The later Figure 8.1.7 is explicitly a local phase portrait and omits its governing equations. A zero-real-eigenvalue bifurcation and a Hopf bifurcation are different: the former has an eigenvalue passing through zero, whereas a generic Hopf crossing uses a complex-conjugate pair with nonzero imaginary part. A nearby periodic orbit may then appear; neither an exact parameter threshold nor a Hopf type can be read from that crop alone.</p>
<p>For illustration only, u̇=μu−u³, v̇=−v has a zero-eigenvalue pitchfork, while u̇=μu−ωv−(u²+v²)u, v̇=ωu+μv−(u²+v²)v with ω≠0 has radial equation ṙ=μr−r³ and a supercritical Hopf cycle r=√μ for μ&gt;0. These are explanatory normal forms, not recovered equations from the screenshot or additional calibrated SIMS models.</p>
<h2>SIMS oscillator assumptions</h2>
<div class="equation">φ̇ᵢ=δᵢ−(K/dᵢ)Σⱼaᵢⱼsin(φᵢ−φⱼ)−Fᵢsinφᵢ.<br>R=|N⁻¹Σᵢexp(iφᵢ)|.</div>
<p>N=30; K=4; δᵢ are sampled uniformly from 0.08 to 0.16; initial phases are uniform on [−π,π]. Every graph has 3N undirected edges and a connected ring backbone. The same total forcing ΣFᵢ=12 is placed at one selected site or split equally over all sites; the no-driver control has Fᵢ=0. A driver is an imposed reference signal, not a leader elected by the SIMS.</p>
<p>Integration uses classical RK4, step 0.04, horizon 120; locking requires |mean phase drift|&lt;0.005 and total unwrapped phase excursion&lt;0.2 over the final 30 time units. Coherence R can be near one even when all phases drift together. Site choice interacts with degree normalization; equal total forcing does not make all input locations dynamically equivalent.</p>
<h2>Scope, omitted text, and reproduction</h2>
<p>The visible content covered here includes circle exercises 4.1.2–4.1.7; the supplied 4.5.1 triangle definition; the Josephson equations and dimensionless limit; pendulum energy, cylinder and damping figures; vector-index Figures 6.8.5–6.8.6; the gravitational-balance prompt; the displayed hypercycle and three-group equations; Hamiltonian exercises 6.5.8–6.5.10; visible parts of 6.5.19; visible index exercises 6.8.2–6.8.11; and the weakly nonlinear equations accompanying Figure 7.6.1. Later subparts cut off in those crops were not reconstructed.</p>
<p><strong>Pending:</strong> the heteroclinic crop starts at part (c) and omits its two differential equations. Knowing that saddles lie at (±1,±1) does not determine their eigenvectors, invariant manifolds, or connecting trajectories. No substitute field has been invented.</p>
<p>Scripts, per-run outputs, design records, exact checks, and the SVG/PNG figures are included. The <a href="README.md">reproduction guide</a> lists execution order. Statistical results and the physical examples are separate; none is an empirical finding about real human populations.</p>
<footer>Source attribution: mathematical statements were transcribed from the user-supplied page images identified above. No edition, page sequence beyond what is visible, or missing exercise text is assumed. Original figures were generated for this companion; scans are not redistributed.</footer>'''


if __name__=='__main__':main()
