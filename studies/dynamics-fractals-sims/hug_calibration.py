"""Fit physical-unit Hug measurements; reserve whole trials for validation.

No entered measurements are automatically published. Outputs are written to
the caller's chosen directory. Synthetic fixtures test the pipeline only.
"""
import argparse
import bisect
import json
import math
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import expm
from scipy.optimize import least_squares

ROOT=Path(__file__).resolve().parent
KINDS=('creep','passive','feedback','autonomous','circular','eccentric')
MATERIAL_KEYS=('G_M_Pa','eta_M_Pa_s','G_K_Pa','eta_K_Pa_s')


def finite(value,label):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError(f'{label}: enter a finite number')
    return float(value)


def positive(value,label):
    value=finite(value,label)
    if value<=0:raise ValueError(f'{label}: must be positive')
    return value


def validate_session(session):
    if session.get('schema_version')!=1:raise ValueError('Unsupported measurement schema')
    if session.get('data_origin') not in ('physical','synthetic'):raise ValueError('Declare physical or synthetic data_origin')
    seen=set()
    for trial in session.get('trials',[]):
        label=trial.get('id','')
        if not isinstance(label,str) or not label.strip() or label in seen:raise ValueError('Trial IDs must be unique and nonempty')
        seen.add(label)
        if trial.get('kind') not in KINDS or trial.get('role') not in ('fit','validation'):raise ValueError(f'{label}: select test type and fit/validation role')
        if trial['role']=='fit' and trial['kind'] in ('autonomous','circular','eccentric'):raise ValueError(f'{label}: reserve active motion and orbit tests for validation')
        samples=trial.get('samples',[])
        if not samples:continue
        if len(samples)<12:raise ValueError(f'{label}: at least 12 samples required')
        required=['time_s','displacement_mm']
        if trial['kind'] in ('creep','passive','autonomous','circular','eccentric'):required+=['force_N']
        if trial['kind']=='feedback':required+=['velocity_mm_s','active_force_N']
        if trial['kind'] in ('circular','eccentric'):required+=['orbit_force_N']
        for i,sample in enumerate(samples):
            for key in required:finite(sample.get(key),f'{label} row {i+1} {key}')
            for key in ('force_N','velocity_mm_s','active_force_N','orbit_force_N'):
                if sample.get(key) is not None:finite(sample[key],f'{label} row {i+1} {key}')
        t=np.array([r['time_s'] for r in samples])
        if t[0]<0 or np.any(np.diff(t)<=0):raise ValueError(f'{label}: times must be nonnegative and strictly increasing')
        if trial['kind']!='feedback':
            initial=trial.get('initial',{})
            if initial.get('known') is not True:raise ValueError(f'{label}: initial clay memory and velocity must be documented')
            for key in ('delayed_strain','viscous_strain','velocity_mm_s'):finite(initial.get(key),f'{label}: initial {key}')
        if trial['kind']=='passive':
            if any(abs(r.get('active_force_N') or 0)>0 or abs(r.get('orbit_force_N') or 0)>0 for r in samples):
                raise ValueError(f'{label}: passive tests must have feedback and orbital forcing off')
        if trial['kind']=='autonomous' and any(abs(r.get('force_N',0))>1e-15 or abs(r.get('orbit_force_N') or 0)>1e-15 for r in samples):
            raise ValueError(f'{label}: autonomous tests must have external and orbital forcing off; split off the push')
        if trial['kind'] in ('feedback','autonomous','circular','eccentric'):
            delay=finite(trial.get('controller_delay_s'),f'{label}: measured controller delay')
            if delay<0:raise ValueError(f'{label}: controller delay cannot be negative')
            if delay>t[-1]-t[0]:raise ValueError(f'{label}: recording is shorter than the controller delay')
    return True


