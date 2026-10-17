"""GPU TIP4P/2005 slab MD plus constant-volume molecular test-area samples.
Parameters: Abascal & Vega, JCP 123,234505 (2005). Test area: Vega & de
Miguel, JCP126,154707 (2007). All lengths nm, energies kJ/mol in OpenMM.
"""
from pathlib import Path
import argparse, json, time, hashlib
import numpy as np
import openmm as mm
from openmm import app, unit as u

P = Path(__file__).resolve().parent
OH = .09572
HH = 2*OH*np.sin(np.deg2rad(104.52/2))
WH = .01546/(2*OH*np.cos(np.deg2rad(104.52/2)))
MASS = np.array([15.99943, 1.007947, 1.007947, 0.])


def create_system(n, box, cutoff=1.):
    system = mm.System()
    system.setDefaultPeriodicBoxVectors(*[mm.Vec3(*v) for v in np.diag(box)])
    nb = mm.NonbondedForce()
    nb.setNonbondedMethod(nb.LJPME)
    nb.setCutoffDistance(cutoff)
    nb.setEwaldErrorTolerance(1e-5)
    nb.setUseDispersionCorrection(False)
    for i in range(n):
        for j in range(4):
            system.addParticle(float(MASS[j]))
            nb.addParticle([0, .5564, .5564, -1.1128][j], .31589,
                           .774907 if j == 0 else 0.)
        b = 4*i
        system.addConstraint(b,b+1,OH)
        system.addConstraint(b,b+2,OH)
        system.addConstraint(b+1,b+2,HH)
        system.setVirtualSite(b+3, mm.ThreeParticleAverageSite(b,b+1,b+2,1-2*WH,WH,WH))
        for j in range(4):
            for k in range(j):
                nb.addException(b+j,b+k,0,1,0)
    system.addForce(nb)
    system.addForce(mm.CMMotionRemover())
    return system


def whole_molecules(pos, box):
    xyz = np.asarray(pos).reshape(-1,4,3).copy()
    delta = xyz - xyz[:,0:1,:]
    delta -= box*np.rint(delta/box)
    return xyz[:,0:1,:] + delta


def scale_centers(pos, box, strain):
    """Change EACH interface area by factor 1+strain, volume constant.
    Translate rigid molecules by their center of mass; do not stretch bonds.
    """
    xyz = whole_molecules(pos, np.asarray(box))
    centers = np.sum(xyz*MASS[None,:,None],axis=1)/MASS.sum()
    scale = np.array([np.sqrt(1+strain), np.sqrt(1+strain), 1/(1+strain)])
    return (xyz+(centers*(scale-1))[:,None,:]).reshape(-1,3), np.asarray(box)*scale


def set_box(ctx, box):
    ctx.setPeriodicBoxVectors(*[mm.Vec3(*v) for v in np.diag(box)])


def make_context(system, seed, dt, temperature):
    integ = mm.LangevinMiddleIntegrator(temperature, 1., dt)
    integ.setConstraintTolerance(1e-7)
    integ.setRandomNumberSeed(seed)
    platform = mm.Platform.getPlatformByName('OpenCL')
    ctx = mm.Context(system, integ, platform, {'Precision':'mixed'})
    return ctx, integ


