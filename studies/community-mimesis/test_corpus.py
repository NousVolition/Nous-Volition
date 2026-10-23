import unittest
import numpy as np
from corpus_equations import *

class CorpusTests(unittest.TestCase):
    def test_alignment(self):np.testing.assert_array_equal(alignment(),np.zeros(4))
    def test_alignment_perturbation(self):
        p=POSITIONS.copy();p[2,1]+=1
        np.testing.assert_array_equal(alignment(p),[0,0,1,0])
    def test_product(self):
        for s,r in [(2,3),(-2,3),(0,4)]:
            for lam in [.01,1.,100.]:
                a,b=reciprocal(s,r,lam);self.assertAlmostEqual(a*b,s*r)
    def test_zero_scaling(self):
        with self.assertRaises(ValueError):reciprocal(1,1,0)
    def test_binary_table(self):
        for a,b in [(0,0),(0,1),(1,0),(1,1)]:self.assertEqual(compare_W(a,b,same_action=True,same_context=True),a==b)
    def test_context_abstention(self):self.assertIsNone(compare_W(0,1,same_action=True,same_context=False))
    def test_action_abstention(self):self.assertIsNone(compare_W(0,1,same_action=False,same_context=True))
    def test_exact_not_minimum(self):
        self.assertEqual(edge_candidates([0,1,2],[1,1,1],[.1,.2,.3],.1).tolist(),[0])
        self.assertEqual(edge_candidates([0,1,2],[1,1,1],[.1,.2,.3],.1,True).tolist(),[0,1,2])
    def test_empty_edge(self):self.assertEqual(len(edge_candidates([0],[1],[.2],.1)),0)
    def test_sharp(self):np.testing.assert_array_equal(response([-1,0,1],'sharp'),[0,0,1])
    def test_negative_tanh(self):self.assertAlmostEqual(float(response(-1,'tanh')),-.11920292202211755)
    def test_tanh_equivalence(self):
        q=np.linspace(-5,5,100);np.testing.assert_allclose(response(q,'tanh'),q*(1+np.tanh(q))/2,atol=1e-15)
    def test_smooth_off(self):
        self.assertEqual(float(response(-1,'smooth_off')),0);self.assertEqual(float(response(0,'smooth_off')),0)
        self.assertAlmostEqual(float(response(1,'smooth_off')),np.exp(-1))
    def test_calibrated_threshold(self):
        self.assertAlmostEqual(float(gradient_excess([2,0],2,.5,True)),0)
        self.assertLess(gradient_excess([2,0],2,.5),0)
    def test_force_reversal(self):
        self.assertGreater(force(-1,1,1,[1,0],'tanh')[0],0)
        self.assertLess(force(1,1,1,[1,0],'tanh')[0],0)
    def test_fixed_force_not_always_drag(self):
        f=force(1,1,1,[1,0],'sharp');self.assertGreater(np.dot([-1,0],f),0)
    def test_stress(self):np.testing.assert_array_equal(stress([[0,2],[-1,0]],3),[[0,3],[3,0]])
    def test_accumulation(self):
        A,M=memory_step(0,0,2,3,gamma=4,kappa=5);self.assertEqual(A,24);self.assertEqual(M,180)
    def test_no_silent_decay(self):self.assertEqual(memory_step(2,0,0,3),(2,6))
    def test_order_matters(self):
        a,m=memory_step(0,0,1,1);a,m=memory_step(a,m,0,1)
        b,n=memory_step(0,0,0,1);b,n=memory_step(b,n,1,1)
        self.assertEqual(a,b);self.assertEqual(m-n,1)
    def test_transport_total(self):
        _,s,A,M=transport(n=32,end=.5);self.assertAlmostEqual(A,.5,places=11);self.assertAlmostEqual(M,.125,places=11)
    def test_grid_refinement(self):
        err=[]
        for n in [16,32,64]:
            x,s,_,M=transport(n=n,end=.5,source=False)
            err.append(np.sqrt(np.mean((s-np.exp(-.05*.5)*np.sin(x-.4*.5))**2)))
            self.assertLess(abs(M),1e-12)
        self.assertGreater(err[0]/err[1],3.8);self.assertGreater(err[1]/err[2],3.8)

if __name__=='__main__':unittest.main()
