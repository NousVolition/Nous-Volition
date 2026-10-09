"""Frozen factorial design, matched controls, and independent seed replication.
Run from this directory: python run_study.py --workers 4 --out data
"""
import argparse, concurrent.futures, hashlib, itertools, json, os, platform, time
from dataclasses import replace, asdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from model import Config, run, initialize, response_matrix


def design(quick=False):
    tasks=[]
    def add(suite,c,split):
        tasks.append(dict(id=f'{len(tasks):05d}',suite=suite,split=split,config=asdict(c)))
    seeds=list(range(1100,1112))+list(range(9100,9112))
    if quick: seeds=[1100,9100]
    for seed in seeds:
        split='discovery' if seed<9000 else 'replication'
        r=(seed%100)
        for topo,balance in itertools.product(('ring','random','hub'),('equal','unequal')):
            base=Config(seed=seed,rotation=r,topology=topo,balance=balance)
            for behavior,memory,stress,transitions,identity in itertools.product((0,1),repeat=5):
                add('factorial',replace(base,behavior=behavior,memory=memory,stress=stress,transitions=transitions,identity=.7*identity),split)
            # Three executable controls, not just aliases of the same file.
            for labels,shift in [('neutral',0),('evocative',0),('evocative',3)]:
                add('labels',replace(base,labels=labels,label_shift=shift),split)
            add('random_null',replace(base,random_choice=1),split)
            if split=='replication':
                full=replace(base,behavior=1,memory=1,transitions=1,identity=.7)
                for n,stress in itertools.product((30,120),(0,1)):
                    add('population',replace(full,n=n,stress=stress),split)
                for kind in ('scarcity','time','information'):
                    add('stress_component',replace(full,stress=1,stress_kind=kind),split)
                if balance=='equal':
                    for decay in (.85,.97,.995):
                        add('sweep',replace(full,decay=decay),split)
                        for scarcity in (.35,.55,.85):
                            add('sweep',replace(full,stress=1,decay=decay,scarcity=scarcity),split)
                    # Semantic mechanism is off in factorial. Only here do words
                    # enter utility. Each word is targeted equally in sensitivity.
                    for target in range(6):
                        add('semantics',replace(base,semantic=-.7,semantic_target=target),split)
                    add('semantics',base,split)
                    add('semantics',replace(base,semantic=.7),split)
                    add('semantics',replace(base,semantic=-.7,label_shift=3),split)
    return tasks


def worker(task):
    result=run(Config(**task['config']))
    return task,result


def leadership(out,seeds):
    records=[]
    for seed in seeds:
        for topo in ('ring','random','hub'):
            c=Config(seed=seed,topology=topo)
            a,g,traits,profiles=initialize(c)
            rng=np.random.default_rng(seed+771)
            charisma=rng.normal(0,.25,c.n)
            def score(ch):
                p=response_matrix(a,ch);v=np.ones(c.n)/c.n
                for _ in range(8):v=v@p
                return v
            homogeneous=score(np.zeros(c.n));hi=int(homogeneous.argmax());lo=int(homogeneous.argmin())
            p=np.arange(c.n);p[hi],p[lo]=p[lo],p[hi]
            for heterogeneity in (0,1):
                before=score(charisma*heterogeneity)
                after_site=score(charisma[p]*heterogeneity)
                after_id=after_site[np.argsort(p)]
                records.append(dict(seed=seed,topology=topo,heterogeneity=heterogeneity,
                    selected_high_site=hi,selected_low_site=lo,
                    old_high_identity_effect=float(after_id[hi]-before[hi]),
                    original_high_site_effect=float(after_site[hi]-before[hi]),
                    leader_before=int(before.argmax()),leader_after_identity=int(p[after_site.argmax()]),
                    max_min_ratio=float(before.max()/before.min()),
                    site_max_difference=float(np.max(abs(after_site-before))),
                    identity_mean_difference=float(np.mean(abs(after_id-before)))))
    (out/'leadership.json').write_text(json.dumps(records,indent=2))
    # Safe, synthetic attribution exercise. Six identical failure records, equal
    # exposure, optional assumed label prior; categorical choices sampled.
    blame=[]
    for seed in seeds:
        u=np.random.default_rng(seed+8001).random(600)
        for target in range(6):
            for bias in (0.,.7):
                logits=np.zeros(6);logits[target]=bias
                probs=np.exp(logits)/np.exp(logits).sum()
                chosen=(u[:,None]>np.cumsum(probs)[None,:]).sum(1)
                blame.append(dict(seed=seed,target=target,bias=bias,trials=600,
                    share=float(np.mean(chosen==target)),expected_share=float(probs[target]),
                    excess_over_equal_evidence=float(np.mean(chosen==target)-1/6)))
    (out/'synthetic_attribution.json').write_text(json.dumps(blame,indent=2))