def columns(trial):
    samples=trial['samples'];t=np.array([r['time_s'] for r in samples]);t=t-t[0]
    q=np.array([r['displacement_mm'] for r in samples])*1e-3
    force=np.array([r.get('force_N') or 0 for r in samples])
    orbit=np.array([r.get('orbit_force_N') or 0 for r in samples])
    return t,q,force,orbit


def geometry(session,kind):
    g=session.get('geometry',{})
    if kind=='creep':return positive(g.get('coupon_area_mm2'),'Coupon shear area')*1e-6,positive(g.get('coupon_gap_mm'),'Coupon gap')*1e-3
    return positive(g.get('mode_length_mm'),'Effective shear length')*1e-3,positive(g.get('mode_volume_mm3'),'Effective sheared volume')*1e-9


def creep_prediction(session,trial,material):
    """Exact Burgers propagation for piecewise-linear measured stress."""
    t,q,force,_=columns(trial);area,gap=geometry(session,'creep');stress=force/area
    gm,em,gk,ek=[material[k] for k in MATERIAL_KEYS];rate=gk/ek
    u=trial['initial']['delayed_strain'];w=trial['initial']['viscous_strain']
    gamma=np.empty(len(t));gamma[0]=stress[0]/gm+u+w
    for i,dt in enumerate(np.diff(t),1):
        x=rate*dt;phi0=-math.expm1(-x)/rate
        phi1=dt*dt*(.5-x/6+x*x/24-x**3/120) if abs(x)<1e-3 else (dt-phi0)/rate
        slope=(stress[i]-stress[i-1])/dt
        u=u*math.exp(-x)+(stress[i-1]*phi0+slope*phi1)/ek
        w+=(stress[i-1]*dt+.5*slope*dt*dt)/em
        gamma[i]=stress[i]/gm+u+w
    return gamma*gap


def mechanical_matrix(material,mass,stiffness,length,volume):
    gm,em,gk,ek=[material[k] for k in MATERIAL_KEYS]
    return np.array([[0,1,0,0],[-(stiffness+volume*gm/length**2)/mass,0,volume*gm/(mass*length),volume*gm/(mass*length)],
        [gm/(ek*length),0,-(gm+gk)/ek,-gm/ek],
        [gm/(em*length),0,-gm/em,-gm/em]])


def passive_prediction(session,trial,material,mass,stiffness):
    """Exact linear motion for piecewise-linear measured external force."""
    t,q,force,_=columns(trial);length,volume=geometry(session,'motion')
    a=np.zeros((6,6));a[:4,:4]=mechanical_matrix(material,mass,stiffness,length,volume);a[1,4]=1/mass;a[4,5]=1
    initial=trial['initial'];y=np.array([q[0],initial['velocity_mm_s']*1e-3,initial['delayed_strain'],initial['viscous_strain']])
    output=np.empty((len(t),4));output[0]=y;cache={}
    for i,dt in enumerate(np.diff(t),1):
        key=round(float(dt),12)
        if key not in cache:cache[key]=expm(a*dt)
        y=(cache[key]@np.r_[y,force[i-1],(force[i]-force[i-1])/dt])[:4];output[i]=y
    return output


def fit_quality(jac):
    norms=np.linalg.norm(jac,axis=0)
    if np.any(norms<1e-12):return dict(identifiable=False,rank=0,condition=None)
    sv=np.linalg.svd(jac/norms,compute_uv=False);rank=int(np.sum(sv>sv[0]*1e-8))
    condition=float(sv[0]/sv[-1]) if sv[-1]>0 else None
    return dict(identifiable=rank==jac.shape[1] and condition is not None and condition<1e5,rank=rank,condition=condition)


def fit_positive(residual,guess,bounds):
    fit=least_squares(lambda log:residual(np.exp(log)),np.log(guess),
        bounds=np.log(np.asarray(bounds)),xtol=1e-10,ftol=1e-10,gtol=1e-10,max_nfev=250)
    quality=fit_quality(fit.jac)
    if not fit.success or not quality['identifiable']:raise ValueError('The fit is not sufficiently identified; collect richer load/recovery trials')
    if np.min(np.minimum(fit.x-np.log(bounds[0]),np.log(bounds[1])-fit.x))<1e-5:raise ValueError('Fit reached a parameter bound; review the data/model')
    return np.exp(fit.x),quality


