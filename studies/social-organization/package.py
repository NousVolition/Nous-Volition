"""Check local report links, write hashes, and package user-facing deliverables."""
import hashlib,json,zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.images=0
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=='a' and d.get('href'):self.links.append(d['href'])
        if tag=='img':
            self.images+=1
            if not d.get('alt'):raise ValueError('Image without alternative text')


def main():
    root=Path(__file__).resolve().parent;checks=[]
    for name in ('report.html','methods.html','human_protocol.html'):
        f=root/name;parser=Links();parser.feed(f.read_text(encoding='utf-8'))
        local=[]
        for link in parser.links:
            u=urlsplit(link)
            if not u.scheme and u.path:
                target=(f.parent/unquote(u.path)).resolve()
                if not target.is_file():raise ValueError(f'Missing target: {link}')
                local.append(link)
        checks.append(dict(file=name,local_links=len(local),images=parser.images,status='passed'))
    (root/'delivery_checks.json').write_text(json.dumps(checks,indent=2))
    files=sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='manifest_sha256.json' and p!=root/'data/arrays.npz')
    manifest={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (root/'manifest_sha256.json').write_text(json.dumps(manifest,indent=2))
    archive=root.parent/'tribalism-study.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files+[root/'manifest_sha256.json']:
            z.write(p,Path('tribalism-study')/p.relative_to(root))
    print(json.dumps(dict(archive=str(archive),files=len(manifest)+1,size_mb=round(archive.stat().st_size/1e6,2),sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),link_checks=checks),indent=2))


if __name__=='__main__':main()
