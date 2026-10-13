"""Audit saved outputs and delivered hashes without repeating long simulations.

After intentionally changing/reproducing results, --refresh-manifest makes a new
snapshot. This option is not a substitute for checking the numerical results.
"""
from pathlib import Path
import csv,json,hashlib,re,sys
import numpy as np
ROOT=Path(__file__).resolve().parent
checks=[]
def check(name,condition):
    checks.append(dict(name=name,passed=bool(condition)))
    if not condition:raise AssertionError(name)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(n):
    with (ROOT/'results'/n).open(encoding='utf-8') as f:return list(csv.DictReader(f))
def nums(rs,k):return np.array([float(r[k]) for r in rs])
def snapshot():
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(ROOT.rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts
        and p.name not in ('manifest.json','verification.json') and p.suffix!='.pyc'}
def run():
    for p in ROOT.rglob('*.json'):
        json.loads(p.read_text(encoding='utf-8'),parse_constant=lambda s:(_ for _ in ()).throw(ValueError(s)))
    check('All JSON documents parse without nonstandard NaN/Infinity',True)
    for p in ROOT.glob('*.py'):compile(p.read_text(encoding='utf-8'),p.name,'exec')
    check('All delivered Python scripts compile',True)
    s=json.loads((ROOT/'results/summary.json').read_text())
    surf=json.loads((ROOT/'results/surface_summary.json').read_text())
    for name,d in [('core',json.loads((ROOT/'results/input_hashes.json').read_text())),('surface',surf['input_hashes'])]:
        check(name+' input hashes match delivered source and data',all(sha(ROOT/p)==h for p,h in d.items()))
    check('Recorded core test run: 28 passed',bool(re.search(r'Ran 28 tests.*?\bOK\b',(ROOT/'test_log.txt').read_text(),re.S)))
    check('Recorded surface test run: 6 passed',bool(re.search(r'Ran 6 tests.*?\bOK\b',(ROOT/'surface_test_log.txt').read_text(),re.S)))
    sizes={'carbonate_cases.csv':11,'carbonate_refinement.csv':3,'radial_cases.csv':12,'radial_refinement.csv':8,
        'radial_sensitivity.csv':7,'capture_seeds.csv':72,'capture_comparison.csv':18,'capture_controls.csv':48,
        'capture_control_summary.csv':12,'peroxide_rate_audit.csv':4,'peroxide_figure_audit.csv':2,
        'ice_aging_endpoints.csv':21,'charge_distribution.csv':603,'charge_relaxation.csv':7,'near_contact.csv':4,
        'surface_partition.csv':46}
    check('Every expected CSV has the stated number of cases',all(len(rows(n))==v for n,v in sizes.items()))
    cap=rows('capture_comparison.csv'); seeds=rows('capture_seeds.csv')
    for r in cap:
        sub=[x for x in seeds if x['RH_percent']==r['RH_percent'] and x['wet_radius_nm']==r['wet_radius_nm']]
        check('Capture mean agrees with 4 seeds: '+r['RH_percent']+'/'+r['wet_radius_nm'],
            len(sub)==4 and len({x['seed'] for x in sub})==4 and abs(np.mean(nums(sub,'CE'))-float(r['predicted_CE']))<1e-14)
    ratio=nums(cap,'predicted_CE')/nums(cap,'observed_CE')
    check('Capture ratio and headline median agree',np.allclose(ratio,nums(cap,'predicted_over_observed'),rtol=1e-13) and
          abs(np.median(np.maximum(ratio,1/ratio))-s['falling']['median_factor_error'])<1e-13)
    check('No censored flux in main capture cases',np.max(nums(cap,'max_censored_bound'))==0)
    radial=rows('radial_cases.csv')
    check('Gas-liquid inventory and separate transfer audit below 1e-9',
          max(np.max(nums(radial,'mass_residual')),np.max(nums(radial,'transfer_audit')))<1e-9)
    check('All radial liquid fractions lie in [0,1]',np.min(nums(radial,'final_liquid_fraction'))>=0 and np.max(nums(radial,'peak_liquid_fraction'))<=1)
    ref=rows('radial_refinement.csv')
    err=nums([x for x in ref if x['module']=='analytic_diffusion_sphere'],'max_mean_error')
    check('Analytic sphere benchmark refinement improves by >3 each doubling',np.all(err[:-1]/err[1:]>3))
    vals=nums([x for x in ref if x['module']=='moving_H2O2'],'final_liquid_fraction')
    check('Moving diffusion refinement contracts and 40/160-cell difference <1e-6',np.all(np.abs(np.diff(vals))[:-1]>np.abs(np.diff(vals))[1:]) and abs(vals[1]-vals[3])<1e-6)
    carb=rows('carbonate_cases.csv')
    check('Carbon inventory residual below 1e-10',np.max(nums(carb,'carbon_error'))<1e-10)
    zero=next(x for x in carb if x['water_scale']=='0' and x['oh_scale']=='0')
    check('Saved no-reaction carbonate control preserves pH and carbon form',float(zero['hydrated_fraction'])==0 and abs(float(zero['pH_final'])-float(zero['pH_initial']))<1e-12)
    cr=rows('carbonate_refinement.csv')
    check('Carbonate saved step refinement within 1e-6 pH',np.ptp(nums(cr,'pH_at_1s'))<1e-6)
    per=rows('peroxide_rate_audit.csv')
    check('Conditional peroxide H/O residuals below 1e-12',max(np.max(nums(per,'hydrogen_residual')),np.max(nums(per,'oxygen_residual')))<1e-12)
    check('Peroxide source discrepancy preserved as a failure',all(r['within_reading_band']=='False' for r in rows('peroxide_figure_audit.csv')) and not s['peroxide']['accepted_predictive_model'])
    ch=rows('charge_distribution.csv')
    check('Each theoretical charge distribution normalized',all(abs(nums([r for r in ch if r['radius_nm']==a],'probability').sum()-1)<1e-12 for a in {r['radius_nm'] for r in ch}))
    near=rows('near_contact.csv')
    check('Near-contact diagnostics stop at positive gaps and match quadrature',np.min(nums(near,'final_gap_um'))>=.67-1e-12 and np.max(nums(near,'quadrature_error_s'))<1e-12)
    sr=rows('surface_partition.csv')
    check('Surface partition bounds ordered and finite',all(0<=float(r['fraction_low'])<=float(r['fraction'])<=float(r['fraction_high'])<=1 for r in sr))
    check('All reported validation gaps remain explicit',not s['falling']['validated_for_smoke'] and not s['radial']['independent_uptake_validation'] and not s['radial']['independent_evaporation_validation'] and not s['carbonate']['independent_transient_validation'] and not s['charge']['coalescence_simulated'] and not surf['kinetic_validation'])
    with np.load(ROOT/'results/trajectories.npz',allow_pickle=False) as z:
        check('Saved trajectory arrays are finite and nonempty',len(z.files)>=10 and all(z[k].size>0 and np.all(np.isfinite(z[k])) for k in z.files))
    report=(ROOT/'report.html').read_text(encoding='utf-8')
    targets=re.findall(r'(?:href|src)="([^"]+)"',report)
    local=[x for x in targets if not re.match(r'(https?://|#)',x)]
    check('HTML local links and images resolve',all(x=='verification.json' or (ROOT/x).exists() for x in local))
    shared=list(ROOT.glob('*.py'))+list(ROOT.glob('*.md'))+list(ROOT.glob('*.json'))+list(ROOT.glob('*.txt'))
    check('No local user-machine paths in shareable text',all(not re.search(r'[A-Za-z]:[\\/]+Users[\\/]',p.read_text(encoding='utf-8')) for p in shared))
    current=snapshot();manifest=ROOT/'manifest.json'
    if '--refresh-manifest' in sys.argv:
        manifest.write_text(json.dumps(current,indent=2)+'\n',encoding='utf-8')
    check('Delivered files match SHA256 snapshot',manifest.exists() and json.loads(manifest.read_text())==current)
    return dict(status='passed',saved_result_checks=len(checks),new_unit_tests_recorded=34,
        note='Saved-result audits, not new experimental validation; unit tests were recorded in this batch.',
        manifest_excludes=['manifest.json','verification.json','__pycache__','*.pyc'],checks=checks)
if __name__=='__main__':
    try:out=run()
    except Exception as e:
        out=dict(status='failed',error=str(e),checks=checks)
        (ROOT/'verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
        raise
    (ROOT/'verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(f"Passed {out['saved_result_checks']} saved-result/package audits; 34 recorded unit tests.")
