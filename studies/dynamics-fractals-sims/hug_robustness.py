"""Parameter robustness of the unchanged synthetic clay/active-Hug equations."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import CubicHermiteSpline
from scipy.optimize import brentq
import hug_rhythm as h
from active_hug import raw_tide, tide_rms
from orbits import protocol as orbit_protocol

ROOT=Path(__file__).resolve().parent
PARAMETERS=[('material','G_M_Pa','Maxwell stiffness'),('material','G_K_Pa','Kelvin stiffness'),
    ('material','eta_M_Pa_s','Maxwell viscosity'),('material','eta_K_Pa_s','Kelvin viscosity'),
    ('mechanics','parallel_stiffness_N_m','Restoring stiffness'),
    ('feedback','saturation_N_s_m3','Feedback saturation'),('feedback','gain_N_s_m','Feedback gain')]


def protocol():return json.loads((ROOT/'hug_robustness_protocol.json').read_text())


def settings(cfg=None):
    cfg=protocol() if cfg is None else cfg
    base=json.loads((ROOT/cfg['baseline_source']).read_text())
    rows=[dict(id='baseline',label='Baseline',kind='baseline',factors=[1.]*7,parameters=base)]
    for j,(group,key,label) in enumerate(PARAMETERS):
        factors=cfg['gain_factors'] if key=='gain_N_s_m' else cfg['one_at_a_time_factors']
        for factor in factors:
            p=copy.deepcopy(base);p[group][key]*=factor;f=[1.]*7;f[j]=factor
            if factor==0 and key=='gain_N_s_m':p['feedback']['saturation_N_s_m3']=0.;f[5]=0.
            rows.append(dict(id=f'{key}_{factor:g}',label='Feedback off' if factor==0 else f'{label} x{factor:g}',kind='one_at_a_time',factors=f,parameters=p))
    rng=np.random.default_rng(cfg['seed'])
    for i in range(cfg['joint_samples']):
        factors=rng.uniform(*cfg['joint_factor_range'],7);p=copy.deepcopy(base)
        for (group,key,_),f in zip(PARAMETERS,factors):p[group][key]*=float(f)
        rows.append(dict(id=f'joint_{i+1:02}',label=f'Joint {i+1:02}',kind='joint',factors=factors.tolist(),parameters=p))
    return rows


def conditions(cfg=None):
    cfg=protocol() if cfg is None else cfg;period=cfg['orbit_period_s']
    rows=[dict(name='No orbit',e=None,period_s=period),dict(name='Circular',e=0.,period_s=period)]
    rows.extend(dict(name=m['name'],e=m['e'],period_s=period) for m in orbit_protocol()['moons'])
    for p in cfg['baseline_detuned_periods_s']:
        rows.extend([dict(name=f'Circular ({p:g} s)',e=0.,period_s=p),dict(name=f'Pasiphae ({p:g} s)',e=.412,period_s=p)])
    return rows


def cases(cfg=None):
    cfg=protocol() if cfg is None else cfg
    return [dict(setting=i,condition=j,start=k) for i in range(len(settings(cfg)))
            for j in range(12 if i==0 else 8) for k in range(len(cfg['starts_scaled']))]


class Ensemble:
    """Independent rows, evaluated together; no coupling between trajectories."""
    def __init__(self,models):
        for key in ('gm','gk','em','ek','mass','k','gain','saturation','ck','qscale','length','volume','energy_scale'):
            setattr(self,key,np.array([getattr(m,key) for m in models]))

    def rhs(self,z,force):
        x,v,u,w=z[:,:4].T;s=x-u-w
        du=(self.gm*s-self.gk*u)/self.ek;dw=self.gm*s/self.em
        active=(self.gain-self.saturation*self.qscale**2*x*x)*v
        out=np.empty_like(z);out[:,0]=v;out[:,1]=(-self.k*x-self.ck*s+active+force/self.qscale)/self.mass
        out[:,2]=du;out[:,3]=dw
        if z.shape[1]==7:
            sigma=self.gm*self.qscale/self.length*s;speed=self.qscale*v
            out[:,4]=active*self.qscale*speed/self.energy_scale;out[:,5]=force*speed/self.energy_scale
            out[:,6]=self.volume*((sigma-self.gk*u*self.qscale/self.length)**2/self.ek+sigma*sigma/self.em)/self.energy_scale
        return out

    def energy(self,z):
        x,v,u,w=z[:,:4].T
        return (.5*self.mass*(self.qscale*v)**2+.5*self.k*(self.qscale*x)**2+
            .5*self.volume*(self.gm*(self.qscale/self.length*(x-u-w))**2+self.gk*(self.qscale/self.length*u)**2))/self.energy_scale


def force(t,condition,cfg):
    if condition['e'] is None:return np.zeros_like(t,dtype=float)
    return cfg['orbital_force_rms_N']*raw_tide(np.asarray(t)/condition['period_s'],condition['e'])/tide_rms(condition['e'])


def integrate_ensemble(cfg,dt,progress=True):
    ss=settings(cfg);cc=conditions(cfg);rows=cases(cfg);ens=Ensemble([h.Model(ss[r['setting']]['parameters']) for r in rows])
    cond=np.array([r['condition'] for r in rows]);z=np.array([cfg['starts_scaled'][r['start']]+[0.,0.,0.] for r in rows])
    n=int(round(cfg['horizon_s']/dt));stride=int(round(cfg['sample_interval_s']/dt));first=int(round((cfg['horizon_s']-cfg['saved_window_s'])/dt))
    if not np.isclose(n*dt,cfg['horizon_s']) or not np.isclose(stride*dt,cfg['sample_interval_s']):raise ValueError('Step must divide time and sampling grid')
    periods=np.array([int(round(2*c['period_s']/dt)) for c in cc])
    if any(not np.isclose(count*dt/2,c['period_s']) for count,c in zip(periods,cc)):raise ValueError('Step must divide orbital periods')
    table=np.zeros((len(cc),max(periods)))
    for j,c in enumerate(cc):table[j,:periods[j]]=force(np.arange(periods[j])*dt/2,c,cfg)
    cindex=np.arange(len(cc));bad=np.zeros(len(rows),bool);bad_time=np.full(len(rows),-1.)
    e0=ens.energy(z);err=np.zeros(len(rows));maxstate=np.max(np.abs(z[:,:4]),axis=1)
    saved=np.empty(((n-first)//stride+1,len(rows),4));times=np.arange(first,n+1,stride)*dt;at=0
    for step in range(n+1):
        if step>=first and (step-first)%stride==0:saved[at]=z[:,:4];at+=1
        if step%max(1,int(round(1/dt)))==0:
            err=np.maximum(err,np.abs(ens.energy(z)-e0-z[:,4]-z[:,5]+z[:,6]))
        if step==n:break
        f0=table[cindex,(2*step)%periods][cond];fm=table[cindex,(2*step+1)%periods][cond];f1=table[cindex,(2*step+2)%periods][cond]
        a=ens.rhs(z,f0);b=ens.rhs(z+dt*a/2,fm);c=ens.rhs(z+dt*b/2,fm);d=ens.rhs(z+dt*c,f1)
        z+=dt*(a+2*b+2*c+d)/6
        now=(~np.all(np.isfinite(z),axis=1))|(np.max(np.abs(z[:,:4]),axis=1)>cfg['gates']['state_guard_scaled'])
        new=now&~bad;bad_time[new]=(step+1)*dt;bad|=now;z[bad]=0.
        maxstate=np.maximum(maxstate,np.max(np.abs(z[:,:4]),axis=1))
        if progress and (step+1)%max(1,n//10)==0:print(f'dt={dt:g}: {(step+1)*dt:.0f}/{cfg["horizon_s"]:g} s; {len(rows)} trajectories',flush=True)
    return dict(time_s=times,state=saved,final=z,energy_error=err,max_state=maxstate,guard_time=bad_time)


def spline_for(t,z,model,condition,cfg):
    dz=Ensemble([model]*len(t)).rhs(z,force(t,condition,cfg))
    return CubicHermiteSpline(t,z,dz)


def sections(t,z,spline):
    ids=np.where((z[:-1,0]<=0)&(z[1:,0]>0))[0]
    tt=np.array([brentq(lambda v:float(spline(v)[0]),t[i],t[i+1],xtol=1e-11) for i in ids])
    return tt,spline(tt)


def repeat_metrics(spline,end,period):
    tt=end-np.arange(40,-1,-1)*period;z=spline(tt)
    errors={str(n):float(np.max(np.abs(z[-20:]-z[-20-n:-n]))) for n in range(1,5)}
    return errors,z


def classify_autonomous(row,cycle,cfg):
    g=cfg['gates']
    if row['guard_time_s']>=0:return 'integration_guard'
    if row['tail_norm_scaled']<g['quiet_norm_scaled'] and row['rest_growth_rate_s_inv']<0:return 'rest'
    m=row['metrics']
    if cycle and cycle.get('status')=='attracting_cycle' and m['status']=='measured':
        agree=abs(m['mean_period_s']/cycle['period_s']-1)<g['metric_relative_agreement']
        if agree and row.get('section_cycle_error_scaled',1)>g['section_error_scaled']:return 'unsettled'
        if agree and row['amplitude_drift_fraction']<g['window_amplitude_drift_fraction']:return 'self_sustained'
    return 'unsettled'


def classify_forced(row,cfg):
    if row['guard_time_s']>=0:return 'integration_guard'
    if row['metrics']['status']!='measured' or row['metrics'].get('mean_half_amplitude_mm',0)<cfg['gates']['observable_half_amplitude_mm']:return 'unsettled'
    if any(e<cfg['gates']['orbit_repeat_error_scaled'] for e in row['return_errors_scaled'].values()):return 'orbit_repeat'
    return 'no_short_repeat'


def compact_metrics(m):return {k:v for k,v in m.items() if k!='crossing_times_s'}


def analyze(cfg,data,refined):
    ss=settings(cfg);cc=conditions(cfg);rows=cases(cfg);t=data['time_s'];tr=refined['time_s'];out=[];cycles={};control=[]
    # Each unforced setting gets a full-state shooting/Floquet check when the rest state is unstable.
    for i,s in enumerate(ss):
        j=next(j for j,r in enumerate(rows) if r==dict(setting=i,condition=0,start=0));model=h.Model(s['parameters']);z=data['state'][:,j]
        growth=float(max(np.linalg.eigvals(model.jacobian(np.zeros(4))).real));cy=dict(status='stable_rest' if growth<0 else 'unresolved',rest_growth_rate_s_inv=growth)
        if growth>0:
            try:
                sp=spline_for(t[-151:],z[-151:],model,cc[0],cfg);ts,zs=sections(t[-151:],z[-151:],sp)
                fit=h.shoot(model,zs[-1],float(np.mean(np.diff(ts[-4:]))))
                amp=float(np.ptp(np.array(fit['cycle_state_scaled'])[:,0])*.05)
                if amp>cfg['gates']['observable_half_amplitude_mm'] and fit['largest_transverse_multiplier']<1 and fit['neutral_multiplier_error']<1e-6:
                    cy.update(status='attracting_cycle',**{k:v for k,v in fit.items() if k not in ('cycle_state_scaled','cycle_time_s')},half_amplitude_mm=amp)
                else:cy.update(status='unresolved_cycle',details='Nontrivial attracting-cycle criteria not met')
            except (RuntimeError,ValueError,IndexError,OverflowError) as error:cy.update(status='shooting_failed',details=str(error))
        cycles[s['id']]=cy
    print('Periodic shooting complete',flush=True)
    for j,r in enumerate(rows):
        s=ss[r['setting']];c=cc[r['condition']];model=h.Model(s['parameters']);z=data['state'][:,j];zr=refined['state'][:,j]
        cy=cycles[s['id']];m=compact_metrics(h.measurement_metrics(t,z[:,0]*.1));mr=compact_metrics(h.measurement_metrics(tr,zr[:,0]*.1))
        early=np.ptp(z[:len(t)//2,0])/2;late=np.ptp(z[len(t)//2:,0])/2
        early_r=np.ptp(zr[:len(tr)//2,0])/2;late_r=np.ptp(zr[len(tr)//2:,0])/2
        row=dict(**r,setting_id=s['id'],condition_name=c['name'],guard_time_s=float(data['guard_time'][j]),
            max_state_scaled=float(data['max_state'][j]),tail_norm_scaled=float(np.max(np.abs(z))),
            energy_error_scaled=float(data['energy_error'][j]),refined_energy_error_scaled=float(refined['energy_error'][j]),
            rest_growth_rate_s_inv=cy['rest_growth_rate_s_inv'],metrics=m,refined_metrics=mr,
            amplitude_drift_fraction=float(abs(late-early)/max(late,early,1e-12)),
            refined_tail_norm_scaled=float(np.max(np.abs(zr))),refined_guard_time_s=float(refined['guard_time'][j]),
            refined_amplitude_drift_fraction=float(abs(late_r-early_r)/max(late_r,early_r,1e-12)),
            refinement_last_state_difference_scaled=float(np.max(np.abs(z[-1]-zr[-1]))))
        if m['status']=='measured' and mr['status']=='measured':
            row['refinement_period_relative_error']=abs(m['mean_period_s']/mr['mean_period_s']-1)
            row['refinement_amplitude_relative_error']=abs(m['mean_half_amplitude_mm']/mr['mean_half_amplitude_mm']-1)
        # Hermite interpolation uses the ODE slope; it does not integrate or change the trajectory.
        span=300 if c['e'] is not None else 15
        mask=t>=t[-1]-span;maskr=tr>=tr[-1]-span
        sp=spline_for(t[mask],z[mask],model,c,cfg);spr=spline_for(tr[maskr],zr[maskr],model,c,cfg)
        if c['e'] is None:
            if cy['status']=='attracting_cycle':
                _,zs=sections(t[mask],z[mask],sp);_,zrs=sections(tr[maskr],zr[maskr],spr)
                row['section_cycle_error_scaled']=float(np.max(np.abs(zs[-4:]-cy['section_state_scaled'])))
                row['refined_section_cycle_error_scaled']=float(np.max(np.abs(zrs[-4:]-cy['section_state_scaled'])))
            row['classification']=classify_autonomous(row,cy,cfg)
            rr={**row,'metrics':mr,'section_cycle_error_scaled':row.get('refined_section_cycle_error_scaled',1),
                'tail_norm_scaled':row['refined_tail_norm_scaled'],'guard_time_s':row['refined_guard_time_s'],
                'amplitude_drift_fraction':row['refined_amplitude_drift_fraction']}
            row['refined_classification']=classify_autonomous(rr,cy,cfg)
        else:
            errors,zz=repeat_metrics(sp,t[-1],c['period_s']);er,zzr=repeat_metrics(spr,tr[-1],c['period_s'])
            row['return_errors_scaled']=errors;row['refined_return_errors_scaled']=er
            row['stroboscopic_last_state_scaled']=zz[-1].tolist();row['classification']=classify_forced(row,cfg)
            row['refined_stroboscopic_last_state_scaled']=zzr[-1].tolist()
            row['refined_classification']=classify_forced({**row,'metrics':mr,'return_errors_scaled':er,'guard_time_s':row['refined_guard_time_s']},cfg)
            row['repeat_orbits']=next((int(n) for n,e in errors.items() if e<cfg['gates']['orbit_repeat_error_scaled']),None)
        if r['start']==0 and (r['setting']==0 or s['id'] in ('gain_N_s_m_0','gain_N_s_m_0.05','G_M_Pa_2','parallel_stiffness_N_m_2')):
            mask=t>=t[-1]-20;row['trace']=dict(time_s=np.round(t[mask]-t[-1]+20,6).tolist(),displacement_mm=np.round(z[mask,0]*.1,9).tolist())
        # Physical-unit Radau controls cover baseline all conditions and each parameter setting unforced.
        if r['start']==0 and (r['setting']==0 or r['condition']==0):
            begin=t[-1]-cfg['independent_control_seconds'];initial=sp(begin)*model.scale
            def physical_rhs(v,y):
                q,speed,u,w=y;sigma=model.gm*(q/model.length-u-w)
                return [speed,(-model.k*q-model.volume*sigma/model.length+(model.gain-model.saturation*q*q)*speed+float(force(v,c,cfg)))/model.mass,
                    (sigma-model.gk*u)/model.ek,sigma/model.em]
            sol=solve_ivp(physical_rhs,(begin,t[-1]),initial,method='Radau',rtol=2e-10,atol=2e-15,max_step=.035,dense_output=True)
            if not sol.success:raise RuntimeError(sol.message)
            tt=np.linspace(begin,t[-1],241);error=float(np.max(np.abs(sol.sol(tt).T/model.scale-sp(tt))))
            control.append(dict(case_index=j,error_scaled=error))
        out.append(row)
    pairs=[]
    for a,b in zip(out[::2],out[1::2]):
        if a['condition']==0:
            status=a['classification'] if a['classification']==b['classification'] else 'mixed_or_unsettled';difference=None
        else:
            difference=float(np.max(np.abs(np.array(a['stroboscopic_last_state_scaled'])-b['stroboscopic_last_state_scaled'])))
            if a['classification']==b['classification']=='orbit_repeat':status='orbit_locked' if difference<cfg['gates']['between_start_error_scaled'] else 'repeat_start_dependent'
            elif a['classification']==b['classification']:status=a['classification']
            else:status='mixed_or_unsettled'
        if a['condition']==0:
            refined_status=a['refined_classification'] if a['refined_classification']==b['refined_classification'] else 'mixed_or_unsettled';rdifference=None
        else:
            rdifference=float(np.max(np.abs(np.array(a['refined_stroboscopic_last_state_scaled'])-b['refined_stroboscopic_last_state_scaled'])))
            if a['refined_classification']==b['refined_classification']=='orbit_repeat':refined_status='orbit_locked' if rdifference<cfg['gates']['between_start_error_scaled'] else 'repeat_start_dependent'
            elif a['refined_classification']==b['refined_classification']:refined_status=a['refined_classification']
            else:refined_status='mixed_or_unsettled'
        pairs.append(dict(setting=a['setting'],condition=a['condition'],classification=status,refined_classification=refined_status,
            between_start_state_error_scaled=difference,refined_between_start_state_error_scaled=rdifference,
            maximum_half_amplitude_mm=max(a['metrics'].get('mean_half_amplitude_mm',0),b['metrics'].get('mean_half_amplitude_mm',0))))
    result=dict(origin='synthetic_parameter_sensitivity',physical_measurements=0,additional_sims_runs=0,protocol=cfg,settings=ss,conditions=cc,cases=out,pairs=pairs,cycles=cycles,independent_controls=control,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (cfg['baseline_source'],'hug_rhythm.py','hug_rhythm_protocol.json','active_hug.py','orbit_protocol.json')})
    audit=ROOT/'hug_robustness_initial_audit.json'
    if audit.exists():result['initial_resolution_audit']=json.loads(audit.read_text())
    result['checks']=validate(result);result['numerical_status']='passed' if all(result['checks'].values()) else 'failed_checks_retained'
    result['counts']=dict(Counter(p['classification'] for p in pairs));return result


def validate(d):
    g=d['protocol']['gates'];rows=d['cases'];valid=[r for r in rows if 'refinement_period_relative_error' in r and r['metrics'].get('mean_half_amplitude_mm',0)>g['observable_half_amplitude_mm']]
    return dict(all_trajectories_finite=all(r['guard_time_s']<0 and r['refined_guard_time_s']<0 for r in rows),
        energy_balance=max(max(r['energy_error_scaled'],r['refined_energy_error_scaled']) for r in rows)<g['energy_error_scaled'],
        refined_period=max(r['refinement_period_relative_error'] for r in valid)<g['refinement_period_relative_error'],
        refined_amplitude=max(r['refinement_amplitude_relative_error'] for r in valid)<g['refinement_amplitude_relative_error'],
        classification_step_agreement=all(r['classification']==r['refined_classification'] for r in rows+d['pairs']),
        independent_solver=max(r['error_scaled'] for r in d['independent_controls'])<g['independent_error_scaled'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--cache-dir',type=Path);p.add_argument('--analyze-only',action='store_true');args=p.parse_args()
    if args.check:
        d=json.loads((ROOT/'hug_robustness_results.json').read_text());print(json.dumps(validate(d)));assert all(validate(d).values());return
    cfg=protocol();cache=args.cache_dir or ROOT/'.robustness-cache';cache.mkdir(parents=True,exist_ok=True)
    for label,step in [('main',cfg['main_step_s']),('refined',cfg['refined_step_s'])]:
        path=cache/f'{label}.npz'
        if not args.analyze_only:np.savez_compressed(path,**integrate_ensemble(cfg,step))
    with np.load(cache/'main.npz') as a,np.load(cache/'refined.npz') as b:
        main_data={k:a[k] for k in a.files};refined_data={k:b[k] for k in b.files}
    data=analyze(cfg,main_data,refined_data)
    (ROOT/'hug_robustness_results.json').write_text(json.dumps(data,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(counts=data['counts'],checks=data['checks'],cases=len(data['cases']))),flush=True)


if __name__=='__main__':main()
