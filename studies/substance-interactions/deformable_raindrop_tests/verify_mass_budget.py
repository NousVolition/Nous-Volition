"""Track numerical wall leakage separately from inlet/outlet mass transfer.

Linear interpolated bounce-back is not exactly mass conservative. This ledger
checks the discrete budget; it does not turn wall leakage into physical flux.
"""
from pathlib import Path
import json
import numpy as np
from flow_lbm import cp,C,W,OPP,equilibrium,advance
P=Path(__file__).resolve().parent
nx,ny,nz=64,32,32;N=nx*ny*nz;U=.03;a,b=4.,5.;center=np.array([24,16,16])
xyz=np.indices((nx,ny,nz));r=xyz-center[:,None,None,None]
solid=(r[0]/a)**2+(r[1]/b)**2+(r[2]/b)**2<=1
vel=np.zeros((3,nx,ny,nz),np.float32);vel[0]=U;vel[:,solid]=0
old=equilibrium(vel);f=cp.asarray(old);g=cp.empty_like(f);s=cp.asarray(solid,cp.uint8)
fields=cp.empty((5,nx,ny,nz),cp.float32);forces=cp.empty((7,nx,ny,nz),cp.float32)
links=[]
for q,c in enumerate(C):
    if q==0:continue
    source_solid=np.roll(solid,tuple(c),axis=(0,1,2));idx=np.where((~solid)&source_solid)
    if not len(idx[0]):continue
    rr=np.array(idx)-center[:,None];den=np.array([a*a,b*b,b*b])
    aa=np.sum(c*c/den);bb=np.sum(rr*c[:,None]/den[:,None],axis=0);cc=np.sum(rr*rr/den[:,None],axis=0)-1
    delta=np.clip((bb-np.sqrt(np.maximum(0,bb*bb-aa*cc)))/aa,0,1)
    away=tuple((idx[k]+c[k])%[nx,ny,nz][k] for k in range(3))
    links.append((q,idx,away,delta))
initial=old[:,~solid].sum(dtype=np.float64);body_total=0.;open_total=0.;records=[]
inlet=equilibrium(np.broadcast_to(np.array([U,0,0])[:,None,None,None],(3,1,ny,nz)))[:,0]
for step in range(1,301):
    body_flux=0.
    for q,idx,away,d in links:
        outgoing=old[(OPP[q],*idx)]
        # Separate branches avoid dividing by delta=0 in the unused formula.
        incoming=np.empty_like(d);small=d<.5
        incoming[small]=2*d[small]*outgoing[small]+(1-2*d[small])*old[(OPP[q],*away)][small]
        incoming[~small]=outgoing[~small]/(2*d[~small])+(2*d[~small]-1)/(2*d[~small])*old[(q,*idx)][~small]
        body_flux+=np.sum(incoming-outgoing,dtype=np.float64)
    outer=0.
    for q,c in enumerate(C):
        for plane in [0,nx-1]:
            source=np.roll(old[q,(plane-c[0])%nx],(c[1],c[2]),axis=(0,1))
            replacement=inlet[q] if plane==0 else old[q,nx-2]
            outer+=np.sum(replacement-source,dtype=np.float64)
    advance(((N+127)//128,),(128,),(f,g,s,fields,forces,*map(np.int32,[nx,ny,nz]),
      *map(np.float32,[U,.55,0]),np.int32(0),*map(np.float32,[*center,a,b]),np.int32(1)))
    f,g=g,f;old=cp.asnumpy(f)
    body_total+=body_flux;open_total+=outer
    mass=old[:,~solid].sum(dtype=np.float64)
    records.append([step,(mass-initial)/initial,body_total/initial,open_total/initial,
                    (mass-initial-body_total-open_total)/initial])
np.savetxt(P/'mass_budget.csv',records,delimiter=',',header='step,total_mass_change,unphysical_wall_leakage,inlet_outlet_transfer,budget_residual',comments='')
report=dict(status='passed' if max(abs(np.array(records)[:,-1]))<2e-6 else 'failed',
    initial_mass=initial,max_relative_budget_residual=float(max(abs(np.array(records)[:,-1]))),
    cumulative_unphysical_wall_leakage_relative=body_total/initial,
    cumulative_open_boundary_transfer_relative=open_total/initial,
    note='Budget closure is checked, not zero physical wall permeability. Production runs record total mass offsets but not a complete production flux ledger. This numerical boundary leak remains a limitation.')
(P/'mass_budget_verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert report['status']=='passed'
