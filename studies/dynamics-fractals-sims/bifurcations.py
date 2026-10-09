"""Second batch: folds, bead mechanics, budworms, laser rates, and pitchforks."""
import cmath
import argparse
import json
import math
from pathlib import Path
from models import integrate


def bisect(function, lo, hi):
    flo, fhi = function(lo), function(hi)
    if flo*fhi > 0:
        raise ValueError('A sign-changing bracket is required')
    for _ in range(80):
        mid = (lo+hi)/2
        fm = function(mid)
        if fm == 0:
            return mid
        if flo*fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return (lo+hi)/2


def distinct(values, tolerance=1e-7):
    result = []
    for value in sorted(values):
        if not result or abs(value-result[-1]) > tolerance:
            result.append(value)
    return result


def polynomial_roots(coefficients):
    """Real roots via derivative intervals, including repeated critical roots."""
    coeff = list(coefficients)
    while len(coeff) > 1 and coeff[0] == 0:
        coeff.pop(0)
    degree = len(coeff)-1
    if degree == 0:
        return []
    if degree == 1:
        return [-coeff[1]/coeff[0]]
    def value(x):
        result = 0
        for c in coeff:
            result = result*x+c
        return result
    critical = polynomial_roots([c*(degree-i) for i,c in enumerate(coeff[:-1])])
    bound = 1+max(abs(c/coeff[0]) for c in coeff[1:])
    points = [-bound]+[x for x in critical if -bound < x < bound]+[bound]
    roots = [x for x in points if abs(value(x)) < 1e-10]
    for left,right in zip(points,points[1:]):
        if value(left)*value(right) < 0:
            roots.append(bisect(value,left,right))
    return distinct(roots)


def stability(derivative):
    return 'stable' if derivative < -1e-8 else 'unstable' if derivative > 1e-8 else 'nonhyperbolic'


def cusp_roots(r, h):
    return [{'x': x, 'stability': stability(r-3*x*x)}
            for x in polynomial_roots([1,0,-r,-h])]


def bead_force(x, load, gap=1, length=1.4):
    # User's equilibrium equation: mg sin(theta)=k*x*(1-L0/sqrt(x²+a²)).
    # load=mg sin(theta)/k, gap=a. Positive damping gives xdot=(k/b)*force.
    return load-x*(1-length/math.sqrt(x*x+gap*gap))


def bead_derivative(x, gap=1, length=1.4):
    return -1+length*gap*gap/(x*x+gap*gap)**1.5


def bead_roots(load, gap=1, length=1.4):
    if gap <= 0 or length <= 0:
        raise ValueError('Positive spring length and gap required')
    critical_squared = (length*gap*gap)**(2/3)-gap*gap
    critical = [-math.sqrt(critical_squared),math.sqrt(critical_squared)] if critical_squared > 0 else [0.0]
    bound = abs(load)+length+gap+1
    points = [-bound]+critical+[bound]
    fn = lambda x: bead_force(x,load,gap,length)
    values = [x for x in points if abs(fn(x)) < 1e-10]
    for left,right in zip(points,points[1:]):
        if fn(left)*fn(right) < 0:
            values.append(bisect(fn,left,right))
    return [{'x': x, 'stability': stability(bead_derivative(x,gap,length))} for x in distinct(values)]


def budworm(x, r=0.5, capacity=10):
    return r*x*(1-x/capacity)-x*x/(1+x*x)


def budworm_derivative(x,r=0.5,capacity=10):
    return r*(1-2*x/capacity)-2*x/(1+x*x)**2


def budworm_roots(r,capacity):
    if r <= 0 or capacity <= 0:
        raise ValueError('Positive growth and capacity required')
    roots = [0]+[x for x in polynomial_roots([1,-capacity,1+capacity/r,-capacity]) if x > 0]
    return [{'x': x,'stability': stability(budworm_derivative(x,r,capacity))} for x in roots]


def budworm_fold(x):
    if x <= 1:
        raise ValueError('Fold parameter x must exceed one')
    return {'x': x, 'capacity': 2*x**3/(x*x-1), 'r': 2*x**3/(1+x*x)**2}


def pitchfork_roots(r,a=1):
    # a=1 is the supplied subcritical example; other a values are an extension.
    roots = [0.0]
    discriminant = a*a+4*r
    if discriminant >= 0:
        for squared in ((a+math.sqrt(discriminant))/2,(a-math.sqrt(discriminant))/2):
            if squared > 1e-14:
                roots.extend((-math.sqrt(squared),math.sqrt(squared)))
    return [{'x': x,'stability': stability(r+3*a*x*x-5*x**4)} for x in distinct(roots)]


def hoop(phi,gamma):
    return math.sin(phi)*(gamma*math.cos(phi)-1)


def full_laser(pump,G=1,loss=1,decay=0.2):
    def rhs(t,state):
        photons, inversion = state
        return (G*photons*inversion-loss*photons,
                -G*photons*inversion-decay*inversion+pump)
    return rhs


