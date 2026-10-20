"""Independent moment, analytic diffusion and curved-wall rest tests."""
import json
from pathlib import Path
import numpy as np
from flow_lbm import cp,C,W,OPP,equilibrium,advance
P=Path(__file__).resolve().parent;checks=[]
def check(name,value,limit):checks.append(dict(name=name,value=float(value),limit=limit,passed=bool(abs(value)<limit)))
check('weights',W.sum()-1,1e-14)
check('isotropic moments',np.max(abs(np.einsum('q,qi,qj->ij',W,C,C)-np.eye(3)/3)),1e-14)
check('opposites',np.max(abs(C[OPP]+C)),1e-14)
def simulate(vel,solid,steps,tau=.8,density=1.,a=4.,b=5.):
    nx,ny,nz=solid.shape;N=nx*ny*nz
    f=cp.asarray(equilibrium(vel)*density);g=cp.empty_like(f);s=cp.asarray(solid,cp.uint8)
    fields=cp.empty((5,nx,ny,nz),cp.float32);forces=cp.empty((7,nx,ny,nz),cp.float32)
    for step in range(steps):
        advance(((N+127)//128,),(128,),(f,g,s,fields,forces,*map(np.int32,[nx,ny,nz]),
          *map(np.float32,[0,tau,0]),np.int32(1),*map(np.float32,[nx/2,ny/2,nz/2,a,b]),np.int32(1)))
        f,g=g,f
    return cp.asnumpy(fields),cp.asnumpy(forces)
errors=[]
for n,steps in [(32,500),(64,2000)]:
    vel=np.zeros((3,4,n,4),np.float32);sine=np.sin(2*np.pi*np.arange(n)/n);vel[0]=.01*sine[None,:,None]
    fields,force=simulate(vel,np.zeros((4,n,4)),steps)
    measured=np.mean(fields[1]*sine[None,:,None])*2;exact=.01*np.exp(-.1*(2*np.pi/n)**2*steps)
    errors.append(abs(measured/exact-1))
    check('analytic shear decay '+str(n),errors[-1],.005)
    check('periodic mass '+str(n),fields[0].mean()-1,2e-6)
check('shear refinement ratio below 0.3',errors[1]/errors[0],.3)
vel=np.zeros((3,16,16,16),np.float32);vel[0]=.03
field,force=simulate(vel,np.zeros((16,16,16)),100)
check('uniform velocity',np.max(abs(field[1]-.03)),1e-6)
check('no obstacle no force',np.max(abs(force)),1e-12)
n=24;x,y,z=np.ogrid[:n,:n,:n];solid=((x-n/2)/4)**2+((y-n/2)/5)**2+((z-n/2)/5)**2<=1
for density in [1.,1.01]:
    fields,force=simulate(np.zeros((3,n,n,n),np.float32),solid,1,density=density)
    F=force.sum((1,2,3),dtype=np.float64);gauge=F[5]/F[6]
    q=F[3]-gauge*F[4]
    check('curved-wall rest net force rho='+str(density),np.linalg.norm(F[:3]),2e-6)
    check('pressure gauge corrected zero shape load rho='+str(density),q,2e-5)
    check('curved-wall rest fluid velocity rho='+str(density),np.max(abs(fields[1:4,:, :, :][:,~solid])),2e-6)
report=dict(status='passed' if all(c['passed'] for c in checks) else 'failed',checks=checks)
(P/'gas_verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
assert report['status']=='passed'
