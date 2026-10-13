"""Finite-reservoir equilibrium from specific measured sorption coefficients.
These coefficients cannot specify adsorption/desorption kinetics separately.
"""
from pathlib import Path
import json,csv,hashlib,unittest
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
def load():return json.loads((ROOT/'surface_data.json').read_text())['rows']
def partition(row, inventory_mol=1., gas_volume_m3=1., area_m2=None, OC_g=None,T=288.15,RH=.5,log_offset=0.):
    if abs(T-row['T_K'])>1e-8 or abs(RH-row['RH'])>1e-8:
        raise ValueError('No temperature/humidity extrapolation for this measurement.')
    if row['units']=='m3/m2':
        if area_m2 is None or OC_g is not None:raise ValueError('Soot coefficient requires surface area only.')
        loading=area_m2
    elif row['units']=='m3/g_OC':
        if OC_g is None or area_m2 is not None:raise ValueError('Mixed aerosol coefficient requires grams OC only.')
        loading=OC_g
    else:raise ValueError('Unknown normalization')
    if loading<0 or gas_volume_m3<=0 or inventory_mol<0:raise ValueError('Invalid inventory/geometry')
    K=10**(row['log10K']+log_offset);cap=K*loading/gas_volume_m3
    gas=inventory_mol/(1+cap);sorbed=inventory_mol-gas
    return dict(K=K,capacity_ratio=cap,gas_mol=gas,sorbed_mol=sorbed,fraction=cap/(1+cap))

class SurfaceTests(unittest.TestCase):
    def test_mass(self):
        r=partition(load()[0],area_m2=1.)
        self.assertAlmostEqual(r['gas_mol']+r['sorbed_mol'],1.)
    def test_normalization_guard(self):
        with self.assertRaises(ValueError):partition(load()[0],OC_g=1.)
    def test_T_guard(self):
        with self.assertRaises(ValueError):partition(load()[0],area_m2=1.,T=298.15)
    def test_RH_guard(self):
        with self.assertRaises(ValueError):partition(load()[0],area_m2=1.,RH=.9)
    def test_empty_surface(self):self.assertEqual(partition(load()[0],area_m2=0.)['fraction'],0.)
    def test_half_partition(self):
        row=load()[0];z=partition(row,area_m2=10**-row['log10K'])
        self.assertAlmostEqual(z['fraction'],.5)

def run():
    rows=[];out=ROOT/'results'
    fig,ax=plt.subplots(1,2,figsize=(10,3.6),layout='constrained')
    for row in load():
        loads=np.logspace(-4,1,6) if row['units']=='m3/m2' else np.logspace(-6,-3,4)
        vals=[]
        for value in loads:
            kw={'area_m2':value} if row['units']=='m3/m2' else {'OC_g':value}
            z=partition(row,RH=row['RH'],**kw)
            lo=partition(row,RH=row['RH'],log_offset=-row['log_error'],**kw)
            hi=partition(row,RH=row['RH'],log_offset=row['log_error'],**kw)
            rows.append(dict(**row,loading=value,loading_units='m2/m3_air' if row['units']=='m3/m2' else 'g_OC/m3_air',
                fraction=z['fraction'],fraction_low=lo['fraction'],fraction_high=hi['fraction']))
            vals.append(z['fraction']*100)
        if row['RH']==.5:
            idx=0 if row['units']=='m3/m2' else 1
            ax[idx].loglog(loads,vals,'o-',label=row['species'])
    ax[0].set(xlabel='Available soot area (m2 / m3 air)',ylabel='Equilibrium sorbed fraction (%)',title='Measured diesel-soot coefficients')
    ax[1].set(xlabel='Organic carbon loading (g / m3 air)',ylabel='Equilibrium sorbed fraction (%)',title='Measured mixed-aerosol coefficients')
    for a in ax:a.legend(fontsize=8);a.grid(alpha=.2)
    fig.suptitle('15 C, 50% RH; specified surfaces; equilibrium only')
    fig.savefig(out/'surface_partition.png',dpi=150,bbox_inches='tight');fig.savefig(out/'surface_partition.svg',bbox_inches='tight');plt.close(fig)
    with (out/'surface_partition.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,rows[0].keys());w.writeheader();w.writerows(rows)
    (out/'surface_summary.json').write_text(json.dumps(dict(measurements=9,equilibrium_cases=len(rows),
        soot_acetone_K_m=10**-5.08,tunnel_acetone_K_m3_gOC=10**-3.64,
        ethanol_soot_K_RH70_over_RH50=10**(-4.70+4.58),
        kinetic_validation=False,aging_law=False,
        input_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'surface_data.json',ROOT/'surface_partition.py')}),indent=2),encoding='utf-8')
    print('Surface equilibrium calculations:',len(rows))

if __name__=='__main__':run()
