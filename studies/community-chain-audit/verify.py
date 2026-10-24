"""Check this release's evidence, source pin and report links offline."""
from pathlib import Path
import json,hashlib,ast,csv
from html.parser import HTMLParser
P=Path(__file__).resolve().parent
class Links(HTMLParser):
 def handle_starttag(self,tag,attrs):
  for k,v in attrs:
   if k in ('href','src') and v and '://' not in v and not v.startswith('#'):
    assert (P/v.split('#')[0]).is_file(),v
def main():
 manifest=json.loads((P/'manifest_sha256.json').read_text())
 for name,h in manifest.items():
  p=P/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==h,name
  if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8'))
  if p.suffix=='.json':json.loads(p.read_text(encoding='utf-8'))
 assert hashlib.sha256((P/'legacy_field.py').read_bytes()).hexdigest()=='00b50a93ae413d46109327ccf0c08e8e07d00028313eaa0da87d765e58705f35'
 b=json.loads((P/'baseline_test_runs.json').read_text());assert sum(x['tests'] for x in b)==443 and all(x['returncode']==0 for x in b)
 r=json.loads((P/'results.json').read_text());assert r['unit_tests']==17 and r['full_coupled_runs']==18
 assert all(x['grid48_72']<x['grid24_48'] for x in r['refinement'])
 assert r['max_mass_error']<1e-12 and r['max_divergence']<1e-12
 m=json.loads((P/'measurement_rerun.json').read_text());assert all(x['byte_equal'] for x in m['comparisons'])
 s=json.loads((P/'source_versions.json').read_text());assert s['miro_total_indexed']==1747 and s['miro_svg_ids']==1745 and len(s['pdf_pages_visually_inspected'])==37
 edges=list(csv.DictReader((P/'connection_ledger.csv').open(encoding='utf-8')))
 assert len(edges)==33 and len({x['id'] for x in edges})==33
 assert all(x['source_excerpt'] and len(x['source_sha256'])==64 and x['remaining_test'] for x in edges)
 assert json.loads((P/'connection_audit_checks.json').read_text())['all_source_anchors_found'] is True
 Links().feed((P/'report.html').read_text(encoding='utf-8'))
 print(json.dumps(dict(files=len(manifest),source_pin=True,baseline_tests=443,new_tests=17,measurement_rerun=True,report_links=True)))
if __name__=='__main__':main()