def run(name, seed=101, lateral=2.5, dt=.002, bulk_ps=100., equil_ps=200., sample_ps=300., temperature=298.15):
    out=P/'water'/name
    out.mkdir(parents=True,exist_ok=True)
    if (out/'metadata.json').exists():
        raise RuntimeError('Completed run already exists; choose a new run name')
    start=time.monotonic()
    mod=app.Modeller(app.Topology(),[])
    mod.addSolvent(app.ForceField('tip4pew.xml'),model='tip4pew',
                   boxSize=mm.Vec3(lateral,lateral,lateral)*u.nanometer)
    # Starting geometry only comes from OpenMM solvent packing. The force
    # field used for integration is constructed above, not TIP4P/Ew.
    pos=mod.positions.value_in_unit(u.nanometer)
    pos=np.asarray(pos)
    names=[a.name for a in mod.topology.atoms()]
    assert all(names[i:i+4]==['O','H1','H2','M'] for i in range(0,len(names),4)), names[:4]
    n=len(pos)//4
    bulk_box=np.full(3,lateral)
    ctx,integ=make_context(create_system(n,bulk_box),seed,dt,temperature)
    ctx.setPositions(pos)
    ctx.applyConstraints(1e-7)
    ctx.computeVirtualSites()
    mm.LocalEnergyMinimizer.minimize(ctx,10.,1000)
    ctx.setVelocitiesToTemperature(temperature,seed)
    print(name,'molecules',n,'bulk equilibration',flush=True)
    integ.step(round(bulk_ps/dt))
    pos=ctx.getState(getPositions=True).getPositions(asNumpy=True).value_in_unit(u.nanometer)
    xyz=whole_molecules(pos,bulk_box)
    xyz-=lateral*np.floor(xyz[:,0:1,:]/lateral)
    box=np.array([lateral,lateral,8.0])
    xyz[:,:,2]+=(box[2]-lateral)/2
    del ctx,integ
    ctx,integ=make_context(create_system(n,box),seed+1,dt,temperature)
    ctx.setPositions(xyz.reshape(-1,3))
    ctx.computeVirtualSites()
    ctx.setVelocitiesToTemperature(temperature,seed+1)
    print(name,'slab equilibration',flush=True)
    for _ in range(round(equil_ps/10)):
        integ.step(round(10/dt))
    # Separate evaluation context: area perturbations never alter sampled dynamics.
    eval_integ=mm.VerletIntegrator(dt)
    eval_ctx=mm.Context(create_system(n,box),eval_integ,
                        mm.Platform.getPlatformByName('OpenCL'),{'Precision':'mixed'})
    strains=np.array([-.002,-.001,0.,.001,.002])
    frames=[]; records=[]
    for k in range(round(sample_ps)):
        integ.step(round(1/dt))
        state=ctx.getState(getPositions=True,getEnergy=True)
        xyz=whole_molecules(state.getPositions(asNumpy=True).value_in_unit(u.nanometer),box)
        energies=[]
        for strain in strains:
            transformed, b=scale_centers(xyz,box,strain)
            set_box(eval_ctx,b)
            eval_ctx.setPositions(transformed)
            eval_ctx.computeVirtualSites()
            energies.append(eval_ctx.getState(getEnergy=True).getPotentialEnergy().value_in_unit(u.kilojoule_per_mole))
        kinetic=state.getKineticEnergy().value_in_unit(u.kilojoule_per_mole)
        dof=6*n-3
        temp=2*kinetic/(dof*.008314462618)
        frames.append(xyz[:,:3,:].astype(np.float32))
        records.append([k+1,temp,state.getPotentialEnergy().value_in_unit(u.kilojoule_per_mole),*energies])
        if (k+1)%50==0:
            print(name,'sample ps',k+1,'elapsed_s',round(time.monotonic()-start,1),flush=True)
    np.savez_compressed(out/'trajectory.npz',xyz_nm=np.asarray(frames),box_nm=box,strains=strains)
    np.savetxt(out/'samples.csv',records,delimiter=',',header='time_ps,temperature_K,potential_kJ_mol,U_minus002,U_minus001,U_zero,U_plus001,U_plus002',comments='')
    state=ctx.getState(getPositions=True,getVelocities=True)
    (out/'final_state.xml').write_text(mm.XmlSerializer.serialize(state))
    meta=dict(name=name,seed=seed,N=n,box_nm=box.tolist(),dt_ps=dt,temperature_K=temperature,
              bulk_equil_ps=bulk_ps,slab_equil_ps=equil_ps,production_ps=sample_ps,
              sample_interval_ps=1.,platform='OpenCL mixed precision',openmm=mm.__version__,
              source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              elapsed_s=time.monotonic()-start,model='TIP4P/2005, LJPME+PME',
              note='Exploratory small-slab run. No empirical parameter fit; all sample frames retained.')
    (out/'metadata.json').write_text(json.dumps(meta,indent=2))
    print(json.dumps(meta),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--name',required=True);ap.add_argument('--seed',type=int,default=101)
    ap.add_argument('--lateral',type=float,default=2.5);ap.add_argument('--dt',type=float,default=.002)
    ap.add_argument('--bulk',type=float,default=100);ap.add_argument('--equil',type=float,default=200)
    ap.add_argument('--sample',type=float,default=300)
    a=ap.parse_args()
    run(a.name,a.seed,a.lateral,a.dt,a.bulk,a.equil,a.sample)
