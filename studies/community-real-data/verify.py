"""Independent checks against raw records and stored results."""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,csv,hashlib,json,math
import numpy as np
from scipy.stats import hypergeom
ROOT=Path(__file__).resolve().parent

def main(raw):
    checks=[]
    def check(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(name)
    def rows(p,sep=','):
        with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f,delimiter=sep))
    r=json.loads((ROOT/'data/results.json').read_text());f=r['flow'];p=r['paired_labels'];h=r['history']
    for src in json.loads((ROOT/'sources.json').read_text())['files']:
        check('source_hash_'+src['id'],hashlib.sha256((raw/src['file']).read_bytes()).hexdigest()==src['sha256'])
    c=rows(raw/'content.tsv','\t');t=rows(raw/'toxicity.tsv','\t')
    cp=defaultdict(set);tx=defaultdict(set)
    for v in c:cp[v['toxic'],v['neutral']].add(v['match'])
    for v in t:tx[v['comment']].add(v['toxic'])
    check('content_conflicts',sum(len(v)>1 for v in cp.values())==f['conflicting_pair_keys'])
    check('text_conflicts',sum(len(v)>1 for v in tx.values())==f['conflicting_comment_keys'])
    check('content_partition',f['changed_match']+f['changed_mismatch']+f['identical_pairs']+f['conflicting_pair_keys']==len(cp))
    independent={}
    candidate_hashes=[]
    for (a,b),v in cp.items():
        if v!={'True'} or a==b:continue
        key=hashlib.sha256((a+'\0'+b).encode()).hexdigest();candidate_hashes.append(key)
        if len(tx.get(a,set()))!=1 or len(tx.get(b,set()))!=1:continue
        independent[key]=(int(tx[a]=={'True'}),int(tx[b]=={'True'}))
    delivered=rows(ROOT/'data/paired_labels.csv')
    check('all_paired_records_exact', {x['pair_id']:(int(x['original_label']),int(x['rewrite_label'])) for x in delivered}==independent)
    tally=Counter(independent.values())
    check('four_cells_and_total',list([tally[0,0],tally[0,1],tally[1,0],tally[1,1]])==[p['both_nonoffensive'],p['nonoffensive_to_offensive'],p['offensive_to_nonoffensive'],p['both_offensive']] and sum(tally.values())==p['n'])
    check('paired_reduction_arithmetic',abs(sum(b-a for a,b in independent.values())/len(independent)-p['rewrite_minus_original']['estimate'])<1e-14)
    audit=rows(ROOT/'data/meaning_audit.csv')
    check('audit_sampling', [x['pair_id'] for x in audit]==sorted(candidate_hashes)[:24])
    check('audit_verdict_counts',dict(Counter(x['core_content_review'] for x in audit))==r['meaning_audit']['verdicts'])
    check('exact_published_endpoint',h['table']==[[12,88],[2,98]])
    probs=[float(hypergeom.pmf(x,200,14,100)) for x in range(15)]
    exact=sum(v for v in probs if v<=probs[12]+1e-14)
    check('fisher_independent_enumeration',abs(exact-h['fisher_two_sided_p'])<1e-13)
    check('history_effect_arithmetic',abs(h['risk_difference']-.1)<1e-14 and h['risk_ratio']==6)
    daily=rows(raw/'WikipediaExp.csv');tot=Counter()
    for x in daily:tot[x['experiment']]+=int(x['awardreceived'])
    check('group_not_individual_rows',len(daily)==242 and Counter(x['experiment'] for x in daily)=={'0':121,'1':121})
    check('event_not_person_totals',tot=={'0':3,'1':14} and h['table'][0][0]==12 and h['table'][1][0]==2)
    check('control_event_day_distinguished_from_treated',min(int(x['timestamp']) for x in daily if x['experiment']=='0' and int(x['awardreceived']))==7)
    check('protocol_hash',hashlib.sha256((ROOT/'data/protocol.json').read_bytes()).hexdigest()==r['protocol_sha256'])
    check('provenance_hash',hashlib.sha256((ROOT/'sources.json').read_bytes()).hexdigest()==r['sources_sha256'])
    result=dict(status='passed',checks=len(checks),check_names=checks,unit_tests=13,
        empirical_scope='Released human labels; exact published randomized endpoint; group-day chronology. No original human data collection.',
        semantic_validation='Single AI audit, not new independent human validation.')
    (ROOT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--raw-dir',type=Path,default=ROOT/'raw');args=parser.parse_args();main(args.raw_dir)
