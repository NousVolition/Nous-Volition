"""Download public source bytes. The large block log requires --include-blocks."""
from pathlib import Path
import argparse,json,hashlib,urllib.request
ROOT=Path(__file__).resolve().parent
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw-dir',type=Path,default=ROOT/'raw');ap.add_argument('--include-blocks',action='store_true');a=ap.parse_args();a.raw_dir.mkdir(parents=True,exist_ok=True)
    for s in json.loads((ROOT/'sources.json').read_text())['files']:
        if s['file']=='blocks.json' and not a.include_blocks:continue
        p=a.raw_dir/s['file']
        if not p.exists():
            temp=p.with_suffix(p.suffix+'.part')
            with urllib.request.urlopen(s['url'],timeout=90) as r,temp.open('wb') as f:
                while b:=r.read(1048576):f.write(b)
            if sha(temp)!=s['sha256']:raise RuntimeError('Downloaded source changed: '+s['file'])
            temp.replace(p)
        if sha(p)!=s['sha256']:raise RuntimeError('Source hash mismatch: '+s['file'])
        print('Verified',s['file'],s['bytes'],'bytes')
if __name__=='__main__':main()
