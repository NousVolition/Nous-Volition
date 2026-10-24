"""Check saved artifacts and links; these checks are not empirical model validation."""
import ast,hashlib,json
from pathlib import Path
from html.parser import HTMLParser
P=Path(__file__).resolve().parent
class Links(HTMLParser):
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ('href','src') and v and '://' not in v and not v.startswith('#'):
                assert (P/v.split('#')[0]).is_file(),v
if __name__=='__main__':
    manifest=json.loads((P/'manifest_sha256.json').read_text())
    for name,h in manifest.items():
        p=P/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==h,name
        if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8'))
        if p.suffix=='.json':json.loads(p.read_text(encoding='utf-8'))
    Links().feed((P/'report.html').read_text(encoding='utf-8'))
    assert not list(P.glob('*.xlsx')) and not list(P.glob('*.qsf')),'Raw participant file unexpectedly staged'
    print(f'Checked {len(manifest)} artifact hashes, Python/JSON parsing, report links and raw-file exclusion.')
