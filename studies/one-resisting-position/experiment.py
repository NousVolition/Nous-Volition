"""Human coordination through nine SIMS, with one resisting position.

See README.md and the results metadata for the simulation assumptions.
"""
from pathlib import Path
import argparse
import json
import random
from itertools import product

from base_simulation import network, matched_schedule, seed_for, simulate, step_b


def run(initial, seed, policy='ordinary', seat=0, topology='ring', innovation=.02,
        continue_after_consensus=False):
    rng = random.Random(seed)
    neighbors = network(topology)
    state = list(initial)
    first = 0 if len(set(state)) == 1 else None
    if first == 0 and not continue_after_consensus:
        return {'first_consensus': 0, 'final_consensus': True, 'final': state, 'breaks': 0}
    breaks = 0
    for second in range(1, 121):
        order = list(range(9))
        rng.shuffle(order)
        for s in order:
            if rng.random() >= .25:
                continue
            was_unanimous = len(set(state)) == 1
            before = state[s]
            if rng.random() < innovation:
                target, refused = 1 - before, False
            else:
                donor = rng.choices(neighbors[s], weights=[1.0] * len(neighbors[s]))[0]
                target = state[donor]
                refused = target != before and rng.random() < .15
            if s == seat and policy == 'hold':
                target, refused = initial[seat], False
            elif s == seat and policy == 'oppose':
                red = sum(state[n] == 0 for n in neighbors[s])
                blue = len(neighbors[s]) - red
                # Opposite of local majority; keep current color on a tie.
                target = 1 if red > blue else 0 if blue > red else before
                refused = False
            if not refused:
                state[s] = target
            now_unanimous = len(set(state)) == 1
            breaks += was_unanimous and not now_unanimous
            if now_unanimous and first is None:
                first = second
            if now_unanimous and not continue_after_consensus:
                return {'first_consensus': first, 'final_consensus': True, 'final': state, 'breaks': breaks}
        if policy == 'hold':
            assert state[seat] == initial[seat]
    return {'first_consensus': first, 'final_consensus': len(set(state)) == 1,
            'final': state, 'breaks': breaks}


def build_results():
    seed = 20261008
    specs = matched_schedule(4000, seed_for(seed, 'main', 'schedule'))
    # Compare independently implemented ordinary dynamics against the original.
    for spec in specs[:100]:
        case_seed = seed_for(seed, 'main', spec['block'], 'C')
        original = simulate('C', spec['initial'], spec['seat_to_id'], case_seed)
        followup = run(spec['initial'], case_seed)
        assert original['consensus_time'] == followup['first_consensus']
        assert original['final'] == followup['final']
    output = {'data_kind': 'simulation', 'seed': seed, 'rounds_per_case': len(specs),
              'baseline_equivalence_checks': 100, 'cases': []}
    cases = [
        ('Ring: ordinary C', 'ordinary', 0, 'ring', .02, False),
        ('Ring: seat 0 holds its initial color', 'hold', 0, 'ring', .02, False),
        ('Star: hub holds its initial color', 'hold', 0, 'star', .02, False),
        ('Star: leaf holds its initial color', 'hold', 1, 'star', .02, False),
        ('Ring: ordinary, no initiative, continue for 120 s', 'ordinary', 0, 'ring', 0, True),
        ('Ring: one local opponent, no other initiative, continue for 120 s', 'oppose', 0, 'ring', 0, True),
    ]
    for name, policy, seat, topology, innovation, ongoing in cases:
        rows = [run(s['initial'], seed_for(seed, 'main', s['block'], 'C'),
                    policy, seat, topology, innovation, ongoing) for s in specs]
        successful = [i for i, r in enumerate(rows) if r['first_consensus'] is not None]
        agreements_with_focal = sum(rows[i]['final'][seat] == specs[i]['initial'][seat]
                                    for i in successful) if not ongoing else None
        if policy == 'hold':
            assert agreements_with_focal == len(successful)
        output['cases'].append({'name': name, 'first_consensus_n': len(successful),
                                'first_consensus_fraction': len(successful) / len(rows),
                                'mean_capped_seconds': sum(r['first_consensus'] if r['first_consensus'] is not None else 120 for r in rows)/len(rows),
                                'unanimous_at_120_fraction': sum(r['final_consensus'] for r in rows)/len(rows) if ongoing else None,
                                'rounds_with_consensus_broken': sum(r['breaks'] > 0 for r in rows),
                                'successful_rounds_at_focal_initial_color': agreements_with_focal})
        print(json.dumps(output['cases'][-1]), flush=True)
    exact_a = exact_b = 0
    for initial in product((0, 1), repeat=9):
        # A: seat 1 leads; distinct stubborn follower at seat 0.
        exact_a += initial[0] == initial[1]
        state = initial
        for _ in range(12):
            nxt = list(step_b(state))
            nxt[0] = initial[0]
            state = tuple(nxt)
        exact_b += len(set(state)) == 1
    output['exact_hold'] = {'A_distinct_stubborn_follower': [exact_a, 512],
                            'B_one_frozen_seat': [exact_b, 512]}
    output['assumptions'] = {'ordinary_C': 'Each second, random sequential order; activation .25; local copying with refusal .15; initiative .02 unless explicitly disabled.', 'hold': 'The selected seat always retains its initial color; the exception attaches to the seat, not identity.', 'oppose': "On each active opportunity the selected seat chooses the opposite of its visible neighbors' majority; holds on a tie. No global information.", 'continued_runs': 'No stopping at first consensus; observe the entire 120 seconds. Initiative is zero for the ordinary and opponent continuation comparison.', 'matching': 'All cases use the same 4,000 starts and seed derivation as the original main sample. State-dependent draws need not remain aligned between different policies.', 'population': 'Nine SIMS (simulated participants) representing a human coordination task. These conditions extend the original study.', 'interpretation': 'All successful frozen-seat rounds must match that seat by construction. This alone is not evidence of authority or persuasion.'}
    print(json.dumps(output['exact_hold']), flush=True)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true',
                        help='Rerun and compare every result with saved results.json without replacing it')
    args = parser.parse_args()
    output = build_results()
    destination = Path(__file__).with_name('results.json')
    if args.check:
        expected = json.loads(destination.read_text(encoding='utf-8'))
        if output != expected:
            raise SystemExit('FAIL: results differ from saved results.json')
        print('PASS: all six 4,000-round cases, exact A/B counts, and metadata reproduced.')
    else:
        destination.write_text(json.dumps(output, indent=2) + '\n',
                               encoding='utf-8', newline='\n')
        print('Saved results.json')


if __name__ == '__main__':
    main()
