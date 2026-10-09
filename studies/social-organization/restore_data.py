"""Restore the exact recorded NPZ from transport parts; standard library only."""
from pathlib import Path
import hashlib,json,os


def restore(data=Path('data'), destination=None):
    data=Path(data);destination=Path(destination) if destination is not None else data/'arrays.npz'
    specification=data/'arrays.parts.json'
    if not specification.exists():
        if destination.is_file():return destination
        raise FileNotFoundError(destination)
    spec=json.loads(specification.read_text(encoding='utf-8'))
    def digest(path):
        h=hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
        return h.hexdigest()
    if destination.exists():
        if digest(destination)!=spec['sha256']:raise ValueError('Existing arrays.npz differs; refusing to overwrite it.')
        return destination
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_name(destination.name+'.assembling')
    total=hashlib.sha256();size=0
    with temporary.open('xb') as out:
        for part in spec['parts']:
            if Path(part['name']).name!=part['name']:raise ValueError('Unsafe part name')
            raw=(data/'array-parts'/part['name']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=part['sha256'] or len(raw)!=part['bytes']:
                raise ValueError('Part checksum mismatch: '+part['name'])
            out.write(raw);total.update(raw);size+=len(raw)
    if total.hexdigest()!=spec['sha256'] or size!=spec['bytes']:
        raise ValueError('Restored array checksum mismatch')
    os.replace(temporary,destination)
    return destination


if __name__=='__main__':print('Verified recorded arrays:',restore())
