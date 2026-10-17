"""Independent mass budget for the solver's open-boundary replacement rule.

Compare total fluid-population mass change with the exact mass supplied by
the inlet/outlet rule, referenced to otherwise periodic streaming. The body
is internal; halfway bounce-back redistributes mass without creating it.
"""
import json
import numpy as np
from flow_lbm import P,cp,C,equilibrium,advance


def run():
    nx,ny,nz=64,32,32;U=.03
    x,y,z=np.ogrid[:nx,:ny,:nz];mask=(x-24)**2+(y-16)**2+(z-16)**2<=4**2
    velocity=np.zeros((3,nx,ny,nz),np.float32);velocity[0]=U;velocity[:,mask]=0
    f=cp.asarray(equilibrium(velocity));g=cp.empty_like(f);solid=cp.asarray(mask,dtype=cp.uint8)
    fields=cp.empty((5,nx,ny,nz),cp.float32);forces=cp.empty((3,nx,ny,nz),cp.float32)
    mass=lambda v:float(cp.sum(v[:,~cp.asarray(mask)],dtype=cp.float64))
    start=mass(f);previous=start;supplied=0.;rows=[]
    for step in range(100):
        # Summing over the full transverse plane removes any y/z permutation.
        planes=cp.asnumpy(f.sum(axis=(2,3),dtype=cp.float64))
        periodic_in=sum(planes[q,(-C[q,0])%nx] for q in range(19))
        periodic_out=sum(planes[q,(nx-1-C[q,0])%nx] for q in range(19))
        inlet_mass=float(equilibrium(np.array([U,0,0],dtype=np.float32)[:,None,None,None]).sum(dtype=np.float64))*ny*nz
        source=inlet_mass+planes[:,nx-2].sum()-periodic_in-periodic_out
        advance(((nx*ny*nz+127)//128,),(128,),(f,g,solid,fields,forces,
            np.int32(nx),np.int32(ny),np.int32(nz),np.float32(U),np.float32(.56),np.float32(.1),np.int32(0)))
        f,g=g,f;current=mass(f);supplied+=source
        rows.append([step+1,current-start,supplied,(current-previous-source)/start]);previous=current
    rows=np.array(rows)
    result=dict(steps=100,initial_mass=start,net_boundary_mass_supplied=supplied,actual_mass_change=previous-start,
                relative_budget_residual=(previous-start-supplied)/start,
                maximum_step_relative_residual=float(abs(rows[:,3]).max()),
                scope='Independent boundary accounting control; production histories do not store full boundary-population fluxes.')
    result['passed']=abs(result['relative_budget_residual'])<2e-6 and result['maximum_step_relative_residual']<1e-6
    np.savetxt(P/'boundary_budget.csv',rows,delimiter=',',header='step,mass_change,boundary_mass_supplied,step_relative_residual',comments='')
    (P/'boundary_budget.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':run()
