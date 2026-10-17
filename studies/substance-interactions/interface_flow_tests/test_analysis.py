"""Analytical checks for derived observable units, balance and classification."""
import unittest
import numpy as np
from analyze import gamma, centered_z, CONVERT
from water_md import scale_centers, whole_molecules, MASS


class AnalysisChecks(unittest.TestCase):
    def test_surface_tension_two_interfaces(self):
        # Synthetic exact free energy F = 2*gamma*A + constant.
        names=['U_minus002','U_minus001','U_zero','U_plus001','U_plus002']
        rows=np.zeros(10,dtype=[(n,float) for n in names]);area=6.25;target=71.5
        for name,s in zip(names,[-.002,-.001,0,.001,.002]):
            rows[name]=-25000+2*target/CONVERT*area*s
        for s in [.001,.002]:self.assertAlmostEqual(gamma(rows,area,s),target,places=8)

    def test_area_translation_preserves_volume_and_bonds(self):
        rng=np.random.default_rng(3);xyz=rng.random((4,4,3))*.1+np.arange(4)[:,None,None]
        box=np.array([5.,5.,8.]);whole=whole_molecules(xyz,box)
        for s in [-.002,.002]:
            out,b=scale_centers(xyz,box,s);out=out.reshape(-1,4,3)
            self.assertAlmostEqual(np.prod(b),np.prod(box),places=10)
            np.testing.assert_allclose(out-out[:,0:1],whole-whole[:,0:1],atol=1e-14)
            self.assertAlmostEqual(b[0]*b[1]/(box[0]*box[1]),1+s,places=12)

    def test_slab_center_periodic_translation(self):
        xyz=np.zeros((10,3,3));xyz[:,:,2]=np.linspace(3,5,10)[:,None];box=np.array([2.5,2.5,8.])
        shifted=xyz.copy();shifted[:,:,2]+=4.5
        np.testing.assert_allclose(centered_z(xyz,box),centered_z(shifted,box),atol=1e-14)

    def test_volume_equivalent_force_balance(self):
        rhoa=1.204;rhow=998.2;g=9.80665;D=.0025;v=7.8
        for aspect in [.7,.84,1.]:
            a=D/2*aspect**(2/3);b=D/2*aspect**(-1/3)
            self.assertAlmostEqual(4*np.pi*a*b*b/3,np.pi*D**3/6,places=18)
            cd=4*(rhow-rhoa)*g*D/(3*rhoa*v*v)*aspect**(2/3)
            self.assertAlmostEqual(.5*rhoa*v*v*np.pi*b*b*cd,(rhow-rhoa)*g*np.pi*D**3/6,places=15)

if __name__=='__main__':unittest.main()
