"""Verify saved outputs, equations, source ownership, controls and actual refinement."""
from pathlib import Path
import hashlib,json,argparse
import numpy as np
from validate_observations import validate
from corpus_field import Field,Parameters
from observer import setup,readout
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def verify(raw=None,published=False):
    r=json.loads((ROOT/'results/results.json').read_text(encoding='utf-8'))
    s=json.loads((ROOT/'results/stronger_reading.json').read_text(encoding='utf-8'))
    checks=[]
    def check(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(name)
    check('Unchanged audited full solver',sha(ROOT/'corpus_field.py')=='00b50a93ae413d46109327ccf0c08e8e07d00028313eaa0da87d765e58705f35')
    for key,file in [('protocol_sha256','PROTOCOL.md'),('observation_operator_sha256','observer.py'),('numerical_amendment_sha256','NUMERICAL_AMENDMENT.md')]:
        check('Source lock '+file,r[key]==sha(ROOT/file))
    check('Original frozen protocol',r['protocol_sha256']=='fa8c0a567f4b12f93d19760258b4891e89d5ed5bd00d11841276d59ed4e49609')
    check('Stricter reading amendment',s['amendment_sha256']==sha(ROOT/'CONSTRAINT_AMENDMENT.md'))
    check('Stricter reading tied to original results',s['original_results_sha256']==sha(ROOT/'results/results.json'))
    ledger=validate(json.loads((ROOT/'observations.json').read_text(encoding='utf-8')))
    check('One actual person, five episodes',ledger['people']==1 and ledger['episodes']==5)
    check('No empirical forecast score',r['empirical_prediction_score'] is None)
    check('Complete declared search',len(r['runs'])==63 and len(r['refinements'])==8 and len(r['controls'])==4)
    check('Complete exploratory refinement',len(s['additional_runs'])==3)
    check('48 compatible candidates',sum(x['compatible'] for x in r['runs'])==48)
    check('60 constructive pairs',len(r['witnesses'])==60)
    allruns=r['runs']+r['refinements']+r['controls']+s['additional_runs']
    for key,tol in [('mass_error_max',1e-10),('divergence_max',1e-12),('energy_residual_max',1e-12)]:
        check(key,max(x[key] for x in allruns)<tol)
    a,b=[r['runs'][i] for i in r['selected_witness']['indices']]
    check('Same initial context and movement readouts',all(a['initial'][k]==b['initial'][k] for k in ['c_P','c_F','v_P','v_F']))
    check('Both compatible and opposite endpoints',a['compatible'] and b['compatible'] and a['final']['contrast']*b['final']['contrast']<0)
    convergence=[]
    for A in [-.02,.005,.02]:
        rows=s['additional_runs'] if A==.005 else [x for x in r['refinements'] if x['A0']==A]
        g48=next(x for x in rows if x['n']==48 and x['refinement_label']=='grid_refinement')
        g72=next(x for x in rows if x['n']==72)
        half=next(x for x in rows if x['refinement_label']=='effective_half_step')
        g24=next(x for x in r['runs'] if x['law']=='sharp' and x['distance']==.15 and x['A0']==A)
        d1=abs(g24['final']['contrast']-g48['final']['contrast']);d2=abs(g48['final']['contrast']-g72['final']['contrast'])
        dt=abs(g48['final']['contrast']-half['final']['contrast'])
        check(f'A={A}: actual half step',half['steps']==2*g48['steps'] and half['dt']==g48['dt']/2)
        check(f'A={A}: grid contraction',d2<d1 and d2<2e-8)
        check(f'A={A}: time agreement',dt<1e-9)
        check(f'A={A}: sign and constraints stable',all(x['compatible'] and x['final']['contrast']*g24['final']['contrast']>0 for x in [g48,g72,half]))
        if A>0:check(f'A={A}: stricter directions survive',all(x['initial']['dc_P']>0 and x['initial']['dc_F']<0 for x in [g24,g48,g72,half]))
        convergence.append(dict(A0=A,grid24_48=d1,grid48_72=d2,actual_half_step=dt,contrast72=g72['final']['contrast']))
    controls=[x for x in r['controls'] if x['control']=='no_source']
    check('No source readouts identical across A',controls[0]['final']=={**controls[1]['final'],'A':controls[0]['final']['A']})
    check('Pressure retained when forcing disabled',all(x['final']['pressure_rms']>0 for x in r['controls'] if x['control']=='no_force'))
    # pressure can still arise from nonlinear advection; sigma=0 does not remove the momentum equation.
    provenance=json.loads((ROOT/'provenance.json').read_text(encoding='utf-8'))
    check('Five primary source hashes',len(provenance['sources'])==5)
    states=np.load(ROOT/'results/states.npz')['search']
    check('Saved full state dimensions and finite values',states.shape==(63,3,24,24) and np.isfinite(states).all())
    error=0.
    for state,row in zip(states,r['runs']):
        field=Field(Parameters(law=row['law']));_,weights=setup(field,row['distance'])
        measured=readout(field,field.fft(state),row['A0'],weights)
        error=max(error,max(abs(measured[k]-row['final'][k]) for k in ['c_P','c_F','contrast']))
    check('Saved fields reproduce saved endpoint readouts',error<1e-12)
    if raw:
        for source in provenance['sources']:check('Downloaded source '+source['file'],sha(Path(raw)/source['file'])==source['sha256'])
    if published:
        for file,h in json.loads((ROOT/'manifest_sha256.json').read_text(encoding='utf-8')).items():check('Artifact hash '+file,sha(ROOT/file)==h)
    return dict(status='pass',checks=len(checks),check_names=checks,ledger=ledger,convergence=convergence,
                maxima={k:max(x[k] for x in allruns) for k in ['mass_error_max','divergence_max','energy_residual_max']})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw-sources');p.add_argument('--save',action='store_true');p.add_argument('--published',action='store_true');args=p.parse_args()
    result=verify(args.raw_sources,args.published)
    if args.save:(ROOT/'results/verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
