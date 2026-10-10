"""JPL mean-element orbit controls and a declared orbit-driven clay SIMS test."""
import argparse
import copy
import json
from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy.integrate import quad, solve_ivp
from clay_sims import ClayNetwork, source, initial, sample_grid
from sims_response import graph_cases, operators, measurements
from bridge_checks import compare_saved

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def protocol():
    return json.loads((ROOT/'orbit_protocol.json').read_text())


def kepler(mean_anomaly, e):
    """Bracketed Newton solution for elliptic Kepler's equation, modulo 2*pi."""
    m = np.asarray(mean_anomaly, dtype=float)
    if not np.isfinite(e) or not 0 <= e < 1 or not np.all(np.isfinite(m)):
        raise ValueError('Finite anomaly and 0 <= eccentricity < 1 required')
    m = (m + np.pi) % (2*np.pi) - np.pi
    lo = np.full_like(m, -np.pi); hi = np.full_like(m, np.pi)
    x = m.copy()
    for _ in range(80):
        f = x-e*np.sin(x)-m
        if np.max(np.abs(f), initial=0) < 2e-14:
            return x
        lo = np.where(f < 0, x, lo); hi = np.where(f >= 0, x, hi)
        new = x-f/(1-e*np.cos(x))
        x = np.where((new > lo) & (new < hi), new, (lo+hi)/2)
    raise RuntimeError('Kepler iteration failed')


def orbit(moon, times_days, eccentricity=None):
    """Position km, velocity km/day in the moon's own periapsis-aligned plane."""
    a = float(moon['a_km']); p = float(moon['period_days'])
    if not np.isfinite(a+p) or min(a,p) <= 0:
        raise ValueError('Positive finite semimajor axis and period required')
    e = moon['e'] if eccentricity is None else eccentricity
    n = 2*np.pi/p; E = kepler(n*np.asarray(times_days), e)
    c = np.cos(E); s = np.sin(E); b = np.sqrt(1-e*e)
    xy = a*np.stack((c-e, b*s), axis=-1)
    v = (a*n/(1-e*c))[...,None]*np.stack((-s,b*c), axis=-1)
    return xy, v


def orbit_control(moon, e):
    """Independent Cartesian gravitational integration in a=1, P=1 units."""
    q = np.linspace(0,1,361); mu = (2*np.pi)**2
    start = [1-e,0,0,2*np.pi*np.sqrt((1+e)/(1-e))]
    def rhs(t,y):
        r = np.linalg.norm(y[:2])
        return np.r_[y[2:], -mu*y[:2]/r**3]
    sol = solve_ivp(rhs,(0,1),start,t_eval=q,method='DOP853',rtol=2e-12,atol=2e-14,max_step=.005)
    if not sol.success: raise RuntimeError(sol.message)
    xy,v = orbit(moon,q*moon['period_days'],e)
    expected = np.c_[xy/moon['a_km'],v*moon['period_days']/moon['a_km']]
    radius = np.linalg.norm(xy,axis=-1)
    energy = np.sum(expected[:,2:]**2,axis=-1)/2-mu/(radius/moon['a_km'])
    h = expected[:,0]*expected[:,3]-expected[:,1]*expected[:,2]
    return {'moon':moon['name'],'e':e,'periapsis_km':float(radius[0]),
            'apoapsis_km':float(radius[180]),'period_days':moon['period_days'],
            'max_position_error_over_a':float(np.max(np.abs(sol.y[:2].T-expected[:,:2]))),
            'max_velocity_error_over_a_per_period':float(np.max(np.abs(sol.y[2:].T-expected[:,2:]))),
            'relative_energy_drift':float(np.ptp(energy)/abs(energy[0])),
            'relative_angular_momentum_drift':float(np.ptp(h)/abs(h[0]))}


def load_factor(phase, e):
    E = kepler(2*np.pi*np.asarray(phase), e)
    return np.sqrt(1-e*e)/(1-e*np.cos(E))**2


def applied_load(t, e, side='right'):
    if t < source.START or t > source.RELEASE or (t == source.START and side == 'left') or (t == source.RELEASE and side == 'right'):
        return 0.
    return protocol()['material_row_stress_Pa']*float(load_factor((t-source.START)/source.HOLD,e))


