"""Direct orbital loading, deformation and recovery of the current clay Hug."""
import argparse
import copy
import json
from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy.integrate import quad,solve_ivp
from orbits import protocol as orbit_protocol,load_factor
from clay_sims import source as clay
from hug_sims import source as hug_geometry
from bridge_checks import compare_saved

ROOT=Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def protocol():return json.loads((ROOT/'hug_orbit_protocol.json').read_text())


def cases():
    return [('Circular control',0.)]+[(m['name'],m['e']) for m in orbit_protocol()['moons']]


def load(t,e,m,side='right'):
    if t<clay.START or t>clay.RELEASE or (t==clay.START and side=='left') or (t==clay.RELEASE and side=='right'):
        return 0.
    return m['stress_Pa']*float(load_factor((t-clay.START)/clay.HOLD,e))


def trajectory(m,e,method='DOP853'):
    """Scalar material ODE, split at both jumps; no participant coupling."""
    grid=clay.sample_times();times=np.array([t for t,_ in grid]);z=np.zeros((len(grid),2))
    def rhs(t,y,s):return [(s-m['G_K_Pa']*y[0])/m['eta_K_Pa_s'],s/m['eta_M_Pa_s']]
    loading=solve_ivp(lambda t,y:rhs(t,y,load(t,e,m,'left')),(clay.START,clay.RELEASE),[0.,0.],
                      method=method,rtol=2e-12,atol=2e-15,max_step=.25,dense_output=True)
    if not loading.success:raise RuntimeError(loading.message)
    mask=(times>=clay.START)&(times<=clay.RELEASE);z[mask]=loading.sol(times[mask]).T
    recovery=solve_ivp(lambda t,y:rhs(t,y,0.),(clay.RELEASE,clay.END),loading.y[:,-1],
                       method=method,rtol=2e-12,atol=2e-15,max_step=1.,dense_output=True)
    if not recovery.success:raise RuntimeError(recovery.message)
    mask=times>clay.RELEASE;z[mask]=recovery.sol(times[mask]).T
    pressure=np.array([load(t,e,m,side) for t,side in grid])
    return z,pressure,loading


def convolution(m,e,t):
    end=min(t,clay.RELEASE)
    if end<=clay.START:return np.zeros(2)
    rate=m['G_K_Pa']/m['eta_K_Pa_s']
    u=quad(lambda s:load(s,e,m)*np.exp(-rate*(t-s))/m['eta_K_Pa_s'],clay.START,end,epsabs=1e-14,epsrel=2e-12)[0]
    w=quad(lambda s:load(s,e,m)/m['eta_M_Pa_s'],clay.START,end,epsabs=1e-14,epsrel=2e-12)[0]
    return np.array([u,w])


def outline(gamma,magnification=1):
    a,b=hug_geometry.arm_points(1,points=protocol()['points_per_arm'])
    return [clay.shear_points(arm,gamma,magnification) for arm in (a,b)]


def area(arms):
    p=np.array(arms[0]+arms[1][::-1])
    return abs(np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1)))/2


def geometry_checks(gammas):
    original=area(outline(0));max_gap=0.;max_area=0.
    for mag in protocol()['magnifications_checked']:
        for g in gammas:
            arms=outline(float(g),mag)
            max_gap=max(max_gap,float(np.linalg.norm(np.array(arms[0][0])-arms[1][0])),
                        float(np.linalg.norm(np.array(arms[0][-1])-arms[1][-1])))
            max_area=max(max_area,abs(area(arms)/original-1))
    return {'max_join_gap':max_gap,'max_relative_area_error':max_area,
            'checked_outline_states':len(gammas)*len(protocol()['magnifications_checked'])}


def energy_budget(m,e,z,sol):
    """Material work/dissipation quadrature, with work at elastic load jumps."""
    gm,gk,em,ek=(m[k] for k in ('G_M_Pa','G_K_Pa','eta_M_Pa_s','eta_K_Pa_s'))
    def rates(t):
        s=load(t,e,m,'left');u=sol.sol(t)[0]
        return s,(s-gk*u)/ek,s/em
    # The elastic continuous work is an exact endpoint term, not a sampled derivative.
    s0=load(clay.START,e,m);s1=load(clay.RELEASE,e,m,'left')
    jump_on=.5*s0*s0/gm;jump_off=-.5*s1*s1/gm
    continuous_elastic=.5*(s1*s1-s0*s0)/gm
    internal_work=quad(lambda t: rates(t)[0]*(rates(t)[1]+rates(t)[2]),20,120,epsabs=1e-13,epsrel=2e-11)[0]
    loading_loss=quad(lambda t:ek*rates(t)[1]**2+em*rates(t)[2]**2,20,120,epsabs=1e-13,epsrel=2e-11)[0]
    recovery_loss=.5*gk*(sol.y[0,-1]**2-z[-1,0]**2)
    final_energy=.5*gk*z[-1,0]**2
    work=jump_on+jump_off+continuous_elastic+internal_work
    loss=loading_loss+recovery_loss
    return {'jump_work_on_J_m3':jump_on,'jump_work_off_J_m3':jump_off,
            'continuous_work_J_m3':continuous_elastic+internal_work,'total_work_J_m3':work,
            'dissipation_J_m3':loss,'final_stored_energy_J_m3':final_energy,
            'energy_budget_error_J_m3':abs(final_energy-work+loss)}


