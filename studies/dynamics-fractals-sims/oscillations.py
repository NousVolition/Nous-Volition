"""Batch 3: limit cycles, exclusion certificates, and nonlinear oscillators.

All times and states are dimensionless. Standard-library-only RK4 calculations.
Analytic arguments and sampled numerical diagnostics are distinguished in results.
"""
import argparse
import json
import math
from pathlib import Path
from models import integrate


def radial_rate(r, kind):
    if kind == 'stable':
        return r * (1-r*r)
    if kind == 'unstable':
        return 0.1*r*(r*r-1)
    if kind == 'half_stable':
        return -r*(1-r*r)**2
    raise ValueError('Unknown radial example')


def radial_field(kind):
    radial_rate(1, kind)
    def rhs(t, state):
        x, y = state
        q = x*x+y*y
        coefficient = {'stable': 1-q, 'unstable': 0.1*(q-1),
                       'half_stable': -(1-q)**2}[kind]
        return coefficient*x-y, x+coefficient*y
    return rhs


def planar_pitchfork(mu):
    """Chosen local normal form; the Figure 8.1.7 crop omits its equations."""
    return lambda t,s: (mu*s[0]-s[0]**3,-s[1])


def hopf_normal_form(mu):
    def rhs(t,s):
        x,y=s; coefficient=mu-x*x-y*y
        return coefficient*x-y,x+coefficient*y
    return rhs


def stable_radius(t, r0):
    return 0.0 if r0 == 0 else 1/math.sqrt(1+(1/r0**2-1)*math.exp(-2*t))


def radial_trajectory(kind, r0, duration=25, step=0.01):
    """Stop the outer unstable example just before its analytic r=2 crossing."""
    if r0 <= 0 or r0 >= 2:
        raise ValueError('Use 0 < r0 < 2')
    stopped = False
    if kind == 'unstable' and r0 > 1:
        hit = math.log((1-1/4)/(1-1/r0**2))/0.2
        if hit < duration:
            duration = math.floor(hit/step)*step
            stopped = True
    return integrate(radial_field(kind), [r0,0], duration, step), stopped


def gradient(t, state):
    x, y = state
    return math.sin(y), x*math.cos(y)


def potential(x, y):
    return -x*math.sin(y)


def dulac_population(t, state):
    x, y = state
    return x*(2-x-y), y*(4*x-x*x-3)


def dulac_polynomial(t, state):
    x, y = state
    return y, -x-y+x*x+y*y


def dulac_weighted(which, x, y):
    if which == 'population':
        if x <= 0 or y <= 0:
            raise ValueError('The certificate requires the open positive quadrant')
        g = 1/(x*y)
        field = dulac_population
    elif which == 'polynomial':
        g = math.exp(-2*x)
        field = dulac_polynomial
    else:
        raise ValueError('Unknown certificate')
    return tuple(g*v for v in field(0, (x,y)))


def selkov(a, b):
    if a <= 0 or b <= 0:
        raise ValueError('Selkov parameters must be positive')
    return lambda t, s: (-s[0]+(a+s[0]**2)*s[1], b-(a+s[0]**2)*s[1])


def selkov_equilibrium(a, b):
    selkov(a,b)
    s = a+b*b
    trace = -1+2*b*b/s-s
    det = s
    return {'x': b, 'y': b/s, 'trace': trace, 'determinant': det,
            'stability': 'repeller' if trace > 1e-12 else
                         'attractor' if trace < -1e-12 else 'nonhyperbolic'}


def selkov_hopf_bounds(a):
    if not 0 < a < 1/8:
        raise ValueError('Two distinct trace-zero boundaries require 0 < a < 1/8')
    return [math.sqrt((1-2*a-sign*math.sqrt(1-8*a))/2) for sign in (1,-1)]


def selkov_trap(a, b):
    """Outer polygon: x>=0, y>=0, y<=Y, x+y<=L."""
    selkov(a,b)
    y = b/a+1
    return {'Y': y, 'L': y+b+1,
            'top_max_ydot': -a, 'diagonal_max_xdot_plus_ydot': -1}


