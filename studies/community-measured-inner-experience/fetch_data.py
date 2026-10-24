"""Download the public original files; never commit this raw-data directory."""
import argparse,hashlib,json,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data-dir',type=Path,required=True);a=p.parse_args();a.data_dir.mkdir(parents=True,exist_ok=True)
    for source in json.loads((HERE/'sources.json').read_text(encoding='utf-8'))['files']:
        dest=a.data_dir/source['file']
        if not dest.exists():
            req=urllib.request.Request(source['url'],headers={'User-Agent':'Research reproduction'})
            with urllib.request.urlopen(req,timeout=90) as r:b=r.read()
            if hashlib.sha256(b).hexdigest()!=source['sha256']:raise ValueError('Changed remote source: '+source['file'])
            dest.write_bytes(b)
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=source['sha256']:raise ValueError('Changed local source: '+source['file'])
        print('Verified',source['file'])
