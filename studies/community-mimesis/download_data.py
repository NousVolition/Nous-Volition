from pathlib import Path
import argparse,urllib.request,shutil
from observations import file_hash,DELI_SHA,CGA_SHA
p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);a=p.parse_args();a.raw.mkdir(parents=True,exist_ok=True)
for name,url,sha in [
 ('deli-corpus.zip','https://zissou.infosci.cornell.edu/convokit/datasets/deli-corpus/deli-corpus.zip',DELI_SHA),
 ('cga_cmv.zip','https://zissou.infosci.cornell.edu/convokit/datasets/conversations-gone-awry-cmv-corpus/conversations-gone-awry-cmv-corpus.zip',CGA_SHA)]:
    target=a.raw/name
    if not target.exists():
        with urllib.request.urlopen(url,timeout=90) as r,target.open('wb') as f:shutil.copyfileobj(r,f)
    if file_hash(target)!=sha:raise ValueError('Source version mismatch: '+name+'; preserve the pinned version, do not silently replace it.')
    print(name,'verified')
