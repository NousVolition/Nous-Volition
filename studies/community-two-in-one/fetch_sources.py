"""Fetch published sources into an explicitly chosen private directory, checking bytes."""
from pathlib import Path
import argparse,hashlib,json,urllib.request
p=argparse.ArgumentParser();p.add_argument('private_directory',type=Path);args=p.parse_args()
root=Path(__file__).resolve().parent;dest=args.private_directory.resolve()
if dest==root or root in dest.parents:raise ValueError('Keep raw source files outside the published study folder')
dest.mkdir(parents=True,exist_ok=True)
for s in json.loads((root/'sources.json').read_text())['input_files']:
    path=dest/s['file']
    data=path.read_bytes() if path.exists() else urllib.request.urlopen(s['url'],timeout=60).read()
    if hashlib.sha256(data).hexdigest()!=s['sha256']:raise ValueError('Source hash mismatch: '+s['file'])
    path.write_bytes(data);print('Verified',s['file'],len(data))
