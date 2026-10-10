"""Run the located Hug equations unchanged locally, with explicit SIMS coupling."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from sims_response import graph_cases, operators, initial_state, measurements, trace
from bridge_checks import compare_saved

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('located_hug_model', ROOT/'hug_source/hug_model.py')
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


def protocol():
    return json.loads((ROOT/'hug_sims_protocol.json').read_text())


def starting(seed, n=20):
    z = np.zeros((n, 5))
    z[:, :2] = initial_state(seed, n)
    return z


def memory_rhs(t, z, p, laplacian, coupling=2.):
    """Vectorized source RHS, preserving its piecewise loading/recovery times."""
    # source.rhs has a scalar `if load > imprint`; vectorization needs np.where.
    q, v, m, _, _ = np.moveaxis(z, -1, 0)
    load = source.pressure(t, p)
    tau = np.where(load > m, .8, 6.)
    feedback = p.memory_coupling*m*q
    return np.stack((v, p.r*q-q**3-p.damping*v+feedback-coupling*(q@laplacian.T),
                     (load-m)/tau, feedback*v, p.damping*v*v), axis=-1)


def path(z, p, laplacian, coupling=2., step=.01, duration=24., sample=.1):
    for length in (duration, sample, p.pulse_duration):
        if not np.isclose(round(length/step)*step, length, atol=1e-12, rtol=0):
            raise ValueError('Resolve the pulse boundary and sampling grid with whole steps.')
    if min(step, duration, sample) <= 0:
        raise ValueError('Positive times required.')
    z = np.array(z, dtype=float, copy=True)
    stride = round(sample/step); saved = [z.copy()]
    f = lambda t, y: memory_rhs(t, y, p, laplacian, coupling)
    for i in range(round(duration/step)):
        z = source.step(f, i*step, z, step)
        if (i+1) % stride == 0:
            saved.append(z.copy())
    values = np.array(saved)
    if not np.isfinite(values).all():
        raise ArithmeticError('Nonfinite Hug trajectory')
    return np.arange(len(saved))*sample, values


def adaptive(z, p, laplacian, times, coupling=2., method='DOP853'):
    shape = z.shape
    sol = solve_ivp(lambda t,y: memory_rhs(t,y.reshape(shape),p,laplacian,coupling).ravel(),
                    (times[0],times[-1]),z.ravel(),t_eval=times,method=method,
                    rtol=1e-10,atol=1e-12,max_step=min(.05,p.pulse_duration/16))
    if not sol.success:
        raise RuntimeError(sol.message)
    return sol.y.T.reshape((len(times),)+shape)


def energy(z, p, laplacian, coupling=2.):
    q, v = z[..., 0], z[..., 1]
    return np.sum(.5*v*v-.5*p.r*q*q+.25*q**4,axis=-1)+.5*coupling*np.sum(q*(q@laplacian.T),axis=-1)


def budget(z, p, laplacian, coupling=2.):
    e = energy(z,p,laplacian,coupling)
    return e-e[0]-np.sum(z[...,3]-z[0,...,3],axis=-1)+np.sum(z[...,4]-z[0,...,4],axis=-1)


def pulse_control():
    p=source.Parameters(pressure=100.,pulse_duration=.001)
    old=[]
    for dt in (.02,.01):
        t,z=source.integrate(p,dt=dt,end=1.)
        old.append({'step':dt,'peak_sampled_memory':float(z[:,2].max())})
    refs=[]
    for method in ('DOP853','Radau'):
        t1=np.linspace(0,.001,101);t2=np.linspace(.001,1.,1001)
        first=solve_ivp(lambda t,y:source.rhs(t,y,p),(0,.001),[.04,0,0,0,0],
                        method=method,t_eval=t1,rtol=1e-11,atol=1e-13,max_step=.001/32)
        second=solve_ivp(lambda t,y:source.rhs(t,y,p),(.001,1.),first.y[:,-1],
                         method=method,t_eval=t2,rtol=1e-11,atol=1e-13,max_step=.01)
        if not first.success or not second.success: raise RuntimeError('Pulse reference failed')
        refs.append(np.concatenate((first.y.T,second.y.T[1:])))
    return {'old_fixed_steps':old,'resolved_peak_memory':float(refs[0][:,2].max()),
            'independent_max_state_difference':float(np.max(np.abs(refs[0]-refs[1])))}


def reproduction_check(actual, saved):
    """Compare main outcomes tightly; reapply fixed accuracy gates to solver errors.

    Error estimates from adaptive solvers vary with floating-point linear algebra.
    They must pass the original protocol, not match their own last few digits.
    """
    a,b=copy.deepcopy(actual),copy.deepcopy(saved);gates=protocol()['controls']
    for d in (a,b):
        if not d['accuracy_gates_passed']:return False
        for row in d['controls']:
            for key in ('max_step_difference','max_rk4_dop853_difference','max_independent_difference'):
                if not 0 <= row.pop(key) < gates['maximum_state_discrepancy']:return False
            if not 0 <= row.pop('max_reflection_error') < gates['maximum_reflection_error']:return False
        if not 0 <= d['short_pulse_control'].pop('independent_max_state_difference') < 2e-8:return False
    return compare_saved(a,b)


def run():
    cfg=protocol();runs=[];traces=[];controls=[];aggregates=[]
    initials=np.array([starting(seed) for seed in cfg['seeds']])
    for name,graph in graph_cases():
        _,l=operators(graph)
        for condition in cfg['conditions']:
            label=condition['name'];p=source.Parameters(**{k:v for k,v in condition.items() if k!='name'})
            t,z=path(initials,p,l,coupling=cfg['coupling'],step=cfg['step'],
                     duration=cfg['duration'],sample=cfg['sample'])
            eerr=np.max(np.abs(budget(z,p,l)),axis=0)
            for i,seed in enumerate(cfg['seeds']):
                row={'graph':name,'condition':label,'seed':seed,**measurements(t,z[:,i,:,:2]),
                     'peak_sampled_abs_lean':float(np.max(np.abs(z[:,i,:,0]))),
                     'peak_sampled_memory':float(z[:,i,:,2].max()),
                     'max_energy_budget_error':float(eerr[i]),
                     'final_q_v':z[-1,i,:,:2].tolist(),
                     'opening_time':source.opening_time(p)}
                runs.append(row)
            traces.append({'graph':name,'condition':label,'seed':cfg['seeds'][0],
                           **trace(t,z[:,0,:,:2]),'memory':z[:,0,0,2].tolist(),
                           'effective_stiffness':(p.r+p.memory_coupling*z[:,0,0,2]).tolist(),
                           'pressure':[source.pressure(x,p) for x in t],
                           'gap':[source.geometry(x,y,p,points=3)['gap'] for x,y in zip(t,z[:,0,0,:])]})
            # First two matched seeds, selected before examining outcomes.
            _,fine=path(initials[:2],p,l,step=.005)
            mirror=initials[:2].copy();mirror[:,:,:2]*=-1
            _,reflected=path(mirror,p,l)
            expected=z[:,:2].copy();expected[...,:2]*=-1
            dop=adaptive(initials[0],p,l,t)
            radau=adaptive(initials[0],p,l,t,method='Radau')
            controls.append({'graph':name,'condition':label,'refinement_runs':2,'reflection_runs':2,
                'adaptive_runs':2,'max_step_difference':float(np.max(np.abs(fine-z[:,:2]))),
                'max_reflection_error':float(np.max(np.abs(expected-reflected))),
                'max_rk4_dop853_difference':float(np.max(np.abs(dop-z[:,0]))),
                'max_independent_difference':float(np.max(np.abs(dop-radau)))})
            rows=runs[-32:]
            aggregates.append({'graph':name,'condition':label,'runs':len(rows),
                'unanimous_final_runs':sum(r['final_choice_unanimity'] for r in rows),
                'mean_final_spread':float(np.mean([r['final_spread'] for r in rows])),
                'mean_peak_abs_lean':float(np.mean([r['peak_sampled_abs_lean'] for r in rows])),
                'mean_final_positive_fraction':float(np.mean([r['final_positive_fraction'] for r in rows])),
                'mean_final_undecided_fraction':float(np.mean([r['final_undecided_fraction'] for r in rows]))})
    gates=cfg['controls']
    passed=(max(r['max_energy_budget_error'] for r in runs)<gates['maximum_energy_budget_residual'] and
            all(max(c['max_step_difference'],c['max_rk4_dop853_difference'],c['max_independent_difference'])<gates['maximum_state_discrepancy'] and
                c['max_reflection_error']<gates['maximum_reflection_error'] for c in controls))
    return {'source_commit':cfg['source_commit'],'main_runs':len(runs),'numerical_and_reflection_controls':72,
            'accuracy_gates_passed':passed,'runs':runs,'aggregates':aggregates,
            'representative_traces':traces,'controls':controls,'short_pulse_control':pulse_control()}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    result=run();destination=ROOT/'hug_sims_results.json'
    if args.check:
        if not reproduction_check(result,json.loads(destination.read_text())):
            raise SystemExit('FAIL: main Hug outcomes differ or original accuracy gates fail.')
    else:
        destination.write_text(json.dumps(result,separators=(',',':'))+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('runs','aggregates','representative_traces','controls')}))
    if not result['accuracy_gates_passed']:raise SystemExit('Accuracy gate failed; outcomes retained.')
