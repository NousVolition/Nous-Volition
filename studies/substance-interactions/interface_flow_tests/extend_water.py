"""Continue a saved slab without refitting; fresh thermostat noise, same model.
Initial 300 ps showed broad block variation, so each primary run is extended
by 700 ps. This is a sampling extension, not selection by experimental fit.
"""
from pathlib import Path
import argparse,json,time,hashlib
import numpy as np
import openmm as mm
from openmm import unit as u
from water_md import P,create_system,make_context,whole_molecules,scale_centers,set_box


def extend(name,extra_ps=700):
    base=P/'water'/name;out=P/'water'/(name+'_extension')
    out.mkdir(exist_ok=True)
    if (out/'metadata.json').exists():raise RuntimeError('Extension already exists')
    meta=json.loads((base/'metadata.json').read_text());box=np.array(meta['box_nm'])
    n=meta['N'];dt=meta['dt_ps'];temp=meta['temperature_K'];start=time.monotonic()
    ctx,integ=make_context(create_system(n,box),meta['seed']+10000,dt,temp)
    ctx.setState(mm.XmlSerializer.deserialize((base/'final_state.xml').read_text()))
    evinteg=mm.VerletIntegrator(dt)
    ev=mm.Context(create_system(n,box),evinteg,mm.Platform.getPlatformByName('OpenCL'),{'Precision':'mixed'})
    strains=np.array([-.002,-.001,0.,.001,.002]);frames=[];rows=[]
    for k in range(extra_ps):
        integ.step(round(1/dt));st=ctx.getState(getPositions=True,getEnergy=True)
        xyz=whole_molecules(st.getPositions(asNumpy=True).value_in_unit(u.nanometer),box)
        energies=[]
        for strain in strains:
            p,b=scale_centers(xyz,box,strain);set_box(ev,b);ev.setPositions(p);ev.computeVirtualSites()
            energies.append(ev.getState(getEnergy=True).getPotentialEnergy().value_in_unit(u.kilojoule_per_mole))
        kinetic=st.getKineticEnergy().value_in_unit(u.kilojoule_per_mole)
        rows.append([k+1,2*kinetic/((6*n-3)*.008314462618),st.getPotentialEnergy().value_in_unit(u.kilojoule_per_mole),*energies])
        frames.append(xyz[:,:3].astype(np.float32))
        if (k+1)%100==0:print(name,'extension ps',k+1,flush=True)
    np.savez_compressed(out/'trajectory.npz',xyz_nm=frames,box_nm=box,strains=strains)
    np.savetxt(out/'samples.csv',rows,delimiter=',',header='time_ps,temperature_K,potential_kJ_mol,U_minus002,U_minus001,U_zero,U_plus001,U_plus002',comments='')
    (out/'final_state.xml').write_text(mm.XmlSerializer.serialize(ctx.getState(getPositions=True,getVelocities=True)))
    meta.update(name=name+'_extension',parent=name,production_ps=extra_ps,bulk_equil_ps=0,slab_equil_ps=0,
                elapsed_s=time.monotonic()-start,extension_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                note='Continuation with unchanged Hamiltonian and fresh Langevin noise, grouped with its parent for uncertainty')
    (out/'metadata.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--extra',type=int,default=700)
    a=p.parse_args();extend(a.name,a.extra)
