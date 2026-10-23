from pathlib import Path
import collections,csv,datetime,json,hashlib,argparse
import numpy as np
from scipy.stats import binomtest
from observations import file_hash,correct
from corpus_equations import response,transport

def save(path,obj):path.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def cluster_interval(values,clusters,seed=20261022,draws=2000):
    groups=collections.defaultdict(list)
    for v,c in zip(values,clusters):groups[c].append(v)
    if not groups:return [None,None]
    total=np.array([sum(v) for v in groups.values()],float);n=np.array([len(v) for v in groups.values()])
    rng=np.random.default_rng(seed);means=[]
    for _ in range(draws):
        ix=rng.integers(0,len(n),len(n));means.append(total[ix].sum()/n[ix].sum())
    return np.quantile(means,[.025,.975]).tolist()
def summarize_deli(rows):
    return {'transitions':len(rows),'groups':len({r['group_hash'] for r in rows}),
            'improved':sum(r['delta']>0 for r in rows),'worsened':sum(r['delta']<0 for r in rows),
            'unchanged_incorrect':sum(not r['before_correct'] and not r['after_correct'] for r in rows),
            'unchanged_correct':sum(r['before_correct'] and r['after_correct'] for r in rows),
            'mean_binary_accuracy_change':float(np.mean([r['delta'] for r in rows])) if rows else None,
            'group_bootstrap_interval':cluster_interval([r['delta'] for r in rows],[r['group_hash'] for r in rows])}
def paired_summary(rows,key):
    pairs=collections.defaultdict(dict)
    for r in rows:pairs[r['pair_hash']][r['removed']]=r
    pairs=list(pairs.values())
    def val(r):
        if '.' in key:a,b=key.split('.');return r[a][b]
        return r[key]
    x=[val(p[1]) for p in pairs];y=[val(p[0]) for p in pairs]
    diff=np.array(x)-np.array(y);a=int(sum(diff>0));b=int(sum(diff<0))
    return {'pairs':len(pairs),'removed_feature':sum(x),'control_feature':sum(y),'removed_only':a,'control_only':b,
            'paired_difference':float(diff.mean()),'cluster_bootstrap_interval':cluster_interval(diff,[p[1]['cluster'] for p in pairs]),
            'clusters':len({p[1]['cluster'] for p in pairs}),
            'discordant_pair_sign_p':float(binomtest(a,a+b).pvalue) if a+b else 1.}
