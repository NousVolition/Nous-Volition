import unittest, numpy as np
from dataclasses import replace
from audited_field import Field,Parameters,evolve,excess_gradient,refinement_is_distinct
from legacy_field import Field as LegacyField,Parameters as LegacyParameters,activation

class Conformance(unittest.TestCase):
 def setUp(self):self.p=Parameters(n=24,mu0=.02);self.f=Field(self.p);self.z,_=self.f.initial(.3)
 def test_full_rhs_matches_pinned_solver_all_laws(self):
  for law in ('sharp','tanh','smooth_off'):
   f=Field(replace(self.p,law=law));legacy=LegacyField(LegacyParameters(n=24,law=law))
   for new,old in zip(f.terms(self.z,.27),legacy.terms(self.z,.27)):np.testing.assert_array_equal(new,old)
 def test_missing_stress_coefficient_rejected(self):
  with self.assertRaises(ValueError):Field(Parameters())
 def test_stress_independent_coefficient(self):
  other=Field(replace(self.p,mu0=.06))
  np.testing.assert_allclose(other.stress(self.z),3*self.f.stress(self.z),atol=1e-14)
  np.testing.assert_array_equal(other.terms(self.z,.1)[0],self.f.terms(self.z,.1)[0])
 def test_nonfinite_parameters(self):
  for key in ('nu','gamma','kappa','baseline','mu0','epsilon'):
   with self.subTest(key=key),self.assertRaises(ValueError):Field(replace(self.p,**{key:float('nan')}))
 def test_bad_direction_and_grid(self):
  for p in (replace(self.p,n=24.),replace(self.p,direction=(1.,0.,0.)),replace(self.p,law='invented')):
   with self.assertRaises(ValueError):Field(p)
 def test_three_responses_retain_distinctions(self):
  q=np.array([-1.,0.,1.]);np.testing.assert_array_equal(activation(q,'sharp',1),[0,0,1])
  np.testing.assert_allclose(activation(q,'tanh',1),[-.11920292202211755,0,.8807970779778824])
  np.testing.assert_allclose(activation(q,'smooth_off',1),[0,0,np.exp(-1)])
 def test_regularization_cutoffs(self):
  G=.4;delta=.3;cut=np.sqrt(G*G+2*delta*G)
  self.assertAlmostEqual(float(excess_gradient(cut,G,'regularized',delta)),0)
  self.assertAlmostEqual(float(excess_gradient(G,G,'calibrated',delta)),0)
  self.assertLess(excess_gradient(G,G,'regularized',delta),0)
 def interval(self,**kwargs):return dict(person='fixture',start=3.,end=3.1,utility=.7,role='Smoke',event_ref='synthetic:1',**kwargs)
 def evolve(self,**kwargs):
  args=dict(person='fixture',intervals=[self.interval()],p=self.p,z=self.z,A=.2,start=3.,initial_state_basis='declared synthetic prehistory',max_dt=.001)
  args.update(kwargs);return evolve(**args)
 def test_nonzero_history_mass_identity(self):
  z,A,rows=self.evolve();self.assertAlmostEqual(A,.27,places=12);self.assertAlmostEqual(rows[-1]['mass'],.3235,places=12)
 def test_split_evolution_preserves_history(self):
  # Binary-exact intervals make the discrete steps identical; otherwise ceil
  # can create 101 steps versus 50+51 and this is a different integration grid.
  i=dict(self.interval(),end=3.125);a=dict(i,end=3.0625);b=dict(i,start=3.0625)
  whole=self.evolve(intervals=[i],max_dt=1/1024);first=self.evolve(intervals=[a],max_dt=1/1024);second=self.evolve(intervals=[b],z=first[0],A=first[1],start=3.0625,max_dt=1/1024)
  self.assertEqual(whole[2][0]['steps'],first[2][0]['steps']+second[2][0]['steps'])
  np.testing.assert_allclose(whole[0],second[0],atol=1e-11);self.assertAlmostEqual(whole[1],second[1])
 def test_missing_and_nonfinite_time(self):
  for overrides in ({'A':None},{'start':float('nan')},{'max_dt':0.},{'max_dt':-1.},{'initial_state_basis':''}):
   with self.assertRaises((ValueError,TypeError)):self.evolve(**overrides)
 def test_gap_overlap_crossperson_rejected(self):
  for changes in ({'start':3.01},{'start':2.99},{'person':'another'},{'end':float('inf')},{'utility':float('nan')}):
   with self.assertRaises(ValueError):self.evolve(intervals=[dict(self.interval(),**changes)])
 def test_imaginary_physical_state_rejected(self):
  z=self.z.copy();z[2,0,0]+=1j
  with self.assertRaises(ValueError):self.evolve(z=z)
 def test_role_labels_do_not_invent_a_force(self):
  a=self.evolve();b=self.evolve(intervals=[dict(self.interval(),role='Clay')]);np.testing.assert_array_equal(a[0],b[0])
 def test_no_implicit_run_history(self):
  with self.assertRaises(ValueError):self.f.run([1.])
 def test_capped_steps_not_refinement(self):
  a=self.evolve(max_dt=.1)[2];b=self.evolve(max_dt=.05)[2]
  self.assertFalse(refinement_is_distinct(a,b));c=self.evolve(max_dt=a[0]['dt']/2)[2];self.assertTrue(refinement_is_distinct(a,c))
 def test_pressure_and_energy_identity(self):
  dz,ph,_,_,force=self.f.terms(self.z,.2);d=self.f.diagnostics(self.z,.2)
  self.assertLess(abs(d['energy_identity_residual']),1e-12);self.assertLess(d['divergence_rms'],1e-12)
 def test_uniform_advection_diffusion_manufactured_solution(self):
  p=replace(self.p,sigma=0);f=Field(p);x=2*np.pi*f.x
  physical=np.array([np.full_like(x,.4),np.zeros_like(x),np.sin(x)])
  z=f.fft(physical)*f.mask
  out,_,_=evolve('fixture',[dict(person='fixture',start=0.,end=.1,utility=0.,role='unattributed',event_ref='analytic')],p,z=z,A=0.,start=0.,initial_state_basis='analytic zero source',max_dt=.0005)
  exact=np.exp(-p.diffusivity*(2*np.pi)**2*.1)*np.sin(x-2*np.pi*.4*.1)
  np.testing.assert_allclose(f.real(out[2]),exact,atol=1e-11)

if __name__=='__main__':unittest.main()