def vdp(mu):
    if mu < 0:
        raise ValueError('This study uses mu >= 0')
    return lambda t, s: (s[1], mu*(1-s[0]**2)*s[1]-s[0])


def cubic(x):
    return x**3/3-x


def vdp_lienard(mu):
    if mu <= 0:
        raise ValueError('The transformed coordinates require mu > 0')
    return lambda t, s: (mu*(s[1]-cubic(s[0])), -s[0]/mu)


def duffing(epsilon):
    if epsilon < 0:
        raise ValueError('This study uses the hardening case epsilon >= 0')
    return lambda t, s: (s[1], -s[0]-epsilon*s[0]**3)


def duffing_energy(x, v, epsilon):
    return (v*v+x*x)/2+epsilon*x**4/4


def duffing_period(amplitude, epsilon, panels=2000):
    """Independent energy-integral period; Simpson quadrature removes endpoint pole."""
    if amplitude <= 0 or epsilon < 0 or panels <= 0 or panels % 2:
        raise ValueError('Positive amplitude, epsilon >= 0, positive even panels required')
    h = math.pi/(2*panels)
    def f(theta):
        return 1/math.sqrt(1+epsilon*amplitude**2*(1+math.sin(theta)**2)/2)
    return 4*h/3*(f(0)+f(math.pi/2)+sum((4 if i%2 else 2)*f(i*h) for i in range(1,panels)))


def upcrossings(rows, level=0, after=0):
    """Linearly interpolate x=level crossings with increasing x; return (t,y)."""
    found = []
    for p,q in zip(rows, rows[1:]):
        if p[1] < level <= q[1]:
            fraction = (level-p[1])/(q[1]-p[1])
            t = p[0]+fraction*(q[0]-p[0])
            if t >= after:
                found.append((t,p[2]+fraction*(q[2]-p[2])))
    return found


def cycle_metrics(rows, level=0, after=0):
    crossings = upcrossings(rows, level, after)
    if len(crossings) < 6:
        raise ValueError('Need at least six late crossings for five complete cycles')
    crossings = crossings[-6:]
    periods = [q[0]-p[0] for p,q in zip(crossings,crossings[1:])]
    late = [r for r in rows if crossings[0][0] <= r[0] <= crossings[-1][0]]
    return {'mean_period': sum(periods)/len(periods),
            'period_range': max(periods)-min(periods),
            'return_y_range': max(c[1] for c in crossings)-min(c[1] for c in crossings),
            'last_return_y': crossings[-1][1],
            'x_min': min(r[1] for r in late), 'x_max': max(r[1] for r in late),
            'measurement_start': crossings[0][0], 'measurement_end': crossings[-1][0],
            'cycles_measured': len(periods)}


def max_difference(coarse, fine):
    if len(fine) != 2*(len(coarse)-1)+1:
        raise ValueError('Expected matched intervals with a halved fine step')
    return max(math.dist(p[1:],q[1:]) for p,q in zip(coarse,fine[::2]))


def undamped_pendulum(t, state):
    return state[1], -math.sin(state[0])


def pendulum_period(amplitude, panels=2000):
    if not 0 < amplitude < math.pi or panels <= 0 or panels % 2:
        raise ValueError('Use 0 < amplitude < pi and positive even panels')
    h=math.pi/(2*panels); k2=math.sin(amplitude/2)**2
    def f(theta): return 1/math.sqrt(1-k2*math.sin(theta)**2)
    return 4*h/3*(f(0)+f(math.pi/2)+sum((4 if i%2 else 2)*f(i*h) for i in range(1,panels)))


def cubic_damping(epsilon):
    return lambda t,s: (s[1],-s[0]-epsilon*s[1]**3)


