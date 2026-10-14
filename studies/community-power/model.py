"""Synthetic community allocation benchmark inspired by an uploaded passage.

This is an optimization comparison, not a fitted model of human behavior.
Material words are display labels. No fluid or chemical force is used.
"""
from dataclasses import dataclass,replace
import numpy as np
from scipy.optimize import linprog

LABELS=('Water','Fog','Mist','Gas','Smoke','Clay','Ice')
@dataclass
class Community:
    skills:np.ndarray
    demand:np.ndarray
    capacity:np.ndarray
    requested:np.ndarray
    connected:np.ndarray
    partitioned:np.ndarray
    effort_cost:np.ndarray
    flow_cost:np.ndarray
    labels:tuple=LABELS

def make_community(seed=31000,heterogeneity=.55,scarcity=1.):
    """Seven people, two complementary services. All numerical choices assumed.
    Productivity row mean is preserved as skill differentiation varies.
    Two contact graphs have nine undirected edges each, plus self-service.
    """
    rng=np.random.default_rng(seed);n=7
    productivity=rng.uniform(.8,1.2,n)
    preference=rng.choice([-1.,1.],n)
    delta=heterogeneity*preference
    skills=productivity[:,None]*(1+np.column_stack([delta,-delta]))
    demand=.35*scarcity*rng.uniform(.8,1.2,(n,2))
    capacity=np.ones(n);requested=rng.uniform(.5,.8,n)
    connected=np.eye(n,dtype=bool)
    for i in range(n):connected[i,(i+1)%n]=connected[(i+1)%n,i]=True
    pairs=np.array([(i,j) for i in range(n) for j in range(i+1,n) if not connected[i,j]])
    for i,j in pairs[rng.choice(len(pairs),2,replace=False)]:connected[i,j]=connected[j,i]=True
    group=np.zeros(n,int);group[rng.permutation(n)[:3]]=1
    partitioned=(group[:,None]==group[None,:])
    # Tie-breaking costs are fixed to people/transactions, never their names.
    effort_cost=1+.01*rng.uniform(size=(n,2))
    flow_cost=.01+.001*rng.uniform(size=(n,n,2))
    return Community(skills,demand,capacity,requested,connected,partitioned,effort_cost,flow_cost)

POLICIES={
 'independent':dict(graph='self'),
 'reciprocal':dict(graph='connected'),
 'partitioned':dict(graph='partitioned'),
 'priority_hierarchy':dict(graph='connected',priority=3.),
 'override_budgets':dict(graph='connected',respect=False),
 'hierarchy_and_override':dict(graph='connected',priority=3.,respect=False),
 'recording_only':dict(graph='connected',recording=True),
 'costly_assessment':dict(graph='connected',assessment=.1),
}

def solve(c,graph='connected',respect=True,priority=1.,leader=0,assessment=0.,recording=False,tolerance=1e-9):
    """Ideal allocation oracle: stage 1 weighted needs, stage 2 least cost.

    All policies use the same optimizer and perfect skill/need information.
    No claim of a decentralized negotiation algorithm or observed surveillance
    effect follows. Assessment here consumes time only; recording is inert.
    """
    n=len(c.capacity);tasks=2
    if not 0<=assessment<1 or priority<=0:raise ValueError('Invalid policy parameter')
    if np.any(c.skills<=0) or np.any(c.demand<=0):raise ValueError('Positive skills and needs required')
    if np.any(c.requested<0) or np.any(c.requested>c.capacity):raise ValueError('Invalid requested time budget')
    if graph=='self':adj=np.eye(n,dtype=bool)
    elif graph=='complete':adj=np.ones((n,n),bool)
    elif graph=='connected':adj=c.connected
    elif graph=='partitioned':adj=c.partitioned
    else:raise ValueError(graph)
    e=np.arange(n*tasks).reshape(n,tasks)
    f=np.arange(e.size,e.size+n*n*tasks).reshape(n,n,tasks)
    z=np.arange(e.size+f.size,e.size+f.size+n);nv=z[-1]+1
    A=[];b=[]
    def inequality(items,rhs):
        row=np.zeros(nv)
        for ix,value in items:row[np.asarray(ix).ravel()]+=value
        A.append(row);b.append(rhs)
    for i in range(n):
        for t in range(tasks):inequality([(f[i,:,t],1),(e[i,t],-c.skills[i,t])],0)
        limit=c.requested[i] if respect else c.capacity[i]
        # Assumed assessment time consumes the same budget as assistance.
        inequality([(e[i,:],1)],max(0.,limit-assessment*c.capacity[i]))
    for j in range(n):
        for t in range(tasks):inequality([(z[j],c.demand[j,t]),(f[:,j,t],-1)],0)
    bounds=[(0,None)]*e.size+[(0,None if adj[i,j] else 0) for i in range(n) for j in range(n) for t in range(tasks)]+[(0,1)]*n
    weights=np.ones(n);weights[leader]=priority
    objective=np.zeros(nv);objective[z]=-weights
    options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9}
    first=linprog(objective,A_ub=np.array(A),b_ub=np.array(b),bounds=bounds,method='highs',options=options)
    if not first.success:raise RuntimeError(first.message)
    optimal=-first.fun
    A.append(objective);b.append(-optimal+tolerance)
    cost=np.zeros(nv);cost[e.ravel()]=c.effort_cost.ravel();cost[f.ravel()]=c.flow_cost.ravel()
    second=linprog(cost,A_ub=np.array(A),b_ub=np.array(b),bounds=bounds,method='highs',options=options)
    if not second.success:raise RuntimeError(second.message)
    x=second.x;effort=x[e];flow=x[f];met=x[z]
    work=effort.sum(1);excess=np.maximum(work+assessment*c.capacity-c.requested,0)
    supply=c.skills*effort;used=flow.sum(1);received=flow.sum(0)
    residual=max(float(np.max(np.array(A)@x-np.array(b))),float(np.max(-x)),0.)
    scalar=dict(mean_needs_met=float(met.mean()),minimum_needs_met=float(met.min()),
        leader_needs_met=float(met[leader]),others_needs_met=float(np.delete(met,leader).mean()),
        total_useful_work=float(work.sum()),total_assessment_time=float(assessment*c.capacity.sum()),
        total_excess_over_requests=float(excess.sum()),fraction_members_over_request=float(np.mean(excess>1e-7)),
        needs_spread=float(met.max()-met.min()),weighted_objective=float(weights@met),optimal_weighted_objective=float(optimal),
        optimality_loss=float(optimal-weights@met),constraint_residual=residual,
        max_supply_violation=float(max(0.,np.max(used-supply))),
        max_need_violation=float(max(0.,np.max(c.demand*met[:,None]-received))),
        unmet_mean=float(1-met.mean()))
    return dict(metrics=scalar,effort=effort,flow=flow,met=met,excess=excess,supply=supply,received=received,
                weights=weights,allowed=adj,assessment_time=np.full(n,assessment))

def permute(c,order):
    o=np.asarray(order)
    return Community(c.skills[o],c.demand[o],c.capacity[o],c.requested[o],c.connected[np.ix_(o,o)],
        c.partitioned[np.ix_(o,o)],c.effort_cost[o],c.flow_cost[o][:,o],tuple(c.labels[i] for i in o))
