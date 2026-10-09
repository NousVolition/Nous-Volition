"""Exploratory six-mode switching and input-history diagnostic (not a brain fit).

Run from this study directory. Outputs are immutable; --out selects a fresh folder.
The vectorized RK4 solver uses constant inputs on each half-open step interval.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

SEEDS = list(range(30100, 30112)) + list(range(40100, 40112))
N = 6
DT = .02
HORIZON = 160.
SAMPLE = .2


def inhibition(kind='directed', weak=.7):
    """R[i,j] is suppression of receiver i by active sender j."""
    r = np.full((N, N), 1.6)
    np.fill_diagonal(r, 1.)
    for j in range(N):
        r[(j + 1) % N, j] = weak
    if kind == 'reverse':
        r = r.T
    elif kind == 'symmetric':
        r = (r + r.T) / 2
    elif kind == 'uncoupled':
        r = np.eye(N)
    return r


def build_tasks():
    tasks = []
    for k, seed in enumerate(SEEDS):
        rng = np.random.default_rng(seed)
        x0, x1 = rng.uniform(.01, .4, (2, N))
        target = k % N
        def add(family, condition, **kw):
            item = dict(seed=seed, split='discovery' if seed < 40000 else 'replication',
                        target=target, family=family, condition=condition,
                        kind='directed', weak=.7, epsilon=.001, gain=0., tau=30.,
                        x0=x0.tolist(), m0=np.zeros(N).tolist(), cue='none')
            item.update(kw)
            tasks.append(item)
        for kind in ('directed', 'reverse', 'symmetric', 'uncoupled'):
            add('sequence', kind, kind=kind)
        add('sequence', 'cue', cue='pulse')
        for weak in (.6, .7, .8):
            for epsilon in (.0001, .001, .01):
                add('sensitivity', f'w{weak}_e{epsilon}', weak=weak, epsilon=epsilon)
        for cue in ('none', 'clamp'):
            for initial, x in (('a', x0), ('b', x1)):
                add('forgetting', cue+'_'+initial, cue=cue, x0=x.tolist())
        # Prepare traces analytically using a 30-unit unit input followed by a
        # deliberate fast-state reset. This isolates stored input history.
        for gain in (0., .8):
            for history in ('a', 'b'):
                m = np.zeros(N)
                m[(target + (0 if history == 'a' else 3)) % N] = 1 - np.exp(-1)
                add('history', f'g{gain}_{history}', gain=gain, m0=m.tolist())
    return tasks


def integrate(tasks, dt=DT, horizon=HORIZON, sample=SAMPLE):
    """No clipping: negative or divergent trajectories are a solver failure."""
    r = np.array([inhibition(q['kind'], q['weak']) for q in tasks])
    gain = np.array([q['gain'] for q in tasks])[:, None]
    tau = np.array([q['tau'] for q in tasks])[:, None]
    epsilon = np.array([q['epsilon'] for q in tasks])[:, None]
    z = np.array([q['x0'] + q['m0'] for q in tasks], dtype=float)
    targets = np.array([q['target'] for q in tasks])
    pulse = np.array([q['cue'] == 'pulse' for q in tasks])
    clamp = np.array([q['cue'] == 'clamp' for q in tasks])
    steps, stride = round(horizon / dt), round(sample / dt)
    assert abs(stride*dt-sample) < 1e-12 and steps % stride == 0
    saved = np.empty((steps // stride + 1, len(tasks), 2*N))
    saved[0] = z
    minimum = float(z[:, :N].min())
    maximum = float(z[:, :N].max())
    def rhs(state, u):
        x, m = state[:, :N], state[:, N:]
        suppression = np.einsum('bij,bj->bi', r, x)
        return np.concatenate((x*(1+u+gain*m-suppression)+epsilon,
                               (u-m)/tau), axis=1)
    for j in range(steps):
        # The endpoint of a discontinuity belongs to the next interval. Keeping
        # u constant through RK stages avoids a spurious endpoint impulse.
        midpoint = (j+.5)*dt
        u = np.zeros((len(tasks), N))
        u[clamp, targets[clamp]] = 2.
        if 80 <= midpoint < 100:
            u[pulse, targets[pulse]] = 2.
        k1 = rhs(z, u)
        k2 = rhs(z+dt*k1/2, u)
        k3 = rhs(z+dt*k2/2, u)
        k4 = rhs(z+dt*k3, u)
        z += dt*(k1+2*k2+2*k3+k4)/6
        minimum = min(minimum, float(z[:, :N].min()))
        maximum = max(maximum, float(z[:, :N].max()))
        if (j+1) % stride == 0:
            saved[(j+1)//stride] = z
    return np.arange(len(saved))*sample, saved, dict(minimum=minimum, maximum=maximum)


def episodes(x, time, threshold=.7):
    """Dominance >= threshold of total activation, persisting >=1 time unit.

    Short intervals and transition gaps are discarded; adjacent equal winners
    after filtering are collapsed when scoring order. Boundary dwell is censored.
    """
    frac = x/x.sum(axis=1, keepdims=True)
    winner = frac.argmax(axis=1)
    winner[frac.max(axis=1) < threshold] = -1
    cuts = np.r_[0, np.flatnonzero(np.diff(winner))+1, len(winner)]
    records = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        duration = (b-a)*(time[1]-time[0])
        if winner[a] >= 0 and duration >= 1.-1e-10:
            records.append(dict(mode=int(winner[a]), start=float(time[a]),
                                duration=float(duration), censored=bool(a == 0 or b == len(winner))))
    sequence = []
    for rec in records:
        if not sequence or rec['mode'] != sequence[-1]:
            sequence.append(rec['mode'])
    delta = np.diff(sequence) % N
    dwell = [r['duration'] for r in records if not r['censored']]
    return dict(episodes=records, sequence=sequence, transitions=len(delta),
                forward_fraction=float(np.mean(delta == 1)) if len(delta) else None,
                reverse_fraction=float(np.mean(delta == N-1)) if len(delta) else None,
                visited=len(set(sequence)), dominant_fraction=float(np.mean(winner >= 0)),
                median_uncensored_dwell=float(np.median(dwell)) if dwell else None)


def interval(values, rng):
    x = np.array([v for v in values if v is not None], dtype=float)
    if not len(x):
        return dict(mean=None, lo=None, hi=None, seeds=0)
    means = x[rng.integers(0, len(x), size=(10000, len(x)))].mean(axis=1)
    lo, hi = np.quantile(means, [.025, .975])
    return dict(mean=float(x.mean()), lo=float(lo), hi=float(hi), seeds=len(x))


def analyze(tasks, time, states):
    metrics = []
    traces = {}
    rng = np.random.default_rng(912021)
    summaries = []
    for i, q in enumerate(tasks):
        x = states[:, i, :N]
        if q['family'] in ('sequence', 'sensitivity'):
            row = {k:q[k] for k in ('seed','split','family','condition','target')}
            row.update(episodes(x[time >= 20], time[time >= 20]))
            row['cue_target_fraction_90_100'] = float(np.mean(
                x[(time >= 90) & (time < 100), q['target']] /
                x[(time >= 90) & (time < 100)].sum(axis=1)))
            metrics.append(row)
    pairs = []
    for seed in SEEDS:
        ix = {(q['family'],q['condition']):i for i,q in enumerate(tasks) if q['seed'] == seed}
        split = 'discovery' if seed < 40000 else 'replication'
        for cue in ('none', 'clamp'):
            a,b = [states[:,ix['forgetting',cue+'_'+s],:N] for s in ('a','b')]
            distance = np.linalg.norm(a-b, axis=1)
            traces[seed,'forgetting',cue] = distance
            pairs.append(dict(seed=seed,split=split,family='forgetting',condition=cue,
                              initial_distance=float(distance[0]),distance_at_20=float(distance[round(20/SAMPLE)]),
                              distance_at_60=float(distance[round(60/SAMPLE)]),
                              ratio_at_20=float(distance[round(20/SAMPLE)]/distance[0])))
        for gain in (0., .8):
            a,b = [states[:,ix['history',f'g{gain}_'+s],:N] for s in ('a','b')]
            distance = np.linalg.norm(a-b, axis=1)
            traces[seed,'history',str(gain)] = distance
            take = time <= 40
            pairs.append(dict(seed=seed,split=split,family='history',condition=str(gain),
                              mean_distance_0_40=float(np.trapezoid(distance[take],time[take])/40),
                              distance_at_160=float(distance[-1])))
    for split in ('discovery','replication'):
        for condition in ('directed','reverse','symmetric','uncoupled','cue'):
            rows = [r for r in metrics if r['family']=='sequence' and r['condition']==condition and r['split']==split]
            for key in ('transitions','forward_fraction','reverse_fraction','visited','dominant_fraction','median_uncensored_dwell','cue_target_fraction_90_100'):
                summaries.append(dict(split=split,family='sequence',condition=condition,metric=key,**interval([r[key] for r in rows],rng)))
        for family,conditions,keys in [('forgetting',('none','clamp'),('distance_at_20','distance_at_60','ratio_at_20')),
                                        ('history',('0.0','0.8'),('mean_distance_0_40','distance_at_160'))]:
            for condition in conditions:
                for key in keys:
                    rows=[r for r in pairs if r['family']==family and r['condition']==condition and r['split']==split]
                    summaries.append(dict(split=split,family=family,condition=condition,metric=key,**interval([r[key] for r in rows],rng)))
        cue_diffs=[]
        for seed in (s for s in SEEDS if ('discovery' if s<40000 else 'replication')==split):
            a,b=[next(r for r in metrics if r['seed']==seed and r['family']=='sequence' and r['condition']==c) for c in ('cue','directed')]
            cue_diffs.append(a['cue_target_fraction_90_100']-b['cue_target_fraction_90_100'])
        summaries.append(dict(split=split,family='paired',condition='cue_minus_none',metric='target_fraction',**interval(cue_diffs,rng)))
    sensitivity=[]
    for weak in (.6,.7,.8):
        for epsilon in (.0001,.001,.01):
            rows=[r for r in metrics if r['split']=='replication' and r['family']=='sensitivity' and r['condition']==f'w{weak}_e{epsilon}']
            sensitivity.append(dict(weak=weak,epsilon=epsilon,transitions=interval([r['transitions'] for r in rows],rng),
                                    forward_fraction=interval([r['forward_fraction'] for r in rows],rng)))
    return dict(per_run=metrics,paired_runs=pairs,summaries=summaries,sensitivity=sensitivity),traces


def diagnostics(tasks,time,states):
    # Two seeds, each with all 22 conditions. Same physical output times.
    subset=[i for i,q in enumerate(tasks) if q['seed'] in (30100,40100)]
    _,fine,_=integrate([tasks[i] for i in subset],dt=DT/2)
    refinement=float(np.max(abs(states[:,subset]-fine)))
    # Whole-coordinate relabeling moves initial rates, traces, inputs, and R.
    # Our cyclic R is also checked directly against its index formula below.
    base=tasks[0];perm=np.array([3,0,5,1,4,2]);r=inhibition()
    x=np.array(base['x0']);m=np.arange(N)*.1;u=np.arange(N)*.03
    f=lambda xx,mm,uu,rr:xx*(1+uu+.8*mm-rr@xx)+.001
    permutation_error=float(np.max(abs(f(x[perm],m[perm],u[perm],r[np.ix_(perm,perm)])-f(x,m,u,r)[perm])))
    # Axial saddle eigenvalues of the zero-floor, zero-input, zero-trace skeleton.
    jac=np.diag(1-r[:,0]);jac[0]=-r[0];jac[0,0]=-1
    eigen=np.sort(np.linalg.eigvals(jac).real)
    unforced=[i for i,q in enumerate(tasks) if q['cue']=='none']
    m0=np.array([tasks[i]['m0'] for i in unforced])
    expected=m0[None,:,:]*np.exp(-time[:,None,None]/30)
    trace_error=float(np.max(abs(states[:,unforced,N:]-expected)))
    gain_zero=[]
    prefix=[]
    duplicate=[]
    for seed in SEEDS:
        ix={(q['family'],q['condition']):i for i,q in enumerate(tasks) if q['seed']==seed}
        gain_zero.append(np.array_equal(states[:,ix['history','g0.0_a'],:N],states[:,ix['history','g0.0_b'],:N]))
        prefix.append(np.array_equal(states[time<=80,ix['sequence','cue']],states[time<=80,ix['sequence','directed']]))
        duplicate.append(np.array_equal(states[:,ix['sequence','directed']],states[:,ix['sensitivity','w0.7_e0.001']]))
    checks=dict(finite=bool(np.isfinite(states).all()),nonnegative=bool(states.min()>=0),
                half_step_agreement=refinement<1e-5,permutation_equivariance=permutation_error<1e-14,
                analytic_trace=trace_error<1e-10,no_history_effect_without_feedback=all(gain_zero),
                no_anticipation_of_cue=all(prefix),duplicate_design_matches=all(duplicate),
                axial_saddle_eigenvalues=bool(np.allclose(eigen,[-1,-.6,-.6,-.6,-.6,.3])))
    return dict(checks=checks,maximum_half_step_difference=refinement,refined_runs=len(subset),
                permutation_error=permutation_error,trace_error=trace_error,axial_eigenvalues=eigen.tolist())


def plot(tasks,time,states,result,traces,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    ix={(q['family'],q['condition']):i for i,q in enumerate(tasks) if q['seed']==40100}
    fig,axs=plt.subplots(2,2,figsize=(12,7.5))
    for ax,condition,title in zip(axs.ravel(),('directed','reverse','symmetric','cue'),
            ('Directed connections: temporary dominance','Reversed connections: reversed sequence',
             'Symmetric connections: control','Same starting state, external cue at 80–100')):
        x=states[:,ix['sequence',condition],:N]
        for j in range(N):ax.plot(time,x[:,j],label=f'Mode {j+1}',lw=1.15)
        if condition=='cue':ax.axvspan(80,100,color='grey',alpha=.15)
        ax.set(title=title,xlabel='Model time',ylabel='Activation (arbitrary units)')
    fig.legend(*axs[0,0].get_legend_handles_labels(),ncol=6,fontsize=9,loc='lower center',bbox_to_anchor=(.5,-.015))
    fig.suptitle('Six interacting modes · one declared replication seed',fontsize=15)
    fig.tight_layout(rect=(0,.035,1,1))
    for ext in ('png','svg'):fig.savefig(out/f'transient_switching.{ext}',dpi=150)
    plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(13,4))
    seeds=SEEDS[12:]
    for condition in ('none','clamp'):
        values=np.array([traces[s,'forgetting',condition] for s in seeds])
        axs[0].plot(time,values.mean(axis=0),label='No cue' if condition=='none' else 'Sustained cue')
    axs[0].set_yscale('symlog',linthresh=1e-12)
    axs[0].set(title='Different starts, same history',xlabel='Time',ylabel='Mean Euclidean separation')
    axs[0].legend(fontsize=8)
    for condition in ('0.0','0.8'):
        values=np.array([traces[s,'history',condition] for s in seeds])
        axs[1].plot(time,values.mean(axis=0),label='Trace disconnected' if condition=='0.0' else 'Trace influences rates')
    axs[1].set(title='Same start, different histories',xlabel='Time',ylabel='Mean Euclidean separation')
    axs[1].legend(fontsize=8)
    a=np.array([q['transitions']['mean'] for q in result['sensitivity']]).reshape(3,3)
    im=axs[2].imshow(a,origin='lower',cmap='viridis',aspect='auto')
    axs[2].set(xticks=range(3),xticklabels=['0.0001','0.001','0.01'],yticks=range(3),yticklabels=['0.6','0.7','0.8'],
               xlabel='Activation floor',ylabel='Suppression of successor',title='Sensitivity: mean transition count')
    for i in range(3):
        for j in range(3):axs[2].text(j,i,f'{a[i,j]:.1f}',ha='center',va='center',color='white' if a[i,j]<a.mean() else 'black')
    fig.colorbar(im,ax=axs[2],shrink=.7)
    fig.tight_layout()
    for ext in ('png','svg'):fig.savefig(out/f'transient_memory.{ext}',dpi=150)
    plt.close(fig)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('.'));args=p.parse_args()
    data=args.out/'data';out=args.out/'analysis';data.mkdir(parents=True,exist_ok=True);out.mkdir(exist_ok=True)
    target=data/'transient_memory.json';protocol=data/'transient_memory_protocol.json'
    if target.exists() or protocol.exists():raise SystemExit('Refusing to overwrite the transient-memory design or results.')
    tasks=build_tasks()
    protocol.write_text(json.dumps(dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Exploratory screenshot-inspired illustrative model; not externally preregistered; no parameter fitting.',
        equation='xdot_i=x_i*(1+u_i+gain*m_i-sum_j R_ij*x_j)+epsilon; mdot_i=(u_i-m_i)/tau',
        initial_conditions='x_a and x_b independent uniform .01.. .4, each paired within seed; m=0 except prepared history contrast.',
        history='Unit input to target or opposite mode for 30 time units from m=0 gives m0=(1-exp(-1))*unit_vector. Then deliberately reset x to the same value; no future cue.',
        cue='Amplitude 2 at target, [80,100) for pulse or [0,160] for clamp; targets balanced modulo 6.',
        solver=dict(method='RK4 piecewise constant input',dt=DT,horizon=HORIZON,sample=SAMPLE),
        outcomes='Dominance fraction .7, episodes >=1 time unit after time20; score transitions after compressing repeats; boundary dwell censored. Pairwise Euclidean distances.',
        uncertainty='10000 percentile bootstrap samples of 12 whole seeds per split; descriptive, unadjusted; deterministic parameter sensitivity is not population uncertainty.',
        controls='reverse, symmetric and uncoupled R; zero memory feedback; no cue; exact cue prefix; coordinate permutation; half step all conditions for two seeds.',
        assumptions='Successor direction is explicitly encoded; positive input is growth drive, not a biophysical excitation population. No synaptic learning or neuron calibration.',
        tasks=tasks),indent=2))
    time,states,bounds=integrate(tasks)
    result,traces=analyze(tasks,time,states)
    result.update(diagnostics(tasks,time,states));result['bounds']=bounds
    result.update(runs=len(tasks),seeds=SEEDS,dt=DT,horizon=HORIZON,
                  all_passed=all(result['checks'].values()),
                  note='Observed dominance episodes at positive activation floor do not establish a heteroclinic channel or formal metastability.')
    target.write_text(json.dumps(result,indent=2))
    np.savez_compressed(data/'transient_memory_trajectories.npz',time=time,states=states)
    plot(tasks,time,states,result,traces,out)
    print(json.dumps({k:result[k] for k in ('runs','refined_runs','checks','maximum_half_step_difference','bounds')},indent=2))
    if not result['all_passed']:raise SystemExit('A numerical diagnostic failed; inspect saved results.')


if __name__=='__main__':main()
