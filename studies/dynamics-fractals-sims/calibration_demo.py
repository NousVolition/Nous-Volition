"""Clearly synthetic recordings for end-to-end calibration software checks.

Fixture motion uses a separately written RK45 physical ODE; creep is integrated
piecewise rather than using the calibration tool's exact recurrence.
"""
import copy
import json
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from hug_calibration import analyze, MATERIAL_KEYS

ROOT=Path(__file__).resolve().parent
TRUTH=dict(material=dict(zip(MATERIAL_KEYS,[28000.,5200000.,19000.,900000.])),
    mechanics=dict(effective_mass_kg=.2,parallel_stiffness_N_m=.7),
    feedback=dict(gain_N_s_m=.03,saturation_N_s_m3=3000000.,controller_delay_s=0.))


def initial(velocity=0.):
    return dict(known=True,delayed_strain=0.,viscous_strain=0.,velocity_mm_s=velocity,constant_delay_history_known=True)


def fixture():
    s=json.loads((ROOT/'calibration/blank_session.json').read_text(encoding='utf-8'))
    s.update(data_origin='synthetic',title='Synthetic software check — no physical observations',specimen_id='SIMULATED',trials=[])
    s['geometry']=dict(coupon_area_mm2=100.,coupon_gap_mm=10.,mode_length_mm=100.,mode_volume_mm3=100.)
    s['environment']=dict(water_mass_fraction=None,temperature_C=None)
    s['instrument']=dict(force_resolution_N=None,displacement_resolution_mm=None,sampling_note='No sensors: independently integrated, noiseless synthetic fixture')
    s['initial_guess'].update(effective_mass_kg=.24,parallel_stiffness_N_m=.6)
    s['acceptance']=dict(displacement_rmse_mm=.0001,force_rmse_N=1e-9)
    gm,em,gk,ek=[TRUTH['material'][k] for k in MATERIAL_KEYS]
    for name,role,peak,release in [('creep-fit-a','fit',20.,90.),('creep-fit-b','fit',30.,145.),('creep-held','validation',25.,110.)]:
        t=np.arange(0.,321.,2.);stress=np.interp(t,[0,8,release,release+8,320],[0,peak,peak,0,0])
        y=np.array([0.,0.]);q=[]
        for i,now in enumerate(t):
            if i:
                def rhs(tt,state):
                    sigma=np.interp(tt,t,stress);u,w=state
                    return [(sigma-gk*u)/ek,sigma/em]
                sol=solve_ivp(rhs,(t[i-1],now),y,rtol=1e-11,atol=1e-15,max_step=.5);y=sol.y[:,-1]
            q.append((stress[i]/gm+y.sum())*.01*1000)
        s['trials'].append(dict(id=name,kind='creep',role=role,initial=initial(),controller_delay_s=None,notes='SYNTHETIC load and recovery',samples=[dict(time_s=float(tt),force_N=float(sig*1e-4),displacement_mm=float(qq),velocity_mm_s=None,active_force_N=None,orbit_force_N=None) for tt,sig,qq in zip(t,stress,q)]))
    for name,role,amp in [('feedback-fit-a','fit',.10),('feedback-fit-b','fit',.16),('feedback-held','validation',.13)]:
        t=np.arange(0.,25.01,.2);omega=1.9;q=amp*1e-3*np.sin(omega*t);v=amp*1e-3*omega*np.cos(omega*t)
        force=(.03-3e6*q*q)*v
        s['trials'].append(dict(id=name,kind='feedback',role=role,initial=initial(),controller_delay_s=0.,notes='SYNTHETIC actuator characterization',samples=[dict(time_s=float(tt),force_N=0.,displacement_mm=float(qq*1000),velocity_mm_s=float(vv*1000),active_force_N=float(ff),orbit_force_N=0.) for tt,qq,vv,ff in zip(t,q,v,force)]))
    cases=[('passive-fit-a','passive','fit',.12),('passive-fit-b','passive','fit',-.09),('passive-held','passive','validation',.075),('auto-small','autonomous','validation',.025),('auto-large','autonomous','validation',.18),('circle-held','circular','validation',.07),('ecc-high','eccentric','validation',.07),('ecc-low','eccentric','validation',-.05)]
    for name,kind,role,q0 in cases:
        t=np.arange(0.,40.01 if kind=='passive' else 160.01,.2)
        orbital=np.zeros(len(t))
        if kind=='circular':orbital=6e-6*np.sin(2*np.pi*t/4.)
        if kind=='eccentric':
            e=.412 if name=='ecc-high' else .009;phase=2*np.pi*t/4.
            orbital=6e-6*(np.sin(phase)+e*np.sin(2*phase)) # laboratory waveform, not lunar reconstruction
        def rhs(now,state):
            q,v,u,w=state;stress=gm*(q/.1-u-w)
            active=0. if kind=='passive' else (.03-3e6*q*q)*v
            return [v,(-.7*q-1e-7*stress/.1+active+np.interp(now,t,orbital))/.2,(stress-gk*u)/ek,stress/em]
        sol=solve_ivp(rhs,(0,t[-1]),[q0*1e-3,0,0,0],t_eval=t,method='RK45',rtol=2e-10,atol=2e-14,max_step=.04)
        if not sol.success:raise RuntimeError(sol.message)
        q,v,u,w=sol.y;active=np.zeros(len(t)) if kind=='passive' else (.03-3e6*q*q)*v
        s['trials'].append(dict(id=name,kind=kind,role=role,initial=initial(),controller_delay_s=None if kind=='passive' else 0.,notes='SYNTHETIC; laboratory harmonic forcing; no physical/gravitational calibration',samples=[dict(time_s=float(tt),force_N=0.,displacement_mm=float(qq*1000),velocity_mm_s=float(vv*1000),active_force_N=float(ff),orbit_force_N=float(oo)) for tt,qq,vv,ff,oo in zip(t,q,v,active,orbital)]))
    return s


def main():
    session=fixture();report=analyze(session)
    (ROOT/'calibration/synthetic_demo.json').write_text(json.dumps(session,indent=2)+'\n',encoding='utf-8')
    (ROOT/'calibration/synthetic_results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (ROOT/'calibration/synthetic_truth.json').write_text(json.dumps(TRUTH,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','physical_calibration_established','pending')}))
    print(json.dumps({k:v['parameters'] for k,v in report['fits'].items()}))
    if report['status']!='synthetic_pipeline_passed':raise RuntimeError('Synthetic pipeline failed')


if __name__=='__main__':main()
