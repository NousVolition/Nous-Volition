"""Post-protocol numerical coverage supplement; no retuning/evaluation selection."""
from pathlib import Path
import json
import numpy as np
from field import Field,Parameters
P=Path(__file__).parent;R=P/'results'
def main():
    seq=json.loads((R/'sequences.json').read_text());fit=json.loads((R/'data_results.json').read_text())['parameters']
    patterns={}
    for s in sorted(seq,key=lambda x:x['sequence']):
        if s['split']=='train' and len(s['y'])>=5:patterns.setdefault(tuple(s['y'][:4]),s)
    out=[];fields={}
    for pattern,s in sorted(patterns.items()):
        key=''.join(map(str,pattern));print('PATTERN',key,flush=True)
        f=Field(Parameters(kappa=fit['kappa'],baseline=fit['baseline']));r,z,_=f.run(pattern,initial_total=pattern[0],dt=.004)
        out.append(dict(pattern=list(pattern),sequence=s['sequence'],group=s['group'],split=s['split'],next_observed=s['y'][4],diagnostics=r))
        fields['input_'+key]=f.real(z)
    (R/'input_patterns.json').write_text(json.dumps(dict(status='Post-protocol training-only numerical coverage; no coefficients or primary analysis changed',runs=len(out),records=out),indent=2)+'\n')
    np.savez_compressed(R/'input_pattern_fields.npz',**fields)
    print(json.dumps(dict(runs=len(out),max_mass_error=max(abs(d['mass_error']) for r in out for d in r['diagnostics'])),indent=2))
if __name__=='__main__':main()
