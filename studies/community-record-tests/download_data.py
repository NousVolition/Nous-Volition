"""Download pinned public research records; never publish the local raw directory."""
import argparse, hashlib, json, shutil, tarfile, urllib.request
from pathlib import Path


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main(raw, which):
    sources = json.loads((Path(__file__).parent / 'sources.json').read_text())
    raw.mkdir(parents=True, exist_ok=True)
    for item in sources['files']:
        if item['study'] != which:
            continue
        target = raw / item['file']
        if not target.exists():
            pending = target.with_suffix(target.suffix + '.partial')
            request = urllib.request.Request(item['url'], headers={'User-Agent': 'StreamsAndRocks-public-research/1.0'})
            with urllib.request.urlopen(request, timeout=120) as source, pending.open('wb') as dest:
                shutil.copyfileobj(source, dest, 1024 * 1024)
            if digest(pending) != item['sha256']:
                raise ValueError('Downloaded source hash differs; retaining .partial for inspection')
            pending.replace(target)
        if digest(target) != item['sha256']:
            raise ValueError('Existing source hash differs')
        if which == 'wording':
            db = raw / 'million_posts.sqlite'
            if not db.exists():
                with tarfile.open(target, 'r:bz2') as tar:
                    member = tar.getmember('million_post_corpus/corpus.sqlite3')
                    if not member.isfile():
                        raise ValueError('Expected regular SQLite member')
                    with tar.extractfile(member) as source, db.open('wb') as dest:
                        shutil.copyfileobj(source, dest)
            if digest(db) != sources['database_sha256']:
                raise ValueError('SQLite source hash differs')
        print(f'Verified {item["file"]}: {item["sha256"]}')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--which', choices=['wording', 'history'], required=True)
    a = p.parse_args(); main(a.raw, a.which)
