import unittest
from dataclasses import replace
import numpy as np
from model import Config, run, initialize, group_sizes, opportunity_adjusted, network_metrics, response_matrix


class ScientificChecks(unittest.TestCase):
    def test_repeatable_and_label_invariant(self):
        c=Config(n=30,rounds=30,memory=1,stress=1,transitions=1,behavior=1,identity=.7)
        a=run(c)
        for d in (c,replace(c,labels='neutral'),replace(c,label_shift=3)):
            b=run(d)
            self.assertEqual(a['digest'],b['digest'])
            np.testing.assert_equal(a['phases'],b['phases'])

    def test_semantic_channel_required(self):
        c=Config(n=30,rounds=30,semantic=-2)
        self.assertNotEqual(run(c)['digest'],run(replace(c,semantic=0))['digest'])
        self.assertEqual(run(replace(c,labels='neutral'))['digest'],run(replace(c,semantic=0))['digest'])

    def test_available_partners_adjustment(self):
        # Two same and eight other partners; exactly proportional successes.
        same=np.array([1,1,0,0,0,0,0,0,0,0],bool)
        w,b,gap=opportunity_adjusted(same,np.ones(10),np.full(10,.2))
        self.assertAlmostEqual(w,1);self.assertAlmostEqual(b,1);self.assertAlmostEqual(gap,0)

    def test_balance_and_counterbalance(self):
        for n in (30,60,120):
            for b in ('equal','unequal'):
                sizes=np.array([group_sizes(n,b,r) for r in range(6)])
                self.assertTrue(np.all(sizes>0));self.assertTrue(np.all(sizes.sum(1)==n))
                np.testing.assert_allclose(sizes.mean(0),n/6)

    def test_equal_edge_counts_and_no_self(self):
        for name in ('ring','random','hub'):
            a,g,tr,p=initialize(Config(topology=name))
            self.assertEqual(a.sum(),360);self.assertFalse(a.diagonal().any())
            np.testing.assert_equal(a,a.T)

    def test_budget_and_trace_invariants(self):
        r=run(Config(n=30,rounds=60,stress=1,memory=1,transitions=1),True)
        self.assertTrue(all(0<=x['pool_used']<=1+1e-12 for x in r['trace']))
        self.assertTrue(all(0<=x['rigid']<=1 for x in r['trace']))
        ev=r['events'];self.assertFalse(np.any(ev[:,:,0]==np.arange(30)[None,:]))
        self.assertTrue(np.isin(ev[:,:,2],np.arange(6)).all())
        self.assertAlmostEqual(sum(r['final_influence']),1)

    def test_frozen_affiliation(self):
        r=run(Config(n=30,rounds=30,transitions=0),True)
        np.testing.assert_equal(r['final_groups'],r['initial_groups'])

    def test_no_stress_ablation_exact_baseline(self):
        a=run(Config(n=30,rounds=30,memory=1),True)
        b=run(Config(n=30,rounds=30,memory=1,stress=1),True)
        np.testing.assert_equal(a['events'][:10],b['events'][:10])

    def test_homogeneous_regular_network_response(self):
        a,g,_,_=initialize(Config(topology='ring'))
        _,v,_=network_metrics(a,g)
        np.testing.assert_allclose(v,np.ones(60)/60,atol=1e-14)

    def test_permutation_equivariance_response(self):
        a,g,_,_=initialize(Config(topology='hub'))
        p=np.random.default_rng(123).permutation(60)
        np.testing.assert_allclose(response_matrix(a[p][:,p]),response_matrix(a)[p][:,p])

    def test_known_segregated_network(self):
        groups=np.repeat(np.arange(6),2)
        w=(groups[:,None]==groups[None,:]).astype(float);np.fill_diagonal(w,0)
        m,_,_=network_metrics(w,groups)
        self.assertEqual(m['components'],6);self.assertAlmostEqual(m['assortativity'],1)
        self.assertAlmostEqual(m['modularity'],5/6)

    def test_stress_only_changes_requested_component(self):
        c=Config(n=30,rounds=30,stress=1,stress_kind='scarcity',scarcity=1)
        self.assertEqual(run(c)['digest'],run(replace(c,stress=0))['digest'])


if __name__=='__main__':
    unittest.main(verbosity=2)
