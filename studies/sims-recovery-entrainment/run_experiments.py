"""Run the frozen follow-up design. Python + NumPy; plotting is separate."""
import argparse, concurrent.futures, hashlib, json, platform, time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from recovery_model import Config, run
from oscillators import integrate_phase, junction_sweep, network_block, circle_solutions

SEEDS=list(range(12100,12112))+list(range(22100,22112))
SCHEDULES={'never':[], 'early':[(40,80)], 'late':[(200,240)], 'repeated':[(40,80),(200,240)]}
FIELDS=['cooperation','rigid','choice_excess','switching','boundary_crossing','pool_used','membership_retention','group_entropy']


def tasks(quick=False):
    out=[]
    for seed in (SEEDS[:1]+SEEDS[12:13] if quick else SEEDS):
        for topology in ('ring','random','hub'):
            for balance in ('equal','unequal'):
                for memory in (0,1):
                    for schedule in SCHEDULES:
                        c=Config(n=60,seed=seed,rotation=seed%100,topology=topology,balance=balance,
                                 rounds=480,behavior=1,memory=memory,stress=1,transitions=1,identity=.7)
                        out.append(dict(id=len(out),split='discovery' if seed<20000 else 'replication',
                                        schedule=schedule,config=asdict(c)))
    return out


def recovery_worker(task):
    r=run(Config(**task['config']),stress_windows=SCHEDULES[task['schedule']])
    trace=np.array([[row[f] for f in FIELDS[:6]] for row in r['trace']])
    history=r['group_history'];retention=(history==np.array(r['initial_groups'])).mean(1)
    fractions=np.array([(history==j).mean(1) for j in range(6)]).T
    entropy=-(fractions*np.log(np.maximum(fractions,1e-300))).sum(1)/np.log(6)
    values=np.column_stack([trace,retention,entropy]).reshape(48,10,len(FIELDS)).mean(1)
    return values,r['digest'],r['final_groups']


def network_worker(args):return network_block(*args)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('data'))
    p.add_argument('--workers',type=int,default=4);p.add_argument('--quick',action='store_true')
    a=p.parse_args();a.out.mkdir(exist_ok=True)
    if (a.out/'protocol.json').exists():raise SystemExit('Refusing to overwrite an existing execution directory.')
    started=time.perf_counter();design=tasks(a.quick)
    sources=['recovery_model.py','oscillators.py','run_experiments.py','analyze.py','test_experiments.py']
    protocol=dict(status='Frozen before this ensemble; exploratory follow-up, not externally preregistered.',
      frozen_utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),numpy=np.__version__,
      quick=a.quick,seeds=sorted({t['config']['seed'] for t in design}),recovery_runs=len(design),
      schedules=SCHEDULES,rounds=480,block_size=10,trace_fields=FIELDS,
      source_hashes={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in sources},
      recovery_primary='Last 40 rounds: early-minus-never and repeated-minus-late, for rigidity, cooperation and choice excess, separated by memory.',
      acute_primary='Rounds 201-240: (repeated-early)-(late-never), separated by memory.',
      recovery_rule='Two consecutive 10-round blocks with abs(paired rigidity difference)<=.03 AND abs(choice-excess difference)<=.03; count from stress removal. First attainment is not sustained recovery.',
      recovery_comparisons={'early':'never','late':'never','repeated':'early'},
      uncertainty='10,000 percentile bootstrap resamples of 12 independent seed means per split; average network and balance within seed. Descriptive unadjusted intervals.',
      network='30 oscillator SIMS; three topologies; four driver positions; two mappings swap the high/low occupants with their detuning and initial phase. Total forcing 12 for every nonzero mode, coupling 4, dt .04, horizon 120, final window 30.',
      network_lock='abs(mean phase drift)<.005 AND phase excursion<.2 in final 30 time units; numerical finite-window criterion.',
      physical_models='Dimensionless equations supplied in screenshots, not measured devices or calibrated human behavior.',
      junction='beta .2,2,10; bias grid 0..1.5 step .025; upward/downward continuation; dt .04, settle160, observe80; repeat dt .02 and settle320.',
      circle='All fully visible exercises 4.1.2--4.1.7; 4.1.8 body and later 4.5.1 subparts are not visible.',
      future='No volunteer activity is executed; no equilibrium or permanent-memory claim from finite horizons.')
    (a.out/'protocol.json').write_text(json.dumps(protocol,indent=2))
    (a.out/'tasks.json').write_text(json.dumps(design,indent=2))
    with concurrent.futures.ProcessPoolExecutor(a.workers) as pool:
        results=list(pool.map(recovery_worker,design,chunksize=4))
        network=list(pool.map(network_worker,[(s,t) for s in protocol['seeds'] for t in ('ring','random','hub')]))
    np.savez_compressed(a.out/'recovery.npz',blocks=np.array([r[0] for r in results]),
                        digests=np.array([r[1] for r in results]),final_groups=np.array([r[2] for r in results]))
    (a.out/'network.json').write_text(json.dumps([r for block in network for r in block],indent=2))
    delta=np.array([0,.25,.5,.75,.95,1.,1.02,1.05,1.1,1.25,1.5,1.6,1.75,2.,2.5,3.])
    phases={}
    for response in ('sine','triangle','triangle_normalized'):
        for suffix,dt in [('',.02),('_fine',.01)]:
            for key,value in integrate_phase(delta,response,dt=dt).items():phases[response+suffix+'_'+key]=value
    np.savez_compressed(a.out/'phase.npz',**phases)
    (a.out/'junction.json').write_text(json.dumps(junction_sweep([.2,2,10]),indent=2))
    (a.out/'junction_refined.json').write_text(json.dumps(junction_sweep([.2,2,10],dt=.02,settle=320),indent=2))
    (a.out/'circle.json').write_text(json.dumps(circle_solutions(),indent=2))
    execution=dict(completed_utc=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-started,
                   recovery_runs=len(design),network_runs=len(network)*8,phase_trajectories=6*len(delta),
                   junction_grid_segments=2*3*2*61,workers=a.workers)
    (a.out/'execution.json').write_text(json.dumps(execution,indent=2));print(json.dumps(execution,indent=2))


if __name__=='__main__':main()
