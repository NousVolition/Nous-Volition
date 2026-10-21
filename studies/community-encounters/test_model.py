import math,unittest
from dataclasses import replace
import numpy as np
from model import *

class Tests(unittest.TestCase):
    def test_baseline_probability(self):
        self.assertAlmostEqual(float(probability('',0,0,Rule())),.2)
    def test_wording_blind_all_forms(self):
        for task in TASKS:
            p=[probability(x,.2,.7,Rule(history=1)) for x in variants(task,20).values()]
            self.assertEqual(len(set(map(float,p))),1)
    def test_marker_case_and_punctuation(self):
        self.assertEqual(lexical_marker('I WILL, NOT go. PLEASE.'),0)
    def test_marker_not_substring(self):
        self.assertEqual(lexical_marker('pleased refusal'),0)
    def test_authored_slot_preservation(self):
        for task in TASKS:
            for text in variants(task,20).values():
                self.assertIn(task,text);self.assertIn('20 minutes',text)
    def test_same_marker_same_response(self):
        v=variants(TASKS[0],20);r=Rule(wording=.8)
        self.assertEqual(probability(v['direct'],0,0,r),probability(v['forceful'],0,0,r))
    def test_reversed_rule_reverses_order(self):
        v=variants(TASKS[0],20)
        for beta in (-.8,.8):
            d=probability(v['direct'],0,0,Rule(wording=beta))-probability(v['courteous'],0,0,Rule(wording=beta))
            self.assertGreater(float(d)*beta,0)
    def test_probability_bounds(self):
        p=probability('refuse',500,np.array([-1e5,1e5]),Rule(history=10,wording=10))
        self.assertTrue(np.all((p>=0)&(p<=1)))
    def test_history_blind_identical_decisions(self):
        a=twin_history(7,Rule())
        np.testing.assert_array_equal(a[:,5],a[:,6])
        np.testing.assert_array_equal(a[:,3],a[:,4])
    def test_zero_input_identical(self):
        a=twin_history(7,Rule(history=1.2,input_gain=0))
        np.testing.assert_array_equal(a[:,3],a[:,4])
    def test_first_encounter_analytic(self):
        a=twin_history(11,Rule(history=1.2))
        self.assertAlmostEqual(math.log(a[0,4]/(1-a[0,4]))-math.log(a[0,3]/(1-a[0,3])),.3)
    def test_record_only_decay(self):
        a=twin_history(11,Rule(history=1.2),record_only=True)
        np.testing.assert_allclose(a[:,2]-a[:,1],.25*.8**np.arange(30),atol=1e-15)
    def test_reset_removes_later_difference(self):
        a=twin_history(11,Rule(history=1.2),reset_at=6)
        np.testing.assert_array_equal(a[5:,1],a[5:,2])
        np.testing.assert_array_equal(a[5:,5],a[5:,6])
    def test_history_order(self):
        r=Rule();self.assertAlmostEqual(float(update(update(0,1,r),0,r)),.2)
        self.assertAlmostEqual(float(update(update(0,0,r),1,r)),.25)
    def test_inert_label_names(self):
        # Names are metadata: API has no name input and the inputs stay identical.
        reference=twin_history(42,Rule(history=1.2))
        for name in LABELS: np.testing.assert_array_equal(reference,twin_history(42,Rule(history=1.2)))
    def test_seed_reproducibility(self):
        np.testing.assert_array_equal(twin_history(4,Rule(history=1)),twin_history(4,Rule(history=1)))
    def test_finite_state_bound(self):
        a=twin_history(31,Rule(history=1.2))
        self.assertLessEqual(float(a[:,1:3].max()),.25/(1-.8)+1e-14)
    def test_source_rounding_consistency(self):
        self.assertTrue(coefficient_audit(-.42,.37,.66)['table_consistent'])
        self.assertFalse(coefficient_audit(-.4,.2,.45)['table_consistent'])
    def test_source_ci_known_zero(self):
        a=coefficient_audit(0,.5,1)
        self.assertEqual(a['odds_ratio'],1);self.assertAlmostEqual(a['lower'],math.exp(-.98))

if __name__=='__main__':unittest.main(verbosity=2)
