"""Audit saved simulation results without declaring empirical validation."""
from pathlib import Path
import csv,json,hashlib,ast
import numpy as np

P=Path(__file__).resolve().parent


def main():
    checks=[];outcomes=[]
    def check(name,ok,detail=''):
        checks.append(dict(name=name,passed=bool(ok),detail=detail))
    whash=hashlib.sha256((P/'water_md.py').read_bytes()).hexdigest()
    fhash=hashlib.sha256((P/'flow_lbm.py').read_bytes()).hexdigest()
    waters=sorted((P/'water').glob('*/metadata.json'));flows=sorted((P/'flow').glob('*/metadata.json'))
    check('water run count including continuations',len(waters)==8,len(waters))
    check('flow attempt count including failed control',len(flows)==15,len(flows))
    for meta in waters:
        m=json.loads(meta.read_text());name=m['name'];folder=meta.parent
        data=np.genfromtxt(folder/'samples.csv',delimiter=',',names=True)
        frames=np.load(folder/'analysis_frames.npz');xyz=frames['xyz_nm'];box=frames['box_nm']
        check(name+': original force source pinned',m['source_sha256']==whash)
        check(name+': finite energy and declared duration',np.isfinite(data.view(float)).all() and len(data)==m['production_ps'])
        zero_error=float(np.max(abs(data['U_zero']-data['potential_kJ_mol']))/m['N'])
        check(name+': zero-strain evaluation agrees per molecule',zero_error<1e-4,dict(maximum_kJ_mol_per_molecule=zero_error))
        check(name+': number of water molecules preserved',xyz.shape[1]==m['N'])
        d=xyz[:,:,1:]-xyz[:,:,0:1];d-=box*np.rint(d/box)
        bond_error=float(np.max(abs(np.linalg.norm(d,axis=-1)-.09572)))
        check(name+': rigid OH geometry',bond_error<2e-5,dict(maximum_error_nm=bond_error))
        check(name+': saved frame cadence',np.array_equal(frames['original_frame_indices'],np.arange(0,len(data),20)))
        # No exact thermostatted energy-conservation assertion is made.
        check(name+': temperature remains finite and physical',np.all((data['temperature_K']>200)&(data['temperature_K']<400)))
    for meta in flows:
        m=json.loads(meta.read_text());name=m['name'];folder=meta.parent
        data=np.genfromtxt(folder/'history.csv',delimiter=',',names=True);field=np.load(folder/'slices.npz')
        check(name+': flow source pinned',m['source_sha256']==fhash)
        check(name+': finite saved output',np.isfinite(data.view(float)).all() and np.isfinite(field['mean']).all())
        check(name+': dimensioned geometry',tuple(field['solid'].shape)==tuple(m['grid'][:2]))
        complete=m['status']=='completed';outcomes.append(dict(name=name,status=m['status'],completed=m['duration_completed']))
        check(name+': termination status consistent',abs(m['duration_completed']-m['duration_requested'])<.01 if complete else m['duration_completed']<m['duration_requested'])
        if complete:
            check(name+': numerical stability guard',data['rho_min'].min()>=.8 and data['rho_max'].max()<=1.2 and data['max_speed_lattice'].max()<=.35)
    with (P/'topology_summary.csv').open() as file:
        for row in csv.DictReader(file):
            counts=[int(row[k]) for k in ['HDL','LDL','unclassified']];n=sum(counts)
            check(row['name']+': topology '+row['layer'],n>0 and abs(float(row['coverage'])-sum(counts[:2])/n)<1e-12)
    r=json.loads((P/'results.json').read_text())
    check('three independent primary water seeds',r['water']['aggregate']['n_seeds']==3)
    check('failed flow excluded from physical Cd mean',all(x['Cd_mean'] is None for x in r['flow']['summary'] if x['status']!='completed'))
    check('flow comparison values are finite',all(np.isfinite(x['drag_over_weight_minus_buoyancy']) for x in r['flow']['comparisons']))
    check('independent inlet/outlet mass budget',json.loads((P/'boundary_budget.json').read_text())['passed'])
    energy=json.loads((P/'nve_check.json').read_text())
    check('smaller step reduces short NVE energy range',energy[1]['energy_range_kJ_mol_per_molecule']<energy[0]['energy_range_kJ_mol_per_molecule'])
    for source in P.glob('*.py'):
        ast.parse(source.read_text(encoding='utf-8'));check('syntax '+source.name,True)
    result=dict(checks=checks,passed=sum(c['passed'] for c in checks),total=len(checks),flow_outcomes=outcomes,
                note='Audit passes can coexist with an expected retained numerical failure and poor physical agreement. This is not a model-validation certificate.')
    (P/'saved_data_audit.json').write_text(json.dumps(result,indent=2));print(f"Saved-data checks: {result['passed']}/{result['total']}")
    if result['passed']!=result['total']:raise SystemExit(1)

if __name__=='__main__':main()
