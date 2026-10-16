import unittest
import numpy as np
from raindrop_model import *

class ModelTests(unittest.TestCase):
    def test_heat_balance(self):
        for D in [.0005,.00125,.003,.005]:
            for rh in [.3,.77,1.]:
                z=efficiency(D,1e-6,RH=rh)
                self.assertLess(abs(z['heat_residual_W_m2']),1e-6)
                self.assertLessEqual(z['surface_T_K'],293.15)
    def test_saturation_control(self):
        z=efficiency(.00125,1e-6,RH=1.)
        self.assertAlmostEqual(z['thermo'],0,14)
        self.assertAlmostEqual(z['diffusio'],0,14)
    def test_published_rear_reference(self):
        # Golden value generated independently with Jones author's released code.
        import json
        from pathlib import Path
        p=Path(__file__).with_name('author_benchmark.json')
        for row in json.loads(p.read_text()):
            z=efficiency(row['D'],row['d'],T=293.15,RH=.8,rho_p=1500,U=row['U'],phoresis=False)
            for key in ['brownian','interception','rear']:
                self.assertLess(abs(z[key]-row[key])/max(row[key],1e-20),.003)
    def test_terminal_speed_physical_range(self):
        u=[terminal_speed(x) for x in [.0001,.0005,.001,.002,.003,.005]]
        self.assertTrue(np.all(np.diff(u)>0))
        self.assertTrue(8<u[-1]<10)
    def test_rear_domain(self):
        z=efficiency(.004,1e-6)
        self.assertFalse(z['rear_in_domain']);self.assertEqual(z['rear'],0)
    def test_impaction_threshold(self):
        a=efficiency(.002,.1e-6);b=efficiency(.002,8e-6)
        self.assertEqual(a['impaction'],0);self.assertGreater(b['impaction'],0)
    def test_mass_accounting(self):
        a,c,l=inventory(.1,.003,8,100,1e8,np.linspace(0,100,501))
        np.testing.assert_allclose(a+c,1e8,rtol=1e-15)
        self.assertTrue(np.all(np.diff(a)<=0));self.assertGreater(l,0)
    def test_no_collection_control(self):
        a,c,l=inventory(0,.003,8,100,1e8,[0,10,100])
        np.testing.assert_array_equal(c,0);self.assertEqual(l,0)
    def test_distribution_limit(self):
        a=distribution(.00125,1e-6,gsd=1.)
        b=distribution(.00125,1e-6,gsd=1.000001)
        for k in COMPONENTS:self.assertAlmostEqual(a[k],b[k],places=9)
    def test_quadrature_refinement(self):
        a=distribution(.003,3e-6,gsd=1.3,moment=3,eps=1e-5)
        b=distribution(.003,3e-6,gsd=1.3,moment=3,eps=1e-8)
        self.assertLess(abs(a['total']/b['total']-1),1e-4)
    def test_input_guards(self):
        for args in [(0,1e-6),(.001,-1),(.001,.0005)]:
            with self.assertRaises(ValueError):efficiency(*args)
        with self.assertRaises(ValueError):terminal_speed(.009)
    def test_brownian_size_trend(self):
        self.assertGreater(efficiency(.001,.01e-6)['brownian'],efficiency(.001,.1e-6)['brownian'])

if __name__=='__main__':unittest.main(verbosity=2)
