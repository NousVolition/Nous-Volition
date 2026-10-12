import unittest
import numpy as np
from models import *


class MechanicalChecks(unittest.TestCase):
    def test_force_is_negative_potential_gradient(self):
        for lam in [.8,1.,2.]:
            for y in [-2.,-.4,.2,1.7]:
                h=1e-5
                derivative=(spring_potential(y+h,.3,lam)-spring_potential(y-h,.3,lam))/(2*h)
                self.assertAlmostEqual(-derivative,spring_force(y,.3,lam),places=8)

    def test_equilibria_and_stability(self):
        roots=spring_roots()
        np.testing.assert_allclose(roots,[-np.sqrt(3),0,np.sqrt(3)],atol=1e-12)
        self.assertEqual([spring_slope(r)<0 for r in roots],[True,False,True])
        self.assertEqual(spring_roots(lam=.8),[0.])
        self.assertLess(spring_slope(0,.8),0)

    def test_folds_have_zero_force_and_slope(self):
        for lam in [1.01,1.2,2.,3.]:
            y,b=spring_folds(lam)
            self.assertAlmostEqual(spring_force(-y,b,lam),0,places=12)
            self.assertAlmostEqual(spring_slope(-y,lam),0,places=12)
            self.assertEqual(len(spring_roots(b+.001,lam)),1)

    def test_pulse_threshold_matches_independent_quadrature(self):
        threshold=spring_critical_pulse()
        _,z=integrate(lambda t,z:[spring_force(z[0],.8)],[-np.sqrt(3)],threshold)
        self.assertLess(abs(z[0,-1]),1e-10)
        self.assertLess(spring_pulse(threshold*.8)[1][0,-1],-1.7)
        self.assertGreater(spring_pulse(threshold*1.2)[1][0,-1],1.7)

    def test_energy_including_tilt_jump_work(self):
        t,z,b,residual=spring_pulse(4.5)
        self.assertLess(residual,1e-9)
        self.assertGreaterEqual(np.min(np.diff(z[1])), -1e-12)

    def test_energy_including_continuous_parameter_work(self):
        self.assertLess(spring_ramp(40.)[-1],1e-8)

    def test_smaller_steps_converge_to_reference(self):
        duration=spring_critical_pulse()*1.1
        _,ref=integrate(lambda t,z:[spring_force(z[0],.8)],[-np.sqrt(3)],duration)
        reference=ref[0,-1];errors=[]
        for h in [.4,.2,.1]:
            got=rk4_piecewise(lambda z:spring_force(z,.8),lambda z:spring_force(z),
                             [-np.sqrt(3)],duration,0.,h)[0]
            errors.append(abs(got-reference))
        self.assertLess(errors[1],errors[0]/8)
        self.assertLess(errors[2],errors[1]/8)


class ChemicalChecks(unittest.TestCase):
    def test_physical_interval_inward_rates(self):
        for s in [0.,.5,2.]:
            self.assertGreaterEqual(rates(0,s)[0]-rates(0,s)[1],0)
            self.assertLess(rates(1,s)[0]-rates(1,s)[1],0)

    def test_stationary_states_and_stability(self):
        roots=chemical_roots()
        self.assertEqual(len(roots),3)
        for p in roots:
            a,b=rates(p);self.assertAlmostEqual(a,b,places=11)
        self.assertEqual([chemical_slope(p)<0 for p in roots],[True,False,True])

    def test_derivative_against_finite_differences(self):
        for p in [.01,.2,.4,.8]:
            h=1e-6
            def f(p):
                a,b=rates(p,.5);return a-b
            self.assertAlmostEqual((f(p+h)-f(p-h))/(2*h),chemical_slope(p,.5),places=8)

    def test_no_feedback_against_exact_solution(self):
        duration=.6;t,z=chemical_pulse(duration,mode='no_feedback',post=5)
        first=t<=duration
        at_end=(.5/1.5)*(1-np.exp(-1.5*duration))
        exact=np.where(first,(.5/1.5)*(1-np.exp(-1.5*t)),at_end*np.exp(-(t-duration)))
        self.assertLess(np.max(np.abs(z[0]-exact)),1e-10)

    def test_pulse_threshold_and_memory(self):
        threshold=chemical_critical_pulse()
        _,z=integrate(lambda t,z:[rates(z[0],.5)[0]-rates(z[0],.5)[1]],[0],threshold)
        self.assertAlmostEqual(z[0,-1],chemical_roots()[1],places=10)
        self.assertLess(chemical_pulse(threshold*.8)[1][0,-1],1e-10)
        self.assertGreater(chemical_pulse(threshold*1.2)[1][0,-1],.65)

    def test_conversion_balance_and_nonnegativity(self):
        t,z=chemical_pulse(.6)
        self.assertLess(np.max(np.abs(z[0]-z[1]+z[2])),1e-12)
        self.assertGreaterEqual(np.min(z),-1e-12)
        self.assertLessEqual(np.max(z[0]),1)

    def test_finite_fuel_adenylate_and_phosphate_balances(self):
        t,z=finite_fuel()
        p,ATP,ADP,Pi=z
        self.assertLess(np.max(np.abs(ATP+ADP-2)),1e-11)
        self.assertLess(np.max(np.abs(3*ATP+2*ADP+Pi+p-(6+p[0]))),1e-11)
        self.assertGreaterEqual(np.min(z),-1e-12)
        self.assertLess(p[-1],1e-12)

    def test_fuel_shutdown_erases_memory(self):
        t,z=chemical_pulse(.6,mode='fuel_off',post=10)
        j=np.searchsorted(t,.6,side='right')-1
        self.assertAlmostEqual(z[0,-1],z[0,j]*np.exp(-10),places=11)

    def test_independent_rk4_refinement(self):
        duration=chemical_critical_pulse()*1.1
        ref=chemical_pulse(duration,post=1)[1][0,-1];errors=[]
        def f(s):
            return lambda z:rates(z,s)[0]-rates(z,s)[1]
        for h in [.05,.025,.0125]:
            got=rk4_piecewise(f(.5),f(0),[0.],duration,1.,h)[0]
            errors.append(abs(got-ref))
        self.assertLess(errors[1],errors[0]/8)
        self.assertLess(errors[2],errors[1]/8)

    def test_seeded_counts_conserved_and_repeatable(self):
        for seed in range(4):
            a=gillespie(100,seed,.6,post=2);b=gillespie(100,seed,.6,post=2)
            self.assertEqual(a,b);self.assertEqual(a['balance_residual'],0)
            self.assertTrue(0<=a['final_active_count']<=100)

    def test_no_stimulus_no_spontaneous_source(self):
        self.assertEqual(gillespie(100,42,.6,stimulus=0.)['final_active_count'],0)
        self.assertEqual(chemical_roots(v=0.),[0.])


if __name__=='__main__':unittest.main()
