"""Independent checks of archived results; no private raw records needed."""
import csv,hashlib,json
from pathlib import Path
import numpy as np
from corpus_field import Field,Parameters
from run_equations import difference

ROOT=Path(__file__).resolve().parent;R=ROOT/'results'

def main():
    checks=[]
    def check(name,ok):
        checks.append(dict(check=name,passed=bool(ok)))
        if not ok:raise AssertionError(name)
    e=json.loads((R/'equation_results.json').read_text());d=json.loads((R/'data_audit.json').read_text())
    check('Unchanged solver hash',hashlib.sha256((ROOT/'corpus_field.py').read_bytes()).hexdigest()==e['solver_sha256'])
    check('Frozen protocol hash',hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest()==e['protocol_sha256'])
    z=np.load(R/'final_fields.npz')
    check('Eighteen completed coupled runs',len(z.files)==len(e['runs'])==18)
    for name,v in e['runs'].items():
        p=Parameters(**v['parameters']);f=Field(p);rows=v['rows']
        A=0.;mass=0.
        for row,U in zip(rows,e['inputs']):
            dt=e['interval'];mass+=p.kappa*(A*dt+.5*p.gamma*(U-p.baseline)*dt**2);A+=p.gamma*(U-p.baseline)*dt
            check(name+' analytic accumulated input at '+str(row['time']),abs(A-row['A'])<1e-12)
            check(name+' analytic total at '+str(row['time']),abs(mass-row['mass'])<1e-12)
        actual=f.diagnostics(z[name],A)
        for k in ('mass','energy','velocity_rms','divergence_rms','pressure_rms','stress_rms'):
            check(name+' saved '+k,abs(actual[k]-rows[-1][k])<1e-12)
        check(name+' finite state',np.isfinite(z[name]).all())
        check(name+' divergence',actual['divergence_rms']<1e-12)
    for r in e['refinement']:
        law=r['law'];x=difference(z[law+'_24'],z[law+'_48']);y=difference(z[law+'_48'],z[law+'_72'])
        check(law+' saved grid difference',abs(x-r['grid24_48'])<1e-14 and abs(y-r['grid48_72'])<1e-14)
        check(law+' decreasing grid difference',y<x)
        check(law+' full state scaling identity',difference(z[law+'_24'],z[law+'_scaled_memory'])<1e-12)
    coverage=list(csv.DictReader((R/'record_coverage.csv').open()))
    check('All participants',len(coverage)==d['participants']==118)
    for k in ['sentences','thoughts','embedding_rows','populated_extra_cells']:
        check('Coverage total '+k,sum(int(r[k]) for r in coverage)==d[k])
    check('Thought count and embedding alignment',d['thoughts']==d['embedding_rows']==6434)
    check('No empirical fit claimed',d['full_two_in_one_fit_performed'] is False)
    check('Known source anomalies retained',d['populated_extra_cells']==8 and d['source_files_with_extra_columns']==2)
    out=dict(passed=all(x['passed'] for x in checks),count=len(checks),checks=checks)
    (R/'verification.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(passed=out['passed'],checks=out['count'])))

if __name__=='__main__':main()
