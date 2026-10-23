"""Download the exact public research files listed in sources.json; verify hashes."""
from pathlib import Path
import argparse,hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);a=p.parse_args();a.raw.mkdir(parents=True,exist_ok=True)
    for f in json.loads((ROOT/'sources.json').read_text(encoding='utf-8')):
        dest=a.raw/f['file']
        b=dest.read_bytes() if dest.exists() else urllib.request.urlopen(f['url'],timeout=60).read()
        if hashlib.sha256(b).hexdigest()!=f['sha256']:raise ValueError('Source changed: '+f['file'])
        dest.write_bytes(b)
    print('All primary-source hashes match')
if __name__=='__main__':main()
