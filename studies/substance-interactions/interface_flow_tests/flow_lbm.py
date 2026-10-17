"""3D external flow around a fixed no-slip spheroid; NOT deformable-drop DNS.
D3Q19 regularized isothermal lattice Boltzmann; optional Smagorinsky closure.
Units are lattice units. Streamwise x, transverse periodic y/z; inlet/outlet x.
"""
from pathlib import Path
import argparse, json, time, hashlib
import numpy as np
from gpu_environment import configure
configure()
import cupy as cp

P=Path(__file__).resolve().parent
C=np.array([[0,0,0],[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1],
 [1,1,0],[-1,-1,0],[1,-1,0],[-1,1,0],[1,0,1],[-1,0,-1],[1,0,-1],[-1,0,1],
 [0,1,1],[0,-1,-1],[0,1,-1],[0,-1,1]],dtype=int)
W=np.array([1/3]+[1/18]*6+[1/36]*12)
OPP=np.array([np.where(np.all(C==-c,axis=1))[0][0] for c in C])

KERNEL=r'''
extern "C" __global__ void advance(const float* old, float* out, const unsigned char* solid,
 float* fields, float* forces, int nx,int ny,int nz,float U,float tau0,float cs,int periodic) {
 int id=blockDim.x*blockIdx.x+threadIdx.x; int N=nx*ny*nz;
 if(id>=N)return;
 int z=id%nz,y=(id/nz)%ny,x=id/(ny*nz);
 const int cx[19]={0,1,-1,0,0,0,0,1,-1,1,-1,1,-1,1,-1,0,0,0,0};
 const int cy[19]={0,0,0,1,-1,0,0,1,-1,-1,1,0,0,0,0,1,-1,1,-1};
 const int cz[19]={0,0,0,0,0,1,-1,0,0,0,0,1,-1,-1,1,1,-1,-1,1};
 const int op[19]={0,2,1,4,3,6,5,8,7,10,9,12,11,14,13,16,15,18,17};
 float f[19],eq[19];double rho=0;float ux=0,uy=0,uz=0,fx=0,fy=0,fz=0;
 double restsum=0;
 for(int q=0;q<19;q++){
  float w=q==0?1.f/3:(q<7?1.f/18:1.f/36);
  if(solid[id]) f[q]=w;
  else if(!periodic && x==0){float cu=cx[q]*U;f[q]=w*(1+3*cu+4.5f*cu*cu-1.5f*U*U);}
  else if(!periodic && x==nx-1)f[q]=old[q*N+id-ny*nz];
  else{
   int sx=(x-cx[q]+nx)%nx,sy=(y-cy[q]+ny)%ny,sz=(z-cz[q]+nz)%nz;
   int src=(sx*ny+sy)*nz+sz;
   if(solid[src]){f[q]=old[op[q]*N+id];fx-=2*f[q]*cx[q];fy-=2*f[q]*cy[q];fz-=2*f[q]*cz[q];}
   else f[q]=old[q*N+src];
  }
  rho+=f[q];ux+=f[q]*cx[q];uy+=f[q]*cy[q];uz+=f[q]*cz[q];
 }
 ux/=rho;uy/=rho;uz/=rho;
 float pxx=0,pyy=0,pzz=0,pxy=0,pxz=0,pyz=0;
 for(int q=0;q<19;q++){
  float w=q==0?1.f/3:(q<7?1.f/18:1.f/36),cu=cx[q]*ux+cy[q]*uy+cz[q]*uz;
  eq[q]=w*rho*(1+3*cu+4.5f*cu*cu-1.5f*(ux*ux+uy*uy+uz*uz));
  float ne=f[q]-eq[q];
  pxx+=ne*cx[q]*cx[q];pyy+=ne*cy[q]*cy[q];pzz+=ne*cz[q]*cz[q];
  pxy+=ne*cx[q]*cy[q];pxz+=ne*cx[q]*cz[q];pyz+=ne*cy[q]*cz[q];
 }
 float norm=sqrtf(2*(pxx*pxx+pyy*pyy+pzz*pzz+2*(pxy*pxy+pxz*pxz+pyz*pyz)));
 float tau=.5f*(tau0+sqrtf(tau0*tau0+18*cs*cs*norm/rho));
 for(int q=0;q<19;q++){
  float w=q==0?1.f/3:(q<7?1.f/18:1.f/36);
  float reg=4.5f*w*((cx[q]*cx[q]-1.f/3)*pxx+(cy[q]*cy[q]-1.f/3)*pyy+
   (cz[q]*cz[q]-1.f/3)*pzz+2*(cx[q]*cy[q]*pxy+cx[q]*cz[q]*pxz+cy[q]*cz[q]*pyz));
  out[q*N+id]=eq[q]+(1-1/tau)*reg;
  if(q>0)restsum+=(double)out[q*N+id];
 }
 // The rest population carries the floating-point mass residual; momentum
 // is unchanged. Double accumulation avoids systematic float summation drift.
 out[id]=(float)(rho-restsum);
 fields[id]=rho;fields[N+id]=ux;fields[2*N+id]=uy;fields[3*N+id]=uz;fields[4*N+id]=tau;
 forces[id]=fx;forces[N+id]=fy;forces[2*N+id]=fz;
}
'''
advance=cp.RawKernel(KERNEL,'advance')