def fit_material(session,trials):
    geometry(session,'creep');guess=session.get('initial_guess',{}).get('material',{})
    start=[positive(guess.get(k),f'Starting guess {k}') for k in MATERIAL_KEYS]
    def residual(values):
        material=dict(zip(MATERIAL_KEYS,values));errors=[]
        for trial in trials:
            _,q,_,_=columns(trial);scale=max(np.ptp(q),1e-9)*math.sqrt(len(q))
            errors.extend((creep_prediction(session,trial,material)-q)/scale)
        return np.array(errors)
    values,quality=fit_positive(residual,start,[[10,100,10,100],[1e9,1e13,1e9,1e13]])
    return dict(parameters=dict(zip(MATERIAL_KEYS,map(float,values))),fit_trial_ids=[t['id'] for t in trials],quality=quality)


def fit_mechanics(session,trials,material):
    geometry(session,'motion');guess=session.get('initial_guess',{})
    start=[positive(guess.get('effective_mass_kg'),'Mass starting guess'),positive(guess.get('parallel_stiffness_N_m'),'Stiffness starting guess')]
    def residual(values,recordings=trials):
        errors=[]
        for trial in recordings:
            _,q,_,_=columns(trial);scale=max(np.ptp(q),1e-9)*math.sqrt(len(q))
            errors.extend((passive_prediction(session,trial,material,*values)[:,0]-q)/scale)
        return np.array(errors)
    bounds=[[1e-6,1e-6],[1e4,1e8]]
    # Long oscillatory records can trap a frequency fit in a wrong phase basin.
    # Warm-start on the first tenth of fitting data, then fit every fitting row.
    # Held-out recordings never enter either optimization.
    short=[dict(t,samples=t['samples'][:max(12,math.ceil(len(t['samples'])/10))]) for t in trials]
    warm=least_squares(lambda log:residual(np.exp(log),short),np.log(start),bounds=np.log(np.asarray(bounds)),max_nfev=150)
    values,quality=fit_positive(residual,np.exp(warm.x),bounds)
    return dict(parameters=dict(effective_mass_kg=float(values[0]),parallel_stiffness_N_m=float(values[1])),fit_trial_ids=[t['id'] for t in trials],quality=quality)


def feedback_arrays(trial):
    t,q,_,_=columns(trial);delay=trial['controller_delay_s'];mask=t>=delay
    v=np.array([r['velocity_mm_s'] for r in trial['samples']])*1e-3
    lagq=np.interp(t[mask]-delay,t,q);lagv=np.interp(t[mask]-delay,t,v)
    return np.column_stack([lagv,-lagq*lagq*lagv]),np.array([r['active_force_N'] for r in trial['samples']])[mask],mask


def fit_feedback(trials):
    delays={t['controller_delay_s'] for t in trials}
    if len(delays)!=1:raise ValueError('Fit separate controllers/sessions when their measured delays differ')
    pairs=[feedback_arrays(t) for t in trials];x=np.vstack([r[0] for r in pairs]);force=np.concatenate([r[1] for r in pairs])
    quality=fit_quality(x)
    if not quality['identifiable']:raise ValueError('Feedback coefficients require different amplitudes and nonzero velocities')
    norms=np.linalg.norm(x,axis=0);scaled,_,_,_=np.linalg.lstsq(x/norms,force,rcond=None);values=scaled/norms
    if np.any(values<=0):raise ValueError('Measurements do not identify positive small-motion gain and positive saturation')
    return dict(parameters=dict(gain_N_s_m=float(values[0]),saturation_N_s_m3=float(values[1]),
        transition_displacement_mm=float(math.sqrt(values[0]/values[1])*1000),controller_delay_s=float(next(iter(delays)))),
        fit_trial_ids=[t['id'] for t in trials],quality=quality)


