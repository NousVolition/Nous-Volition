import unittest
import math
from scipy.stats import hypergeom
from analysis_core import label_index, pair_id, cluster_interval, randomized_counts, wilson, parse_bool

class AnalysisTests(unittest.TestCase):
    def test_duplicate_is_not_new_rater(self):
        rows=[dict(text='a',label='True')]*3
        good,bad,duplicates=label_index(rows,['text'],'label')
        self.assertEqual(good,{('a',):True});self.assertEqual(duplicates,2)
    def test_conflict_is_excluded_not_majority_voted(self):
        rows=[dict(text='a',label='True')]*3+[dict(text='a',label='False')]
        good,bad,_=label_index(rows,['text'],'label')
        self.assertEqual(good,{});self.assertEqual(bad,{('a',)})
    def test_no_fuzzy_join(self):
        good,_,_=label_index([dict(text='No.',label='True')],['text'],'label')
        self.assertNotIn(('no',),good)
    def test_column_names_do_not_set_outcome(self):
        good,_,_=label_index([dict(comment='an original',toxic='False')],['comment'],'toxic')
        self.assertFalse(good['an original',])
    def test_invalid_label_rejected(self):
        with self.assertRaises(ValueError):parse_bool('possibly')
    def test_pair_hash_keeps_direction_and_boundary(self):
        self.assertNotEqual(pair_id('ab','c'),pair_id('a','bc'))
        self.assertNotEqual(pair_id('a','b'),pair_id('b','a'))
    def test_zero_change_control(self):
        r=cluster_interval([1,2,7],[0,0,0],draws=100)
        self.assertEqual([r['estimate'],r['low'],r['high']],[0,0,0])
    def test_cluster_not_pair_resampling(self):
        r=cluster_interval([100,1],[-100,1],draws=100)
        self.assertEqual(r['clusters'],2);self.assertAlmostEqual(r['estimate'],-99/101)
        self.assertEqual(r['low'],-1);self.assertEqual(r['high'],1)
    def test_seed_reproducibility(self):
        self.assertEqual(cluster_interval([2,4],[0,-3]),cluster_interval([2,4],[0,-3]))
    def test_fisher_matches_hypergeometric_enumeration(self):
        r=randomized_counts(12,100,2,100)
        obs=hypergeom.pmf(12,200,14,100)
        expected=sum(hypergeom.pmf(k,200,14,100) for k in range(15) if hypergeom.pmf(k,200,14,100)<=obs+1e-14)
        self.assertAlmostEqual(r['fisher_two_sided_p'],expected,places=13)
    def test_history_endpoint_and_reversal(self):
        a=randomized_counts(12,100,2,100);b=randomized_counts(2,100,12,100)
        self.assertAlmostEqual(a['risk_difference'],.1);self.assertEqual(a['risk_ratio'],6)
        self.assertAlmostEqual(a['fisher_two_sided_p'],b['fisher_two_sided_p'])
        self.assertAlmostEqual(a['risk_difference_ci'][0],-b['risk_difference_ci'][1])
    def test_null_history(self):
        r=randomized_counts(12,100,12,100)
        self.assertEqual(r['risk_difference'],0);self.assertEqual(r['fisher_two_sided_p'],1)
    def test_binomial_boundaries(self):
        self.assertAlmostEqual(wilson(0,100)[0],0);self.assertAlmostEqual(wilson(100,100)[1],1)
        with self.assertRaises(ValueError):wilson(101,100)

if __name__=='__main__':unittest.main(verbosity=2)
