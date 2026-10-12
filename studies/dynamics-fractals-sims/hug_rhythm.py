"""Synthetic-observation rhythm tests with fixed previously fitted parameters."""
import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp, quad
from scipy.optimize import root
from active_hug import raw_tide, tide_rms
from orbits import protocol as orbit_protocol

ROOT=Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def protocol():return json.loads((ROOT/'hug_rhythm_protocol.json').read_text())


class Model:
    """State q/Q, qdot/Q, u/(Q/L), w/(Q/L); time remains seconds."""
    def __init__(self,parameters,passive=False):
        p=protocol();m=parameters['material'];f=parameters['feedback'];mechanics=parameters['mechanics']
        if f['controller_delay_s']!=0:raise ValueError('This rhythm experiment requires the calibrated zero-delay fixture')
        self.gm=m['G_M_Pa'];self.em=m['eta_M_Pa_s'];self.gk=m['G_K_Pa'];self.ek=m['eta_K_Pa_s']
        self.mass=mechanics['effective_mass_kg'];self.k=mechanics['parallel_stiffness_N_m']
        self.gain=0. if passive else f['gain_N_s_m'];self.saturation=0. if passive else f['saturation_N_s_m3']
        self.length=p['effective_shear_length_m'];self.volume=p['effective_sheared_volume_m3'];self.qscale=p['displacement_scale_m']
        self.scale=np.array([self.qscale,self.qscale,self.qscale/self.length,self.qscale/self.length])
        self.ck=self.volume*self.gm/self.length**2
        self.energy_scale=(self.k+self.ck)*self.qscale**2

    def rhs(self,t,z,force=0.):
        x,v,u,w=z[:4];s=x-u-w
        du=(self.gm*s-self.gk*u)/self.ek;dw=self.gm*s/self.em
        active=(self.gain-self.saturation*self.qscale**2*x*x)*v
        out=[v,(-self.k*x-self.ck*s+active+force/self.qscale)/self.mass,du,dw]
        if len(z)==7:
            qspeed=self.qscale*v;sigma=self.gm*self.qscale/self.length*s
            out.extend([active*self.qscale*qspeed/self.energy_scale,force*qspeed/self.energy_scale,
                self.volume*((sigma-self.gk*u*self.qscale/self.length)**2/self.ek+sigma**2/self.em)/self.energy_scale])
        return np.array(out)

    def jacobian(self,z):
        x,v,_,_=z[:4];b=self.saturation*self.qscale**2
        return np.array([[0,1,0,0],[-(self.k+self.ck+2*b*x*v)/self.mass,(self.gain-b*x*x)/self.mass,self.ck/self.mass,self.ck/self.mass],
            [self.gm/self.ek,0,-(self.gm+self.gk)/self.ek,-self.gm/self.ek],[self.gm/self.em,0,-self.gm/self.em,-self.gm/self.em]])

    def energy(self,z):
        a=np.asarray(z)[...,:4]*self.scale;q,v,u,w=np.moveaxis(a,-1,0);sigma=self.gm*(q/self.length-u-w)
        return (.5*self.mass*v*v+.5*self.k*q*q+.5*self.volume*(sigma*sigma/self.gm+self.gk*u*u))/self.energy_scale


def force_at(t,e,period):
    if e is None:return 0.
    return protocol()['orbital_force_rms_N']*raw_tide(t/period,e)/tide_rms(e)


def integrate(model,start,end=None,e=None,period=None,begin=0.,energy=True):
    cfg=protocol();s=cfg['solver'];end=cfg['horizon_s'] if end is None else end;period=cfg['orbit_period_s'] if period is None else period
    def crossing(t,z):return z[0]
    crossing.direction=1
    y=np.r_[start,0.,0.,0.] if energy else np.asarray(start)
    sol=solve_ivp(lambda t,z:model.rhs(t,z,force_at(t,e,period)),(begin,end),y,method=s['method'],rtol=s['rtol'],atol=s['atol'],max_step=s['max_step_s'],events=crossing,dense_output=True)
    if not sol.success:raise RuntimeError(sol.message)
    return sol


