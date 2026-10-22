"""Saved scientific checks without re-integrating the trajectories."""
import base64,hashlib,json,math,re,struct
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parent
def audit():
    checks={}
    def check(name,ok):
        checks[name]=bool(ok)
        if not ok:raise AssertionError(name)
    def read(f):return json.loads((ROOT/f).read_text(encoding='utf-8'))
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    d=read('results.json');cfg=read('protocol.json');g=cfg['gates'];a=read('animation.json')
    check('protocol_unchanged',d['protocol']==cfg)
    check('frozen_sources_unchanged',all(sha(ROOT/f)==h for f,h in read('freeze.json')['sha256'].items()))
    check('results_sources_unchanged',d['source_sha256']==read('freeze.json')['sha256'])
    expected=[dict(model=m,arm=arm,condition=c,history=h) for m in cfg['models'] for arm in cfg['arms'] for c in range(1,8) for h in cfg['histories']]
    check('84_declared_cases',d['cases']==expected)
    check('complete_summaries_and_projection',len(d['summary'])==len(d['refined_summary'])==len(d['mechanical_projection'])==42)
    check('numerical_gates_pass',len(d['checks'])==10 and all(d['checks'].values()) and d['numerical_status']=='passed')
    check('path_refinement',d['maximum_path_difference']<g['full_path_refinement_error_scaled'])
    check('energy_with_switch_work',d['maximum_energy_residual']<g['energy_error_scaled'])
    check('42_independent_segments',len(d['independent_controls'])==42 and max(x['error_scaled'] for x in d['independent_controls'])==d['maximum_independent_error']<g['independent_solver_error_scaled'])
    check('continuous_states_both_switches',all(len(m['events'])==2 and all(e['before']==e['after'] for e in m['events']) for m in d['run_metadata']))
    check('guard_bounds',d['guard_range'][0]>=-g['guard_bounds'] and d['guard_range'][1]<=1+g['guard_bounds'])
    check('timing_refinement',all(x is not None and x<=cfg['orbit_period_s'] for x in d['confirmation_time_differences_s']))
    check('no_measurement_claim',d['physical_measurements']==0)
    check('historical_comparison_complete',len(d['comparison'])==7 and d['historical_results_sha256']==sha(ROOT/'../dynamics-fractals-sims/hug_sync_results.json'))
    for r in d['summary']:
        for stage in r['stages']:
            assert all(e is None and status=='assessing' for e,status in zip(stage['errors'][:23],stage['status'][:23]))
            for e,h,status in zip(stage['errors'][23:],stage['history_error'][23:],stage['status'][23:]):
                predicted='quiet' if stage['half_amplitude_mm']<=g['observable_half_amplitude_mm'] else 'synchronized' if min(e)<g['repeat_error_scaled'] and h<g['between_history_error_scaled'] else 'no_short_repeat'
                assert status==predicted
            last_nonlock=max((i for i,v in enumerate(stage['status']) if v!='synchronized'),default=-1)
            actual=stage['time_s'][last_nonlock+1] if last_nonlock+1<len(stage['status']) else None
            assert actual==stage['sustained_lock_s']
        if r['relock_confirmed_s'] is not None:assert r['loss_confirmed_s'] is not None and abs(r['confirmation_delay_after_restore_s']-(r['relock_confirmed_s']-741))<1e-8
    check('classification_and_confirmation_recomputed',True)
    check('animation_source_and_cases',a['source_sha256']==sha(ROOT/'results.json') and a['cases']==expected and a['comparison']==d['comparison'])
    raw=base64.b64decode(a['values'],validate=True);values=[x[0] for x in struct.iter_unpack('<f',raw)]
    check('animation_samples_finite',a['shape'][1:]==[84,286] and len(values)==math.prod(a['shape']) and all(math.isfinite(x) for x in values))
    check('ghost_samples_within_clip',all(abs(c['sample_start_s']+cfg['orbit_period_s']-c['start_s'])<1e-7 for c in a['clips']))
    for r,t in zip(d['summary'],a['timelines']):
        assert t['time']==[v for stage in r['stages'] for v in stage['time_s']]
        assert t['status']==[v for stage in r['stages'] for v in stage['status']]
        assert t['error']==[None if e is None else min(e) for stage in r['stages'] for e in stage['errors']]
    check('animation_statuses_are_saved_diagnostics',True)
    html=(ROOT/'player.html').read_text(encoding='utf-8');scripts=re.findall(r'<script(?:\s[^>]*)?>([\s\S]*?)</script>',html)
    check('embedded_animation_identical',json.loads(scripts[0])==a and 'SYNC_GUARD_DATA_PLACEHOLDER' not in html)
    check('offline_player',not re.search(r'fetch\(|XMLHttpRequest|WebSocket',html))
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.links=[]
        def handle_starttag(self,tag,attrs):self.links.extend(v.split('#')[0] for k,v in attrs if k in ['href','src'] and v and not v.startswith(('https:','http:','#')))
    links=[]
    for name in ['report.html','player.html']:
        parser=Links();parser.feed((ROOT/name).read_text(encoding='utf-8'));links+=parser.links
    check('report_links_resolve',all((ROOT/f).exists() for f in links))
    if (ROOT/'manifest_sha256.json').exists():check('package_hashes',all(sha(ROOT/f)==h for f,h in read('manifest_sha256.json').items()))
    return checks
if __name__=='__main__':
    x=audit();print(json.dumps(dict(passed=len(x),checks=x),indent=2))
