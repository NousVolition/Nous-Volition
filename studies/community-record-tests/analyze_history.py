"""Compare genuine repeat block decisions with exact-reason controls."""
from pathlib import Path
import argparse, collections, hashlib, itertools, json, math, sqlite3
import numpy as np
from scipy.stats import spearmanr
from block_episodes import episodes, epoch, DAY, paired_duration
from record_core import reason_key, sha

BLOCK_SHA = '002a12802858e3d0e8672435dc6f9c09d0ab9e5cd274d508f7c1dbcb14d860c6'


def main(raw, private, out):
    private.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((raw / 'block_cache_meta.json').read_text())
    if meta['sha256'] != BLOCK_SHA:
        raise ValueError('Incorrect source cache')
    con = sqlite3.connect('file:' + (raw / 'blocks_v2.sqlite').resolve().as_posix() + '?mode=ro', uri=True)
    counts = collections.Counter(); pairs = []
    it = con.execute('SELECT account,t,logid,action,expiry,moderator,reason FROM events ORDER BY account,t,logid')
    for account, group in itertools.groupby(it, key=lambda r: r[0]):
        eps, issues = episodes([tuple(r[1:]) for r in group])
        if issues or not eps:
            continue
        first = eps[0]
        if first['start'] < epoch('2006-01-01T00:00:00Z') or not math.isfinite(first['initial_duration']) or not math.isfinite(first['end']):
            continue
        if first['end'] + 180 * DAY > meta['latest']:
            continue
        counts['complete_followup_accounts'] += 1
        if len(eps) < 2:
            continue
        second = eps[1]
        gap = (second['start'] - first['end']) / DAY
        if not 0 < gap <= 180:
            continue
        counts['repeated_within_180_days'] += 1
        if not math.isfinite(second['initial_duration']):
            counts['second_indefinite'] += 1
            continue
        counts['finite_pairs'] += 1
        pairs.append({'account_hash': account, 'first_logid': first['logid'], 'second_logid': second['logid'],
                      'first_seconds': first['initial_duration'], 'second_seconds': second['initial_duration'],
                      'gap_days': gap, 'same_moderator': bool(first['moderator'] and first['moderator'] == second['moderator'])})
    if counts['finite_pairs'] != 8687:
        raise AssertionError('Original cohort did not reproduce')
    wanted = {p[key] for p in pairs for key in ('first_logid', 'second_logid')}
    reasons, moderators = {}, {}
    h = hashlib.sha256()
    with (raw / 'blocks.json').open('rb') as f:
        for line in f:
            h.update(line)
            record = json.loads(line)
            if record['logid'] in wanted:
                reasons[record['logid']] = reason_key(record.get('comment', ''))
                moderators[record['logid']] = record.get('user')
    if h.hexdigest() != BLOCK_SHA:
        raise ValueError('Source block-log hash mismatch')
    if set(reasons) != wanted:
        raise ValueError('Missing initial-decision source records')
    for p in pairs:
        a, b = p['first_logid'], p['second_logid']
        p['same_reason'] = bool(reasons[a] and reasons[a] == reasons[b])
        p['same_moderator'] = bool(moderators[a] and moderators[b] and moderators[a] == moderators[b])
        p['both_controls'] = p['same_reason'] and p['same_moderator']
        p['reason_hash'] = sha(reasons[a]) if p['same_reason'] else None
    (private / 'history_pairs_private.json').write_text(json.dumps(pairs, indent=2))
    results = {}
    histograms = []
    for days in (30, 90, 180):
        for subset in ('all', 'same_reason', 'same_moderator', 'both_controls'):
            chosen = [p for p in pairs if p['gap_days'] <= days and (subset == 'all' or p[subset])]
            values = [(p['first_seconds'], p['second_seconds']) for p in chosen]
            summary = paired_duration(values)
            if subset in ('same_reason', 'both_controls') and len(values) > 2:
                x, y = np.asarray(values).T
                rho, pv = spearmanr(np.log2(x), np.log2(y))
                summary['spearman_log_durations'] = float(rho) if np.isfinite(rho) else None
                summary['spearman_p_exploratory'] = float(pv) if np.isfinite(pv) else None
            summary['distinct_matching_reason_strings'] = len({p['reason_hash'] for p in chosen if p['same_reason']})
            results[f'{days}d_{subset}'] = summary
            histograms.extend({'gap_window_days': days, 'subset': subset, 'first_seconds': x, 'second_seconds': y, 'count': n}
                              for (x, y), n in sorted(collections.Counter(values).items()))
    document = {'source_sha256': BLOCK_SHA, 'cohort': dict(counts),
                'analysis': results, 'followup_note': 'All sensitivities use the same 180-day complete-follow-up cohort.',
                'causal_effect_identified': False,
                'reason_equality_is_not_conduct_equality': True}
    (out / 'history_results.json').write_text(json.dumps(document, indent=2, allow_nan=False))
    import csv
    with (out / 'history_duration_histogram.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(histograms[0])); w.writeheader(); w.writerows(histograms)
    print(json.dumps({'cohort': dict(counts), 'primary_180d': {k: v for k, v in results.items() if k.startswith('180d')}}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--private', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path(__file__).parent / 'results')
    a = p.parse_args(); main(a.raw, a.private, a.out)
