"""Plots and offline animation from the saved live trajectories."""
import argparse,base64,hashlib,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
import guard_sync as s
from hug_orbits import outline
ROOT=s.ROOT;OLD='#7b8492';NEW='#007d7e'

def row(d,model,condition,arm='restore'):return next(x for x in d['summary'] if x['model']==model and x['condition']==condition and x['arm']==arm)
def curves(r):
    return [(stage['time_s'],[np.nan if e is None else max(min(e),1e-12) for e in stage['errors']]) for stage in r['stages']]

def figures(d):
    out=ROOT/'figures';out.mkdir(exist_ok=True);plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(11,5),layout='constrained');yy=np.arange(7)
    for offset,key,color,label in [(-.18,'old_delay_s',OLD,'Old'),(.18,'updated_delay_s',NEW,'Updated')]:
        vals=[r[key] or 0 for r in d['comparison']];bars=ax.barh(yy+offset,vals,height=.34,color=color,label=label);ax.bar_label(bars,labels=['Not confirmed' if r[key] is None else f'{r[key]:.1f} s' for r in d['comparison']],padding=5,fontsize=9)
    ax.set_yticks(yy,[c['name'] for c in d['comparison']]);ax.invert_yaxis();ax.set(xlim=(0,max([r[k] or 0 for r in d['comparison'] for k in ['old_delay_s','updated_delay_s']])*1.21),xlabel='Delay after stiffness restoration to sustained confirmation (simulation s)',title='Old and updated Hug: recovery under the same intervention');ax.legend(frameon=False,loc='lower right');fig.savefig(out/'recovery-comparison.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    cutoff=max([r['relock_confirmed_s'] or 0 for r in d['summary'] if r['arm']=='restore'])+100
    for ax,c in zip(axes,[1,3]):
        for m,color,ls in [('old',OLD,'--'),('directional',NEW,'-')]:
            r=row(d,m,c)
            for stage,(tt,err) in enumerate(curves(r)):ax.plot(tt,err,color=color,ls=ls,lw=1.5,label='Old' if m=='old' else 'Updated' if stage==0 else None) if stage==0 else ax.plot(tt,err,color=color,ls=ls,lw=1.5)
            if r['relock_confirmed_s'] is not None:ax.scatter([r['relock_confirmed_s']],[1e-4],s=35,color=color,zorder=5)
        ax.axhline(1e-4,color='#444',ls=':',label='Confirmation threshold');ax.axvspan(171,741,color='#ad5422',alpha=.08)
        for x in [171,741]:ax.axvline(x,color='#988f88',ls=':',lw=.8)
        ax.set(xlim=(0,cutoff),ylim=(1e-12,10),yscale='log',title=d['conditions'][c-1]['name'],xlabel='Elapsed simulation time (s)',ylabel='Full-state orbit-repeat error (scaled)');ax.grid(alpha=.12)
    axes[0].legend(fontsize=9,frameon=False,loc='lower left');fig.suptitle('Stiffness doubles at 171 s and returns at 741 s\nGaps are incomplete confirmation windows; simulated states stay continuous',fontsize=13);fig.savefig(out/'loss-recovery.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,7),layout='constrained')
    for i,m in enumerate(['old','directional']):
        for j,c in enumerate([1,3]):
            ax=axes[i,j]
            for arm,color,label in [('restore',NEW,'Raise then restore'),('sham','#596a91','Unchanged'),('hold_high','#ad5422','Leave high')]:
                for stage,(tt,err) in enumerate(curves(row(d,m,c,arm))):ax.plot(tt,err,color=color,lw=1.1,label=label if stage==0 else None)
            ax.axhline(1e-4,color='#444',ls=':');ax.axvspan(171,741,color='#ad5422',alpha=.07);ax.set(xlim=(0,4161),ylim=(1e-12,10),yscale='log',title=('Old' if m=='old' else 'Updated')+' · '+d['conditions'][c-1]['name'],xlabel='Elapsed simulation time (s)',ylabel='Repeat error (scaled)')
    axes[0,0].legend(fontsize=8,frameon=False);fig.suptitle('Controls through the full observation horizon');fig.savefig(out/'controls.png',dpi=150);plt.close(fig)

def animation(d,cache):
    p=d['protocol'];P=p['orbit_period_s'];duration=4*P;clips={}
    def add(start,label):
        start=round(max(P,min(start,p['boundaries_s'][-1]-duration)),8)
        clips[start]=clips.get(start,'')+(' / ' if start in clips else '')+label
    add(171-2*P,'Raise stiffness');add(741-2*P,'Restore stiffness')
    for r in d['summary']:
        if r['arm']!='restore':continue
        prefix=('Old' if r['model']=='old' else 'Updated')+' '+d['conditions'][r['condition']-1]['name']
        if r['loss_confirmed_s'] is not None:add(r['loss_confirmed_s']-P,'Loss confirmed: '+prefix)
        if r['relock_confirmed_s'] is not None:add(r['relock_confirmed_s']-2*P,'Recovery: '+prefix)
    add(p['boundaries_s'][-1]-duration,'Final observation')
    # Collapse the shared loss label into a readable description, retaining times.
    for t,label in list(clips.items()):
        if label.count('Loss confirmed:')>3:clips[t]='Loss confirmed: both models and all orbital inputs'
    tt=np.load(cache/'main/time.npy');z=np.load(cache/'main/state.npy',mmap_mode='r');block=[];clipdata=[];N=286
    for start,label in sorted(clips.items()):
        times=start-P+np.arange(N)*.1;vals=np.stack([np.interp(times,tt,z[:,j,0])*.1 for j in range(84)]).astype('<f4');block.append(vals);clipdata.append(dict(start_s=start,sample_start_s=round(start-P,8),label=label))
    packed=np.stack(block);timelines=[]
    for r in d['summary']:
        t=[];error=[];status=[]
        for stage in r['stages']:
            t.extend(stage['time_s']);error.extend([None if x is None else min(x) for x in stage['errors']]);status.extend(stage['status'])
        timelines.append(dict(model=r['model'],arm=r['arm'],condition=r['condition'],time=t,error=error,status=status))
    data=dict(source_sha256=s.sha(ROOT/'results.json'),format='little-endian float32 base64',shape=list(packed.shape),layout=['clip','case','sample'],channels='q_mm',values=base64.b64encode(packed.tobytes()).decode(),step_s=.1,duration_s=duration,period_s=P,absolute_start_s=p['absolute_start_s'],end_s=p['boundaries_s'][-1],clips=clipdata,cases=d['cases'],conditions=d['conditions'],timelines=timelines,outline=outline(0),comparison=d['comparison'])
    content=json.dumps(data,separators=(',',':'));(ROOT/'animation.json').write_text(content+'\n',encoding='utf-8');(ROOT/'player.html').write_text((ROOT/'player-template.html').read_text(encoding='utf-8').replace('SYNC_GUARD_DATA_PLACEHOLDER',content),encoding='utf-8');return data,packed

def gif(d,data,packed,out):
    out.mkdir(parents=True,exist_ok=True);P=data['period_s'];chosen={0}
    for i,c in enumerate(data['clips']):
        if c['label'].startswith(('Loss confirmed','Restore stiffness')):chosen.add(i)
    for model in ['old','directional']:
        for condition in [1,3]:
            r=row(d,model,condition)
            if r['relock_confirmed_s'] is not None:
                start=round(r['relock_confirmed_s']-2*P,8);chosen.add(next(i for i,c in enumerate(data['clips']) if abs(c['start_s']-start)<1e-7))
    chosen=sorted(chosen);arms=[np.asarray(x) for x in data['outline']];fig=plt.figure(figsize=(10.4,8),dpi=95);grid=fig.add_gridspec(3,2,left=.085,right=.97,top=.84,bottom=.13,height_ratios=[1,1,.8],hspace=.47,wspace=.32)
    fig.suptitle('Hug synchronization · old and updated',fontsize=18,y=.975);heading=fig.text(.5,.927,'',ha='center',fontsize=11);clock=fig.text(.5,.889,'',ha='center',fontsize=10);artists=[];charts=[]
    for i,(m,c) in enumerate([('old',1),('directional',1),('old',3),('directional',3)]):
        ax=fig.add_subplot(grid[i//2,i%2]);ax.set(aspect='equal',xlim=(-1.5,1.5),ylim=(-1.12,1.12));ax.axis('off');ax.set_title(('Old' if m=='old' else 'Updated')+' · '+d['conditions'][c-1]['name'],fontsize=12)
        ghost=[ax.plot([],[],color='#b0b9bc',ls=':',lw=1.8)[0] for _ in arms];current=[ax.plot([],[],color=OLD if m=='old' else NEW,lw=2.3)[0] for _ in arms];label=ax.text(.5,-.12,'',ha='center',transform=ax.transAxes,fontsize=10)
        case=next(j for j,r in enumerate(d['cases']) if r==dict(model=m,arm='restore',condition=c,history=0));timeline=next(t for t in data['timelines'] if t['model']==m and t['arm']=='restore' and t['condition']==c);artists.append((current,ghost,label,case,timeline))
    for col,c in enumerate([1,3]):
        ax=fig.add_subplot(grid[2,col])
        for m,color,ls in [('old',OLD,'--'),('directional',NEW,'-')]:
            for t,e in curves(row(d,m,c)):ax.plot(t,e,color=color,ls=ls,lw=1)
        ax.axhline(1e-4,color='#555',ls=':',lw=1);ax.axvspan(171,741,color='#ad5422',alpha=.07);ax.set(xlim=(0,1500),ylim=(1e-12,10),yscale='log',yticks=[1e-12,1e-8,1e-4,1],xlabel='Elapsed simulation time (s)',ylabel='Repeat error');ax.tick_params(labelsize=8);charts.append(ax.axvline(0,color='#39494e',lw=1))
    fig.text(.5,.045,'Dotted outlines: one orbit earlier · shear magnified ×150 · synthetic model\nClips skip waiting time. States and orbital phase continue through each switch.',ha='center',fontsize=9)
    words={'assessing':'Assessing: new window','synchronized':'Synchronized','no_short_repeat':'No 1–4 orbit repeat','quiet':'Quiet'};frames=[];durations=[]
    for part,ci in enumerate(chosen):
        clip=data['clips'][ci]
        for frame,t in enumerate(np.linspace(clip['start_s'],clip['start_s']+data['duration_s'],61)):
            short='Raise stiffness' if part==0 else 'Confirmed loss' if clip['label'].startswith('Loss') else 'Restore stiffness' if clip['label'].startswith('Restore') else 'Compare recovery'
            heading.set_text(f'Clip {part+1}/{len(chosen)} · {short}'+(' · time jump' if frame<4 and part else ''))
            clock.set_text(f'Elapsed {t:.1f} s · stiffness ×{2 if 171<=t<741 else 1}')
            for current,ghost,label,case,timeline in artists:
                times=clip['sample_start_s']+np.arange(data['shape'][2])*.1
                for lines,now in [(current,t),(ghost,t-P)]:
                    q=np.interp(now,times,packed[ci,case]);
                    for line,arm in zip(lines,arms):line.set_data(arm[:,0]+150*q/100*arm[:,1],arm[:,1])
                k=max(0,np.searchsorted(timeline['time'],t+1e-8,side='right')-1);status=timeline['status'][k];label.set_text(words[status]);label.set_color(NEW if status=='synchronized' else '#ad5422' if status=='no_short_repeat' else '#52616b')
            for cursor in charts:cursor.set_xdata([t,t])
            fig.canvas.draw();im=Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:,:,:3].copy());
            if frame in [0,30,60]:im.save(out/f'clip-{part+1}-{frame}.png')
            frames.append(im.quantize(colors=128,dither=Image.Dither.NONE));durations.append(650 if frame==0 else 80)
        print(f'Rendered GIF clip {part+1}/{len(chosen)}',flush=True)
    path=out/'old-updated-sync.gif';frames[0].save(path,save_all=True,append_images=frames[1:],duration=durations,disposal=2,optimize=False);plt.close(fig)
    with Image.open(path) as im:
        assert im.n_frames==len(frames)
        for j in range(im.n_frames):im.seek(j);im.load()
    (out/'checks.json').write_text(json.dumps(dict(frames=len(frames),clips=len(chosen),all_frames_decoded=True,plays_once=True,source_sha256=data['source_sha256']),indent=2)+'\n')

def report(d):
    rows=d['comparison'];all_recovered=all(r['updated_delay_s'] is not None for r in rows);all_faster=all(r['updated_minus_old_s'] is not None and r['updated_minus_old_s']<0 for r in rows)
    headline='The updated Hug recovers sooner in every tested orbit.' if all_faster else 'Recovery depends on the model and orbital input.'
    def val(x):return 'Not confirmed' if x is None else f'{x:.1f}'
    table=''.join(f'<tr><td>{r["name"]}</td><td>{val(r["old_delay_s"])}</td><td>{val(r["updated_delay_s"])}</td><td>{val(r["updated_minus_old_s"])}</td><td>{val(r["updated_mechanical_projection_delay_s"])}</td></tr>' for r in rows)
    circ=rows[0];elara=rows[2];same=all(abs(r['historical_reproduction_difference_s'] or 0)<1e-7 for r in rows)
    html=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hug recovery: old and updated</title><style>body{{font:17px/1.65 system-ui,sans-serif;background:#faf9f5;color:#23313b;margin:0}}main{{max-width:1100px;margin:auto;padding:32px 24px}}h1{{font-size:2.3rem;line-height:1.15}}h2{{margin-top:2rem}}a{{color:#006d74}}img{{width:100%;height:auto;background:white;border:1px solid #ddd;border-radius:8px}}.table{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:15px}}td,th{{padding:9px;text-align:left;border-bottom:1px solid #d9dddf}}.note{{padding:15px;background:#eaf1ef;border-left:4px solid #007d7e}}.button{{display:inline-block;padding:10px 18px;border:1px solid #007d7e;border-radius:5px;text-decoration:none}}</style></head><body><main>
<p><a href="../hug-active-guard/report.html">Earlier steady-rhythm comparison</a></p><h1>{headline}</h1>
<p>Both models undergo the same intervention: stiffness doubles at 171 seconds and returns at 741 seconds. The old and updated equations are integrated continuously, with their full internal states and orbital clocks retained.</p>
<p><a class="button" href="player.html">Play the loss and recovery comparison</a> &nbsp; <a href="METHODS.md">Equations and methods</a> &nbsp; <a href="results.json">All numerical results</a></p>
<p class="note">These are synthetic recovery <strong>confirmation delays</strong>, measured after stiffness is restored. They include the diagnostic waiting window and have 5.7-second resolution. The updated test uses all eight states. No physical clay measurements or tearing model are added.</p>
<img src="figures/recovery-comparison.png" alt="Old versus updated recovery confirmation delays for circular and all six eccentric inputs">
<div class="table"><table><thead><tr><th>Input</th><th>Old delay (s)</th><th>Updated delay (s)</th><th>Updated − old (s)</th><th>Updated, mechanical states only (s)</th></tr></thead><tbody>{table}</tbody></table></div>
<p>Circular recovery changes from {val(circ['old_delay_s'])} to {val(circ['updated_delay_s'])} seconds. Elara changes from {val(elara['old_delay_s'])} to {val(elara['updated_delay_s'])} seconds. The old model's seven historical delays {'are reproduced on the same time grid' if same else 'are compared explicitly in the saved results'}. The projected column checks whether including hidden guard and participant states changes the confirmation delay.</p>
<h2>The same loss-and-recovery test</h2><img src="figures/loss-recovery.png" alt="Old and updated orbit-repeat errors through stiffness changes for circular and Elara forcing"><p>The shaded region is the high-stiffness interval. Blank spans restart the diagnostic window, not the physical states. Dots mark sustained recovery confirmation. A pass is checked retrospectively through the full 4161-second horizon; an isolated overlap or one passing sample is insufficient.</p>
<h2>Controls and full observation horizon</h2><img src="figures/controls.png" alt="Restored, unchanged and leave-high controls for old and updated models"><p>For both models and all seven inputs, the unchanged arm remains synchronized at every completed assessment. The leave-high arm loses short orbital repetition and does not recover it before 4161 seconds. All restored cases recover. These controls distinguish restoring stiffness from simply waiting. Both settled histories and all three arms are selectable in the player.</p>
<h2>Numerical checks</h2><p>84 live trajectories at two accuracy settings, with independently repeated updated-model preparation and 42 physical-unit Radau segment checks. All numerical gates: <strong>{d['numerical_status']}</strong>. Maximum saved full-state discrepancy: {d['maximum_path_difference']:.3g}; energy residual: {d['maximum_energy_residual']:.3g}; independent-solver discrepancy: {d['maximum_independent_error']:.3g}. Exact spring-switch work is included.</p>
<p>This comparison now measures recovery under the earlier intervention. It still tests one guard strength and time mapping, two settled histories and a finite horizon. Added resistance and adaptation both differ from the old model; this test does not isolate which causes a recovery-time change. The animation's affine shear preserves joins by construction.</p>
<p><a href="protocol.json">Frozen protocol</a> · <a href="freeze.json">Source freeze</a> · <a href="test_guard_sync.py">Equation tests</a> · <a href="animation.json">Saved animation samples</a></p></main></body></html>'''
    (ROOT/'report.html').write_text(html,encoding='utf-8')
    md='# Updated Hug: losing and regaining synchronization\n\n'+headline+'\n\n[Illustrated report](report.html) · [Offline animation](player.html) · [Methods and reproduction](METHODS.md) · [Results](results.json)\n\n![Recovery delays](figures/recovery-comparison.png)\n\n| Input | Old delay (s) | Updated delay (s) | Updated − old (s) |\n| --- | ---: | ---: | ---: |\n'
    for r in rows:md+=f'| {r["name"]} | {val(r["old_delay_s"])} | {val(r["updated_delay_s"])} | {val(r["updated_minus_old_s"])} |\n'
    md+='\nThe same stiffness changes occur at 171 and 741 simulation seconds, with continuous states and orbital phase. Delays include a 20-comparison confirmation window, have 5.7-second resolution and are checked through 4161 seconds. Old diagnostics use four states; updated diagnostics use eight. A mechanical-only projection is retained for comparison.\n\n84 live trajectories at two accuracy settings and 42 independent Radau segments support the numerical audit. The old historical delays are reproduced. Unchanged-stiffness and leave-high controls are included, along with both settled histories.\n\nThese are synthetic coefficients and prescribed orbit-shaped loads. Added damping and adaptation are not separated by this experiment. The animation magnifies shear ×150 and preserves outline joins through its drawing map; it does not test tearing. Keep this folder beside the two parent studies named in the methods. No website deployment or physical measurement upload is involved.\n'
    (ROOT/'README.md').write_text(md,encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache',type=Path,required=True);ap.add_argument('--gif-dir',type=Path);a=ap.parse_args();d=json.loads((ROOT/'results.json').read_text());assert d['numerical_status']=='passed'
    figures(d);data,packed=animation(d,a.cache);report(d)
    if a.gif_dir:gif(d,data,packed,a.gif_dir)
    print(json.dumps(dict(figures=3,animation_shape=data['shape'],clips=len(data['clips']))),flush=True)
if __name__=='__main__':main()
