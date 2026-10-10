"""Damping-aware Verlet versus RK4, crossed with bias order and state reset.

Exploratory follow-up to the separately retained method pilot. No stochastic
forcing is added: randomization changes the order of prescribed current values.
Run from the study folder; --out selects a fresh output folder.
"""
import argparse
import hashlib
import json
import time as walltime
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

GRID = np.array([0., .25, .5, .7, .8, .9, .95, 1., 1.025, 1.05, 1.1, 1.25, 1.5])
SEEDS = list(range(51100, 51112)) + list(range(61100, 61112))
BETAS = (.2, 2., 10.)
OBSERVE = 80.
MOVING = .05


def step(z, h, bias, beta, method, friction=1., sine_strength=1.):
    """States are (unwrapped phase, same-time velocity); arrays are vectorized.

    split_verlet is deterministic BAOAB: kick, drift, exact drag, drift, kick.
    It reduces to velocity Verlet when friction=0, and is second order.
    Signed h is supported for conservative reversibility tests only.
    """
    if method == 'split_verlet':
        phi, v = z
        v = v + h*(bias-sine_strength*np.sin(phi))/(2*beta)
        phi = phi + h*v/2
        v = v*np.exp(-friction*h/beta)
        phi = phi + h*v/2
        v = v + h*(bias-sine_strength*np.sin(phi))/(2*beta)
        return np.array([phi, v])
    if method != 'rk4':
        raise ValueError('Unknown integrator')
    def f(x):
        return np.array([x[1], (bias-friction*x[1]-sine_strength*np.sin(x[0]))/beta])
    a=f(z); b=f(z+h*a/2); c=f(z+h*b/2); d=f(z+h*c)
    return z+h*(a+2*b+2*c+d)/6


def segment(z, bias, beta, method, h, settle, observe=OBSERVE):
    if h <= 0 or np.any(np.asarray(beta) <= 0) or settle < 0 or observe <= 0:
        raise ValueError('Require positive step, inertia and observation time; nonnegative settling.')
    nset=round(settle/h); nobs=round(observe/h)
    if abs(nset*h-settle)>1e-10 or abs(nobs*h-observe)>1e-10 or nobs % 2:
        raise ValueError('Windows must be whole steps, with an even observation-step count.')
    for _ in range(nset): z=step(z,h,bias,beta,method)
    before=z[0].copy()
    for k in range(nobs):
        z=step(z,h,bias,beta,method)
        if k+1 == nobs//2: middle=z[0].copy()
    metrics=np.stack(((z[0]-before)/observe, (middle-before)/(observe/2),
                      (z[0]-middle)/(observe/2)),axis=-1)
    # Subtract whole cycles only after measuring net phase change.
    z[0]=(z[0]+np.pi)%(2*np.pi)-np.pi
    return z,metrics


