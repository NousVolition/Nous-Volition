import argparse,base64,csv,html,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline
from PIL import Image,ImageDraw,ImageFont
from model import protocol,exposure_weights
ROOT=Path(__file__).resolve().parent
COLORS=['#087f8c','#c45a23','#6b7280']
def plot():
    p=protocol();r=json.loads((ROOT/'results.json').read_text());d=np.load(ROOT/'plot_data.npz');t=d['time'];a=d['amplitude'];figdir=ROOT/'figures';figdir.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'#faf9f5','axes.facecolor':'#faf9f5'})
    fig,axes=plt.subplots(3,1,figsize=(11,8.4),sharex=True,constrained_layout=True)
    for c,ax in enumerate(axes):
        for sid,label,col in [(0,'History retained',COLORS[0]),(1,'Reset control',COLORS[1]),(2,'No interruption',COLORS[2])]:
            j=sid*6+c*2;ax.plot(t,a[:,j],label=label,color=col,lw=1.6,ls='--' if sid==1 else '-')
            ax.fill_between(t,np.minimum(a[:,j],a[:,j+1]),np.maximum(a[:,j],a[:,j+1]),color=col,alpha=.1)
        ax.axvspan(480,720,color='#8896a0',alpha=.15);ax.axvspan(950,970,color='#d7b552',alpha=.23)
        ax.set_title(p['conditions'][c]['name'],loc='left');ax.set_ylabel('Half-amplitude (mm)');ax.grid(alpha=.15)
    axes[0].legend(ncol=3,loc='upper right',fontsize=9);axes[2].set_xlabel('Elapsed simulation time (s)')
    fig.suptitle('Rhythm can become quiet while history remains\nGray: drive off + brake · gold: later neighbor account',fontsize=15)
    fig.savefig(figdir/'rhythm.png',dpi=155);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(12,3.8),constrained_layout=True)
    for j,label,col in [(0,'Retained',COLORS[0]),(6,'Reset control',COLORS[1])]:
        axes[0].plot(t,d['accumulators'][:,j].sum(axis=1),color=col,label=label)
        axes[1].plot(t,d['field_rms'][:,j],color=col,label=label)
    axes[0].set_ylabel('Sum of three input accumulators');axes[1].set_ylabel('Expressed field S, RMS')
    for ax in axes[:2]:ax.axvspan(480,720,color='gray',alpha=.12);ax.set_xlabel('Time (s)');ax.grid(alpha=.15)
    axes[0].set_title('Stored inputs survive braking');axes[0].legend(fontsize=9)
    axes[1].set_title('Expression changes\nindependently')
    g=np.arange(6)
    for rr,col,label in [(.55,COLORS[0],'Assumed transfer 0.55'),(.9,COLORS[1],'Sensitivity 0.90')]:
        axes[2].plot(g,rr**g,'o-',color=col,label=label)
    axes[2].set(xlabel='Generation distance',ylabel='Origin-route weight before budget',title='Partial influence;\nprovenance preserved',xticks=g,ylim=(0,1.05));axes[2].legend(fontsize=8);axes[2].grid(alpha=.15)
    fig.suptitle('Synthetic memory mechanisms · no human inheritance rates fitted',fontsize=14)
    fig.savefig(figdir/'memory.png',dpi=155);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(12,4),constrained_layout=True)
    cases=[s['id'] for s in p['scenarios'] if s['pause']];labels=[{'retained':'Retained, G2','erased_control':'Reset, G2','origin':'Origin, G0','generation1':'Account, G1','generation3':'Account, G3','changed_care':'Changed care','persistent':'Stronger transfer','opposing':'Opposing exchange'}[s] for s in cases]
    for c,ax in enumerate(axes):
        for i,sid in enumerate(cases):
            rr=[v for v in r['results'] if v['scenario']==sid and v['condition']==c];vals=[x['amplitude_recovery_delay_s'] for x in rr]
            finite=[x for x in vals if x is not None]
            if finite:ax.scatter(finite,[i]*len(finite),s=32,c=COLORS[0]);ax.plot([min(finite),max(finite)],[i,i],color=COLORS[0])
            if len(finite)<len(vals):ax.scatter([229.5],[i],marker='>',c=COLORS[1],s=40)
        ax.set_title(p['conditions'][c]['name']);ax.set_xlim(0,245);ax.set_yticks(np.arange(len(cases)),labels if c==0 else []);ax.invert_yaxis();ax.grid(axis='x',alpha=.18);ax.set_xlabel('Amplitude confirmation delay (s)')
    fig.suptitle('Return to 80% of baseline amplitude · two mechanical starts\nArrow: not confirmed before the separate reminder at 950 s',fontsize=14)
    fig.savefig(figdir/'recovery.png',dpi=155);plt.close(fig)
    refs=list(csv.DictReader((ROOT/'adoption_reference.csv').open()))
    fig,ax=plt.subplots(figsize=(9,3.4),constrained_layout=True);ax.plot([int(x['year']) for x in refs],[int(x['reported_intercountry_adoptions']) for x in refs],color='#66558f',marker='o',ms=3)
    ax.set(xlabel='Reporting year',ylabel='Intercountry adoptions in reporting set',title='Worldwide reference: HCCH/Selman receiving-state compilation\nNot a total of all worldwide adoptions; annual coverage varies')
    ax.grid(alpha=.15);fig.savefig(figdir/'adoption-reference.png',dpi=140);plt.close(fig)
    return p,r,d
