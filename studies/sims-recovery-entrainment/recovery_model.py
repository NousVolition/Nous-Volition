"""Six-group SOCIAL analogy. No molecular or fluid equations; no empirical fit.

Each agent requests one partner per round. The partner may cooperate, then shares
its round's resource pool equally among successful requests. All causal rules are
specified here. Display strings are inert unless the explicit semantic coefficient
is nonzero. Actor preferences and organizational transitions are hypotheses.
"""
from dataclasses import dataclass, asdict
import hashlib
import numpy as np

LABELS = ("Ice", "Water", "Fog", "Mist", "Gas (water vapor)", "Smoke")


@dataclass(frozen=True)
class Config:
    n: int = 60
    seed: int = 1100
    rotation: int = 0
    topology: str = "ring"
    balance: str = "equal"
    rounds: int = 120
    behavior: int = 0
    memory: int = 0
    stress: int = 0
    transitions: int = 0
    identity: float = 0.0
    labels: str = "evocative"
    label_shift: int = 0
    semantic: float = 0.0  # negative = assumed avoidance of target label
    semantic_target: int = 5
    stress_kind: str = "combined"
    scarcity: float = 0.55
    decay: float = 0.97
    adaptation: float = 0.08
    random_choice: int = 0


def sigmoid(x):
    return 1 / (1 + np.exp(-np.clip(x, -30, 30)))


def group_sizes(n, balance, rotation=0):
    weights = np.ones(6) / 6 if balance == "equal" else np.array([.35,.25,.15,.10,.10,.05])
    raw = weights * (n - 6)
    sizes = np.floor(raw).astype(int) + 1
    for k in np.argsort(-(raw - np.floor(raw)), kind="stable")[:n-sizes.sum()]:
        sizes[k] += 1
    return np.roll(sizes, rotation % 6)


def make_network(n, topology, rng):
    a = np.zeros((n,n), bool)
    # A ring backbone guarantees initial connectivity. No group labels enter.
    k = 3 if topology == "ring" else 1
    for shift in range(1, k+1):
        i = np.arange(n)
        a[i,(i+shift)%n] = True
        a[(i+shift)%n,i] = True
    if topology == "random":
        ii,jj = np.triu_indices(n,1)
        available = np.flatnonzero(~a[ii,jj])
        chosen = rng.choice(available, size=2*n, replace=False)
        a[ii[chosen],jj[chosen]] = a[jj[chosen],ii[chosen]] = True
    elif topology == "hub":
        # Same 3N undirected edges as ring/random, concentrated around 3 sites.
        hubs = rng.choice(n,3,replace=False)
        ii,jj = np.triu_indices(n,1)
        available = np.flatnonzero((~a[ii,jj]) & (np.isin(ii,hubs)|np.isin(jj,hubs)))
        chosen = rng.choice(available, size=2*n, replace=False)
        a[ii[chosen],jj[chosen]] = a[jj[chosen],ii[chosen]] = True
    elif topology != "ring":
        raise ValueError(topology)
    return a


