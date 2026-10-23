"""Independent arithmetic and provenance checks, without downloading raw text."""
from pathlib import Path
import json,collections,hashlib,math
from scipy.stats import binomtest
from observations import read_public_cga
p=Path(__file__).parent;r=p/'results';count=0
def check(condition):
    global count
    assert condition
    count+=1
def read(n):return json.loads((r/n).read_text(encoding='utf-8'))
res=read('observed_results.json');d=read('deli_transitions.json');c=read_public_cga(r/'cga_features.csv');a=read('functional_audit.json');s=read('selection.json')
check(hashlib.sha256((r/'functional_audit.json').read_bytes()).hexdigest()==read('audit_lock.json')['audit_sha256'])
check(hashlib.sha256((p/'PROTOCOL.md').read_bytes()).hexdigest()==s['protocol_sha256'])
check([x['event_hash'] for x in a['deli']]==s['deli_audit_ids']);check([x['conversation_hash'] for x in a['cga']]==s['cga_audit_ids'])
check(len(d)==538);check(len(c)==2*2259)
for name,rows in [('all_changed',d),('candidate_uptake',[x for x in d if x['candidate']]),('no_detected_proposal',[x for x in d if not x['candidate']]),('candidate_complete_card_vocabulary',[x for x in d if x['candidate'] and x['full_card_vocabulary']]),('candidate_within_10_events',[x for x in d if x['candidate'] and x['message_gap']<=10])]:
    z=res['deli'][name]
    check(len(rows)==z['transitions']);check(len({x['group_hash'] for x in rows})==z['groups'])
    check(sum(x['delta']>0 for x in rows)==z['improved']);check(sum(x['delta']<0 for x in rows)==z['worsened'])
    check(sum(x['delta'] for x in rows)/len(rows)==z['mean_binary_accuracy_change'])
    check(sum(x['delta']==0 for x in rows)==z['unchanged_incorrect']+z['unchanged_correct'])
pairs=collections.defaultdict(dict)
for x in c:pairs[x['pair_hash']][x['removed']]=x
for key,z in res['cga'].items():
    if key=='third_minus_cross_branch':continue
    def v(x):
        if '.' in key:a,b=key.split('.');return x[a][b]
        return x[key]
    cells=collections.Counter((v(x[1]),v(x[0])) for x in pairs.values())
    check(len(pairs)==z['pairs']);check(cells[1,0]==z['removed_only']);check(cells[0,1]==z['control_only'])
    check(cells[1,0]+cells[1,1]==z['removed_feature']);check(cells[0,1]+cells[1,1]==z['control_feature'])
    check(math.isclose((cells[1,0]-cells[0,1])/len(pairs),z['paired_difference']))
    check(math.isclose(binomtest(cells[1,0],cells[1,0]+cells[0,1]).pvalue,z['discordant_pair_sign_p']))
eq=read('equation_results.json');check(abs(eq['tanh_at_minus_epsilon_for_epsilon_1']+.11920292202211755)<1e-14)
for x in eq['grid_refinement']:check(x['source_integral_error']<1e-11)
g=eq['grid_refinement'];check(all(g[i]['l2_error']/g[i+1]['l2_error']>3.8 for i in range(len(g)-1)))
t=eq['time_refinement'];check(all(t[i]['semidiscrete_l2_error']/t[i+1]['semidiscrete_l2_error']>15 for i in range(len(t)-1)))
check(not res['corpus_pde_fitted_to_social_records']);check(not res['girard_rivalry_validated'])
print(json.dumps({'passed':count,'all_passed':True}))
