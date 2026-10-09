"""Check tracked Python/JSON, Markdown file links, and packaged study hashes.

No simulation, network request, or file rewrite is performed. Markdown heading
fragments and external URLs are outside this check. Run from any directory.
"""
import ast
import hashlib
import json
import posixpath
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit


def check(root):
    if (root / '.git').exists():
        names = subprocess.check_output(
            ['git', '-C', str(root), 'ls-files', '-z']).decode('utf-8').split('\0')
        files = {name for name in names if name}
    else:
        files = {p.relative_to(root).as_posix() for p in root.rglob('*')
                 if p.is_file() and not any(x in p.parts for x in
                    ('__pycache__', '.pytest_cache', 'scratch'))}
    dirs = {'.'}
    for name in files:
        parent = posixpath.dirname(name)
        while parent:
            dirs.add(parent)
            parent = posixpath.dirname(parent)
    errors = []
    counts = dict(python=0, json=0, markdown=0, local_links=0, manifest_files=0)
    for name in sorted(files):
        suffix = Path(name).suffix.lower()
        if suffix not in ('.py', '.json', '.md'):
            continue
        try:
            text = (root / name).read_text(encoding='utf-8-sig')
            if suffix == '.py':
                ast.parse(text, filename=name)
                counts['python'] += 1
            elif suffix == '.json':
                json.loads(text)
                counts['json'] += 1
            else:
                counts['markdown'] += 1
                text = re.sub(r'(?ms)^```.*?^```[^\n]*', '', text)
                for match in re.finditer(r'\]\(\s*(<[^>]+>|[^\s)]+)\s*\)', text):
                    link = match.group(1).strip('<>')
                    url = urlsplit(link)
                    if url.scheme or url.netloc or not url.path:
                        continue
                    target = posixpath.normpath(posixpath.join(
                        posixpath.dirname(name), unquote(url.path)))
                    counts['local_links'] += 1
                    if target not in files and target not in dirs:
                        errors.append(f'{name}: missing link target {link}')
        except (OSError, UnicodeError, ValueError, SyntaxError) as exc:
            errors.append(f'{name}: {exc}')
    # These manifests cover their published study packages. Other repositories
    # retain historical manifests or raw-data inventories with different scopes.
    for name in sorted(files):
        if not re.fullmatch(r'studies/[^/]+/manifest_sha256.json', name):
            continue
        try:
            manifest = json.loads((root / name).read_text(encoding='utf-8'))
            for relative, expected in manifest.items():
                target = posixpath.normpath(posixpath.join(posixpath.dirname(name), relative))
                if target not in files:
                    errors.append(f'{name}: missing manifested file {relative}')
                    continue
                actual = hashlib.sha256((root / target).read_bytes()).hexdigest()
                counts['manifest_files'] += 1
                if actual != expected:
                    errors.append(f'{name}: SHA-256 mismatch for {relative}')
        except (OSError, UnicodeError, ValueError, TypeError, AttributeError) as exc:
            errors.append(f'{name}: {exc}')
    return counts, errors


if __name__ == '__main__':
    counts, errors = check(Path(__file__).resolve().parents[1])
    print(json.dumps(dict(checked=counts, errors=errors), indent=2))
    raise SystemExit(bool(errors))
