from pathlib import Path
import zipfile,json,collections,csv,gzip,argparse,hashlib
from analysis_core import tokens,available,jaccard,digest,did_bounds
ROOT=Path(__file__).resolve().parent

def load_endpoints(raw):
    expected=next(s['sha256'] for s in json.loads((ROOT/'sources.json').read_text())['files'] if s['file']=='cga_cmv.zip')
    if hashlib.sha256((raw/'cga_cmv.zip').read_bytes()).hexdigest()!=expected:raise ValueError('CGA source hash mismatch')
    with zipfile.ZipFile(raw/'cga_cmv.zip') as z:
        pre='conversations-gone-awry-cmv-corpus/';cv=json.loads(z.read(pre+'conversations.json'));by=collections.defaultdict(list)
        with z.open(pre+'utterances.jsonl') as f:
            for line in f:
                r=json.loads(line);r['meta'].pop('parsed',None);by[r['conversation_id']].append(r)
    end=[]
    for c,rs in by.items():
        parents={r['reply-to'] for r in rs};leaves=[r for r in rs if r['id'] not in parents]
        if len(leaves)!=1:raise ValueError('Ambiguous conversation endpoint')
        r=dict(leaves[0]);r['removed']=bool(cv[c]['meta']['has_removed_comment']);r['pair_id']=cv[c]['meta']['pair_id'];end.append(r)
    return end,by

def pairkey(a,b):return digest('\0'.join(sorted((a['id'],b['id']))))
def analyze(raw,out):
    end,contexts=load_endpoints(raw);by={r['conversation_id']:r for r in end};pairs=[]
    for a in end:
        b=by[a['pair_id']]
        assert by[b['pair_id']]['id']==a['id'] and a['removed']!=b['removed']
        if a['conversation_id']<b['conversation_id'] and available(a['text']) and available(b['text']):
            pairs.append({'a':a,'b':b,'jaccard':jaccard(a['text'],b['text']),'hash':pairkey(a,b)})
    pairs.sort(key=lambda r:(-r['jaccard'],r['hash']));audit=pairs[:12]
    near=[];idx=collections.defaultdict(set);sets={r['id']:set(tokens(r['text'])) for r in end};lut={r['id']:r for r in end};groups=collections.defaultdict(list)
    for a in sorted(end,key=lambda r:r['id']):
        if not available(a['text']):continue
        groups[a['text']].append(a)
        if len(tokens(a['text']))<8:continue
        ts=sets[a['id']];candidates=set().union(*(idx[t] for t in ts))
        for bid in candidates:
            bs=sets[bid]
            if min(len(ts),len(bs))<.8*max(len(ts),len(bs)):continue
            j=len(ts&bs)/len(ts|bs)
            if j>=.8 and a['text']!=lut[bid]['text']:near.append(pairkey(a,lut[bid]))
        for t in ts:idx[t].add(a['id'])
    notes=json.loads((ROOT/'data/meaning_audit.json').read_text())
    assert {r['pair_hash'] for r in notes}=={r['hash'] for r in audit}
    out.mkdir(parents=True,exist_ok=True)
    with (out/'topic_pair_scores.csv').open('w',newline='') as f:
        wr=csv.writer(f);wr.writerow(['pair_hash','token_jaccard','audited'])
        for i,r in enumerate(pairs):wr.writerow([r['hash'],r['jaccard'],int(i<12)])
    # Local review can reconstruct full texts and preceding context from pinned data.
    local=[dict(r,context_a=contexts[r['a']['conversation_id']],context_b=contexts[r['b']['conversation_id']]) for r in audit]
    (raw/'audit_context_private.json').write_text(json.dumps(local),encoding='utf-8')
    result={'conversations':len(end),'removed':sum(r['removed'] for r in end),'comparison':sum(not r['removed'] for r in end),'unavailable_endpoint_texts':sum(not available(r['text']) for r in end),'author_topic_pairs':len(end)//2,'text_available_pairs':len(pairs),'max_topic_token_jaccard':pairs[0]['jaccard'],'topic_pairs_jaccard_ge_08':sum(r['jaccard']>=.8 for r in pairs),'exact_duplicate_endpoint_groups':sum(len(g)>1 for g in groups.values()),'changed_endpoint_pairs_jaccard_ge_08_min8tokens':len(near),'audited_pairs':len(audit),'audit_verdicts':dict(collections.Counter(n['verdict'] for n in notes)),'causal_wording_effect':None,'reason':'No accepted same-meaning contrasts in this audit. Retrieval is not exhaustive semantic matching; neither absence of wording effects nor fair moderation is established.'}
    (out/'wording_results.json').write_text(json.dumps(result,indent=2))
    # Released CMV matching IDs do not include subsequent removal outcomes.
    def load(n):
        data=(raw/(n+'.json.gz')).read_bytes();expected=next(s['sha256'] for s in json.loads((ROOT/'sources.json').read_text())['files'] if s['file']==n+'.json.gz')
        if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('CMV source hash mismatch: '+n)
        return [json.loads(l) for l in gzip.decompress(data).splitlines()]
    first=load('first_removals');both=load('first_and_second_removals');removed={r['comment_id'] for r in both};labels={r['id']:int(r['removed']) for r in end}
    conflicts={i for i in removed if labels.get(i)==0};assert not conflicts
    known=dict(labels);known.update({i:1 for i in removed});history={'first_removal_records':len(first),'first_second_records':len(both),'users_with_recorded_second_removal':sum(n==2 for n in collections.Counter(r['author_id'] for r in both).values()),'outcome_conflicts':len(conflicts),'matched_designs':{}}
    fields=['treatent before removal comment id','treatment after removal comment id','control before virtual removal comment id','control after virtual removal comment id']
    for name in ('delayed_feedback_setup_non_treatment_trees','delayed_feedback_setup_treatment_trees'):
        rows=load(name);cells=[[known.get(r[k]) for k in fields] for r in rows]
        history['matched_designs'][name]={'matched_pairs':len(rows),'complete_outcome_quadruples':sum(all(v is not None for v in r) for r in cells),'field_counts':[{str(k):sum(r[i]==k for r in cells) for k in (0,1,None)} for i in range(4)],'did_logical_bounds':did_bounds(cells)}
    (out/'cmv_history_coverage.json').write_text(json.dumps(history,indent=2));print(json.dumps({'wording':result,'history':history},indent=2))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--raw-dir',type=Path,required=True);ap.add_argument('--out-dir',type=Path,default=ROOT/'data');a=ap.parse_args();analyze(a.raw_dir,a.out_dir)
