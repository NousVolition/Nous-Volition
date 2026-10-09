"""Independent analytic checks and invariance tests. Run: python -m unittest -v."""
import math
import random
import unittest
from models import (integrate, logistic, logistic_exact, lorenz, pendulum, spring,
                    spring_exact, threshold, threshold_exact, menger_cells,
                    menger_graph, menger_metrics, koch_metrics, koch_graph, ring_graph)
from sims import run


class DynamicsTests(unittest.TestCase):
    def test_euler_is_first_order_on_logistic_solution(self):
        errors = [abs(integrate(logistic, [0.1], 4, h, 'euler')[-1][1]-logistic_exact(4, 0.1))
                  for h in (0.1, 0.05, 0.025)]
        self.assertTrue(all(1.8 < a/b < 2.2 for a,b in zip(errors, errors[1:])))

    def test_rk4_is_fourth_order_on_exponential(self):
        errors = [abs(integrate(lambda t,x: x, [1], 1, h)[-1][1]-math.e)
                  for h in (0.2, 0.1, 0.05)]
        self.assertTrue(all(14 < a/b < 18 for a,b in zip(errors, errors[1:])))

    def test_logistic_from_above_and_below(self):
        for initial in (0.1, 0.5, 1.5, 2.0):
            rows = integrate(logistic, [initial], 10, 0.05)
            self.assertLess(max(abs(x-logistic_exact(t, initial)) for t,x in rows), 1e-6)

    def test_damped_pendulum_loses_energy(self):
        rows = integrate(pendulum, [1.4, 0], 20, 0.01)
        energies = [v*v/2 + 1-math.cos(x) for _,x,v in rows]
        self.assertTrue(all(b <= a+1e-10 for a,b in zip(energies, energies[1:])))
        self.assertLess(energies[-1], energies[0]/20)

    def test_overdamped_spring_matches_exact_and_does_not_overshoot(self):
        rows = integrate(spring, [1, 0], 20, 0.01)
        self.assertLess(max(abs(x-spring_exact(t)) for t,x,v in rows), 1e-8)
        self.assertTrue(all(x > 0 for _,x,v in rows))
        self.assertTrue(all(v <= 1e-12 for _,x,v in rows))

    def test_lorenz_equilibria(self):
        r = math.sqrt((8/3)*27)
        for state in [(0,0,0), (r,r,27), (-r,-r,27)]:
            self.assertLess(max(map(abs, lorenz(0, state))), 1e-12)

    def test_lorenz_short_time_refinement(self):
        ref = integrate(lorenz, [1,1,1], 1, 0.00125)[-1][1:]
        errors = [math.dist(integrate(lorenz, [1,1,1], 1, h)[-1][1:], ref)
                  for h in (0.01, 0.005)]
        self.assertLess(errors[1], errors[0]/10)

    def test_laser_inspired_threshold_matches_exact(self):
        for pump in (0.5, 1, 1.5):
            rows = integrate(threshold(pump), [0.01], 40, 0.05)
            self.assertLess(max(abs(x-threshold_exact(t, 0.01, pump)) for t,x in rows), 1e-7)
            self.assertTrue(all(x >= 0 for t,x in rows))

    def test_zero_seed_is_absorbing_even_above_threshold(self):
        self.assertEqual(integrate(threshold(2), [0], 10, 0.1)[-1][1], 0)

    def test_bad_integration_settings_fail(self):
        for args in [(1,0,'rk4'), (1,0.3,'rk4'), (1,0.1,'unknown')]:
            with self.assertRaises(ValueError):
                integrate(logistic, [0.1], *args)


class FractalTests(unittest.TestCase):
    def test_menger_counts_volume_and_surface(self):
        for level in range(4):
            result = menger_metrics(level)
            self.assertEqual(result['cubes'], 20**level)
            self.assertAlmostEqual(result['volume'], (20/27)**level)
            self.assertAlmostEqual(result['surface_area'], 2*(20/9)**level+4*(8/9)**level)

    def test_menger_face_contacts_connected(self):
        for level in (1,2):
            cells, graph = menger_cells(level), menger_graph(level)
            visited, pending = {0}, [0]
            while pending:
                node = pending.pop()
                for other in graph[node]:
                    self.assertIn(node, graph[other])
                    self.assertEqual(sum(abs(a-b) for a,b in zip(cells[node], cells[other])), 1)
                    if other not in visited:
                        visited.add(other)
                        pending.append(other)
            self.assertEqual(len(visited), len(graph))

    def test_koch_counts_perimeter_and_area(self):
        initial_area = math.sqrt(3)/4
        for level in range(6):
            result = koch_metrics(level)
            self.assertEqual(result['segments'], 3*4**level)
            self.assertAlmostEqual(result['perimeter'], 3*(4/3)**level, places=9)
            self.assertAlmostEqual(result['area']/initial_area, 8/5-3/5*(4/9)**level, places=10)

    def test_koch_network_is_a_cycle(self):
        for level in range(4):
            self.assertEqual(koch_graph(level), ring_graph(3*4**level))


class SIMSTests(unittest.TestCase):
    def test_koch_and_ring_identical_paired_trajectories(self):
        for seed in range(4):
            rng = random.Random(seed)
            state = [rng.randrange(2) for _ in range(48)]
            for policy in ('ordinary','hold','oppose'):
                self.assertEqual(run(koch_graph(2), state, seed, policy, horizon=20),
                                 run(ring_graph(48), state, seed, policy, horizon=20))

    def test_identity_permutation_changes_only_labels(self):
        graph = menger_graph(1)
        state = [i%2 for i in range(20)]
        labels = list(reversed(range(20)))
        a = run(graph, state, 42, 'oppose', horizon=20)
        b = run(graph, state, 42, 'oppose', horizon=20, seat_to_id=labels)
        for field in ('final','first_consensus','switches','refusals','breaks','credits_by_seat'):
            self.assertEqual(a[field], b[field])
        self.assertEqual(b['credits_by_id'], list(reversed(a['credits_by_seat'])))
        self.assertEqual(b['first_switch_id'], labels[a['first_switch_id']])

    def test_ordinary_agreement_persists_without_initiative(self):
        result = run(ring_graph(9), [0]*9, 13)
        self.assertEqual(result['first_consensus'], 0)
        self.assertEqual(result['switches'], 0)
        self.assertEqual(result['agreement_snapshot_fraction'], 1)

    def test_opponent_breaks_unanimity_on_active_turn(self):
        result = run(ring_graph(9), [0]*9, 13, 'oppose', activation=1, horizon=1)
        self.assertGreater(result['breaks'], 0)

    def test_hold_preserves_focal_color(self):
        for seed in range(10):
            result = run(menger_graph(1), [i%2 for i in range(20)], seed, 'hold', 1, initiative=0.5)
            self.assertEqual(result['final'][1], 1)

    def test_complete_refusal_prevents_copy_switches(self):
        state = [i%2 for i in range(20)]
        result = run(menger_graph(1), state, 5, refusal=1)
        self.assertEqual(result['final'], state)
        self.assertGreater(result['refusals'], 0)


if __name__ == '__main__':
    unittest.main()
