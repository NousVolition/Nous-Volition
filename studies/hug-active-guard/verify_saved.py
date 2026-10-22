"""Audit saved evidence, provenance and animation without rerunning the ensemble."""
from pathlib import Path
import base64,hashlib,json,math,re,struct
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parent

def audit():
    checks={}
    def check(name,condition):
        checks[name]=bool(condition)
        if not condition:raise AssertionError(name)
    def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
    def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    d=read('results.json');p=read('protocol.json');g=p['gates'];a=read('animation.json')
    check('frozen_protocol_unchanged',d['protocol']==p)
    check('pre_run_sources_unchanged',all(digest(ROOT/f)==h for f,h in read('freeze.json')['sha256'].items()))
    check('analysis_sources_unchanged',all(digest(ROOT/f)==h for f,h in d['source_sha256'].items()))
    expected=[dict(model=m,condition=c,start=s) for m in p['models'] for c in range(8) for s in range(2)]
    check('128_cases_in_declared_order',d['cases']==expected)
    check('per_start_diagnostics_complete',len(d['per_start'])==128 and all(all(z[k]==row[k] for k in row) for z,row in zip(d['per_start'],expected)))
    check('both_summaries_complete',len(d['summary'])==len(d['refined_summary'])==64)
    check('all_seven_numerical_gates',len(d['verification'])==7 and all(d['verification'].values()) and d['numerical_status']=='passed')
    check('saved_path_refinement',d['maximum_saved_path_difference']<g['saved_path_difference'])
    check('energy_balance',d['maximum_energy_residual']<g['energy_residual'])
    check('52_independent_segments',len(d['independent_controls'])==52 and max(x['error'] for x in d['independent_controls'])==d['maximum_independent_error']<g['independent_error'])
    check('six_attracting_cycles',len(d['cycles'])==6 and all(x['passed'] and x['shooting_error']<g['shooting_error'] and x['neutral_error']<g['floquet_neutral_error'] and x['largest_transverse_modulus']<g['floquet_transverse_max'] for x in d['cycles']))
    check('guard_bounds',-g['guard_bounds']<=d['guard_range'][0]<=d['guard_range'][1]<=1+g['guard_bounds'])
    check('classifications_agree',[(x['model'],x['condition'],x['status']) for x in d['summary']]==[(x['model'],x['condition'],x['status']) for x in d['refined_summary']])
    for x in d['summary']:
        if x['status']=='quiet':check('quiet_'+x['model'],max(x['half_amplitude_mm'],x['second_start_half_amplitude_mm'])<g['observable_half_amplitude_mm'])
        else:
            assert x['status'] in ['autonomous repeat confirmed','orbital repeat confirmed']
            assert x['repeat_error']<g['repeat_error'] and x['between_start_error']<g['history_error']
    check('repeat_and_start_gates_recomputed',True)
    check('animation_bound_to_results',a['source_sha256']==digest(ROOT/'results.json') and a['summary']==d['summary'] and a['cases']==expected)
    check('display_dimensions',a['shape']==[2,128,229,3] and a['sample_s']==.1 and a['clips'][0]['start']==0 and abs(a['clips'][1]['start']+a['duration_s']-p['horizon_s'])<1e-9)
    raw=base64.b64decode(a['values'],validate=True);values=[x[0] for x in struct.iter_unpack('<f',raw)]
    check('display_samples_finite',len(values)==math.prod(a['shape']) and all(math.isfinite(x) for x in values))
    check('display_guards_bounded',all(-1e-6<=x<=1+1e-6 for j,x in enumerate(values) if j%3))
    html=(ROOT/'player.html').read_text(encoding='utf-8');scripts=re.findall(r'<script(?:\s[^>]*)?>([\s\S]*?)</script>',html)
    check('embedded_animation_identical',json.loads(scripts[0])==a and 'GUARD_DATA_PLACEHOLDER' not in html)
    check('player_offline',not re.search(r'fetch\(|XMLHttpRequest|WebSocket',html))
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.links=[]
        def handle_starttag(self,tag,attrs):self.links.extend(v.split('#')[0] for k,v in attrs if k in ['href','src'] and v and not v.startswith(('http:','https:','#')))
    links=[]
    for filename in ['report.html','player.html']:
        parser=Links();parser.feed((ROOT/filename).read_text(encoding='utf-8'));links+=parser.links
    check('report_player_links_resolve',all((ROOT/link).exists() for link in links))
    if (ROOT/'provenance.json').exists():
        check('parent_dependencies_unchanged',all(digest(ROOT.parent/'dynamics-fractals-sims'/f)==h for f,h in read('provenance.json')['parent_sha256'].items()))
    if (ROOT/'manifest_sha256.json').exists():
        check('published_manifest',all(digest(ROOT/f)==h for f,h in read('manifest_sha256.json').items()))
    return checks

if __name__=='__main__':
    checks=audit();print(json.dumps(dict(passed=len(checks),checks=checks),indent=2))