def measurement_metrics(t,q,noise_sd=0.):
    """Crossings with hysteresis avoid counting noise repeatedly at zero."""
    t=np.asarray(t);q=np.asarray(q)
    if len(t)<12 or len(q)!=len(t) or np.any(np.diff(t)<=0) or not np.all(np.isfinite(t)) or not np.all(np.isfinite(q)):raise ValueError('Finite regularly ordered observations required')
    half=float(np.ptp(q)/2)
    if half<=max(5*noise_sd,1e-7):return dict(status='signal_below_detection',cycles=0)
    threshold=.2*half;armed=False;crossings=[];indices=[]
    for i in range(1,len(t)):
        if q[i]<-threshold:armed=True
        if armed and q[i-1]<=0<q[i]:
            crossings.append(float(t[i-1]-q[i-1]*(t[i]-t[i-1])/(q[i]-q[i-1])));indices.append(i);armed=False
    if len(crossings)<5:return dict(status='insufficient_cycles',cycles=max(0,len(crossings)-1))
    periods=np.diff(crossings);amps=np.array([np.ptp(q[a:b+1])/2 for a,b in zip(indices[:-1],indices[1:])])
    n=len(periods)//2
    return dict(status='measured',cycles=len(periods),mean_period_s=float(np.mean(periods)),period_cv=float(np.std(periods)/np.mean(periods)),
        mean_half_amplitude_mm=float(np.mean(amps)),amplitude_cv=float(np.std(amps)/np.mean(amps)),
        period_drift_fraction=float(abs(np.mean(periods[:n])-np.mean(periods[-n:]))/np.mean(periods)),
        crossing_times_s=crossings)


def energy_error(model,sol):
    t=np.linspace(sol.t[0],sol.t[-1],1201);z=sol.sol(t).T
    r=model.energy(z)-model.energy(z[0])-z[:,4]-z[:,5]+z[:,6]
    return float(np.max(np.abs(r)))


def shoot(model,seed,period):
    def residual(a):
        y=np.r_[0,a[:3]];duration=float(np.exp(a[3]))
        sol=solve_ivp(lambda t,z:model.rhs(t,z),(0,duration),y,method='DOP853',rtol=2e-12,atol=2e-14,max_step=.04)
        if not sol.success:raise RuntimeError(sol.message)
        return sol.y[:,-1]-y
    fit=root(residual,np.r_[seed[1:4],np.log(period)],tol=1e-10)
    error=float(np.max(np.abs(residual(fit.x))));y=np.r_[0,fit.x[:3]];period=float(np.exp(fit.x[3]))
    if error>1e-7 or y[1]<=0:raise RuntimeError('Periodic shooting did not locate the positive nontrivial cycle')
    def variational(t,z):return np.r_[model.rhs(t,z[:4]),(model.jacobian(z[:4])@z[4:].reshape(4,4)).ravel()]
    sol=solve_ivp(variational,(0,period),np.r_[y,np.eye(4).ravel()],method='DOP853',rtol=2e-12,atol=2e-14,max_step=.025,dense_output=True)
    eig=np.linalg.eigvals(sol.y[4:,-1].reshape(4,4));neutral=int(np.argmin(np.abs(eig-1)));transverse=np.delete(eig,neutral)
    def power(t,index):return model.rhs(t,np.r_[sol.sol(t)[:4],0,0,0])[index]
    active=quad(lambda t:power(t,4),0,period,epsabs=1e-11,epsrel=1e-11)[0]
    dissipated=quad(lambda t:power(t,6),0,period,epsabs=1e-11,epsrel=1e-11)[0]
    return dict(period_s=period,section_state_scaled=y.tolist(),shooting_error_scaled=error,
        floquet_multipliers=[[float(e.real),float(e.imag)] for e in eig],neutral_multiplier_error=float(abs(eig[neutral]-1)),
        largest_transverse_multiplier=float(max(abs(transverse))),active_work_per_cycle_J=active*model.energy_scale,
        dissipated_energy_per_cycle_J=dissipated*model.energy_scale,cycle_energy_mismatch_scaled=abs(active-dissipated),
        cycle_time_s=np.linspace(0,period,301).tolist(),cycle_state_scaled=sol.sol(np.linspace(0,period,301))[:4].T.tolist())


def stroboscopic(sol,e,period):
    t=sol.t[-1]-np.arange(40,-1,-1)*period;z=sol.sol(t)[:4].T
    errors={str(n):float(np.max(np.abs(z[-20:]-z[-20-n:-n]))) for n in range(1,5)}
    repeat=next((int(n) for n,error in errors.items() if error<protocol()['gates']['orbit_repeat_error_scaled']),None)
    crossings=sol.t_events[0];crossings=crossings[crossings>=t[0]]
    return dict(period_s=period,return_errors_scaled=errors,repeat_orbits=repeat,
        classification='orbit-periodic within tolerance' if repeat else 'no repeat found over one to four orbits',
        mean_upward_crossings_per_orbit=float((len(crossings)-1)*period/(crossings[-1]-crossings[0])) if len(crossings)>1 else None,
        times_s=t.tolist(),state_scaled=z.tolist())


