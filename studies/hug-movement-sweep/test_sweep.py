import copy,hashlib,unittest
import numpy as np
from model import ROOT,Hug,configured,protocol
from analyze import cycle_period

class SweepChecks(unittest.TestCase):
    def test_pinned_equations(self):
        for f,sha in protocol()['pinned_sources'].items():self.assertEqual(hashlib.sha256((ROOT/f).read_bytes()).hexdigest(),sha,f)
    def test_memory_and_material_parameters_unchanged(self):
        source=protocol()
        for r in source['sweep']['scales']:
            p=configured(r)
            for k in ['field','clay','events','scenarios','orbit_period_s','pause_s']:self.assertEqual(p[k],source[k])
            self.assertEqual(p['mechanics']['scale_m'],source['mechanics']['scale_m'])
    def test_scale_symmetry_without_memory_force(self):
        # Independent analytic scaling: q,v,strains scale as r, work as r^2.
        p=configured(1);p['field']['response_strength_Pa']=0;m=Hug(p,32)
        rng=np.random.default_rng(43);z=rng.normal(size=m.initial().shape);base=m.rhs(123,z)
        for r in [3,100,300]:
            p2=configured(r);p2['field']['response_strength_Pa']=0;m2=Hug(p2,32);zz=z.copy();zz[:,:4]*=r;zz[:,-5:]*=r*r;out=m2.rhs(123,zz)
            np.testing.assert_allclose(out[:,:4]/r,base[:,:4],atol=1e-13,rtol=1e-12)
            np.testing.assert_allclose(out[:,-5:]/r**2,base[:,-5:],atol=1e-13,rtol=1e-12)
    def test_lower_pair_terms_zero_at_arbitrary_states(self):
        m=Hug(configured(300),32);rng=np.random.default_rng(44)
        for size in [1e-10,1,1e9]:
            S=rng.normal(size=(12,32))*size;terms=m.exchange(S)
            np.testing.assert_array_equal(terms[:,m.y<0],0)
            np.testing.assert_allclose(terms.sum(axis=1),0,atol=1e-16)
    def test_fixed_orbit_control_only_changes_force(self):
        p=configured(100);fixed=configured(100,'fixed');expected=copy.deepcopy(p);expected['orbital_force_rms_N']/=100
        self.assertEqual(expected,fixed)
    def test_period_from_known_harmonic(self):
        t=np.arange(0,1800.01,.5);w=2*np.pi/2.85
        period=cycle_period(t,30*np.sin(w*t)+.2,30*w*np.cos(w*t))
        self.assertAlmostEqual(period,2.85,places=4)
    def test_no_period_is_not_infinite_period(self):
        t=np.arange(0,1801.);self.assertIsNone(cycle_period(t,np.zeros_like(t),np.zeros_like(t)))
    def test_invalid_inputs(self):
        for r,policy in [(0,'scaled'),(-1,'scaled'),(1,'unknown')]:
            with self.assertRaises(ValueError):configured(r,policy)
if __name__=='__main__':unittest.main()