def animate(p,r,d):
    clips=[('Before interruption',420,450),('Drive off + brake',480,510),('Quiet interval',650,680),('Drive restored',720,750),('Late recovery',900,930),('Neighbor reminder',945,975),('After reminder',1100,1130),('Late outcome',1740,1770)]
    tt=np.concatenate([np.linspace(a,b,151) for _,a,b in clips]);t=d['time'];q=CubicSpline(t,d['mechanics'][:,:,0],axis=0)(tt)*p['mechanics']['scale_m']*1000
    acc=np.stack([np.interp(tt,t,d['accumulators'][:,s*6].sum(axis=1)) for s in range(len(p['scenarios']))],axis=1)
    expr=np.stack([np.interp(tt,t,d['field_rms'][:,s*6]) for s in range(len(p['scenarios']))],axis=1)
    aa=np.stack([np.interp(tt,t,d['amplitude'][:,j]) for j in range(q.shape[1])],axis=1)
    # Status from completed exact orbital checkpoint; never label autonomous motion synchronized.
    ot=d['orbital_time'];re=d['repeat'];oi=np.maximum(np.searchsorted(ot,tt,side='right')-1,0);repeat=re[oi]
    def b64(x):return base64.b64encode(np.asarray(x,dtype='<f4').tobytes()).decode()
    data=dict(times=tt.tolist(),shape=list(q.shape),q=b64(q),A=b64(acc),S=b64(expr),amplitude=b64(aa),repeat=b64(np.nan_to_num(repeat,nan=-1)),conditions=p['conditions'],scenarios=[dict(id=s['id'],label=s['label'],pause=s['pause']) for s in p['scenarios']],clips=[dict(label=label,start=i*151,count=151) for i,(label,_,_) in enumerate(clips)],baselines=[x['baseline_half_amplitude_mm'] for x in r['results']],period=p['orbit_period_s'],repeatTolerance=p['diagnostics']['repeat_tolerance_scaled'],memoryBound=r['checks']['field_bound'])
    (ROOT/'animation-data.js').write_text('const HUGDATA='+json.dumps(data,separators=(',',':'),allow_nan=False)+';\n',encoding='utf-8')
    # Export a short GIF from these same saved samples; timestamps show clip jumps.
    from matplotlib.font_manager import findfont
    frames=[];fontpath=findfont('DejaVu Sans');font=ImageFont.truetype(fontpath,17);small=ImageFont.truetype(fontpath,13);title=ImageFont.truetype(fontpath,23)
    for clipidx in [0,2,3,4,7]:
        for fi in range(0,151,3):
            k=clipidx*151+fi;time=tt[k];im=Image.new('RGB',(990,450),'#faf9f5');draw=ImageDraw.Draw(im)
            draw.text((24,16),'Hug: retained history through an interrupted rhythm',fill='#153b43',font=title)
            draw.text((24,53),f'{clips[clipidx][0]} | elapsed {time:.1f} s | synthetic, shear x150',fill='#4b5563',font=font)
            for c in range(3):
                cx=165+c*330;cy=220;draw.text((c*330+22,100),['No orbit','Circular','Eccentric: e = 0.212'][c],fill='#153b43',font=font)
                for s,col in [(1,COLORS[1]),(0,COLORS[0])]:
                    shear=150*q[k,s*6+c*2]/1000/.1;th=np.linspace(0,2*np.pi,201)
                    points=list(zip(cx+83*(np.cos(th)+shear*np.sin(th)),cy+83*np.sin(th)))
                    draw.line(points,fill=col,width=3)
                j=c*2
                if 480<=time<720:state='Drive off; residual motion'
                elif c==0:state='No orbit; '+('amplitude below 80%' if aa[k,j]<.8*data['baselines'][j] else 'amplitude at least 80%')
                elif 720<=time<783 or 950<=time<1033:state='Assessing after intervention'
                else:state='1-orbit repeat confirmed' if repeat[k,j]>=0 and repeat[k,j]<.01 else 'No 1-orbit confirmation'
                draw.text((c*330+20,325),state,fill='#153b43',font=small)
                draw.text((c*330+20,353),f'Stored input: {acc[k,0]:.2f} | reset: {acc[k,1]:.2f}',fill='#4b5563',font=small)
                draw.text((c*330+20,378),f'Expression RMS: {expr[k,0]:.3f}',fill='#4b5563',font=small)
            draw.text((24,418),'Teal: history retained    Orange: reset control    Clips skip waiting time; states are never restarted.',fill='#4b5563',font=small)
            frames.append(im)
    frames[0].save(ROOT/'hug-memory.gif',save_all=True,append_images=frames[1:],duration=80,loop=0,optimize=True)
    return data
