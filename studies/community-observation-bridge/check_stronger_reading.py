"""Explicit post-result sensitivity to a stricter observation hypothesis."""
import json
import numpy as np
from run_tests import ROOT, trial, sha

def main():
    original=json.loads((ROOT/'results/results.json').read_text(encoding='utf-8'))
    group=[r for r in original['runs'] if r['law']=='sharp' and r['distance']==.15
           and r['initial']['dc_P']>0 and r['initial']['dc_F']<0 and r['compatible']]
    assert [r['A0'] for r in group]==[.005,.02]
    assert group[0]['final']['contrast']*group[1]['final']['contrast']<0
    runs=[];states={}
    for n in [48,72]:
        r,z=trial('sharp',.15,.005,n=n,keep=True)
        r['refinement_label']='grid_refinement';runs.append(r);states[f'n{n}']=z
    r,z=trial('sharp',.15,.005,n=48,max_dt=runs[0]['dt']/2,keep=True)
    r['refinement_label']='effective_half_step';runs.append(r);states['n48_half']=z
    out=dict(status='exploratory_post_result_observation_sensitivity',
             amendment_sha256=sha(ROOT/'CONSTRAINT_AMENDMENT.md'),
             original_results_sha256=sha(ROOT/'results/results.json'),
             selected_existing_indices=[r['index'] for r in group],additional_runs=runs)
    (ROOT/'results/stronger_reading.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    np.savez_compressed(ROOT/'results/stronger_states.npz',**states)
    print(json.dumps([(r['n'],r['dt'],r['final']['contrast']) for r in runs]))

if __name__=='__main__':main()