def run():
    cfg=protocol()
    if cfg['material_rows_stress_Pa']!=[m['stress_Pa'] for m in clay.materials()]:raise ValueError('Material rows changed')
    if cfg['cases']!=[name for name,_ in cases()]:raise ValueError('Orbital cases changed')
    if cfg['schedule_seconds']!={'rest':clay.START,'loading':clay.HOLD,'recovery':clay.END-clay.RELEASE}:raise ValueError('Schedule changed')
    grid=clay.sample_times();times=np.array([t for t,_ in grid]);rows=[]
    for m in clay.materials():
        for name,e in cases():
            z,s,sol=trajectory(m,e);gamma=s/m['G_M_Pa']+z.sum(axis=-1)
            az,ap,_=trajectory(m,e,'Radau');ag=ap/m['G_M_Pa']+az.sum(axis=-1)
            solver_error=float(max(np.max(np.abs(z-az)),np.max(np.abs(gamma-ag))))
            qerror=max(float(np.max(np.abs(z[i]-convolution(m,e,t)))) for i,(t,side) in enumerate(grid) if t in (35,70,119,120,240,420))
            peak=int(np.argmax(gamma));snapshots=[]
            for label,i in [('Before load',grid.index((20.,'left'))),('Loaded peak',peak),
                            ('After release',grid.index((120.,'right'))),('After recovery',len(grid)-1)]:
                snapshots.append({'label':label,'seconds':times[i],'side':grid[i][1],
                    'strain':float(gamma[i]),'actual_arms':outline(gamma[i]),
                    'display_arms':outline(gamma[i],cfg['display_magnification'])})
            rows.append({'case':name,'e':e,'material_row_stress_Pa':m['stress_Pa'],
                'time':times.tolist(),'side':[side for _,side in grid],'load_Pa':s.tolist(),
                'elastic_strain':(s/m['G_M_Pa']).tolist(),'delayed_strain':z[:,0].tolist(),
                'retained_strain':z[:,1].tolist(),'total_strain':gamma.tolist(),
                'maximum_sampled_strain':float(gamma[peak]),'sampled_peak_seconds':float(times[peak]),
                'final_total_strain':float(gamma[-1]),'final_retained_strain':float(z[-1,1]),
                'max_solver_strain_error':solver_error,'max_convolution_strain_error':qerror,
                'geometry_checks':geometry_checks(gamma),'energy':energy_budget(m,e,z,sol),
                'snapshots':snapshots})
    out={'model':'Current clay Hug with orbital loading','main_hug_trajectories':len(rows),
         'independent_Radau_controls':len(rows),'additional_sims_runs':0,
         'closed_outline':outline(0),'runs':rows}
    out['accuracy_gates_passed']=gates_pass(out)
    return out


def gates_pass(d):
    g=protocol()['gates']
    return len(d['runs'])==28 and all(
        r['max_solver_strain_error']<g['max_solver_strain_error'] and
        r['max_convolution_strain_error']<g['max_convolution_strain_error'] and
        r['energy']['energy_budget_error_J_m3']<g['max_energy_budget_error_J_m3'] and
        r['energy']['dissipation_J_m3']>=0 and
        r['geometry_checks']['max_join_gap']<g['max_join_gap'] and
        r['geometry_checks']['max_relative_area_error']<g['max_relative_area_error'] for r in d['runs'])


def reproduction_check(a,b):
    a,b=copy.deepcopy(a),copy.deepcopy(b)
    for d in (a,b):
        if not d['accuracy_gates_passed'] or not gates_pass(d):return False
        for r in d['runs']:
            for k in ('max_solver_strain_error','max_convolution_strain_error'):r.pop(k)
            r['energy'].pop('energy_budget_error_J_m3')
            r['geometry_checks'].pop('max_relative_area_error')
    return compare_saved(a,b)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    d=run();dest=ROOT/'hug_orbit_results.json'
    if args.check:
        if not reproduction_check(d,json.loads(dest.read_text())):raise SystemExit('Direct Hug orbit reproduction failed')
    else:dest.write_text(json.dumps(d,separators=(',',':'))+'\n',encoding='utf-8')
    print(json.dumps({k:d[k] for k in ('main_hug_trajectories','independent_Radau_controls','additional_sims_runs','accuracy_gates_passed')}))
    if not d['accuracy_gates_passed']:raise SystemExit('Direct Hug accuracy gate failed')
