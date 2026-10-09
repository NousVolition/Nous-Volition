"""Matched network experiments with SIMS (simulated participants)."""
import hashlib
import math
import random
from models import menger_graph, koch_graph, ring_graph


def seed_for(*parts):
    return int.from_bytes(hashlib.sha256('|'.join(map(str, parts)).encode()).digest()[:8], 'big')


def run(graph, initial, seed, policy='ordinary', focal=0, initiative=0.0,
        refusal=0.15, activation=0.25, horizon=120, seat_to_id=None):
    n = len(graph)
    if n != len(initial) or any(x not in (0, 1) for x in initial):
        raise ValueError('One binary starting color per seat is required')
    if any(not row or any(j < 0 or j >= n for j in row) for row in graph):
        raise ValueError('Every SIM must have valid neighbors')
    if policy not in ('ordinary', 'hold', 'oppose') or not 0 <= focal < n:
        raise ValueError('Unknown policy or focal seat')
    if any(not 0 <= p <= 1 for p in (initiative, refusal, activation)):
        raise ValueError('Probabilities must lie in [0,1]')
    identities = list(range(n)) if seat_to_id is None else list(seat_to_id)
    if sorted(identities) != list(range(n)):
        raise ValueError('Identity labels must form a permutation')
    rng = random.Random(seed)
    state = list(initial)
    red = state.count(0)
    first = 0 if red in (0, n) else None
    switches = refusals = breaks = agreement_snapshots = 0
    first_switch_id = None
    credits = [0]*n
    # Fixed number of draws per seat maintains a common opportunity stream
    # across policies, even after state-dependent behavior diverges.
    for second in range(1, horizon+1):
        order = list(range(n))
        rng.shuffle(order)
        for seat in order:
            active_u, initiative_u, donor_u, refusal_u = (rng.random() for _ in range(4))
            if active_u >= activation:
                continue
            before = state[seat]
            donor = None
            refused = False
            if seat == focal and policy == 'hold':
                target = initial[focal]
            elif seat == focal and policy == 'oppose':
                ones = sum(state[j] for j in graph[seat])
                target = 0 if 2*ones > len(graph[seat]) else 1 if 2*ones < len(graph[seat]) else before
            elif initiative_u < initiative:
                target = 1-before
            else:
                donor = graph[seat][int(donor_u*len(graph[seat]))]
                target = state[donor]
                refused = target != before and refusal_u < refusal
                refusals += int(refused)
            was_unanimous = red in (0, n)
            if target != before and not refused:
                state[seat] = target
                red += 1 if target == 0 else -1
                switches += 1
                if first_switch_id is None:
                    first_switch_id = identities[seat]
                if donor is not None:
                    credits[donor] += 1
            now_unanimous = red in (0, n)
            breaks += int(was_unanimous and not now_unanimous)
            if now_unanimous and first is None:
                first = second
        agreement_snapshots += int(red in (0, n))
    by_id = [0]*n
    for seat, identity in enumerate(identities):
        by_id[identity] = credits[seat]
    return {'first_consensus': first, 'unanimous_at_end': red in (0, n),
            'capped_time': first if first is not None else horizon,
            'switches': switches, 'refusals': refusals, 'breaks': breaks,
            'agreement_snapshot_fraction': agreement_snapshots/horizon,
            'first_switch_id': first_switch_id, 'final': state,
            'credits_by_seat': credits, 'credits_by_id': by_id}


def wilson(successes, total):
    z = 1.959963984540054
    p = successes/total
    denominator = 1+z*z/total
    center = (p+z*z/(2*total))/denominator
    half = z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/denominator
    return [max(0.0, center-half), min(1.0, center+half)]


def scenario_specs():
    menger = menger_graph(1)
    high = max(range(len(menger)), key=lambda i: len(menger[i]))
    low = min(range(len(menger)), key=lambda i: len(menger[i]))
    specs = []
    for name, graph in [('Menger L1', menger), ('Ring 20', ring_graph(20))]:
        specs.append((name, graph, 'ordinary', high, 'baseline'))
        for policy in ('hold', 'oppose'):
            for seat, role in [(high, 'Menger corner'), (low, 'Menger edge')]:
                specs.append((name, graph, policy, seat, role))
    for name, graph in [('Koch L2', koch_graph(2)), ('Ring 48', ring_graph(48))]:
        for policy in ('ordinary', 'hold', 'oppose'):
            specs.append((name, graph, policy, 0, 'boundary seat'))
    return specs