def active_prediction(session,trial,material,mechanics,feedback):
    """Predict active force from state feedback, never from measured active force.

    For positive measured delay use the method of steps with declared constant
    initial history. Orbital/external loads remain measured conditional inputs.
    """
    t,q,force,orbit=columns(trial);length,volume=geometry(session,'motion')
    mass=mechanics['effective_mass_kg'];stiffness=mechanics['parallel_stiffness_N_m']
    matrix=mechanical_matrix(material,mass,stiffness,length,volume)
    initial=trial['initial'];y=np.array([q[0],initial['velocity_mm_s']*1e-3,initial['delayed_strain'],initial['viscous_strain']])
    delay=feedback['controller_delay_s']
    if not math.isclose(trial['controller_delay_s'],delay,abs_tol=1e-12):raise ValueError('Validation controller delay differs from fitted controller')
    if delay>0 and initial.get('constant_delay_history_known') is not True:raise ValueError('Delayed prediction requires documented initial controller history')
    if delay>0 and t[-1]/delay>10000:raise ValueError('Delay prediction exceeds 10000 intervals; rescale recording or use a dedicated delay solver')
    segments=[];ends=[];history=y.copy()
    def rhs(now,state):
        if delay==0:lag=state
        elif now-delay<=0:lag=history
        else:
            index=min(bisect.bisect_left(ends,now-delay),len(segments)-1)
            lag=segments[index].sol(now-delay)
        active=(feedback['gain_N_s_m']-feedback['saturation_N_s_m3']*lag[0]**2)*lag[1]
        dy=matrix@state;dy[1]+=(np.interp(now,t,force+orbit)+active)/mass
        return dy
    begin=0.;step=t[-1] if delay==0 else delay
    while begin<t[-1]-1e-12:
        end=min(begin+step,t[-1]);sol=solve_ivp(rhs,(begin,end),y,method='DOP853',rtol=2e-9,atol=2e-12,max_step=min(.05,float(np.min(np.diff(t)))),dense_output=True)
        if not sol.success:raise ValueError('Active forward prediction did not converge')
        segments.append(sol);ends.append(end);y=sol.y[:,-1];begin=end
    output=np.empty((len(t),4))
    for i,now in enumerate(t):output[i]=segments[min(bisect.bisect_left(ends,now),len(segments)-1)].sol(now)
    return output


def motion_summary(t,q):
    # Upward crossings of measured zero reference; interpolate crossing times.
    ids=np.where((q[:-1]<=0)&(q[1:]>0))[0]
    crossings=t[ids]-q[ids]*(t[ids+1]-t[ids])/(q[ids+1]-q[ids])
    periods=np.diff(crossings[-7:])
    return dict(positive_crossings=len(crossings),late_mean_period_s=float(np.mean(periods)) if len(periods)>=3 else None,
        late_period_cv=float(np.std(periods)/np.mean(periods)) if len(periods)>=3 else None,
        peak_displacement_mm=float(np.max(np.abs(q))*1000))