def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=4)
    p.add_argument('--out',type=Path,default=Path('data'));p.add_argument('--quick',action='store_true')
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    if (args.out/'arrays.npz').exists():
        raise SystemExit('Choose a new --out directory; recorded arrays are never overwritten.')
    tasks=design(args.quick)
    sources={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in ('model.py','run_study.py')}
    protocol=dict(status='frozen before ensemble; exploratory simulation, not externally preregistered',
        started_utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),numpy=np.__version__,
        workers=args.workers,task_count=len(tasks),source_hashes=sources,quick=args.quick,
        primary_metrics=['choice_excess','coop_gap','window_excluded','rigid','switching'],
        uncertainty='Paired seed-cluster bootstrap; collapse topology and group balance within independent seed.',
        discovery='1100 through 1111',replication='9100 through 9111',
        phase_rounds='0-39 baseline, 40-79 stress (when enabled), 80-119 recovery',
        note='All parameters fixed before these batches. No learned predictor, no fit to humans. Replication is independent seeds, not prospective external confirmation.')
    (args.out/'protocol.json').write_text(json.dumps(protocol,indent=2))
    (args.out/'tasks.json').write_text(json.dumps(tasks,indent=2))
    traces=[];phases=[];groups=[];pairs=[];digests=[];schemas=None;t0=time.perf_counter()
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for i,(task,result) in enumerate(pool.map(worker,tasks,chunksize=8)):
            if schemas is None:
                schemas={name:list(result[name][0]) for name in ('trace','phases','groups','pairs')}
            for name,store in [('trace',traces),('phases',phases),('groups',groups),('pairs',pairs)]:
                store.append(np.array([[r[k] for k in schemas[name]] for r in result[name]],dtype=float))
            digests.append(result['digest'])
            if (i+1)%200==0:print(f'{i+1}/{len(tasks)} runs; {time.perf_counter()-t0:.1f}s',flush=True)
    np.savez_compressed(args.out/'arrays.npz',trace=np.array(traces),phases=np.array(phases),groups=np.array(groups),pairs=np.array(pairs),digests=np.array(digests))
    (args.out/'schema.json').write_text(json.dumps(schemas,indent=2))
    leadership(args.out,sorted({t['config']['seed'] for t in tasks}))
    # Auditable event logs for the full model, paired stress/no-stress exemplar.
    for stress in (0,1):
        c=Config(seed=9100,topology='hub',behavior=1,memory=1,transitions=1,identity=.7,stress=stress)
        result=run(c,True)
        np.savez_compressed(args.out/f'example_events_stress{stress}.npz',events=result['events'],groups=result['group_history'])
    protocol.update(completed_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-t0,completed_runs=len(tasks),leadership_assays=len(json.loads((args.out/'leadership.json').read_text())),attribution_assays=len(json.loads((args.out/'synthetic_attribution.json').read_text())))
    (args.out/'execution.json').write_text(json.dumps(protocol,indent=2))
    print(json.dumps(protocol,indent=2))


if __name__=='__main__':main()
