import math
import unittest
from models import integrate
from bifurcations import (polynomial_roots,cusp_roots,bead_force,bead_roots,
    bead_derivative,budworm,budworm_derivative,budworm_roots,budworm_fold,
    pitchfork_roots,hoop,full_laser,laser_equilibria,equilibrium_sweep)


class BifurcationTests(unittest.TestCase):
    def test_repeated_polynomial_roots_are_retained(self):
        roots = polynomial_roots([1,0,-3,2])
        self.assertEqual(len(roots),2)
        for a,b in zip(roots,[-2,1]):
            self.assertAlmostEqual(a,b)

    def test_cusp_changes_from_three_to_one_root(self):
        self.assertEqual([r['stability'] for r in cusp_roots(1,0)],['stable','unstable','stable'])
        self.assertEqual(len(cusp_roots(1,0.5)),1)
        self.assertEqual(len(cusp_roots(-1,0)),1)

    def test_cusp_fold_residual_and_derivative_vanish(self):
        x = -1/math.sqrt(3)
        h = 2/(3*math.sqrt(3))
        self.assertAlmostEqual(h+x-x**3,0)
        self.assertAlmostEqual(1-3*x*x,0)

    def test_quasistatic_cusp_hysteresis(self):
        values = [-0.5+i*0.01 for i in range(101)]
        up = equilibrium_sweep(values,lambda h:cusp_roots(1,h))
        down = equilibrium_sweep(list(reversed(values)),lambda h:cusp_roots(1,h),'high')
        self.assertLess(up[50][1],-0.9)
        self.assertGreater(down[50][1],0.9)

    def test_horizontal_bead_matches_geometric_equilibria(self):
        roots = bead_roots(0)
        expected = [-math.sqrt(1.4**2-1),0,math.sqrt(1.4**2-1)]
        for row,x in zip(roots,expected):
            self.assertAlmostEqual(row['x'],x)
        self.assertEqual(len(bead_roots(0,length=0.8)),1)

    def test_tilted_bead_satisfies_user_equation(self):
        for theta in (-0.2,-0.05,0,0.05,0.2):
            for row in bead_roots(math.sin(theta)):
                x = row['x']
                self.assertAlmostEqual(math.sin(theta),x*(1-1.4/math.sqrt(x*x+1)),places=10)

    def test_bead_fold(self):
        x = math.sqrt(1.4**(2/3)-1)
        load = x*(1-1.4/math.sqrt(x*x+1))
        self.assertAlmostEqual(bead_force(x,load),0)
        self.assertAlmostEqual(bead_derivative(x),0)

    def test_budworm_known_three_positive_roots(self):
        roots = budworm_roots(0.5,10)
        for row,x in zip(roots,[0,4-math.sqrt(11),2,4+math.sqrt(11)]):
            self.assertAlmostEqual(row['x'],x)
        self.assertEqual([r['stability'] for r in roots],['unstable','stable','unstable','stable'])

    def test_budworm_fold_curve_satisfies_both_conditions(self):
        for x in (1.1,math.sqrt(3),3,10):
            f = budworm_fold(x)
            self.assertAlmostEqual(budworm(x,f['r'],f['capacity']),0)
            self.assertAlmostEqual(budworm_derivative(x,f['r'],f['capacity']),0)

    def test_budworm_initial_state_selects_basin(self):
        low = integrate(lambda t,s:(budworm(s[0]),),[1],100,0.05)[-1][1]
        high = integrate(lambda t,s:(budworm(s[0]),),[3],100,0.05)[-1][1]
        self.assertAlmostEqual(low,4-math.sqrt(11),places=5)
        self.assertAlmostEqual(high,4+math.sqrt(11),places=5)

    def test_subcritical_pitchfork_roots_and_stability(self):
        self.assertEqual(len(pitchfork_roots(-0.3)),1)
        rows = pitchfork_roots(-0.1)
        self.assertEqual([r['stability'] for r in rows],['stable','unstable','stable','unstable','stable'])
        for row in rows:
            x = row['x']
            self.assertAlmostEqual(-0.1*x+x**3-x**5,0)
        self.assertEqual(len(pitchfork_roots(0.1)),3)

    def test_parameter_a_extension_changes_onset(self):
        self.assertEqual(len(pitchfork_roots(-0.1,a=-1)),1)
        self.assertEqual(len(pitchfork_roots(0.1,a=-1)),3)
        self.assertEqual(len(pitchfork_roots(-0.1,a=1)),5)

    def test_rotating_hoop_equilibria_and_cubic_expansion(self):
        self.assertAlmostEqual(hoop(math.acos(0.5),2),0)
        self.assertLess(hoop(2,2),0)
        phi = 0.01
        self.assertLess(abs(hoop(phi,2)-(phi-7/6*phi**3)),1e-10)

    def test_two_variable_laser_equilibria_and_threshold(self):
        for pump in (0.1,0.2,0.8):
            eq = laser_equilibria(pump)
            for key in ('off','on'):
                if key in eq:
                    self.assertLess(max(map(abs,full_laser(pump)(0,eq[key]))),1e-12)
        eq = laser_equilibria(0.8)
        self.assertTrue(all(v[0]<0 for v in eq['on_eigenvalues']))
        self.assertTrue(any(abs(v[1])>0 for v in eq['on_eigenvalues']))
        self.assertGreater(eq['off_eigenvalues'][0],0)


if __name__=='__main__':
    unittest.main()
