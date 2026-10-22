import unittest,math
from analysis_core import available,jaccard,expiry,episodes,paired_duration,did_bounds,DAY

class AnalysisTests(unittest.TestCase):
    def test_replacement_template_excluded(self):self.assertFalse(available('[deleted] 123 https://example.test'))
    def test_forceful_language_not_excluded(self):self.assertTrue(available('I refuse. This decision is unjust.'))
    def test_overlap_is_not_semantics(self):self.assertEqual(jaccard('I agree','I do not agree'),.5)
    def test_explicit_expiry(self):self.assertEqual(expiry({'expiry':'1970-01-02T00:00:00Z'},0),DAY)
    def test_known_duration(self):self.assertEqual(expiry({'duration':'2 weeks'},1),1+14*DAY)
    def test_unknown_duration_not_zero(self):self.assertIsNone(expiry({'duration':'a long time'},0))
    def test_indefinite(self):self.assertTrue(math.isinf(expiry({'duration':'indefinite'},0)))
    def test_never_means_infinite(self):self.assertTrue(math.isinf(expiry({'duration':'never'},0)))
    def test_reblock_is_not_new_penalty(self):
        e,s=episodes([(0,1,'block',10,'a',0),(5,2,'reblock',20,'b',0),(21,3,'block',31,'a',0)])
        self.assertEqual(len(e),2);self.assertEqual(e[0]['initial_duration'],10);self.assertEqual(e[0]['end'],20);self.assertFalse(s)
    def test_unblock_closes_episode(self):
        e,s=episodes([(0,1,'block',math.inf,'a',0),(5,2,'unblock',None,'b',0),(6,3,'block',16,'a',0)])
        self.assertEqual(e[0]['end'],5);self.assertEqual(len(e),2);self.assertFalse(s)
    def test_orphan_is_flagged(self):self.assertIn('orphan_reblock',episodes([(5,1,'reblock',10,'a',0)])[1])
    def test_expiry_boundary(self):self.assertEqual(len(episodes([(0,1,'block',10,'a',0),(10,2,'block',20,'a',0)])[0]),2)
    def test_no_false_extension(self):self.assertEqual(episodes([(0,1,'block',10,'a',0),(5,2,'reblock',7,'b',0)])[0][0]['end'],7)
    def test_duration_summary(self):
        r=paired_duration([(3600,7200),(3600,3600),(7200,3600)],reps=50)
        self.assertEqual((r['longer'],r['equal'],r['shorter']),(1,1,1));self.assertEqual(r['median_ratio'],1)
    def test_swap_negates_log_ratio(self):
        a=paired_duration([(1,2),(1,4)],reps=50);b=paired_duration([(2,1),(4,1)],reps=50)
        self.assertEqual(a['median_log2_ratio'],-b['median_log2_ratio'])
    def test_unknown_outcomes_preserved(self):self.assertEqual(did_bounds([[None]*4]),[-2,2])
    def test_known_null(self):self.assertEqual(did_bounds([[0,1,0,1]]),[0,0])
    def test_bounds_signs(self):self.assertEqual(did_bounds([[1,None,0,0]]),[-1,0])
    def test_bootstrap_seed(self):self.assertEqual(paired_duration([(1,2),(3,2)],reps=50),paired_duration([(1,2),(3,2)],reps=50))
if __name__=='__main__':unittest.main()
