"""Run all five screenshot examples and build an illustrated, self-contained report."""
import base64,hashlib,html,json,platform,time,zipfile
from pathlib import Path
from fractions import Fraction
import numpy as np
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from equations import *

HERE=Path(__file__).resolve().parent
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
    'figure.dpi':120,'savefig.dpi':180})


def main():
    start=time.perf_counter()
    data={'scope':'Verification of five supplied equations and explicit one-way coupling to gas/fog transport; no chemical-model substitution',
          'source':'User attachments, Images1-5. Images4/5 are cropped; equations reconstructed from their visible terms.',
          'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,
          'matplotlib':matplotlib.__version__,'cases':{}}
    allcurves={}
    fig,ax=plt.subplots(2,3,figsize=(14,8.8),layout='constrained')

    cycles=[]
    for r in [0,.01,.2,.8,1,1.5,3]:
        z=integrate_cycle(r)
        cycles.append(dict(initial_radius=r,final_radius_t10=z['final_radius'],
                           max_cartesian_error=z['max_position_error']))
        if r in [.2,.8,1,1.5]:
            ax[0,0].plot(*z['numeric'],label=f'r₀={r:g}',lw=1)
        allcurves['cycle_'+str(r)]=z['numeric']
    ax[0,0].scatter(0,0,color='black',s=16,label='r₀=0: fixed')
    ax[0,0].set(title='1. Attraction to a limit cycle',xlabel='x (dimensionless)',ylabel='y (dimensionless)',aspect='equal')
    ax[0,0].legend(fontsize=8,loc='upper right')
    data['cases']['limit_cycle']=dict(results=cycles,period=2*np.pi,
        radial_floquet_multiplier=float(np.exp(-4*np.pi)),
        r0_2_backward_blowup_time=float(.5*np.log(1-1/4)),
        correction='r0=0 is fixed; log derivation needs absolute value for r>1. Positive nonunit radii approach the unit circle.')

    junctions=[]
    for label,i,z0 in [('locked',.5,(0,0)),('running_same_bias',.5,(0,2.5)),('above_threshold',1.2,(0,0))]:
        z=junction(i=i,z0=z0)
        si=junction_si(i=i,z0=z0)
        p=si['parameters']
        row=dict(case=label,i=i,alpha=.2,initial_phase=z0[0],initial_dimensionless_rate=z0[1],
            final_phase_unwrapped=float(z['phi'][-1]),mean_rate_last50=z['mean_last50_rate'],
            mean_voltage_last50_V=z['mean_last50_rate']*p['V_scale_V'],
            max_tilted_energy_balance_error=z['max_energy_balance_error'],
            max_SI_dimensionless_phase_difference=float(np.max(abs(z['phi']-si['phase']))))
        junctions.append(row)
        ax[0,1].plot(z['time'],z['v'],label=f'i={i}, {label.replace("_same_bias","")}',lw=.9)
        allcurves['junction_'+label]=np.vstack([z['time'],z['phi'],z['v']])
    ax[0,1].set(title='2. Junction / driven pendulum',xlabel='τ = ωₚt',ylabel='dφ/dτ')
    ax[0,1].legend(fontsize=8)
    overdamped=[]
    for i in [1.1,1.2,2]:
        actual,exact=overdamped_period(i)
        overdamped.append(dict(i=i,numeric_period=actual,analytic_period=exact,relative_error=abs(actual/exact-1)))
    data['cases']['junction']=dict(parameters=junction_parameters(),runs=junctions,
        overdamped_limit=overdamped,note='C=0 period uses s=(2eRIc/hbar)t, a different time scale from finite-C τ.')

    clock=clock_alignment();rational=Fraction(720,11)
    data['cases']['clock']=dict(numeric_minutes=clock,exact_minutes=str(rational),
        elapsed_minutes_integer=65,elapsed_seconds_remainder=float((rational-65)*60),
        next_clock_time='13:05:27.272727...',
        absolute_error_minutes=abs(clock-float(rational)),
        meaning='Same direction coincidence, not merely collinear opposite hands')
    mins=np.linspace(0,75,301)
    ax[0,2].plot(mins,6*mins,label='Minute hand')
    ax[0,2].plot(mins,.5*mins+360,label='Hour hand + one turn')
    ax[0,2].scatter(clock,6*clock,color='black',zorder=3)
    ax[0,2].set(title='3. Next clock coincidence',xlabel='Minutes after 12:00',ylabel='Unwrapped angle (degrees)')
    ax[0,2].legend(fontsize=8)
    ax[0,2].text(8,420,'65 min 27.273 s',fontsize=10)

    saddle=[]
    for r in [1,.1,.01,.001,.0001]:
        actual,exact=saddle_transit(r)
        tau,u,ue=saddle_scaled(r)
        saddle.append(dict(r=r,transit_from_minus1_to_plus1=actual,analytic_transit=exact,
            asymptotic_pi_over_sqrt_r=float(np.pi/np.sqrt(r)),relative_error=abs(actual/exact-1),
            max_scaled_trajectory_error=float(np.max(abs(u-ue)))))
        ax[1,0].plot(tau,u,label=f'r={r:g}',lw=1.2,ls='--' if r in [.1,.001] else '-')
        allcurves['saddle_scaled_'+str(r)]=np.vstack([tau,u,ue])
    ax[1,0].set(title='4. Rescaling makes curves coincide',xlabel='τ = √r t',ylabel='u = x/√r')
    ax[1,0].legend(fontsize=8)
    data['cases']['saddle_node']=dict(a=.5,b=-.5,validity='r>0 for the real square-root scaling',runs=saddle,
        negative_r_equilibria='x=±sqrt(-r); negative equilibrium stable, positive unstable',
        r0_behavior='xdot=x²; origin semistable, not an r>0 through-transit')

    oscill=[]
    for method in ['DOP853','Verlet','Euler']:
        z=oscillator(method=method)
        oscill.append(dict(method=method,dt=z['dt'],omega_rad_per_time=1,periods=10,
            final_energy_ratio=z['final_energy_ratio'],max_relative_energy_error=z['max_relative_energy_error'],
            max_position_error=z['max_position_error']))
        ax[1,1].plot(z['time']/(2*np.pi),z['energy']/z['energy'][0],label=method)
        if method!='Verlet':ax[1,2].plot(*z['state'],label=method,lw=1)
        allcurves['oscillator_'+method]=np.vstack([z['time'],z['state'],z['energy']])
    ax[1,1].set(title='5. Oscillator energy: method matters',xlabel='Number of periods',ylabel='Energy / initial energy')
    ax[1,1].legend(fontsize=8)
    ax[1,2].set(title='5. Euler produces a false outward spiral',xlabel='Position x',ylabel='Velocity v',aspect='equal')
    ax[1,2].legend(fontsize=8)
    refine=[]
    for step in [.04,.02,.01]:
        z=oscillator(method='Verlet',step=step)
        refine.append(dict(dt=z['dt'],max_position_error=z['max_position_error'],max_relative_energy_error=z['max_relative_energy_error']))
    data['cases']['harmonic_oscillator']=dict(runs=oscill,verlet_refinement=refine,
        exact_invariant='v²+ω²x²',motion='Clockwise closed ellipses in position-velocity space. Not real-space pair repulsion.')
    fig.suptitle('Five screenshot equations: numerical tests against exact predictions',fontsize=16)
    fig.savefig(HERE/'five_equations.png',bbox_inches='tight')
    fig.savefig(HERE/'five_equations.svg',bbox_inches='tight')
    plt.close(fig)

    data['elapsed_seconds']=time.perf_counter()-start
    (HERE/'results.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    np.savez_compressed(HERE/'trajectories.npz',**allcurves)
    log=(HERE/'test_log.txt').read_text(encoding='utf-8-sig')
    tests_ok='Ran 20 tests' in log and log.rstrip().endswith('OK')
    assert tests_ok,'Run the supplied verification suite before producing the report.'
    combined_log=(HERE/'combined_test_log.txt').read_text(encoding='utf-8-sig')
    assert 'Ran 8 tests' in combined_log and combined_log.rstrip().endswith('OK')
    report(data)
    files=sorted(p for p in HERE.iterdir() if p.is_file() and p.suffix!='.zip' and p.name!='manifest.json')
    (HERE/'manifest.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2))
    with zipfile.ZipFile(HERE/'equation_tests.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files+[HERE/'manifest.json']:z.write(p,arcname='equation_tests/'+p.name)
    print(json.dumps(data,indent=2))


def report(data):
    c=data['cases'];j=c['junction'];osc=c['harmonic_oscillator']['runs'];snd=c['saddle_node']['runs']
    def table(heads,rows):
        return '<div class="scroll"><table><tr>'+''.join('<th>'+html.escape(h)+'</th>' for h in heads)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</table></div>'
    b64=base64.b64encode((HERE/'five_equations.png').read_bytes()).decode()
    combined=json.loads((HERE/'combined_results.json').read_text(encoding='utf-8'))
    cr={r['case']:r for r in combined['runs']};ref=combined['refinement']
    cb64=base64.b64encode((HERE/'combined_transport.png').read_bytes()).decode()
    uptake=cr['combined']['final_aqueous_percent']
    mixing_change=100*(1-cr['combined']['gas_variance'][0]/cr['no_flow']['gas_variance'][0])
    all_mass=max(r['max_relative_mass_residual'] for r in list(cr.values())+[ref['coarse_24'],ref['fine_96'],combined['no_uptake_control']])
    body=f'''<p><a href="../README.md">Substance interaction study</a> · <a href="README.md">This supplement</a> · <a href="../../mechanisms-switching-memory/README.md">Switching and memory</a></p><h1>Five equations, tested together</h1>
    <p class="sub">Supplement to the NousVolition / My-Sources-Project-ALL study</p>
    <p class="lead">Yes: all five can be tested together when their connection is defined. Completed: 20 mathematical checks, 8 coupled-model checks, and 12 transport runs. All 28 checks passed. The shared simulation uses the five equations to control an imposed flow carrying CO, acetone and hydrogen peroxide through fog.</p>
    <p>This is an explicitly constructed numerical benchmark. The chosen flow connections have not been measured in a real apparatus. They test whether the equations and transport accounting work consistently together; they do not establish that clock, circuit or oscillator equations determine molecular reactions. Images 4 and 5 are cropped; their equations are reconstructed from the visible terms and diagram.</p>
    <h2>The completed combined test</h2>
    <p>The domain is a periodic 1 m × 1 m layer of depth 1 m, at 25°C and 101,325 Pa. It contains a fixed, uniformly distributed fog-water volume of 0.5 mL (about 0.5 g) per cubic metre of air, with 10 µm droplet radius and imposed 100% relative humidity. Initial mean wet-gas concentrations are CO 1 ppm, acetone 1 ppm and H₂O₂ 0.001 ppm. Each initially has the spatial profile C/C₀=1+½cos(2πx/L)cos(2πy/L). Liquid starts solute-free. The simulation lasts 180 seconds.</p>
    <p>The carrier velocity is uₓ=Aₓ(t)sin(2πy/L), uᵧ=Aᵧ(t)sin(2πx/L). Its divergence is zero. Every screenshot contributes an explicitly bounded signal to the amplitudes:</p>
    <div class="eq">Aₓ=0.01[1+0.2h<sub>cycle</sub>+0.2h<sub>clock</sub>] m/s<br>Aᵧ=0.01[0.6+0.2h<sub>junction</sub>+0.1h<sub>oscillator</sub>+0.1h<sub>gate</sub>] m/s</div>
    {table(['Screenshot','Connection used in this constructed benchmark'],[
        ['1. Limit cycle','h = r(t/30 s) cos(t/30 s), with r₀=0.2'],
        ['2. Junction / pendulum','h = sinφ; φ″+0.2φ′+sinφ=1.2, φ(0)=φ′(0)=0; normalized time t/(30 s)'],
        ['3. Clock','h = cos[2πt/(43,200/11 s)]; actual relative-hand period 3,927.27 s'],
        ['4. Saddle-node scaling','dx/dt=(0.01+x²)/(3 s), x(0)=−1; h=(x+1)/2, held at 1 after x reaches +1'],
        ['5. Harmonic oscillator','h = cos[t/(30 s)], with initial displacement 1 and initial velocity 0']])}
    <p>The saddle-node gate reaches full output at {cr['combined']['gate_full_activation_s']:.8f} s, matching its exact finite-cutoff transit. The clock varies slowly over this 180 s window. These amplitude gains and time mappings are scenario choices, not extracted physical couplings. In particular, the junction controller uses a chosen 30 s signal scale; this is not the nanosecond dynamics of the illustrative physical junction tested separately below. Coupling is one-way: concentrations do not feed back onto the controllers.</p>
    <figure><img src="data:image/png;base64,{cb64}" alt="Computed CO concentration fields for diffusion alone, steady flow and all five controllers"><figcaption>Completed 48×48 calculations at 180 s, on the same concentration scale. Patterns show redistribution and diffusion, not conversion of CO into another molecule.</figcaption></figure>
    {table(['Run','CO gas variance (ppm²)','Aqueous CO (% of initial CO)','Mass residual (relative)'],[[r['case'],f"{r['gas_variance'][0]:.8f}",f"{r['final_aqueous_percent'][0]:.8g}",f"{r['max_relative_mass_residual']:.3g}"] for r in combined['runs']])}
    <p>At 48×48 resolution, the all-five flow has {mixing_change:.2f}% less CO concentration variance than diffusion alone at 180 s. Lower variance means a more uniform concentration. This comparison is specific to the chosen flows; their amplitudes and energy inputs are not matched. Removing one controller sometimes improves mixing. The result does not prove that using more controllers is inherently better.</p>
    <p>Global aqueous fractions at 180 s are <strong>CO {uptake[0]:.8g}%, acetone {uptake[1]:.8g}%, and H₂O₂ {uptake[2]:.8g}%</strong>. They are identical across the flow cases to numerical precision. This follows from the fixed water inventory and uniform linear transfer coefficients: integration over the closed periodic domain cancels the transport fluxes. It is a conservation-law consequence of the selected model, not evidence that flow never affects dissolution in nature. No-uptake controls retain zero liquid solute.</p>
    <h2>What supplies the substance physics</h2>
    <p>Define G as gas solute moles per gas volume, and Q as fog-liquid solute moles per gas volume. Actual liquid concentration is Q/ε with ε=5×10⁻⁷. For each solute m=H<sup>cp</sup>RT. The two-phase equations are</p>
    <div class="eq">∂G/∂t + ∇·(uG) = D<sub>g</sub>∇²G − J<br>∂Q/∂t + ∇·(uQ) = J<br>J = k<sub>L</sub>a (εmG − Q).</div>
    <p>Local exchange is integrated exactly and conserves G+Q. Its equilibrium aqueous fraction is εm/(1+εm). Gas diffusivity D<sub>g</sub>=2×10⁻⁵ m²/s and liquid diffusivity D<sub>l</sub>=2×10⁻⁹ m²/s are shared illustrative values, not separately fitted species measurements. For droplet radius a=10⁻⁵ m, k<sub>l</sub>=D<sub>l</sub>/a, k<sub>g</sub>=D<sub>g</sub>/a, K<sub>L</sub>=[1/k<sub>l</sub>+m/k<sub>g</sub>]<sup>−1</sup>, and the liquid-volume transfer coefficient k<sub>L</sub>a=3K<sub>L</sub>/a, in s⁻¹. Here the conventional symbol k<sub>L</sub>a denotes a volumetric coefficient; it is not k<sub>l</sub> times the droplet radius.</p>
    <p>The literature Henry coefficients at 298.15 K are H<sup>cp</sup>=9.7×10⁻⁶ for <a href="https://henrys-law.org/henry/casrn/630-08-0">CO</a>, 0.27 for <a href="https://henrys-law.org/henry/casrn/67-64-1">acetone</a>, and 860 for <a href="https://henrys-law.org/henry/casrn/7722-84-1">H₂O₂</a>, all in mol m⁻³ Pa⁻¹. Source: <a href="https://doi.org/10.5194/acp-23-10901-2023">Sander’s 2023 Henry-law compilation</a>, selected review entries documented in references.json. These encode species-specific partitioning; molecular mass alone does not set the answer.</p>
    <p>The transfer model contains no chemical reaction term. “Zero conversion” is therefore an explicit control assumption, not a new experimental finding that reactions can never occur. There is no OH radical, light-driven chemistry or catalyst here. In particular, mixing CO with water does not get an invented CO→CO₂ term. CO₂ is a different species, and its dissolution and acid–base equilibrium remain in the broader substance study. H₂O₂ is used here solely as a soluble tracer; catalytic decomposition needs a specified catalyst and validated kinetics.</p>
    <p>Fog liquid co-moves horizontally with the air; settling, evaporation, droplet growth, heat balance and solute feedback are excluded. There are no charged particles in this combined supplement, hence no modeled electrical attraction or repulsion. Ice, smoke collection, surface adsorption and Coulomb/Brownian interaction retain their separate models in the broader study. This supplement does not pretend to couple all of them using the five screenshots.</p>
    <h2>Numerical verification and limits</h2>
    <p>Transport uses conservative finite-volume MUSCL fluxes with a monotonized-central slope limiter, centered diffusion, a three-stage strong-stability-preserving time integrator, and exact exchange in a split update. Initial conditions are exact cell averages of the same continuous field. The main grid is 48×48 with Δt=0.25 s. An explicit positivity timestep bound is enforced; concentrations stayed nonnegative. The maximum relative species inventory residual across reported cases and grids is {all_mass:.3g}. No chemical mass is silently lost.</p>
    {table(['Refinement check','Completed numerical result'],[
        ['24² → 48² CO-field RMS difference (ppm)',f"{ref['CO_rms_24_vs_restricted48']:.8g}"],
        ['48² → 96² CO-field RMS difference (ppm)',f"{ref['CO_rms_48_vs_restricted96']:.8g}"],
        ['Δt 0.25 → 0.125 s at 48², CO RMS difference (ppm)',f"{ref['CO_rms_dt025_vs_dt0125']:.8g}"],
        ['CO variance at 24² / 48² / 96² (ppm²)',f"{ref['coarse_24']['gas_variance'][0]:.8f} / {cr['combined']['gas_variance'][0]:.8f} / {ref['fine_96']['gas_variance'][0]:.8f}"]])}
    <p>Fine fields are averaged onto the coarser grid before comparison. The spatial differences decrease by a factor of {ref['CO_rms_24_vs_restricted48']/ref['CO_rms_48_vs_restricted96']:.2f}; this supports convergence but is not an experimental accuracy certificate or an analytic error bound. The 48² variance differs from the 96² result by {100*abs(cr['combined']['gas_variance'][0]/ref['fine_96']['gas_variance'][0]-1):.2f}%, so fine mixing-rate claims beyond that level are not justified. The diffusion-only control is also checked against exact Fourier-mode decay. All eight coupled tests and all twenty independent equation tests pass. The physical model is deterministic; its single randomized conservation test uses fixed seed 123. Statistical repeated-seed sampling is not needed for this supplement.</p>
    <h2>Why the five equations cannot simply be identified with one another</h2>
    <p>They evolve different quantities: radius and angle, superconducting phase and voltage, clock-hand angles, a bifurcation coordinate, and position plus velocity. Equal-looking symbols do not give them equal units or mechanisms. They can coexist in a larger simulation through a specified controller, boundary condition or force law. They cannot replace the missing chemical constants, surface properties or forces just because their plots show circles, attraction or separation. Quantum bonding determines chemical identity; continuum flow and species equations describe transport at much larger scales. No new Navier–Stokes law is proposed.</p>
    <h2>Independent checks of each screenshot</h2>
    <figure><img src="data:image/png;base64,{b64}" alt="Five systems compared with exact mathematical predictions"><figcaption>Actual numerical output. The overlapping curves in panel 4 are the expected scaling collapse. The outward Euler spiral in panel 6 is a numerical error.</figcaption></figure>
    <h2>1. A stable unit-circle orbit, with an exception</h2>
    <div class="eq">θ̇ = 1, &nbsp; ṙ = (1 − r²)r</div>
    <p>For r₀ ≥ 0, a version of the exact solution that also handles the origin is</p>
    <div class="eq">r(t) = r₀ / √[r₀² + (1 − r₀²)e<sup>−2t</sup>], &nbsp; θ(t) = θ₀ + t.</div>
    <p>At r₀ = 0 the Cartesian state remains (0,0), and a polar angle is not physically defined there. For every r₀ &gt; 0, the radius tends to 1. At r₀ = 1, it is already a periodic orbit with period 2π. For 0 &lt; r₀ &lt; 1, the path spirals outward; for r₀ &gt; 1, inward. “Every radius approaches 1” needs the r₀ &gt; 0 condition.</p>
    <p>The screenshot’s logarithmic integration uses √(1−r²), which is real only inside the circle. The corresponding antiderivative on either side is ln r − ½ ln|1−r²|. Equilibria r=0 and r=1 must be handled separately when variables are separated. The final flow formula is nevertheless valid for all nonnegative radii at forward times.</p>
    <p>For r₀&gt;1, backward flow has a finite blow-up boundary. At r₀=2, the real solution requires t&gt;{c['limit_cycle']['r0_2_backward_blowup_time']:.9f}. The origin and unit circle are treated separately in the tests. Radial perturbations near the cycle shrink by e<sup>−4π</sup>≈{c['limit_cycle']['radial_floquet_multiplier']:.8g} per revolution; angular phase offsets do not decay.</p>
    {table(['Initial radius','Radius at t=10','Maximum Cartesian error'],[[r['initial_radius'],f"{r['final_radius_t10']:.9g}",f"{r['max_cartesian_error']:.3g}"] for r in c['limit_cycle']['results']])}
    <h2>2. The Josephson-junction / pendulum analogy works after scaling</h2>
    <div class="eq">C V̇ + V/R + I<sub>c</sub> sinφ = I, &nbsp; V = ℏφ̇/(2e)</div>
    <p>Substitution gives (ℏC/2e)φ̈ + (ℏ/2eR)φ̇ + I<sub>c</sub>sinφ = I. Set ω<sub>p</sub>=√(2eI<sub>c</sub>/ℏC), τ=ω<sub>p</sub>t, α=1/(RCω<sub>p</sub>), and i=I/I<sub>c</sub>:</p>
    <div class="eq">d²φ/dτ² + α dφ/dτ + sinφ = i.</div>
    <p>A pendulum with constant torque has the same normalized equation. Its inertia is mL², not merely m when length varies. This is an analogy of equations after the coefficients and units are matched. A superconducting phase difference is not a literal pendulum angle, and voltage requires the factor ℏ/(2e).</p>
    <p>The example uses I<sub>c</sub>=1 µA, C=1 pF and α=0.2, which implies R={j['parameters']['R_ohm']:.6f} Ω and ω<sub>p</sub>={j['parameters']['omega_p_rad_s']:.6g} rad/s. Direct dimensional circuit integration agrees with the normalized equation. At i=0.5 the resting initial condition locks at φ=arcsin(0.5)=π/6. A sufficiently rotating initial condition keeps running at that same bias. This illustrates bistability for these selected underdamped parameters, not universal behavior for every circuit.</p>
    {table(['Case','i','Initial dφ/dτ','Mean dφ/dτ over last 50','Mean voltage (µV)'],[[r['case'],r['i'],r['initial_dimensionless_rate'],f"{r['mean_rate_last50']:.9g}",f"{r['mean_voltage_last50_V']*1e6:.6g}"] for r in j['runs']])}
    <p>The tracked tilted energy is H=½φ′²+1−cosφ−iφ. Its balance H′=−αφ′² is checked against an independently integrated dissipation accumulator. The maximum absolute balance error over the examples is {max(r['max_tilted_energy_balance_error'] for r in j['runs']):.3g}. A running solution may have decreasing tilted energy while the current source supplies physical energy.</p>
    <p>In the separate C=0 overdamped limit, using s=(2eRI<sub>c</sub>/ℏ)t, the rotating period for i&gt;1 is 2π/√(i²−1), and mean voltage is R√(I²−I<sub>c</sub>²). This is not the finite-capacitance running-state formula.</p>
    {table(['i','Numerical overdamped period','Exact period','Relative error'],[[r['i'],f"{r['numeric_period']:.10f}",f"{r['analytic_period']:.10f}",f"{r['relative_error']:.3g}"] for r in j['overdamped_limit']])}
    <h2>3. Clock alignment: 1:05:27.2727…</h2>
    <p>The minute hand moves at 6°/min and the hour hand at 0.5°/min. Their relative angular speed is 5.5°/min. The next same-direction coincidence satisfies 5.5t=360, so t=720/11 minutes: <strong>65 minutes and 27.2727… seconds after noon</strong>. Integration of the two angular motions gives {c['clock']['numeric_minutes']:.12f} minutes, an error of {c['clock']['absolute_error_minutes']:.3g} minutes.</p>
    <p>An alternative derivation sets the minute-hand angle equal to one full turn plus the hour-hand angle: 6t=360+0.5t. “Aligned” here means pointing in the same direction. If merely being on the same straight line, pointing oppositely, also counts, the first such event is 360/11 minutes after noon, at 12:32:43.6363… .</p>
    <h2>4. Saddle-node scaling: a=½, b=−½</h2>
    <div class="eq">ẋ = r+x²; &nbsp; x=r<sup>a</sup>u, &nbsp; t=r<sup>b</sup>τ.</div>
    <p>The visible rescaling yields r<sup>a−b</sup>du/dτ = r+r<sup>2a</sup>u². Balancing all exponents requires a−b=1=2a. Thus a=½ and b=−½. For r&gt;0, u=x/√r and τ=√r t reduce the equation to du/dτ=1+u². The scaled trajectories collapse onto u(τ)=tan(τ−arctan2) for the chosen initial u=−2.</p>
    <p>The exact transit time from x=−1 to +1 is T(r)=2 arctan(1/√r)/√r. The asymptotic π/√r applies when r is small relative to the squared cutoff. It is not an exact formula for a finite cutoff.</p>
    {table(['r','Numerical transit','Exact finite-cutoff transit','π/√r asymptote'],[[r['r'],f"{r['transit_from_minus1_to_plus1']:.8f}",f"{r['analytic_transit']:.8f}",f"{r['asymptotic_pi_over_sqrt_r']:.8f}"] for r in snd])}
    <p>At r=0, the origin is semistable. For r&lt;0, the real equilibria are ±√(−r), with the negative one stable and positive one unstable. The real r&gt;0 square-root substitution cannot be applied unchanged to negative r. The parameter r in this example is distinct from the polar radius in Image 1.</p>
    <h2>5. Harmonic-oscillator ellipses; a false spiral from Euler</h2>
    <p>From the visible vector components (v,0) and (0,−ω²x), the fifth image is interpreted as ẋ=v, v̇=−ω²x. Its exact invariant is v²+ω²x². Trajectories are clockwise closed ellipses in the position–velocity plane, with period 2π/ω. Position and velocity are not two spatial coordinates of interacting droplets.</p>
    <p>Tests use ω=1, x₀=1, v₀=0 over ten periods. For forward Euler, each step multiplies energy by exactly 1+ω²Δt², so the numerical trajectory spirals outward despite the physical equation conserving energy. Velocity Verlet has bounded energy oscillation and converges at second order; the adaptive high-order solver agrees with the exact sinusoid.</p>
    {table(['Method','Final energy / initial','Maximum relative energy error','Maximum x error'],[[r['method'],f"{r['final_energy_ratio']:.10g}",f"{r['max_relative_energy_error']:.3g}",f"{r['max_position_error']:.3g}"] for r in osc])}
    <h2>How this relates to the substance study</h2>
    <p>A stable circle in a state-space plot does not by itself demonstrate molecular attraction or repulsion. Image 1 specifies a vector field; if interpreted as a planar fluid velocity it has divergence 2−4(x²+y²), so it is not an incompressible 2D carrier flow. A compressible interpretation would require its own density and boundary conditions. Image 2 is an equation-level analogy. Image 3 has relative motion without any hand-to-hand force. Image 4 describes a local dynamical bottleneck. Image 5 is a restoring-force oscillator, and its Euler spiral demonstrates why numerical refinement matters.</p>
    <p>The combined test above supplies explicit state variables, units, conservation balances and assumed flow connections. None of the screenshots itself supplies a chemical reaction rate or a Coulomb force law. A model intended to predict a particular apparatus would additionally require measured forcing, calibrated coefficients and validation against data.</p>
    <h2>Reproduce</h2>
    <p>See <a href="README.txt">README.txt</a>. The package includes Python scripts, all 28 tests, completed JSON results, saved field and trajectory arrays, PNG/SVG figures, verification logs, references and a SHA256 manifest. Run combined_transport.py before run_examples.py. Results are numerical calculations, not laboratory measurements. Some source context is missing from the cropped screenshots; tests verify these explicit interpretations, not unseen portions of the pages.</p>'''
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Five screenshot equations tested</title><style>
    body{margin:0;background:#f1f4f8;color:#1d2b40;font:16px/1.7 system-ui,Segoe UI,sans-serif}main{max-width:1180px;padding:44px 32px;margin:auto;background:white}h1{font-size:44px;line-height:1.2}h2{margin-top:40px;padding-top:20px;border-top:1px solid #d4dce8;font-size:25px}.lead{font-size:21px}.sub,figcaption{color:#536379;font-size:14px}.eq{padding:15px 22px;background:#f1f4fa;border-left:3px solid #456bac;font:19px/1.8 Georgia,serif}figure{margin:28px 0}img{width:100%;height:auto}a{color:#265bb6}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px}th{text-align:left;padding:10px;background:#edf2f9}td{padding:10px;border-bottom:1px solid #d8dfe9}p{max-width:1050px}@media(max-width:700px){main{padding:24px 15px}h1{font-size:32px}}
    </style></head><body><main>'''+body+'</main></body></html>'
    (HERE/'report.html').write_text(page,encoding='utf-8')


if __name__=='__main__':main()
