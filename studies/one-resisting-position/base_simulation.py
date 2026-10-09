"""Standard-library simulator. Colors are 0/1; IDs and seats are distinct.

Rule B is an analogy, not a water or molecular-dynamics simulation.
C represents human choices through specified stochastic behavioral assumptions.
"""
from dataclasses import dataclass
from itertools import permutations, product
import hashlib
import random

N = 9
HORIZON = 120


def seed_for(seed, *labels):
    """Stable independent streams, unaffected by loop order or Python hash salt."""
    text = "|".join(map(str, (seed,) + labels))
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")


def network(kind="ring"):
    if kind == "ring":
        return tuple(((s - 1) % N, (s + 1) % N) for s in range(N))
    if kind == "star":
        return (tuple(range(1, N)),) + tuple((0,) for _ in range(1, N))
    raise ValueError("Network must be ring or star")


def unanimous(state):
    return len(set(state)) == 1


def step_b(state):
    """Simultaneous decisions from the OLD state; self-inclusive majority."""
    if len(state) != N or any(x not in (0, 1) for x in state):
        raise ValueError("Expected nine binary colors")
    return tuple(1 - x if state[(s - 1) % N] == state[(s + 1) % N] != x
                 else x for s, x in enumerate(state))


@dataclass(frozen=True)
class Parameters:
    refusal: float = 0.15
    innovation: float = 0.02
    activation: float = 0.25
    update: str = "async1"
    compliance: float = 1.0
    heterogeneous: bool = False
    former_leader_weight: float = 1.0

    def __post_init__(self):
        for name in ("refusal", "innovation", "activation", "compliance"):
            if not 0 <= getattr(self, name) <= 1:
                raise ValueError(name + " must be in [0,1]")
        if self.update not in ("async1", "sync10"):
            raise ValueError("Unknown update schedule")
        if self.former_leader_weight <= 0:
            raise ValueError("Former-leader weight must be positive")


