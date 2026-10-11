"""Active Hug: autonomous-cycle checks before signed orbital forcing.

Scaled time tau=t/t0; gamma=gamma0*x, u=gamma0*U, w=gamma0*W.
Inertial stress coefficient I=G_M*t0**2. Parallel stiffness k=kappa*G_M.
Stored energy is measured in G_M*gamma0**2 J/m^3. New mechanical
parameters are specified computational choices, not measured clay fits.
"""
import argparse
import json
import math
from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy.integrate import quad, solve_ivp
from scipy.optimize import brentq, root
from clay_sims import source
from orbits import kepler, protocol as orbit_protocol

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def protocol():
    return json.loads((ROOT/'active_hug_protocol.json').read_text())


class ActiveHug:
    def __init__(self, material, gain=None):
        self.m = material
        p = protocol()
        self.gain = p['active_gain'] if gain is None else float(gain)
        self.kappa = p['parallel_stiffness_over_G_M']
        self.r = material['G_K_Pa']/material['G_M_Pa']
        self.a = p['time_scale_seconds']*material['G_M_Pa']/material['eta_K_Pa_s']
        self.b = p['time_scale_seconds']*material['G_M_Pa']/material['eta_M_Pa_s']
        self.energy_scale = material['G_M_Pa']*p['strain_scale']**2

    def rhs(self, t, y, force=0.):
        x, v, u, w = y[:4]
        s = x-u-w
        du = self.a*(s-self.r*u); dw = self.b*s
        active = self.gain*(1-x*x)*v
        dy = [v, -self.kappa*x-s+active+force, du, dw]
        if len(y) == 7:
            dy += [active*v, force*v, du*du/self.a+dw*dw/self.b]
        return np.array(dy)

    def jacobian(self, y):
        x,v,_,_ = y[:4]
        return np.array([[0,1,0,0],
            [-self.kappa-1-2*self.gain*x*v,self.gain*(1-x*x),1,1],
            [self.a,0,-self.a*(1+self.r),-self.a],
            [self.b,0,-self.b,-self.b]])

    def energy(self, y):
        y = np.asarray(y); x,v,u,w = np.moveaxis(y[..., :4],-1,0)
        return .5*(v*v+self.kappa*x*x+(x-u-w)**2+self.r*u*u)


def integrate(model, start, end, forcing=None, method='DOP853', max_step=None):
    p = protocol()['solver']; start = np.asarray(start,dtype=float)
    if start.size == 4: start = np.r_[start,0.,0.,0.]
    def event(t,y): return y[0]
    event.direction = 1
    sol = solve_ivp(lambda t,y:model.rhs(t,y,0. if forcing is None else forcing(t)),
        (0,end),start,method=method,rtol=p['rtol'],atol=p['atol'],
        max_step=p['max_step'] if max_step is None else max_step,
        dense_output=True,events=event)
    if not sol.success: raise RuntimeError(sol.message)
    return sol


def energy_error(model, sol):
    t = np.linspace(0,sol.t[-1],801); z = sol.sol(t).T
    residual = model.energy(z)-model.energy(z[0])-(z[:,4]-z[0,4])-(z[:,5]-z[0,5])+(z[:,6]-z[0,6])
    return float(np.max(np.abs(residual)))


def cycle_metrics(sol):
    t = sol.t_events[0]; z = sol.y_events[0]
    if len(t) < 4: raise RuntimeError('Too few positive crossings to measure a cycle')
    return dict(period_scaled=float(t[-1]-t[-2]),
        period_relative_variation=float(np.ptp(np.diff(t[-6:]))/np.mean(np.diff(t[-6:]))),
        full_state_return_error=float(np.max(np.abs(z[-1,:4]-z[-2,:4]))),
        section_state=z[-1,:4].tolist())


