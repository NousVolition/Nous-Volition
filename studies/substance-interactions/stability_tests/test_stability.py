import unittest
import numpy as np
from models import *


class StabilityTests(unittest.TestCase):
    def test_cubic_against_exact_solution(self):
        for a in [-1,0,1]:
            _,_,r=cubic_case(a)
            self.assertLess(r['max_state_error'],2e-9)

    def test_cubic_stability_differs_despite_same_linearization(self):
        finals=[cubic_case(a)[2]['final_radius'] for a in [-1,0,1]]
        self.assertLess(finals[0],.2)
        self.assertAlmostEqual(finals[1],.2,places=10)
        self.assertGreater(finals[2],.2)
        for a in [-1,0,1]:
            h=1e-6;J=np.column_stack([(cubic_rhs(0,h*np.eye(2)[i],a)-cubic_rhs(0,-h*np.eye(2)[i],a))/(2*h) for i in range(2)])
            np.testing.assert_allclose(J,[[0,-1],[1,0]],atol=2e-12)

    def test_cubic_blowup_domain(self):
        with self.assertRaises(ValueError):cubic_exact(12.6,.2,1)
        self.assertAlmostEqual(float(cubic_exact(10,.2,1)),np.sqrt(.2),places=12)

    def test_cubic_tolerance_refinement(self):
        coarse=cubic_case(1,rtol=1e-7,max_step=1)[2]['max_state_error']
        fine=cubic_case(1,rtol=1e-11,max_step=1)[2]['max_state_error']
        self.assertLess(fine,coarse/50)
        self.assertLess(fine,1e-9)

    def test_return_map_event(self):
        for r0 in [.2,.8,1,1.5,3]:
            t,r=numerical_return(r0)
            self.assertAlmostEqual(t,2*np.pi,places=9)
            self.assertAlmostEqual(r,float(cycle_radius(2*np.pi,r0)),places=10)

    def test_backward_flow_has_different_limit(self):
        self.assertLess(float(cycle_radius(-2*np.pi,.8)),.003)
        with self.assertRaises(ValueError):cycle_radius(-2*np.pi,1.5)
        self.assertEqual(float(cycle_radius(8,0)),0)
        with self.assertRaises(ValueError):numerical_return(0)

    def test_cycle_floquet_multipliers(self):
        eig=np.sort(np.linalg.eigvals(cycle_monodromy()))
        np.testing.assert_allclose(eig,[np.exp(-4*np.pi),1],atol=1e-10,rtol=1e-7)

    def test_competition_fixed_points_and_eigenvalues(self):
        expected=[[2,3],[-2,-1],[-3,-1],[-1-np.sqrt(2),-1+np.sqrt(2)]]
        for r,want in zip(competition_fixed_points(),expected):
            np.testing.assert_allclose(competition_rhs(0,r['point']),0,atol=1e-15)
            np.testing.assert_allclose(r['eigenvalues'],want,atol=1e-14)

    def test_competition_jacobian_finite_difference(self):
        for r in competition_fixed_points():
            p=np.array(r['point']);h=1e-6
            J=np.column_stack([(competition_rhs(0,p+h*np.eye(2)[i])-competition_rhs(0,p-h*np.eye(2)[i]))/(2*h) for i in range(2)])
            np.testing.assert_allclose(J,competition_jacobian(p),atol=2e-9)

    def test_linearization_quadratic_remainder_and_short_time_error(self):
        a,b=linearization_error(.01),linearization_error(.005)
        self.assertAlmostEqual(a['vector_field_remainder']/b['vector_field_remainder'],4,places=8)
        self.assertGreater(a['max_trajectory_error']/b['max_trajectory_error'],3.8)
        self.assertLess(a['max_trajectory_error']/b['max_trajectory_error'],4.2)

    def test_competition_positive_quadrant_and_two_basins(self):
        cases=competition_examples()
        for t,z,r in cases:self.assertGreaterEqual(r['minimum'],-1e-13)
        np.testing.assert_allclose(cases[-2][1][:,-1],[3,0],atol=2e-6)
        np.testing.assert_allclose(cases[-1][1][:,-1],[0,2],atol=2e-6)

    def test_conservative_well_energy(self):
        for initial in [(1,.4),(0,.7)]:
            t,z,e,r=well_case(initial)
            self.assertLess(r['max_energy_balance_error'],1e-9)
        r=well_case((1,.4))[3]
        self.assertGreater(r['x_min'],0)

    def test_homoclinic_exact_orbit(self):
        t,z=integrate(lambda t,z:well_rhs(t,z,0),[np.sqrt(2),0,0],8,801)
        x=np.sqrt(2)/np.cosh(t);v=-x*np.tanh(t)
        self.assertLess(float(np.max(np.linalg.norm(z[:2]-[x,v],axis=0))),1e-7)

    def test_damping_energy_loss_accounted(self):
        t,z,e,r=well_case(gamma=.2)
        self.assertTrue(np.all(np.diff(e)<=1e-11))
        self.assertLess(r['max_energy_balance_error'],1e-9)
        self.assertGreater(r['dissipated_energy'],.05)

    def test_velocity_flip_time_reversal(self):
        self.assertLess(reversal_case(0)['max_retrace_error'],1e-8)
        self.assertGreater(reversal_case(.2)['max_retrace_error'],.05)

    def test_exchange_mass_and_exact_relaxation(self):
        for name,H in [('CO',9.7e-6),('acetone',.27),('H2O2',860)]:
            t,z,r=exchange_case(name,H)
            self.assertLess(r['max_mass_error'],1e-12)
            self.assertLess(r['max_liquid_fraction_error'],1e-11)
            self.assertGreaterEqual(float(z.min()),-1e-13)

    def test_exchange_zero_mode_is_conservation(self):
        for name,H in [('CO',9.7e-6),('acetone',.27),('H2O2',860)]:
            t,z,r=exchange_case(name,H)
            J=np.array(r['jacobian_per_s'])
            np.testing.assert_allclose(np.ones(2)@J,[0,0],atol=1e-14)
            self.assertAlmostEqual(r['eigenvalues_per_s'][1],0,places=12)
            self.assertAlmostEqual(r['eigenvalues_per_s'][0],-r['relaxation_rate_per_s'],places=10)

    def test_coulomb_drag_analytic_separation(self):
        for sign in [-1,0,1]:
            t,s,U,Q,r=charged_drag_case(sign)
            self.assertLess(r['max_separation_error_m'],1e-12)
            if sign==0:np.testing.assert_allclose(s,20e-6,rtol=1e-14)

    def test_coulomb_drag_energy_and_far_field_stop(self):
        for sign in [-1,1]:
            t,s,U,Q,r=charged_drag_case(sign)
            self.assertLess(r['relative_energy_residual'],1e-8)
            self.assertGreaterEqual(float(Q[-1]),0)
            self.assertTrue(np.all(np.diff(U)<=1e-28))
            self.assertEqual(r['far_field_stop'],sign<0)
            if sign<0:self.assertAlmostEqual(s[-1]/1e-6,6,places=6)


if __name__=='__main__':unittest.main()
