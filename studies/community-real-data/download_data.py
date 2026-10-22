"""Fetch pinned public inputs, verifying every byte against sources.json."""
from pathlib import Path
import argparse, hashlib, json, urllib.request

ROOT=Path(__file__).resolve().parent
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--raw-dir',type=Path,default=ROOT/'raw')
    args=parser.parse_args();args.raw_dir.mkdir(parents=True,exist_ok=True)
    for src in json.loads((ROOT/'sources.json').read_text())['files']:
        path=args.raw_dir/src['file']
        if path.exists():
            data=path.read_bytes()
        else:
            data=urllib.request.urlopen(src['url'],timeout=90).read()
        if hashlib.sha256(data).hexdigest()!=src['sha256']:
            raise RuntimeError(f"Source hash mismatch: {src['id']}; do not silently accept changed data")
        path.write_bytes(data)
        print(f"Verified {src['id']}: {len(data):,} bytes")
if __name__=='__main__':main()