def experiment(rounds=512, sensitivity_rounds=128, seed=20261009):
    specs = scenario_specs()
    rows = []
    paired = []
    for initiative, count in [(0.0, rounds), (0.02, sensitivity_rounds)]:
        sums = [{'first': 0, 'end': 0, 'capped': 0, 'switches': 0, 'refusals': 0,
                 'break_rounds': 0, 'snapshots': 0.0, 'credits': [0]*len(s[1])} for s in specs]
        outcomes = [[] for _ in specs]
        for block in range(count):
            scenario_order = list(range(len(specs)))
            random.Random(seed_for(seed, 'order', initiative, block)).shuffle(scenario_order)
            for i in scenario_order:
                name, graph, policy, seat, role = specs[i]
                n = len(graph)
                rng = random.Random(seed_for(seed, 'start', n, block))
                initial = [rng.randrange(2) for _ in range(n)]
                labels = list(range(n))
                random.Random(seed_for(seed, 'identity', n, block)).shuffle(labels)
                result = run(graph, initial, seed_for(seed, 'dynamics', n, block), policy,
                             seat, initiative, seat_to_id=labels)
                total = sums[i]
                hit = result['first_consensus'] is not None
                total['first'] += int(hit)
                total['end'] += int(result['unanimous_at_end'])
                total['capped'] += result['capped_time']
                total['switches'] += result['switches']
                total['refusals'] += result['refusals']
                total['break_rounds'] += int(result['breaks'] > 0)
                total['snapshots'] += result['agreement_snapshot_fraction']
                total['credits'] = [a+b for a, b in zip(total['credits'], result['credits_by_seat'])]
                outcomes[i].append((block, int(hit), result['capped_time']))
        for i, (name, graph, policy, seat, role) in enumerate(specs):
            total = sums[i]
            credit_total = sum(total['credits'])
            rows.append({'network': name, 'sims': len(graph), 'policy': policy,
                         'focal_seat': seat, 'focal_role': role, 'focal_degree': len(graph[seat]),
                         'initiative': initiative, 'rounds': count,
                         'first_consensus_n': total['first'], 'first_consensus_fraction': total['first']/count,
                         'first_consensus_wilson95': wilson(total['first'], count),
                         'unanimous_at_120_fraction': total['end']/count,
                         'mean_capped_seconds': total['capped']/count,
                         'mean_switches': total['switches']/count, 'mean_refusals': total['refusals']/count,
                         'rounds_with_broken_agreement': total['break_rounds'],
                         'mean_agreement_snapshot_fraction': total['snapshots']/count,
                         'copy_credit_share_by_seat': [c/credit_total if credit_total else 0 for c in total['credits']]})
        for i, j in [(i, i+5) for i in range(5)]+[(i, i+3) for i in range(10, 13)]:
            left, right = sorted(outcomes[i]), sorted(outcomes[j])
            for metric, column in [('first_consensus', 1), ('capped_seconds', 2)]:
                diffs = [a[column]-b[column] for a, b in zip(left, right)]
                mean = sum(diffs)/count
                sem = math.sqrt(sum((x-mean)**2 for x in diffs)/(count-1)/count) if count > 1 else 0
                paired.append({'network': specs[i][0], 'control': specs[j][0],
                               'policy': specs[i][2], 'focal_role': specs[i][4],
                               'initiative': initiative, 'metric': metric,
                               'mean_paired_difference': mean,
                               'monte_carlo_normal95': [mean-1.96*sem, mean+1.96*sem]})
    # Both drawings use exactly the same adjacency and paired random schedule.
    for row in rows:
        if row['network'] == 'Koch L2':
            match = next(r for r in rows if r['network'] == 'Ring 48' and
                         r['policy'] == row['policy'] and r['initiative'] == row['initiative'])
            assert {k:v for k,v in row.items() if k != 'network'} == {k:v for k,v in match.items() if k != 'network'}
    return {'seed': seed, 'data_kind': 'SIMS simulation', 'total_rounds': sum(r['rounds'] for r in rows),
            'horizon_seconds': 120, 'activation': 0.25, 'refusal': 0.15,
            'cases': rows, 'paired_comparisons': paired}
