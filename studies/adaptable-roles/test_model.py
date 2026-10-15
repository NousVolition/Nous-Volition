import unittest
from dataclasses import replace
import numpy as np
from model import Community,make_community,balanced_work,run,audit,POLICIES

class ModelTests(unittest.TestCase):
    def test_equal_skills_closed_form(self):
        np.testing.assert_allclose(balanced_work(1.4,np.ones(7),np.ones(7)),.2)
    def test_unequal_skills_equal_normalized_work(self):
        s=np.arange(1,8);b=np.linspace(.3,.6,7)
        np.testing.assert_allclose(balanced_work(.4*(s@b),s,b),.4*b)
    def test_saturation(self):
        np.testing.assert_array_equal(balanced_work(100,np.ones(7),np.ones(7)),np.ones(7))
    def test_preused_analytic(self):
        np.testing.assert_allclose(balanced_work(.6,np.ones(2),np.ones(2),np.array([.4,0])),[.1,.5])
    def test_handoff_overhead(self):
        t=balanced_work(.8,np.ones(2),np.ones(2),overhead=.25)
        self.assertAlmostEqual(t.sum(),1.)
    def test_zero_capacity(self):
        np.testing.assert_array_equal(balanced_work(1,np.ones(3),np.zeros(3)),0)
    def test_zero_demand(self):
        c=make_community(3);c.demand[:]=0
        self.assertEqual(run(c)['work'].sum(),0)
    def test_nobody_does_extra_work(self):
        c=make_community(3);h=run(c,policy='none')
        np.testing.assert_array_equal(h['done'],0)
        np.testing.assert_array_equal(h['unmet'],c.demand)
        np.testing.assert_array_equal(h['planned_done'],c.planned)
    def test_accounting_all_policies(self):
        for p in POLICIES:
            self.assertLess(max(audit(run(make_community(5,2.4),policy=p)).values()),1e-9,p)
    def test_refusal_means_zero_work_after_switch(self):
        for p in ('target_stops','target_stops_handoff'):
            self.assertEqual(run(make_community(7),target=4,policy=p)['work'][30:,4].sum(),0)
    def test_all_stop(self):
        h=run(make_community(4),policy='all_stop')
        self.assertEqual(h['done'][30:].sum(),0)
    def test_matched_history(self):
        c=make_community(4);base=run(c)
        for p in POLICIES[2:-1]:
            other=run(c,policy=p)
            for k in ('done','work','belief','skill'):np.testing.assert_array_equal(base[k][:30],other[k][:30])
    def test_no_learning(self):
        c=make_community(9);h=run(c,gain=0)
        np.testing.assert_array_equal(h['final_skill'],c.skill)
    def test_no_memory(self):
        h=run(make_community(9),memory=0)
        np.testing.assert_allclose(h['belief'],1/7)
    def test_labels_do_nothing(self):
        c=make_community(8);other=replace(c,labels=tuple(reversed(c.labels)))
        a,b=run(c),run(other)
        for k in a:np.testing.assert_array_equal(a[k],b[k])
    def test_person_permutation(self):
        c=make_community(8,2.4);order=np.array([6,2,4,0,5,1,3]);target=2
        c2=Community(c.skill[order],c.willing[order],c.planned[:,order],c.demand)
        a=run(c,target,policy='target_stops_handoff')
        b=run(c2,int(np.where(order==target)[0][0]),policy='target_stops_handoff')
        for k in ('done','work','belief','skill'):np.testing.assert_allclose(a[k][:,order],b[k],atol=1e-12)
    def test_uniform_no_bias_stays_uniform(self):
        c=Community(np.ones(7),np.full(7,.6),np.full((60,7),.6),np.ones(60))
        h=run(c,bias=0)
        np.testing.assert_allclose(h['belief'],1/7)
    def test_tighter_arithmetic_tolerance(self):
        c=make_community(10,2.4)
        a=run(c,policy='target_stops_handoff');b=run(c,policy='target_stops_handoff',tolerance=1e-13)
        np.testing.assert_allclose(a['done'],b['done'],atol=1e-10)
    def test_invalid_input(self):
        with self.assertRaises(ValueError):run(make_community(1),memory=2)
        with self.assertRaises(ValueError):balanced_work(1,np.array([-1.]),np.ones(1))

if __name__=='__main__':unittest.main(verbosity=2)
