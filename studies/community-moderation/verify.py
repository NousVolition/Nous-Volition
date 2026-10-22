from pathlib import Path
import json,csv,unittest,subprocess,sys,re,collections
from reproduce_aggregates import verify as aggregate_verify
ROOT=Path(__file__).resolve().parent
def main():
    b=json.loads((ROOT/'data/block_results.json').read_text());w=json.loads((ROOT/'data/wording_results.json').read_text());c=json.loads((ROOT/'data/cmv_history_coverage.json').read_text());audit=json.loads((ROOT/'data/meaning_audit.json').read_text());scores=list(csv.DictReader((ROOT/'data/topic_pair_scores.csv').open()))
    checks={}
    def ck(name,value):checks[name]=bool(value)
    ck('raw_log_accounting',b['log']['counts']['raw_events']==sum(b['log']['counts'][k] for k in ('ip_target_events','named_events','hidden_target_events')))
    ck('source_hash_matches_log',b['log']['sha256']==next(s['sha256'] for s in json.loads((ROOT/'sources.json').read_text())['files'] if s['file']=='blocks.json'))
    ck('source_bytes_matches_log',b['log']['bytes']==1670592624)
    ck('endpoint_outcomes_partition',w['removed']+w['comparison']==w['conversations'])
    ck('topic_pairs_are_balanced_by_design',w['removed']==w['comparison']==w['author_topic_pairs'])
    ck('topic_score_coverage',len(scores)==w['text_available_pairs'])
    ck('audit_keys_equal_top12',set(r['pair_hash'] for r in audit)==set(r['pair_hash'] for r in scores if r['audited']=='1'))
    ck('audit_count',len(audit)==12==w['audited_pairs'])
    ck('audit_classification_accounting',dict(collections.Counter(a['verdict'] for a in audit))==w['audit_verdicts'])
    ck('no_causal_wording_estimate',w['causal_wording_effect'] is None)
    ck('highest_score_matches',float(scores[0]['token_jaccard'])==w['max_topic_token_jaccard'])
    ck('topic_score_sorted',all(float(a['token_jaccard'])>=float(z['token_jaccard']) for a,z in zip(scores,scores[1:])))
    for window,s in b['windows'].items():
        f=s['finite_pairs'];ck(window+'_episode_partition',s['repeat']==s['infinite_second']+f['n'] and s['repeat']<=s['eligible'])
        ck(window+'_duration_partition',f['n']==f['longer']+f['shorter']+f['equal'])
        ck(window+'_sensitivities_are_subsets',max(s[k]['n'] for k in ('same_moderator','disruption_subset'))<=f['n'])
    for name,d in c['matched_designs'].items():
        ck(name+'_outcome_cells_partition',all(sum(z.values())==d['matched_pairs'] for z in d['field_counts']))
        ck(name+'_bounds_do_not_identify_sign',d['did_logical_bounds'][0]<0<d['did_logical_bounds'][1])
    ag=aggregate_verify();ck('all_nine_aggregate_summaries_reproduce',len(ag)==9 and all(ag.values()))
    tests=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT),'-p','test_analysis.py','-v'],capture_output=True,text=True)
    (ROOT/'data/test_log.txt').write_text(tests.stdout+tests.stderr);ck('unit_tests',tests.returncode==0)
    result={'checks':checks,'passed':sum(checks.values()),'total':len(checks),'unit_tests':19,'aggregate_reproductions':ag,'browser_preview':'Not performed: local-file browser navigation was blocked by policy. Static HTML and figure inspection are separate checks.'}
    (ROOT/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
    if not all(checks.values()):raise SystemExit(1)
if __name__=='__main__':main()
