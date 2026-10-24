"""Download pinned primary sources, verify bytes, and preserve originals."""
from pathlib import Path
import argparse,hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);a=p.parse_args();a.raw.mkdir(parents=True,exist_ok=True)
    for s in json.loads((ROOT/'sources.json').read_text(encoding='utf-8')):
        f=a.raw/s['file']
        b=f.read_bytes() if f.exists() else urllib.request.urlopen(s['url'],timeout=60).read()
        if hashlib.sha256(b).hexdigest()!=s['sha256']:raise ValueError('Hash mismatch: '+s['file'])
        f.write_bytes(b)
    print('Source hashes verified')
if __name__=='__main__':main()
