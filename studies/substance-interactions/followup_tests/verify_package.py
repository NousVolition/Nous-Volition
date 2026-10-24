"""Verify saved results, provenance, syntax and publication integrity.
Use --write-manifest only after an intentional regeneration or documentation edit.
"""
from pathlib import Path
import argparse,ast,csv,hashlib,json,re
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import numpy as np

ROOT=Path(__file__).resolve().parent
def readj(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def rows(name):
    with (ROOT/'results'/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files():return sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.zip'})
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):self.links.extend(v for k,v in attrs if k in {'href','src'} and v)
def run(write=False):
    checks=[]
    def check(name,test):
        if not test:raise AssertionError(name)
        checks.append(name)
    for name,digest in readj('results/input_hashes.json').items():check('Numerical input hash: '+name,sha(ROOT/name)==digest)
    log=(ROOT/'test_log.txt').read_text(encoding='utf-8')
    check('29 completed unit tests recorded',bool(re.search(r'Ran 29 tests.*\n\s*\nOK',log,re.S)))
    s=readj('results/summary.json');f=rows('fog_cases.csv');pp=rows('particle_seeds.csv');measure=rows('published_data_comparison.csv')
    check('Case counts',len(f)==108 and len(pp)==42 and len(measure)==18 and len(rows('fog_refinement.csv'))==12 and len(rows('particle_refinement.csv'))==36)
    check('Conservation residuals',max(float(r['water_error']) for r in f)<1e-6 and max(float(r['solute_error']) for r in f)<1e-12)
    check('Refinement recorded at required steps',set(float(r['dt_s']) for r in rows('particle_refinement.csv'))=={.002,.001,.0005})
    with np.load(ROOT/'results/trajectories.npz') as data:
        for row in f:
            state=data[row['case']+'_state'];a=float(row['radius']);tt=data[row['case']+'_time']
            check('Saved fog states: '+row['case'],np.max(abs(state[0]**1.5+state[1]-1))<1e-6 and np.max(abs(state[3:7]+state[7:11]-1))<1e-12 and np.all(np.diff(tt)>0) and a*np.sqrt(state[0].min())>=2e-6-1e-12)
        for row in pp:
            key=row['case']+'_seed'+row['seed'];pos=data[key+'_final'];stop=data[key+'_stops'];rr=np.linalg.norm(pos,axis=1)
            check('Saved particle ensemble: '+key,pos.shape==(512,3) and rr.min()>=2e-5-1e-14 and abs(np.isfinite(stop).mean()-float(row['stopped_fraction']))<1e-14 and abs(rr.mean()*1e6-float(row['mean_separation_um']))<1e-10)
        for seed in range(101,107):
            check('Matched neutral/monopole control: '+str(seed),np.array_equal(data[f'neutral_seed{seed}_final'],data[f'charged_neutral_monopole_seed{seed}_final']))
    check('All central measurements exceed stated sensitivity envelope',all(float(r['measured_CE'])>float(r['sensitivity_max']) for r in measure))
    check('Comparison ratios reproduce table',all(abs(float(r['measured_CE'])/float(r['brownian_only_CE'])-float(r['measured_over_prediction']))<1e-10 for r in measure))
    check('No silently extrapolated collision result',all(float(r['final_separation_um'])>=20-1e-7 for r in rows('particle_deterministic.csv')))
    for p in files():
        if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8-sig'))
        if p.suffix=='.json':json.loads(p.read_text(encoding='utf-8-sig'))
    check('All Python and JSON parse',True)
    # Cross-study links are known repository destinations; available in repo,
    # while this local output package can stand alone beside earlier outputs.
    repo_links={'../README.md','../../../README.md','../../social-organization/README.md','../../sims-recovery-entrainment/README.md'}
    count=0
    for p in files():
        if p.suffix not in {'.md','.html'}:continue
        txt=p.read_text(encoding='utf-8')
        if p.suffix=='.html':parser=Links();parser.feed(txt);links=parser.links
        else:links=re.findall(r'\]\(([^\s)]+)\)',txt)
        for href in links:
            u=urlsplit(href)
            if u.scheme or u.netloc or not u.path:continue
            if href in repo_links:continue
            if href=='manifest.json' and write:continue
            target=p.parent/unquote(u.path)
            # In the published tree this is studies/community-*. Locally the
            # output packages are siblings named community_*. Verify the file;
            # do not whitelist a link merely because its name looks familiar.
            if not target.exists() and u.path.startswith('../../community-'):
                parts=Path(unquote(u.path)).parts
                target=ROOT.parent/parts[2].replace('-','_')/Path(*parts[3:])
            check('Local link: '+href,target.exists());count+=1
    record=dict(status='passed',unit_tests_passed=29,saved_result_and_integrity_assertions=len(checks),local_links=count,
        measured_data_verdict=s['measurements']['verdict'],figures='Three scientific figures visually inspected; no empirical validation of the new fog or isolated-force trajectories claimed.',
        baseline_copy='baseline_model.py retains the original pilot code; new work is in followup_model.py.',community='COMMUNITY.md is a proposed family-role guide, not a newly run human-behavior experiment.')
    if write:
        (ROOT/'verification.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        (ROOT/'manifest.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():sha(p) for p in files() if p.name!='manifest.json'},indent=2)+'\n',encoding='utf-8')
    else:
        manifest=readj('manifest.json')
        for name,digest in manifest.items():check('Package SHA256: '+name,sha(ROOT/name)==digest)
        check('Manifest covers all files',set(manifest)=={p.relative_to(ROOT).as_posix() for p in files() if p.name!='manifest.json'})
    print(json.dumps(record,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--write-manifest',action='store_true');args=parser.parse_args();run(args.write_manifest)