def main(private,out):
    lock=json.loads((out/'audit_lock.json').read_text());audit=json.loads((out/'functional_audit.json').read_text(encoding='utf-8'))
    if file_hash(out/'functional_audit.json')!=lock['audit_sha256']:raise ValueError('Audit changed after lock')
    sel=json.loads((out/'selection.json').read_text())
    if file_hash(Path(__file__).with_name('PROTOCOL.md'))!=sel['protocol_sha256']:raise ValueError('Protocol changed')
    if [r['event_hash'] for r in audit['deli']]!=sel['deli_audit_ids'] or [r['conversation_hash'] for r in audit['cga']]!=sel['cga_audit_ids']:raise ValueError('Audit sample changed')
    for name,h in sel['blinded_inputs_sha256'].items():
        if file_hash(private/(name+'.json'))!=h:raise ValueError('Audit input changed')
    dr=json.loads((private/'deli_rows.json').read_text());cr=json.loads((private/'cga_rows.json').read_text())
    dh={r['event_hash']:r for r in dr};ch={r['conversation_hash']:r for r in cr}
    djoin=[dict(r,delta=dh[r['event_hash']]['delta'],before_correct=dh[r['event_hash']]['before_correct'],after_correct=dh[r['event_hash']]['after_correct']) for r in audit['deli']]
    cjoin=[dict(r,removed=ch[r['conversation_hash']]['removed']) for r in audit['cga']]
    save(out/'audited_outcomes.json',{'deli':djoin,'cga':cjoin})
    dgroups={name:summarize_deli([r for r in dr if fn(r)]) for name,fn in {
      'all_changed':lambda r:True,'candidate_uptake':lambda r:r['candidate'],'no_detected_proposal':lambda r:not r['candidate'],
      'candidate_complete_card_vocabulary':lambda r:r['candidate'] and r['full_card_vocabulary'],
      'candidate_within_10_events':lambda r:r['candidate'] and r['message_gap']<=10}.items()}
    keys=['primary.any','primary.reciprocal','primary.third','quotes.any','fourgram.any','cross_branch_placebo']
    cg={k:paired_summary(cr,k) for k in keys}
    # Record a matched-window placebo contrast, not primary.any versus third-only.
    cg['third_minus_cross_branch']={'removed':float(np.mean([r['primary']['third']-r['cross_branch_placebo'] for r in cr if r['removed']])),
                                    'control':float(np.mean([r['primary']['third']-r['cross_branch_placebo'] for r in cr if not r['removed']]))}
    results={'deli':dgroups,'cga':cg,'deli_audit_categories':dict(collections.Counter(r['category'] for r in djoin)),
             'cga_audit_categories':dict(collections.Counter(r['category'] for r in cjoin)),
             'causal_copying_identified':False,'girard_rivalry_validated':False,'corpus_pde_fitted_to_social_records':False}
    save(out/'observed_results.json',results)
    # Sufficient numerical records contain no text, aliases or original IDs.
    save(out/'deli_transitions.json',dr)
    clean=[]
    for r in cr:
        r=dict(r)
        for name in ['primary','quotes','fourgram']:r[name]={k:v for k,v in r[name].items() if k!='phrases'}
        clean.append(r)
    # Short, collision-checked hashes retain pairing/clustering without huge JSON.
    for key in ['conversation_hash','pair_hash','cluster']:
        full={r[key] for r in clean}
        if len({s[:16] for s in full})!=len(full):raise ValueError('Short hash collision')
    compact=[{'conversation_hash':r['conversation_hash'][:16],'pair_hash':r['pair_hash'][:16],'cluster_hash':r['cluster'][:16],
              'removed':r['removed'],**{'primary_'+k:r['primary'][k] for k in ['any','third','reciprocal']},
              'quotes_any':r['quotes']['any'],'fourgram_any':r['fourgram']['any'],'cross_branch_placebo':r['cross_branch_placebo']} for r in clean]
    with (out/'cga_features.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(compact[0]));w.writeheader();w.writerows(compact)
    grid=[]
    for n in [16,32,64,128]:
        x,s,A,M=transport(n=n,end=1.,source=False)
        _,_,AS,MS=transport(n=n,end=1.)
        grid.append({'n':n,'l2_error':float(np.sqrt(np.mean((s-np.exp(-.05)*np.sin(x-.4))**2))),
                     'source_integral_error':abs(MS-.5),'accumulated_input_error':abs(AS-1)})
    ts=[]
    for dt in [.1,.05,.025]:
        x,s,A,M=transport(n=16,end=1.,max_dt=dt,source=False)
        dx=2*np.pi/16
        exact=np.exp(-.05*4*np.sin(dx/2)**2/dx**2)*np.sin(x-.4*np.sin(dx)/dx)
        ts.append({'max_dt':dt,'semidiscrete_l2_error':float(np.sqrt(np.mean((s-exact)**2)))})
    save(out/'equation_results.json',{'tanh_at_minus_epsilon_for_epsilon_1':float(response(-1,'tanh')),
        'sharp_at_minus_1':float(response(-1,'sharp')),'smooth_exact_off_at_minus_1':float(response(-1,'smooth_off')),
        'grid_refinement':grid,'time_refinement':ts,'empirical_social_validation':False})
    save(out/'outcome_join.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'audit_sha256':lock['audit_sha256'],'protocol_sha256':sel['protocol_sha256']})
    print(json.dumps(results,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private',type=Path,required=True);a=p.parse_args();main(a.private,Path(__file__).with_name('results'))
