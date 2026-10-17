"""Short unthermostatted energy check from the same saved liquid slab.

This tests numerical integration, not equilibrium sampling or model accuracy.
"""
from pathlib import Path
import json
import numpy as np
import openmm as mm
from openmm import unit as u
from water_md import P, create_system


def run():
    folder=P/'water/primary_seed101';meta=json.loads((folder/'metadata.json').read_text())
    saved=mm.XmlSerializer.deserialize((folder/'final_state.xml').read_text())
    rows=[];summary=[]
    for dt in [.002,.001]:
        integ=mm.VerletIntegrator(dt);integ.setConstraintTolerance(1e-7)
        ctx=mm.Context(create_system(meta['N'],meta['box_nm']),integ,
            mm.Platform.getPlatformByName('OpenCL'),{'Precision':'mixed'})
        ctx.setState(saved);energies=[]
        for i in range(101):
            state=ctx.getState(getEnergy=True)
            energy=(state.getPotentialEnergy()+state.getKineticEnergy()).value_in_unit(u.kilojoule_per_mole)
            energies.append(energy);rows.append([dt*1000,i*.1,energy])
            if i<100:integ.step(round(.1/dt))
        values=np.array(energies);times=np.arange(101)*.1
        summary.append(dict(dt_fs=dt*1000,duration_ps=10.,N=meta['N'],
           drift_kJ_mol_molecule_per_ps=float(np.polyfit(times,values,1)[0]/meta['N']),
           energy_range_kJ_mol_per_molecule=float(np.ptp(values)/meta['N']),
           max_relative_energy_deviation=float(np.max(np.abs(values-values[0]))/abs(values[0]))))
        del ctx,integ
    np.savetxt(P/'nve_energy.csv',rows,delimiter=',',header='dt_fs,time_ps,total_energy_kJ_mol',comments='')
    (P/'nve_check.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))

if __name__=='__main__':run()