def equilibrium(velocity):
    vel=np.asarray(velocity,dtype=np.float32)
    cu=np.einsum('qd,dxyz->qxyz',C,vel)
    return (W[:,None,None,None]*(1+3*cu+4.5*cu*cu-1.5*np.sum(vel*vel,axis=0))).astype(np.float32)


def run(name, diameter=20, reynolds=1500., aspect=.7, speed=.06, width=5., length=12., duration=40., cs=.1, seed=31):
    folder=P/'flow'/name;folder.mkdir(parents=True,exist_ok=True)
    if (folder/'metadata.json').exists():raise RuntimeError('Run exists')
    start=time.monotonic();D=diameter
    nx,ny,nz=round(length*D),round(width*D),round(width*D)
    center=np.array([3*D,ny/2,nz/2]);a=D/2*aspect**(2/3);b=D/2*aspect**(-1/3)
    x,y,z=np.ogrid[:nx,:ny,:nz]
    solid=(((x-center[0])/a)**2+((y-center[1])/b)**2+((z-center[2])/b)**2<=1)
    solid_gpu=cp.asarray(solid,dtype=cp.uint8)
    vel=np.zeros((3,nx,ny,nz),dtype=np.float32);vel[0]=speed
    rng=np.random.default_rng(seed)
    # Small zero-mean transverse initial perturbation seeds wake symmetry breaking.
    vel[1:]=rng.normal(0,speed*1e-3,size=vel[1:].shape)
    vel[:,solid]=0
    f=cp.asarray(equilibrium(vel));g=cp.empty_like(f)
    fields=cp.empty((5,nx,ny,nz),dtype=cp.float32)
    forces=cp.empty((3,nx,ny,nz),dtype=cp.float32)
    tau0=.5+3*speed*D/reynolds
    steps=round(duration*D/speed);rows=[];mean_slice=np.zeros((4,nx,ny));ns=0
    area=np.pi*b*b;initial_mass=float(np.count_nonzero(~solid))
    print(name,'grid',nx,ny,nz,'steps',steps,'tau',tau0,flush=True)
    for step in range(1,steps+1):
        advance(((nx*ny*nz+127)//128,),(128,),
          (f,g,solid_gpu,fields,forces,np.int32(nx),np.int32(ny),np.int32(nz),np.float32(speed),np.float32(tau0),np.float32(cs),np.int32(0)))
        f,g=g,f
        if step%100==0 or step==steps:
            force=cp.asnumpy(forces.sum(axis=(1,2,3),dtype=cp.float64))
            stats=[float(cp.min(fields[0])),float(cp.max(fields[0])),
                   float(cp.max(cp.sqrt(cp.sum(fields[1:4]**2,axis=0)))),
                   float(cp.sum(fields[0][~solid_gpu.astype(bool)],dtype=cp.float64))/initial_mass-1,
                   float(cp.max(fields[4]))]
            t=step*speed/D
            rows.append([t,*force/(.5*speed**2*area),*stats])
            if t>=duration/2:
                mean_slice+=cp.asnumpy(fields[:4,:,:,nz//2]);ns+=1
            if not np.isfinite(stats).all() or stats[0]<.8 or stats[1]>1.2 or stats[2]>.35:
                print('NUMERICAL GUARD FAILED',rows[-1],flush=True);break
            if step%5000==0:print(name,'tU/D',round(t,2),'Cd',round(rows[-1][1],4),'elapsed',round(time.monotonic()-start),flush=True)
    np.savetxt(folder/'history.csv',rows,delimiter=',',header='tU_D,Cd_projected,Cl_y,Cl_z,rho_min,rho_max,max_speed_lattice,mass_relative,tau_max',comments='')
    np.savez_compressed(folder/'slices.npz',instant=cp.asnumpy(fields[:4,:,:,nz//2]),
                         mean=mean_slice/max(ns,1),solid=solid[:,:,nz//2],center=center,
                         D=D,speed=speed,mean_samples=ns)
    meta=dict(name=name,D_lattice=D,Re_D=reynolds,aspect=aspect,speed=speed,width_D=width,length_D=length,
              duration_requested=duration,duration_completed=step*speed/D,cs=cs,seed=seed,tau0=tau0,
              grid=[nx,ny,nz],projected_area_lattice=area,body_volume_voxels=int(solid.sum()),
              exact_body_volume=np.pi*D**3/6,elapsed_s=time.monotonic()-start,
              status='completed' if step==steps else 'numerical_guard_failed',
              source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              notes='Fixed no-slip body; periodic transverse domain; regularized LES if Cs>0; no evolving liquid surface')
    (folder/'metadata.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--name',required=True)
    for key,default,typ in [('diameter',20,int),('reynolds',1500.,float),('aspect',.7,float),('speed',.06,float),('width',5.,float),('length',12.,float),('duration',40.,float),('cs',.1,float),('seed',31,int)]:
        ap.add_argument('--'+key,type=typ,default=default)
    run(**vars(ap.parse_args()))