def initialize(c):
    if c.n < 12 or c.rounds % 3:
        raise ValueError("n >= 12 and rounds divisible by three required")
    rng = np.random.default_rng(np.random.SeedSequence([c.seed,c.n,17]))
    a = make_network(c.n,c.topology,rng)
    g = np.repeat(np.arange(6),group_sizes(c.n,c.balance,c.rotation))
    rng.shuffle(g)  # random identity placement, independent of network sites
    # Two independent cyclic schedules cross each size rank with each trait over
    # the combined discovery/replication batches; no word fixes a profile.
    profile = (g + c.rotation + c.rotation//6) % 6
    # hold, contact exploration, generosity; modest non-moral differences.
    profiles = np.array([[.65,.10,-.12],[.50,.12,0],[.35,.16,.12],
                         [.40,.14,-.06],[.30,.18,.06],[.55,.13,0]])
    traits = profiles[profile] if c.behavior else np.tile([.45,.14,0],(c.n,1))
    return a,g,traits,profile


def opportunity_adjusted(same, success, expected_same):
    """Unconditional cooperation per available partner class, not just choices."""
    exposure = float(np.sum(expected_same))
    count = len(same)
    within = float(np.sum(success * same)) / exposure if exposure else np.nan
    between = float(np.sum(success * ~same)) / (count-exposure) if count>exposure else np.nan
    return within,between,within-between


def gini(x):
    x = np.sort(np.asarray(x,float))
    return float(2*np.dot(np.arange(1,len(x)+1),x)/(len(x)*x.sum())-(len(x)+1)/len(x)) if x.sum() else 0.


def network_metrics(w, groups):
    n = len(groups)
    total = w.sum()
    mix = np.zeros((6,6))
    np.add.at(mix,(np.repeat(groups,n),np.tile(groups,n)),w.ravel())
    e = mix/total if total else mix
    expected = np.dot(e.sum(0),e.sum(1))
    q = np.trace(e)-expected
    adj = (w+w.T)>0
    unseen=set(range(n)); sizes=[]
    while unseen:
        root=unseen.pop(); stack=[root]; size=1
        while stack:
            j=stack.pop()
            neighbors=set(np.flatnonzero(adj[j])) & unseen
            unseen-=neighbors; stack.extend(neighbors); size+=len(neighbors)
        sizes.append(size)
    p = response_matrix(w)
    influence = np.ones(n)/n
    for _ in range(8):
        influence = influence @ p
    per_group = np.bincount(groups,weights=influence,minlength=6)
    membership=np.bincount(groups,minlength=6)/n
    return dict(assortativity=float(q/(1-expected)) if expected<1-1e-12 else np.nan,
                modularity=float(q),components=len(sizes),fragmentation=1-max(sizes)/n,
                excluded=float(np.mean(w.sum(0)==0)),influence_gini=gini(influence),
                influence_max=float(influence.max()),group_influence_gap=float(np.max(per_group-membership))), influence, mix


def response_matrix(w, receptivity=None):
    """Hypothetical copying dynamics; column response is NOT human leadership."""
    w=np.asarray(w,float).copy()
    if receptivity is not None:
        w *= np.exp(np.asarray(receptivity)[None,:])
    sums=w.sum(1)
    p=np.divide(w,sums[:,None],out=np.zeros_like(w),where=sums[:,None]>0)
    p[sums==0,np.flatnonzero(sums==0)]=1
    return .5*np.eye(len(w))+.5*p


def run(c, keep_events=False, stress_windows=None):
    # Extension: optional zero-based, half-open stress windows. The inherited
    # thirds are reporting bins only; they no longer determine a supplied schedule.
    if stress_windows is not None:
        previous_end = 0
        for start, end in stress_windows:
            if not (isinstance(start, int) and isinstance(end, int)
                    and previous_end <= start < end <= c.rounds):
                raise ValueError("Stress windows must be ordered, nonoverlapping integer intervals")
            previous_end = end
    n=c.n; phase_len=c.rounds//3; ii=np.arange(n)
    a,g,traits,profiles=initialize(c); g0=g.copy()
    rng=np.random.default_rng(np.random.SeedSequence([c.seed,n,991]))
    trust=np.zeros((n,n)); rigid=np.zeros(n)
    label_ids=(np.arange(6)+c.label_shift)%6
    trace=[]; phase_rows=[]; group_rows=[]; pair_rows=[]
    w=np.zeros((n,n)); window_w=np.zeros((n,n)); opportunities=np.zeros((6,6))
    phase_incoming=np.zeros(6); phase_alloc=np.zeros(6); member_rounds=np.zeros(6)
    contemporaneous_mix=np.zeros((6,6)); event_hash=hashlib.sha256()
    events=[]; group_history=[]; final_influence=None
    for t in range(c.rounds):
        phase=t//phase_len
        stressed=bool(c.stress and (phase==1 if stress_windows is None else any(start <= t < end for start,end in stress_windows)))
        scarcity=stressed and c.stress_kind in ("combined","scarcity")
        time_pressure=stressed and c.stress_kind in ("combined","time")
        limited=stressed and c.stress_kind in ("combined","information")
        pool=c.scarcity if scarcity else 1.
        # Draw fixed-size streams even when a mechanism is disabled. Matched
        # runs therefore use common exogenous draws without branch-dependent RNG.
        u=rng.random((n,n)); choice_u=rng.random(n); coop_u=rng.random(n)
        switch_u=rng.random(n); info_u=rng.random(n)
        explore_u=rng.random(n); global_u=rng.integers(0,n-1,n)
        # 'Mobility' is contact exploration, not coordinates or a physical phase.
        eligible=a.copy()
        global_j=global_u+(global_u>=ii)
        mobile=explore_u < traits[:,1]*(1-.7*rigid)
        eligible[ii[mobile],global_j[mobile]]=True
        k=2 if time_pressure else 6
        rank=np.where(eligible,u,2.)
        selected=np.argpartition(rank,k-1,axis=1)[:,:k]
        candidates=np.zeros((n,n),bool)
        candidates[ii[:,None],selected]=True
        candidates &= eligible
        counts=candidates.sum(1)
        same_all=g[:,None]==g[None,:]
        expected=(candidates*same_all).sum(1)/counts
        visible=info_u < (.30 if limited else 1.)
        remembered=trust * (c.memory*visible[:,None])
        semantic=(label_ids[g]==c.semantic_target).astype(float)
        if c.labels=="neutral": semantic[:]=0
        utility=1.6*(1+.5*rigid[:,None])*remembered+c.identity*same_all+c.semantic*semantic[None,:]
        if c.random_choice: utility[:]=0
        weights=np.where(candidates,np.exp(np.clip(utility,-10,10)),0.)
        probs=weights/weights.sum(1)[:,None]
        partners=(np.cumsum(probs,axis=1)<choice_u[:,None]).sum(1).clip(max=n-1)
        # Cooperation is a recipient decision on each request; the pool is then
        # shared, so total allocations cannot exceed n*pool. Scarcity affects
        # willingness through a declared cost heuristic, with NO group term.
        logit=1.1+traits[partners,2]+1.8*c.memory*trust[partners,ii]*visible[partners]+1.2*(pool-1)
        success=coop_u < sigmoid(logit)
        incoming=np.bincount(partners[success],minlength=n)
        amounts=success*pool/np.maximum(incoming[partners],1)
        same=g==g[partners]
        within,between,gap=opportunity_adjusted(same,success,expected)
        opportunity_matrix=np.zeros((6,6))
        for source in range(6):
            mask=g==source
            if mask.any():
                by_recipient=(candidates[mask]/counts[mask,None]).sum(0)
                opportunity_matrix[source]=np.bincount(g,weights=by_recipient,minlength=6)
        opportunities+=opportunity_matrix
        np.add.at(w,(ii,partners),success)
        np.add.at(window_w,(ii,partners),success)
        phase_incoming+=np.bincount(g[partners],minlength=6)
        phase_alloc+=np.bincount(g,weights=amounts,minlength=6)
        member_rounds+=np.bincount(g,minlength=6)
        np.add.at(contemporaneous_mix,(g,g[partners]),success)
        record=dict(round=t,phase=phase,cooperation=float(success.mean()),
                    choice_excess=float(same.mean()-expected.mean()),coop_gap=gap,
                    coop_within=within,coop_between=between,boundary_crossing=float((~same).mean()),
                    conditional_within=float(success[same].mean()) if same.any() else np.nan,
                    conditional_between=float(success[~same].mean()) if (~same).any() else np.nan,
                    allocation_within=float(amounts[same].sum()/expected.sum()) if expected.sum() else np.nan,
                    allocation_between=float(amounts[~same].sum()/(n-expected.sum())) if n>expected.sum() else np.nan,
                    rigid=float(rigid.mean()),switching=0.,window_excluded=np.nan,
                    pool_used=float(amounts.sum()/(n*pool)))
        trust *= c.decay
        if c.memory:
            trust[ii,partners] += .30*((2*success-1)-trust[ii,partners])
        if c.transitions:
            rigid += c.adaptation*((~success).astype(float)-rigid)
            switch=(switch_u < .06*(1-rigid)*(1-traits[:,0])) & success & ~same
            new_g=g[partners].copy()
            g[switch]=new_g[switch]
            record['switching']=float(switch.mean())
        if (t+1)%10==0:
            record['window_excluded']=float(np.mean(window_w.sum(0)==0)); window_w[:]=0
        trace.append(record)
        event=np.column_stack([partners,success,g]).astype(np.int16)
        event_hash.update(event.tobytes()); group_history.append(g.copy())
        if keep_events: events.append(event)
        if (t+1)%phase_len==0:
            # Group network uses ENDPOINT membership: differs intentionally from
            # contemporaneous group mixing below when affiliation can switch.
            metrics,final_influence,endpoint_mix=network_metrics(w,g)
            rows=trace[-phase_len:]
            for key in rows[0]:
                if key not in ("round","phase"):
                    vals=np.array([r[key] for r in rows]); finite=vals[np.isfinite(vals)]
                    metrics[key]=float(finite.mean()) if len(finite) else np.nan
            metrics.update(phase=phase,groups_remaining=int(len(np.unique(g))))
            phase_rows.append(metrics)
            for label in range(6):
                mask=g==label
                group_rows.append(dict(phase=phase,group=label,label_id=int(label_ids[label]),
                    members=int(mask.sum()),member_rounds=float(member_rounds[label]),
                    incoming_per_member=float(phase_incoming[label]/member_rounds[label]) if member_rounds[label] else np.nan,
                    received_per_member=float(phase_alloc[label]/member_rounds[label]) if member_rounds[label] else np.nan,
                    influence_share=float(final_influence[mask].sum()),mean_rigidity=float(rigid[mask].mean()) if mask.any() else np.nan))
            for source in range(6):
                for dest in range(6):
                    pair_rows.append(dict(phase=phase,source=source,dest=dest,opportunities=float(opportunities[source,dest]),cooperation=float(contemporaneous_mix[source,dest]),endpoint_cooperation=float(endpoint_mix[source,dest])))
            w[:]=0; opportunities[:]=0;phase_incoming[:]=0;phase_alloc[:]=0;member_rounds[:]=0;contemporaneous_mix[:]=0
    return dict(config=asdict(c),phases=phase_rows,trace=trace,groups=group_rows,pairs=pair_rows,
                digest=event_hash.hexdigest(),initial_groups=g0.tolist(),final_groups=g.tolist(),
                final_influence=final_influence.tolist(),events=np.array(events),group_history=np.array(group_history))