def cubic_damping_approx(t, amplitude, epsilon):
    return amplitude*math.cos(t)/math.sqrt(1+3*epsilon*amplitude**2*t/4)


def swing(epsilon, gamma, linear=False):
    def rhs(t,s):
        position=s[0] if linear else math.sin(s[0])
        return s[1], -(1+epsilon*gamma+epsilon*math.cos(2*t))*position
    return rhs


def swing_averaged(epsilon, gamma):
    # Physical-time quadratures x=A*cos(t)+B*sin(t), regular at zero amplitude.
    # Equivalent slow-time equations: r'=r*sin(2*phi)/4,
    # phi'=(gamma+cos(2*phi)/2)/2, T=epsilon*t.
    return lambda t,s: (epsilon*(gamma/2-1/4)*s[1],
                         -epsilon*(gamma/2+1/4)*s[0])


def approximation_results():
    pend=[]
    for amplitude in (.1,.4,.8):
        period=pendulum_period(amplitude)
        rows=integrate(undamped_pendulum,[amplitude,0],100,.02)
        pend.append({'amplitude':amplitude,'exact_integral_frequency':2*math.pi/period,
                     'leading_frequency':1-amplitude**2/16,
                     'numerical_period':cycle_metrics(rows,after=50)['mean_period'],
                     'energy_integral_period':period})
    damp=[]
    for epsilon in (.1,2):
        rows=integrate(cubic_damping(epsilon),[1,0],50,.01)
        fine=integrate(cubic_damping(epsilon),[1,0],50,.005)
        errors=[abs(r[1]-cubic_damping_approx(r[0],1,epsilon)) for r in fine]
        damp.append({'epsilon':epsilon,'amplitude':1,'duration':50,
                     'maximum_approximation_error':max(errors),
                     'rms_approximation_error':math.sqrt(sum(e*e for e in errors)/len(errors)),
                     'max_step_refinement_difference':max_difference(rows,fine),
                     'final_energy':sum(x*x for x in fine[-1][1:])/2})
    swings=[]
    for gamma in (0,1):
        epsilon=.1; initial=[.005,0]; duration=160; step=.01
        rows=integrate(swing(epsilon,gamma),initial,duration,step)
        fine=integrate(swing(epsilon,gamma),initial,duration,step/2)
        linear=integrate(swing(epsilon,gamma,True),initial,duration,step)
        averaged=integrate(swing_averaged(epsilon,gamma),initial,duration,step)
        prediction=[r[1]*math.cos(r[0])+r[2]*math.sin(r[0]) for r in averaged]
        swings.append({'epsilon':epsilon,'gamma':gamma,'initial':initial,'duration':duration,
                        'max_absolute_angle':max(abs(r[1]) for r in rows),
                        'max_linearization_error':max(abs(p[1]-q[1]) for p,q in zip(rows,linear)),
                        'max_averaging_error_vs_linear':max(abs(p[1]-q) for p,q in zip(linear,prediction)),
                        'max_step_refinement_difference':max_difference(rows,fine),
                        'leading_growth_rate':epsilon/4 if gamma==0 else 0})
    return {'pendulum':pend,'cubic_velocity_damping':damp,'pumped_swing':swings,
            'swing_zero_state':'Exact solution for every epsilon and gamma; a nonzero perturbation is required.',
            'swing_leading_instability_band':'abs(gamma)<1/2, growth=epsilon*sqrt(1-4*gamma^2)/4',
            'vdp_green_integral':'epsilon*pi*R^2*(1-R^2/4)=0; nonzero circle gives R=2'}


