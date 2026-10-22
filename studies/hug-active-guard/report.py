"""Scientific plots and saved-trajectory animation; never integrates new cases."""
import argparse,base64,hashlib,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from PIL import Image
from model import ROOT,LABELS,protocol,cases
from hug_orbits import outline

OLD='#7b8492';NEW='#007d7e';FROZEN='#b76a36';BG='#faf9f5'

def row(d,m,c):return next(x for x in d['summary'] if x['model']==m and x['condition']==c)
def index(rows,m,c,s=0):return next(i for i,x in enumerate(rows) if x==dict(model=m,condition=c,start=s))

def figures(d,t,state):
    p=d['protocol'];rows=d['cases'];out=ROOT/'figures';out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','savefig.facecolor':'white'})
    mask=t>=p['horizon_s']-3*p['orbit_period_s'];tt=t[mask]
    fig,axes=plt.subplots(2,3,figsize=(12.6,6.8),layout='constrained')
    for col,c in enumerate([0,1,3]):
        for name,color,ls in [('old',OLD,'--'),('directional',NEW,'-')]:
            z=state[mask,index(rows,name,c)]
            axes[0,col].plot(tt,z[:,0]*.1,color=color,ls=ls,lw=1.6,label='Old' if name=='old' else 'Updated')
            axes[1,col].plot(z[:,0]*.1,z[:,1]*.1,color=color,ls=ls,lw=1.6)
        axes[0,col].set(title=p['conditions'][c]['name'],xlabel='Simulation time (s)',ylabel='Displacement (mm)',ylim=(-.27,.27))
        axes[0,col].xaxis.set_major_locator(MaxNLocator(4))
        axes[1,col].set(xlabel='Displacement (mm)',ylabel='Velocity (mm/s)',xlim=(-.27,.27),ylim=(-.6,.6))
        for ax in axes[:,col]:ax.grid(alpha=.13)
    axes[0,0].legend(frameon=False,ncol=2);fig.suptitle('The updated Hug keeps its rhythm with a smaller swing\nSame forcing, material and active energy source; added evolving resistance',fontsize=14)
    fig.savefig(out/'old-new-rhythm.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12.4,4.8),layout='constrained',gridspec_kw={'width_ratios':[1.5,1]})
    x=np.arange(8);width=.24
    for j,(name,color,label) in enumerate([('old',OLD,'Old'),('frozen',FROZEN,'Added resistance, frozen guards'),('directional',NEW,'Updated evolving guards')]):
        axes[0].bar(x+(j-1)*width,[row(d,name,c)['half_amplitude_mm'] for c in range(8)],width=width,color=color,label=label)
    axes[0].set_xticks(x,[c['name'] for c in p['conditions']],rotation=32,ha='right')
    axes[0].set(ylabel='Late displacement half-range (mm)',title='Added resistance and adaptation both matter',ylim=(0,.34));axes[0].legend(frameon=False,fontsize=8,loc='upper right')
    names=p['models'];values=[row(d,m,0)['half_amplitude_mm'] for m in names]
    labels=['Old','Directional','B to A stronger','A to B stronger','Shared','Frozen','Strain feedback off','Active source off']
    bars=axes[1].barh(labels,values,color=[OLD]+[NEW]*7);axes[1].invert_yaxis();axes[1].bar_label(bars,fmt='%.3f',padding=3,fontsize=9)
    axes[1].set(xlim=(0,.235),xlabel='No-orbit half-range (mm)',title='No orbit: energy-off control settles')
    fig.savefig(out/'amplitude-controls.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,6.7),layout='constrained')
    j=index(rows,'directional',3);z=state[mask,j]
    axes[0,0].plot(tt,z[:,6],label='A receives B',color=NEW);axes[0,0].plot(tt,z[:,7],label='B receives A',color=FROZEN,ls='--');axes[0,0].set(title='Elara: guards keep evolving',ylabel='Transmitted fraction',xlabel='Simulation time (s)',ylim=(0,1));axes[0,0].legend(frameon=False)
    axes[0,1].plot(tt,z[:,4],label='A',color=NEW);axes[0,1].plot(tt,z[:,5],label='B',color=FROZEN,ls='--');axes[0,1].set(title='Internal participants retain different states',ylabel='Abstract state',xlabel='Simulation time (s)');axes[0,1].legend(frameon=False)
    for m,color,ls in [('old',OLD,'--'),('directional',NEW,'-')]:
        err=[row(d,m,c)['repeat_error'] for c in range(1,8)]
        axes[1,0].plot(range(7),err,'o',ls=ls,color=color,label='Old' if m=='old' else 'Updated')
    axes[1,0].axhline(p['gates']['repeat_error'],ls=':',color='#333333',label='Repeat tolerance')
    axes[1,0].set_xticks(range(7),[c['name'] for c in p['conditions'][1:]],rotation=25,ha='right');axes[1,0].set(yscale='log',ylim=(1e-9,3e-4),ylabel='Full-state repeat error (scaled)',title='All seven orbital inputs pass');axes[1,0].legend(frameon=False,fontsize=8)
    a=state[mask,index(rows,'directional',3),0]*.1;b=state[mask,index(rows,'shared',3),0]*.1
    axes[1,1].plot(tt,a,color=NEW,label='Directional');axes[1,1].plot(tt,b,color=FROZEN,ls='--',label='Shared');axes[1,1].set(title='Shared and directional shapes coincide here',xlabel='Simulation time (s)',ylabel='Displacement (mm)');axes[1,1].legend(frameon=False)
    fig.suptitle('A changing guard is not the same as a visibly different outline',fontsize=14)
    for ax in [axes[0,0],axes[0,1],axes[1,1]]:ax.xaxis.set_major_locator(MaxNLocator(4))
    fig.savefig(out/'guard-diagnostics.png',dpi=150);plt.close(fig)

def animation(d,t,state):
    p=d['protocol'];N=229;starts=[0,p['horizon_s']-22.8];blocks=[]
    for start in starts:
        tt=start+np.arange(N)*.1
        vals=np.empty((len(d['cases']),N,3),dtype='<f4')
        for j in range(len(d['cases'])):
            vals[j,:,0]=np.interp(tt,t,state[:,j,0])*.1
            vals[j,:,1]=np.interp(tt,t,state[:,j,6]);vals[j,:,2]=np.interp(tt,t,state[:,j,7])
        blocks.append(vals)
    packed=np.stack(blocks)
    data=dict(format='little-endian float32 base64',layout=['clip','case','sample','channel'],channels=['q_mm','g_AB','g_BA'],shape=list(packed.shape),values=base64.b64encode(packed.tobytes()).decode(),clips=[dict(label='Early response',start=starts[0]),dict(label='Late settled response',start=starts[1])],sample_s=.1,duration_s=22.8,period_s=p['orbit_period_s'],conditions=p['conditions'],models=p['models'],labels=LABELS,cases=d['cases'],summary=d['summary'],outline=outline(0),magnification=150,source_sha256=hashlib.sha256((ROOT/'results.json').read_bytes()).hexdigest())
    content=json.dumps(data,separators=(',',':'))
    (ROOT/'animation.json').write_text(content+'\n',encoding='utf-8')
    html=(ROOT/'player-template.html').read_text(encoding='utf-8').replace('GUARD_DATA_PLACEHOLDER',content)
    (ROOT/'player.html').write_text(html,encoding='utf-8');return data,packed

def gif(d,data,packed,out):
    out.mkdir(exist_ok=True,parents=True);arms=[np.array(x) for x in data['outline']];rows=d['cases'];frames=[]
    fig,axes=plt.subplots(2,3,figsize=(10.5,6.1),dpi=90,gridspec_kw={'height_ratios':[1.5,1]})
    fig.subplots_adjust(left=.07,right=.98,top=.81,bottom=.14,wspace=.32,hspace=.18)
    fig.suptitle('Old and updated Hug · saved synthetic motion',fontsize=16,y=.97)
    caption=fig.text(.5,.9,'',ha='center',fontsize=10)
    fig.text(.5,.04,'Dashed gray: old   |   Teal: updated   ·   Shape deformation magnified ×150\nOrbit force is prescribed; outline closure is a display property.',ha='center',fontsize=9)
    lines=[];cursors=[];tt=data['clips'][1]['start']+np.arange(data['shape'][2])*.1
    for col,c in enumerate([0,1,3]):
        ax=axes[0,col];ax.set(xlim=(-1.6,1.6),ylim=(-1.3,1.3),aspect='equal');ax.axis('off')
        ax.set_title(data['conditions'][c]['name']+'\n'+('Stable autonomous rhythm' if c==0 else 'Full-state orbital repeat'),fontsize=11)
        current=[]
        for m,color,ls in [('old',OLD,'--'),('directional',NEW,'-')]:
            for arm in arms:current.append((ax.plot([],[],color=color,ls=ls,lw=2)[0],arm,m,c))
            vals=packed[1,index(rows,m,c),:,0];axes[1,col].plot(tt,vals,color=color,ls=ls,lw=1.2)
        lines.extend(current);axes[1,col].set(xlim=(tt[0],tt[-1]),ylim=(-.27,.27),xlabel='Simulation time (s)',ylabel='q (mm)');axes[1,col].tick_params(axis='x',labelsize=8)
        cursors.append(axes[1,col].axvline(tt[0],color='#343a40',lw=.8))
    for n,f in enumerate(np.linspace(0,len(tt)-1,161)):
        lo=int(f);hi=min(lo+1,len(tt)-1);a=f-lo
        for line,arm,m,c in lines:
            vals=packed[1,index(rows,m,c),:,0];q=(1-a)*vals[lo]+a*vals[hi]
            line.set_data(arm[:,0]+data['magnification']*q/100*arm[:,1],arm[:,1])
        now=tt[0]+f*.1
        for cursor in cursors:cursor.set_xdata([now,now])
        caption.set_text(f'Simulation time {now:.2f} s · both models shown on the same clock')
        fig.canvas.draw();im=Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:,:,:3].copy())
        if n in [0,80,160]:im.save(out/f'frame-{n}.png')
        frames.append(im)
    frames[0].save(out/'old-updated-hug.gif',save_all=True,append_images=frames[1:],duration=100,optimize=False,disposal=2)
    plt.close(fig)