def analyze(session):
    validate_session(session)
    report=dict(data_origin=session['data_origin'],session_title=session.get('title',''),
        physical_calibration_established=False,status='awaiting_measurements',fits={},validation=[],pending=[],fit_trial_ids=[])
    trials=[t for t in session.get('trials',[]) if t.get('samples')]
    if not trials:
        report['pending']=['Enter measured trials; the blank template contains no observations.'];return report
    groups={kind:[t for t in trials if t['kind']==kind and t['role']=='fit'] for kind in KINDS}
    fits=report['fits']
    for kind in ('creep','passive','feedback'):
        if not groups[kind]:report['pending'].append(f'Add {kind} fitting trials');continue
        try:
            if kind=='creep':fits[kind]=fit_material(session,groups[kind])
            elif kind=='passive':
                if 'creep' not in fits:report['pending'].append('Passive mechanics needs the fitted clay coefficients');continue
                fits[kind]=fit_mechanics(session,groups[kind],fits['creep']['parameters'])
            else:fits[kind]=fit_feedback(groups[kind])
        except ValueError as error:report['pending'].append(f'{kind}: {error}')
    report['fit_trial_ids']=[t['id'] for kind in ('creep','passive','feedback') for t in groups[kind]]
    for trial in [t for t in trials if t['role']=='validation']:
        kind=trial['kind'];result=dict(id=trial['id'],kind=kind,status='pending')
        try:
            t,q,_,_=columns(trial)
            if kind=='feedback':
                if kind not in fits:raise ValueError('Fit feedback first')
                x,observed,mask=feedback_arrays(trial);pars=fits[kind]['parameters']
                if trial['controller_delay_s']!=pars['controller_delay_s']:raise ValueError('Validation controller delay differs')
                predicted=x@np.array([pars['gain_N_s_m'],pars['saturation_N_s_m3']]);unit='N';metric='force_rmse_N';times=t[mask]
            else:
                if 'creep' not in fits:raise ValueError('Fit clay first')
                clay=fits['creep']['parameters'];observed=q*1000;times=t;unit='mm';metric='displacement_rmse_mm'
                if kind=='creep':predicted=creep_prediction(session,trial,clay)*1000
                elif kind=='passive':
                    if 'passive' not in fits:raise ValueError('Fit passive mechanics first')
                    predicted=passive_prediction(session,trial,clay,**dict(mass=fits['passive']['parameters']['effective_mass_kg'],stiffness=fits['passive']['parameters']['parallel_stiffness_N_m']))[:,0]*1000
                else:
                    if 'passive' not in fits or 'feedback' not in fits:raise ValueError('Fit mechanics and feedback first')
                    predicted=active_prediction(session,trial,clay,fits['passive']['parameters'],fits['feedback']['parameters'])[:,0]*1000
                    result['observed_motion']=motion_summary(t,q);result['predicted_motion']=motion_summary(t,predicted*1e-3)
                    if all(r.get('active_force_N') is not None for r in trial['samples']):
                        work=float(np.trapezoid(np.array([r['active_force_N'] for r in trial['samples']]),q))
                        result['measured_active_work_J']=work
            error=predicted-observed;rmse=float(np.sqrt(np.mean(error*error)))
            limit=session.get('acceptance',{}).get(metric)
            if limit is not None:limit=positive(limit,metric)
            result.update(rmse=rmse,max_absolute_error=float(np.max(np.abs(error))),units=unit,
                acceptance_limit=limit,status='passed' if limit is not None and rmse<=limit else 'failed' if limit is not None else 'tolerance_not_set',
                time_s=times.tolist(),observed=observed.tolist(),predicted=predicted.tolist())
        except (ValueError,KeyError) as error:result['reason']=str(error)
        report['validation'].append(result)
    kinds={r['kind'] for r in report['validation'] if r['status']=='passed'}
    complete=all(k in fits for k in ('creep','passive','feedback')) and all(k in kinds for k in KINDS) and all(r['status']=='passed' for r in report['validation'])
    report['status']='synthetic_pipeline_passed' if complete and session['data_origin']=='synthetic' else 'measured_predictions_passed' if complete else 'incomplete_or_failed_validation'
    # Passed recordings support only this declared mode and tested domain;
    # physical limit-cycle existence/contact mechanics are not established here.
    report['physical_calibration_established']=complete and session['data_origin']=='physical'
    report['scope']='Conditional predictions for the recorded modes and loads; not proof of a physical limit cycle, contact strength, or tidal calibration.'
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('session',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    session=json.loads(args.session.read_text(encoding='utf-8-sig'));report=analyze(session)
    args.output.mkdir(parents=True,exist_ok=True);(args.output/'calibration_results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','data_origin','physical_calibration_established','pending')}))


if __name__=='__main__':main()