def results():
    radial = []
    for kind,starts in [('stable',(.25,1.5)), ('unstable',(.98,1.02)),
                        ('half_stable',(.8,1.5))]:
        for initial in starts:
            rows,stop = radial_trajectory(kind,initial)
            radial.append({'kind':kind, 'initial_radius':initial,
                           'final_time':rows[-1][0], 'final_radius':math.hypot(*rows[-1][1:]),
                           'terminated_before_r2':stop})
    stable = integrate(radial_field('stable'),[.25,0],10,.01)
    radial_error = max(abs(math.hypot(*r[1:])-stable_radius(r[0],.25)) for r in stable)
    grad = integrate(gradient,[.5,.7],10,.01)
    values = [potential(*r[1:]) for r in grad]
    sel = []
    for b in (.2,.5,1):
        a,initial = .1,[.4,1.5]
        coarse = integrate(selkov(a,b),initial,500,.02)
        fine = integrate(selkov(a,b),initial,500,.01)
        item = {'a':a,'b':b,'initial':initial,'duration':500,'step':.02,
                'equilibrium':selkov_equilibrium(a,b),
                'endpoint':list(fine[-1][1:]),
                'max_step_refinement_difference':max_difference(coarse,fine),
                'minimum_xy':min(min(r[1:]) for r in fine), 'outer_trap':selkov_trap(a,b)}
        if item['equilibrium']['stability'] == 'repeller':
            item['cycle'] = cycle_metrics(fine,level=b,after=300)
            other = integrate(selkov(a,b),[1.2,.3],500,.01)
            item['second_initial'] = [1.2,.3]
            item['second_cycle'] = cycle_metrics(other,level=b,after=300)
        else:
            item['distance_to_equilibrium'] = math.dist(fine[-1][1:],(b,item['equilibrium']['y']))
        sel.append(item)
    vdps = []
    for mu,duration,step in [(.1,600,.02),(1,240,.02),(10,400,.004)]:
        initial = [.1,0] if mu == .1 else [2,0]
        coarse = integrate(vdp(mu),initial,duration,step)
        fine = integrate(vdp(mu),initial,duration,step/2)
        metric = cycle_metrics(fine,after=duration/2)
        other = integrate(vdp(mu),[3,1],duration,step)
        vdps.append({'mu':mu,'initial_x_velocity':initial,'duration':duration,'step':step,
                     'cycle':metric,'coarse_cycle':cycle_metrics(coarse,after=duration/2),
                     'second_initial_x_velocity':[3,1],
                     'second_cycle':cycle_metrics(other,after=duration/2),
                     'max_step_refinement_difference':max_difference(coarse,fine),
                     'large_mu_period_leading_term':mu*(3-2*math.log(2)) if mu == 10 else None})
    duff = []
    for amplitude in (.5,1.5,2):
        rows = integrate(duffing(.1),[amplitude,0],100,.02)
        energy = duffing_energy(amplitude,0,.1)
        duff.append({'epsilon':.1,'initial_amplitude':amplitude,'duration':100,'step':.02,
                     'cycle':cycle_metrics(rows,after=50),
                     'energy_integral_period':duffing_period(amplitude,.1),
                     'max_energy_drift':max(abs(duffing_energy(*r[1:],.1)-energy) for r in rows)})
    return {'provenance':'Computed mathematical examples; no new SIMS behavioral coupling.',
            'radial':radial,'stable_radius_max_error':radial_error,
            'gradient':{'initial':[.5,.7],'duration':10,'step':.01,
                        'largest_sampled_potential_increment':max(b-a for a,b in zip(values,values[1:])),
                        'analytic_identity':'dV/dt = -sin(y)^2 - x^2*cos(y)^2'},
            'dulac':[
                {'field':'x*(2-x-y), y*(4*x-x*x-3)','weight':'1/(x*y)',
                 'weighted_divergence':'-1/y','domain':'x>0, y>0',
                 'provenance':'Reconstructed algebraically from the displayed weighted components.'},
                {'field':'y, -x-y+x*x+y*y','weight':'exp(-2*x)',
                 'weighted_divergence':'-exp(-2*x)','domain':'R^2',
                 'provenance':'Exact supplied equations.'}],
            'unit_annulus':{'inner_radius':.5,'outer_radius':1.5,
                            'inner_radial_rate':radial_rate(.5,'stable'),
                            'outer_radial_rate':radial_rate(1.5,'stable'),
                            'angular_rate':1,'equilibria_in_annulus':0},
            'missing_mu_example':{'status':'not run',
                                  'reason':'Figure 7.3.3 / Example 7.3.1 crop omits the vector field; awaiting equations.'},
            'selkov_hopf_b_at_a_0_1':selkov_hopf_bounds(.1), 'selkov':sel,
            'van_der_pol':vdps,'duffing':duff,'averaging':approximation_results(),
            'lienard_certificate':{'f':'mu*(x^2-1)','g':'x','F':'mu*(x^3/3-x)',
                                    'requires':'mu>0','positive_zero_of_F':math.sqrt(3),
                                    'result':'Unique stable limit cycle; all supplied hypotheses verified analytically.'},
            'zero_eigenvalue_vs_hopf':{
                'provenance':'Chosen comparison; Figure 8.1.7 equations were not supplied.',
                'pitchfork':'xdot=mu*x-x^3, ydot=-y; origin eigenvalues mu,-1',
                'hopf':'xdot=(mu-r^2)*x-y, ydot=x+(mu-r^2)*y; origin eigenvalues mu +/- i',
                'positive_mu':.5,'pitchfork_stable_x':[-math.sqrt(.5),math.sqrt(.5)],
                'hopf_stable_radius':math.sqrt(.5),'hopf_period':2*math.pi}}


