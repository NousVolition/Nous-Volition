"""Sixteen coupled nine-state GLV units; deterministic source-equation checks.

Thakur & Meyer-Ortmanns (2022), Eq. 1, section 4.3 / Fig. 4g-h.
NumPy is required for the ensemble; no clipping or stochastic forcing is used.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from heteroclinic import competition_matrix

SOURCE='https://arxiv.org/html/2112.12642v2#S4.SS3'


def chain_field(state,forward=1.5,closure=.01,gamma_p=1.05,gamma_d=1.47):
    """State shape (..., units, 9); K[k,k-1]=forward, K[0,-1]=closure."""
    A=np.array(competition_matrix())
    np.fill_diagonal(A,0.)
    gamma=np.full((state.shape[-2],1),gamma_d);gamma[0]=gamma_p
    rate=state*(1-state@A.T-gamma*state)
    rate[...,1:,:]+=forward*(state[...,:-1,:]-state[...,1:,:])
    rate[...,0,:]+=closure*(state[...,-1,:]-state[...,0,:])
    return rate


def integrate_chain(initial,duration=2000.,step=.05,forward=1.5,closure=.01,sample_step=1.):
    if min(forward,closure)<0 or step<=0 or duration<=0:raise ValueError('Invalid time or coupling')
    x=np.asarray(initial,dtype=float).copy()
    if x.ndim!=3 or x.shape[-1]!=9 or np.any(x<=0):raise ValueError('Positive (runs, units, 9) input required')
    steps=round(duration/step);stride=round(sample_step/step)
    if stride<1 or not math.isclose(steps*step,duration) or not math.isclose(stride*step,sample_step):
        raise ValueError('Times must be whole numbers of steps')
    A=np.array(competition_matrix());np.fill_diagonal(A,0.)
    gamma=np.full((x.shape[-2],1),1.47);gamma[0]=1.05
    def rhs(y):
        if np.any(y<=0) or not np.all(np.isfinite(y)):
            raise ArithmeticError('Nonpositive or nonfinite RK stage; reduce step')
        dy=y*(1-y@A.T-gamma*y)
        dy[:,1:,:]+=forward*(y[:,:-1,:]-y[:,1:,:])
        dy[:,0,:]+=closure*(y[:,-1,:]-y[:,0,:])
        return dy
    saved=[x.copy()];minimum=float(np.min(x))
    for tick in range(steps):
        k1=rhs(x);k2=rhs(x+step*k1/2);k3=rhs(x+step*k2/2);k4=rhs(x+step*k3)
        x+=step*(k1+2*k2+2*k3+k4)/6
        minimum=min(minimum,float(np.min(x)))
        if (tick+1)%stride==0:saved.append(x.copy())
    if minimum<=0:raise ArithmeticError('Nonpositive activity; reduce step')
    return np.asarray(saved),minimum


def dominant_labels(data):
    shares=data/data.sum(axis=-1,keepdims=True)
    top=np.sort(shares,axis=-1)
    labels=np.argmax(shares,axis=-1)+1
    # Avoid mistaking numerical ties at coexistence for meaningful switching.
    clear=(top[...,-1]>=.25)&((top[...,-1]-top[...,-2])>=.01)
    return np.where(clear,labels,0)


def path_summary(labels):
    seq=[]
    for v in labels:
        v=int(v)
        if v and (not seq or seq[-1]!=v):seq.append(v)
    within=between=other=0
    for i,j in zip(seq,seq[1:]):
        gi,ki=divmod(i-1,3);gj,kj=divmod(j-1,3)
        if gi==gj and (kj-ki)%3==1:within+=1
        elif ki==kj and (gj-gi)%3==1:between+=1
        else:other+=1
    return dict(sequence=seq,within=within,between=between,unclassified=other,
                within_fraction=within/(within+between) if within+between else None)


def measurements(data,burn=1000):
    labels=dominant_labels(data);window=labels[burn:];pacemaker=window[:,0];valid=pacemaker>0
    agreement=[float(np.mean(window[valid,k]==pacemaker[valid])) if np.any(valid) else None
               for k in range(labels.shape[1])]
    clear=[float(np.mean(window[:,k]>0)) for k in range(labels.shape[1])]
    lag_scores=[]
    for lag in range(51):
        p=labels[burn:len(labels)-lag if lag else None,0]
        q=labels[burn+lag:,-1];mask=p>0
        lag_scores.append(float(np.mean(p[mask]==q[mask])) if np.any(mask) else 0.)
    best=int(np.argmax(lag_scores))
    normalized=data/data.sum(axis=-1,keepdims=True)
    return dict(pacemaker=path_summary(pacemaker),same_time_agreement_by_unit=agreement,
                clear_dominance_fraction_by_unit=clear,
                final_unit_best_lag=best,final_unit_lag_adjusted_agreement=lag_scores[best],
                normalized_mean_absolute_error_last_unit=float(np.mean(abs(normalized[burn:,-1]-normalized[burn:,0]))),
                minimum_activity=float(np.min(data)))


def results(seeds=64,duration=2000.,step=.05):
    initial=np.asarray([np.random.default_rng(20261012+k).uniform(.01,.1,(16,9)) for k in range(seeds)])
    data,low=integrate_chain(initial,duration,step)
    all_metrics=[dict(seed=20261012+k,**measurements(data[:,k])) for k in range(seeds)]
    fractions=[row['pacemaker']['within_fraction'] for row in all_metrics]
    available=[k for k,v in enumerate(fractions) if v is not None]
    representatives=[max(available,key=lambda k:fractions[k]),min(available,key=lambda k:fractions[k])]
    cases=[]
    for tag,k in zip(('within_path','between_path_candidate'),representatives):
        cases.append(dict(name=tag,initial=initial[k].tolist(),
                          labels=dominant_labels(data[:,k]).T.tolist(),
                          first_activity=data[:,k,0].tolist(),last_activity=data[:,k,-1].tolist(),
                          **all_metrics[k]))
    chosen=initial[representatives]
    fine,_=integrate_chain(chosen,duration,step/2)
    refinements=[]
    for j,k in enumerate(representatives):
        other=measurements(fine[:,j]);coarse=all_metrics[k]
        refinements.append(dict(seed=20261012+k,fine_step=step/2,
            max_state_error=float(np.max(abs(data[:,k]-fine[:,j]))),
            same_pacemaker_sequence=coarse['pacemaker']['sequence']==other['pacemaker']['sequence'],
            last_unit_agreement_difference=abs(coarse['same_time_agreement_by_unit'][-1]-other['same_time_agreement_by_unit'][-1])))
    # Matched initial state; cut all couplings or just the ring closure.
    controls=[]
    for name,forward,closure in (('uncoupled',0.,0.),('open_chain',1.5,0.)):
        rows,_=integrate_chain(initial[representatives[:1]],duration,step,forward,closure)
        controls.append(dict(name=name,forward=forward,closure=closure,
            labels=dominant_labels(rows[:,0]).T.tolist(),**measurements(rows[:,0])))
    return dict(source=SOURCE,units=16,items_per_unit=9,gamma_p=1.05,gamma_d=1.47,
        forward=1.5,closure=.01,noise=0.,duration=duration,step=step,sample_step=1.,burn=1000,
        seeds=seeds,initial_distribution='NumPy default_rng(seed), independent uniform [0.01,0.1]',
        clear_dominance_rule='largest share >= 0.25 and gap to second >= 0.01',
        minimum_activity=low,within_path_seeds=sum(v is not None and v>.5 for v in fractions),
        between_path_seeds=sum(v is not None and v<.5 for v in fractions),
        unresolved_seeds=sum(v is None or v==.5 for v in fractions),
        metrics=all_metrics,representatives=cases,refinements=refinements,controls=controls)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    args=parser.parse_args();data=results();path=Path(__file__).with_name('pacemaker_results.json')
    if args.check:
        if data!=json.loads(path.read_text(encoding='utf-8')):raise SystemExit('FAIL: pacemaker results differ')
        print('PASS: 64 pacemaker starts, controls, and step refinements reproduced.')
    else:
        path.write_text(json.dumps(data,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
        print('Saved 64 pacemaker starts, controls, and step refinements.')
