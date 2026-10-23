import base64,html,json
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import findfont
from PIL import Image,ImageDraw,ImageFont
from model import protocol
ROOT=Path(__file__).resolve().parent
TEAL='#087f8c';GRAY='#697983';BG='#faf9f5';INK='#193f46'
def plots(p,r,d):
    figdir=ROOT/'figures';figdir.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.facecolor':BG,'figure.facecolor':BG})
    t=d['time'];amp=d['amplitude'];fig,axs=plt.subplots(3,1,figsize=(10.5,7.8),sharex=True,constrained_layout=True)
    for c,ax in enumerate(axs):
        j=c*2;ax.plot(t,amp[:,j],color=TEAL,lw=2.7,label='Movement feeds back into the field')
        ax.plot(t,amp[:,j+6],color=GRAY,lw=1.4,ls='--',label='Previous fixed spatial calculations')
        ax.axvspan(480,720,color=GRAY,alpha=.15);ax.axvspan(950,970,color='#cba35b',alpha=.2)
        ax.set_title(p['conditions'][c]['name'],loc='left');ax.set_ylabel('Movement size (mm)');ax.grid(alpha=.15)
    axs[0].legend(loc='upper right',fontsize=8);axs[-1].set_xlabel('Time through the experiment (s)')
    fig.suptitle('The rhythm becomes quiet, then returns\nThe new and previous curves almost overlap',fontsize=16)
    fig.savefig(figdir/'rhythm.png',dpi=150);plt.close(fig)
    delta=d['field_delta'];fig,axs=plt.subplots(3,2,figsize=(12,7.8),constrained_layout=True)
    # Short windows avoid visually aliasing hundreds of oscillations into one image.
    uniform=np.abs(t*2-np.round(t*2))<1e-8;limit=12
    for c in range(3):
        for col,(a,b,label) in enumerate([(420,450,'moving'),(650,680,'braked')]):
            ax=axs[c,col];ii=np.flatnonzero(uniform&(t>=a)&(t<=b))
            im=ax.imshow(delta[ii,c*2].T*1e6,origin='lower',aspect='auto',extent=[a,b,0,360],vmin=-limit,vmax=limit,cmap='PuOr_r',interpolation='nearest')
            ax.set_title(p['conditions'][c]['name']+' · '+label,loc='left',fontsize=10);ax.set_yticks([0,90,180,270,360],['Right','Top','Left','Bottom','Right'] if col==0 else [])
            if c==2:ax.set_xlabel('Simulation time (s)')
    fig.colorbar(im,ax=axs.ravel().tolist(),label='Local change from previous model (millionths of S)',shrink=.75)
    fig.suptitle('Movement changes where influence is expressed\nColors enlarge a tiny redistribution; compare moving and braked intervals',fontsize=14)
    fig.savefig(figdir/'redistribution.png',dpi=150);plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(12,3.9),constrained_layout=True)
    axs[0].plot(t,d['A'].sum(axis=1),color=TEAL,lw=2);axs[0].set_title('History is kept');axs[0].set_ylabel('Accumulated input A')
    axs[1].plot(t,d['field_mean'][:,0],color=TEAL,lw=3,label='New');axs[1].plot(t,d['field_mean'][:,6],color=GRAY,ls='--',label='Previous');axs[1].set_title('Same overall expression');axs[1].set_ylabel('Mean expressed field S');axs[1].legend(fontsize=8)
    for c,col in enumerate([TEAL,'#9751a1','#c46c2e']):
        power=np.mean(delta[:,c*2].astype(float)**2,axis=1);smooth=np.array([np.sqrt(np.mean(power[np.searchsorted(t,x-5.7):i+1])) for i,x in enumerate(t)])
        axs[2].plot(t,smooth*1e6,label=p['conditions'][c]['name'],color=col,lw=1.2)
    axs[2].set_title('Different spatial pattern\n(short-window average)');axs[2].set_ylabel('Pattern difference (millionths of S)');axs[2].legend(fontsize=7)
    for ax in axs:ax.set_xlabel('Time (s)');ax.axvspan(480,720,color=GRAY,alpha=.12);ax.grid(alpha=.15)
    fig.suptitle('Preserving the record does not require freezing the pattern',fontsize=16)
    fig.savefig(figdir/'history-and-pattern.png',dpi=150);plt.close(fig)

