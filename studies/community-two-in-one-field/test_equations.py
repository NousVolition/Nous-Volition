import hashlib
from pathlib import Path
import unittest
import numpy as np
from corpus_field import Field,Parameters,activation
from run_equations import difference

class ExactCorpusTests(unittest.TestCase):
    def test_audited_solver_is_unchanged(self):
        self.assertEqual(hashlib.sha256(Path(__file__).with_name('corpus_field.py').read_bytes()).hexdigest(),'00b50a93ae413d46109327ccf0c08e8e07d00028313eaa0da87d765e58705f35')
    def test_signed_tanh_tail_and_exact_off_alternatives(self):
        q=np.array([-.1,0.,.1])
        self.assertLess(activation(q,'tanh',.1)[0],0)
        for law in ('sharp','smooth_off'):
            self.assertEqual(activation(q,law,.1)[0],0)
            self.assertEqual(activation(q,law,.1)[1],0)
    def test_fixed_direction_force_is_not_drag(self):
        f=Field();z,a=f.initial();force=f.terms(z,a)[-1]
        self.assertGreater(np.linalg.norm(force[0]),0)
        self.assertEqual(np.linalg.norm(force[1]),0)
    def test_pressure_reconstruction_and_divergence(self):
        f=Field();z,a=f.initial();dz,p,u,gu,force=f.terms(z,a)
        b=f.fft(-np.einsum('jxy,ijxy->ixy',u,gu)+force)*f.mask
        expected=b-1j*np.array([f.kx,f.ky])*p-f.p.nu*f.k2*z[:2]
        np.testing.assert_allclose(dz[:2],expected,atol=1e-12)
        self.assertLess(np.max(abs(f.kx*dz[0]+f.ky*dz[1])),1e-11)
    def test_memory_continues_to_source_at_baseline(self):
        f=Field(Parameters(kappa=.3));r,z,_=f.run([1.,0.],interval=.1)
        self.assertAlmostEqual(r[-1]['A'],.1)
        self.assertAlmostEqual(r[0]['mass'],.0015)
        self.assertAlmostEqual(r[-1]['mass'],.0045)
    def test_negative_input_retains_signed_field(self):
        f=Field(Parameters(kappa=.3));r,z,_=f.run([-1.],interval=.1,texture=0.,speed=0.)
        self.assertLess(r[-1]['mass'],0)
        self.assertLess(r[-1]['S_min'],0)
    def test_full_state_scale_symmetry(self):
        a=Field(Parameters(gamma=1,kappa=.3));b=Field(Parameters(gamma=4,kappa=.075))
        ra,za,_=a.run([1.,-.5],interval=.1);rb,zb,_=b.run([1.,-.5],interval=.1)
        np.testing.assert_array_equal(za,zb)
        self.assertAlmostEqual(4*ra[-1]['A'],rb[-1]['A'])
    def test_all_terms_active_in_coupled_trial(self):
        f=Field();z,a=f.initial();z,a=f.step(z,a,1.,.01)
        dz,p,u,gu,force=f.terms(z,a)
        self.assertGreater(np.linalg.norm(np.einsum('jxy,ijxy->ixy',u,gu)),0)
        self.assertGreater(np.linalg.norm(np.sum(u*f.gradient(z[2]),axis=0)),0)
        for term in (p,force,f.k2*z[:2],f.k2*z[2],f.p.kappa*a*f.kh):self.assertGreater(np.linalg.norm(term),0)
    def test_stress_is_symmetric(self):
        f=Field();z,a=f.initial();gu=f.terms(z,a)[3]
        T=f.p.rho*f.p.nu*(gu+gu.swapaxes(0,1))
        np.testing.assert_allclose(T,T.swapaxes(0,1),atol=0)
    def test_energy_accounting(self):
        f=Field();r,_,_=f.run([1.,-.5],interval=.1)
        self.assertLess(max(abs(x['energy_identity_residual']) for x in r),1e-12)
    def test_grid_difference_includes_fine_only_modes(self):
        a=np.zeros((3,24,24),complex);b=np.zeros((3,48,48),complex);b[0,15,0]=48**2
        self.assertEqual(difference(a,b),1)
    def test_grid_difference_normalizes_identical_modes(self):
        f=Field(Parameters(n=24));g=Field(Parameters(n=48))
        a=f.fft(np.array([np.cos(2*np.pi*f.x)]*3));b=g.fft(np.array([np.cos(2*np.pi*g.x)]*3))
        self.assertLess(difference(a,b),1e-14)

if __name__=='__main__':unittest.main()
