"""Restore byte-exact published numerical files; no simulation or pickle loading.

By default restore numerical archives into this checkout. --full-snapshot with a
new --destination reconstructs the complete original source/report/data snapshot.
Archives can be downloaded automatically or supplied with --assets-dir for offline use.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import urllib.request
import zipfile


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_path(root, name):
    rel = PurePosixPath(name)
    if (not name or rel.is_absolute() or '\\' in name or ':' in name
            or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError('Unsafe archive path: ' + name)
    root = Path(root).resolve()
    result = root.joinpath(*rel.parts)
    current = result
    while current != root:
        if current.is_symlink():
            raise ValueError('Refusing symlink: ' + str(current))
        current = current.parent
    if not result.resolve().is_relative_to(root):
        raise ValueError('Path escapes destination: ' + name)
    return result


def load_catalog(path):
    catalog = json.loads(Path(path).read_text(encoding='utf-8'))
    if catalog.get('schema') != 1:
        raise ValueError('Unsupported catalog schema')
    names = set()
    assets = {a['name']: a for a in catalog['assets']}
    if len(assets) != len(catalog['assets']):
        raise ValueError('Duplicate asset name')
    for f in catalog['files']:
        safe_path(Path.cwd(), f['path'])
        if f['path'] in names or f['asset'] not in assets:
            raise ValueError('Duplicate file or missing asset: ' + f['path'])
        if f['kind'] not in ('numerical', 'source') or f['bytes'] < 0:
            raise ValueError('Invalid file record')
        if len(f['sha256']) != 64 or any(c not in '0123456789abcdef' for c in f['sha256']):
            raise ValueError('Invalid file checksum')
        names.add(f['path'])
    for a in catalog['assets']:
        if (Path(a['name']).name != a['name'] or a['name'] in ('.', '..')
                or '/' in a['name'] or '\\' in a['name'] or ':' in a['name']):
            raise ValueError('Invalid asset name')
        if (a['bytes'] < 0 or len(a['sha256']) != 64
                or any(c not in '0123456789abcdef' for c in a['sha256'])
                or a['files'] != sum(f['asset'] == a['name'] for f in catalog['files'])):
            raise ValueError('Invalid asset size, checksum or file count')
        expected = 'https://github.com/' + catalog['repository'] + '/releases/download/' + catalog['release_tag'] + '/' + a['name']
        if a['url'] != expected:
            raise ValueError('Asset URL differs from declared release')
    return catalog


def matching(path, record):
    return path.is_file() and path.stat().st_size == record['bytes'] and digest(path) == record['sha256']


def verify_files(catalog, destination, full=False, studies=()):
    files = [f for f in catalog['files'] if (full or f['kind'] == 'numerical')
             and (not studies or any(f['path'] == s or f['path'].startswith(s.rstrip('/') + '/') for s in studies))]
    if not files:
        raise ValueError('No catalog files selected')
    for f in files:
        target = safe_path(destination, f['path'])
        if not matching(target, f):
            raise ValueError('Missing or changed restored file: ' + f['path'])
    return len(files)


def obtain(asset, cache, assets_dir=None):
    target = safe_path(cache, asset['name'])
    source = safe_path(assets_dir, asset['name']) if assets_dir else target
    if source.exists():
        if not matching(source, asset):
            raise ValueError('Archive checksum mismatch: ' + str(source))
        return source
    if assets_dir:
        raise FileNotFoundError(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    # A failed download never replaces a verified cached asset.
    fd, temp = tempfile.mkstemp(prefix=asset['name'] + '.', suffix='.partial', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as out, urllib.request.urlopen(
                urllib.request.Request(asset['url'], headers={'User-Agent': 'verified-numerical-data-restore'}), timeout=180) as inp:
            shutil.copyfileobj(inp, out, 1024 * 1024)
        if not matching(Path(temp), asset):
            raise ValueError('Downloaded archive checksum mismatch: ' + asset['name'])
        os.replace(temp, target)
    finally:
        if Path(temp).exists():
            Path(temp).unlink()
    return target


def validate_archive(path, asset, records):
    if not matching(Path(path), asset):
        raise ValueError('Archive checksum mismatch: ' + asset['name'])
    expected = {f['path']: f for f in records}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError('Archive member inventory differs: ' + asset['name'])
        for info in archive.infolist():
            f = expected[info.filename]
            if info.is_dir() or stat.S_ISLNK(info.external_attr >> 16) or info.file_size != f['bytes']:
                raise ValueError('Invalid archive member: ' + info.filename)
            h = hashlib.sha256()
            with archive.open(info) as inp:
                for block in iter(lambda: inp.read(1024 * 1024), b''):
                    h.update(block)
            if h.hexdigest() != f['sha256']:
                raise ValueError('Member checksum mismatch: ' + info.filename)
    return len(expected)


def restore(catalog, destination, cache, assets_dir=None, full=False, studies=(), archives_only=False):
    destination = Path(destination).resolve()
    selected = [f for f in catalog['files'] if (full or f['kind'] == 'numerical')
                and (not studies or any(f['path'] == s or f['path'].startswith(s.rstrip('/') + '/') for s in studies))]
    if not selected:
        raise ValueError('No catalog files selected')
    # Preflight all conflicts before changing any destination file.
    if not archives_only:
        for f in selected:
            p = safe_path(destination, f['path'])
            if p.exists() and not matching(p, f):
                raise ValueError('Refusing to overwrite different existing file: ' + f['path'])
    required = {f['asset'] for f in selected}
    assets = {a['name']: a for a in catalog['assets']}
    verified = []
    for name in sorted(required):
        archive = obtain(assets[name], cache, assets_dir)
        members = [f for f in catalog['files'] if f['asset'] == name]
        validate_archive(archive, assets[name], members)
        verified.append((name, archive))
        print('Verified archive: ' + name, flush=True)
    # No destination writes occur until all required archives pass.
    written = 0
    if not archives_only:
        for name, path in verified:
            with zipfile.ZipFile(path) as archive:
                for f in selected:
                    if f['asset'] != name:
                        continue
                    target = safe_path(destination, f['path'])
                    if matching(target, f):
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    fd, temp = tempfile.mkstemp(prefix=target.name + '.', suffix='.restore', dir=target.parent)
                    try:
                        with os.fdopen(fd, 'wb') as out, archive.open(f['path']) as inp:
                            shutil.copyfileobj(inp, out, 1024 * 1024)
                        if not matching(Path(temp), f):
                            raise ValueError('Restored bytes differ: ' + f['path'])
                        safe_path(destination, f['path'])
                        if target.exists() and not matching(target, f):
                            raise ValueError('Destination changed during restore: ' + f['path'])
                        os.replace(temp, target)
                        written += 1
                    finally:
                        if Path(temp).exists():
                            Path(temp).unlink()
        verify_files(catalog, destination, full, studies)
    return {'verified_archives': len(required), 'selected_files': len(selected), 'written_files': written,
            'bytes': sum(f['bytes'] for f in selected), 'full_snapshot': full}


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=root/'data-release/catalog.json')
    parser.add_argument('--destination', type=Path, default=root)
    parser.add_argument('--cache', type=Path, default=Path.home()/'.cache/numerical-data-releases')
    parser.add_argument('--assets-dir', type=Path)
    parser.add_argument('--full-snapshot', action='store_true')
    parser.add_argument('--study', action='append', default=[])
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--verify-archives', action='store_true')
    args = parser.parse_args()
    catalog = load_catalog(args.catalog)
    cache = args.cache/catalog['repository'].replace('/', '_')/catalog['release_tag']
    if args.verify_only:
        result = {'verified_files': verify_files(catalog, args.destination, args.full_snapshot, args.study)}
    else:
        result = restore(catalog, args.destination, cache, args.assets_dir, args.full_snapshot,
                         args.study, args.verify_archives)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