def simulate(condition, initial, seat_to_id, seed, params=None, leader_id=0,
             topology="ring", former_leader=None, keep_trace=False):
    """Stop at first consensus, or censor at 120 s.

    async1 C: each second, shuffled sequential seats, independent activation.
    sync10 C sensitivity: everyone decides every 10 s from the old state.
    A: leader's initial color is the fixed command, acted on every 10 s.
    B: simultaneous deterministic two-neighbor rule every 10 s.
    Traces include holds/refusals; copy credits only count actual switches.
    """
    if condition not in ("A", "B", "C"):
        raise ValueError("Condition must be A, B, or C")
    if len(initial) != N or any(x not in (0, 1) for x in initial):
        raise ValueError("Expected nine binary colors")
    if sorted(seat_to_id) != list(range(N)):
        raise ValueError("IDs must be a permutation of 0..8")
    if leader_id not in range(N) or former_leader not in (None, *range(N)):
        raise ValueError("Invalid leader identity")
    if condition == "B" and topology != "ring":
        raise ValueError("B is defined only on the two-neighbor ring")
    params = params or Parameters()
    rng = random.Random(seed)
    neighbors = network(topology)
    state = list(initial)
    leader_seat = seat_to_id.index(leader_id)
    command = state[leader_seat]
    weights = [4.0 if params.heterogeneous and i == 0 else 1.0 for i in seat_to_id]
    if former_leader is not None:
        weights[seat_to_id.index(former_leader)] *= params.former_leader_weight
    credits = [0.0] * N
    switches_by_id = [0] * N
    refusals_by_id = [0] * N
    per_tick = []
    events = []
    first_ids, first_initiative_ids = [], []
    first_time = initiative_time = None
    previous_changed = set()
    previous_tick_state = tuple(state)
    seen_changed_states = {tuple(state)}
    revisits = reversals = proposals = refusals = initiatives = 0
    consensus_time = 0 if unanimous(state) else None
    tick = 1 if condition == "C" and params.update == "async1" else 10
    if keep_trace:
        per_tick.append({"second": 0, "state": list(state)})
    if consensus_time is None:
        for second in range(tick, HORIZON + 1, tick):
            old = state.copy()
            order = list(range(N))
            asynchronous = condition == "C" and params.update == "async1"
            if asynchronous:
                rng.shuffle(order)
            changed = set()
            for seat in order:
                identity = seat_to_id[seat]
                if asynchronous and rng.random() >= params.activation:
                    continue
                visible = state if asynchronous else old
                before = visible[seat]
                target, reason, donors = before, "hold", []
                rejected = False
                if condition == "A":
                    target, donors, reason = command, [leader_seat], "command"
                    rejected = target != before and rng.random() >= params.compliance
                elif condition == "B":
                    left, right = neighbors[seat]
                    if visible[left] == visible[right] != before:
                        target, donors, reason = 1 - before, [left, right], "local_rule"
                else:
                    # Identity 0's profile is a sensitivity assumption only.
                    refusal_p = 0.65 if params.heterogeneous and identity == 0 else params.refusal
                    innovation_p = 0.03 if params.heterogeneous and identity == 0 else params.innovation
                    if rng.random() < innovation_p:
                        target, reason = 1 - before, "initiative"
                    else:
                        candidates = neighbors[seat]
                        donor = rng.choices(candidates, weights=[weights[j] for j in candidates])[0]
                        target, donors, reason = visible[donor], [donor], "copy"
                        rejected = target != before and rng.random() < refusal_p
                differs = target != before
                proposals += differs
                if rejected:
                    refusals += 1
                    refusals_by_id[identity] += 1
                elif differs:
                    state[seat] = target
                    changed.add(seat)
                    switches_by_id[identity] += 1
                    if first_time is None:
                        first_time = second
                    if second == first_time:
                        first_ids.append(identity)
                    if reason == "initiative":
                        initiatives += 1
                        if initiative_time is None:
                            initiative_time = second
                        if second == initiative_time:
                            first_initiative_ids.append(identity)
                    if donors:
                        for donor in donors:
                            credits[donor] += 1 / len(donors)
                if keep_trace:
                    events.append({"second": second, "seat": seat, "identity": identity,
                                   "before": before, "proposed": target,
                                   "after": state[seat], "reason": reason,
                                   "refused": rejected,
                                   "donor_ids": [seat_to_id[j] for j in donors]})
                if asynchronous and unanimous(state):
                    break
            reversals += len(changed & previous_changed)
            previous_changed = changed
            current = tuple(state)
            if current != previous_tick_state:
                revisits += current in seen_changed_states
                seen_changed_states.add(current)
            previous_tick_state = current
            if keep_trace:
                per_tick.append({"second": second, "state": list(state)})
            if unanimous(state):
                consensus_time = second
                break
    by_id = [0.0] * N
    for seat, identity in enumerate(seat_to_id):
        by_id[identity] = credits[seat]
    total = sum(credits)
    return {"condition": condition, "initial": list(initial), "seat_to_id": list(seat_to_id),
            "leader_id": leader_id, "leader_seat": leader_seat, "topology": topology,
            "consensus": consensus_time is not None, "consensus_time": consensus_time,
            "capped_time": consensus_time if consensus_time is not None else HORIZON,
            "final": state, "switches": sum(switches_by_id), "refusals": refusals,
            "differing_proposals": proposals, "initiatives": initiatives,
            "adjacent_tick_reversals": reversals, "state_revisits": revisits,
            "first_switch_ids": sorted(first_ids), "first_switch_time": first_time,
            "first_initiative_ids": sorted(first_initiative_ids),
            "first_initiative_time": initiative_time,
            "credits_by_seat": credits, "credits_by_id": by_id,
            "switches_by_id": switches_by_id, "refusals_by_id": refusals_by_id,
            "copy_hhi": sum((v / total) ** 2 for v in credits) if total else None,
            "former_leader_share": by_id[former_leader] / total
            if former_leader is not None and total else None,
            "trajectory": per_tick, "events": events}


def matched_schedule(blocks, seed):
    """Independent starting states; balanced/shuffled six condition orders."""
    rng = random.Random(seed)
    orders = list(permutations("ABC"))
    selected = []
    for block in range(blocks):
        if block % 6 == 0:
            rng.shuffle(orders)
        mapping = list(range(N))
        rng.shuffle(mapping)
        selected.append({"block": block, "order": "".join(orders[block % 6]),
                         "initial": [rng.randrange(2) for _ in range(N)],
                         "seat_to_id": mapping, "leader_id": rng.randrange(N)})
    return selected


def crossed_mappings(seed):
    """Each identity occupies every seat once in nine mappings."""
    rng = random.Random(seed)
    base = list(range(N))
    rng.shuffle(base)
    shifts = list(range(N))
    rng.shuffle(shifts)
    return [base[k:] + base[:k] for k in shifts]


def exact_b():
    """Enumerate all 512 starts to the first recurring state (not just 120 s)."""
    rows = []
    for initial in product((0, 1), repeat=N):
        state, visited, time = initial, {}, 0
        consensus_time = None
        while state not in visited:
            visited[state] = time
            if unanimous(state) and consensus_time is None:
                consensus_time = time * 10
            state = step_b(state)
            time += 1
        period = time - visited[state]
        rows.append({"initial": list(initial), "attractor": list(state),
                     "period": period, "transient_ticks": visited[state],
                     "consensus_time": consensus_time,
                     "consensus_120": consensus_time is not None and consensus_time <= HORIZON})
    return rows
