import unittest
from observations import *
from corpus_equations import momentum_rhs
import numpy as np

class ObservationsTests(unittest.TestCase):
    def test_card_order_irrelevant(self):self.assertEqual(card_set('7,A'),card_set('A,7'))
    def test_no_interpreting_prose_as_submission(self):self.assertIsNone(card_set('I think A and 7'))
    def test_missing_submission(self):self.assertIsNone(card_set(''));self.assertIsNone(card_set(float('nan')))
    def test_correct_counterexample_cards(self):self.assertTrue(correct(('7','A')))
    def test_confirmation_pair_incorrect(self):self.assertFalse(correct(('8','A')))
    def test_extra_card_not_correct(self):self.assertFalse(correct(('7','8','A')))
    def test_quotes_not_endorsement(self):self.assertEqual(phrases('> this is evidence\n"you are wrong"'),set())
    def test_quote_continuation_limitation(self):
        # Explicitly documents the remaining Markdown lazy-continuation limitation.
        self.assertIn(('continued','quoted','words'),phrases('> quotation begins\ncontinued quoted words'))
    def test_no_join_across_removed_quote(self):self.assertNotIn(('these','are','linked'),phrases('these are "discard this" linked'))
    def test_novel_cross_speaker(self):
        rs=[dict(speaker='a',text='the evidence is strong'),dict(speaker='b',text='the evidence is strong')]
        self.assertEqual(reuse_features(rs)['any'],1)
    def test_self_repetition_excluded(self):
        rs=[dict(speaker='a',text='the evidence is strong'),dict(speaker='a',text='the evidence is strong')]
        self.assertEqual(reuse_features(rs)['any'],0)
    def test_past_self_use_excluded(self):
        rs=[dict(speaker=s,text='the evidence is strong') for s in ['a','b','a']]
        self.assertEqual(reuse_features(rs)['reciprocal'],0)
    def test_reciprocal_different_phrases(self):
        rs=[dict(speaker='a',text='this specific evidence'),dict(speaker='b',text='this specific evidence and that strange argument'),dict(speaker='a',text='that strange argument')]
        self.assertEqual(reuse_features(rs)['reciprocal'],1)
    def test_outcome_not_used(self):
        rs=[dict(speaker=s,text='this specific evidence',removed=w) for s,w in [('a',0),('b',1)]]
        got=reuse_features(rs)
        for r in rs:r['removed']=1-r['removed']
        self.assertEqual(got,reuse_features(rs))
    def test_momentum_density_normalization(self):
        adv=np.array([1.,2.]);gp=np.array([3.,4.]);lap=np.array([5.,6.]);f=np.array([-2.,0.]);rho=3.;mu=2.
        np.testing.assert_allclose(rho*momentum_rhs(adv,gp,lap,rho,mu,f),-rho*adv-gp+mu*lap+rho*f)

if __name__=='__main__':unittest.main()
