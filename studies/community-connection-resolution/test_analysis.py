import unittest,itertools
import numpy as np
from analyze import scale,displacement,expected_displacement,shuffled

class TestMeasurements(unittest.TestCase):
    def test_source_units(self):
        x=np.array([[[-1,0,-1],[1,1,1]]*4],float)
        self.assertTrue(np.array_equal(scale(x), (x+np.array([1,0,1]))/np.array([2,1,2])))
    def test_no_cross_run_transition(self):
        x=np.repeat(np.arange(4)[None,:,None,None],3,axis=2)
        x=np.repeat(x,3,axis=3).reshape(1,12,3)
        d,n=displacement(x);self.assertEqual(n[0],8);self.assertEqual(d[0],0)
    def test_missing_not_zero(self):
        x=np.zeros((1,12,3));x[0,1]=np.nan
        self.assertEqual(displacement(x)[1][0],6)
        y=shuffled(x,np.random.default_rng(1));self.assertTrue(np.isnan(y[0,1]).all())
    def test_expected_null_against_exhaustive(self):
        c=np.array([[0,0,0],[1,0,0],[3,0,0]],float);x=np.tile(c,(4,1))[None]
        exhaustive=[np.mean(np.sum(np.diff(c[list(p)],axis=0)**2,axis=1)) for p in itertools.permutations(range(3))]
        self.assertAlmostEqual(expected_displacement(x)[0],np.mean(exhaustive))
    def test_shuffle_stays_person_and_chain(self):
        x=np.arange(2*12*3).reshape(2,12,3).astype(float);y=shuffled(x,np.random.default_rng(3))
        for p in range(2):
            for c in range(4):
                self.assertEqual(sorted(map(tuple,x[p,c*3:(c+1)*3])),sorted(map(tuple,y[p,c*3:(c+1)*3])))
    def test_invalid_scale_fails(self):
        with self.assertRaises(ValueError):scale(np.ones((1,160,3))*2)

if __name__=='__main__':unittest.main()
