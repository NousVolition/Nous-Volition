"""Batch 5: finite-time tests of three- and nine-state heteroclinic dynamics.

The nine-state matrix follows Voit & Meyer-Ortmanns (2018), equations 1-2.
All integrations use log coordinates, without a population floor or clipping.
Constant positive input is an explicit deterministic modification, not noise.
"""
import argparse
import json
import math
import random
import statistics
from pathlib import Path
from models import integrate

SOURCE = 'https://arxiv.org/abs/1806.11039'
PARAMETERS = dict(gamma=1.05, c=2.0, d=2.0, e=.2, f=.3, r=1.25)


def competition_matrix(n=9, gamma=1.05, c=2., d=2., e=.2, f=.3, r=1.25):
    """B includes gamma on the diagonal; x_i'=x_i(1-sum_j B_ij x_j)."""
    if n not in (3, 9) or not all(math.isfinite(v) and v > 0 for v in (gamma,c,d,e,f,r)):
        raise ValueError('Use 3 or 9 states and finite positive interaction rates')
    B=[]
    for i in range(n):
        row=[]
        for j in range(n):
            gi,ki=divmod(i,3);gj,kj=divmod(j,3)
            if i==j: value=gamma
            elif gi==gj: value=e if (ki-kj)%3==1 else c
            elif ki==kj: value=f if (gi-gj)%3==1 else d
            else: value=r
            row.append(value)
        B.append(tuple(row))
    return tuple(B)


def glv(B, drive=0.):
    if drive < 0 or not math.isfinite(drive):
        raise ValueError('Drive must be finite and nonnegative')
    return lambda t,x: tuple(xi*(1-sum(b*y for b,y in zip(row,x)))+drive
                             for xi,row in zip(x,B))


def jacobian(B,x):
    return tuple(tuple((1-sum(b*y for b,y in zip(row,x)) if i==j else 0)-x[i]*row[j]
                       for j in range(len(x))) for i,row in enumerate(B))


def axis_state(B,i):
    return tuple(1/B[i][i] if j==i else 0. for j in range(len(B)))


def axis_eigenvalues(B,i):
    return tuple(-1. if j==i else 1-B[j][i]/B[i][i] for j in range(len(B)))


def transition_edges(B):
    return tuple((i,j) for i in range(len(B)) for j,v in enumerate(axis_eigenvalues(B,i)) if v>0)


def log_trajectory(B,initial,duration=400.,step=.05,drive=0.):
    if len(initial)!=len(B) or any(x<=0 or not math.isfinite(x) for x in initial):
        raise ValueError('Log integration requires a finite strictly positive initial state')
    glv(B,drive)
    def rhs(t,z):
        x=tuple(math.exp(zi) for zi in z)
        # Refuse silent floating-point extinction or overflow; never impose a floor.
        if any(v==0 or not math.isfinite(v) for v in x):
            raise ArithmeticError('Activity outside floating-point range; shorten horizon')
        return tuple(1-sum(b*y for b,y in zip(row,x))+drive/xi for xi,row in zip(x,B))
    logs=integrate(rhs,tuple(math.log(x) for x in initial),duration,step)
    rows=[(row[0],*(math.exp(z) for z in row[1:])) for row in logs]
    return rows, min(min(row[1:]) for row in logs)


def visits(rows,threshold):
    """Completed above-threshold dominance intervals; boundary intervals censored.

    Threshold crossings are linearly interpolated between saved integration steps.
    Only the strongest component qualifies; no attribution when all are below it.
    """
    def label(row):
        i=max(range(len(row)-1),key=lambda j:row[j+1])
        return i if row[i+1]>=threshold else None
    active=label(rows[0]);start=rows[0][0] if active is not None else None
    left_censored=active is not None;out=[]
    for prev,row in zip(rows,rows[1:]):
        new=label(row)
        if new==active:continue
        if active is not None:
            a,b=prev[active+1],row[active+1]
            fraction=(threshold-a)/(b-a) if b!=a else 1.
            stop=prev[0]+(row[0]-prev[0])*min(1.,max(0.,fraction))
            out.append(dict(state=active+1,start=start,end=stop,dwell=stop-start,
                            left_censored=left_censored,right_censored=False))
        if new is not None:
            a,b=prev[new+1],row[new+1]
            fraction=(threshold-a)/(b-a) if b!=a else 1.
            start=prev[0]+(row[0]-prev[0])*min(1.,max(0.,fraction))
            left_censored=False
        active=new
    if active is not None:
        stop=rows[-1][0]
        out.append(dict(state=active+1,start=start,end=stop,dwell=stop-start,
                        left_censored=left_censored,right_censored=True))
    return out


def sequence_summary(events,n=9):
    seq=[]
    for event in events:
        if not seq or seq[-1]!=event['state']:seq.append(event['state'])
    counts=[[0]*n for _ in range(n)]
    for i,j in zip(seq,seq[1:]):counts[i-1][j-1]+=1
    within=between=other=0
    for i,j in zip(seq,seq[1:]):
        gi,ki=divmod(i-1,3);gj,kj=divmod(j-1,3)
        if gi==gj and (kj-ki)%3==1:within+=1
        elif ki==kj and (gj-gi)%3==1:between+=1
        else:other+=1
    return dict(sequence=seq,transition_counts=counts,within=within,between=between,
                unclassified=other,total=max(0,len(seq)-1),
                within_fraction=within/(within+between) if within+between else None)


