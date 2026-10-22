"""Reproduce every published paired statistic from anonymous count histograms."""
from pathlib import Path
import csv, json, collections, math
import numpy as np
from scipy.stats import spearmanr
from block_episodes import paired_duration
from record_core import confusion


def main():
    root = Path(__file__).parent / 'results'; checks = []
    def check(name, ok):
        checks.append({'check': name, 'passed': bool(ok)})
        if not ok:
            raise AssertionError(name)
    stored = json.loads((root / 'history_results.json').read_text())['analysis']
    groups = collections.defaultdict(list)
    for r in csv.DictReader((root / 'history_duration_histogram.csv').open()):
        groups[r['gap_window_days'] + 'd_' + r['subset']].extend([(float(r['first_seconds']), float(r['second_seconds']))] * int(r['count']))
    for name, pairs in groups.items():
        rerun = paired_duration(pairs)
        for key, value in rerun.items():
            check(name + ' ' + key, value == stored[name][key])
        if 'spearman_log_durations' in stored[name]:
            x, y = np.asarray(pairs).T
            rho, p = spearmanr(np.log2(x), np.log2(y))
            check(name + ' Spearman', np.isclose(rho, stored[name]['spearman_log_durations'], rtol=1e-12))
    observed = json.loads((root / 'wording_results.json').read_text())['groups']
    status_groups = collections.defaultdict(list)
    for r in csv.DictReader((root / 'status_histogram.csv').open()):
        status_groups[r['group'], r['window']].extend([r] * int(r['count']))
    for group, record in observed.items():
        for window, key in [('24h', 'status_pairs'), ('1h', 'within_1h'), ('10min', 'within_10min')]:
            check(group + ' ' + key, confusion(status_groups[group, window]) == record[key])
    check('all requested history subsets present', len(groups) == 12)
    check('positive wording findings not silently excluded', observed['pass']['status_pairs']['discordant'] == 3)
    check('exact duplicate control retained', observed['exact_all']['status_pairs']['discordant'] == 193)
    (root / 'verification.json').write_text(json.dumps({'checks': checks, 'passed': len(checks)}, indent=2))
    print(f'{len(checks)} saved-result checks passed; all 12 history summaries and 24 status tables reproduced.')


if __name__ == '__main__':
    main()
