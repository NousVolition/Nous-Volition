import copy,json,unittest
from pathlib import Path
import numpy as np
from corpus_field import Field,Parameters
from observer import setup,readout
from validate_observations import validate
ROOT=Path(__file__).resolve().parent

class ObservationTests(unittest.TestCase):
    def setUp(self):self.data=json.loads((ROOT/'observations.json').read_text(encoding='utf-8'))
    def test_ledger_integrity(self):self.assertEqual(validate(self.data),dict(episodes=5,people=1,history_references=3,nodes=10))
    def test_cross_person_history_rejected(self):
        self.data['history'][0]['person_id']='a different person'
        with self.assertRaisesRegex(ValueError,'Cross-person'):validate(self.data)
    def test_unmeasured_balance_not_inferred_from_calm(self):
        self.data['episodes'][3]['forms']['Water']='observed'
        with self.assertRaisesRegex(ValueError,'Unmeasured'):validate(self.data)
    def test_dangling_reconsideration_rejected(self):
        self.data['episodes'][3]['edges'][0]['to']='absent'
        with self.assertRaisesRegex(ValueError,'Dangling'):validate(self.data)

class FullEquationTests(unittest.TestCase):
    def test_constant_context_shift_is_not_a_new_direction(self):
        f=Field();z,w=setup(f,.15);a=readout(f,z,.02,w)
        shifted=z.copy();shifted[2]+=f.fft(np.ones_like(f.x)*2)
        b=readout(f,shifted,.02,w)
        np.testing.assert_allclose(f.terms(shifted,.02)[0],f.terms(z,.02)[0],atol=2e-12)
        self.assertAlmostEqual(b['c_P']-a['c_P'],2,places=12)
        self.assertAlmostEqual(b['contrast'],a['contrast'],places=12)
        # Positive support is origin-dependent. It must remain a declared hypothesis.
        self.assertTrue(all(abs(v.mean()-1)<1e-12 for v in w.values()))
    def test_accumulator_and_total_field_match_integrals(self):
        f=Field();z,_=f.initial(total=.3);A=.2;T=.1;h=.001;U=.3
        for _ in range(100):z,A=f.step(z,A,U,h)
        self.assertAlmostEqual(A,.2+U*T,places=12)
        self.assertAlmostEqual(f.real(z[2]).mean(),.3+.2*T+.5*U*T*T,places=12)
    def test_pressure_restores_unprojected_momentum(self):
        f=Field();z,_=setup(f,.15);dz,ph,u,gu,force=f.terms(z,.02)
        adv=np.einsum('jxy,ijxy->ixy',u,gu)
        raw=f.fft(-adv+force)*f.mask-f.p.nu*f.k2*z[:2]
        gradp=1j*np.array([f.kx,f.ky])*ph
        np.testing.assert_allclose(dz[:2],raw-gradp,atol=1e-12)
        self.assertGreater(np.linalg.norm(ph),1e-6)
    def test_zero_source_erases_only_this_initial_A_difference(self):
        f=Field(Parameters(kappa=0));z,_=setup(f,.15)
        a,_=f.step(z,-.02,0,.001);b,_=f.step(z,.02,0,.001)
        np.testing.assert_array_equal(a,b)
        g=Field();za,_=g.step(z,-.02,0,.001);zb,_=g.step(z,.02,0,.001)
        self.assertGreater(np.linalg.norm(za-zb),.001)

if __name__=='__main__':unittest.main()
