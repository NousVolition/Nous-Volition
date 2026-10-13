"""Figures and an offline animation of the tested live intervention."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from hug_orbits import outline
import hug_sync as s

ROOT=Path(__file__).resolve().parent
COLORS=['#157b82','#ad5422','#596a91']

def load():return json.loads((ROOT/'hug_sync_results.json').read_text())

def curves(summary):
    return [(x['time_s'],[None if e is None else max(min(e),1e-12) for e in x['errors_scaled']]) for x in summary['stages']]

def build_figures():
    d=load();fig,axes=plt.subplots(1,2,figsize=(13,4.8),layout='constrained')
    for ax,j in zip(axes,[0,1]):
        for arm,color,label in zip(['restore','sham','hold_high'],COLORS,['Raise then restore','Unchanged stiffness','Leave stiffness high']):
            row=next(x for x in d['summary'] if x['arm']==arm and x['condition']==j)
            for stage,(tt,err) in enumerate(curves(row)):ax.plot(tt,err,color=color,lw=1.4,label=label if stage==0 else None)
        ax.axhline(1e-4,color='#444444',ls=':',lw=1,label='Confirmation threshold')
        ax.axvspan(171,741,color='#ad5422',alpha=.08)
        for t in [171,741]:ax.axvline(t,color='#777777',lw=.7,ls='--')
        row=next(x for x in d['summary'] if x['arm']=='restore' and x['condition']==j)
        ax.scatter([row['relock_confirmed_s']],[1e-4],color=COLORS[0],s=35,zorder=5)
        ax.set(yscale='log',ylim=(1e-12,20),xlim=(0,1550),xlabel='Elapsed simulation time (s)',ylabel='Full-state orbit-repeat error (scaled)',title=d['conditions'][j]['name'])
        ax.grid(alpha=.12)
    axes[0].legend(fontsize=8,loc='lower left')
    fig.suptitle('Raise stiffness at 171 s; restore it at 741 s · synthetic trajectories')
    fig.savefig(ROOT/'figures/hug_sync_transitions.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained')
    rows=[x for x in d['summary'] if x['arm']=='restore'];values=[x['confirmation_delay_after_restore_s'] for x in rows]
    bars=ax.barh([c['name'] for c in d['conditions']],values,color=COLORS[0]);ax.invert_yaxis()
    ax.bar_label(bars,labels=[f'{x:.1f} s' for x in values],padding=4)
    ax.set(xlim=(0,max(values)*1.17),xlabel='Time from restoring stiffness to confirmed synchronization (simulation s)',title='All seven cases regain synchronization in this intervention')
    ax.spines[['top','right']].set_visible(False)
    fig.savefig(ROOT/'figures/hug_sync_recovery.png',dpi=150);plt.close(fig)

def animation_data(cache):
    d=load();assert d['numerical_status']=='passed'
    rows=[x for x in d['summary'] if x['arm']=='restore'];p=d['protocol']['orbit_period_s']
    clips=[dict(label='Raise stiffness',start=171-2*p),dict(label='Loss confirmed',start=rows[0]['loss_confirmed_s']),dict(label='Restore stiffness',start=741-2*p)]
    for row in sorted(rows,key=lambda x:x['relock_confirmed_s']):
        start=row['relock_confirmed_s']-2*p
        match=next((x for x in clips if abs(x['start']-start)<1e-8),None)
        name=d['conditions'][row['condition']]['name']
        if match is not None:match['label']+=' / '+name
        else:clips.append(dict(label='Recovery: '+name,start=start))
    with np.load(cache/'main.npz') as f:
        time=f['time_s'];full=f['state'];ids=[next(i for i,c in enumerate(d['cases']) if c==dict(arm='restore',condition=j,history=0)) for j in range(7)];q=full[:,ids,0]*.1;del full
    data=dict(synthetic=True,source_sha256=hashlib.sha256((ROOT/'hug_sync_results.json').read_bytes()).hexdigest(),
        period_s=p,absolute_start_s=6000,conditions=d['conditions'],arms=outline(0),magnification=150,
        clips=[],timeline=[],events=[171,741],duration_s=4*p,
        recovery_confirmed_s=[x['relock_confirmed_s'] for x in rows],simulation_end_s=4161)
    for clip in clips:
        lo=int(round((clip['start']-p)/.05));hi=int(round((clip['start']+4*p)/.05))
        data['clips'].append({**clip,'sample_start_s':round(time[lo],8),'step_s':.05,'q_mm':np.round(q[lo:hi+1].T,9).tolist()})
    for row in rows:
        t=[];err=[];status=[]
        for stage in row['stages']:
            t.extend(stage['time_s']);err.extend([None if e is None else round(float(np.log10(max(min(e),1e-12))),7) for e in stage['errors_scaled']]);status.extend(stage['status'])
        data['timeline'].append(dict(time_s=t,log10_error=err,status=status))
    (ROOT/'hug_sync_animation.json').write_text(json.dumps(data,separators=(',',':'))+'\n',encoding='utf-8')
    template=(ROOT/'hug_sync_player_template.html').read_text(encoding='utf-8')
    (ROOT/'hug_sync_player.html').write_text(template.replace('SYNC_DATA_PLACEHOLDER',json.dumps(data,separators=(',',':'))),encoding='utf-8')
    return data

def frame_state(data,clip_index,t,condition):
    clip=data['clips'][clip_index];tt=clip['sample_start_s']+np.arange(len(clip['q_mm'][condition]))*clip['step_s'];q=np.interp(t,tt,clip['q_mm'][condition]);old=np.interp(t-data['period_s'],tt,clip['q_mm'][condition])
    timeline=data['timeline'][condition];i=max(0,np.searchsorted(timeline['time_s'],t,side='right')-1)
    return q,old,timeline['status'][i]

def render_gif(data,out):
    out.mkdir(exist_ok=True,parents=True);arms=[np.array(x) for x in data['arms']]
    # Keep both switch instants and both representative recovery times visible.
    chosen=[0,1,2,3,len(data['clips'])-1]
    fig=plt.figure(figsize=(10,6.9),dpi=95);grid=fig.add_gridspec(2,2,left=.085,right=.97,top=.79,bottom=.18,height_ratios=[1.6,1],hspace=.44,wspace=.24)
    fig.suptitle('Hug · losing and regaining orbital synchronization',fontsize=17,y=.97)
    heading=fig.text(.5,.916,'',ha='center',fontsize=12)
    info=fig.text(.5,.873,'',ha='center',fontsize=10)
    artists=[]
    for j in [0,1]:
        ax=fig.add_subplot(grid[0,j]);ax.set(aspect='equal',xlim=(-1.5,1.5),ylim=(-1.13,1.13));ax.axis('off');ax.set_title('Circular' if j==0 else 'Eccentric · Pasiphae e = 0.412',fontsize=11)
        ghost=[ax.plot([],[],color='#a0a7ad',ls=':',lw=2)[0] for _ in arms];lines=[ax.plot([],[],color=COLORS[0],lw=3)[0] for _ in arms]
        label=ax.text(.5,-.06,'',ha='center',transform=ax.transAxes,fontsize=10)
        chart=fig.add_subplot(grid[1,j]);timeline=data['timeline'][j]
        chart.plot(timeline['time_s'],timeline['log10_error'],color=COLORS[0],lw=1.3)
        chart.axhline(-4,color='#555555',ls=':',lw=1);chart.axvspan(171,741,color=COLORS[1],alpha=.08)
        chart.set(xlim=(0,1500),ylim=(-12.3,1.7),yticks=[-12,-8,-4,0],yticklabels=['10⁻¹²','10⁻⁸','10⁻⁴','1'],xlabel='Elapsed simulation time (s)',ylabel='Orbit-repeat error')
        cursor=chart.axvline(0,color='#333333',lw=1);artists.append((ghost,lines,label,cursor))
    fig.text(.5,.105,'Solid: current shape · dotted outline: one orbit earlier · deformation exaggerated ×150',ha='center',fontsize=9)
    fig.text(.5,.075,'Clips skip waiting time. Each timestamp belongs to the same continuous simulated trajectory.',ha='center',fontsize=9)
    fig.text(.5,.045,'Stiffness changes at 171 s and 741 s; the four states and orbital clock are never reset.',ha='center',fontsize=9)
    fig.text(.5,.015,'Synchronization requires 20 full-state comparisons; no 1–4 orbit repeat is not a claim of chaos.',ha='center',fontsize=9)
    frames=[];durations=[];palette=None;metadata=[]
    textmap={'assessing':'Settling · confirmation window incomplete','synchronized':'Synchronized','no_short_repeat':'Not synchronized: no 1–4 orbit repeat','quiet':'At rest'}
    for part,ci in enumerate(chosen):
        clip=data['clips'][ci];times=np.linspace(clip['start'],clip['start']+data['duration_s'],77)
        for fi,t in enumerate(times):
            heading.set_text(f'Clip {part+1}/5 · '+clip['label'])
            factor=2 if 171<=t<741 else 1
            info.set_text(f'Elapsed {t:.1f} simulation s · stiffness ×{factor}'+(' · time jump to this clip' if fi<6 and part else ''))
            for j,(ghost,lines,label,cursor) in enumerate(artists):
                q,old,status=frame_state(data,ci,t,j)
                for values,v in [(lines,q),(ghost,old)]:
                    for line,a in zip(values,arms):line.set_data(a[:,0]+data['magnification']*v/100*a[:,1],a[:,1])
                for line in lines:line.set_color(COLORS[0] if status=='synchronized' else COLORS[1])
                label.set_text(textmap[status]);cursor.set_xdata([t,t])
            fig.canvas.draw();im=Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:,:,:3].copy())
            if fi in (0,38,76):im.save(out/f'clip_{part+1}_{fi:02d}.png')
            frame=im.quantize(colors=128,dither=Image.Dither.NONE)
            if palette is None:palette=frame
            frames.append(frame);durations.append(800 if fi==0 else 70)
        metadata.append(dict(clip=part+1,begin_s=float(times[0]),end_s=float(times[-1]),source_clip=ci))
        print(f'Rendered clip {part+1}/5',flush=True)
    target=out/'hug_loses_and_regains_sync.gif';frames[0].save(target,save_all=True,append_images=frames[1:],duration=durations,disposal=2,optimize=False)
    with Image.open(target) as im:
        assert im.n_frames==len(frames)
        for i in range(im.n_frames):im.seek(i);im.load()
    (out/'animation_checks.json').write_text(json.dumps(dict(source_sha256=data['source_sha256'],frames=len(frames),every_frame_decoded=True,clips=metadata,file_bytes=target.stat().st_size),indent=2)+'\n')
    print('GIF verified:',target,flush=True)

def html_section():
    d=load();rows=[x for x in d['summary'] if x['arm']=='restore']
    table=''.join(f'<tr><td>{d["conditions"][x["condition"]]["name"]}</td><td>{x["confirmation_delay_after_restore_s"]:.1f} s</td></tr>' for x in rows)
    return f'''<section id="hug-sync"><h2>Batch 16 · the Hug loses and regains orbital synchronization</h2>
<p>These are continuous live-intervention runs. Restoring stiffness doubles at 171 simulation seconds and returns to baseline at 741 seconds. All four state variables and the orbital clock continue through each change. The 42 trajectories include seven orbital shapes, two previously settled histories, and restore/unchanged/leave-high controls.</p>
<p>All seven restored cases lose short orbital repetition and regain confirmed synchronization. The unchanged control stays synchronized; the leave-high control does not regain a 1–4 orbit repeat within the horizon. These are synthetic results. Times below include the 20-comparison confirmation window and are resolved on a 5.7-second orbital grid.</p>
<p><a href="hug_sync_player.html">Play the actual loss-and-recovery trajectories</a> · <a href="HUG_SYNC_METHODS.md">Methods and controls</a> · <a href="hug_sync_results.json">Saved results</a></p>
<figure><img src="figures/hug_sync_transitions.png" alt="Full-state orbit-repeat error loses and regains the threshold during the live stiffness intervention"><figcaption>Gray dotted line: acceptance threshold. Blank spans restart the confirmation window after each parameter change. The spring-energy change is included as external intervention work.</figcaption></figure>
<figure><img src="figures/hug_sync_recovery.png" alt="Time after restoration to confirmed recovery for circular and all six eccentric cases"></figure>
<table><tr><th>Orbital shape</th><th>Confirmation delay after restoration</th></tr>{table}</table>
<p>The animation skips waiting time in explicitly labelled clips; it does not reset the simulated state. Faint shapes show one orbit earlier. Numerical checks: {d['numerical_status']}. Independent physical-unit solver checks span both switches and late recovery.</p></section>'''

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--cache-dir',type=Path,default=ROOT/'.sync-cache');ap.add_argument('--gif-dir',type=Path);a=ap.parse_args()
    build_figures();data=animation_data(a.cache_dir)
    if a.gif_dir:render_gif(data,a.gif_dir)