def independent_control(model,sol,e,period):
    begin=sol.t[-1]-12.;end=sol.t[-1];start=sol.sol(begin)[:4]*model.scale
    def physical_rhs(t,z):
        q,v,u,w=z;sigma=model.gm*(q/model.length-u-w);active=(model.gain-model.saturation*q*q)*v
        return [v,(-model.k*q-model.volume*sigma/model.length+active+force_at(t,e,period))/model.mass,
            (sigma-model.gk*u)/model.ek,sigma/model.em]
    check=solve_ivp(physical_rhs,(begin,end),start,method='Radau',rtol=2e-10,atol=2e-15,max_step=.04,dense_output=True)
    if not check.success:raise RuntimeError(check.message)
    t=np.linspace(begin,end,241)
    return float(np.max(np.abs(check.sol(t).T/model.scale-sol.sol(t)[:4].T)))


def observed_case(name,sol,model,prediction=None,e=None,period=None,seed_offset=0):
    cfg=protocol();dt=cfg['sample_interval_s'];end=sol.t[-1];t=np.arange(end-cfg['observation_window_s'],end+dt/2,dt)
    clean=sol.sol(t)[0]*model.qscale*1000;base=measurement_metrics(t,clean)
    noisy_metrics=[];representative=None
    for sd in cfg['measurement_noise_sd_mm']:
        for seed in cfg['measurement_noise_seeds']:
            noise=np.random.default_rng(seed+seed_offset).normal(0,sd,len(t));noisy=clean+noise;metrics=measurement_metrics(t,noisy,sd)
            metrics.update(noise_sd_mm=sd,seed=seed+seed_offset)
            if metrics['status']=='measured' and base['status']=='measured':
                metrics.update(period_relative_error=abs(metrics['mean_period_s']/base['mean_period_s']-1),amplitude_relative_error=abs(metrics['mean_half_amplitude_mm']/base['mean_half_amplitude_mm']-1))
            noisy_metrics.append(metrics)
            if sd==cfg['measurement_noise_sd_mm'][-1] and seed==cfg['measurement_noise_seeds'][0]:representative=noisy
    tt=np.arange(0,60+dt/2,dt);early=sol.sol(tt)[0]*model.qscale*1000
    out=dict(name=name,eccentricity=e,orbit_period_s=period,recording_duration_s=end,clean_metrics=base,measurement_noise_checks=noisy_metrics,
        energy_balance_error_scaled=energy_error(model,sol),
        observation=dict(time_s=np.round(t,7).tolist(),clean_displacement_mm=np.round(clean,9).tolist(),measured_displacement_mm=np.round(representative,9).tolist()),
        early_trace=dict(time_s=np.round(tt,7).tolist(),displacement_mm=np.round(early,9).tolist()))
    if prediction is not None:
        predicted=prediction.sol(t)[0]*model.qscale*1000;out['observation']['predicted_displacement_mm']=np.round(predicted,9).tolist()
        out['prediction_rmse_mm']=float(np.sqrt(np.mean((predicted-clean)**2)));out['predicted_metrics']=measurement_metrics(t,predicted)
    if e is not None:out['orbit_repeat']=stroboscopic(sol,e,period)
    out['independent_solver_error_scaled']=independent_control(model,sol,e,period)
    return out


def validate(data):
    g=protocol()['gates'];cycle=data['autonomous_cycle']
    checks=dict(shooting=cycle['shooting_error_scaled']<g['shooting_error_scaled'],
        neutral_multiplier=cycle['neutral_multiplier_error']<g['neutral_multiplier_error'],
        attracting_cycle=cycle['largest_transverse_multiplier']<g['largest_transverse_multiplier'],
        cycle_energy=cycle['cycle_energy_mismatch_scaled']<g['energy_balance_error_scaled'],
        multiple_starts=max(r['distance_to_cycle_scaled'] for r in data['autonomous_starts'])<g['section_recovery_error_scaled'],
        disturbed_return=data['disturbance']['distance_to_cycle_scaled']<g['section_recovery_error_scaled'],
        passive_decay=data['passive']['final_norm_scaled']<g['passive_final_norm_scaled'],
        energy_balance=max(r['energy_balance_error_scaled'] for r in data['cases'])<g['energy_balance_error_scaled'],
        independent_solver=max(r['independent_solver_error_scaled'] for r in data['cases'])<g['independent_solver_error_scaled'],
        fixed_parameter_prediction=max(r.get('prediction_rmse_mm',0) for r in data['cases'])<g['parameter_prediction_rmse_mm'],
        noise_period=all(r['status']=='measured' and r['period_relative_error']<g['noise_period_relative_error'] for c in data['cases'] for r in c['measurement_noise_checks']),
        noise_amplitude=all(r['status']=='measured' and r['amplitude_relative_error']<g['noise_amplitude_relative_error'] for c in data['cases'] for r in c['measurement_noise_checks']))
    return checks