def shoot_cycle(model, seed, period):
    """Solve all four periodic-state conditions with x=0 as phase condition."""
    def residual(z):
        y = np.r_[0.,z[:3]]
        if z[3] <= 0: return np.ones(4)*1e3
        sol = solve_ivp(lambda t,y:model.rhs(t,y),(0,z[3]),y,
            method='DOP853',rtol=2e-12,atol=2e-14,max_step=.06)
        if not sol.success: raise RuntimeError(sol.message)
        return sol.y[:,-1]-y
    fit = root(residual,np.r_[np.asarray(seed)[1:4],period],tol=1e-10)
    error = float(np.max(np.abs(residual(fit.x))))
    if error > protocol()['gates']['cycle_full_state_error'] or fit.x[0] <= 0:
        raise RuntimeError(f'Periodic shooting failed: {fit.message}, {error}')
    y = np.r_[0.,fit.x[:3]]; period=float(fit.x[3])
    def variational(t,z):
        return np.r_[model.rhs(t,z[:4]),(model.jacobian(z[:4])@z[4:].reshape(4,4)).ravel()]
    sol=solve_ivp(variational,(0,period),np.r_[y,np.eye(4).ravel()],
        method='DOP853',rtol=2e-12,atol=2e-14,max_step=.03,dense_output=True)
    if not sol.success: raise RuntimeError(sol.message)
    matrix=sol.y[4:,-1].reshape(4,4); multipliers=np.linalg.eigvals(matrix)
    neutral=int(np.argmin(np.abs(multipliers-1))); transverse=np.delete(multipliers,neutral)
    def power(t,which):
        z=sol.sol(t)[:4]; dz=model.rhs(t,z)
        return model.gain*(1-z[0]**2)*z[1]**2 if which=='active' else dz[2]**2/model.a+dz[3]**2/model.b
    work=quad(lambda t:power(t,'active'),0,period,epsabs=2e-11,epsrel=2e-11)[0]
    loss=quad(lambda t:power(t,'loss'),0,period,epsabs=2e-11,epsrel=2e-11)[0]
    return dict(period_scaled=period,period_seconds=period*protocol()['time_scale_seconds'],
        section_state=y.tolist(),shooting_error=error,
        monodromy=matrix.tolist(),multipliers=[[float(z.real),float(z.imag)] for z in multipliers],
        neutral_multiplier_error=float(abs(multipliers[neutral]-1)),
        largest_transverse_modulus=float(np.max(np.abs(transverse))),
        active_work_per_cycle_scaled=float(work),dissipation_per_cycle_scaled=float(loss),
        independent_power_balance_error=float(abs(work-loss)),
        cycle_time_seconds=(np.linspace(0,period,241)*protocol()['time_scale_seconds']).tolist(),
        cycle_state=sol.sol(np.linspace(0,period,241))[:4].T.tolist())


def linear_threshold(material):
    def leading(gain): return float(np.max(np.linalg.eigvals(ActiveHug(material,gain).jacobian(np.zeros(4))).real))
    gain=brentq(leading,0,1,xtol=2e-13)
    ev=np.linalg.eigvals(ActiveHug(material,gain).jacobian(np.zeros(4)))
    return dict(gain=gain,eigenvalues=[[float(z.real),float(z.imag)] for z in ev],
        below_leading_real=leading(gain*.9),above_leading_real=leading(gain*1.1))


def raw_tide(phase,e):
    # Scalar integration calls avoid NumPy's per-iteration array overhead.
    # The vector route remains the independent pinned Kepler implementation.
    if np.ndim(phase)==0 and 0 <= e < .8:
        mean=(2*math.pi*float(phase)+math.pi)%(2*math.pi)-math.pi
        angle=mean
        for _ in range(30):
            residual=angle-e*math.sin(angle)-mean
            if abs(residual)<1e-14:break
            angle-=residual/(1-e*math.cos(angle))
        else:raise RuntimeError('Scalar Kepler solve failed')
        radius=1-e*math.cos(angle)
        return 2*(math.cos(angle)-e)*math.sqrt(1-e*e)*math.sin(angle)/radius**5
    E=kepler(2*np.pi*np.asarray(phase),e); radius=1-e*np.cos(E)
    cx=(np.cos(E)-e)/radius; sy=np.sqrt(1-e*e)*np.sin(E)/radius
    return 2*cx*sy/radius**3


