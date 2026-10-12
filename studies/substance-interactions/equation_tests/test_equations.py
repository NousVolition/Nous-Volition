import unittest
import numpy as np
from equations import *


class ScreenshotTests(unittest.TestCase):
    def test_cycle_inside_and_outside_exact_flow(self):
        for r in [.01,.2,.8,1,1.5,3]:
            self.assertLess(integrate_cycle(r)['max_position_error'],2e-8)

    def test_cycle_origin_is_an_exception(self):
        z=integrate_cycle(0)
        self.assertEqual(z['final_radius'],0)

    def test_cycle_forward_semigroup(self):
        for r in [.2,1,2]:
            a=radial_exact(1.7,float(radial_exact(.8,r)))
            b=radial_exact(2.5,r)
            self.assertAlmostEqual(float(a),float(b),places=13)

    def test_cycle_backward_blowup_domain(self):
        minimum=.5*np.log(1-1/4)
        self.assertGreater(radial_exact(minimum+.01,2),2)
        with self.assertRaises(ValueError):radial_exact(minimum-.01,2)

    def test_radius_is_nonnegative(self):
        with self.assertRaises(ValueError):radial_exact(1,-1)

    def test_cycle_radial_stability(self):
        self.assertGreater((1-.5**2)*.5,0)
        self.assertLess((1-2**2)*2,0)
        sol=solve_ivp(lambda t,z:[-2*z[0]],(0,2*np.pi),[1],rtol=1e-10,atol=1e-14)
        self.assertLess(abs(sol.y[0,-1]/np.exp(-4*np.pi)-1),2e-8)

    def test_junction_dimensional_mapping(self):
        for i,z0 in [(.5,(0,0)),(.5,(0,2.5)),(1.2,(0,0))]:
            a=junction(i=i,z0=z0,end=100)
            b=junction_si(i=i,z0=z0,end=100)
            self.assertLess(np.max(abs(a['phi']-b['phase'])),2e-6)
            self.assertLess(np.max(abs(a['v']-b['voltage_V']/b['parameters']['V_scale_V'])),2e-6)

    def test_junction_tilted_energy_balance(self):
        z=junction(i=1.2)
        self.assertLess(z['max_energy_balance_error'],2e-6)

    def test_junction_locked_and_running_same_bias(self):
        locked=junction(i=.5);running=junction(i=.5,z0=(0,2.5))
        self.assertLess(abs(locked['phi'][-1]-np.pi/6),1e-8)
        self.assertLess(abs(locked['mean_last50_rate']),1e-8)
        self.assertGreater(running['mean_last50_rate'],1)

    def test_overdamped_rotation_analytic_period(self):
        for i in [1.1,1.2,2]:
            t,exact=overdamped_period(i)
            self.assertLess(abs(t/exact-1),1e-9)

    def test_clock_first_alignment(self):
        t=clock_alignment()
        self.assertAlmostEqual(t,720/11,places=10)
        self.assertAlmostEqual(6*t-.5*t,360,places=10)

    def test_clock_no_earlier_coincidence(self):
        t=np.linspace(1e-6,720/11-1e-6,1000)
        delta=(6-.5)*t
        self.assertTrue(np.all((delta>0)&(delta<360)))

    def test_saddle_balance_exponents(self):
        a=.5;b=-.5
        self.assertEqual(a-b,1);self.assertEqual(2*a,1)

    def test_saddle_transit_analytic(self):
        for r in [1,.1,.01,.001,.0001]:
            t,exact=saddle_transit(r)
            self.assertLess(abs(t/exact-1),1e-8)

    def test_saddle_rescaled_trajectory_collapse(self):
        for r in [1,.01,.0001]:
            t,u,exact=saddle_scaled(r)
            self.assertLess(np.max(abs(u-exact)),1e-8)

    def test_saddle_no_real_transit_formula_for_negative_r(self):
        with self.assertRaises(ValueError):saddle_transit(-.1)

    def test_harmonic_exact_solution_and_energy(self):
        for omega in [.5,1,2]:
            z=oscillator(omega=omega,x0=1,v0=.2)
            self.assertLess(z['max_position_error'],1e-8)
            self.assertLess(z['max_relative_energy_error'],1e-8)

    def test_forward_euler_energy_growth_is_numerical(self):
        z=oscillator(method='Euler')
        predicted=(1+z['dt']**2)**z['steps']
        self.assertLess(abs(z['final_energy_ratio']/predicted-1),1e-10)
        self.assertGreater(z['final_energy_ratio'],3)

    def test_verlet_bounded_energy(self):
        z=oscillator(method='Verlet',periods=50)
        self.assertLess(z['max_relative_energy_error'],.00011)

    def test_verlet_second_order_refinement(self):
        a=oscillator(method='Verlet',step=.04)
        b=oscillator(method='Verlet',step=.02)
        c=oscillator(method='Verlet',step=.01)
        self.assertLess(b['max_position_error'],a['max_position_error']*.26)
        self.assertLess(c['max_position_error'],b['max_position_error']*.26)


if __name__=='__main__':unittest.main()
