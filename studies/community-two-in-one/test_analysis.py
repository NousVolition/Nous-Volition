import unittest
import analyze as a

def rows(person='A', vals=(1,0,1)):
    return [dict(person=person,probe=i+1,eligible=1,dialogic=v) for i,v in enumerate(vals)]

class AnalysisTests(unittest.TestCase):
    def test_future_does_not_change_prediction(self):
        x=rows();p=a.predict(x,.4,2);x[-1]['dialogic']=0
        self.assertEqual(p[-1]['history'],a.predict(x,.4,2)[-1]['history'])
    def test_person_isolation(self):
        x=rows();self.assertEqual(a.predict(x,.4,2),[r for r in a.predict(x+rows('B',(0,0,0)),.4,2) if r['person']=='A'])
    def test_missing_is_not_no(self):
        x=rows();x[1]['eligible']=0;x[1]['dialogic']=''
        p=a.predict(x,.4,2);self.assertEqual(len(p),1);self.assertEqual(p[0]['past_n'],1);self.assertEqual(p[0]['last'],1)
    def test_space_normalization(self):
        self.assertTrue(a.eligible(dict(exp_type='Inner voice',dial='Partially agree')))
        self.assertFalse(a.eligible(dict(exp_type='Inner seeing',dial='NA')))
    def test_known_history_value(self):
        self.assertAlmostEqual(a.predict(rows(),.4,2)[0]['history'],.6)
    def test_probability_bounds(self):
        for prior in [0,.4,1]:
            for r in a.predict(rows(),prior,1): self.assertTrue(0<=r['history']<=1)
    def test_first_is_not_scored(self):
        self.assertEqual(a.predict(rows(vals=(1,)),.4,2),[])
    def test_ordering(self):
        self.assertEqual(a.predict(rows(),.4,2),a.predict(list(reversed(rows())),.4,2))
    def test_person_equal_population_weight(self):
        self.assertEqual(a.population(rows('A',(1,))+rows('B',(0,0,0)),'dialogic'),.5)
    def test_memory_pair_orientation(self):
        x=[dict(person='A',probe=i,youth_bin=b,total_content=c) for i,(b,c) in enumerate([(0,9),(1,7),(8,5),(9,3)])]
        r,s=a.cram_analysis(x);self.assertEqual(s[0]['remote_greater_fraction'],1);self.assertEqual(s[0]['recent_minus_remote'],-4)
    def test_bootstrap_reproducible(self):
        self.assertEqual(a.interval([1,2,3]),a.interval([1,2,3]))
    def test_no_eligible_error(self):
        with self.assertRaises(ValueError):a.interval([])

if __name__=='__main__':unittest.main()