@lru_cache(maxsize=1)
def material():
    s = protocol()['material_row_stress_Pa']
    return next(m for m in source.materials() if m['stress_Pa'] == s)


@lru_cache(maxsize=16)
def uniform_path(e):
    """Population mean Burgers response to an equal-mean orbital waveform."""
    m = material(); grid = sample_grid(); times = np.array([t for t,_ in grid])
    sol = solve_ivp(lambda t,z: [(applied_load(t,e,'left')-m['G_K_Pa']*z[0])/m['eta_K_Pa_s'],
                                 applied_load(t,e,'left')/m['eta_M_Pa_s']],
                    (source.START,source.RELEASE),[0.,0.],method='DOP853',
                    rtol=2e-12,atol=2e-15,max_step=.5,dense_output=True)
    if not sol.success: raise RuntimeError(sol.message)
    z = np.zeros((len(grid),2))
    mask = (times >= source.START) & (times <= source.RELEASE)
    z[mask] = sol.sol(times[mask]).T
    mask = times > source.RELEASE
    z[mask,0] = sol.y[0,-1]*np.exp(-(times[mask]-source.RELEASE)*m['G_K_Pa']/m['eta_K_Pa_s'])
    z[mask,1] = sol.y[1,-1]
    loads = np.array([applied_load(t,e,side) for t,side in grid])
    return z,loads


def uniform_quadrature(t,e):
    """Independent convolution integral for u,w (no ODE solver)."""
    m=material(); end=min(t,source.RELEASE)
    if end <= source.START: return np.zeros(2)
    rate=m['G_K_Pa']/m['eta_K_Pa_s']
    u=quad(lambda s:applied_load(s,e)*np.exp(-rate*(t-s))/m['eta_K_Pa_s'],source.START,end,epsabs=1e-14,epsrel=2e-12)[0]
    w=quad(lambda s:applied_load(s,e)/m['eta_M_Pa_s'],source.START,end,epsabs=1e-14,epsrel=2e-12)[0]
    return np.array([u,w])


def path(net, starts, e):
    times=np.array([t for t,_ in sample_grid()]); mean,loads=uniform_path(e)
    z=net.evolve(starts,np.zeros(starts.shape[-2]),times)
    z += mean.reshape((len(times),)+(1,)*(z.ndim-2)+(2,))
    g=np.array([net.gamma(zz,load) for zz,load in zip(z,loads)])
    return z,g,loads


def adaptive(net,start,e,method):
    """Full-coordinate check; no modal evolution or population-mean decomposition."""
    grid=sample_grid(); times=np.array([t for t,_ in grid]); n=len(start)
    z=np.zeros((len(grid),n,2)); y=start.ravel()
    for a,b in [(0,source.START),(source.START,source.RELEASE),(source.RELEASE,source.END)]:
        loading=(a==source.START)
        sol=solve_ivp(lambda t,y:net.rhs(y.reshape(n,2),applied_load(t,e,'left') if loading else 0).ravel(),
                      (a,b),y,method=method,rtol=2e-11,atol=2e-14,max_step=.5,dense_output=True)
        if not sol.success: raise RuntimeError(sol.message)
        mask=(times>=a)&(times<=b); z[mask]=sol.sol(times[mask]).T.reshape(-1,n,2);y=sol.y[:,-1]
    loads=[applied_load(t,e,side) for t,side in grid]
    return z,np.array([net.gamma(zz,s) for zz,s in zip(z,loads)])


