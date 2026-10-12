"""Plots and report section for the simulated Hug rhythm measurements."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent


def read():return json.loads((ROOT/'hug_rhythm_results.json').read_text())


def build_figures():
    d=read();cases={c['name']:c for c in d['cases']};cfg=d['protocol'];cycle=d['autonomous_cycle']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    for c in d['cases'][:3]:axes[0,0].plot(c['early_trace']['time_s'],c['early_trace']['displacement_mm'],lw=1.1,label=c['name'])
    p=d['passive'];mask=np.array(p['time_s'])<=60;axes[0,0].plot(np.array(p['time_s'])[mask],np.array(p['displacement_mm'])[mask],color='black',lw=1,ls='--',label='Feedback off')
    axes[0,0].set(title='Different starts and a passive control',xlabel='Simulation time (s)',ylabel='Displacement (mm)');axes[0,0].legend(fontsize=8,ncol=2)
    o=cases['No orbit']['observation'];t=np.array(o['time_s']);mask=t>t[-1]-12
    axes[0,1].plot(t[mask]-t[-1]+12,np.array(o['predicted_displacement_mm'])[mask],color='#df783c',lw=1.8,label='Prediction from fixed calibration')
    axes[0,1].plot(t[mask]-t[-1]+12,np.array(o['measured_displacement_mm'])[mask],'.',color='#236783',ms=2,label='Simulated sensor readings')
    axes[0,1].set(title=f"Late rhythm: {cycle['period_s']:.6f} s per cycle",xlabel='Time in a late 12-second window (s)',ylabel='Displacement (mm)');axes[0,1].legend(fontsize=8)
    z=np.array(cycle['cycle_state_scaled']);axes[1,0].plot(z[:,0]*.1,z[:,1]*.1,color='#236783')
    axes[1,0].set(title='Full-state periodic orbit checked separately',xlabel='Displacement (mm)',ylabel='Velocity (mm/s)')
    k=d['disturbance'];axes[1,1].semilogy(k['crossing_time_s'],np.maximum(k['section_distance_scaled'],1e-14),color='#236783');axes[1,1].axhline(cfg['gates']['section_recovery_error_scaled'],ls='--',color='#df783c',label='Declared return tolerance')
    axes[1,1].set(title='Return after a disturbance',xlabel='Time after disturbance (s)',ylabel='Distance from the cycle at matching phase');axes[1,1].legend(fontsize=8)
    fig.suptitle('Hug rhythm without an orbit — simulated measurements',fontsize=17)
    fig.savefig(ROOT/'figures/hug_rhythm_autonomous.png',dpi=165);plt.close(fig)
    names=['No orbit','Circular','Pasiphae','Elara','Himalia','Europa','Callisto','Thebe']
    limit=1.1*max(np.max(np.abs(cases[n]['observation']['measured_displacement_mm'])) for n in names)
    fig,axes=plt.subplots(2,4,figsize=(15,7.5),constrained_layout=True)
    for ax,name in zip(axes.flat,names):
        c=cases[name];o=c['observation'];t=np.array(o['time_s']);mask=t>=t[-1]-20;xx=t[mask]-t[-1]+20
        ax.plot(xx,np.array(o['predicted_displacement_mm'])[mask],color='#df783c',lw=1.4,label='Fixed-parameter prediction')
        ax.plot(xx,np.array(o['measured_displacement_mm'])[mask],'.',color='#236783',ms=1.8,label='Simulated measurement')
        subtitle='Autonomous' if name=='No orbit' else ('Repeats each orbit' if c['orbit_repeat']['repeat_orbits']==1 else 'No 1–4 orbit repeat' if c['orbit_repeat']['repeat_orbits'] is None else f"Repeats every {c['orbit_repeat']['repeat_orbits']} orbits")
        ax.set(title=name+'\n'+subtitle,xlabel='Time in late window (s)',ylabel='Displacement (mm)',ylim=(-limit,limit));ax.grid(alpha=.15)
    axes[0,0].legend(fontsize=7,loc='lower left');fig.suptitle('Circular and eccentric forcing — equal RMS force, 5.7 s orbit',fontsize=17)
    fig.savefig(ROOT/'figures/hug_rhythm_orbits.png',dpi=165);plt.close(fig)
    selected=[cases['No orbit']]+[c for c in d['cases'] if c['eccentricity'] is not None]
    fig,axes=plt.subplots(1,2,figsize=(13,7),constrained_layout=True)
    means=[];lo=[];hi=[]
    for c in selected:
        values=[r['mean_period_s'] for r in c['measurement_noise_checks']];mean=c['clean_metrics']['mean_period_s'];means.append(mean);lo.append(mean-min([mean]+values));hi.append(max([mean]+values)-mean)
    yy=np.arange(len(selected));labels=[c['name'].replace(' — detuned control',' (4 s orbit)') for c in selected]
    axes[0].errorbar(means,yy,xerr=[lo,hi],fmt='o',color='#236783',capsize=4);axes[0].axvline(cycle['period_s'],color='#df783c',ls='--',label='Unforced cycle')
    axes[0].set_yticks(yy,labels);axes[0].invert_yaxis();axes[0].set(xlabel='Mean interval between upward crossings (s)',title='Timing from simulated measurements');axes[0].legend(fontsize=8)
    forced=selected[1:];errors=[min(c['orbit_repeat']['return_errors_scaled'].values()) for c in forced]
    axes[1].scatter(errors,np.arange(len(forced)),c=['#236783' if c['orbit_repeat']['repeat_orbits'] else '#df783c' for c in forced]);axes[1].set_xscale('log');axes[1].axvline(cfg['gates']['orbit_repeat_error_scaled'],ls='--',color='gray',label='Declared repetition tolerance')
    axes[1].set_yticks(np.arange(len(forced)),labels[1:]);axes[1].invert_yaxis();axes[1].set(xlabel='Smallest full-state mismatch over 1–4 orbits',title='Does the simulated state repeat with the orbit?');axes[1].legend(fontsize=8)
    fig.suptitle('Noise and forcing-period controls — simulation only',fontsize=16)
    fig.savefig(ROOT/'figures/hug_rhythm_controls.png',dpi=165);plt.close(fig)


def html_section():
    d=read();cy=d['autonomous_cycle'];rows=[]
    for c in [d['cases'][0]]+[c for c in d['cases'] if c['eccentricity'] is not None]:
        m=c['clean_metrics'];repeat='Autonomous cycle' if c['eccentricity'] is None else ('No 1–4 orbit repeat detected' if c['orbit_repeat']['repeat_orbits'] is None else 'Repeats after '+str(c['orbit_repeat']['repeat_orbits'])+' full orbit(s)')
        rows.append(f"<tr><td>{c['name']}</td><td>{m['mean_period_s']:.6f}</td><td>{m['period_cv']*100:.3f}%</td><td>{m['mean_half_amplitude_mm']:.4f}</td><td>{repeat}</td></tr>")
    return f'''<section id="hug-rhythm"><h2>Batch 14 · the Hug’s rhythm in simulated measurements</h2>
<p>The synthetic calibration defines a rhythm of <strong>{cy['period_s']:.6f} simulation seconds</strong> without an orbit. Three starts approach the same full-state cycle; a disturbed cycle returns, and a feedback-off control decays. These results use the assumed mass, stiffness and clay properties from the synthetic calibration. They do not measure the period of your physical clay Hug.</p>
<p>Fixed fitted parameters predict new recordings. We add two levels of Gaussian position-measurement noise and three seeds, then estimate period and amplitude from the resulting readings. Noise affects the observations only. Circular and six eccentric Kepler-shaped forces share a chosen 5.7-second orbital period and equal RMS force; two 4-second cases test detuning.</p>
<figure><img src="figures/hug_rhythm_autonomous.png" alt="Simulated autonomous Hug growth, noisy measurements, phase portrait and recovery after a disturbance"><figcaption>Powered feedback sustains the simulated rhythm. Full-state shooting, Floquet stability, energy accounting and independent integration support the numerical result.</figcaption></figure>
<figure><img src="figures/hug_rhythm_orbits.png" alt="Simulated recordings without an orbit and with circular, Pasiphae, Elara, Himalia, Europa, Callisto and Thebe inputs"><figcaption>Dots are simulated sensor readings; lines are predictions from the fixed calibration. Orbital repetition is checked using all four simulated state variables.</figcaption></figure>
<div class="scroll"><table><thead><tr><th>Case</th><th>Mean interval (s)</th><th>Interval variability</th><th>Half amplitude (mm)</th><th>Repetition result</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<figure><img src="figures/hug_rhythm_controls.png" alt="Comparison of measured periods and full-state orbital repetition errors including detuned controls"><figcaption>Period whiskers span the six chosen noise realizations, not confidence intervals. A missing short repeat does not establish chaos.</figcaption></figure>
<p><a href="HUG_RHYTHM_METHODS.md">Rhythm methods and limits</a> · <a href="hug_rhythm_results.json">Saved simulated observations and checks</a> · <a href="CLAY_STARTER_TEST.md">Tomorrow’s clay starter test</a> · <a href="calibration/compression_observations.csv">Empty compression record</a> · <a href="calibration/measurements.html">Shear-calibration entry</a></p>
<p>All {len(d['checks'])} declared rhythm accuracy gates: <strong>{d['status']}</strong>. This batch adds no physical measurements and no SIMS participant runs. Compression observations belong in their separate starter record; the existing calibration form expects sideways shear.</p></section>'''


if __name__=='__main__':build_figures();print('Built three simulated rhythm figures')
