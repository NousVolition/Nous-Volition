from pathlib import Path
import unittest,hashlib,json
import numpy as np
from corpus_field import Field,Parameters,activation
from person_field import InputInterval,integrate,observation_support
from audit_records import split

ROOT=Path(__file__).resolve().parent
class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.p=Parameters(n=12,kappa=.3);self.f=Field(self.p);self.z,_=self.f.initial()
        self.e=[InputInterval('p',0,.2,1,'Smoke','e1'),InputInterval('p',.2,.4,-1,'Clay','e2')]
    def go(self,events=None,**kw):
        args=dict(person='p',intervals=self.e if events is None else events,p=self.p,z=self.z,A=0,start=0,initial_state_basis='test state')
        args.update(kw);return integrate(**args)
    def test_original_solver_hash(self):
        self.assertEqual(hashlib.sha256((ROOT/'corpus_field.py').read_bytes()).hexdigest(),'00b50a93ae413d46109327ccf0c08e8e07d00028313eaa0da87d765e58705f35')
    def test_original_runner_parity(self):
        z,A,rows=self.go()
        rr,zz,_=self.f.run([1,-1],interval=.2,dt=.002)
        np.testing.assert_allclose(z,zz,rtol=0,atol=1e-13)
        self.assertAlmostEqual(A,rr[-1]['A'],places=14)
    def test_cross_person_rejected(self):
        with self.assertRaisesRegex(ValueError,'Cross-person'):self.go([InputInterval('q',0,.2,1,'Clay','x')])
    def test_unknown_history_is_not_zero(self):
        with self.assertRaisesRegex(ValueError,'unknown is not zero'):self.go(A=None)
    def test_gap_is_not_filled(self):
        with self.assertRaisesRegex(ValueError,'gap'):self.go([InputInterval('p',.1,.2,1,'Clay','x')])
    def test_missing_utility_is_not_affect(self):
        with self.assertRaisesRegex(ValueError,'utility'):self.go([InputInterval('p',0,.2,None,'Clay','x')])
    def test_nonfinite_utility_rejected(self):
        with self.assertRaisesRegex(ValueError,'utility'):self.go([InputInterval('p',0,.2,float('nan'),'Clay','x')])
    def test_nonzero_prior_mass_identity(self):
        _,_,r=self.go(A=.1)
        self.assertLess(max(abs(x['mass_error']) for x in r),1e-12)
        self.assertAlmostEqual(r[-1]['mass'],.024,places=12)
    def test_role_labels_retained_but_do_not_invent_force(self):
        a,_,r=self.go();b,_,s=self.go([InputInterval('p',0,.2,1,'Clay','e1'),InputInterval('p',.2,.4,-1,'Smoke','e2')])
        self.assertEqual(r[0]['role'],'Smoke');self.assertEqual(s[0]['role'],'Clay');np.testing.assert_array_equal(a,b)
    def test_all_three_response_scalings(self):
        q=np.array([-.2,-.01,0,.01,.3]);c=2.
        for law in ['sharp','tanh','smooth_off']:np.testing.assert_allclose(activation(c*q,law,c*.1),c*activation(q,law,.1),atol=1e-15,rtol=1e-15)
    def test_tanh_tail_preserved(self):
        self.assertLess(activation(np.array([-.1]),'tanh',.1)[0],0)
    def test_no_form_proxy_from_survey_names(self):
        support=observation_support(json.loads((ROOT/'source_codebook.json').read_text()))
        self.assertFalse(support['full_two_in_one_measured']);self.assertIn('perceived_balance',support['missing']);self.assertTrue(support['partial_movement_report'])
    def test_reserved_split_disjoint(self):
        r=json.loads((ROOT/'results/data_audit.json').read_text());a,b=split(r['reserved_participants']+r['development_participants'])
        self.assertEqual(a,set(r['reserved_participants']));self.assertEqual(len(a),8);self.assertFalse(a&set(b))
    def test_no_state_mutation(self):
        before=self.z.copy();self.go();np.testing.assert_array_equal(before,self.z)
if __name__=='__main__':unittest.main()