def close_results(a,b):
    if isinstance(a,dict) and isinstance(b,dict):
        return a.keys()==b.keys() and all(close_results(a[k],b[k]) for k in a)
    if isinstance(a,list) and isinstance(b,list):
        return len(a)==len(b) and all(close_results(x,y) for x,y in zip(a,b))
    if isinstance(a,float) and isinstance(b,(int,float)):
        return math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-10)
    return a==b


def validate_measurements(data):
    """Accuracy gates for the saved long integrations, beyond fast unit tests."""
    def require(condition,message):
        if not condition: raise ArithmeticError(message)
    for row in data['van_der_pol']:
        cycle=row['cycle']
        require(abs(cycle['mean_period']-row['coarse_cycle']['mean_period'])<5e-5,
                'van der Pol period did not survive step refinement')
        require(abs(cycle['mean_period']-row['second_cycle']['mean_period'])<1e-4,
                'van der Pol late period differs between starting states')
        require(row['max_step_refinement_difference']<.01,'van der Pol state error gate failed')
        require(cycle['period_range']<1e-4,'van der Pol late periods have not stabilized')
    for row in data['selkov']:
        require(row['minimum_xy']>0,'Selkov trajectory left the positive quadrant')
        require(row['max_step_refinement_difference']<1e-6,'Selkov refinement failed')
        if 'cycle' in row:
            require(abs(row['cycle']['mean_period']-row['second_cycle']['mean_period'])<1e-4,
                    'Selkov cycles differ between starting states')
            require(row['cycle']['period_range']<1e-4,'Selkov late periods have not stabilized')
        else:
            require(row['distance_to_equilibrium']<1e-7,'Selkov endpoint has not settled')
    for row in data['duffing']:
        require(abs(row['cycle']['mean_period']-row['energy_integral_period'])<1e-5,
                'Duffing period disagrees with independent integral')
        require(row['max_energy_drift']<1e-6,'Duffing energy drift exceeds tolerance')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    path = Path(__file__).with_name('oscillation_results.json')
    computed = results()
    validate_measurements(computed)
    if args.check:
        if not close_results(computed,json.loads(path.read_text(encoding='utf-8'))):
            raise SystemExit('FAIL: oscillation results differ.')
        print('PASS: oscillation results reproduced (relative 1e-8 / absolute 1e-10 tolerance).')
    else:
        path.write_text(json.dumps(computed,indent=2)+'\n',encoding='utf-8',newline='\n')
        print('Saved cycle, exclusion, Selkov, van der Pol, and Duffing checks.')
