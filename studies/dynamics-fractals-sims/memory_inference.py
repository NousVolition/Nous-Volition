"""Local saddle memory diagnostic and an identifiable GLV inference baseline.

These are explicit derived controls, not reproductions of a noisy global network,
delay learning rule, or the adaptive template algorithm in the supplied review.
"""
import argparse
import json
import math
import random
from pathlib import Path
import numpy as np
from heteroclinic import competition_matrix,log_trajectory,glv,transition_edges


def saddle_exit(x_in,y_in,expanding=1.,contracting=.5,section=1.):
    if not 0<x_in<section or expanding<=0 or contracting<=0:raise ValueError('Invalid saddle sections or eigenvalues')
    time=math.log(section/x_in)/expanding
    return time,y_in*(x_in/section)**(contracting/expanding)


def branch_probability_gap(epsilon,ratios):
    """Exact conditional gap for the declared exit-map plus Gaussian readout."""
    signal_over_noise=epsilon**(sum(ratios)-1)
    return math.erf(signal_over_noise/math.sqrt(2))


def local_memory_results(samples=4096,seed=20261013):
    configs=[('one saddle, positive saddle quantity',[.5]),
             ('one saddle, negative saddle quantity',[1.5]),
             ('two saddles, retained offset',[.4,.4]),
             ('two saddles, erased offset',[.4,.9])]
    rows=[]
    for name,ratios in configs:
        for epsilon in (.1,.03,.01,.003,.001):
            rng=random.Random(seed)
            noises=[rng.gauss(0,1) for _ in range(samples)]
            amplitude=epsilon**sum(ratios)
            plus=sum(amplitude+epsilon*z>0 for z in noises)/samples
            minus=sum(-amplitude+epsilon*z>0 for z in noises)/samples
            gap=branch_probability_gap(epsilon,ratios)
            p=(1+gap)/2
            entropy=-sum(q*math.log2(q) for q in (p,1-p) if q>0)
            rows.append(dict(name=name,ratios=ratios,epsilon=epsilon,exit_offset=amplitude,
                offset_relative_to_noise=amplitude/epsilon,p_plus_given_history_plus=plus,
                p_plus_given_history_minus=minus,measured_conditional_gap=plus-minus,
                exact_conditional_gap=gap,exact_mutual_information_bits=1-entropy))
    # Resetting the incoming history coordinate makes both histories use the same readout.
    return dict(seed=seed,readouts_per_history_per_case=samples,configurations=rows,
                markov_control_conditional_gap=0.,
                model='x grows linearly, y contracts linearly; x resets to epsilon at each saddle; Gaussian noise added only at final branch readout')


def infer_matrix(trajectories,step=.02,log_noise=0.,seed=20261014):
    rng=np.random.default_rng(seed);design=[];targets=[]
    for rows in trajectories:
        x=np.asarray(rows)[:,1:]
        logs=np.log(x)
        if log_noise:logs+=rng.normal(0,log_noise,logs.shape)
        # Derivatives estimated from observations; the true RHS is not a regression input.
        index=np.arange(1,len(x)-1,10)
        design.append(np.exp(logs[index]))
        targets.append(1-(logs[index+1]-logs[index-1])/(2*step))
    X=np.concatenate(design);Y=np.concatenate(targets)
    coefficients,residuals,rank,singular=np.linalg.lstsq(X,Y,rcond=None)
    return coefficients.T,dict(rank=int(rank),observations=len(X),
        condition_number=float(singular[0]/singular[-1]) if rank==X.shape[1] else None,
        root_mean_square_residual=float(np.sqrt(np.mean((X@coefficients-Y)**2))))


def inference_results():
    B=np.asarray(competition_matrix());training=[];step=.02
    for seed in range(20261014,20261020):
        rng=np.random.default_rng(seed);initial=rng.uniform(.01,.1,9)
        rows,_=log_trajectory(B,initial,40.,step)
        training.append(rows)
    rng=np.random.default_rng(20262014);heldout=rng.uniform(.01,.1,9)
    reference,_=log_trajectory(B,heldout,100.,step)
    cases=[]
    for noise in (0.,1e-4):
        fitted,diagnostics=infer_matrix(training,step,noise)
        predicted,_=log_trajectory(fitted,heldout,100.,step)
        cases.append(dict(log_measurement_noise_sd=noise,fitted_matrix=fitted.tolist(),**diagnostics,
            maximum_parameter_error=float(np.max(abs(fitted-B))),
            exact_transition_edges_recovered=transition_edges(fitted)==transition_edges(B),
            heldout_max_state_error=max(abs(a-b) for x,y in zip(reference,predicted) for a,b in zip(x[1:],y[1:]))))
    C=np.asarray(competition_matrix(e=.3,f=.2));coexist=np.full(9,1/sum(B[0]))
    return dict(method='least-squares baseline from complete activity observations and finite-difference log derivatives',
        training_seeds=list(range(20261014,20261020)),training_duration=40.,step=step,
        heldout_seed=20262014,heldout_initial=heldout.tolist(),heldout_duration=100.,
        true_matrix=B.tolist(),cases=cases,
        coexistence_counterexample=dict(design_rank=int(np.linalg.matrix_rank(np.tile(coexist,(100,1)))),
            different_matrices_same_observation=bool(not np.array_equal(B,C) and np.allclose(B@coexist,C@coexist)),
            vector_field_residual=max(abs(v) for v in glv(C)(0,coexist))))


def results():return dict(memory=local_memory_results(),inference=inference_results())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    args=parser.parse_args();data=results();path=Path(__file__).with_name('memory_inference_results.json')
    if args.check:
        if data!=json.loads(path.read_text(encoding='utf-8')):raise SystemExit('FAIL: memory/inference results differ')
        print('PASS: local memory diagnostics and held-out inference checks reproduced.')
    else:
        path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
        print('Saved local memory diagnostics and held-out inference checks.')
