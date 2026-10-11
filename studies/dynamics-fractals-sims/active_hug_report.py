"""Original scientific figures for the proposed active mechanical extension."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from active_hug import ActiveHug, protocol, orbital_force
from clay_sims import source

ROOT=Path(__file__).resolve().parent
COLORS=['#7950a1','#d26b36','#258770','#287b99','#b9941a','#566583']


def build_figures():
    d=json.loads((ROOT/'active_hug_results.json').read_text());p=protocol();scale=100*p['strain_scale'];t0=p['time_scale_seconds']
    row=20; m=next(m for m in source.materials() if m['stress_Pa']==row);model=ActiveHug(m)
    end=p['horizon_scaled_time']*t0;tail_begin=end-600;last_three=end-300
    autos=[r for r in d['autonomous'] if r['coefficient_row_stress_Pa']==row]
    cyc=next(r for r in d['cycles'] if r['coefficient_row_stress_Pa']==row)
    fig,axes=plt.subplots(2,3,figsize=(13,7.8));a=axes.flat
    for r,c in zip(autos,COLORS):
        t=np.array(r['trace']['time_seconds']);z=np.array(r['trace']['state']);mask=t<=1000
        a[0].plot(t[mask],scale*z[mask,0],color=c,label=f"Start {r['start_index']+1}",lw=1)
        a[1].plot(scale*z[t>tail_begin,0],scale*z[t>tail_begin,1]/t0,color=c,lw=1)
    a[0].set(title='Different starts approach sustained motion',xlabel='Model time (s)',ylabel='Actual shear strain (%)');a[0].legend(fontsize=8)
    a[1].set(title='Autonomous phase portrait',xlabel='Actual shear strain (%)',ylabel='Strain rate (% / s)')
    z=np.array(cyc['cycle_state']);t=np.array(cyc['cycle_time_seconds'])
    for i,label,c in [(0,'Total strain','#236783'),(2,'Delayed clay strain','#d26b36'),(3,'Viscous memory','#258770')]:a[2].plot(t,scale*z[:,i],label=label,color=c)
    a[2].set(title='Both clay memory states repeat',xlabel='Time within cycle (s)',ylabel='Actual strain (%)');a[2].legend(fontsize=8)
    passive=next(r for r in d['passive'] if r['coefficient_row_stress_Pa']==row)
    for r,label,c in [(autos[1],'Feedback on','#236783'),(passive,'Feedback off','#d26b36')]:
        tt=np.array(r['trace']['time_seconds']);zz=np.array(r['trace']['state']);mask=tt<=1000
        a[3].plot(tt[mask],scale*zz[mask,0],label=label,color=c,lw=1)
    a[3].set(title='Passive control loses its motion',xlabel='Model time (s)',ylabel='Actual shear strain (%)');a[3].legend(fontsize=8)
    a[4].bar(['Feedback input','Clay dissipation'],np.array([cyc['active_work_per_cycle_scaled'],cyc['dissipation_per_cycle_scaled']])*model.energy_scale,color=['#236783','#d26b36'])
    a[4].set(title='Independent energy integrals agree',ylabel='Energy per cycle (J / m³)')
    a[4].text(.03,.93,f"Balance error: {cyc['independent_power_balance_error']*model.energy_scale:.2g} J/m³",transform=a[4].transAxes,va='top',fontsize=8,bbox=dict(facecolor='white',edgecolor='none',alpha=.8))
    for rr,c in zip((10,20,30,40),COLORS):
        g=[r for r in d['gain_controls'] if r['coefficient_row_stress_Pa']==rr]
        a[5].plot([r['gain'] for r in g],[r['leading_real_eigenvalue']/t0 for r in g],marker='o',ms=3,color=c,label=f'{rr} Pa fit')
    a[5].axhline(0,color='#777',lw=.8);a[5].set(xlim=(0,1.05),title='Rest becomes linearly unstable',xlabel='Feedback gain (dimensionless)',ylabel='Largest growth rate (1 / s)');a[5].legend(fontsize=8)
    fig.suptitle(f'Active clay Hug without an orbit · period {cyc["period_seconds"]:.2f} model seconds',fontsize=15)
    fig.text(.5,.015,'20 Pa coefficient set except the gain comparison. Inertia, restoring stiffness and feedback are chosen model additions.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.045,1,.95));fig.savefig(ROOT/'figures/active_hug_autonomous.png',dpi=135);plt.close(fig)

    forced=[r for r in d['forced'] if r['coefficient_row_stress_Pa']==row];circle=forced[0]
    fig,axes=plt.subplots(2,3,figsize=(13,7.8))
    for ax,r,c in zip(axes.flat,forced[1:],COLORS):
        t=np.array(r['trace']['time_seconds']);z=np.array(r['trace']['state']);mask=t>=last_three
        ct=np.array(circle['trace']['time_seconds']);cz=np.array(circle['trace']['state']);cm=ct>=last_three
        ax.plot(ct[cm]-last_three,scale*cz[cm,0],color='#59616a',ls='--',lw=1.2,label='Circular input')
        ax.plot(t[mask]-last_three,scale*z[mask,0],color=c,lw=1.3,label='Eccentric input')
        ax.set(title=f"{r['name']} · e={r['e']:.3f}",xlabel='Time over final three orbits (s)',ylabel='Actual shear strain (%)')
        repeat=r['detected_repeat_orbits'];text=f'Repeats within {repeat} orbit(s)' if repeat else 'No repeat detected within 1–4 orbits'
        ax.text(.02,.97,text,transform=ax.transAxes,va='top',fontsize=8,bbox=dict(facecolor='white',edgecolor='none',alpha=.85))
        ax.margins(y=.12)
        ax.legend(fontsize=8,loc='lower right')
    fig.suptitle('Active Hug with circular and eccentric orbital inputs',fontsize=15)
    fig.text(.5,.015,'Equal RMS signed tidal-shaped input; one orbit = 100 model seconds. 20 Pa fit. Forces are chosen, not measured gravitational stresses.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.045,1,.95));fig.savefig(ROOT/'figures/active_hug_orbits.png',dpi=135);plt.close(fig)

    fig,axes=plt.subplots(2,3,figsize=(13,7.8));t=np.linspace(0,100,501)
    for e,label,c in [(0,'Circular','#59616a'),(.412,'Pasiphae',COLORS[0]),(.009,'Europa',COLORS[3])]:
        axes[0,0].plot(t,orbital_force(t/t0,e),color=c,label=label,ls='--' if e==0 else '-')
    axes[0,0].set(title='Signed forcing over one orbit',xlabel='Model time (s)',ylabel='Scaled force');axes[0,0].legend(fontsize=8)
    for r,c in [(circle,'#59616a'),(forced[1],COLORS[0]),(forced[4],COLORS[3])]:
        z=np.array(r['trace']['state']);axes[0,1].plot(scale*z[:,0],scale*z[:,1]/t0,color=c,lw=.9,label=r['name'])
        st=np.array(r['strobe_state']);axes[0,2].scatter(scale*st[:,0],scale*st[:,1]/t0,color=c,s=16,label=r['name'])
    axes[0,1].set(title='Last six orbits: phase portraits',xlabel='Actual shear strain (%)',ylabel='Strain rate (% / s)');axes[0,1].legend(fontsize=8)
    axes[0,1].xaxis.set_major_locator(MaxNLocator(5))
    axes[0,2].set(title='Sample once per full orbital period',xlabel='Actual shear strain (%)',ylabel='Strain rate (% / s)');axes[0,2].legend(fontsize=8)
    for r,c in zip([circle]+forced[1:],["#59616a"]+COLORS):
        tt=np.array(r['trace']['time_seconds']);z=np.array(r['trace']['state'])
        axes[1,0].plot(tt-tail_begin,scale*z[:,3],color=c,label=r['name'],lw=.9)
        # Tail work increments, evaluated against the local change in stored energy.
        balance=model.energy(z)-model.energy(z[0])-(z[:,4]-z[0,4])-(z[:,5]-z[0,5])+(z[:,6]-z[0,6])
        axes[1,1].plot(tt-tail_begin,balance*model.energy_scale,color=c,lw=.9)
    axes[1,0].set(title='Viscous memory: check for drift',xlabel='Time over final six orbits (s)',ylabel='Actual viscous strain (%)')
    axes[1,1].set(title='Energy accounting residual',xlabel='Time over final six orbits (s)',ylabel='Residual (J / m³)')
    for rr,c in zip((10,20,30,40),COLORS):
        rows=[r for r in d['forced'] if r['coefficient_row_stress_Pa']==rr]
        axes[1,2].plot(range(7),[r['peak_actual_strain']*100 for r in rows],color=c,marker='o',ms=3,label=f'{rr} Pa fit')
    axes[1,2].set(title='All four frozen clay coefficient sets',ylabel='Peak absolute strain (%)',xticks=range(7),xticklabels=['Circle','Pasiphae','Elara','Himalia','Europa','Callisto','Thebe'])
    axes[1,2].tick_params(axis='x',rotation=45);axes[1,2].legend(fontsize=8)
    fig.suptitle('Orbital forcing, memory and numerical checks',fontsize=15)
    fig.text(.5,.015,'A repeated forced response is reported separately from the autonomous limit cycle. Contacts are not modeled.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.045,1,.95));fig.savefig(ROOT/'figures/active_hug_diagnostics.png',dpi=135);plt.close(fig)

    from hug_orbits import outline
    fig,axes=plt.subplots(2,4,figsize=(13,7.2))
    shape_cases=[('Autonomous',np.array(cyc['cycle_state'])[:,0]*p['strain_scale'])]+[(r['name'],np.array(r['trace']['state'])[-81:,0]*p['strain_scale']) for r in forced]
    for ax,(name,values) in zip(axes.flat,shape_cases):
        for arm in outline(0):
            arm=np.array(arm);ax.plot(arm[:,0],arm[:,1],color='#b3bec7',ls=':',lw=1)
        for strain,label,c in [(float(np.min(values)),'Minimum strain','#287b99'),(float(np.max(values)),'Maximum strain','#d26b36')]:
            for i,arm in enumerate(outline(strain,200)):
                arm=np.array(arm);ax.plot(arm[:,0],arm[:,1],color=c,lw=1.4,label=label if i==0 else None)
        ax.set(title=name,xlim=(-1.7,1.7),ylim=(-1.2,1.2),aspect='equal')
        ax.text(.03,.04,f'{np.min(values)*100:+.3f}% to {np.max(values)*100:+.3f}%',transform=ax.transAxes,fontsize=8)
    axes.flat[0].legend(fontsize=7,loc='upper left')
    fig.suptitle('The Hug moves in both shear directions',fontsize=15)
    fig.text(.5,.035,'20 Pa fit. Shapes magnified 200×; labels show actual strain. Forced extrema cover the final orbit. Closure follows the display map.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.07,1,.95));fig.savefig(ROOT/'figures/active_hug_shapes.png',dpi=135);plt.close(fig)


def html_section():
    d=json.loads((ROOT/'active_hug_results.json').read_text())
    periods=', '.join(f"{r['coefficient_row_stress_Pa']:g} Pa fit: {r['period_seconds']:.2f} s" for r in d['cycles'])
    return f'''<section id="active-hug"><h2>Active Hug: establish its own cycle, then add the orbit</h2>
<p>This proposed extension adds inertia, a parallel restoring stiffness and amplitude-dependent powered feedback to the unchanged Burgers clay internal law. Twelve starts establish autonomous motion across four frozen coefficient sets. Periodic shooting closes all four states, transverse Floquet multipliers test attraction, and kicks return toward the cycle. Four passive controls lose their motion.</p>
<p>Autonomous periods in model seconds: {periods}. Twenty-eight additional forced trajectories compare one circular input with the six reference eccentricities. A signed tidal-shaped signal has equal RMS across cases, with one orbit compressed to 100 model seconds. It is a declared input, not a calibrated gravitational stress.</p>
<figure><img src="figures/active_hug_autonomous.png" alt="Autonomous Hug cycles, memory, passive controls and energy"><figcaption>Cycles emerge from feedback; all clay memory states are included in the periodicity checks.</figcaption></figure>
<figure><img src="figures/active_hug_orbits.png" alt="Circular and eccentric forced active Hug responses"><figcaption>Dashed gray is the circular input response; color is the eccentric input response. Actual strains are shown.</figcaption></figure>
<figure><img src="figures/active_hug_diagnostics.png" alt="Signed forcing, state portraits, memory and energy residuals"><figcaption>Full-state orbital samples distinguish repeat patterns from continuing drift. No contact or opening prediction is made.</figcaption></figure>
<figure><img src="figures/active_hug_shapes.png" alt="Active Hug outlines at minimum and maximum strain"><figcaption>Both directions of the Hug's shear mode; shapes magnified 200 times, strain labels are actual.</figcaption></figure>
<p>Thirty-two separate Radau integrations verify late segments of every autonomous and forced coefficient/input pair. These are direct Hug experiments, adding zero SIMS participant runs. <a href="ACTIVE_HUG_METHODS.md">Equations, controls and interpretation</a> · <a href="active_hug_protocol.json">Protocol</a> · <a href="active_hug_results.json">Results</a> · <a href="test_active_hug.py">Tests</a>.</p></section>'''


if __name__=='__main__':build_figures()
