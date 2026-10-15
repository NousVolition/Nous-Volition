import unittest
import numpy as np
from run_external import verify_model, measurements, nominal, aggregate, jobs, stokes_velocity

class ExternalTests(unittest.TestCase):
    def test_rare_count_bounds_do_not_collapse(self):
        from uncertainty import count_mean_bounds
        lo,hi=count_mean_bounds(4,65536)
        self.assertLess(lo,4);self.assertGreater(hi,4)
        self.assertGreater(hi-lo,5)
    def test_rare_bound_coverage_independent_binomial(self):
        from scipy.stats import binom
        from uncertainty import count_mean_bounds
        n=100
        ranges=np.array([count_mean_bounds(k,n) for k in range(n+1)])
        for p in [.0001,.001,.01,.1,.5,.9,.99]:
            inside=(ranges[:,0]<=n*p)&(ranges[:,1]>=n*p)
            self.assertGreaterEqual(float(np.sum(binom.pmf(np.arange(n+1),n,p)[inside])),.95-1e-12)
    def test_frozen_hashes(self):verify_model()
    def test_diameter_radius_units(self):
        for r in measurements():
            p=nominal(r)
            self.assertAlmostEqual(p['A'],.000625)
            self.assertAlmostEqual(p['a']*2e6,r['daero_um']*.88)
    def test_all_rows_and_replicates_kept(self):
        rows=measurements();self.assertEqual([r['row'] for r in rows],list(range(1,9)))
        self.assertEqual(rows[0]['dphysical_um'],rows[1]['dphysical_um'])
        self.assertNotEqual(rows[0]['CE'],rows[1]['CE'])
        self.assertEqual(len(list(jobs(rows))),47)
    def test_source_mass_ratio_audit(self):
        ratios=[]
        for r in measurements():
            e=2*(r['drop_diameter_mm']*.001)/(3*1.3)*r['fluo_drop_g_cm3']/r['fluo_chamber_g_cm3']
            ratios.append(e/r['CE'])
            if r['row']!=6:self.assertLess(abs(e/r['CE']-1),.16)
        self.assertGreater(ratios[5],40)
        self.assertFalse(measurements()[5]['aggregate_eligible'])
    def test_nonzero_upper_bound_with_zero_hits(self):
        r=measurements()[0];p=nominal(r)
        batch=[dict(CE=0.,samples=4096,hits=0,censored_bound=0.,Re=1.,Pe=1.) for _ in range(4)]
        a=aggregate(batch,p)
        self.assertGreater(a['zero_hit_CE95_upper'],0)
        self.assertLess(a['zero_hit_CE95_upper'],7e-5)
    def test_inlet_bound(self):
        from run_external import phoretic_speeds
        for r in measurements():
            p=nominal(r);q=phoretic_speeds(p['A'],p['a'],p['T'],p['RH'])
            ph=(q['vdf']+q['vth'])/p['U']
            xyz=np.c_[np.linspace(0,1.2,1000),np.zeros(1000),np.full(1000,-8.)]
            flux=stokes_velocity(xyz)[:,2]+ph*xyz[:,2]/np.linalg.norm(xyz,axis=1)**3
            self.assertTrue(np.all(flux>0))
            self.assertTrue(np.all(flux<=1+abs(ph)/8**2))
    def test_censor_not_counted_as_capture(self):
        p=nominal(measurements()[0])
        batch=[dict(CE=.01,samples=4096,hits=100,censored_bound=.03,Re=1.,Pe=1.) for _ in range(4)]
        a=aggregate(batch,p)
        self.assertAlmostEqual(a['mean_CE'],.01)
        self.assertAlmostEqual(a['censored_mean'],.03)
        self.assertIsNone(a['zero_hit_CE95_upper'])

if __name__=='__main__':unittest.main(verbosity=2)
