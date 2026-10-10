"""Recreate every result in a fresh directory without touching delivered data."""
import argparse,shutil,subprocess,sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--workers',type=int,default=4);a=p.parse_args()
    source=Path(__file__).resolve().parent;destination=a.out.resolve()
    if destination.exists():raise SystemExit('Destination already exists; choose a new directory.')
    study=destination/'studies/sims-recovery-entrainment';reference=destination/'studies/social-organization'
    study.mkdir(parents=True);reference.mkdir()
    for f in source.glob('*.py'):shutil.copy2(f,study/f.name)
    for name in ('model_provenance.json','requirements.txt','README.md','.gitignore','.gitattributes'):shutil.copy2(source/name,study/name)
    shutil.copy2(source.parent/'social-organization/model.py',reference/'model.py')
    commands=[['test_experiments.py'],['run_experiments.py','--workers',str(a.workers)],['analyze.py'],['verify_results.py'],
              ['pendulum.py'],['index_and_bistability.py'],['structural_models.py'],['index_exercises.py'],['weak_oscillators.py'],['averaging.py'],['transient_memory.py'],['test_junction_orders.py'],['junction_orders.py'],['build_report.py'],['package.py']]
    for args in commands:
        print('Running',args[0],flush=True);subprocess.run([sys.executable,*args],cwd=study,check=True)
    print('Completed:',study/'report.html')


if __name__=='__main__':main()
