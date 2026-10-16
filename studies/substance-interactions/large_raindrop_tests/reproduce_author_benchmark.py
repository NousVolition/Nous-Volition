"""Usage: python reproduce_author_benchmark.py /path/to/scavenging_routines.py
Read its Non-Commercial Government Licence before obtaining/using author code.
This script does not bundle or modify the author's implementation.
"""
import sys,importlib.util,json,hashlib
from pathlib import Path
import numpy as np
p=Path(__file__).resolve().parent
source=Path(sys.argv[1]);protocol=json.loads((p/'frozen_protocol.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==protocol['author_code_sha256']
spec=importlib.util.spec_from_file_location('author',source)
j=importlib.util.module_from_spec(spec);spec.loader.exec_module(j)
rows=[]
for dp in [.1e-6,1e-6,5e-6]:
    ds=np.array([.0005,.00125,.003])
    with np.errstate(invalid='ignore'): z=j.collision_efficiency(101325,293.15,.8,ds,dp)
    for i,D in enumerate(ds):rows.append(dict(D=D,d=dp,U=z[8][i],brownian=z[0][i],interception=z[1][i],rear=z[7][i]))
expected=json.loads((p/'author_benchmark.json').read_text())
for a,b in zip(rows,expected):
    for k in a:np.testing.assert_allclose(a[k],b[k],rtol=1e-12,atol=1e-15)
print('All 9 independent component benchmark records reproduced.')
