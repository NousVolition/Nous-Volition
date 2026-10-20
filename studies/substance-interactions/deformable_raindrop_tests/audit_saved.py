"""Check scientific record integrity without rerunning GPU calculations."""
from pathlib import Path
import csv,json,hashlib,ast
import numpy as np
from shape_model import GasLibrary,MAT,geometry,mechanics
from analyze import library_rows,flow_rows
from study_status import study_status
P=Path(__file__).resolve().parent;checks=[]
def check(name,passed,value=None):checks.append(dict(name=name,passed=bool(passed),value=value))

for f,sha in json.loads((P/'source_freeze.json').read_text()).items():
    check('frozen source '+f,hashlib.sha256((P/f).read_bytes()).hexdigest()==sha)
for f in P.glob('*.py'):
    ast.parse(f.read_text(encoding='utf-8'));check('valid Python '+f.name,True)
for f in ['shape_verification.json','gas_verification.json','surface_load_verification.json','mass_budget_verification.json']:
    check('verification record '+f,json.loads((P/f).read_text())['status']=='passed')
rows=flow_rows();results=json.loads((P/'results.json').read_text())
expected=[]
for f in ['run_design.json','refined_run_design.json']:
    expected.extend(name for name,_ in json.loads((P/f).read_text()))
expected=set(expected);status=study_status()
recorded=set(x['name'] for x in rows)
unfinished=set(x['name'] for x in status['unfinished'])
check('every planned case completed or explicitly unfinished',expected==recorded|unfinished,len(rows))
check('no undeclared final case records',recorded<=expected)
check('saved status matches case inventory',results['study_status']==status)
frozen=json.loads((P/'source_freeze.json').read_text())['flow_lbm.py']
for row in rows:
    name=row['name'];folder=P/'flow'/name;m=json.loads((folder/'metadata.json').read_text())
    h=np.genfromtxt(folder/'history.csv',names=True,delimiter=',')
    check(name+' same physical solver',m['source_sha256']==frozen)
    check(name+' completed',m['status']=='completed')
    check(name+' increasing recorded time',np.all(np.diff(h['tU_D'])>0))
    check(name+' finite saved history',all(np.isfinite(h[k]).all() for k in h.dtype.names))
    check(name+' density guard',h['rho_min'].min()>=.8 and h['rho_max'].max()<=1.2)
    check(name+' lattice speed guard',h['max_speed_lattice'].max()<=.35)
    check(name+' final time',abs(h['tU_D'][-1]-m['duration_requested'])<=m['speed']/m['D_lattice'])
    check(name+' positive mean drag',row['Cd']>0,row['Cd'])
    check(name+' mean slice accumulated',int(np.load(folder/'slices.npz')['mean_samples'])>0)
for d in [20,28]:
    data=library_rows(rows,d);check('complete library '+str(d),len(data)==9)
    lib=GasLibrary(data)
    try:lib.forces(.004,20,np.log(.75))
    except ValueError:check('no extrapolation '+str(d),True)
    else:check('no extrapolation '+str(d),False)
    for saved in [p for p in results['predictions'] if p['gas_grid_D']==d]:
        calc=lib.terminal(saved['diameter_mm']/1000)
        check('saved equilibrium '+str(d)+' '+str(saved['diameter_mm']),abs(calc['aspect']-saved['aspect'])<1e-10)
        check('self-consistent force/shape balance '+str(d)+' '+str(saved['diameter_mm']),calc['balance_error']<1e-5,calc['balance_error'])
        D=saved['diameter_mm']/1000;s=np.log(saved['aspect']);speed=saved['speed_m_s'];eps=1e-5
        capillary=(mechanics(s+eps,D)[3]-mechanics(s-eps,D)[3])/(2*eps)
        air=(lib.forces(D,speed,s+eps)[1]-lib.forces(D,speed,s-eps)[1])/(2*eps)
        check('locally restoring shape equilibrium '+str(d)+' '+str(saved['diameter_mm']),capillary-air>0,float(capillary-air))
obs=list(csv.DictReader((P/'measurements.csv').open()))
check('all preselected measured diameters',[float(x['diameter_mm']) for x in obs]==[2.5,2.9,3.6,4.])
check('table2 vs table3 discrepancy retained',float(obs[-1]['mean_axis_ratio'])==.808 and float(obs[-1]['table3_mean'])==.807)
check('every diameter scored on both grids',len(results['predictions'])==8)
check('all compared results are inside gas table',all(x['status']=='root_inside_library' for x in results['predictions']))
for name,trace in np.load(P/'deformation_traces.npz').items():
    check(name+' finite shape trajectory',np.isfinite(trace).all())
    check(name+' positive shape ratio',np.all(trace[:,3]>0))
    D=float(name[1:])/1000 if name.startswith('D') else .004
    a,b=geometry(trace[:,1],D);volume=4*np.pi*a*b*b/3
    check(name+' constant water volume',np.max(abs(volume/(np.pi*D**3/6)-1))<1e-13)
    check(name+' liquid work-energy budget',np.max(abs(trace[:,-1]))/(MAT['surface_tension_N_m']*D**2)<1e-7)
report=dict(scope='Integrity of available records; this audit does not pass unfinished numerical checks.',
    all_planned_cases_completed=status['all_planned_cases_completed'],unfinished_cases=status['unfinished'],
    total=len(checks),passed=sum(x['passed'] for x in checks),failed=[x for x in checks if not x['passed']],checks=checks)
(P/'saved_data_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))
assert report['passed']==report['total']
