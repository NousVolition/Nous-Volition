"""Run the complete pilot sequentially on a compatible GPU, then analyze.

Completed folders are skipped. Change a run name or use a fresh directory to
repeat. Runtime depends strongly on GPU and installed OpenMM platform.
"""
from pathlib import Path
import subprocess,sys
P=Path(__file__).resolve().parent


def call(script,*args):subprocess.run([sys.executable,str(P/script),*map(str,args)],check=True)


def main():
    call('verify_runtime.py')
    call('boundary_budget.py')
    for seed in [101,202,303]:
        name=f'primary_seed{seed}'
        if not (P/'water'/name/'metadata.json').exists():call('water_md.py','--name',name,'--seed',seed)
        if not (P/'water'/(name+'_extension')/'metadata.json').exists():call('extend_water.py',name)
    for name,args in [('timestep_1fs',['--dt',.001]),('lateral_3nm',['--lateral',3])]:
        if not (P/'water'/name/'metadata.json').exists():call('water_md.py','--name',name,*args)
    cases=[('re1500_d20',[]),('re2500_d20',['--reynolds',2500]),
      ('re1500_d28',['--diameter',28]),('re2500_d28',['--reynolds',2500,'--diameter',28]),
      ('re1500_sphere',['--aspect',1]),('re1500_slow',['--speed',.03]),
      ('re1500_wide',['--width',7,'--length',16]),('low_re20',['--reynolds',20,'--aspect',1,'--cs',0]),
      ('micev_dvs',['--reynolds',1300]),('micev_parsivel',['--reynolds',1066.666667]),
      ('micev_dvs_aspect084',['--reynolds',1300,'--aspect',.84]),('re1500_seed97',['--seed',97]),
      ('re1500_no_sgs',['--cs',0]),('terminal_re800',['--reynolds',800]),('terminal_re1000',['--reynolds',1000])]
    for name,args in cases:
        if not (P/'flow'/name/'metadata.json').exists():call('flow_lbm.py','--name',name,*args)
    if not (P/'nve_check.json').exists():call('nve_check.py')
    call('test_analysis.py');call('analyze.py');call('audit_saved.py');call('make_report.py')

if __name__=='__main__':main()
