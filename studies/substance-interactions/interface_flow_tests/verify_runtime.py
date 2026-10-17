"""Numerical checks independent of the experimental comparisons."""
from pathlib import Path
import json
import numpy as np
import openmm as mm
from openmm import unit as u
from water_md import create_system, scale_centers, OH, HH, WH
from flow_lbm import cp, C, W, OPP, equilibrium, advance

P=Path(__file__).resolve().parent
checks=[]
def check(name, passed, value=None):
    checks.append(dict(name=name,passed=bool(passed),value=value))

check('D3Q19 weights', abs(W.sum()-1)<1e-14)
check('D3Q19 isotropic second moment', np.allclose(np.einsum('q,qi,qj->ij',W,C,C),np.eye(3)/3))
check('D3Q19 opposite velocities', np.all(C[OPP]==-C))
for ny,steps in ((32,500),(64,2000)):
    nx,nz=4,4
    vel=np.zeros((3,nx,ny,nz),np.float32)
    sine=np.sin(2*np.pi*np.arange(ny)/ny)
    vel[0]=.01*sine[None,:,None]
    f=cp.asarray(equilibrium(vel));g=cp.empty_like(f)
    solid=cp.zeros((nx,ny,nz),cp.uint8)
    fields=cp.empty((5,nx,ny,nz),cp.float32);forces=cp.empty((3,nx,ny,nz),cp.float32)
    for k in range(steps):
        advance(((nx*ny*nz+127)//128,),(128,),
          (f,g,solid,fields,forces,np.int32(nx),np.int32(ny),np.int32(nz),np.float32(0),np.float32(.8),np.float32(0),np.int32(1)))
        f,g=g,f
    measured=float(np.mean(cp.asnumpy(fields[1])*sine[None,:,None])*2)
    # fields describe the pre-collision moments on the last step, which have
    # completed this many streaming operations.
    exact=.01*np.exp(-.1*(2*np.pi/ny)**2*steps)
    error=abs(measured/exact-1)
    check(f'shear decay ny={ny}',error<.015,dict(measured=measured,exact=exact,relative_error=error))
    check(f'periodic mass ny={ny}',abs(float(cp.mean(fields[0]))-1)<2e-5,float(cp.mean(fields[0])))

vel=np.zeros((3,8,8,8),np.float32);vel[0]=.03
f=cp.asarray(equilibrium(vel));g=cp.empty_like(f)
s=cp.zeros((8,8,8),cp.uint8);field=cp.empty((5,8,8,8),cp.float32);force=cp.empty((3,8,8,8),cp.float32)
for k in range(100):
    advance((4,),(128,),(f,g,s,field,force,np.int32(8),np.int32(8),np.int32(8),np.float32(.03),np.float32(.8),np.float32(.1),np.int32(1)))
    f,g=g,f
check('uniform flow remains uniform',np.max(np.abs(cp.asnumpy(field[1])-.03))<2e-6)
check('no body means no force',float(cp.max(cp.abs(force)))==0)

angle=np.deg2rad(104.52)
mol=np.array([[0,0,0],[OH,0,0],[OH*np.cos(angle),OH*np.sin(angle),0],[0,0,0]])
mol[3]=(1-2*WH)*mol[0]+WH*(mol[1]+mol[2])
pos=np.concatenate((mol+[.5,.5,.5],mol+[.8,.6,.5]))
scaled,box=scale_centers(pos,[3,3,8],.002)
check('test-area preserves volume',abs(np.prod(box)-72)<1e-12)
for i in (0,4):
    before=np.linalg.norm(pos[i:i+4,None]-pos[None,i:i+4],axis=-1)
    after=np.linalg.norm(scaled[i:i+4,None]-scaled[None,i:i+4],axis=-1)
    check(f'test-area preserves molecular geometry {i//4}',np.max(abs(after-before))<1e-14)
system=create_system(2,[3,3,3]);nb=system.getForce(0);nb.setNonbondedMethod(nb.NoCutoff)
charges=np.array([0,.5564,.5564,-1.1128]);d=np.linalg.norm(pos[:4,None,:]-pos[None,4:,:],axis=-1)
manual=float(138.93545764438198*np.sum(charges[:,None]*charges[None,:]/d)+4*.774907*((.31589/d[0,0])**12-(.31589/d[0,0])**6))
energies={}
for platform in ('Reference','OpenCL'):
    integ=mm.VerletIntegrator(.001);ctx=mm.Context(system,integ,mm.Platform.getPlatformByName(platform))
    ctx.setPositions(pos);ctx.computeVirtualSites()
    e=ctx.getState(getEnergy=True).getPotentialEnergy().value_in_unit(u.kilojoule_per_mole)
    energies[platform]=e
    check(f'independent dimer energy {platform}',abs(e-manual)<.002,dict(energy=e,manual=manual))
    del ctx,integ
report=dict(status='passed' if all(c['passed'] for c in checks) else 'failed',checks=checks)
(P/'runtime_verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['status']=='passed' else 1)
