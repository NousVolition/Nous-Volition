import unittest
import numpy as np
from field import Field,Parameters,activation
from data_test import evaluate,design

class FieldTests(unittest.TestCase):
    def test_activation_signs(self):
        q=np.array([-1.,0.,1.]);self.assertAlmostEqual(activation(q,'tanh',1)[0],-.11920292202211755)
        for law in ['sharp','smooth_off']:self.assertEqual(activation(q,law,1)[0],0)
    def test_invalid_parameters(self):
        for kw in [dict(n=11),dict(sigma=-1),dict(nu=0),dict(direction=(1,1))]:
            with self.assertRaises(ValueError):Field(Parameters(**kw))
    def test_refinement_comparison_indexes_exact_modes(self):
        from run_spatial import l2_low_difference
        rng=np.random.default_rng(7);a=rng.normal(size=(3,24,24))+1j*rng.normal(size=(3,24,24))
        self.assertEqual(l2_low_difference(a,a),0.)
        f=Field(Parameters(n=24));g=Field(Parameters(n=48))
        a=f.fft(np.array([np.cos(14*np.pi*f.x),np.sin(10*np.pi*f.y),np.cos(8*np.pi*f.x)]))
        b=g.fft(np.array([np.cos(14*np.pi*g.x),np.sin(10*np.pi*g.y),np.cos(8*np.pi*g.x)]))
        self.assertLess(l2_low_difference(a,b),1e-14)
        a=np.zeros((3,24,24),complex);b=np.zeros((3,48,48),complex);b[0,15,0]=48**2
        self.assertAlmostEqual(l2_low_difference(a,b),1.)
    def test_normalized_kernel(self):
        f=Field();self.assertAlmostEqual(f.K.mean(),1.)
    def test_projection_preserves_mean(self):
        f=Field();rng=np.random.default_rng(4);v=f.fft(rng.normal(size=(2,24,24)))
        out=f.project(v);np.testing.assert_allclose(out[:,0,0],v[:,0,0]);self.assertLess(np.max(abs(f.kx*out[0]+f.ky*out[1])),1e-11)
    def test_pressure_reconstructs_projected_force(self):
        f=Field();z,A=f.initial();dz,p,u,g,force=f.terms(z,A)
        b=f.fft(-np.einsum('jxy,ijxy->ixy',u,g)+force)*f.mask
        predicted=b-1j*np.array([f.kx,f.ky])*p-f.p.nu*f.k2*z[:2]
        np.testing.assert_allclose(predicted,dz[:2],atol=1e-12)
    def test_exact_mass_and_zero_divergence(self):
        f=Field(Parameters(kappa=.3,baseline=.25));rows,z,_=f.run([1.,0.,1.],initial_total=.2,interval=.1)
        self.assertLess(max(abs(r['mass_error']) for r in rows),1e-12)
        self.assertLess(max(r['divergence_rms'] for r in rows),1e-12)
    def test_energy_identity(self):
        f=Field();z,A=f.initial();d=f.diagnostics(z,A)
        self.assertLess(abs(d['energy_identity_residual']),1e-13)
    def test_force_can_add_energy(self):
        f=Field(Parameters(law='tanh'));z,A=f.initial(texture=0.,speed=0.)
        z[0,0,0]=24**2*.1
        self.assertGreater(f.diagnostics(z,A)['work'],0)
    def test_memory_persists_after_input(self):
        f=Field(Parameters(kappa=1.,baseline=0.));rows,z,_=f.run([1.,0.],interval=.1,texture=0.)
        self.assertAlmostEqual(rows[-1]['A'],.1);self.assertAlmostEqual(rows[-1]['mass'],.015)
    def test_mass_independent_of_spatial_parameters(self):
        masses=[];textures=[]
        for sigma,D in [(0.,.01),(.2,.04)]:
            f=Field(Parameters(sigma=sigma,diffusivity=D));r,z,_=f.run([1.],interval=.1)
            masses.append(r[-1]['mass']);textures.append(f.real(z[2]))
        self.assertAlmostEqual(masses[0],masses[1]);self.assertGreater(np.max(abs(textures[0]-textures[1])),1e-4)
    def test_taylor_green(self):
        f=Field(Parameters(sigma=0.,kappa=0.));rows,z,_=f.run([0.],interval=.2,texture=0.)
        z0,_=f.initial(texture=0.);expected=f.real(z0[:2])*np.exp(-8*np.pi**2*.02*.2)
        self.assertLess(np.max(abs(f.real(z[:2])-expected)),1e-8)
    def test_passive_scalar(self):
        f=Field(Parameters(sigma=0.,kappa=0.));z,A=f.initial(texture=0.,speed=0.)
        z[0,0,0]=24**2*.2;z[2]=f.fft(np.sin(2*np.pi*f.x))
        for _ in range(100):z,A=f.step(z,A,0.,.001)
        exact=np.exp(-.01*4*np.pi**2*.1)*np.sin(2*np.pi*(f.x-.2*.1))
        self.assertLess(np.max(abs(f.real(z[2])-exact)),1e-10)

class DataTests(unittest.TestCase):
    def fixture(self):
        return [dict(group='a',sequence='a1',split='train',y=[0,0,1,1]),dict(group='b',sequence='b1',split='train',y=[1,1,0]),dict(group='c',sequence='c1',split='evaluation',y=[0,1,1])]
    def test_memory_is_accumulated_twice(self):
        s=[dict(group='a',sequence='a1',split='train',y=[1,1,1])];r=design(s,0.)
        self.assertEqual([x['B'] for x in r],[.5,2.])
    def test_next_target_not_used_in_own_predictor(self):
        d=self.fixture();r=design(d,.2);d[-1]['y'][1]=0;r2=design(d,.2)
        self.assertEqual(r[-2]['B'],r2[-2]['B']);self.assertNotEqual(r[-1]['B'],r2[-1]['B'])
    def test_training_parameters_ignore_evaluation_outcomes(self):
        d=self.fixture();a=evaluate(d)[2]['parameters'];d[-1]['y']=[1,0,0];b=evaluate(d)[2]['parameters']
        self.assertEqual(a,b)
    def test_kappa_gamma_product_not_separately_identified(self):
        # Integral solution unchanged when gamma is scaled and kappa inversely scaled.
        a=[]
        for gamma,kappa in [(1.,.4),(2.,.2)]:
            f=Field(Parameters(gamma=gamma,kappa=kappa));r,_,_=f.run([1.,0.],interval=.1)
            a.append(r[-1]['mass'])
        self.assertAlmostEqual(*a)
if __name__=='__main__':unittest.main()
