"""Inspect original text locally; outcomes remain hidden unless explicitly requested."""
import argparse, json, sqlite3
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', type=Path, required=True); p.add_argument('--private', type=Path, required=True)
    p.add_argument('--pair-hash', required=True); p.add_argument('--show-status', action='store_true')
    a = p.parse_args()
    pairs = json.loads((a.private / 'blind_wording_audit.json').read_text(encoding='utf-8'))
    matches = [r for r in pairs if r['pair_hash'].startswith(a.pair_hash)]
    if len(matches) != 1:
        raise ValueError('Provide a unique pair hash prefix from the published audit')
    record = dict(matches[0])
    if a.show_status:
        frozen = json.loads((a.private / 'frozen_pairs.json').read_text())['changed']
        pair = next(r for r in frozen if r['pair_hash'] == record['pair_hash'])
        db = sqlite3.connect('file:' + a.db.resolve().as_posix() + '?mode=ro', uri=True)
        record['statuses'] = {k: db.execute('SELECT Status FROM Posts WHERE ID_Post=?', (pair[k],)).fetchone()[0] for k in ('earlier', 'later')}
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
