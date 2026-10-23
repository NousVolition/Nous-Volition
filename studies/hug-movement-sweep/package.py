"""Audit local artifact links/syntax and refresh the package's byte manifest."""
import ast,hashlib,json,re
from pathlib import Path
from urllib.parse import unquote,urlsplit
ROOT=Path(__file__).resolve().parent
def main():
    files=sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    count=0
    for p in files:
        if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8-sig'),filename=p.name)
        if p.suffix=='.json':json.loads(p.read_text(encoding='utf-8'))
        if p.suffix in ('.md','.html'):
            text=p.read_text(encoding='utf-8');links=re.findall(r'\]\(([^)]+)\)',text) if p.suffix=='.md' else re.findall(r'(?:href|src)="([^"]+)"',text)
            for link in links:
                u=urlsplit(link)
                if u.scheme or not u.path:continue
                assert (p.parent/unquote(u.path)).exists(),(p.name,link);count+=1
    manifest={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.name!='manifest_sha256.json'}
    (ROOT/'manifest_sha256.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(files=len(manifest),local_links=count,syntax_and_json='passed')))
if __name__=='__main__':main()
