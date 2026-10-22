"""Display the hashed audit sample locally; comments are not republished."""
from pathlib import Path
import argparse,csv,json
from analysis_core import pair_id
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--raw-dir',type=Path,default=ROOT/'raw');args=parser.parse_args()
reviews=list(csv.DictReader((ROOT/'data/meaning_audit.csv').open(encoding='utf8')))
wanted={r['pair_id']:r for r in reviews};found={}
with (args.raw_dir/'content.tsv').open(encoding='utf8',newline='') as f:
    for row in csv.DictReader(f,delimiter='\t'):
        key=pair_id(row['toxic'],row['neutral'])
        if key in wanted:found[key]=row
for review in reviews:
    row=found[review['pair_id']]
    print(json.dumps(dict(**review,original=row['toxic'],rewrite=row['neutral']),ensure_ascii=False))
