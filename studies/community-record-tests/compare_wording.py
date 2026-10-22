"""Join actual moderation statuses only after verifying the frozen semantic audit."""
from pathlib import Path
import argparse, collections, csv, datetime, hashlib, json, sqlite3
from record_core import sha, normalize, confusion, require_audit, window_pairs


def verify_lock(audit_path, lock_path):
    decisions = json.loads(audit_path.read_text())
    lock = json.loads(lock_path.read_text())
    if hashlib.sha256(audit_path.read_bytes()).hexdigest() != lock['audit_sha256']:
        raise ValueError('Semantic judgments changed after lock')
    if not lock['verdicts_frozen_before_status_join']:
        raise ValueError('Audit not frozen')
    return decisions, lock


def main(db, private, out):
    decisions, lock = verify_lock(out / 'semantic_audit.json', out / 'semantic_audit_lock.json')
    selection = json.loads((out / 'wording_selection.json').read_text())
    frozen = json.loads((private / 'frozen_pairs.json').read_text())
    if sha(json.dumps(frozen, sort_keys=True)) != selection['sample_sha256']:
        raise ValueError('Sample changed')
    require_audit(frozen['changed'], decisions)
    if [d['pair_hash'] for d in decisions] != selection['audit_sample_order']:
        raise ValueError('Audit order changed')
    if hashlib.file_digest(db.open('rb'), 'sha256').hexdigest() != selection['database_sha256']:
        raise ValueError('Source database changed')
    con = sqlite3.connect('file:' + db.resolve().as_posix() + '?mode=ro', uri=True)
    def enrich(p):
        p = dict(p)
        for direction in ('earlier', 'later'):
            row = con.execute('SELECT Status,ID_Article,ID_User,ID_Parent_Post,Headline,Body FROM Posts WHERE ID_Post=?', (p[direction],)).fetchone()
            if row is None or tuple(row[1:4]) != (p['article'], p['author'], p['parent']):
                raise ValueError('Missing or mismatched context')
            p[direction + '_status'] = row[0]
            p[direction + '_text'] = normalize((row[4] or '') + '\n' + (row[5] or ''))
        if p['kind'] == 'exact' and p['earlier_text'] != p['later_text']:
            raise ValueError('Exact control changed text')
        p['parent_record_available'] = bool(p['parent'] is not None and con.execute('SELECT 1 FROM Posts WHERE ID_Post=?', (p['parent'],)).fetchone())
        p['article_record_available'] = bool(con.execute('SELECT 1 FROM Articles WHERE ID_Article=?', (p['article'],)).fetchone())
        confusion([p])  # fail closed on unexpected status labels
        return p
    audit = {d['pair_hash']: d for d in decisions}
    changed = [{**enrich(p), **audit[p['pair_hash']]} for p in frozen['changed']]
    exact_all = [enrich(p) for p in json.loads((private / 'exact_pool.json').read_text())]
    exact_ids = {p['pair_hash'] for p in frozen['exact']}
    groups = {'all_changed': changed,
              **{v: [p for p in changed if p['verdict'] == v] for v in ('pass', 'fail', 'uncertain')},
              'pass_lexical': [p for p in changed if p['verdict'] == 'pass' and p['change_type'] == 'lexical_syntactic'],
              'pass_typography': [p for p in changed if p['verdict'] == 'pass' and p['change_type'] == 'typography'],
              'exact_all': exact_all, 'exact_sample': [p for p in exact_all if p['pair_hash'] in exact_ids]}
    results = {}
    for name, pairs in groups.items():
        results[name] = {'status_pairs': confusion(pairs),
                         'within_1h': confusion(window_pairs(pairs, 1)),
                         'within_10min': confusion(window_pairs(pairs, 1/6)),
                         'distinct_authors': len({p['author'] for p in pairs}),
                         'distinct_articles': len({p['article'] for p in pairs}),
                         'non_top_level': sum(p['parent'] is not None for p in pairs),
                         'parent_record_available': sum(p['parent_record_available'] for p in pairs),
                         'article_record_available': sum(p['article_record_available'] for p in pairs)}
    fields = ['pair_hash', 'verdict', 'change_type', 'earlier_status', 'later_status', 'gap_hours', 'parent_record_available']
    with (out / 'audited_status_pairs.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        w.writerows({k: p[k] for k in fields} for p in changed)
    # Aggregate sufficient statistics for independent rechecking; no source IDs.
    aggregate = []
    for name, pairs in groups.items():
        for window, hours in [('24h', 24), ('1h', 1), ('10min', 1/6)]:
            counts = confusion(window_pairs(pairs, hours))
            for a in ('online', 'deleted'):
                for b in ('online', 'deleted'):
                    aggregate.append({'group': name, 'window': window, 'earlier_status': a,
                                      'later_status': b, 'count': counts[a + '_' + b]})
    with (out / 'status_histogram.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(aggregate[0])); w.writeheader(); w.writerows(aggregate)
    document = {'audit_sha256': lock['audit_sha256'], 'sample_sha256': selection['sample_sha256'],
                'source_database_sha256': selection['database_sha256'], 'groups': results,
                'equivalence_counts': dict(collections.Counter(p['verdict'] for p in changed)),
                'exact_control_check': 'All 353 mechanically verified for identical normalized text and matching author/article/parent; no independent referent review.',
                'wording_causal_effect_identified': False, 'decision_timestamps_available': False}
    (out / 'wording_results.json').write_text(json.dumps(document, indent=2))
    receipt = out / 'status_join_receipt.json'
    if not receipt.exists():
        receipt.write_text(json.dumps({'first_join_completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                      'audit_lock_created_utc': lock['created_utc'], 'audit_sha256': lock['audit_sha256']}, indent=2))
    print(json.dumps({'equivalence_counts': document['equivalence_counts'],
                      'outcomes': {k: v['status_pairs'] for k, v in results.items()}}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', type=Path, required=True); p.add_argument('--private', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path(__file__).parent / 'results')
    a = p.parse_args(); main(a.db, a.private, a.out)
