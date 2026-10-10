"""Independent analytic and numerical checks for the new integrator/control design."""
import unittest
import numpy as np
from junction_orders import step,segment,make_orders,GRID,SEEDS


class JunctionTests(unittest.TestCase):
    def test_equilibria(self):
        for method in ('rk4','split_verlet'):
            for bias in (0.,.5,1.):
                z=np.array([np.arcsin(bias),0.])
                np.testing.assert_allclose(step(z,.04,bias,10.,method),z,atol=1e-15,rtol=0)

    def test_exact_drag_velocity(self):
        z=np.array([.2,.8]);beta=2.
        for _ in range(100):z=step(z,.02,0.,beta,'split_verlet',sine_strength=0.)
        self.assertAlmostEqual(z[1],.8*np.exp(-1),places=13)

    def test_second_order_against_exact_damped_motion(self):
        errors=[]
        for h in (.08,.04,.02):
            z=np.array([.2,.8])
            for _ in range(round(2/h)):z=step(z,h,0.,2.,'split_verlet',sine_strength=0.)
            exact=.2+1.6*(1-np.exp(-1))
            errors.append(abs(z[0]-exact))
        self.assertTrue(all(3.99<a/b<4.01 for a,b in zip(errors,errors[1:])))

    def test_rk4_against_exact_linear_solution(self):
        # v'= (i-v)/beta, phi'=v after disabling the sine restoring force.
        z=np.array([.2,.8]);bias=.4;beta=2.;t=4.;h=.02
        for _ in range(round(t/h)):z=step(z,h,bias,beta,'rk4',sine_strength=0.)
        exact=[.2+bias*t+beta*(.8-bias)*(1-np.exp(-t/beta)),bias+(.8-bias)*np.exp(-t/beta)]
        np.testing.assert_allclose(z,exact,atol=3e-11,rtol=0)

    def test_conservative_reversibility(self):
        initial=np.array([.7,.4]);z=initial.copy()
        for _ in range(100):z=step(z,.02,.2,2.,'split_verlet',friction=0)
        for _ in range(100):z=step(z,-.02,.2,2.,'split_verlet',friction=0)
        np.testing.assert_allclose(z,initial,atol=2e-14,rtol=0)

    def test_phase_shift_equivariance(self):
        z=np.array([.4,.2]);a=step(z,.02,.8,2.,'split_verlet');z[0]+=8*np.pi
        b=step(z,.02,.8,2.,'split_verlet');b[0]-=8*np.pi
        np.testing.assert_allclose(a,b,atol=1e-14,rtol=0)

    def test_current_order_reversal(self):
        orders=make_orders();self.assertEqual(len(orders),4+2*len(SEEDS))
        for o in orders:self.assertEqual(sorted(o['indices']),list(range(len(GRID))))
        for k in range(len(SEEDS)):self.assertEqual(orders[4+2*k]['indices'],orders[5+2*k]['indices'][::-1])

    def test_invalid_windows_and_inertia(self):
        with self.assertRaises(ValueError):segment(np.zeros(2),.5,0.,'rk4',.02,1.)
        with self.assertRaises(ValueError):segment(np.zeros(2),.5,2.,'rk4',.03,1.)


if __name__=='__main__':unittest.main()