def run():
    cfg=protocol();truth=json.loads((ROOT/cfg['truth_source']).read_text());cal=json.loads((ROOT/cfg['calibration_source']).read_text())
    if cal['data_origin']!='synthetic' or cal['status']!='synthetic_pipeline_passed':raise ValueError('Require the completed synthetic calibration')
    fitted=dict(material=cal['fits']['creep']['parameters'],mechanics=cal['fits']['passive']['parameters'],feedback=cal['fits']['feedback']['parameters'])
    model=Model(truth);predictor=Model(fitted);data=dict(origin='synthetic',physical_measurements=0,additional_sims_runs=0,protocol=cfg,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [cfg['truth_source'],cfg['calibration_source'],'orbit_protocol.json']},
        fitted_parameters=fitted,fit_trial_ids=cal['fit_trial_ids'],cases=[],autonomous_starts=[])
    print('Autonomous starts and periodic orbit',flush=True)
    sols=[integrate(model,start,end=cfg['memory_control_horizon_s'] if i==2 else cfg['horizon_s']) for i,start in enumerate(cfg['starts_scaled'])]
    cycle=shoot(model,sols[0].y_events[0][-1,:4],float(np.diff(sols[0].t_events[0])[-1]));data['autonomous_cycle']=cycle
    for i,sol in enumerate(sols):
        data['autonomous_starts'].append(dict(index=i,start_scaled=cfg['starts_scaled'][i],distance_to_cycle_scaled=float(np.max(np.abs(sol.y_events[0][-1,:4]-cycle['section_state_scaled']))),late_period_s=float(np.diff(sol.t_events[0])[-1])))
    pred=integrate(predictor,cfg['starts_scaled'][0]);data['cases'].append(observed_case('No orbit',sols[0],model,pred))
    for i in (1,2):data['cases'].append(observed_case('No orbit — start '+str(i+1),sols[i],model,seed_offset=i*10))
    kick=np.array(cycle['section_state_scaled'])+cfg['kick_scaled'];recovery=integrate(model,kick,end=cfg['memory_control_horizon_s'])
    data['disturbance']=dict(kick_scaled=cfg['kick_scaled'],distance_to_cycle_scaled=float(np.max(np.abs(recovery.y_events[0][-1,:4]-cycle['section_state_scaled']))),
        crossing_time_s=recovery.t_events[0].tolist(),section_distance_scaled=np.max(np.abs(recovery.y_events[0][:,:4]-cycle['section_state_scaled']),axis=1).tolist())
    passive_model=Model(truth,True);passive=integrate(passive_model,cfg['starts_scaled'][1],end=cfg['memory_control_horizon_s']);data['passive']=dict(final_norm_scaled=float(np.linalg.norm(passive.y[:4,-1])),energy_balance_error_scaled=energy_error(passive_model,passive),time_s=np.linspace(0,180,1801).tolist(),displacement_mm=(passive.sol(np.linspace(0,180,1801))[0]*model.qscale*1000).tolist())
    section=np.array(cycle['section_state_scaled']);original_end=cfg['horizon_s']
    data['initial_horizon_audit']=dict(horizon_s=original_end,gate_scaled=cfg['gates']['section_recovery_error_scaled'],
        memory_start_error_scaled=float(np.max(np.abs(sols[2].y_events[0][sols[2].t_events[0]<=original_end][-1,:4]-section))),
        disturbed_return_error_scaled=float(np.max(np.abs(recovery.y_events[0][recovery.t_events[0]<=original_end][-1,:4]-section))),
        passive_final_norm_scaled=float(np.linalg.norm(passive.sol(original_end)[:4])))
    cases=[('Circular',0.,cfg['orbit_period_s'])]+[(m['name'],m['e'],cfg['orbit_period_s']) for m in orbit_protocol()['moons']]+[('Circular — detuned control',0.,cfg['detuned_orbit_period_s']),('Pasiphae — detuned control',.412,cfg['detuned_orbit_period_s'])]
    for i,(name,e,period) in enumerate(cases):
        print('Rhythm recording: '+name,flush=True)
        sol=integrate(model,cfg['starts_scaled'][0],e=e,period=period);pred=integrate(predictor,cfg['starts_scaled'][0],e=e,period=period)
        data['cases'].append(observed_case(name,sol,model,pred,e,period,100+i*10))
    data['checks']=validate(data);data['status']='passed' if all(data['checks'].values()) else 'failed_checks_retained'
    return data


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if args.check:
        d=json.loads((ROOT/'hug_rhythm_results.json').read_text());checks=validate(d);print(json.dumps(checks));assert all(checks.values());return
    data=run();(ROOT/'hug_rhythm_results.json').write_text(json.dumps(data,separators=(',',':'))+'\n',encoding='utf-8');print(json.dumps(dict(status=data['status'],checks=data['checks'],period_s=data['autonomous_cycle']['period_s'])))


if __name__=='__main__':main()
