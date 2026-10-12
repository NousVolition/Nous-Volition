"""Reproduce the complete switching supplement, including its verification log."""
import base64
import hashlib
import html
import io
import json
import platform
import unittest
import zipfile
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
    log=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(ROOT),pattern='test_models.py')
    verified=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    (ROOT/'test_log.txt').write_text(log.getvalue(),encoding='utf-8')
    if not verified.wasSuccessful():raise RuntimeError(log.getvalue())
    print(f'{verified.testsRun} verification tests passed.',flush=True)
    data=dict(scope='Ideal spring mechanics and an explicitly uncalibrated biochemical feedback hypothesis',
              verification_tests=verified.testsRun,
              versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__))
    arrays={};fig,ax=plt.subplots(2,3,figsize=(16,9),layout='constrained')
    seconds=SPRING['gamma_N_s_m']/SPRING['k_N_m'];mm=SPRING['a_m']*1000
    energy=SPRING['k_N_m']*SPRING['a_m']**2
    tc=spring_critical_pulse();yf,bf=spring_folds()
    spring=dict(parameters=SPRING,lambda_=2.,time_unit_s=seconds,energy_unit_J=energy,
                neglected_inertia_ratio=SPRING['mass_kg']*SPRING['k_N_m']/SPRING['gamma_N_s_m']**2,
                stable_rest_positions_mm=[-np.sqrt(3)*mm,np.sqrt(3)*mm],
                quasistatic_fold_bias=bf,fold_tilt_deg=np.degrees(np.arcsin(bf*SPRING['k_N_m']*SPRING['a_m']/(SPRING['mass_kg']*SPRING['g_m_s2']))),
                pulse_bias=.8,pulse_tilt_deg=np.degrees(np.arcsin(.8*SPRING['k_N_m']*SPRING['a_m']/(SPRING['mass_kg']*SPRING['g_m_s2']))),
                critical_pulse_tau=tc,critical_pulse_s=tc*seconds,pulses=[],ramps=[],geometry_sensitivity=[])
    y=np.linspace(-2.6,2.6,400)
    for lam,col in [(2.,'#ba5727'),(.8,'#18776c')]:
        ax[0,0].plot(y*mm,spring_potential(y,0,lam)*energy*1000,color=col,label=f'L₀/a={lam:g}')
    ax[0,0].set(title='Spring geometry creates two resting positions',xlabel='Bead position (mm)',ylabel='Potential energy (mJ)');ax[0,0].legend()
    for duration,col in [(40.,'#e9b18b'),(160.,'#ba5727'),(640.,'#773517')]:
        t,z,b,sw,res=spring_ramp(duration)
        ax[0,1].plot(b,z[0]*mm,label=f'{duration*seconds:g} s per ramp',color=col,lw=1.2)
        arrays[f'spring_ramp_{int(duration)}']=np.vstack([t*seconds,z,b])
        spring['ramps'].append(dict(half_duration_tau=duration,half_duration_s=duration*seconds,
                                   zero_crossing_biases=sw,max_energy_residual_J=res*energy))
    for sign in [-1,1]:ax[0,1].axvline(sign*bf,color='#777',ls=':',lw=1)
    ax[0,1].set(title='Changing tilt: hysteresis and rate delay',xlabel='Tilt force / (k a)',ylabel='Bead position (mm)');ax[0,1].legend(fontsize=8)
    for factor,lam,label,col,ls in [(.8,2.,'Short pulse','#61778d','-'),(1.2,2.,'Long pulse','#ba5727','-'),(1.2,.8,'Uncompressed control','#18776c','--')]:
        t,z,b,res=spring_pulse(tc*factor,lam=lam)
        ax[0,2].plot(t*seconds,z[0]*mm,color=col,label=label,ls=ls)
        ax[0,2].scatter(tc*factor*seconds,z[0,800]*mm,color=col,s=22)
        arrays[f'spring_pulse_{label.replace(" ","_")}']=np.vstack([t*seconds,z,b])
        spring['pulses'].append(dict(label=label,lambda_=lam,pulse_s=tc*factor*seconds,
                                     end_s=t[-1]*seconds,final_position_mm=z[0,-1]*mm,
                                     heat_J=z[1,-1]*energy,parameter_work_J=z[2,-1]*energy,
                                     max_energy_residual_J=res*energy))
    ax[0,2].set(title='After the pulse: return or switch',xlabel='Time (s)',ylabel='Bead position (mm)',xlim=(0,45));ax[0,2].legend(fontsize=8)
    for lam in [.8,1.,1.2,1.5,2.,2.5]:
        fold=spring_folds(lam)
        spring['geometry_sensitivity'].append(dict(lambda_=lam,positive_fold_bias=None if fold is None else fold[1],
                                                   stable_states_at_zero_bias=2 if lam>1 else 1))
    data['spring']=spring
    print('Spring pulses, work balance and three ramp speeds completed.',flush=True)

    roots=chemical_roots();ct=chemical_critical_pulse()
    chem=dict(parameters_assumed=CHEM,stimulus_during_pulse_s_inv=.5,total_protein_uM=1.,
              roots_at_zero_stimulus=roots,root_slopes_s_inv=[chemical_slope(p) for p in roots],
              critical_pulse_s=ct,pulses=[],sensitivity=[])
    p=np.linspace(0,1,500)
    for v,label,col in [(2.,'Cooperative feedback','#ba5727'),(0.,'No feedback','#18776c')]:
        up,down=rates(p,v=v)
        ax[1,0].plot(p,up-down,color=col,label=label)
    ax[1,0].axhline(0,color='#777',lw=.7);ax[1,0].scatter(roots,[0]*3,color=['#18776c','#ba5727','#18776c'],zorder=5)
    ax[1,0].set(title='Chemical hypothesis: two stable active fractions',xlabel='Active protein fraction p',ylabel='dp/dt (s⁻¹)',ylim=(-.6,.4));ax[1,0].legend(fontsize=8)
    for factor,mode,label,col,ls in [(.8,'feedback','Short pulse','#61778d','-'),(1.2,'feedback','Long pulse','#ba5727','-'),(1.2,'no_feedback','No feedback','#18776c','--'),(1.2,'fuel_off','Fuel off after pulse','#9365a5',':')]:
        t,z=chemical_pulse(ct*factor,mode=mode)
        arrays[f'chemical_{mode}_{factor}']=np.vstack([t,z])
        ax[1,1].plot(t,z[0],label=label,color=col,ls=ls,lw=1.8)
        ax[1,1].scatter(ct*factor,z[0,800],color=col,s=18)
        chem['pulses'].append(dict(label=label,mode=mode,pulse_s=ct*factor,end_s=t[-1],
                                   fraction_at_pulse_end=z[0,800],final_fraction=z[0,-1],
                                   ATP_consumed_uM=z[1,-1],Pi_released_uM=z[2,-1],
                                   max_conversion_balance_residual_uM=float(np.max(np.abs(z[0]-z[1]+z[2])))))
    ax[1,1].set(title='Feedback can maintain a pulse response',xlabel='Time (s, assumed kinetic scale)',ylabel='Active protein fraction',xlim=(0,12));ax[1,1].legend(fontsize=8)
    t,z=finite_fuel();pp,ATP,ADP,Pi=z
    arrays['finite_ATP']=np.vstack([t,z])
    ax[1,2].plot(t,pp,label='Active protein (µM)',color='#ba5727')
    ax[1,2].plot(t,ATP,label='ATP (µM)',color='#18776c')
    ax[1,2].plot(t,Pi,label='Released phosphate (µM)',color='#61778d',ls='--')
    ax[1,2].set(title='A finite fuel supply loses its active state',xlabel='Time (s, assumed kinetic scale)',ylabel='Concentration (µM)',xlim=(0,15));ax[1,2].legend(fontsize=8)
    chem['finite_ATP']=dict(initial_ATP_uM=2.,KmATP_uM=.1,initial_active_fraction=pp[0],end_s=t[-1],
                            final_active_fraction=pp[-1],final_ATP_uM=ATP[-1],
                            max_adenylate_residual_uM=float(np.max(np.abs(ATP+ADP-2))),
                            max_phosphate_residual_uM=float(np.max(np.abs(3*ATP+2*ADP+Pi+pp-(6+pp[0])))))
    for key,values in [('v',[.5,1.,1.5,2.,3.]),('K',[.2,.3,.4]),('n',[1,2,4,8]),('d',[.5,1.,2.])]:
        for val in values:
            rr=chemical_roots(**{key:val})
            critical=chemical_critical_pulse(**{key:val})
            chem['sensitivity'].append(dict(changed_parameter=key,value=val,roots=rr,
                                            stable_roots=[p for p in rr if chemical_slope(p,**(CHEM|{key:val}))<0],
                                            critical_pulse_s=None if not np.isfinite(critical) else critical))
    data['chemical_hypothesis']=chem
    fig.suptitle('Two mechanisms for switching and memory — computed, conditional examples',fontsize=17)
    fig.savefig(ROOT/'mechanisms.png',dpi=170,bbox_inches='tight');fig.savefig(ROOT/'mechanisms.svg',bbox_inches='tight');plt.close(fig)
    print('Chemical pulses, finite fuel and parameter sensitivity completed.',flush=True)

    # The numerical method is checked at a transient time, not only at a final
    # stable state where all approximate trajectories could hide earlier error.
    refinement=[]
    for kind,hs,duration,post,initial in [('spring',[.4,.2,.1],tc*1.1,0.,[-np.sqrt(3)]),('chemical',[.05,.025,.0125],ct*1.1,1.,[0.])]:
        if kind=='spring':
            f1=lambda z:spring_force(z,.8);f2=lambda z:spring_force(z)
            ref=integrate(lambda t,z:f1(z),initial,duration)[1][0,-1]
        else:
            def cf(s):return lambda z:rates(z,s)[0]-rates(z,s)[1]
            f1,f2=cf(.5),cf(0.);ref=chemical_pulse(duration,post=post)[1][0,-1]
        for h in hs:
            result=rk4_piecewise(f1,f2,initial,duration,post,h)[0]
            refinement.append(dict(model=kind,max_step=h,comparison_time=duration+post,
                                   reference=ref,value=result,absolute_state_error=abs(result-ref)))
    data['fixed_step_refinement']=refinement

    samples=[];ensemble=[];trials=24
    for N in [100,1000]:
        for condition,factor in enumerate([.8,1.,1.2]):
            passed=0
            for seed in range(trials):
                row=gillespie(N,[N,condition,seed],ct*factor)
                high=row['final_active_count']/N>roots[1];passed+=int(high)
                samples.append(dict(N=N,seed_entropy=[N,condition,seed],pulse_factor=factor,
                                    mode='feedback',in_high_basin_at_end=bool(high),**row))
            ensemble.append(dict(N=N,pulse_factor=factor,mode='feedback',successes=passed,trials=trials,
                                 fraction=passed/trials,wilson95=wilson(passed,trials)))
    passed=0
    for seed in range(trials):
        row=gillespie(1000,[1000,3,seed],ct*1.2,v=0.)
        high=row['final_active_count']/1000>roots[1];passed+=int(high)
        samples.append(dict(N=1000,seed_entropy=[1000,3,seed],pulse_factor=1.2,
                            mode='no_feedback',in_high_basin_at_end=bool(high),**row))
    ensemble.append(dict(N=1000,pulse_factor=1.2,mode='no_feedback',successes=passed,trials=trials,
                         fraction=passed/trials,wilson95=wilson(passed,trials)))
    data['stochastic']=dict(method='Exact Gillespie jumps of a phenomenological Hill process',
                            post_pulse_s=20.,high_basin_boundary=roots[1],runs=len(samples),
                            seeds_per_condition=trials,ensemble=ensemble,individual_runs=samples)
    print(f'{len(samples)} seeded jump simulations completed.',flush=True)

    fig,ax=plt.subplots(1,3,figsize=(16,4.5),layout='constrained')
    for N,offset,col in [(100,-.012,'#ba5727'),(1000,.012,'#18776c')]:
        rr=[r for r in ensemble if r['N']==N and r['mode']=='feedback']
        x=np.array([r['pulse_factor'] for r in rr]);y=np.array([r['fraction'] for r in rr])
        lo=np.array([r['wilson95'][0] for r in rr]);hi=np.array([r['wilson95'][1] for r in rr])
        ax[0].errorbar(x+offset,y,yerr=np.vstack([y-lo,hi-y]),color=col,marker='o',capsize=4,label=f'N={N}, 24 seeds')
    ax[0].set(title='Finite counts blur the switching threshold',xlabel='Pulse duration / deterministic threshold',ylabel='Fraction in high basin, 20 s after pulse',ylim=(-.03,1.03));ax[0].legend(fontsize=8)
    for kind,col in [('spring','#ba5727'),('chemical','#18776c')]:
        rr=[r for r in refinement if r['model']==kind]
        ax[1].loglog([r['max_step'] for r in rr],[r['absolute_state_error'] for r in rr],'o-',label=kind,color=col)
    ax[1].set(title='Independent fixed-step accuracy check',xlabel='Maximum step (τ or s as appropriate)',ylabel='Absolute dimensionless state error');ax[1].legend(fontsize=8)
    ax[1].xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax[1].set_xticks([.01,.03,.1,.3],labels=['0.01','0.03','0.1','0.3'])
    vv=np.linspace(.3,3,160)
    for v in vv:
        for p in chemical_roots(v=v):
            stable=chemical_slope(p,**(CHEM|{'v':v}))<0
            ax[2].plot(v,p,'.',ms=2.5,color='#18776c' if stable else '#ba5727')
    ax[2].plot([],[],'.',color='#18776c',label='Stable');ax[2].plot([],[],'.',color='#ba5727',label='Unstable')
    ax[2].set(title='Feedback strength changes possible states',xlabel='Assumed feedback v (s⁻¹)',ylabel='Steady active fraction p');ax[2].legend(fontsize=8)
    fig.savefig(ROOT/'verification.png',dpi=170,bbox_inches='tight');fig.savefig(ROOT/'verification.svg',bbox_inches='tight');plt.close(fig)
    np.savez_compressed(ROOT/'trajectories.npz',**arrays)
    (ROOT/'results.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    report(data)
    package()
    print(json.dumps({k:v for k,v in data.items() if k in ['verification_tests','fixed_step_refinement']},indent=2))


def table(heads,rows):
    return '<div class="scroll"><table><tr>'+''.join('<th>'+html.escape(h)+'</th>' for h in heads)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</table></div>'


def report(d):
    s=d['spring'];c=d['chemical_hypothesis'];noise=d['stochastic']
    def image(name,alt):
        encoded=base64.b64encode((ROOT/name).read_bytes()).decode()
        return '<figure><img src="data:image/png;base64,'+encoded+'" alt="'+alt+'"></figure>'
    body=f'''<h1>What can make a system switch and remember?</h1>
    <p class="sub">NousVolition / My-Sources-Project-ALL · completed computational supplement · 11 October 2026</p>
    <p class="lead">A spring can remember which side a bead reached. A feedback reaction model can remember a brief stimulus. Both effects appear in these completed calculations, but their causes and the quantities being measured differ.</p>
    <p><strong>{d['verification_tests']} verification tests passed; {noise['runs']} seeded jump simulations ran.</strong> The spring force follows the supplied textbook geometry. The chemical model is an explicit, uncalibrated hypothesis with chosen rates. It is not a fitted model of the photographed experiment, and it does not assign new reactions to CO, CO₂, water, VOCs, smoke or H₂O₂.</p>
    <p><a href="README.md">Study overview on GitHub</a> · <a href="results.json">Numerical results</a> · <a href="README.txt">Reproduction instructions</a> · <a href="../../README.md">Streams and Rocks</a></p>
    {image('mechanisms.png','Spring energy, tilt hysteresis and pulses; biochemical phase rates, pulse memory and finite fuel')}
    <h2>1. A defined physical reason for outward motion</h2>
    <p>The screenshot gives the equilibrium of a bead on a tilted wire, attached to an ideal spring whose length is √(x²+a²). Its relaxed length is L₀. Taking positive x downhill gives:</p>
    <div class="eq">F(x)=mg sinθ − kx[1−L₀/√(x²+a²)]<br>V(x)=½k[√(x²+a²)−L₀]²−mgx sinθ</div>
    <p>This ideal spring can push when compressed. At zero tilt and L₀&gt;a, it pushes a slightly displaced bead away from the center. It stops doing so when the geometry lets the spring reach its relaxed length. The two stable resting positions are ±√(L₀²−a²). This outward motion is an elastic force on one bead; it does not establish repulsion between molecules or droplets.</p>
    <p>For the chosen a=10 mm, L₀=20 mm and k=1 N/m, the resting positions are <strong>±{s['stable_rest_positions_mm'][1]:.5f} mm</strong>. Mass is 10 g and linear drag is γ=2 N·s/m. The implemented overdamped equation is γẋ=F(x), with time unit γ/k=2 s. The neglected inertia ratio mk/γ²={s['neglected_inertia_ratio']:.4f}; this selects a strong-drag approximation, not a measured apparatus. No thermal forcing, dry friction, spring buckling, tension-only string or geometric contact is included.</p>
    <p>Writing y=x/a, λ=L₀/a and b=mg sinθ/(ka), the dynamics become y′=b−y+λy/√(1+y²). For λ&gt;1, the static folds occur at |b|=(λ<sup>2/3</sup>−1)<sup>3/2</sup>. Here that is {s['quasistatic_fold_bias']:.8f}, or a tilt of ±{s['fold_tilt_deg']:.4f}°. Faster ramps switch beyond the static fold because the bead needs time to move. The recorded switch is its crossing of x=0; that is distinct from disappearance of a static equilibrium.</p>
    {table(['Time per ramp (s)','Upward zero-crossing bias','Downward zero-crossing bias','Maximum energy residual (J)'],[[f"{r['half_duration_s']:g}",f"{r['zero_crossing_biases'][0]:.7f}",f"{r['zero_crossing_biases'][1]:.7f}",f"{r['max_energy_residual_J']:.3g}"] for r in s['ramps']])}
    <p>Starting at the left resting position, apply b=0.8 (tilt {s['pulse_tilt_deg']:.4f}°), then return to zero tilt. The exact overdamped crossing time, independently computed by integrating dx/F, is <strong>{s['critical_pulse_s']:.6f} s</strong>. A shorter pulse returns left; a longer one leaves the bead on the right. An exactly threshold-length pulse ends at the unstable center and is exceptionally sensitive to perturbations.</p>
    {table(['Case','Pulse (s)','Final position (mm)','Heat lost to drag (J)','Parameter work (J)'],[[r['label'],f"{r['pulse_s']:.6f}",f"{r['final_position_mm']:.6f}",f"{r['heat_J']:.6g}",f"{r['parameter_work_J']:.6g}"] for r in s['pulses']])}
    <p>The uncompressed control uses L₀/a=0.8 and returns to x=0. All spring energies are accounted for as V+heat−parameter work=constant. Changing the tilt changes the potential: its work includes −∫y db in dimensionless units and the two instantaneous tilt changes in pulse runs. Omitting that work would falsely appear to create or destroy energy.</p>
    <h2>2. A chemical hypothesis that can be rejected or refined</h2>
    <p>Let p be the fraction of a fixed protein population in an active, phosphorylated state. We chose a bounded cooperative activation model:</p>
    <div class="eq">dp/dt = [s(t)+v pⁿ/(Kⁿ+pⁿ)](1−p) − d p<br>v=2 s⁻¹, K=0.3, n=4, d=1 s⁻¹; total protein=1 µM</div>
    <p>The activation term uses inactive protein (1−p); deactivation restores it. The interval 0≤p≤1 is invariant. These parameters are assumptions selected to test bistability, not measured enzyme constants. The Hill exponent represents an effective cooperative response, not proof of a four-molecule collision or an identified catalyst. It differs deliberately from any incomplete equation below the screenshot crop.</p>
    <p>At zero stimulus, the active fractions are <strong>0, {c['roots_at_zero_stimulus'][1]:.8f} and {c['roots_at_zero_stimulus'][2]:.8f}</strong>. The middle state is unstable; the other two are stable in this deterministic model. A pulse s=0.5 s⁻¹ starting from p=0 needs to last longer than <strong>{c['critical_pulse_s']:.8f} s</strong> to cross that boundary. The times are consequences of our assumed rates.</p>
    {table(['Case','Pulse duration (s)','Active fraction 30 s after pulse','Cumulative ATP use (µM)'],[[r['label'],f"{r['pulse_s']:.8f}",f"{r['final_fraction']:.8g}",f"{r['ATP_consumed_uM']:.8g}"] for r in c['pulses']])}
    <p>Under sustained feedback and replenished ATP, the longer pulse leaves about {100*c['roots_at_zero_stimulus'][2]:.3f}% active. With no feedback, the response decays. Stopping the ATP-dependent activation flux after the pulse also makes activity decay. At the high steady state, activation and deactivation remain nonzero and equal: about {c['roots_at_zero_stimulus'][2]:.6f} µM/s each. A constant concentration therefore does not mean that chemical events have stopped.</p>
    <p>Bookkeeping assumes P+ATP→P*+ADP and P*+H₂O→P+Pi, with buffered proton/water reservoirs and unspecified effective enzymes. P+P*=1 µM is fixed. The replenished-fuel case records ATP consumption and phosphate release, checking P*(t)−P*(0)=activations−deactivations. It does not claim complete atom/charge or heat closure for a specified enzyme chemistry. No chemical potentials or calorimetry were supplied, so this is not a thermodynamic validation.</p>
    <p>A separate finite-fuel test starts in the high state with 2 µM ATP, no replenishment, and an assumed ATP availability multiplier ATP/(0.1 µM+ATP). It falls to p={c['finite_ATP']['final_active_fraction']:.3g} after 40 s. Adenylate ATP+ADP and the phosphate count 3ATP+2ADP+Pi+P* are conserved to {max(c['finite_ATP']['max_adenylate_residual_uM'],c['finite_ATP']['max_phosphate_residual_uM']):.3g} µM. Its particular depletion time depends on this additional assumed law; it is not a measurement.</p>
    <h2>3. What connects the three screenshots</h2>
    <p>The refuge/outbreak drawing illustrates two stable states separated by an unstable branch. The supplied crop does not contain its full population equation, so no population calculation is claimed. The spring calculation independently produces the same kind of folded equilibrium surface. Near y=0, its rate is b+(λ−1)y−(λ/2)y³+O(y⁵): changing compression and bias supplies two controls for the familiar imperfect bifurcation. This is a mathematical relationship between model structures.</p>
    <p>The phosphorylation screenshot proposes a specific feedback mechanism. <a href="https://pubmed.ncbi.nlm.nih.gov/14647386/">Xiong and Ferrell (2003)</a> reported maintained kinase activity after transient stimulation in Xenopus oocytes and loss of that persistence when feedback was blocked. That supplies biological evidence for the mechanism in that system, not the numerical constants or single-variable equation used here. The paper has a 2007 corrigendum; no experimental values or figures from it were fitted. Cooperative activation/deactivation models also appear in <a href="https://doi.org/10.1103/PhysRevE.79.031902">Smolen, Baxter and Byrne (2009)</a>; our single-loop construction is not a reproduction of their full network.</p>
    <p>Thus the models can share a computational test suite and concepts such as stability, thresholds and hysteresis. Their variables remain bead position, population level and active protein fraction. No interaction between these systems has been assumed.</p>
    <h2>4. Robustness, noise and the limits of memory</h2>
    {image('verification.png','Seeded finite-count switching probabilities, timestep refinement and feedback-strength equilibria')}
    <p>An independent fixed-step fourth-order method was compared with a high-accuracy adaptive solution at transient times. Smaller steps reduce the errors below. Looking only at a final resting state would be a weaker check, because incorrect transients could still end at the same state. No spatial grid is used in these lumped models.</p>
    {table(['Model','Maximum step (τ or s)','Absolute dimensionless state error'],[[r['model'],r['max_step'],f"{r['absolute_state_error']:.7g}"] for r in d['fixed_step_refinement']])}
    <p>The {noise['runs']} jump runs conserve integer protein counts. Each condition uses 24 recorded seeds, N=100 or 1000 proteins, and the same assumed Hill rates. The table reports the fraction lying above the deterministic unstable boundary 20 s after the pulse; it is an endpoint classification, not a lifetime or a claim of permanent memory. The bars are 95% Wilson intervals for those finite trial counts. These exact jump simulations test noise in the chosen effective process, not molecular collision kinetics.</p>
    {table(['Protein count','Pulse / deterministic threshold','Feedback','High-state outcomes','95% interval'],[[r['N'],r['pulse_factor'],r['mode'],f"{r['successes']}/{r['trials']}",f"{r['wilson95'][0]:.3f}–{r['wilson95'][1]:.3f}"] for r in noise['ensemble']])}
    <p>At zero stimulus, p=0 is absorbing in the finite-count model: eventually a finite stochastic system can lose its active population. These finite runs do not determine that eventual escape time. A nonzero background activation rate would change this assumption. Sensitivity calculations vary v, K, n and d one at a time; weaker feedback or altered cooperativity can remove bistability altogether. Geometry sensitivity similarly removes the spring's two resting positions when L₀≤a. Full roots and conditional thresholds are saved in results.json; this is scenario sensitivity, not uncertainty estimated from measured parameters.</p>
    <h2>What this adds to the substance research</h2>
    <p>You can propose a mechanism first and test its consequences. These completed examples give concrete predictions: two bead positions, finite switching thresholds, persistent activity with ongoing fuel use, and loss of activity when fuel is limited. To apply such a hypothesis to one of the original substance pairs, specify the relevant force or reaction network and obtain or estimate its parameters. A useful hypothesis makes a prediction that controls or observations could disprove.</p>
    <p>The existing dissolution, transport and charged-droplet results retain their own models. Nothing here shows that CO mixed with water undergoes phosphorylation, that neutral droplets repel, or that a new Navier–Stokes law is required. The numerical findings are complete for the stated cases; experimental validation of the proposed biochemical model remains open.</p>'''
    css='body{margin:0;background:#edf2f5;color:#203247;font:16px/1.7 system-ui,Segoe UI,sans-serif}main{max-width:1220px;margin:auto;padding:40px 30px;background:white}h1{font-size:43px;line-height:1.2}h2{font-size:26px;border-top:1px solid #d3dce5;padding-top:24px;margin-top:40px}.lead{font-size:22px}.sub{font-size:14px;color:#607182}.eq{background:#eef4f6;padding:18px;border-left:4px solid #18776c;font:19px/1.8 Georgia,serif}figure{margin:25px 0}img{width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:11px;border-bottom:1px solid #d4dde4;text-align:left}th{background:#eff4f7}.scroll{overflow:auto}a{color:#195a9c}@media(max-width:700px){main{padding:22px 14px}h1{font-size:31px}}'
    (ROOT/'report.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mechanisms, switching and memory</title><style>'+css+'</style></head><body><main>'+body+'</main></body></html>',encoding='utf-8')


def package():
    files=sorted(p for p in ROOT.iterdir() if p.is_file() and p.name not in ['manifest.json','switching_tests.zip'])
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    with zipfile.ZipFile(ROOT/'switching_tests.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in files+[ROOT/'manifest.json']:archive.write(p,'switching_tests/'+p.name)


if __name__=='__main__':run()
