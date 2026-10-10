"""Reversibility, linear stability, and independent channel formula checks."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from models import integrate

ROOT = Path(__file__).resolve().parent


def references():
    return json.loads((ROOT/'bridge_references.json').read_text(encoding='utf-8'))


def reversible(t, state):
    x, y = state
    return (-2*math.cos(x)-math.cos(y), -math.cos(x)-2*math.cos(y))


def reversible_jacobian(state):
    x, y = state
    return np.array([[2*math.sin(x), math.sin(y)],
                     [math.sin(x), 2*math.sin(y)]])


def potential(state):
    return sum(math.sin(z) for z in state)


def potential_rate(state):
    a, b = [math.cos(z) for z in state]
    return -2*(a*a+a*b+b*b)


def diagonal_exact(t, initial):
    if not -math.pi/2 < initial < math.pi/2:
        raise ValueError('This branch of the exact formula requires -pi/2 < initial < pi/2.')
    return 2*math.atan(math.tan(math.pi/4+initial/2)*math.exp(-3*t))-math.pi/2


def matrix2(matrix):
    a = np.asarray(matrix, dtype=float)
    if a.shape != (2,2) or not np.isfinite(a).all():
        raise ValueError('A finite 2 by 2 matrix is required.')
    return a


def classify(matrix):
    a = matrix2(matrix)
    trace = float(np.trace(a))
    det = float(a[0,0]*a[1,1]-a[0,1]*a[1,0])
    disc = trace*trace-4*det
    scale = float(np.max(np.abs(a)))
    tol = 64*np.finfo(float).eps*scale
    tol2 = 256*np.finfo(float).eps*scale*scale
    if abs(det) <= tol2:
        kind = 'zero eigenvalue; inspect neutral direction'
    elif det < 0:
        kind = 'saddle'
    elif disc < -tol2:
        kind = 'linear center' if abs(trace) <= tol else ('stable spiral' if trace < 0 else 'unstable spiral')
    else:
        kind = ('stable node' if trace < 0 else 'unstable node')
    return {'trace':trace, 'determinant':det, 'discriminant':disc, 'classification':kind}


def linear_flow(matrix, state, time):
    """Real 2x2 exponential via Cayley-Hamilton, including a Jordan block."""
    a = matrix2(matrix)
    half_trace = float(np.trace(a))/2
    b = a-half_trace*np.eye(2)
    delta = float(b[0,0]**2+b[0,1]*b[1,0])
    q = delta*time*time
    # Series avoids cancellation at repeated eigenvalues and at small times.
    if abs(q) < 1e-8:
        c = 1+q/2+q*q/24+q**3/720
        s = time*(1+q/6+q*q/120+q**3/5040)
    elif delta > 0:
        root = math.sqrt(delta)
        c, s = math.cosh(root*time), math.sinh(root*time)/root
    else:
        root = math.sqrt(-delta)
        c, s = math.cos(root*time), math.sin(root*time)/root
    return math.exp(half_trace*time)*((c*np.eye(2)+s*b)@np.asarray(state,dtype=float))


def channel_steady(mu, gradient=10., gap=.001):
    return gradient*gap*gap/(12*mu)


def channel_tau(rho, mu, gap=.001):
    return rho*gap*gap/(math.pi**2*mu)


def channel_mean(time, rho, mu, gradient=10., gap=.001):
    if time < 0:
        raise ValueError('Startup time must be nonnegative.')
    if time == 0:
        return 0.
    modes = np.arange(1,2000,2,dtype=float)
    remainder = np.sum(np.exp(-modes*modes*time/channel_tau(rho,mu,gap))/modes**4)
    return channel_steady(mu,gradient,gap)*(1-96/math.pi**4*remainder)


def channel_profile(y, time, rho, mu, gradient=10., gap=.001):
    y = np.asarray(y,dtype=float)
    if time <= 0:
        return np.zeros_like(y)
    modes = np.arange(1,2000,2,dtype=float)
    amplitudes = np.exp(-modes*modes*time/channel_tau(rho,mu,gap))/modes**3
    transient = 4*gradient*gap*gap/(mu*math.pi**3)*(amplitudes@np.sin(np.pi*modes[:,None]*y/gap))
    return gradient*y*(gap-y)/(2*mu)-transient


def discrete_channel(rho, mu, intervals, end=.1, dt=.00025, gradient=10., gap=.001):
    """CN evolution of the discrete sine modes; independent of source's band solver."""
    count = round(end/dt)
    if intervals < 2 or dt <= 0 or end < 0 or not math.isclose(count*dt,end,abs_tol=1e-12):
        raise ValueError('Use at least 2 intervals and a nonnegative whole number of positive steps.')
    k = np.arange(1,intervals)
    y = np.arange(1,intervals)*gap/intervals
    basis = np.sin(np.pi*np.outer(np.arange(1,intervals),k)/intervals)
    eigen = -4*(mu/rho)/(gap/intervals)**2*np.sin(k*np.pi/(2*intervals))**2
    forcing = 2/intervals*(basis.T@np.full(intervals-1,gradient/rho))
    gain = (1+dt*eigen/2)/(1-dt*eigen/2)
    amplitudes = -forcing/eigen*(1-gain**count)
    return np.r_[0.,y,gap], np.r_[0.,basis@amplitudes,0.]


