import base64,html,json
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline,CubicHermiteSpline
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import findfont
from PIL import Image,ImageDraw,ImageFont
from model import ROOT,protocol
BG='#faf9f5';INK='#193f46';TEAL='#087f8c';GRAY='#718087';ORANGE='#bc5d32';COLORS=[TEAL,'#8651a0',ORANGE]

def plots(p,r):
    target=ROOT/'figures';target.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.facecolor':BG,'figure.facecolor':BG,'axes.titleweight':'bold'})
    primary=[x for x in r['studies'] if x['orbit_policy']=='scaled']
    fig,ax=plt.subplots(1,2,figsize=(12,4.6),constrained_layout=True)
    for c in range(3):
        x=[100*s['paths'][2*c]['max_shear'] for s in primary];y=[100*s['pairs'][2*c]['late_field_relative_rms'] for s in primary]
        ax[0].plot(x,y,'o-',color=COLORS[c],label=p['conditions'][c]['name']);ax[1].plot(x,[100*abs(s['pairs'][2*c]['relative_amplitude_change']) for s in primary],'o-',color=COLORS[c])
    for a in ax:a.set_xscale('log');a.set_xlabel('Largest actual shear in that path (%)');a.grid(alpha=.15)
    ax[0].set_title('The spatial pattern changes more');ax[0].set_ylabel('Late pattern difference from fixed geometry (%)');ax[0].legend(fontsize=8)
    ax[1].axhline(1,color=ORANGE,ls='--');ax[1].set_ylim(-.06,1.16);ax[1].set_title('Rhythm-size change stays near zero');ax[1].set_ylabel('Late amplitude change from fixed geometry (%)')
    ax[1].text(.03,.91,'1% screening band',transform=ax[1].transAxes,color=ORANGE)
    peak=max(abs(x['relative_amplitude_change'])*100 for s in primary for x in s['pairs'])
    pace=max(abs(x['relative_period_change'])*100 for s in primary for x in s['pairs'])
    ax[1].text(.06,.37,f'Largest amplitude change: {peak:.5f}%\nLargest period change: {pace:.6f}%\nNo sampled primary setting crosses a rhythm band.',transform=ax[1].transAxes,fontsize=10,bbox={'facecolor':'white','edgecolor':'#cdd5d5','pad':9})
    fig.suptitle('Larger motion redistributes expression; the tested rhythm barely changes',fontsize=16)
    fig.savefig(target/'sweep.png',dpi=150);plt.close(fig)
    d=np.load(ROOT/'data/scaled-300.npz');t=d['time'];mask=(t>=1740)&(t<=1757);uniform=np.isclose(t*2,np.round(t*2),atol=1e-7)&mask
    fig,axes=plt.subplots(2,3,figsize=(12,6.7),constrained_layout=True)
    for c in range(3):
        j=2*c;tt=np.linspace(1740,1757,681)
        for k,color,width,style,labeltext in [(j,TEAL,2.8,'-','Movement feedback'),(j+6,GRAY,1.5,'--','Fixed geometry')]:
            curve=CubicHermiteSpline(t,d['mechanics'][:,k,0],d['mechanics'][:,k,1])(tt)*.1
            axes[0,c].plot(tt,curve,color=color,lw=width,ls=style,label=labeltext)
        axes[0,c].set_title(p['conditions'][c]['name']);axes[0,c].set_xlabel('Simulation time (s)');axes[0,c].grid(alpha=.15)
        im=axes[1,c].imshow(d['field_delta'][uniform,c].T,origin='lower',aspect='auto',extent=[1740,1757,0,360],cmap='PuOr_r',vmin=-.012,vmax=.012,interpolation='nearest')
        axes[1,c].set_yticks([0,90,180,270,360],['Right','Top','Left','Bottom','Right'] if c==0 else []);axes[1,c].set_xlabel('Simulation time (s)');axes[1,c].set_xticks([1740,1745,1750,1755])
    axes[0,0].set_ylabel('Displacement (mm)');axes[0,0].legend(fontsize=7);axes[1,0].set_ylabel('Position around the Hug')
    fig.colorbar(im,ax=axes[1].tolist(),label='Local expression change from fixed geometry',shrink=.8)
    fig.suptitle('Largest setting: nearly overlapping movement, different field patterns\nFactor 300; first start; actual movement, synthetic material',fontsize=14)
    fig.savefig(target/'largest-motion.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.3),constrained_layout=True)
    for ci,c in enumerate([1,2]):
        ax=axes[ci]
        for policy,color,label in [('scaled',TEAL,'Orbit force grows with motion'),('fixed',ORANGE,'Orbit force held fixed')]:
            dd=np.load(ROOT/f'data/{policy}-300.npz');ot=dd['orbital_time'];j=c*2
            ax.semilogy(ot,dd['repeat'][:,j],color=color,lw=2,label=label)
            ax.semilogy(ot,dd['repeat'][:,j+6],color=color,ls=':',lw=1,label='Fixed-geometry control' if policy=='fixed' else None)
        ax.axhline(.01,color=GRAY,ls='--');ax.axvspan(480,720,color=GRAY,alpha=.15);ax.set_title(p['conditions'][c]['name']);ax.set_xlabel('Simulation time (s)');ax.grid(alpha=.15)
    axes[0].set_ylabel('Mechanical orbit-repeat error (lower is closer)');axes[1].legend(fontsize=8)
    fig.suptitle('Relative orbital forcing changes repetition\nFactor 300; feedback and fixed-geometry controls closely overlap',fontsize=15)
    fig.savefig(target/'forcing-control.png',dpi=150);plt.close(fig)

def build_animation(p,r):
    clips=[('Before braking',420,450),('During braking',650,680),('After release',900,930),('Late outcome',1740,1770)]
    times=np.concatenate([np.linspace(a,b,151) for _,a,b in clips]);datasets=[]
    pack=lambda a:base64.b64encode(np.asarray(a,dtype='<f4').tobytes()).decode()
    for s in r['studies']:
        d=np.load(ROOT/f"data/{s['orbit_policy']}-{s['scale']}.npz");t=d['time'];ids=[0,2,4,6,8,10]
        q=CubicHermiteSpline(t,d['mechanics'][:,ids,0],d['mechanics'][:,ids,1],axis=0)(times)*.1
        delta=CubicSpline(t,d['field_delta'].astype(float),axis=0)(times)
        amp=np.stack([np.interp(times,t,d['amplitude'][:,j]) for j in [0,2,4]],axis=1)
        oi=np.maximum(np.searchsorted(d['orbital_time'],times,side='right')-1,0);rep=d['repeat'][oi][:,[0,2,4]]
        datasets.append(dict(scale=s['scale'],policy=s['orbit_policy'],q=pack(q),delta=pack(delta),amplitude=pack(amp),repeat=pack(rep),baseline=[s['paths'][j]['baseline_half_amplitude_mm'] for j in [0,2,4]],fieldRMS=[s['pairs'][j]['late_field_relative_rms'] for j in [0,2,4]],flags=[s['pairs'][j]['flags'] for j in [0,2,4]]))
    data=dict(times=times.tolist(),frames=len(times),cells=32,clips=[dict(name=n,start=i*151,count=151) for i,(n,_,_) in enumerate(clips)],datasets=datasets,conditions=[c['name'] for c in p['conditions']],colorLimit=.012,period=5.7,displayGain=1)
    (ROOT/'animation-data.js').write_text('const SWEEPDATA='+json.dumps(data,separators=(',',':'))+';\n',encoding='utf-8')
    # GIF compares the two force policies at the largest movement setting.
    selected=[datasets[5],datasets[7]];decoded=[]
    for s in selected:decoded.append({k:np.frombuffer(base64.b64decode(s[k]),dtype='<f4').reshape(len(times),*shape) for k,shape in [('q',(6,)),('delta',(3,32)),('amplitude',(3,)),('repeat',(3,))]})
    fontpath=findfont('DejaVu Sans');title=ImageFont.truetype(fontpath,23);normal=ImageFont.truetype(fontpath,16);small=ImageFont.truetype(fontpath,12);cmap=plt.get_cmap('PuOr_r');frames=[]
    for ci in range(4):
        for frame in range(ci*151,(ci+1)*151,3):
            image=Image.new('RGB',(1080,800),BG);draw=ImageDraw.Draw(image);time=times[frame]
            draw.text((28,20),'Larger Hug movement: what changes the rhythm?',font=title,fill=INK)
            draw.text((28,57),f'Factor 300 | {clips[ci][0]} | simulation {time:.1f} s | actual shape, gain x1',font=normal,fill=INK)
            draw.text((28,83),'Solid: movement feedback. Dashed gray: fixed-geometry control. Colors show field differences.',font=small,fill=GRAY)
            for row,(s,a) in enumerate(zip(selected,decoded)):
                ytop=120+row*300;draw.text((28,ytop),'Orbit force grows with motion' if row==0 else 'Orbit force stays at its original value',font=normal,fill=TEAL if row==0 else ORANGE)
                for c in range(3):
                    left=28+c*355;cx=left+150;cy=ytop+151;radius=69;shear=float(a['q'][frame,c])/100;old=float(a['q'][frame,c+3])/100
                    th=np.linspace(0,2*np.pi,257);xy=np.column_stack([cx+radius*(np.cos(th)+shear*np.sin(th)),cy-radius*np.sin(th)]);oldxy=np.column_stack([cx+radius*(np.cos(th)+old*np.sin(th)),cy-radius*np.sin(th)])
                    draw.text((left,ytop+32),data['conditions'][c],font=normal,fill=INK)
                    if c==0:status='Self-rhythm (no orbit)'
                    else:status='Orbit-repeat confirmed' if a['repeat'][frame,c]<.01 else 'Orbit-repeat not confirmed'
                    if a['amplitude'][frame,c]<.1*s['baseline'][c]:status='Small motion during braking'
                    draw.text((left,ytop+56),status,font=small,fill=INK)
                    draw.line([tuple(x) for x in xy],fill='#aab4b6',width=9)
                    for j in range(256):
                        k=int(j*32/256);value=float(a['delta'][frame,c,k]);rgb=tuple(int(255*x) for x in cmap(np.clip(.5+value/.024,0,1))[:3]);draw.line([tuple(xy[j]),tuple(xy[j+1])],fill=rgb,width=5)
                    for j in range(0,256,8):draw.line([tuple(x) for x in oldxy[j:j+4]],fill=GRAY,width=1)
                    draw.text((left,ytop+239),f'd = {a["q"][frame,c]:+.2f} mm | shear {100*shear:+.1f}%',font=small,fill=INK)
                    draw.text((left,ytop+258),'No paired rhythm band crossed',font=small,fill=TEAL)
            draw.text((28,735),'Purple: less local expression than control. Orange: more. White: little difference.',font=normal,fill=INK)
            draw.text((28,760),'Same color scale +/- 0.012 S. Accumulated history is retained. Synthetic equations, unmeasured clay.',font=small,fill=GRAY)
            frames.append(image)
    frames[0].save(ROOT/'hug-movement.gif',save_all=True,append_images=frames[1:],duration=100,loop=0,optimize=False)
    return data

def report(p,r):
    primary=[s for s in r['studies'] if s['orbit_policy']=='scaled'];maxstrain=max(x['max_shear'] for s in primary for x in s['paths'])*100
    flagcount=sum(bool(x['flags']) for s in r['studies'] for x in s['pairs']);rows=[]
    for s in r['studies']:
        for c in range(3):
            j=2*c;a=s['paths'][j];b=s['paths'][j+6];pair=s['pairs'][j]
            def delay(value):return 'Not confirmed' if value is None else f'{value:.1f} s'
            rows.append(f'<tr><td>{s["scale"]}</td><td>{"Proportional" if s["orbit_policy"]=="scaled" else "Fixed"}</td><td>{html.escape(p["conditions"][c]["name"])}</td><td>{100*a["max_shear"]:.2f}%</td><td>{100*pair["late_field_relative_rms"]:.4f}%</td><td>{delay(b["amplitude_delay_s"])} / {delay(a["amplitude_delay_s"])}</td><td>{"N/A" if c==0 else ("Yes" if a["late_repeats"] else "No")}</td><td>{"; ".join(pair["flags"]) or "None"}</td></tr>')
    maxamp=max(abs(x['relative_amplitude_change'])*100 for s in primary for x in s['pairs']);maxperiod=max(abs(x['relative_period_change'])*100 for s in primary for x in s['pairs'])
    text=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hug — larger movement tests</title><style>body{{max-width:1100px;margin:36px auto;padding:0 22px;background:{BG};color:{INK};font:17px/1.65 system-ui}}h1{{font-size:36px;line-height:1.2}}img{{width:100%;border-radius:12px}}a{{color:{TEAL}}}.card{{background:white;padding:20px 26px;border:1px solid #d9dfdf;border-radius:12px;margin:20px 0}}table{{font-size:13px;border-collapse:collapse;width:100%}}td,th{{padding:9px;border-bottom:1px solid #d9dfdf;text-align:left}}.scroll{{overflow:auto}}small{{color:{GRAY}}}</style><h1>Larger movement changes the pattern.<br>The tested rhythm stays almost the same.</h1><p>We tested the Hug without an orbit, with a circular orbit, and with an eccentric orbit. Actual simulated shear ranged up to {maxstrain:.1f}%. Movement increasingly restructures the expressed field, while the stored history remains intact.</p><p><a href="player.html">Play the comparisons</a> · <a href="TESTING_STRUCTURE.md">SciSpace-assisted testing structure</a> · <a href="METHODS.md">Equations and reproduction</a></p><div class="card"><strong>Scope correction: this is a reduced surrogate</strong><p>The corpus accumulator and selected response are retained, but the capped source, relaxation, pair exchange and Burgers mechanics are additional modeling choices. The corpus does not supply a Girardian doubling law or derive the clay material law. Upper-region mimetic interaction remains a separate graded design intent.</p><p><a href="SPECIFICATION_STATUS.md">See the specification register: what is assumed and what a full field simulation still needs.</a></p></div><div class="card"><strong>What counts as a change?</strong><p>We set screening bands before the sweep: 1% in amplitude or period, .05 cycle in phase, one orbit in recovery delay, or a changed orbit-repeat result. There were {flagcount} flagged matched comparisons in the completed set. This means no tested setting crossed those bands; it does not mean every numerical difference was exactly zero.</p><p>In the primary sweep the largest amplitude difference was {maxamp:.5f}% and the largest period difference was {maxperiod:.6f}%. Those tiny values should not be interpreted as physically measured precision.</p></div><img src="figures/sweep.png" alt="Field restructuring increases with shear while amplitude differences stay far below the one percent screening band"><h2>The comparison is paired</h2><p>For each movement setting we compare the declared movement-feedback surrogate with the same equations using fixed spatial operators. Sources, clay coefficients, spring and orbital clock are identical. Larger movement is created by a declared change to active saturation and starting displacement. In the primary family the orbital force grows in proportion; in a second family it stays fixed.</p><img src="figures/largest-motion.png" alt="Three orbital conditions at the largest setting show overlapping displacement curves and different spatial patterns"><h2>Why the extra orbital control matters</h2><p>When orbital force stays fixed as self-motion grows, it becomes relatively weaker. A loss of orbital repetition in both paired models is therefore not evidence that memory feedback caused the loss. The plot below keeps this distinction visible.</p><img src="figures/forcing-control.png" alt="Mechanical repeat errors with proportional and fixed orbital force"><h2>Watch the largest setting</h2><img src="hug-movement.gif" alt="Six panels compare actual Hug deformation in all three orbital conditions and two forcing policies"><p>The outlines use actual shear (gain ×1). Colors enlarge local field differences on a common ±.012 S scale; they do not show erased history. Clips jump between labeled windows of each saved trajectory. The outline is closed by its drawing map, not by a tested contact law.</p><h2>Testing structure for this chat</h2><ol><li><strong>Check the equations:</strong> distinguish retained corpus laws, modified laws and added operators; complete the full-field specification before claiming a full Hug field run.</li><li><strong>Check the calculations:</strong> finer space/time, retained history and energy accounting.</li><li><strong>Separate causes:</strong> matched feedback controls and the fixed-force family.</li><li><strong>Measure each kind of rhythm change:</strong> size, pace, timing, recovery and orbit repetition.</li><li><strong>Test the real clay separately:</strong> repeat load/recovery measurements, then identify which mechanisms and coefficients they can support.</li></ol><p>SciSpace helped locate material-testing and synchronization research. The <a href="TESTING_STRUCTURE.md">full structure</a> links the primary papers and explains how each informed the design. It also records what remains untested.</p><h2>First-start results</h2><p>Recovery numbers include the 57 s confirmation window. “Not confirmed” means unconfirmed by 949.5 s, before a separate input event. Both starts and every refinement are in <a href="results.json">results.json</a> and <a href="summary.csv">summary.csv</a>.</p><div class="scroll"><table><tr><th>Setting</th><th>Orbit force</th><th>Condition</th><th>Peak shear</th><th>Pattern difference</th><th>Amplitude return: fixed / feedback</th><th>Late orbit repeat</th><th>Paired rhythm bands crossed</th></tr>{''.join(rows)}</table></div><h2>What these tests establish</h2><p>{r['main_paths']} main trajectories and {r['refinement_paths']} refinement trajectories test the reduced model. Twenty equation tests and saved-data/player checks accompany the study. No physical clay or human measurements were added. The linear Burgers element has no identified yielding, damage or hydration mechanism; large synthetic shear is a stress test of its equations, not a validated prediction for your clay.</p><p>The conclusion is finite and conditional: within the tested settings and horizon, restructuring the field did not produce a noticeable paired rhythm change. There is no demonstrated movement threshold for that transition.</p><p><a href="README.md">Files and summary</a> · <a href="protocol.json">Frozen settings</a> · <a href="run_provenance.json">Run/source hashes</a></p></html>'''
    (ROOT/'report.html').write_text(text,encoding='utf-8')
    md=f'''# Hug: larger movement and a testing structure

Larger simulated movement restructures the expressed field more strongly, but no tested paired case crosses the predeclared rhythm-change bands. Stored A and event provenance remain intact. This is a synthetic stress test of reduced equations, not measured clay behavior.

[Plain-language report](report.html) · [Interactive animation](player.html) · [Animated GIF](hug-movement.gif) · [SciSpace-assisted testing structure](TESTING_STRUCTURE.md) · [Methods and reproduction](METHODS.md) · [Specification status](SPECIFICATION_STATUS.md)

![Movement sweep](figures/sweep.png)

Six primary movement settings (1, 3, 10, 30, 100, 300), three orbital conditions, two mechanical starts, and moving/fixed spatial operators give 72 main paths. Two larger settings with fixed orbital force add 24 controls. {r['refinement_paths']} finer calculations accompany the 96 main paths. Actual shear reaches {maxstrain:.2f}% in the reduced model. The largest primary amplitude effect is {maxamp:.5f}%, far below the operational 1% band; this is not a claim of physical measurement precision.

The field can change without changing the rhythm substantially. When the orbit's force is held fixed while self-motion grows, orbital repetition can change in both paired models. That is not a memory-feedback effect. All outcomes, including unconfirmed recovery windows, remain in [results.json](results.json), [summary.csv](summary.csv), and the report.

The [testing structure](TESTING_STRUCTURE.md) separates equation fidelity, numerical reliability, causal controls, rhythm outcomes and future material measurements. SciSpace discovery was checked against linked primary sources; the numerical thresholds are explicit study choices. The preceding surrogate stays fixed across the sweep; it is not the unmodified corpus system. The [specification register](SPECIFICATION_STATUS.md) identifies the changed source law, added relaxation and pair exchange, separate Burgers mechanics, and missing full-field inputs.

Twenty unit tests cover source fidelity, scaling symmetry, conservative transport, exact lower-half exclusion and diagnostics. [Saved checks](verify_saved.py) recompute mechanics and retained inputs; [player checks](check_player.cjs) exercise offline controls and finite coordinates, not browser layout. Full double-precision trajectories are reproducible; compact primary data and refinement audits are published. See [run provenance](run_provenance.json), [protocol](protocol.json), and [hash manifest](manifest_sha256.json).

Animation shape uses actual shear, gain ×1. Colors show a magnified difference from fixed geometry, on a common scale; no history is erased. The animation's closure is a drawing property. Linear Burgers coefficients are uncalibrated and do not establish finite-strain clay validity, hydration or fracture. No human/adoption data set coefficients. This updates repository files, not a website deployment. The [previous smaller-motion study](../hug-memory-feedback/README.md) is preserved.
'''
    (ROOT/'README.md').write_text(md,encoding='utf-8')

def main():
    p=protocol();r=json.loads((ROOT/'results.json').read_text());plots(p,r);build_animation(p,r);report(p,r);print('Rendered figures, comparison GIF, player data and report.')
if __name__=='__main__':main()
