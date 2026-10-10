"""Accessible report for the executed Josephson method/order factorial."""
import json
from pathlib import Path


def section(figure):
    r=json.loads(Path('data/junction_orders.json').read_text())
    configs=r['configs'];rk=configs.index(dict(method='rk4',dt=.02,settle=320));lf=configs.index(dict(method='split_verlet',dt=.02,settle=320))
    def fixed(c,name):
        return next(q for q in r['fixed_orders'] if q['config']==c and q['beta']==10 and not q['reset'] and q['order']==name and q['bias']==.5)
    random=next(q for q in r['random_orders'] if q['config']==rk and q['beta']==10 and not q['reset'] and q['bias']==.5 and q['split']=='replication')
    def ci(q,scale=1):return f"{q['mean']*scale:.3f} [{q['lo']*scale:.3f}, {q['hi']*scale:.3f}]"
    rows=[]
    for name,label in [('up','Upward'),('down','Downward'),('alternate_low','Alternate low first'),('alternate_high','Alternate high first')]:
        values=[fixed(c,name)['voltage'] for c in (rk,lf)]
        rows.append('<tr><td>'+label+'</td>'+''.join(f'<td>{0 if abs(v)<1e-8 else v:.6f}</td>' for v in values)+'</tr>')
    errors=[]
    for method,label in [('rk4','RK4'),('split_verlet','Damped leapfrog / Verlet')]:
        for h in (.04,.02):
            value=max(q['maximum_absolute_error'] for q in r['fixed_start_errors'] if configs[q['config']]['method']==method and configs[q['config']]['dt']==h)
            errors.append(f'<tr><td>{label}</td><td>{h}</td><td>{value:.6g}</td></tr>')
    return f'''<div class="eyebrow">Streams and Rocks · executed Josephson follow-up</div>
<h1>Leapfrog, jumping currents, and random order</h1>
<p class="lead">The junction remembers earlier drive through its phase and velocity. Changing current order exposes that history. A second solver checks whether the numerical method is producing the difference.</p>
<nav><a href="worked_models.html">Model atlas</a> · <a href="README.md">Reproduction guide</a> · <a href="data/junction_orders_protocol.json">Frozen design</a> · <a href="data/junction_orders.json">Numerical results</a></nav>
<p class="note">Both requested meanings of “leapfrog” were executed: a damping-aware leapfrog/Verlet solver and an alternating low/high current order. Randomness selected current orders only. No random force or thermal-noise model was added.</p>
<h2>What we varied independently</h2>
<table><tr><th>Factor</th><th>Executed settings</th></tr>
<tr><td>Numerical solver</td><td>Classical RK4; symmetric kick–drift–drag–drift–kick splitting.</td></tr>
<tr><td>Integration step</td><td>0.04 or 0.02.</td></tr>
<tr><td>Settling before measurement</td><td>160 or 320 model-time units.</td></tr>
<tr><td>Measurement</td><td>Always 80 time units; its two 40-unit halves were also recorded.</td></tr>
<tr><td>Inertia parameter β</td><td>0.2, 2, 10.</td></tr>
<tr><td>State handling</td><td>Reset phase and velocity to zero at every current, or retain both between currents. Each independent path starts at zero.</td></tr>
<tr><td>Current order</td><td>Upward, downward, alternate low/high, alternate high/low; 24 seeded random permutations, each paired with its reversal.</td></tr>
<tr><td>Same current values for every path</td><td>0, 0.25, 0.5, 0.7, 0.8, 0.9, 0.95, 1, 1.025, 1.05, 1.1, 1.25, 1.5.</td></tr></table>
<p>This is <strong>{r['sweep_paths']:,} full paths comprising {r['sweep_segments']:,} current-setting segments</strong>, plus {r['fixed_start_runs']} fixed-start trajectories and {r['fixed_reference_runs']} finer-reference trajectories. The 24 permutation seeds are the independent randomization blocks; thousands of segments are not thousands of independent statistical samples. The design was frozen before this batch, after the earlier small pilot, so this remains an exploratory follow-up.</p>
<p>The two alternating orders begin 0 → 1.5 → 0.25 → 1.25… and 1.5 → 0 → 1.25 → 0.25…. Each random permutation contains every current exactly once. Its reversal gives each current complementary early/late positions. Random orders are reused across all numerical settings, making comparisons paired.</p>
<h2>1. Order changes the response when state is retained</h2>
<p>At β=10 and normalized current 0.5, with step 0.02, settling 320, and measurement 80:</p>
<table><tr><th>Order, retaining state</th><th>RK4 mean voltage</th><th>Damped leapfrog mean voltage</th></tr>{''.join(rows)}</table>
<p>Values below 10⁻⁸ in magnitude are rounded to zero in this table; the full signed values are saved. Both methods reproduce the large difference between the upward path and the other three paths. The small variation among moving paths reflects their finite observation windows and trajectories. This does not establish an exact asymptotic switching threshold.</p>
<p><strong>The reset control passed exactly:</strong> within every solver/step/settling/β setting, every current gave the same recorded measurements across all orders when phase and velocity were reset. Initial segments also matched exactly between reset and retained-state paths when their first current matched.</p>
{figure('junction_orders','Each curve is drawn against ascending current for comparison; the connecting lines are not the chronological path. Shading describes random-order mean uncertainty across 12 replication seed blocks. Top-row orders coincide under resetting. All panels use RK4, step 0.02, settling 320, and observation 80.')}
<p>These new downward paths start independently at the highest current. They are not the return leg of the original published up-and-back sweep, which carried its upper-end state straight into the descent. The previous curves and data remain unchanged.</p>
<h2>2. Random order reveals a mixture of outcomes</h2>
<p>For β=10 and current 0.5 under the same RK4 settings, the mean voltage across replication random orders was <strong>{ci(random['voltage'])}</strong>. The fraction exceeding the declared finite-window motion criterion, mean voltage &gt;0.05, was <strong>{ci(random['moving_fraction'],100)}%</strong>. Brackets are descriptive 95% seed-bootstrap intervals.</p>
<p>The mean combines paths that remain near zero and paths that keep moving. It is not a newly discovered intermediate steady-voltage branch. Resetting to the common zero state removes this mixture at current 0.5. A zero reset state is not necessarily the stationary equilibrium for the new current, so resetting does not force zero voltage at every current.</p>
{figure('junction_random_orders','The left panel shows 24 replication paths from 12 seed/reversal pairs; columns are sorted currents, not temporal order. The right panel applies a declared motion threshold. The bands resample whole seed pairs, not individual segments.')}
<p>Discovery seeds were 51100–51111 and replication seeds 61100–61111. Each confidence interval uses 10,000 percentile-bootstrap draws from the 12 seed-pair averages in its split. Intervals quantify variation over the chosen random-order design; they do not measure experimental junction noise, biological variability, or model uncertainty. They are unadjusted for multiple comparisons.</p>
<h2>3. Leapfrog is a useful check, but RK4 is more accurate here</h2>
<p>A separate fixed-start test removes preceding-sweep history: each case begins from a declared rest-style or running state, and both solvers receive the same state and windows. Rest-style starts use φ=arcsin(min(i,1)), v=0; running starts use φ=0, v=max(i,1). For i&gt;1 the rest-style start is not an equilibrium. At i=1, φ=π/2 and v=0 is the exact critical equilibrium.</p>
<p>The table shows the largest voltage discrepancy across 24 fixed-start cases and both settling windows, relative to RK4 step 0.005 at the same windows. This finer reference is a numerical comparison, not exact truth.</p>
<table><tr><th>Method</th><th>Step</th><th>Maximum absolute voltage discrepancy</th></tr>{''.join(errors)}</table>
<p>In these tests, halving the leapfrog step reduces its maximum discrepancy from about 0.01111 to 0.00498. RK4 already agrees much more closely with the finer reference. The worst leapfrog case has β=0.2, i=1.025, the rest-style start, and settling 320. Thus the requested leapfrog option is implemented and verified, but it is not an accuracy upgrade at these steps. Equal step sizes also do not imply equal computational cost; no speed-per-accuracy ranking is claimed.</p>
{figure('junction_numerics','Left: fixed-start numerical discrepancies at identical observation windows. Right: paired effects of changing settling time alone for retained-state random paths at β=10 and step 0.02. Whole-path comparisons include the accumulated consequences of earlier segments.')}
<p>Longer settling can shift the phase at which a finite observation window starts, even after transients have decayed. The two half-window means help expose time-window sensitivity, but their agreement is not a proof of an asymptotic state. Near thresholds, neither a solver switch nor a longer wait automatically settles the question; longer observation and cycle-based averages would be separate future checks.</p>
<h2>How the damping-aware leapfrog step works</h2>
<div class="equation">φ̇=v, &nbsp; βv̇=i−v−sinφ, &nbsp; β&gt;0.<br>Measured voltage: [φ(t₀+T)−φ(t₀)]/T.</div>
<p>For a constant current i during one time step h, perform these updates in order:</p>
<div class="equation">1. v ← v + [h/(2β)](i−sinφ)<br>2. φ ← φ + (h/2)v<br>3. v ← exp(−h/β)v<br>4. φ ← φ + (h/2)v<br>5. v ← v + [h/(2β)](i−sinφ).</div>
<p>Steps 1 and 5 apply the force; steps 2 and 4 advance phase; step 3 integrates drag exactly over its subproblem. The symmetric composition is second order. Removing drag gives ordinary velocity Verlet, the same-time form of leapfrog. This deterministic composition uses the BAOAB splitting structure described by <a href="https://arxiv.org/abs/1308.5814">Leimkuhler, Matthews and Stoltz</a>; its stochastic noise term is absent here. It is not globally energy conserving for the driven, damped junction. The β=0 overdamped equation needs a different formulation.</p>
<h2>Checks and reproducibility</h2>
<p>Eight unit tests passed: exact equilibria, exact drag velocity, second-order phase convergence against an analytic solution, RK4 against an independent analytic linear solution, conservative reversibility, phase-period equivariance, order/reversal integrity, and invalid-parameter handling. Six saved-data checks passed, including finite output, exactly one visit per current, identical initial segments, reset-order invariance, and consistency between whole- and half-window means.</p>
<p><a href="junction_orders.py">Simulation and analysis source</a> · <a href="test_junction_orders.py">Tests</a> · <a href="data/junction_orders_arrays.npz">All segment measurements</a>. Array indices and every current order are documented in the frozen design. To execute independently without overwriting delivered data:</p>
<pre>python test_junction_orders.py
python junction_orders.py --out ../../reproduced-junction-orders</pre>
<p>The original Josephson sweep, the earlier fixed-bias diagnostic, the social SIMS model, and the six-mode memory experiment remain separate. Random current order tests history dependence within this specified junction model; it makes no claim about human leadership or social groups.</p>'''
