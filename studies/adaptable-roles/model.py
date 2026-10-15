"""Synthetic coordination work, expectations and contestable roles.

All time is normalized per person per round. Material names are inert labels.
This is a discrete process, not fluid dynamics or a fitted theory of people.
"""
from dataclasses import dataclass
import numpy as np

LABELS = ('Water', 'Fog', 'Mist', 'Gas', 'Smoke', 'Clay', 'Ice')
POLICIES = ('shared', 'assigned', 'remove_label', 'target_stops',
            'target_stops_handoff', 'share_after', 'all_stop', 'none')

@dataclass
class Community:
    skill: np.ndarray
    willing: np.ndarray
    planned: np.ndarray
    demand: np.ndarray
    labels: tuple = LABELS

def make_community(seed, load=1., rounds=60):
    rng = np.random.default_rng(seed)
    return Community(rng.uniform(.8, 1.2, 7), rng.uniform(.45, .65, 7),
        rng.uniform(.5, .65, (rounds, 7)), load*rng.uniform(.85, 1.15, rounds))

def balanced_work(amount, skill, budget, used=None, overhead=0., tolerance=1e-11):
    """Equalize total used/budget among participants accepting extra work.

    Exact piecewise-linear water filling. Returned time includes handoff cost;
    output/(1/skill + overhead) is the corresponding productivity relation.
    `tolerance` only resolves tiny floating-point breakpoint residuals.
    """
    if amount < 0 or overhead < 0 or tolerance <= 0:
        raise ValueError('Invalid work parameters')
    skill = np.asarray(skill, float); budget = np.asarray(budget, float)
    used = np.zeros_like(budget) if used is None else np.asarray(used, float)
    if np.any(skill <= 0) or np.any(budget < 0) or np.any(used < -tolerance) or np.any(used > budget+tolerance):
        raise ValueError('Invalid capacities')
    productivity = 1/(1/skill+overhead)
    remaining = np.maximum(budget-used, 0)
    target = min(amount, float(remaining@productivity))
    if target == 0: return np.zeros_like(budget)
    ratio = np.divide(used, budget, out=np.ones_like(budget), where=budget>0)
    levels = np.unique(np.r_[0., ratio, 1.])
    for low, high in zip(levels[:-1], levels[1:]):
        at_low = np.maximum(low*budget-used, 0)
        value = float(at_low@productivity)
        active = (budget>0) & (ratio <= low)
        slope = float((budget*productivity)[active].sum())
        if slope > 0 and target <= value+(high-low)*slope+tolerance:
            level = np.clip(low+(target-value)/slope, low, high)
            return np.minimum(remaining, np.maximum(level*budget-used, 0))
    return remaining

def run(c, target=0, policy='assigned', switch=30, bias=.75, memory=.25,
        learning=.10, gain=.6, handoff_cost=.05, tolerance=1e-11):
    if policy not in POLICIES or not 0 <= target < len(c.skill): raise ValueError('Unknown policy/member')
    if not 0 <= bias <= 1 or not 0 <= memory <= 1 or min(learning,gain,handoff_cost)<0:
        raise ValueError('Invalid dynamics')
    n=len(c.skill); rounds=len(c.demand)
    if c.planned.shape != (rounds,n) or len(c.willing)!=n or np.any(c.skill<=0) or np.any(c.willing<0) or np.any(c.willing>1) or np.any(c.planned<0) or np.any(c.planned>1) or np.any(c.demand<0):
        raise ValueError('Invalid community')
    if not 0 <= switch <= rounds: raise ValueError('Invalid switch')
    belief=np.full(n,1/n); practice=np.zeros(n)
    keys=('request','done','work','overhead','planned_done','slack','skill','belief','budget')
    hist={k:np.zeros((rounds,n)) for k in keys}
    unmet=np.zeros(rounds)
    for t in range(rounds):
        s=c.skill+gain*(-np.expm1(-learning*practice))
        budget=c.willing.copy()
        post=t>=switch
        shared=policy=='shared' or (policy=='share_after' and post)
        stop_target=policy in ('target_stops','target_stops_handoff') and post
        stop_all=policy=='none' or (policy=='all_stop' and post)
        if stop_target: budget[target]=0
        if stop_all: budget[:]=0
        if policy=='share_after' and t==switch: belief[:]=1/n
        role_active=not shared and not (policy=='remove_label' and post) and policy!='none'
        shares=belief.copy()
        if role_active:
            shares*=(1-bias);shares[target]+=bias
        if policy=='none': shares[:]=1/n
        if shared:
            # Scheduling is revised before assigning work. No handoff overhead.
            work=balanced_work(c.demand[t],s,budget,tolerance=tolerance)
            done=s*work; extra=np.zeros(n)
            request=done.copy()
            # If capacity is insufficient, distribute unfilled requests equally.
            request+=(c.demand[t]-done.sum())/n
        else:
            request=c.demand[t]*shares
            done=np.minimum(request,s*budget)
            work=done/s;extra=np.zeros(n)
            if policy=='target_stops_handoff' and post:
                extra_time=balanced_work(max(0.,c.demand[t]-done.sum()),s,budget,
                                        used=work,overhead=handoff_cost,tolerance=tolerance)
                extra_done=extra_time/(1/s+handoff_cost)
                extra=extra_done*handoff_cost
                done+=extra_done;work+=extra_time
        own=np.minimum(c.planned[t],1-work)
        for k,v in dict(request=request,done=done,work=work,overhead=extra,
                       planned_done=own,slack=1-work-own,skill=s,belief=belief,budget=budget).items():
            hist[k][t]=v
        unmet[t]=max(0.,c.demand[t]-done.sum())
        practice+=work-extra
        if done.sum()>0: belief=(1-memory)*belief+memory*done/done.sum()
    hist.update(unmet=unmet,demand=c.demand.copy(),planned=c.planned.copy(),
                final_skill=c.skill+gain*(-np.expm1(-learning*practice)),final_belief=belief)
    return hist

def audit(h):
    """Whole-path accounting, in normalized units."""
    return {
      'demand_residual':float(np.max(abs(h['done'].sum(1)+h['unmet']-h['demand']))),
      'time_residual':float(np.max(abs(h['work']+h['planned_done']+h['slack']-1))),
      'production_residual':float(np.max(abs(h['done']-h['skill']*(h['work']-h['overhead'])))),
      'budget_excess':float(max(0.,np.max(h['work']-h['budget']))),
      'negative_inventory':float(max(0.,-min(h[k].min() for k in ('done','work','overhead','planned_done','slack','unmet')))),
      'belief_residual':float(np.max(abs(h['belief'].sum(1)-1)))
    }

def metrics(h,target,switch=30):
    q=slice(switch,None); others=np.arange(h['work'].shape[1])!=target
    demand=h['demand'][q].sum();done=h['done'][q].sum()
    return dict(coordination_met=float(done/demand) if demand else 1.,
      planned_met=float(h['planned_done'][q].sum()/h['planned'][q].sum()),
      target_work=float(h['work'][q,target].mean()),
      others_work=float(h['work'][q][:,others].mean()),
      target_plans_met=float(h['planned_done'][q,target].sum()/h['planned'][q,target].sum()),
      target_request_share=float(h['request'][q,target].sum()/demand) if demand else 0.,
      target_output_share=float(h['done'][q,target].sum()/done) if done else 0.,
      handoff_time=float(h['overhead'][q].sum(1).mean()),
      target_final_skill=float(h['final_skill'][target]))