def results():
    ref = references()
    fixed = []
    for sx,sy in [(-1,-1),(1,1),(-1,1),(1,-1)]:
        point = [sx*math.pi/2,sy*math.pi/2]
        fixed.append({'point':point,**classify(reversible_jacobian(point)),
                      'eigenvalues':sorted(np.linalg.eigvals(reversible_jacobian(point)).tolist())})
    starts = [[.2,.4],[-1.2,-.8],[.6,-.5]]
    symmetry, refinements = [], []
    for initial in starts:
        coarse = np.array(integrate(reversible,initial,1.,.01))
        fine = np.array(integrate(reversible,initial,1.,.005))
        end = coarse[-1,1:]
        reflected = np.array(integrate(reversible,-end,1.,.01))[:,1:]
        symmetry.append(float(np.max(np.abs(reflected+coarse[::-1,1:]))))
        refinements.append(float(np.max(np.abs(coarse[:,1:]-fine[::2,1:]))))
    diagonal = []
    for h in [.04,.02,.01,.005]:
        path = integrate(reversible,[.3,.3],2.,h)
        diagonal.append({'step':h,'max_error':max(abs(x-diagonal_exact(t,.3)) for t,x,y in path)})
    sink = np.array([-math.pi/2]*2)
    initials = [sink+[.2,0],sink+[0,.2],sink+[-.15,.1]]
    attraction = []
    for initial in initials:
        path = np.array(integrate(reversible,initial,8.,.01))
        values = [potential(z) for z in path[:,1:]]
        attraction.append({'initial_distance':float(np.linalg.norm(initial-sink)),
                           'final_distance':float(np.linalg.norm(path[-1,1:]-sink)),
                           'largest_potential_increment':max(np.diff(values).tolist())})
    linear = []
    for case in ref['linear_reference']:
        matrix = np.array(case['matrix'])
        kind = classify(matrix)
        path = np.array(integrate(lambda t,z:matrix@z,[.2,-.1],2.,.01))
        error = max(float(np.linalg.norm(z-linear_flow(matrix,[.2,-.1],t))) for t,*z in path)
        linear.append({'name':case['name'],'matrix':case['matrix'],**kind,
                       'source_classification':case['classification'],'rk4_max_error':error})
    nonnormal = np.array([[-1.,10.],[0.,-2.]])
    times = np.linspace(0,10,1001)
    norms = [float(np.linalg.norm(linear_flow(nonnormal,[0,1],t))) for t in times]
    checks = []
    for row in ref['water_channels']:
        rho,mu,gap,G = [row[k] for k in ['rho','mu','H_m','G_Pam']]
        steady = channel_steady(mu,G,gap)
        tau = channel_tau(rho,mu,gap)
        mean = channel_mean(1.,rho,mu,G,gap)
        checks.append({'T_K':row['T_K'],'material':row['material'],'G_Pam':G,
                       'steady_relative_error':abs(steady/row['steady_mean_ms']-1),
                       'tau_relative_error':abs(tau/row['tau_s']-1),
                       'startup_mean_relative_difference':abs(mean/row['mean_velocity_ms']-1),
                       'perturbation_absolute_error':abs(math.exp(-1/tau)-row['exact_perturbation_amplitude_ratio'])})
    ratios = []
    for temperature,p in ref['water_properties'].items():
        h,d = p['H2O'],p['D2O']
        ratios.append({'temperature_C':float(temperature)-273.15,
                       'steady_D_over_H':h['mu']/d['mu'],
                       'tau_D_over_H':(d['rho']/d['mu'])/(h['rho']/h['mu']),
                       'initial_acceleration_D_over_H':h['rho']/d['rho']})
    grids = []
    for name,p in ref['water_properties']['298.15'].items():
        for n in [32,64,128]:
            y,u = discrete_channel(p['rho'],p['mu'],n)
            exact = channel_profile(y,.1,p['rho'],p['mu'])
            grids.append({'material':name,'intervals':n,'dt':.00025,
                          'relative_L2_error':float(np.linalg.norm(u-exact)/np.linalg.norm(exact))})
    return {'reversible':{'equation':'xprime=-2*cos(x)-cos(y); yprime=-cos(x)-2*cos(y)',
                         'domain':'Four equilibria per 2pi-periodic cell; infinitely many on R^2.',
                         'fixed_points':fixed,'path_reversal_max_errors':symmetry,
                         'step_halving_max_errors':refinements,'diagonal_accuracy':diagonal,
                         'attraction':attraction},
            'linear':linear,
            'transient_growth':{'matrix':nonnormal.tolist(),'initial':[0,1],
                                'largest_sampled_norm':max(norms),'sampled_peak_time':float(times[np.argmax(norms)]),
                                'norm_at_10':norms[-1],**classify(nonnormal)},
            'water':{'comparison_kind':'Independent analytical and discrete-mode checks of saved continuum data; no new molecular or 3D vortex runs.',
                     'source_rows_checked':len(checks),'checks':checks,'material_ratios':ratios,'grid_convergence':grids}}


def compare_saved(a,b):
    """Tight numerical reproducibility while allowing platform roundoff."""
    if isinstance(a,dict):
        return isinstance(b,dict) and a.keys()==b.keys() and all(compare_saved(a[k],b[k]) for k in a)
    if isinstance(a,list):
        return isinstance(b,list) and len(a)==len(b) and all(compare_saved(x,y) for x,y in zip(a,b))
    if isinstance(a,float):
        return isinstance(b,(int,float)) and math.isclose(a,b,rel_tol=1e-9,abs_tol=2e-12)
    return a==b


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    out=results();path=ROOT/'bridge_results.json'
    if args.check:
        if not compare_saved(out,json.loads(path.read_text(encoding='utf-8'))):
            raise SystemExit('FAIL: bridge results differ beyond roundoff tolerance.')
        print('PASS: reversibility, 7 linear cases, and 36 channel comparisons reproduced.')
    else:
        path.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
        print('Saved reversibility, linear stability, and independent channel checks.')