def make_orders():
    n=len(GRID)
    alternating=[]
    for j in range((n+1)//2):
        alternating.append(j)
        if n-1-j != j: alternating.append(n-1-j)
    orders=[dict(name='up',seed=None,split='fixed',indices=list(range(n))),
            dict(name='down',seed=None,split='fixed',indices=list(range(n-1,-1,-1))),
            dict(name='alternate_low',seed=None,split='fixed',indices=alternating),
            dict(name='alternate_high',seed=None,split='fixed',indices=[n-1-j for j in alternating])]
    for seed in SEEDS:
        indices=np.random.default_rng(seed).permutation(n).tolist()
        for reverse in (False,True):
            orders.append(dict(name=f'{seed}_'+('reverse' if reverse else 'forward'),seed=seed,
                               split='discovery' if seed < 60000 else 'replication',
                               indices=indices[::-1] if reverse else indices))
    return orders


def bootstrap(values,rng):
    """One value per independent permutation seed; each includes its reversal."""
    x=np.asarray(values,float)
    means=x[rng.integers(0,len(x),size=(10000,len(x)))].mean(axis=1)
    lo,hi=np.quantile(means,[.025,.975])
    return dict(mean=float(x.mean()),lo=float(lo),hi=float(hi),seeds=len(x))


def get_rows(tasks,beta,reset,split=None,name=None,seed=None):
    return [i for i,q in enumerate(tasks) if q['beta']==beta and q['reset']==reset
            and (split is None or q['split']==split) and (name is None or q['order']==name)
            and (seed is None or q['seed']==seed)]


def analyze(configs,tasks,metrics,fixed_cases,fixed_values,reference):
    rng=np.random.default_rng(819302)
    summaries=[]; fixed_orders=[]; contrasts=[]
    def ci(values):return bootstrap(values,rng)
    for c,config in enumerate(configs):
        for beta in BETAS:
            for reset in (True,False):
                for split in ('discovery','replication'):
                    seeds=SEEDS[:12] if split=='discovery' else SEEDS[12:]
                    v=np.array([metrics[c,get_rows(tasks,beta,reset,seed=s),:,0].mean(axis=0) for s in seeds])
                    moving=np.array([(metrics[c,get_rows(tasks,beta,reset,seed=s),:,0]>MOVING).mean(axis=0) for s in seeds])
                    instability=np.array([abs(metrics[c,get_rows(tasks,beta,reset,seed=s),:,2]-metrics[c,get_rows(tasks,beta,reset,seed=s),:,1]).mean(axis=0) for s in seeds])
                    for j,bias in enumerate(GRID):
                        summaries.append(dict(config=c,beta=beta,reset=reset,split=split,bias=float(bias),
                                              voltage=ci(v[:,j]),moving_fraction=ci(moving[:,j]),
                                              half_window_change=ci(instability[:,j])))
                for name in ('up','down','alternate_low','alternate_high'):
                    row=get_rows(tasks,beta,reset,name=name)[0]
                    for j,bias in enumerate(GRID):
                        fixed_orders.append(dict(config=c,beta=beta,reset=reset,order=name,bias=float(bias),
                                                 voltage=float(metrics[c,row,j,0]),
                                                 half_window_change=float(abs(metrics[c,row,j,2]-metrics[c,row,j,1]))))
    for c,config in enumerate(configs):
        # Paired effects vary exactly one numerical factor across whole paths.
        other_configs=[]
        if config['method']=='split_verlet':
            other_configs.append(('solver',dict(config,method='rk4')))
        if config['dt']==.02:
            other_configs.append(('step',dict(config,dt=.04)))
        if config['settle']==320:
            other_configs.append(('settling',dict(config,settle=160)))
        for name,other in other_configs:
            d=configs.index(other)
            for beta in BETAS:
                for reset in (True,False):
                    for split,seeds in (('discovery',SEEDS[:12]),('replication',SEEDS[12:])):
                        paired=np.array([(metrics[c,get_rows(tasks,beta,reset,seed=s),:,0]-metrics[d,get_rows(tasks,beta,reset,seed=s),:,0]).mean(axis=0) for s in seeds])
                        for j,bias in enumerate(GRID):
                            contrasts.append(dict(kind=name,config=c,reference_config=d,beta=beta,reset=reset,
                                                  split=split,bias=float(bias),voltage_difference=ci(paired[:,j])))
    errors=[]
    for c,config in enumerate(configs):
        ref=reference[(160,320).index(config['settle'])]
        delta=abs(fixed_values[c,:,0]-ref[:,0]);worst=int(delta.argmax())
        errors.append(dict(config=c,maximum_absolute_error=float(delta.max()),
                           median_absolute_error=float(np.median(delta)),worst_case=fixed_cases[worst],
                           worst_voltage=float(fixed_values[c,worst,0]),reference_voltage=float(ref[worst,0])))
    return dict(random_orders=summaries,fixed_orders=fixed_orders,paired_contrasts=contrasts,
                fixed_start_errors=errors)


def validate(configs,tasks,metrics,fixed_values,reference,orders):
    reset_spread=0.
    for c in range(len(configs)):
        for beta in BETAS:
            rows=get_rows(tasks,beta,True)
            reset_spread=max(reset_spread,float(np.ptp(metrics[c,rows],axis=0).max()))
    # At the same first bias, carryover and reset must start identically.
    first_error=0.
    for i,q in enumerate(tasks):
        if q['reset']:continue
        j=next(j for j,p in enumerate(tasks) if p['reset'] and p['beta']==q['beta'] and p['order']==q['order'])
        b=q['indices'][0]
        first_error=max(first_error,float(abs(metrics[:,i,b]-metrics[:,j,b]).max()))
    permutation_ok=all(sorted(o['indices'])==list(range(len(GRID))) for o in orders)
    reversal_ok=all(orders[4+2*k]['indices']==orders[5+2*k]['indices'][::-1] for k in range(len(SEEDS)))
    checks=dict(finite=bool(np.isfinite(metrics).all() and np.isfinite(fixed_values).all() and np.isfinite(reference).all()),
                every_bias_visited_once=permutation_ok,paired_order_reversals=reversal_ok,
                reset_order_invariance=reset_spread==0,identical_first_segments=first_error==0,
                window_mean_identity=bool(np.allclose(metrics[...,0],(metrics[...,1]+metrics[...,2])/2,atol=1e-12,rtol=0)))
    return dict(checks=checks,maximum_reset_order_spread=reset_spread,maximum_first_segment_discrepancy=first_error)


def plot(configs,tasks,metrics,result,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    chosen=configs.index(dict(method='rk4',dt=.02,settle=320))
    fig,axs=plt.subplots(2,3,figsize=(12.5,7.5),sharex=True,sharey=True)
    for col,beta in enumerate(BETAS):
        for row,reset in enumerate((True,False)):
            ax=axs[row,col]
            for name,label in [('up','Upward'),('down','Downward'),('alternate_low','Alternate low first'),('alternate_high','Alternate high first')]:
                i=get_rows(tasks,beta,reset,name=name)[0]
                ax.plot(GRID,metrics[chosen,i,:,0],marker='.',lw=1.2,label=label)
            records=[q for q in result['random_orders'] if q['config']==chosen and q['beta']==beta and q['reset']==reset and q['split']=='replication']
            ax.plot(GRID,[q['voltage']['mean'] for q in records],'k--',lw=1.2,label='Random order mean')
            ax.fill_between(GRID,[q['voltage']['lo'] for q in records],[q['voltage']['hi'] for q in records],color='grey',alpha=.22)
            ax.set(title=f"beta={beta:g} · {'reset each current' if reset else 'retain previous state'}",xlabel='Normalized current',ylabel='Mean normalized voltage')
    fig.legend(*axs[0,0].get_legend_handles_labels(),ncol=3,loc='lower center',bbox_to_anchor=(.5,.005),fontsize=9)
    fig.suptitle('Current order matters when the junction retains its history',fontsize=15)
    fig.tight_layout(rect=(0,.10,1,.96))
    for ext in ('png','svg'):fig.savefig(out/f'junction_orders.{ext}',dpi=150)
    plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(12,5))
    rows=get_rows(tasks,10.,False,split='replication')
    voltage=metrics[chosen,rows,:,0]
    im=axs[0].imshow(voltage,aspect='auto',origin='lower',cmap='viridis',vmin=0,vmax=1.5)
    axs[0].set(xticks=range(len(GRID)),xticklabels=[f'{x:g}' for x in GRID],xlabel='Normalized current (sorted for display)',
               ylabel='Random path / its reversal',title='Same current, different preceding history')
    axs[0].tick_params(axis='x',rotation=60)
    fig.colorbar(im,ax=axs[0],label='Mean voltage',shrink=.8)
    for reset,label in ((False,'Retain state'),(True,'Reset state')):
        records=[q for q in result['random_orders'] if q['config']==chosen and q['beta']==10. and q['reset']==reset and q['split']=='replication']
        ax=axs[1];ax.plot(GRID,[q['moving_fraction']['mean'] for q in records],marker='.',label=label)
        ax.fill_between(GRID,[q['moving_fraction']['lo'] for q in records],[q['moving_fraction']['hi'] for q in records],alpha=.15)
    axs[1].set(xlabel='Normalized current',ylabel='Fraction with mean voltage > 0.05',ylim=(-.03,1.03),title='A declared finite-window motion threshold')
    axs[1].legend()
    fig.suptitle('beta=10 · 12 replication seeds, each paired with its reversal',fontsize=14)
    fig.tight_layout()
    for ext in ('png','svg'):fig.savefig(out/f'junction_random_orders.{ext}',dpi=150)
    plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(12,4.8))
    for method,label in (('rk4','RK4'),('split_verlet','Damped leapfrog / Verlet')):
        for settle,style in ((160,'--'),(320,'-')):
            rows=[q for q in result['fixed_start_errors'] if configs[q['config']]['method']==method and configs[q['config']]['settle']==settle]
            axs[0].plot([configs[q['config']]['dt'] for q in rows],[q['maximum_absolute_error'] for q in rows],style,marker='o',label=f'{label}; settle {settle}')
    axs[0].set(xscale='log',yscale='log',xticks=[.02,.04],xticklabels=['0.02','0.04'],xlabel='Integration step',ylabel='Maximum voltage difference from RK4 step 0.005',title='Identical fixed starting states')
    axs[0].legend(fontsize=8)
    for method,label in (('rk4','RK4'),('split_verlet','Damped leapfrog / Verlet')):
        c=configs.index(dict(method=method,dt=.02,settle=320))
        rows=[q for q in result['paired_contrasts'] if q['kind']=='settling' and q['config']==c and q['beta']==10. and not q['reset'] and q['split']=='replication']
        axs[1].plot(GRID,[q['voltage_difference']['mean'] for q in rows],marker='.',label=label)
        axs[1].fill_between(GRID,[q['voltage_difference']['lo'] for q in rows],[q['voltage_difference']['hi'] for q in rows],alpha=.15)
    axs[1].axhline(0,color='grey',lw=.7)
    axs[1].set(xlabel='Normalized current',ylabel='Voltage: settling 320 minus 160',title='Longer settling; same 80-unit observation')
    axs[1].legend(fontsize=9)
    fig.tight_layout()
    for ext in ('png','svg'):fig.savefig(out/f'junction_numerics.{ext}',dpi=150)
    plt.close(fig)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('.'));args=p.parse_args()
    data=args.out/'data';out=args.out/'analysis';data.mkdir(parents=True,exist_ok=True);out.mkdir(exist_ok=True)
    target=data/'junction_orders.json';protocol=data/'junction_orders_protocol.json'
    if target.exists() or protocol.exists():raise SystemExit('Refusing to overwrite junction-order design or results.')
    orders=make_orders()
    tasks=[dict(beta=beta,reset=reset,order=o['name'],seed=o['seed'],split=o['split'],indices=o['indices'])
           for beta in BETAS for reset in (True,False) for o in orders]
    configs=[dict(method=method,dt=h,settle=settle) for method in ('rk4','split_verlet') for h in (.04,.02) for settle in (160,320)]
    fixed_cases=[dict(beta=b,bias=i,initial=start) for b in BETAS for i in (.5,.9,1.,1.025) for start in ('rest','running')]
    root=Path(__file__).resolve().parent
    protocol.write_text(json.dumps(dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        tests_file='test_junction_orders.py',tests_sha256=hashlib.sha256((root/'test_junction_orders.py').read_bytes()).hexdigest(),
        status='Exploratory follow-up after an observed pilot; not external preregistration.',
        equation='phi_dot=v; beta*v_dot=i-v-sin(phi); beta>0; normalized voltage is mean v.',
        no_noise='All dynamics are deterministic. Randomness selects current order only.',
        solver='split_verlet: half force kick, half phase drift, exact drag exp(-h/beta), half drift, half kick. RK4 is independently implemented.',
        configs=configs,tasks=tasks,grid=GRID.tolist(),seeds=SEEDS,orders=orders,
        windows=dict(observe=OBSERVE,half_window=OBSERVE/2),
        state_policy='Each independent whole path starts phi=v=0. Reset paths restart phi=v=0 at each current. Carryover paths retain both variables. Downward paths are independent runs, not the return leg of the earlier published up/down sweep.',
        fixed_cases=fixed_cases,fixed_initial='rest: phi=asin(min(i,1)),v=0; running: phi=0,v=max(i,1). For i>1 the rest-style start is not an equilibrium.',
        fixed_reference='RK4 dt .005; same fixed starts, settling160/320, observation80; deterministic numerical reference, not exact truth.',
        uncertainty='10000 percentile bootstrap draws from 12 independent permutation seeds per split, averaging a permutation and its reversal within seed. Descriptive unadjusted intervals; no CI for deterministic fixed orders.',
        threshold=MOVING,threshold_note='Mean voltage >.05 labels finite-window motion; it is not a proof of asymptotic locking or a measured switching-current threshold.',
        outputs='metrics[configuration,path,ascending_bias,metric]; metrics are full-window mean, first-half mean, second-half mean. Complete orders are preserved in protocol.',
        pilot='Prior local pilot: 192 fixed-start trajectories and70 sweep segments, retained separately; this design adds current levels, paired order reversals, seeds and a finer reference.'),indent=2))
    started=walltime.perf_counter();metrics=[];fixed_values=[];reference=[]
    betas=np.array([q['beta'] for q in tasks]);reset=np.array([q['reset'] for q in tasks]);indices=np.array([q['indices'] for q in tasks])
    fb=np.array([q['beta'] for q in fixed_cases]);fi=np.array([q['bias'] for q in fixed_cases])
    initial=np.array([[np.arcsin(min(q['bias'],1)) if q['initial']=='rest' else 0 for q in fixed_cases],
                      [0 if q['initial']=='rest' else max(q['bias'],1) for q in fixed_cases]],float)
    for config in configs:
        z=np.zeros((2,len(tasks)));saved=np.empty((len(tasks),len(GRID),3))
        for j in range(len(GRID)):
            z[:,reset]=0
            z,values=segment(z,GRID[indices[:,j]],betas,config['method'],config['dt'],config['settle'])
            saved[np.arange(len(tasks)),indices[:,j]]=values
        metrics.append(saved)
        _,values=segment(initial.copy(),fi,fb,config['method'],config['dt'],config['settle'])
        fixed_values.append(values)
        print('Completed',config,flush=True)
    for settle in (160,320):
        _,values=segment(initial.copy(),fi,fb,'rk4',.005,settle);reference.append(values)
    metrics=np.array(metrics);fixed_values=np.array(fixed_values);reference=np.array(reference)
    result=analyze(configs,tasks,metrics,fixed_cases,fixed_values,reference)
    result.update(validate(configs,tasks,metrics,fixed_values,reference,orders))
    result.update(configs=configs,sweep_paths=len(configs)*len(tasks),sweep_segments=len(configs)*len(tasks)*len(GRID),
                  fixed_start_runs=len(configs)*len(fixed_cases),fixed_reference_runs=2*len(fixed_cases),
                  seconds=walltime.perf_counter()-started,all_passed=all(result['checks'].values()))
    target.write_text(json.dumps(result,indent=2))
    np.savez_compressed(data/'junction_orders_arrays.npz',metrics=metrics,fixed_values=fixed_values,reference=reference)
    plot(configs,tasks,metrics,result,out)
    print(json.dumps({k:result[k] for k in ('sweep_paths','sweep_segments','fixed_start_runs','fixed_reference_runs','seconds','checks')},indent=2))
    if not result['all_passed']:raise SystemExit('A diagnostic failed; inspect saved data.')


if __name__=='__main__':main()
