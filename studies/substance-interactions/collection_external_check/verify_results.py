"""Audit completed saved results independently of report prose."""
from pathlib import Path
import json,csv,hashlib
import numpy as np
from run_external import verify_model,measurements,jobs,nominal,aggregate,PROTOCOL
HERE=Path(__file__).resolve().parent;OUT=HERE/'results'
def main():
 verify_model();checks=[]
 def check(name,ok):
  checks.append(dict(name=name,passed=bool(ok)))
  if not ok:raise AssertionError(name)
 data=json.loads((OUT/'cases.json').read_text())
 with (OUT/'seeds.csv').open() as f:seeds=list(csv.DictReader(f))
 meta=json.loads((OUT/'run_metadata.json').read_text())
 check('all 47 prescribed row/scenario records',len(data)==47)
 check('all 188 seed records, including reused duplicate-size predictions',len(seeds)==188)
 check('184 unique simulations (duplicate physical inputs reused)',meta['unique_simulations']==184)
 check('901120 unique paths',meta['simulated_paths']==901120)
 expected={(r['row'],tag) for r,tag,p in jobs(measurements())}
 check('no added or dropped comparisons',{(d['row'],d['scenario']) for d in data}==expected)
 for r,tag,p in jobs(measurements()):
  batch=[s for s in seeds if int(s['row'])==r['row'] and s['scenario']==tag]
  check(f"row{r['row']} {tag} seeds",[int(s['seed']) for s in batch]==PROTOCOL['numerics']['seeds'])
  parsed=[]
  for s in batch:
   z={k:float(s[k]) for k in ['CE','censored_bound','Re','Pe']}
   z.update(samples=int(s['samples']),hits=int(s['hits']))
   assert 0<=z['hits']<=z['samples']
   assert 0<=z['CE']<=p['bmax']**2
   # Captures have inlet weights near unity but never get unit weight by assumption.
   assert z['CE'] <= p['bmax']**2*1.01*z['hits']/z['samples']+1e-12
   assert 0<=z['censored_bound']<=p['bmax']**2
   parsed.append(z)
  a=aggregate(parsed,p)
  saved=next(x for x in data if x['row']==r['row'] and x['scenario']==tag)
  check(f"row{r['row']} {tag} aggregate",all(
   a[k]==saved[k] if a[k] is None else np.isclose(a[k],saved[k],rtol=1e-12,atol=1e-16)
   for k in a))
 check('duplicate-size predictions identical',data[0]['mean_CE']==data[1]['mean_CE'])
 check('source model hashes preserved',meta['frozen_sha256']==PROTOCOL['source_sha256'])
 for name,want in meta['input_sha256'].items():
  check(name+' run-input hash',hashlib.sha256((HERE/name).read_bytes()).hexdigest()==want)
 check('large Re explicitly outside creeping flow',all(d['Re']>300 for d in data))
 result=dict(status='passed',checks=len(checks),items=checks,
  note='File/numerical bookkeeping checks passed; this does not imply physical validation or rare-event convergence.')
 (HERE/'verification.json').write_text(json.dumps(result,indent=2))
 print(f"{len(checks)} saved-result checks passed")
if __name__=='__main__':main()
