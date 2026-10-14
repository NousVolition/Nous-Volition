import unittest
from dataclasses import replace
import numpy as np
from model import make_community,solve,permute,POLICIES

class Tests(unittest.TestCase):
    def setUp(self):self.c=make_community(31000)
    def test_equal_edge_counts(self):
        self.assertEqual((self.c.connected.sum()-7)//2,9)
        self.assertEqual((self.c.partitioned.sum()-7)//2,9)
    def test_analytic_isolated(self):
        z=solve(self.c,graph='self')['met']
        exact=np.minimum(1,self.c.requested/np.sum(self.c.demand/self.c.skills,axis=1))
        np.testing.assert_allclose(z,exact,atol=2e-8,rtol=0)
    def test_analytic_identical(self):
        c=replace(self.c,skills=np.ones((7,2)),demand=np.ones((7,2))*.5,requested=np.ones(7)*.6)
        z=solve(c)
        self.assertAlmostEqual(z['met'].mean(),.6,places=8)
    def test_zero_budget(self):
        c=replace(self.c,requested=np.zeros(7))
        self.assertEqual(solve(c)['metrics']['mean_needs_met'],0)
    def test_all_constraints(self):
        for options in POLICIES.values():
            z=solve(self.c,**options)
            self.assertLess(z['metrics']['constraint_residual'],1e-7)
            self.assertLess(z['metrics']['max_supply_violation'],1e-7)
            self.assertLess(z['metrics']['max_need_violation'],1e-7)
            self.assertLess(z['metrics']['optimality_loss'],2e-8)
    def test_forbidden_edges(self):
        z=solve(self.c,graph='partitioned')
        np.testing.assert_allclose(z['flow'][~z['allowed']],0,atol=1e-12)
    def test_recording_is_inert(self):
        a=solve(self.c);b=solve(self.c,recording=True)
        np.testing.assert_array_equal(a['flow'],b['flow'])
    def test_labels_are_inert(self):
        a=solve(self.c);b=solve(replace(self.c,labels=tuple(reversed(self.c.labels))))
        np.testing.assert_array_equal(a['flow'],b['flow'])
    def test_neutral_priority_exact_control(self):
        a=solve(self.c);b=solve(self.c,priority=1.,leader=5)
        np.testing.assert_array_equal(a['flow'],b['flow'])
    def test_self_subset(self):
        self.assertGreaterEqual(solve(self.c)['metrics']['mean_needs_met']+1e-8,solve(self.c,graph='self')['metrics']['mean_needs_met'])
    def test_complete_graph_upper_bound(self):
        self.assertGreaterEqual(solve(self.c,graph='complete')['metrics']['mean_needs_met']+1e-8,solve(self.c)['metrics']['mean_needs_met'])
    def test_relaxation_cannot_lower_optimal_total(self):
        self.assertGreaterEqual(solve(self.c,respect=False)['metrics']['mean_needs_met']+1e-8,solve(self.c)['metrics']['mean_needs_met'])
    def test_assessment_cannot_raise_optimal_total(self):
        self.assertLessEqual(solve(self.c,assessment=.1)['metrics']['mean_needs_met'],solve(self.c)['metrics']['mean_needs_met']+1e-8)
    def test_priority_increases_weighted_objective(self):
        a=solve(self.c);b=solve(self.c,priority=3)
        self.assertGreaterEqual(b['weights']@b['met']+1e-8,b['weights']@a['met'])
    def test_requested_time_respected(self):
        for name in ('independent','reciprocal','partitioned','priority_hierarchy','costly_assessment'):
            self.assertLess(solve(self.c,**POLICIES[name])['metrics']['total_excess_over_requests'],1e-7)
    def test_identity_reindexing(self):
        order=np.array([2,5,1,0,6,4,3]);leader=int(np.flatnonzero(order==0)[0])
        a=solve(self.c,priority=3);b=solve(permute(self.c,order),priority=3,leader=leader)
        np.testing.assert_allclose(a['met'][order],b['met'],atol=1e-7,rtol=0)
    def test_differentiation_preserves_row_mean(self):
        a=make_community(31000,0);b=make_community(31000,.55)
        np.testing.assert_allclose(a.skills.mean(1),b.skills.mean(1),atol=1e-14)
        np.testing.assert_array_equal(a.requested,b.requested)
    def test_solver_tolerance(self):
        a=solve(self.c,tolerance=1e-9);b=solve(self.c,tolerance=1e-10)
        self.assertLess(abs(a['metrics']['mean_needs_met']-b['metrics']['mean_needs_met']),1e-8)
    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):solve(self.c,assessment=2)
        with self.assertRaises(ValueError):solve(self.c,priority=0)

if __name__=='__main__':unittest.main(verbosity=2)