@lru_cache(maxsize=16)
def tide_rms(e):
    return float(np.sqrt(quad(lambda p:float(raw_tide(p,e))**2,0,1,epsabs=1e-11,epsrel=1e-11,limit=150)[0]))


def orbital_force(t,e):
    p=protocol(); period=p['orbit_period_model_seconds']/p['time_scale_seconds']
    return p['orbital_force_rms']*raw_tide(t/period,e)/tide_rms(e)


def trace(sol, tail_only=False):
    end=sol.t[-1]; t=np.linspace(max(0,end-60),end,481) if tail_only else np.unique(np.r_[np.linspace(0,min(100,end),501),np.linspace(max(0,end-60),end,481)])
    return dict(time_seconds=(t*protocol()['time_scale_seconds']).tolist(),state=sol.sol(t).T.tolist())


def forced_metrics(sol, model, e):
    p=protocol(); period=p['orbit_period_model_seconds']/p['time_scale_seconds']
    strobes=np.arange(sol.t[-1]-20*period,sol.t[-1]+period/2,period)
    z=sol.sol(strobes)[:4].T
    distances={str(n):float(np.max(np.abs(z[-10:]-z[-10-n:-n]))) for n in (1,2,3,4)}
    match=next((int(n) for n,d in distances.items() if d < 1e-5),None)
    tailt=np.linspace(sol.t[-1]-10*period,sol.t[-1],2001); tail=sol.sol(tailt).T
    crossings=sol.t_events[0]; crossings=crossings[crossings>sol.t[-1]-20*period]
    return dict(e=e,strobe_time_seconds=(strobes*p['time_scale_seconds']).tolist(),
        strobe_state=z.tolist(),strobe_return_errors=distances,
        detected_repeat_orbits=match,classification='periodic within numerical tolerance' if match else 'no repeat detected within 1-4 orbits',
        positive_crossings_per_orbit=float((len(crossings)-1)*period/(crossings[-1]-crossings[0])) if len(crossings)>1 else None,
        peak_actual_strain=float(np.max(np.abs(tail[:,0]))*p['strain_scale']),
        retained_state_change_last_10_orbits=float((tail[-1,3]-tail[0,3])*p['strain_scale']),
        energy_balance_error_scaled=energy_error(model,sol),
        trace=trace(sol,True))


def validate(data):
    g=protocol()['gates']
    if len(data['autonomous'])!=12 or len(data['forced'])!=28: raise AssertionError('Incomplete paired experiment')
    for row in data['cycles']:
        assert row['shooting_error'] < g['cycle_full_state_error']
        assert row['neutral_multiplier_error'] < 1e-6
        assert row['largest_transverse_modulus'] < g['transverse_multiplier_max']
        assert row['independent_power_balance_error'] < g['independent_cycle_power_error']
        assert row['perturbation_return_error'] < g['perturbation_return_error']
    for row in data['autonomous']:
        assert row['metrics']['full_state_return_error'] < g['initial_state_cycle_error']
        assert row['metrics']['period_relative_variation'] < g['cycle_period_relative_error']
        assert row['section_distance_to_shot_cycle'] < g['initial_state_cycle_error']
        assert row['energy_balance_error_scaled'] < g['energy_balance_error']
    for row in data['passive']:
        assert row['final_norm'] < g['passive_final_norm']
        assert row['energy_balance_error_scaled'] < g['energy_balance_error']
    for row in data['forced']: assert row['energy_balance_error_scaled'] < g['energy_balance_error']
    for row in data['solver_controls']: assert row['max_state_error'] < g['solver_state_error']
    for row in data['autonomous']+data['forced']+data['passive']:
        assert np.all(np.isfinite(row['trace']['state']))
    return True


