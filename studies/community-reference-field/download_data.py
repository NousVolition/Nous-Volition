"""Fetch pinned public inputs locally; no credentials or execution of source code."""
import argparse,hashlib,json,urllib.request
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);a=p.parse_args();a.raw.mkdir(parents=True,exist_ok=True)
    manifest=Path(__file__).with_name('source_manifest.json');meta=json.loads(manifest.read_text())
    for r in meta['files']:
        target=a.raw/r['name']
        if not target.exists():
            with urllib.request.urlopen(r['url'],timeout=120) as response:target.write_bytes(response.read())
        b=target.read_bytes()
        if hashlib.sha256(b).hexdigest()!=r['sha256']:raise ValueError('Source hash mismatch: '+r['name'])
        print(r['name'],len(b),'verified')
    (a.raw/'source_manifest.json').write_bytes(manifest.read_bytes())
if __name__=='__main__':main()
