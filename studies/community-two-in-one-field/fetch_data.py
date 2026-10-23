"""Retrieve original public measurements at a pinned upstream commit.

Keep narratives and embeddings outside the publication folder. No credentials.
"""
import concurrent.futures as cf
import hashlib
import json
from pathlib import Path
import time
import urllib.request

COMMIT = 'e8005a84122e208f1607064d897763d6cbddf25a'
REPO = 'Lee-Memory-Cognition-Lab/thinkaloud_paper'
ROOT = Path(__file__).resolve().parent
RAW = ROOT.parents[1] / 'work' / 'twoinone-field-raw'

def get(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'NousVolition-research-audit'}), timeout=50) as r:
                return r.read()
        except Exception:
            if attempt == 3: raise
            time.sleep(attempt + 1)

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    tree = json.loads(get(f'https://api.github.com/repos/{REPO}/git/trees/{COMMIT}?recursive=1'))
    assert not tree.get('truncated')
    (RAW/'upstream_tree.json').write_text(json.dumps(tree,indent=2))
    files = [x for x in tree['tree'] if x['type']=='blob' and (x['path'].startswith(('behav_data/','embeddings/')) or x['path'] in ('README.md','participant_info.xlsx','thinkaloud_behavior_analysis.ipynb'))]
    def one(f):
        p=RAW/f['path'];p.parent.mkdir(parents=True,exist_ok=True)
        url=f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/{f["path"]}'
        b=p.read_bytes() if p.exists() else get(url)
        sha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        if sha!=f['sha']: raise ValueError('Upstream hash mismatch '+f['path'])
        if not p.exists(): p.write_bytes(b)
        return dict(path=f['path'],url=url,bytes=len(b),git_blob_sha1=sha,sha256=hashlib.sha256(b).hexdigest())
    with cf.ThreadPoolExecutor(max_workers=4) as pool: manifest=list(pool.map(one,files))
    out=dict(repository=REPO,commit=COMMIT,files=manifest)
    (ROOT/'source_manifest.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(files=len(manifest),bytes=sum(x['bytes'] for x in manifest),commit=COMMIT)))

if __name__=='__main__': main()