def run():
    p=protocol(); data=dict(protocol=p,autonomous=[],cycles=[],passive=[],gain_controls=[],forced=[],solver_controls=[],additional_sims_runs=0)
    cases=[('Circular control',0.)]+[(m['name'],m['e']) for m in orbit_protocol()['moons']]
    for material in source.materials():
        row=material['stress_Pa']; model=ActiveHug(material); end=p['horizon_scaled_time']
        print(f'Active Hug: {row:g} Pa coefficient row, autonomous starts',flush=True)
        sols=[]
        for i,start in enumerate(p['initial_states']):
            sol=integrate(model,start,p['autonomous_horizon_scaled_time']);sols.append(sol)
            data['autonomous'].append(dict(coefficient_row_stress_Pa=row,start_index=i,
                metrics=cycle_metrics(sol),energy_balance_error_scaled=energy_error(model,sol),trace=trace(sol)))
        metrics=cycle_metrics(sols[0]);cycle=shoot_cycle(model,metrics['section_state'],metrics['period_scaled'])
        cycle['coefficient_row_stress_Pa']=row;cycle['linear_instability_threshold']=linear_threshold(material)
        pert=integrate(model,np.array(cycle['section_state'])+p['perturbation'],cycle['period_scaled']*p['perturbation_return_cycles'])
        cycle['perturbation_return_error']=float(np.max(np.abs(pert.y_events[0][-1,:4]-cycle['section_state'])))
        cycle['perturbation_initial_distance']=float(np.linalg.norm(p['perturbation']))
        data['cycles'].append(cycle)
        for item in data['autonomous'][-3:]:item['section_distance_to_shot_cycle']=float(np.max(np.abs(np.array(item['metrics']['section_state'])-cycle['section_state'])))
        passive=integrate(ActiveHug(material,0),p['initial_states'][1],end)
        data['passive'].append(dict(coefficient_row_stress_Pa=row,final_norm=float(np.linalg.norm(passive.y[:4,-1])),energy_balance_error_scaled=energy_error(ActiveHug(material,0),passive),trace=trace(passive)))
        for gain in p['gain_controls']:
            ev=np.linalg.eigvals(ActiveHug(material,gain).jacobian(np.zeros(4)))
            data['gain_controls'].append(dict(coefficient_row_stress_Pa=row,gain=gain,leading_real_eigenvalue=float(np.max(ev.real))))
        # Independent Radau evolution from the same late state; autonomous orbit remains active.
        for name,e in [('Autonomous',None)]+cases:
            forcing=None if e is None else lambda t,e=e:orbital_force(t,e)
            sol=sols[0] if e is None else integrate(model,p['initial_states'][0],end,forcing)
            if e is not None:
                print(f'  orbit: {name}',flush=True)
                data['forced'].append(dict(coefficient_row_stress_Pa=row,name=name,**forced_metrics(sol,model,e)))
            horizon=sol.t[-1];origin=horizon-20.; start=sol.sol(origin)[:4]
            shifted=None if e is None else lambda t,e=e:orbital_force(t+origin,e)
            check=integrate(model,start,20.,shifted,method='Radau',max_step=.08)
            tt=np.linspace(0,20,321);err=float(np.max(np.abs(check.sol(tt)[:4]-sol.sol(tt+origin)[:4])))
            data['solver_controls'].append(dict(coefficient_row_stress_Pa=row,name=name,interval_seconds=[origin*p['time_scale_seconds'],horizon*p['time_scale_seconds']],max_state_error=err))
    validate(data);data['accuracy_gates']='passed'
    return data


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    data=run();path=ROOT/'active_hug_results.json'
    if args.check:
        saved=json.loads(path.read_text());validate(saved)
        for a,b in zip(data['cycles'],saved['cycles']):
            np.testing.assert_allclose(a['section_state'],b['section_state'],atol=1e-7,rtol=1e-7)
            assert abs(a['period_seconds']-b['period_seconds'])<1e-5
        for a,b in zip(data['forced'],saved['forced']):
            np.testing.assert_allclose(a['trace']['state'],b['trace']['state'],atol=2e-6,rtol=2e-6)
        print('Saved autonomous and orbital outcomes reproduced; all original gates pass.')
    else:
        path.write_text(json.dumps(data,separators=(',',':'))+'\n',encoding='utf-8')
        print(json.dumps({'autonomous':12,'forced':28,'passive':4,'solver_controls':32,'gates':'passed'}))


if __name__=='__main__': main()
