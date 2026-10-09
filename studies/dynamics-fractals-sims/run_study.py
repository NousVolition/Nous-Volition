"""Reproduce the dynamics/fractals/SIMS experiment using the standard library."""
import argparse
import json
import math
from pathlib import Path
from models import (integrate, logistic, logistic_exact, lorenz, spring,
                    spring_exact, pendulum, threshold, threshold_exact,
                    menger_metrics, koch_metrics)
from sims import experiment

ROOT = Path(__file__).resolve().parent


def mathematical_checks():
    accuracy = []
    for method in ('euler', 'rk4'):
        for step in (0.2, 0.1, 0.05):
            rows = integrate(logistic, [0.1], 4, step, method)
            accuracy.append({'method': method, 'step': step,
                             'max_error': max(abs(x-logistic_exact(t, 0.1)) for t,x in rows)})
    spring_rows = integrate(spring, [1,0], 20, 0.01)
    phase = integrate(pendulum, [1.4,0], 20, 0.01)
    energy = [v*v/2+1-math.cos(x) for _,x,v in phase]
    ref = integrate(lorenz, [1,1,1], 1, 0.00125)[-1][1:]
    sensitivity = []
    for step in (0.01, 0.005):
        a = integrate(lorenz, [1,1,1], 40, step)
        b = integrate(lorenz, [1+1e-8,1,1], 40, step)
        separation = [math.dist(x[1:], y[1:]) for x,y in zip(a,b)]
        crossing = next((row[0] for row,d in zip(a,separation) if d >= 1), None)
        sensitivity.append({'step': step, 'initial_displacement': 1e-8,
                            'first_separation_at_least_one': crossing,
                            'short_time_error_at_t1': math.dist(a[round(1/step)][1:], ref)})
    laser = []
    for pump in (0.5,1,1.5):
        rows = integrate(threshold(pump), [0.01], 40, 0.05)
        laser.append({'pump': pump, 'positive_seed': 0.01, 'equilibrium_from_positive_seed': max(0,pump-1),
                      'value_at_40': rows[-1][1],
                      'max_error': max(abs(x-threshold_exact(t,0.01,pump)) for t,x in rows)})
    return {'logistic_accuracy': accuracy,
            'spring': {'max_error': max(abs(x-spring_exact(t)) for t,x,v in spring_rows),
                       'minimum_position': min(x for t,x,v in spring_rows),
                       'overdamped_limit_max_error_after_t1': max(abs(x-math.exp(-t/4)) for t,x,v in spring_rows if t >= 1)},
            'pendulum': {'initial_energy': energy[0], 'final_energy': energy[-1],
                         'maximum_energy_step_increase': max(b-a for a,b in zip(energy,energy[1:]))},
            'lorenz': sensitivity, 'laser_inspired_threshold': laser,
            'menger': [menger_metrics(i) for i in range(4)],
            'koch': [koch_metrics(i) for i in range(6)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds', type=int, default=512)
    parser.add_argument('--sensitivity-rounds', type=int, default=128)
    parser.add_argument('--seed', type=int, default=20261009)
    parser.add_argument('--check', action='store_true', help='Recompute and compare with saved results')
    args = parser.parse_args()
    if min(args.rounds, args.sensitivity_rounds) < 2:
        parser.error('Use at least two rounds in each sample')
    print('Checking dynamics and fractal geometry...', flush=True)
    math_results = mathematical_checks()
    print('Running matched SIMS network scenarios...', flush=True)
    results = {'mathematics': math_results,
               'sims': experiment(args.rounds, args.sensitivity_rounds, args.seed)}
    dest = ROOT / 'results.json'
    if args.check:
        expected = json.loads(dest.read_text(encoding='utf-8'))
        # Stable integer checks and tight floating comparison allow libm differences.
        def compare(a, b, path='results'):
            if isinstance(a, dict) and isinstance(b, dict):
                if a.keys() != b.keys():
                    raise AssertionError(path+' keys differ')
                for key in a:
                    compare(a[key], b[key], path+'.'+key)
            elif isinstance(a, list) and isinstance(b, list):
                if len(a) != len(b):
                    raise AssertionError(path+' length differs')
                for i,(x,y) in enumerate(zip(a,b)):
                    compare(x,y,path+f'[{i}]')
            elif isinstance(a,float) and isinstance(b,(int,float)):
                if not math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-10):
                    raise AssertionError(path+f': {a} differs from {b}')
            elif a != b:
                raise AssertionError(path+f': {a} differs from {b}')
        compare(results, expected)
        print('PASS: saved mathematics and all SIMS aggregates reproduced.')
    else:
        dest.write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8',newline='\n')
        print(f"Saved {results['sims']['total_rounds']} SIMS rounds and mathematical checks.")


if __name__ == '__main__':
    main()
