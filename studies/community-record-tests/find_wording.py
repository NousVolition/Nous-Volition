"""Select text comparisons without consulting moderation status."""
from pathlib import Path
import argparse, sqlite3, json, itertools, datetime, collections, hashlib
from record_core import normalize, candidate, nonoverlap, sha


def main(db, private, out):
    private.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect('file:' + db.resolve().as_posix() + '?mode=ro', uri=True)
    staff = {r[0] for r in con.execute('SELECT ID_User FROM Newspaper_Staff')}
    counts = collections.Counter()
    pools = {'exact': [], 'changed': []}
    # Status intentionally omitted from this query and all candidate processing.
    query = '''SELECT ID_Article,ID_User,ID_Parent_Post,ID_Post,CreatedAt,Headline,Body
               FROM Posts ORDER BY ID_Article,ID_User,ID_Parent_Post,CreatedAt,ID_Post'''
    for key, group in itertools.groupby(con.execute(query), key=lambda r: tuple(r[:3])):
        records = list(group)
        counts['posts'] += len(records)
        if key[1] in staff:
            counts['staff_posts_excluded'] += len(records)
            continue
        prepared = []
        for row in records:
            text = normalize((row[5] or '') + '\n' + (row[6] or ''))
            if not text:
                continue
            parsed = datetime.datetime.fromisoformat(row[4])
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=datetime.timezone.utc)
            time = parsed.timestamp()
            prepared.append((row[3], time, text))
        for i, a in enumerate(prepared):
            for b in prepared[i + 1:]:
                gap = (b[1] - a[1]) / 3600
                if gap > 24:
                    break
                counts['context_time_pairs_screened'] += 1
                result = candidate(a[2], b[2])
                if result:
                    pair = {'earlier': a[0], 'later': b[0], 'article': key[0], 'author': key[1],
                            'parent': key[2], 'gap_hours': gap, **result,
                            'pair_hash': sha(f'wording-v1|{a[0]}|{b[0]}')}
                    pools[result['kind']].append(pair)
    selected = {}
    for kind, values in pools.items():
        counts[kind + '_raw_pairs'] = len(values)
        clean = nonoverlap(values)
        counts[kind + '_nonoverlapping_pairs'] = len(clean)
        selected[kind] = sorted(clean, key=lambda p: p['pair_hash'])[:40]
        (private / f'{kind}_pool.json').write_text(json.dumps(clean, indent=2))
    (private / 'frozen_pairs.json').write_text(json.dumps(selected, indent=2))
    audit = []
    for pair in selected['changed']:
        def get_text(pid):
            r = con.execute('SELECT Headline,Body FROM Posts WHERE ID_Post=?', (pid,)).fetchone()
            return normalize((r[0] or '') + '\n' + (r[1] or '')) if r else None
        article = con.execute('SELECT Title FROM Articles WHERE ID_Article=?', (pair['article'],)).fetchone()
        audit.append({'pair_hash': pair['pair_hash'], 'gap_hours': pair['gap_hours'],
                      'article_title': article[0], 'parent': get_text(pair['parent']) if pair['parent'] else None,
                      'earlier_text': get_text(pair['earlier']), 'later_text': get_text(pair['later'])})
    (private / 'blind_wording_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    receipt = {'selection': dict(counts), 'sample_size': len(audit),
               'status_accessed_for_selection': False,
               'database_sha256': hashlib.file_digest(db.open('rb'), 'sha256').hexdigest(),
               'sample_sha256': sha(json.dumps(selected, sort_keys=True)),
               'protocol_sha256': hashlib.sha256((Path(__file__).parent / 'PROTOCOL.md').read_bytes()).hexdigest(),
               'audit_sample_order': [a['pair_hash'] for a in audit]}
    (out / 'wording_selection.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', type=Path, required=True)
    p.add_argument('--private', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path(__file__).parent / 'results')
    a = p.parse_args(); main(a.db, a.private, a.out)
