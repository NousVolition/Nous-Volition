"""Validate local report references and hashes; package this study plus its reference model."""
import hashlib,json,zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,unquote


class Report(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.images=0
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='a' and attrs.get('href'):self.links.append(attrs['href'])
        if tag=='img':
            assert attrs.get('alt'),'Missing figure alternative text'
            assert attrs.get('src','').startswith('data:image/'),'Expected embedded figure'
            self.images+=1


def main():
    root=Path(__file__).resolve().parent;checks=[]
    for filename in ('report.html','worked_models.html','junction_methods.html'):
        parser=Report();parser.feed((root/filename).read_text(encoding='utf-8'))
        for link in parser.links:
            u=urlsplit(link)
            if not u.scheme and u.path:assert (root/unquote(u.path)).is_file(),link
        checks.append(dict(file=filename,links=len(parser.links),embedded_figures=parser.images,status='passed'))
    for name in ('pendulum','index_bistability','structural','index_exercises','weak_oscillators','averaging','transient_memory','junction_orders'):
        record=json.loads((root/'data'/f'{name}.json').read_text())
        assert all(record['checks'].values()),name
    assert json.loads((root/'verification.json').read_text())['all_passed']
    for p in (root/'data').glob('*_protocol.json'):
        record=json.loads(p.read_text());name={'pendulum_protocol.json':'pendulum.py','index_bistability_protocol.json':'index_and_bistability.py',
          'structural_protocol.json':'structural_models.py','index_exercises_protocol.json':'index_exercises.py','weak_oscillators_protocol.json':'weak_oscillators.py','averaging_protocol.json':'averaging.py','transient_memory_protocol.json':'transient_memory.py','junction_orders_protocol.json':'junction_orders.py'}[p.name]
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==record['source_sha256'],name
        if 'tests_file' in record:
            assert hashlib.sha256((root/record['tests_file']).read_bytes()).hexdigest()==record['tests_sha256'],record['tests_file']
    (root/'delivery_checks.json').write_text(json.dumps(checks,indent=2))
    files=sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='manifest_sha256.json' and not any(s.startswith('reproduced') for s in p.relative_to(root).parts))
    manifest={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (root/'manifest_sha256.json').write_text(json.dumps(manifest,indent=2))
    archive=root.parent/'sims-recovery-entrainment.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files+[root/'manifest_sha256.json']:z.write(p,Path('studies/sims-recovery-entrainment')/p.relative_to(root))
        z.write(root.parent/'social-organization/model.py','studies/social-organization/model.py')
    print(json.dumps(dict(files=len(files)+1,archive=str(archive),size=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),checks=checks),indent=2))


if __name__=='__main__':main()