def report(d):
    p=d['protocol'];old=row(d,'old',0);new=row(d,'directional',0);frozen=row(d,'frozen',0)
    ratio=100*(new['half_amplitude_mm']/old['half_amplitude_mm']-1);adapt=100*(new['half_amplitude_mm']/frozen['half_amplitude_mm']-1)
    table=''.join(f"<tr><td>{c['name']}</td><td>{row(d,'old',j)['half_amplitude_mm']:.6f}</td><td>{row(d,'directional',j)['half_amplitude_mm']:.6f}</td><td>{100*(row(d,'directional',j)['half_amplitude_mm']/row(d,'old',j)['half_amplitude_mm']-1):+.1f}%</td><td>{'Stable cycle' if j==0 else 'Orbital repeat'}</td></tr>" for j,c in enumerate(p['conditions']))
    text=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hug: old and updated equations</title><style>body{{font:17px/1.65 system-ui,sans-serif;background:{BG};color:#23313b;margin:0}}main{{max-width:1080px;margin:auto;padding:35px 24px}}h1{{font-size:2.3rem;line-height:1.15}}h2{{margin-top:2rem}}a{{color:#006d74}}img{{width:100%;height:auto;background:white;border:1px solid #ddd;border-radius:8px}}.table{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:15px}}td,th{{padding:9px;text-align:left;border-bottom:1px solid #d9dddf}}.note{{padding:15px 20px;background:#e9f1ef;border-left:4px solid {NEW}}}button,.button{{display:inline-block;padding:10px 18px;border:1px solid #007d7e;border-radius:5px;text-decoration:none}}small{{font-size:14px}}</style></head><body><main>
<p><a href="../dynamics-fractals-sims/report.html#hug-sync">Earlier Hug study</a> / Updated comparison</p>
<p><strong>Recovery follow-up completed:</strong> <a href="../hug-guard-sync/report.html">Compare old and updated loss/recovery times</a> · <a href="../hug-guard-sync/player.html">Play the stiffness-switch comparison</a></p>
<h1>The rhythm remains.<br>The swing becomes smaller.</h1>
<p>The updated evolving guards preserve the synthetic Hug's stable autonomous rhythm and its orbital repetition in all seven forced conditions. The no-orbit displacement half-range falls by <strong>{abs(ratio):.1f}%</strong>. All declared numerical checks pass.</p>
<p><a class="button" href="player.html">Play old and updated Hug</a> &nbsp; <a href="METHODS.md">Equations and full methods</a> &nbsp; <a href="results.json">Numerical results</a></p>
<p class="note"><strong>What was tested:</strong> the old clay oscillator plus two abstract participant states and continuously evolving directional guards. The optional resistance loop is represented by a damper. This is an explicit reduced coupling choice, not a full fluid, contact, rupture or measured-clay model.</p>
<h2>Without an orbit, then with circular and eccentric inputs</h2>
<img src="figures/old-new-rhythm.png" alt="Old and updated displacement and phase plots for no orbit, circular forcing and Elara forcing">
<p>Without an orbit, the old period is <strong>{d['cycles'][0]['period_s']:.6f} s</strong>; the primary updated period is <strong>{next(x['period_s'] for x in d['cycles'] if x['model']=='directional'):.6f} s</strong>. Both have locally attracting cycles verified by shooting and Floquet tests. Under orbital forcing, the mean motion period is about 2.85 s, with the entire state repeating after the 5.7 s orbit. Nonzero eccentricity can make consecutive within-orbit motions unequal.</p>
<div class="table"><table><thead><tr><th>Input</th><th>Old half-range (mm)</th><th>Updated half-range (mm)</th><th>Change</th><th>Outcome in both</th></tr></thead><tbody>{table}</tbody></table></div>
<p>Half-ranges are measured over the last 456 simulation seconds from start 1; both starts pass the full-state agreement tests. Moon names select eccentricity. All orbital periods and force RMS values are held fixed; these are not actual lunar loads.</p>
<h2>What caused the change?</h2><img src="figures/amplitude-controls.png" alt="Amplitude comparisons between old, frozen and evolving guards, plus all no-orbit controls">
<p>Adding fixed resistance already reduces the no-orbit swing from {old['half_amplitude_mm']:.6f} to {frozen['half_amplitude_mm']:.6f} mm. Allowing the guard to evolve reduces it by a further {abs(adapt):.1f}% relative to that frozen control. Turning off the active energy source removes the autonomous rhythm; orbital forcing can still produce motion. The energy-off switch removes both feedback gain and nonlinear saturation, so forced amplitude need not always be smaller than in the active model.</p>
<h2>The hidden states matter</h2><img src="figures/guard-diagnostics.png" alt="Evolving directed guards and participant states, full-state repeat errors and a shared-guard motion control">
<p>With equal weights, the shared and directional rules give the same mechanical motion here: the displacement, participant difference and guard sum form the same closed subsystem from matched starting values. The directional guards themselves differ. Thus these results do not show that directional asymmetry caused the smaller swing. The unequal-weight comparisons produce small additional changes, retained in the results and player.</p>
<h2>Accuracy and limits</h2><p>128 trajectories at two accuracy settings; 52 independent physical-unit Radau segments; six autonomous cycle stability calculations. Maximum saved full-state difference: {d['maximum_saved_path_difference']:.3g}, below 0.0002. Maximum energy residual: {d['maximum_energy_residual']:.3g}, below 0.00001. Maximum independent-solver difference: {d['maximum_independent_error']:.3g}, below 0.00002. Both accuracy settings produce identical classifications.</p>
<p>This experiment does not repeat the earlier stiffness-switch loss/recovery protocol, so it does not establish a new circular-versus-Elara recovery-time ordering. It tests one damper strength and one guard time mapping, two starts, and a finite horizon. The parameter choices and material remain synthetic. The outline animation preserves closure through its drawing map.</p>
<p><a href="protocol.json">Frozen comparison</a> · <a href="freeze.json">Pre-run source freeze</a> · <a href="test_model.py">Equation tests</a> · <a href="test_analysis.py">Diagnostic tests</a> · <a href="animation.json">Saved animation samples</a></p>
</main></body></html>'''
    (ROOT/'report.html').write_text(text,encoding='utf-8')
    md=f'''# Hug with evolving guards: old and updated equations

The updated synthetic Hug retains a locally attracting autonomous rhythm and full-state orbital repetition for circular and all six eccentric inputs. Its no-orbit displacement half-range is {abs(ratio):.1f}% smaller. This is a declared reduced mechanical coupling of the updated participant/guard equations, not a unique derivation or full Navier-Stokes model.

[Illustrated report](report.html) · [Offline animation](player.html) · [Equations, controls and reproduction](METHODS.md) · [Results](results.json)

**Recovery follow-up completed:** [old and updated stiffness-switch recovery times](../hug-guard-sync/README.md), with a [live comparison animation](../hug-guard-sync/player.html).

![Old and updated motion](figures/old-new-rhythm.png)

| Input | Old half-range (mm) | Updated half-range (mm) | Change |
| --- | ---: | ---: | ---: |
'''
    for j,c in enumerate(p['conditions']):
        a=row(d,'old',j)['half_amplitude_mm'];b=row(d,'directional',j)['half_amplitude_mm'];md+=f"| {c['name']} | {a:.6f} | {b:.6f} | {100*(b/a-1):+.1f}% |\n"
    md+=f'''
No-orbit periods are {d['cycles'][0]['period_s']:.6f} s (old) and {next(x['period_s'] for x in d['cycles'] if x['model']=='directional'):.6f} s (updated). These are simulation seconds, not measured clay or real orbital times.

The frozen control shows that adding resistance already reduces amplitude; evolving guards reduce it further. Shared and directional guards with equal weights yield the same mechanics here by an exact closed-subsystem identity. This is not evidence that asymmetry itself caused the amplitude reduction. Turning off active gain and saturation removes the autonomous rhythm while allowing an externally forced response.

**Verification:** 128 trajectories at two accuracy settings, 52 independent Radau segments and six cycle stability checks. All saved numerical gates pass, with identical classifications. No old scientific results were replaced. The earlier stiffness-switch recovery delays are not recalculated in this experiment.

**Scope:** one-mode clay mechanics plus abstract internal participants and evolving guards. The added resistance, guard coefficients and time mapping are declared synthetic assumptions. No physical measurements, moving-boundary test, rupture law or orbital backreaction is included. The drawing shear preserves outline closure by construction.

Keep this folder beside `dynamics-fractals-sims`; it imports that study's unchanged forcing and outline. See [methods](METHODS.md) for reproduction. Large raw caches are local; compact diagnostics, both-resolution summaries, animation samples and sources are published.
'''
    (ROOT/'README.md').write_text(md,encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache',type=Path,required=True);ap.add_argument('--gif-dir',type=Path);a=ap.parse_args()
    d=json.loads((ROOT/'results.json').read_text());assert d['numerical_status']=='passed'
    with np.load(a.cache/'main.npz') as f:t=f['time'];state=f['state']
    figures(d,t,state);data,packed=animation(d,t,state);report(d)
    if a.gif_dir:gif(d,data,packed,a.gif_dir)
    print(json.dumps(dict(figures=3,animation_shape=data['shape'],report=str(ROOT/'report.html'))))
if __name__=='__main__':main()
