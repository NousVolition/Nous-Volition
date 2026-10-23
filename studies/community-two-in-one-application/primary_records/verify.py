"""Offline checks for the published source audit; no invented empirical fit."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
r=json.loads((ROOT/'results.json').read_text(encoding='utf-8'))
a=json.loads((ROOT/'annotations.json').read_text(encoding='utf-8'))
s=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))
checks={
 'sample_count_and_training_split':r['des_samples_indexed']==39 and r['training_samples']==2 and r['post_training_samples']==37,
 'unique_samples':len({x['sample'] for x in r['inventory']})==39,
 'unknown_original_times_preserved':all(x['original_thought_time'] is None for x in r['inventory']),
 'annotation_scope':len(a)==r['fully_read_selected_episodes']==5 and all(x['sample'] in {y['sample'] for y in r['inventory']} for x in a),
 'no_predictive_score_or_form_classification':r['prediction_score'] is None and not r['full_empirical_fit_completed'] and r['forms_classified']==0,
 'wave_denominators_preserved':r['workbook']['GISQ_Full']['waves']=={'t1':23,'t2':22,'t3':21} and r['workbook']['GISQ_Full']['keyed_rows']==66,
 'exact_solver_unchanged':hashlib.sha256((ROOT.parent/'corpus_field.py').read_bytes()).hexdigest()==r['corpus_solver_sha256']=='00b50a93ae413d46109327ccf0c08e8e07d00028313eaa0da87d765e58705f35',
 'plan_unchanged':hashlib.sha256((ROOT.parent/'PRIMARY_RECORD_PLAN.md').read_bytes()).hexdigest()==r['plan_sha256'],
 'source_provenance':len(s)==r['source_files_verified']==22 and all(len(x['sha256'])==64 and not x['redistributed'] for x in s),
 'original_locator_used':next(x for x in r['inventory'] if x['sample']=='8.5')['page']==14 and next(x for x in r['inventory'] if x['sample']=='8.5')['interview_offset']=='35:12'
}
assert all(checks.values()),checks
print(json.dumps(dict(passed=True,checks=checks),indent=2))