def run():
    cfg=protocol(); seeds=cfg['seeds']; starts=np.array([initial(s) for s in seeds]); m=material()
    grid=sample_grid(); times=np.array([t for t,_ in grid]); star=m['stress_Pa']*source.HOLD/m['eta_M_Pa_s']
    cases=[('Circular control',0.)]+[(x['name'],x['e']) for x in cfg['moons']]
    runs=[]; traces=[]; aggregates=[]; controls=[]; orbit_checks=[]; quadrature_checks=[]
    for moon in cfg['moons']:
        for e in (0.,moon['e']): orbit_checks.append(orbit_control(moon,e))
    for name,e in cases:
        mean,loads=uniform_path(e)
        error=max(float(np.max(np.abs(mean[i]-uniform_quadrature(t,e)))) for i,(t,side) in enumerate(grid) if t in (20,35,70,119,120,240,420))
        quadrature_checks.append({'case':name,'max_internal_strain_error':error,
            'load_impulse_Pa_s':float(quad(lambda t:applied_load(t,e),20,120,epsabs=1e-10)[0]),
            'max_load_Pa':float(loads.max()),'final_mean_strain':float(mean[-1].sum())})
    for graph_name,graph in graph_cases():
        _,lap=operators(graph);net=ClayNetwork(m,lap,cfg['coupling_ratio_K_over_G_M']); baseline_spread=None
        for name,e in cases:
            z,g,loads=path(net,starts,e)
            mean,_=uniform_path(e); expected=mean.sum(axis=-1)+loads/net.gm
            spread=g.std(axis=-1)
            if baseline_spread is None: baseline_spread=spread.copy()
            mean_error=float(np.max(np.abs(g.mean(axis=-1)-expected[:,None])))
            spread_error=float(np.max(np.abs(spread-baseline_spread)))
            controls.append({'case':name,'graph':graph_name,'mean_response_error':mean_error,'paired_spread_error':spread_error})
            for i,seed in enumerate(seeds):
                runs.append({'case':name,'e':e,'graph':graph_name,'seed':seed,
                    'final_strain':g[-1,i].tolist(),'initial_retained_strain':starts[i,:,1].tolist(),
                    'final_mean_strain':float(g[-1,i].mean()),'final_absolute_spread':float(spread[-1,i]),
                    **measurements(times,g[:,i]/star)})
            rows=runs[-len(seeds):]
            aggregates.append({'case':name,'e':e,'graph':graph_name,'runs':len(rows),
                'final_mean_strain':float(np.mean([r['final_mean_strain'] for r in rows])),
                'mean_final_absolute_spread':float(np.mean([r['final_absolute_spread'] for r in rows])),
                'final_response_sign_unanimous':sum(r['final_choice_unanimity'] for r in rows)})
            traces.append({'case':name,'graph':graph_name,'seed':seeds[0],'time':times.tolist(),
                           'side':[s for _,s in grid],'load_Pa':loads.tolist(),
                           'mean_total':g[:,0].mean(axis=-1).tolist(),'absolute_spread':spread[:,0].tolist()})
            if graph_name=='Menger L1' and e>0:
                for method in ('DOP853','Radau'):
                    az,ag=adaptive(net,starts[0],e,method)
                    controls.append({'case':name,'method':method,'max_strain_error':float(max(np.max(np.abs(az-z[:,0])),np.max(np.abs(ag-g[:,0]))))})
    out={'main_runs':len(runs),'distinct_conditions':7,'shared_circular_control':True,
         'orbit_control_paths':len(orbit_checks),'independent_full_network_solver_controls':12,
         'runs':runs,'aggregates':aggregates,'representative_traces':traces,
         'orbit_controls':orbit_checks,'quadrature_controls':quadrature_checks,'controls':controls}
    out['accuracy_gates_passed']=gates_pass(out)
    return out


def gates_pass(d):
    g=protocol()['gates']
    return (all(x['max_position_error_over_a']<g['max_orbit_position_error_over_a'] for x in d['orbit_controls'])
        and all(x['max_internal_strain_error']<g['max_clay_strain_error'] for x in d['quadrature_controls'])
        and all(x.get('max_strain_error',0)<g['max_clay_strain_error'] and
                x.get('mean_response_error',0)<g['max_mean_response_error'] and
                x.get('paired_spread_error',0)<g['max_paired_spread_error'] for x in d['controls']))


def reproduction_check(a,b):
    a,b=copy.deepcopy(a),copy.deepcopy(b)
    for d in (a,b):
        if not d['accuracy_gates_passed'] or not gates_pass(d):return False
        for key in ('controls','orbit_controls','quadrature_controls'):d.pop(key)
    return compare_saved(a,b)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    d=run(); dest=ROOT/'orbit_results.json'
    if args.check:
        if not reproduction_check(d,json.loads(dest.read_text())):raise SystemExit('Orbit reproduction failed')
    else:dest.write_text(json.dumps(d,separators=(',',':'))+'\n',encoding='utf-8')
    print(json.dumps({k:d[k] for k in ('main_runs','orbit_control_paths','independent_full_network_solver_controls','accuracy_gates_passed')}))
    if not d['accuracy_gates_passed']:raise SystemExit('Orbit accuracy gates failed')