def sampled(rows,spacing=.5):
    step=rows[1][0]-rows[0][0]
    stride=round(spacing/step)
    if stride<1 or not math.isclose(stride*step,spacing):raise ValueError('Invalid sampling interval')
    return rows[::stride]


def mean_interval(values):
    mean=statistics.mean(values)
    sem=statistics.stdev(values)/math.sqrt(len(values)) if len(values)>1 else 0.
    return dict(mean=mean,normal95=[mean-1.96*sem,mean+1.96*sem],n=len(values))


def three_state_results():
    B=competition_matrix(3,gamma=1.)
    initial=(.8,.12,.03)
    cases=[]
    for drive in (0.,1e-6,1e-4):
        rows,low=log_trajectory(B,initial,600.,.025,drive)
        events=visits(rows,.5)
        full=[v for v in events if not v['left_censored'] and not v['right_censored']]
        cases.append(dict(drive=drive,minimum_log_activity=low,events=events,
                          completed_dwells=[v['dwell'] for v in full],
                          sequence=sequence_summary(events,3)['sequence'],
                          trajectory=sampled(rows),
                          final_three_mean_dwell=statistics.mean(v['dwell'] for v in full[-3:])))
    fine,_=log_trajectory(B,initial,600.,.0125)
    coarse=cases[0]['trajectory'];fine_sample=sampled(fine)
    error=max(abs(x-y) for a,b in zip(coarse,fine_sample) for x,y in zip(a[1:],b[1:]))
    fine_visits=visits(fine,.5)
    timing=max(abs(a['start']-b['start']) for a,b in zip(cases[0]['events'],fine_visits))
    return dict(matrix=B,initial=initial,duration=600.,step=.025,
                axis_eigenvalues=axis_eigenvalues(B,0),
                contraction_to_expansion_ratio=1/.8,cases=cases,
                refinement=dict(fine_step=.0125,max_state_error=error,
                                same_sequence=sequence_summary(fine_visits,3)['sequence']==cases[0]['sequence'],
                                max_visit_entry_difference=timing))


def nine_state_results(rounds=16,seed=20261011):
    configs=[('within_preferred',.2,.3),('balanced',.25,.25),('between_preferred',.3,.2)]
    starts=[]
    for k in range(rounds):
        rng=random.Random(seed+k)
        starts.append(tuple(rng.uniform(.01,.1) for _ in range(9)))
    conditions=[]
    for name,e,f in configs:
        params=dict(PARAMETERS,e=e,f=f);B=competition_matrix(**params);runs=[]
        for k,initial in enumerate(starts):
            rows,low=log_trajectory(B,initial)
            events=visits(rows,.5/params['gamma']);summary=sequence_summary(events)
            item=dict(block=k,initial=initial,minimum_log_activity=low,**summary)
            if k==0:item.update(trajectory=sampled(rows),events=events)
            runs.append(item)
        totals={key:sum(x[key] for x in runs) for key in ('within','between','unclassified','total')}
        conditions.append(dict(name=name,parameters=params,matrix=B,edges=transition_edges(B),
                               axis_eigenvalues=axis_eigenvalues(B,0),runs=runs,totals=totals,
                               within_fraction_by_run=mean_interval([x['within_fraction'] for x in runs
                                                                   if x['within_fraction'] is not None])))
    diffs=[a['within_fraction']-b['within_fraction'] for a,b in zip(conditions[0]['runs'],conditions[2]['runs'])
           if a['within_fraction'] is not None and b['within_fraction'] is not None]
    refinements=[]
    for case in (conditions[0],conditions[2]):
        B=case['matrix'];fine,_=log_trajectory(B,starts[0],400.,.025)
        coarse=case['runs'][0];fine_sample=sampled(fine)
        seq=sequence_summary(visits(fine,.5/PARAMETERS['gamma']))
        refinements.append(dict(condition=case['name'],block=0,fine_step=.025,
            max_state_error=max(abs(x-y) for a,b in zip(coarse['trajectory'],fine_sample) for x,y in zip(a[1:],b[1:])),
            same_sequence=seq['sequence']==coarse['sequence']))
    return dict(seed=seed,rounds_per_condition=rounds,trajectory_runs=3*rounds,
                initial_distribution='independent uniform [0.01, 0.1], matched across conditions',
                duration=400.,step=.05,threshold=.5/PARAMETERS['gamma'],conditions=conditions,
                paired_within_preferred_minus_between_preferred=mean_interval(diffs),refinement=refinements)


def results():
    return dict(source=SOURCE,model='Generalized Lotka-Volterra activity dynamics',
                three_state=three_state_results(),nine_state=nine_state_results())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true');args=parser.parse_args()
    path=Path(__file__).with_name('heteroclinic_results.json');data=results()
    normalized=json.loads(json.dumps(data))
    if args.check:
        if normalized!=json.loads(path.read_text(encoding='utf-8')):
            raise SystemExit('FAIL: heteroclinic results differ.')
        print('PASS: three-state and 48 matched nine-state trajectories reproduced.')
    else:
        path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
        print('Saved three-state and 48 matched nine-state trajectories.')