def laser_equilibria(pump,G=1,loss=1,decay=0.2):
    off = [0.0,pump/decay]
    threshold = loss*decay/G
    output = {'pump': pump,'threshold': threshold,'off': off,
              'off_eigenvalues': [G*pump/decay-loss,-decay]}
    if pump >= threshold:
        photons = pump/loss-decay/G
        trace = -G*photons-decay
        determinant = loss*G*photons
        eigs = [(trace+sign*cmath.sqrt(trace*trace-4*determinant))/2 for sign in (-1,1)]
        output.update({'on': [photons,loss/G],
                       'on_eigenvalues': [[v.real,v.imag] for v in eigs]})
    return output


def equilibrium_sweep(values, roots_function, starting_side='low'):
    path = []
    previous = None
    for value in values:
        candidates = [row['x'] for row in roots_function(value) if row['stability']=='stable']
        if not candidates:
            raise ArithmeticError('No stable branch available on selected sweep grid')
        if previous is None:
            previous = min(candidates) if starting_side=='low' else max(candidates)
        else:
            previous = min(candidates,key=lambda x: abs(x-previous))
        path.append([value,previous])
    return path


def results():
    load_fold_x = math.sqrt(1.4**(2/3)-1)
    load_fold = abs(load_fold_x*(1-1.4/math.sqrt(1+load_fold_x**2)))
    hvalues = [-0.6+i*0.01 for i in range(121)]
    bvalues = [-0.25+i*0.005 for i in range(101)]
    phase_rows = []
    for initial in (0.1,1,3,9):
        rows = integrate(lambda t,s: (budworm(s[0]),),[initial],100,0.05)
        phase_rows.append({'initial': initial,'final': rows[-1][1],
                           'residual': abs(budworm(rows[-1][1]))})
    laser = []
    for pump in (0.1,0.2,0.8):
        eq = laser_equilibria(pump)
        rows = integrate(full_laser(pump),[0.01,pump/0.2],120,0.02)
        fine = integrate(full_laser(pump),[0.01,pump/0.2],120,0.01)
        eq.update({'final_at_120': list(rows[-1][1:]),
                   'max_step_refinement_difference': max(math.dist(a[1:],b[1:]) for a,b in zip(rows,fine[::2])),
                   'minimum_photons': min(row[1] for row in rows),
                   'minimum_inversion': min(row[2] for row in rows)})
        laser.append(eq)
    return {'cusp': {'equation': 'xdot=h+r*x-x^3','r': 1,
                     'fold_h': [-2/(3*math.sqrt(3)),2/(3*math.sqrt(3))],
                     'equilibria_at_h0': cusp_roots(1,0),
                     'up_sweep': equilibrium_sweep(hvalues,lambda h:cusp_roots(1,h)),
                     'down_sweep': equilibrium_sweep(list(reversed(hvalues)),lambda h:cusp_roots(1,h),'high')},
            'bead': {'equation': 'mg*sin(theta)=k*x*(1-L0/sqrt(x^2+a^2))',
                     'gap_a': 1,'spring_length_L0': 1.4,'mg_over_k': 1,
                     'fold_load_magnitude': load_fold,'fold_angle_degrees': math.degrees(math.asin(load_fold)),
                     'horizontal_equilibria': bead_roots(0),
                     'up_sweep': equilibrium_sweep(bvalues,bead_roots),
                     'down_sweep': equilibrium_sweep(list(reversed(bvalues)),bead_roots,'high')},
            'budworm': {'equation': 'xdot=r*x*(1-x/k)-x^2/(1+x^2)',
                        'r': 0.5,'k': 10,'equilibria': budworm_roots(0.5,10),
                        'basin_trials': phase_rows,'cusp': budworm_fold(math.sqrt(3))},
            'pitchfork': {'equation': 'xdot=r*x+a*x^3-x^5','supplied_case_a': 1,
                          'subcritical_fold_r': -0.25,'r_minus_0_1_roots': pitchfork_roots(-0.1),
                          'extension_a_values': [-1,0,1],
                          'extension_status': 'Chosen parameter-a extension; last image omitted its equation.'},
            'hoop': {'equation': 'phidot=sin(phi)*(gamma*cos(phi)-1)',
                     'gamma': 2,'stable_angles': [-math.acos(0.5),math.acos(0.5)],
                     'small_angle_A': 1,'small_angle_B': 7/6},
            'two_variable_laser': laser}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = Path(__file__).with_name('bifurcation_results.json')
    data = results()
    if args.check:
        if data != json.loads(path.read_text(encoding='utf-8')):
            raise SystemExit('FAIL: second-batch results differ; inspect Python/platform precision.')
        print('PASS: second-batch results reproduced.')
    else:
        path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
        print('Saved all second-batch equilibria, stability checks, sweeps, and trajectories.')