def animation(p,r,d):
    clips=[('Before braking',420,450),('Quiet interval',650,680),('Drive restored',720,750),('Rhythm returning',900,930),('New neighbor input',945,975),('Late outcome',1740,1770)]
    tt=np.concatenate([np.linspace(a,b,151) for _,a,b in clips]);t=d['time']
    q=CubicSpline(t,d['mechanics'][:,:12,0],axis=0)(tt)*p['mechanics']['scale_m']*1000
    old=CubicSpline(t,d['field_frozen'].astype(float),axis=0)(tt);delta=CubicSpline(t,d['field_delta'].astype(float),axis=0)(tt)
    amp=np.stack([np.interp(tt,t,d['amplitude'][:,j]) for j in range(6)],axis=1)
    A=np.stack([np.interp(tt,t,d['A'][:,k]) for k in range(3)],axis=1).sum(axis=1)
    oi=np.maximum(np.searchsorted(d['orbital_time'],tt,side='right')-1,0);rep=np.nan_to_num(d['repeat'][oi,:6],nan=-1)
    def pack(v):return base64.b64encode(np.asarray(v,dtype='<f4').tobytes()).decode()
    data=dict(times=tt.tolist(),frames=len(tt),cells=32,paths=12,q=pack(q),old=pack(old),delta=pack(delta),amplitude=pack(amp),A=pack(A),repeat=pack(rep),baseline=[x['baseline_half_amplitude_mm'] for x in r['paths'][:6]],conditions=p['conditions'],period=p['orbit_period_s'],deltaColorLimit=12e-6,fieldColorLimit=.7,clips=[dict(label=label,start=i*151,count=151) for i,(label,_,_) in enumerate(clips)])
    (ROOT/'animation-data.js').write_bytes(('const HUGDATA='+json.dumps(data,separators=(',',':'))+';\n').encode())
    cmap=plt.get_cmap('PuOr_r');fontpath=findfont('DejaVu Sans');title=ImageFont.truetype(fontpath,25);font=ImageFont.truetype(fontpath,17);small=ImageFont.truetype(fontpath,13)
    frames=[]
    for ci in [0,1,2,3,5]:
        for fi in range(0,151,3):
            k=ci*151+fi;time=tt[k];im=Image.new('RGB',(1050,530),BG);draw=ImageDraw.Draw(im)
            draw.text((24,16),'Movement reshapes the field. The record stays.',font=title,fill=INK)
            draw.text((24,53),f'{clips[ci][0]} | {time:.1f} simulation seconds',font=font,fill=INK)
            draw.text((24,81),'Synthetic results | shape x150 | colors enlarge the tiny change from the previous model',font=small,fill=GRAY)
            for c in range(3):
                j=c*2;cx=175+c*350;cy=260;draw.text((c*350+24,120),['No orbit','Circular orbit','Eccentric orbit'][c],font=font,fill=INK)
                th=np.linspace(0,2*np.pi,257);shear=150*q[k,j]/1000/.1;xx=cx+92*(np.cos(th)+shear*np.sin(th));yy=cy-92*np.sin(th)
                draw.line(list(zip(xx,yy)),fill='#9aaba6',width=10)
                # Every segment's color belongs to the same material cell throughout.
                for n in range(256):
                    theta=2*np.pi*(n+.5)/256;cell=int(theta/(2*np.pi)*32)%32;v=delta[k,j,cell]
                    color=tuple(int(255*x) for x in cmap(np.clip(.5+.5*v/data['deltaColorLimit'],0,1))[:3]);draw.line([(xx[n],yy[n]),(xx[n+1],yy[n+1])],fill=color,width=7)
                draw.line([(cx-120,cy),(cx+120,cy)],fill='#ccd5d2',width=1)
                if 480<=time<720:status='Drive off + brake'
                elif c==0:status='Autonomous motion; no orbit'
                elif time<783 and time>=720:status='Assessing orbital repetition'
                else:status='Orbital repeat confirmed' if rep[k,j]>=0 and rep[k,j]<.01 else 'No orbital repeat confirmation'
                draw.text((c*350+24,382),status,font=small,fill=INK)
                draw.text((c*350+24,407),f'Stored input: {A[k]:.2f} | no reset',font=small,fill=INK)
                draw.text((c*350+24,432),f'Pattern change: {np.sqrt(np.mean(delta[k,j]**2))*1e6:.2f} millionths',font=small,fill=GRAY)
            for x in range(180):draw.line([(435+x,473),(435+x,485)],fill=tuple(int(255*v) for v in cmap(x/179)[:3]))
            draw.text((24,470),'Purple: less influence here',font=small,fill=INK);draw.text((650,470),'Orange: more influence here',font=small,fill=INK)
            draw.text((24,506),'White: similar expression to before, not erased history. Recovery times unchanged. Clips skip waiting time.',font=small,fill=GRAY)
            frames.append(im)
    frames[0].save(ROOT/'hug-feedback.gif',save_all=True,append_images=frames[1:],duration=80,loop=0,optimize=True)
    return data

