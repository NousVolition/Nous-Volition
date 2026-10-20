"""Manufactured quadrupolar pressure: independent exact surface virtual work.

This tests spatial traction extraction, not a steady Navier-Stokes solution.
The continuum result follows from integrating P2(u)*(u^2-1/3) over a sphere.
"""
from pathlib import Path
import json
import numpy as np
from flow_lbm import cp,W,advance
P=Path(__file__).resolve().parent;rows=[]
for aspect in [1.,.75]:
  for D in [12,20,36]:
    n=3*D;R=D/2;a=R*aspect**(2/3);b=R*aspect**(-1/3)
    x,y,z=np.ogrid[:n,:n,:n];rx=(x-n/2)/a;ry=(y-n/2)/b;rz=(z-n/2)/b
    radius=np.sqrt(rx*rx+ry*ry+rz*rz);solid=radius<=1
    u=rx/np.maximum(radius,1e-10);amp=.002
    rho=1+3*amp*(3*u*u-1)/2
    f=cp.asarray(W[:,None,None,None]*rho,dtype=cp.float32);g=cp.empty_like(f)
    fields=cp.empty((5,n,n,n),cp.float32);forces=cp.empty((7,n,n,n),cp.float32)
    advance(((n**3+127)//128,),(128,),(f,g,cp.asarray(solid,cp.uint8),fields,forces,
      *map(np.int32,[n,n,n]),*map(np.float32,[0,.8,0]),np.int32(1),
      *map(np.float32,[n/2,n/2,n/2,a,b]),np.int32(1)))
    F=cp.asnumpy(forces.sum((1,2,3),dtype=cp.float64));q=F[3]-F[5]/F[6]*F[4]
    exact=-8*np.pi/15*amp*R**3
    rows.append(dict(aspect=aspect,D=D,computed=q,exact=exact,relative_error=float(q/exact-1)))
    del f,g,fields,forces;cp.get_default_memory_pool().free_all_blocks()
report=dict(rows=rows,status='passed' if all(abs(r['relative_error'])<.10 for r in rows if r['D']==36) else 'failed')
(P/'surface_load_verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
assert report['status']=='passed'
