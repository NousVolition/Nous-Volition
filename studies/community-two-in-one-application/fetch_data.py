"""Fetch only public experience-sampling records and their dictionaries."""
from pathlib import Path
import concurrent.futures,hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parent
RAW=ROOT.parent.parent/'work'/'twoinone-application-raw'
def main():
    m=json.loads((ROOT/'source_manifest.json').read_text())
    def get(f):
        p=RAW/f['path'];url='https://raw.githubusercontent.com/'+m['repository']+'/'+m['commit']+'/'+f['path']
        b=p.read_bytes() if p.exists() else urllib.request.urlopen(url,timeout=60).read()
        h=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        if h!=f['sha']:raise ValueError('Upstream hash mismatch: '+f['path'])
        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        return dict(path=f['path'],url=url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),git_blob_sha1=h)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:out=list(pool.map(get,m['files']))
    (RAW/'download_manifest.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(files=len(out),bytes=sum(x['bytes'] for x in out))))
if __name__=='__main__':main()