def reports(p,r):
    primary=[x for x in r['comparisons'] if x['history']==0];esc=html.escape
    def time(x):return 'Not applicable' if x is None else f'{x:.1f} s'
    table=''.join(f'<tr><td>{esc(p["conditions"][x["condition"]]["name"])}</td><td>{time(x["old_amplitude_delay"])} / {time(x["new_amplitude_delay"])}</td><td>{time(x["old_repeat_delay"])} / {time(x["new_repeat_delay"])}</td><td>{x["tail_field_relative_rms"]*1e6:.2f} parts per million</td></tr>' for x in primary)
    message='The clay now changes the spatial expression of history, while the accumulated record stays intact. In these tests the change is very small, and the rhythm recovers at the same measured times as before.'
    body=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hug: movement restructures expression</title><style>body{{font:17px/1.6 system-ui;max-width:1100px;margin:40px auto;padding:0 24px;color:{INK};background:{BG}}}h1{{font-size:38px;line-height:1.15}}h2{{font-size:25px;margin-top:34px}}a{{color:{TEAL}}}img{{max-width:100%;height:auto}}.lead{{font-size:22px}}.story{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}.card,details{{background:white;border:1px solid #d5dfda;border-radius:12px;padding:20px}}.note{{background:#e6eeeb;border-left:4px solid {TEAL};padding:18px}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #d5dfda}}.scroll{{overflow:auto}}summary{{cursor:pointer;font-weight:bold}}@media(max-width:700px){{.story{{grid-template-columns:1fr}}h1{{font-size:30px}}}}</style></head><body>
    <p><a href="../hug-memory-continuity/report.html">Earlier retained-history model</a> · <a href="player.html">Play the new animation</a></p>
    <h1>The record stays.<br>Movement can reshape its expression.</h1><p class="lead">{message}</p>
    <div class="story"><div class="card"><h2>History stays</h2><p>Braking, restarting and changing orbit do not erase the recorded inputs. New events are added to the record.</p></div><div class="card"><h2>Influence moves</h2><p>The clay's real deformation changes how the field spreads and how its gradients push back on the clay.</p></div><div class="card"><h2>The effect is small</h2><p>The spatial pattern changes subtly. The no-orbit, circular and eccentric recovery results remain effectively the same at this resolution.</p></div></div>
    <p class="note">Read left to right as time passes. A higher curve means larger movement. The gray band is deliberate braking. The new and old curves almost overlap because the feedback has little effect on rhythm at these small strains.</p>
    <img src="figures/rhythm.png" alt="Three orbit conditions become quiet during braking and regain movement; new and previous amplitude curves nearly overlap.">
    <h2>Where the influence changes</h2><p>Purple means less influence at that location than in the previous model; orange means more. White means similar expression to the previous model, with the stored history still present. These colors enlarge changes measured in millionths of the field unit. They do not mean a large physical change or a loss of the recorded history.</p>
    <img src="figures/redistribution.png" alt="Color maps show tiny positive and negative spatial changes caused by deformation in three orbit conditions.">
    <p><a href="player.html">Open the interactive animation →</a> · <a href="hug-feedback.gif">Short animated comparison</a></p>
    <img src="figures/history-and-pattern.png" alt="Stored input survives braking; the mean field agrees with the previous model even while the spatial pattern differs.">
    <h2>What changed in the equations</h2><p>Your transport term carries the field with the material. This version also updates diffusion and physical gradients as the material deforms. That completes a two-way connection: clay movement changes the expressed field, and the field changes force on the clay. It introduces no fitted restructuring multiplier.</p>
    <p>The existing source cap, expression relaxation and upper-only paired exchange remain declared extensions. This is an angular-field and single-shear-mode reduction; it does not resolve full fluid motion, contact, fracture or hydration. The record is preserved by its stated law. The tests check the law's consequences rather than establish how human memory works.</p>
    <details><summary>Numbers, controls and checks</summary><div class="scroll"><table><tr><th>Condition</th><th>Amplitude return: previous / new</th><th>Orbital repeat: previous / new</th><th>Late relative pattern change</th></tr>{table}</table></div>
    <p>Delays are after release. Amplitude uses a trailing 57 s window, so 57 s is its earliest eligible confirmation. Results are checked through 949.5 s before the next input. Orbital repetition has a separate ten-comparison window and tolerance .01; no-orbit motion has no synchronization label.</p>
    <p>30 main paths and 72 refinement paths; two starts. All tested confirmation times agree on refinement. The 64-to-128-cell paired field discrepancy is {r['refinements']['spatial']['maximum_paired_field_difference_to_64']:.3g}, while the new spatial effect reaches about 1e-5. The tighter-time paired field discrepancy is {max(x['max_field_contrast_difference'] for x in r['refinements']['timefine']['paired_field_refinement']):.3g}. Absolute field discretization error is larger than the small effect, so matched new-minus-old differences are checked separately.</p>
    <p>Stored-input error: {r['checks']['retained_input_error']:.3g}. Maximum difference in field means: {r['checks']['maximum_mean_difference']:.3g}. Main normalized energy residual: {r['checks']['max_energy_residual_scaled']:.3g}. Physical shear never exceeds {100*r['checks']['maximum_physical_shear']:.3f}%. The animation's shape magnification never enters the dynamics.</p>
    <p>The diffusion-only control reproduces the spatial redistribution. Changing only the force gradient leaves S unchanged; it accounts for most of the already tiny mechanical difference. Controls and unrounded values are retained in <a href="results.json">results.json</a>.</p></details>
    <h2>Inspect or reproduce</h2><p><a href="METHODS.md">Equation derivation and limitations</a> · <a href="protocol.json">Protocol</a> · <a href="model.py">Feedback code</a> · <a href="summary.csv">All path summaries</a> · <a href="plot_data.npz">Saved numerical data</a> · <a href="run_provenance.json">Run provenance</a></p><p>All material values, inputs and family-history analogies remain synthetic. No new physical clay or human measurements were collected. Adoption references remain separate from the equations. Repository publication does not deploy a website.</p></body></html>'''
    (ROOT/'report.html').write_bytes(body.encode())
    rows='\n'.join(f'| {p["conditions"][x["condition"]]["name"]} | {time(x["old_amplitude_delay"])} / {time(x["new_amplitude_delay"])} | {time(x["old_repeat_delay"])} / {time(x["new_repeat_delay"])} | {x["tail_field_relative_rms"]*1e6:.2f} ppm |' for x in primary)
    text=f'''# Hug: movement restructures expressed history

{message}

[Plain-language report and plots](report.html) · [Interactive animation](player.html) · [Animated GIF](hug-feedback.gif) · [Equations and reproduction](METHODS.md)

![Movement and rhythm](figures/rhythm.png)

The supplied `partial_t S + u·grad(S)` is evaluated in material coordinates. Diffusion and source-force gradients now follow the actual clay shear through its deformation tensor. Stored A and event provenance are never reset. The existing bounded-expression extensions remain explicit. This is an angular-field and single-mode mechanical reduction, not a full fluid/contact solver or human-memory measurement.

Five scenarios × three conditions × two starts = 30 main paths, with 72 refinement paths. Conditions are no orbit, circular, and synthetic eccentric forcing e=.212. There is no new tuned restructuring gain. Physical shear remains below 0.242%; its field effect is small.

| Condition | Amplitude return: previous / new | Orbital repeat: previous / new | Late relative pattern change |
|---|---|---|---|
{rows}

Delays include confirmation windows. Forced amplitude return at 57 s is the first eligible confirmation, not an exact regrowth time. All tested timing results agree on refinement. The 64-to-128-cell discrepancy in the paired field effect is {r['refinements']['spatial']['maximum_paired_field_difference_to_64']:.3g}; full differences and controls are in [results.json](results.json). No new recovery-time ordering or large physical effect is claimed.

The diffusion-only control changes the spatial pattern; the force-gradient-only control leaves S unchanged. Mean S agrees between matched cases because redistribution is conservative, even though existing sources and relaxation still change that mean over time. Retention of A follows the specified accumulation law and is checked, not discovered as a human fact.

![Where influence changes](figures/redistribution.png)

Colors enlarge differences of a few millionths; shape deformation in the animation is magnified ×150. Neither display scale enters the equations. The [saved-data checker](verify_saved.py), 25 equation tests, [offline player checks](check_player.cjs), [protocol](protocol.json), [immutable event catalog](history_ledger.json) and [source/run hashes](run_provenance.json) are included. Full trajectories can be regenerated using the documented commands.

The [previous fixed-spatial model](../hug-memory-continuity/README.md) is preserved. Biological ancestry and adoption statistics do not set model coefficients. No physical clay or human measurements were added. This update publishes repository files and does not deploy a website.
'''
    (ROOT/'README.md').write_bytes(text.encode())
def main():
    p=protocol();r=json.loads((ROOT/'results.json').read_text());d=np.load(ROOT/'plot_data.npz');plots(p,r,d);data=animation(p,r,d);reports(p,r)
    print(json.dumps(dict(animation_frames=data['frames'],gif_bytes=(ROOT/'hug-feedback.gif').stat().st_size,plots=3)))
if __name__=='__main__':main()