def report(p,r):
    esc=html.escape;primary=[x for x in r['results'] if x['scenario']=='retained' and x['history']==0]
    def val(x):return 'Not confirmed before reminder' if x is None else f'{x:.1f} s'
    table=''.join(f'<tr><td>{esc(p["conditions"][x["condition"]]["name"])}</td><td>{100*x["braked_min_fraction"]:.3g}%</td><td>{val(x["amplitude_recovery_delay_s"])}</td><td>{"Not applicable" if x["condition"]==0 else val(x["mechanical_repeat_confirmation_delay_s"])}</td></tr>' for x in primary)
    checks=r['checks'];ref=r['refinements'];num=''.join(f'<li>{esc(k)}: {v["paths"]} paths, {v["nodes"]} cells; maximum mechanical state difference from main {v["max_scaled_mechanical_path_difference"]:.3g}; amplitude difference {v["max_amplitude_difference_mm"]:.4g} mm.</li>' for k,v in ref.items())
    body=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hug — memory remains, expression has limits</title><style>body{{max-width:1100px;margin:40px auto;padding:0 24px;background:#faf9f5;color:#183b43;font:17px/1.6 system-ui}}h1{{font-size:36px;line-height:1.2}}h2{{margin-top:40px}}a{{color:#087f8c}}img{{width:100%;height:auto}}table{{border-collapse:collapse;width:100%;font-size:15px}}td,th{{text-align:left;padding:12px;border-bottom:1px solid #ccd5d2}}.note{{background:#e9f1ee;padding:20px;border-left:4px solid #087f8c}}code{{font-size:14px}}.scroll{{overflow:auto}}</style>
    <p><a href="../hug-guard-sync/report.html">Earlier Hug comparison</a> · <a href="player.html">Open animation</a></p><h1>Memory remains.<br>Its current expression has a limit.</h1>
    <p class="note">The new model preserves accumulated input and event provenance while limiting the expressed field. In the main cases, braking makes motion quiet without deleting history. Circular and eccentric forcing leave residual movement. These are synthetic model results, not measurements of clay, families or inherited trauma.</p>
    <p><a href="player.html">Play all three conditions together →</a> · <a href="hug-memory.gif">Short animation</a> · <a href="METHODS.md">Equations and declared changes</a> · <a href="REFERENCE.md">Worldwide adoption and ancestry references</a></p>
    <img src="figures/rhythm.png" alt="Amplitude histories under no orbit, circular and eccentric forcing, with retained, reset and no-pause controls.">
    <h2>What persists, and what changes</h2><p>Your accumulated-input equation remains. A permanent event record distinguishes direct experience from communicated family or neighbor history. The new source cap, expression relaxation and bounded pair exchange are explicit additions required for a finite limit. They do not erase the retained input. A later account is recorded as a later account, not the recipient’s own earlier experience.</p>
    <img src="figures/memory.png" alt="Stored input stays during braking while expression changes; hypothetical generation weights decrease.">
    <p>Doubling acts only in the upper reference region. Both directed terms are exactly zero below the centreline for arbitrary finite states. Lower clay can still respond through material mechanics and field diffusion. Aligning/opposing are feedback signs, not judgments about people. Reversing S alone cannot reverse the source force because the source uses gradient magnitude.</p>
    <h2>Rhythm return and orbital repetition are different</h2><p>The drive is off and braking is applied from 480 to 720 seconds. Every retained state is carried forward. Only the labeled reset control deletes working A and S at release. A neighbor reminder occurs at 950–970 seconds. The table shows the first starting history; the plots and CSV include both.</p>
    <div class="scroll"><table><tr><th>Condition</th><th>Smallest braked amplitude / baseline</th><th>80% amplitude confirmation after release</th><th>Mechanical 1-orbit repeat confirmation</th></tr>{table}</table></div>
    <p>Amplitude uses a trailing 57-second window; the earliest eligible recovery report is 57 seconds after release. Confirmations above remain valid through 949.5 seconds, before the reminder. Orbital confirmation uses ten successive exact-checkpoint comparisons and a declared scaled tolerance of .01. No-orbit motion has no orbital synchronization label. These are finite-horizon tests, not a proof of a limit cycle or the earlier full-state four-lag criterion.</p>
    <img src="figures/recovery.png" alt="Amplitude recovery times for all synthetic transmission and exchange scenarios, showing both starts and unconfirmed outcomes.">
    <p>The reset control returns sooner without an orbit because deleting S changes the continuing memory force and shifts the mechanical equilibrium. That supplies a larger disturbance when the drive returns. This comparison does not show that forgetting helps people. One changed-caregiving start does not reach the amplitude criterion before the later reminder.</p>
    <h2>Numerical checks and approximation</h2><p>{r['paths']} main trajectories. Maximum retained-accumulator error {checks['retained_accumulator_max_error']:.3g}; mechanical energy residual {checks['maximum_energy_residual_scaled']:.3g} in the declared normalization. Maximum |S| is {checks['maximum_field_magnitude']:.4f}, below the derived discrete bound {checks['field_bound']:.4f}. The bound is not imposed by clipping.</p><ul>{num}</ul>
    <p>The field is resolved along a material-coordinate ring. Its force is projected by virtual work onto the earlier clay shear mode. This is a documented reduction, not a complete moving-boundary fluid or rupture calculation. The field uses reference geometry and does not receive strain feedback. Spatial and temporal differences are reported rather than hidden; fine timing differences smaller than the reported diagnostic resolution should not be ranked.</p>
    <p>The 64-cell check changes one no-orbit reset-control amplitude confirmation from 150.5 to 149.0 s. Other tested confirmation times agree at the reported resolution. The 128-cell check covers nine selected retained-history paths, not the reset control. The 57 s amplitude confirmations in the forced primary cases equal the minimum diagnostic waiting window.</p>
    <h2>Adoption is a reference for distinct connections</h2><p>Biological ancestry, prenatal exposure, caregiving and communicated family history are kept separate. Unknown ancestry remains unknown. A biological transmission channel is uncalibrated and disabled in these runs; this does not establish its absence in people. Adoption status and conformity are not parameters.</p>
    <img src="figures/adoption-reference.png" alt="HCCH receiving-state intercountry adoption totals from 2004 to 2022; not all worldwide adoptions.">
    <p>The <a href="https://assets.hcch.net/docs/a8fe9f19-23e6-40c2-855e-388e112bf1f5.pdf">HCCH/Selman compilation</a> reports 45,482 in 2004 and 3,700 in 2022 within its intercountry receiving-state coverage. Domestic adoptions are not included. These counts are never used as trauma, transmission or exception rates. The <a href="https://pubmed.ncbi.nlm.nih.gov/31526412/">561-adoptee EGDS study</a> informs the separation of family routes; it is not a world prevalence estimate or evidence of inherited personal memories.</p>
    <h2>Inspect and reproduce</h2><p><a href="protocol.json">Protocol</a> · <a href="model.py">Model</a> · <a href="history_ledger.json">Provenance ledger</a> · <a href="summary.csv">All path summaries</a> · <a href="results.json">Checks and refinement</a> · <a href="plot_data.npz">Saved plot data</a> · <a href="REFERENCE.md">Evidence and limitations</a></p></html>'''
    (ROOT/'report.html').write_text(body,encoding='utf-8')
    rows='\n'.join(f'| {p["conditions"][x["condition"]]["name"]} | {100*x["braked_min_fraction"]:.3g}% | {val(x["amplitude_recovery_delay_s"])} | {"Not applicable" if x["condition"]==0 else val(x["mechanical_repeat_confirmation_delay_s"])} |' for x in primary)
    (ROOT/'README.md').write_text(f'''# Hug: persistent history with bounded expression

[Plots and report](report.html) · [Interactive animation](player.html) · [Short GIF](hug-memory.gif) · [Equations and reproduction](METHODS.md) · [Adoption references](REFERENCE.md)

The supplied corpus's accumulation and gradient-response laws are connected to a spatial memory field and a documented clay-mode projection. The requested finite limit is implemented through **explicit new saturation, expression-relaxation and bounded-exchange terms**. Retained inputs and provenance are not reset when the drive stops. A deliberate reset control measures the consequences of deletion.

Nine synthetic scenarios × three orbit conditions × two starts = 54 main paths. The three conditions are no orbit, circular and eccentric e=.212 with the previous signed waveform, common 5.7-second orbital clock and matched 6-micronewton force RMS. These are not actual lunar forces.

| Condition, first start | Braked amplitude / baseline | Amplitude confirmation delay | Mechanical repeat confirmation delay |
|---|---:|---|---|
{rows}

Drive off plus brake: 480–720 s. A later reminder at 950–970 s is separate. Amplitude confirmations use 57 s windows and remain valid through 949.5 s. Mechanical repetition uses exact orbit checkpoints, ten comparisons and tolerance .01. No-orbit motion has no orbital synchronization label. [All starts and scenarios](summary.csv), including non-confirmations, remain available. The older four-lag full-state recovery criterion is different and its times are not directly compared.

The forced primary amplitude confirmations equal the minimum 57 s waiting window. Deleting S in the reset control changes the applied force and disturbs the mechanical equilibrium, which accelerates its unforced return here. This is not evidence that forgetting helps people. One changed-caregiving start does not meet the amplitude criterion before the later reminder.

Maximum retained-input error: {checks['retained_accumulator_max_error']:.3g}. Main energy residual: {checks['maximum_energy_residual_scaled']:.3g}. Maximum |S| {checks['maximum_field_magnitude']:.4f} is below the discrete bound {checks['field_bound']:.4f}. All main states are finite. [Refinement details](results.json) report measured errors; the model is a material-coordinate field plus a mechanical shear mode, not a full moving-boundary Navier-Stokes solution.

The 64-cell run shifts one unforced reset-control confirmation from 150.5 to 149.0 s; other tested confirmations agree at the diagnostic resolution. The 128-cell subset checks nine retained-history paths. [Saved-data verification](verify_saved.py) and [player logic checks](check_player.cjs) are reproducible offline; the latter is not a browser layout test.

![Rhythm](figures/rhythm.png)

![Persistent input and bounded expression](figures/memory.png)

Adoption is reference material for distinguishing biological ancestry, caregiving and communicated family history. It is not an anomaly label or a trauma calibration. Specific autobiographical memory inheritance is not assumed. The biological channel is uncalibrated and disabled; unknown ancestry remains unknown. The HCCH intercountry totals in [the source table](adoption_reference.csv) are not a complete worldwide adoption count.

Sources: corrected corpus hash and Miro links are in [METHODS.md](METHODS.md). All parameters and event histories are synthetic. No physical clay or human measurements were collected. Publication updates repository files; it does not deploy a website.
''',encoding='utf-8')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache',required=True);ap.parse_args()
    p,r,d=plot();data=animate(p,r,d);report(p,r);print(json.dumps(dict(frames=len(data['times']),paths=data['shape'][1],files=[x.name for x in ROOT.glob('*.html')],gif_bytes=(ROOT/'hug-memory.gif').stat().st_size)))
if __name__=='__main__':main()
