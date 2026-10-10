"""Original circular/eccentric orbit and orbit-driven clay SIMS figures."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from orbits import protocol,orbit

ROOT=Path(__file__).resolve().parent
COLORS=['#7e3f8f','#d36c37','#348b72','#236783','#b69024','#565f77']


def data():return json.loads((ROOT/'orbit_results.json').read_text())


def build_figures():
    cfg=protocol();q=np.linspace(0,1,721)
    fig,axes=plt.subplots(2,3,figsize=(13,8),layout='constrained')
    for ax,m,c in zip(axes.flat,cfg['moons'],COLORS):
        x,_=orbit(m,q*m['period_days']);circle,_=orbit(m,q*m['period_days'],0)
        ax.plot(circle[:,0]/m['a_km'],circle[:,1]/m['a_km'],ls='--',color='#92999d',label='Circular control, e=0')
        ax.plot(x[:,0]/m['a_km'],x[:,1]/m['a_km'],color=c,lw=2,label=f"Reference e={m['e']:.3f}")
        ax.scatter([0],[0],s=35,color='#1b2935',zorder=5,label='Jupiter focus')
        ax.scatter([(1-m['e'])], [0],s=15,color=c,zorder=5)
        ax.set(aspect='equal',xlim=(-1.5,1.2),ylim=(-1.2,1.2),xlabel='x / semimajor axis',ylabel='y / semimajor axis',
               title=f"{m['name']} · requested {m['requested_group']}\na={m['a_km']:,} km · P={m['period_days']:g} days")
        ax.legend(fontsize=7,loc='lower left');ax.grid(alpha=.15)
    fig.suptitle('Circular controls and eccentric Jupiter-moon paths\nEach panel uses its own orbital plane and scale; these are frozen shapes, not current positions.',fontsize=14)
    fig.savefig(ROOT/'figures/jupiter_orbits.png',dpi=125,bbox_inches='tight');plt.close(fig)
    d=data();fig,axes=plt.subplots(2,2,figsize=(13,9),layout='constrained')
    rows=[x for x in d['representative_traces'] if x['graph']=='Menger L1']
    base=rows[0]
    for ax,key,label in [(axes[0,0],'load_Pa','Applied load (Pa)'),(axes[0,1],'mean_total','Mean strain (%)')]:
        factor=100 if key=='mean_total' else 1
        ax.plot(base['time'],factor*np.array(base[key]),color='#1b2935',ls='--',label='Circular control',lw=2)
        for row,c in zip(rows[1:],COLORS):ax.plot(row['time'],factor*np.array(row[key]),label=row['case'],color=c)
        ax.set(xlabel='SIMS time (s)',ylabel=label);ax.grid(alpha=.15);ax.legend(fontsize=8)
    axes[0,0].set_title('One equal-mean orbit-shaped loading cycle')
    axes[0,1].set_title('Mean deformation responds to waveform timing')
    ax=axes[1,0]
    for g,c in zip(['Menger L1','Ring 20','Complete 20'],['#236783','#d36c37','#348b72']):
        row=next(x for x in d['representative_traces'] if x['graph']==g and x['case']=='Circular control')
        ax.plot(row['time'],100*np.array(row['absolute_spread']),label=g,color=c)
    ax.set(title='Within each graph, all seven inputs give the same spread',xlabel='SIMS time (s)',ylabel='Strain standard deviation (%)')
    ax.grid(alpha=.15);ax.legend(fontsize=9)
    ax=axes[1,1];q=np.linspace(0,1,721)
    for m,c in zip(cfg['moons'],COLORS):
        x,_=orbit(m,q*m['period_days']);ax.plot(q,np.linalg.norm(x,axis=-1)/m['a_km'],label=m['name'],color=c)
    ax.axhline(1,color='#1b2935',ls='--',label='Circular control');ax.set(title='The orbital-distance signal behind the experiment',xlabel='Elapsed fraction of one orbit',ylabel='Radius / semimajor axis')
    ax.grid(alpha=.15);ax.legend(fontsize=8)
    fig.suptitle('Orbit-driven clay SIMS · 672 matched runs, fixed 20 Pa coefficient set\nOne orbit is compressed into 100 SIMS seconds; the pressure mapping is an experiment choice.',fontsize=14)
    fig.savefig(ROOT/'figures/orbit_clay_sims.png',dpi=125,bbox_inches='tight');plt.close(fig)


def html_section():
    d=data();cfg=protocol()
    rows=''.join(f"<tr><td>{m['name']}</td><td>{m['requested_group']}</td><td>{m['e']:.3f}</td><td>{m['a_km']:,}</td><td>{m['period_days']:g}</td></tr>" for m in cfg['moons'])
    error=max(x.get('max_strain_error',0) for x in d['controls'])
    return f'''<section id="orbits"><h2>Batch 10 · circular and eccentric moon orbits</h2>
<p>Your CO group is Pasiphae, Elara and Himalia; your eccentric group is Europa, Callisto and Thebe. “Dasiphae” is interpreted as Pasiphae and “thebes” as Thebe. All six now have a circular control and a reference eccentric ellipse. The first three have substantial reference eccentricity, so their circular paths are explicitly experimental approximations.</p>
<div class="scroll"><table><tr><th>Moon</th><th>Requested group</th><th>Reference eccentricity</th><th>Semimajor axis (km)</th><th>Reference period (days)</th></tr>{rows}</table></div>
<figure><img src="figures/jupiter_orbits.png" alt="Six normalized orbital-plane plots comparing circles and eccentric paths for Pasiphae, Elara, Himalia, Europa, Callisto and Thebe"><figcaption>Jupiter lies at the focus. Each panel uses a separate orbital plane and semimajor-axis scale. The nearly circular Europa, Callisto and Thebe paths overlap their controls closely. JPL mean elements describe general shapes, not present positions or accurate ephemerides; inclination and precession are excluded from this frozen two-dimensional comparison.</figcaption></figure>
<h3>Use the orbit inside the clay-SIMS test</h3>
<p>A stated inverse-square-distance waveform applies the same pressure to each participant. Its time average is fixed at 20 Pa for every case, and one orbit is compressed into the existing 100-second loading interval. The 20 Pa clay coefficient set, recovery duration, graph coupling and 32 starting patterns stay fixed. The six eccentric signals plus one shared circular signal produce <strong>672 main SIMS runs</strong> on three networks. Identical circular participant runs are shared across moon labels rather than counted six times.</p>
<figure><img src="figures/orbit_clay_sims.png" alt="Orbital loading waveforms, clay population mean deformation, graph-dependent spread and varying orbital radius"><figcaption>The conversion from orbital distance into clay pressure is a controlled SIMS input choice. It does not calculate measured lunar stress. Orbital periods in days remain in the orbit controls; participant time is in seconds.</figcaption></figure>
<p>Eccentric timing changes transient deformation and residual recoverable strain. Equal total loading gives the same final retained population mean. Differences between participants follow the same decay for every orbit-shaped input on a given graph: the common drive excites only the population mean in this linear clay model. Positive shared loading and response-sign agreement do not establish voluntary agreement.</p>
<p>Twenty-three new tests check Kepler's equation, circular limits, periapsis and apoapsis, equal swept areas, energy and angular momentum, independent Cartesian integration, loading jumps, the original clay reduction, convolution quadrature and paired SIMS outcomes. Twelve full-network solver controls agree within {error:.3g} strain, and all accuracy gates pass.</p>
<p><a href="ORBIT_METHODS.md">Equations, controls and limitations</a> · <a href="orbit_protocol.json">Pinned orbital data and protocol</a> · <a href="orbit_results.json">All new runs and controls</a> · <a href="https://ssd.jpl.nasa.gov/sats/elem/sep.html">JPL primary orbital data</a></p></section>'''
