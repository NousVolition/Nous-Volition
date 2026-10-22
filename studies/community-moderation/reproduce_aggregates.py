"""Recompute penalty comparisons from published aggregate duration counts."""
from pathlib import Path
import csv,json,collections
from analysis_core import paired_duration
ROOT=Path(__file__).resolve().parent
def verify():
    groups=collections.defaultdict(list)
    for r in csv.DictReader((ROOT/'data/duration_histogram.csv').open()):
        groups[(r['window_days'],r['subset'])].extend([(float(r['first_seconds']),float(r['second_seconds']))]*int(r['count']))
    target=json.loads((ROOT/'data/block_results.json').read_text());checks={}
    for (w,s),pairs in groups.items():checks[w+'_'+s]=paired_duration(pairs)==target['windows'][w][s]
    if not all(checks.values()):raise AssertionError(checks)
    return checks
if __name__=='__main__':print(json.dumps(verify(),indent=2))
