"""Analytic and independent graph checks; these are NOT water measurements."""
from pathlib import Path
import hashlib
import json
import unittest
import numpy as np
from scipy.sparse.csgraph import shortest_path
from water_topology import (hydrogen_bonds, classify, adjacency, fourth_shell,
                            layer_summary, analyze_snapshot)

P = Path(__file__).resolve().parent
CHAIN = [(0, 1), (1, 2), (2, 3), (3, 4)]


def line(n=5, spacing=2.8):
    return np.column_stack((np.arange(n)*spacing, np.zeros(n), np.zeros(n)))


class TopologyTests(unittest.TestCase):
    def test_exact_chain_and_missing_shell(self):
        rows = classify(line(), CHAIN)
        self.assertAlmostEqual(rows[0]['psi_A'], 11.2)
        self.assertEqual(rows[0]['label'], 'LDL-like')
        self.assertEqual(rows[2]['label'], 'unclassified')
        self.assertIsNone(rows[2]['psi_A'])

    def test_fourth_nearest_is_not_fourth_topological(self):
        o = line(spacing=1)
        o[4] = [0, .5, 0]  # nearest in space but four graph edges away
        rows = classify(o, CHAIN)
        self.assertEqual(rows[0]['psi_A'], .5)
        self.assertEqual(rows[0]['closest_fourth_neighbor'], 4)

    def test_shorter_path_excludes_four_step_walk(self):
        graph = adjacency(5, CHAIN + [(0, 4)])
        self.assertEqual(fourth_shell(graph, 0), [])

    def test_minimum_over_all_exact_four_neighbors(self):
        o = line(6, 1)
        o[5] = [0, 2, 0]
        rows = classify(o, CHAIN + [(3, 5)])
        self.assertEqual(rows[0]['fourth_shell_count'], 2)
        self.assertEqual(rows[0]['psi_A'], 2)

    def test_threshold_equality(self):
        self.assertEqual(classify(line(spacing=1.25), CHAIN)[0]['label'], 'LDL-like')
        self.assertEqual(classify(line(spacing=1.249), CHAIN)[0]['label'], 'HDL-like')

    def test_periodic_endpoint_distance(self):
        o = line(spacing=2.8)
        row = classify(o, CHAIN, [12, 20, 20], [True, False, False])[0]
        self.assertAlmostEqual(row['psi_A'], .8)

    def test_geometric_chain_and_reverse_donor(self):
        o = line()
        h = np.stack((o + [.9572, 0, 0], o + [-.24, .927, 0]), axis=1)
        self.assertEqual(hydrogen_bonds(o, h), CHAIN)
        # Only molecule 1 donates toward molecule 0.
        o2 = np.array([[0, 0, 0], [2.8, 0, 0]])
        h2 = np.array([[[-.95, 0, 0], [-.24, .927, 0]],
                       [[1.85, 0, 0], [3.04, .927, 0]]])
        self.assertEqual(hydrogen_bonds(o2, h2), [(0, 1)])

    def test_both_geometric_cutoffs_are_strict(self):
        def pair(d, hx):
            return hydrogen_bonds([[0, 0, 0], [d, 0, 0]],
                                  [[[hx, 0, 0], [-.5, 0, 0]],
                                   [[d+.5, 0, 0], [d+1, 0, 0]]])
        self.assertEqual(pair(3.5, 1), [])  # O--O equality excludes
        self.assertEqual(pair(3, .5), [])  # H--O equality excludes
        self.assertEqual(pair(3, .501), [(0, 1)])

    def test_hydrogen_bond_across_periodic_boundary(self):
        o = [[.2, 0, 0], [9.2, 0, 0]]
        h = [[[.7, 0, 0], [.2, .8, 0]], [[10.1, 0, 0], [9.2, .8, 0]]]
        self.assertEqual(hydrogen_bonds(o, h), [])
        self.assertEqual(hydrogen_bonds(o, h, [10, 10, 10], [True]*3), [(0, 1)])

    def test_rotation_translation_and_permutation_invariance(self):
        o = line()
        h = np.stack((o + [.9572, 0, 0], o + [-.24, .927, 0]), axis=1)
        q, _ = np.linalg.qr(np.random.default_rng(11).normal(size=(3, 3)))
        shift = [5, 8, 13]
        rot_o, rot_h = o @ q + shift, h @ q + shift
        self.assertEqual(hydrogen_bonds(rot_o, rot_h), CHAIN)
        orig, rot = classify(o, CHAIN), classify(rot_o, CHAIN)
        for a, b in zip(orig, rot):
            if a['psi_A'] is not None:
                self.assertAlmostEqual(a['psi_A'], b['psi_A'])
        perm = np.array([3, 0, 4, 1, 2])
        transformed = classify(o[perm], hydrogen_bonds(o[perm], h[perm]))
        for i, old in enumerate(perm):
            self.assertEqual(transformed[i]['psi_A'], orig[old]['psi_A'])

    def test_cutting_graph_changes_label_without_coordinate_motion(self):
        o = line(6, 1)
        # Extra node 5 creates a two-edge shortcut between 0 and 4.
        full = classify(o, CHAIN + [(0, 5), (5, 4)])
        cut = classify(o[:5], CHAIN)
        self.assertIsNone(full[0]['psi_A'])
        self.assertEqual(cut[0]['psi_A'], 4)
        self.assertEqual(cut[0]['label'], 'HDL-like')

    def test_layer_coverage_and_full_graph_before_selection(self):
        rows = classify(line(), CHAIN)
        stats = layer_summary(rows, ['surface', 'bulk', 'bulk', 'bulk', 'surface'])
        self.assertEqual(stats['surface']['coverage'], 1)
        self.assertEqual(stats['bulk']['coverage'], 0)
        self.assertIsNone(stats['bulk']['HDL_fraction_of_classified'])

    def test_against_independent_all_pairs_shortest_path(self):
        for seed in (3, 17, 41, 89, 123):
            rng = np.random.default_rng(seed)
            n = 35
            matrix = np.triu(rng.random((n, n)) < .075, 1)
            matrix = matrix | matrix.T
            edges = list(zip(*np.where(np.triu(matrix, 1))))
            graph = adjacency(n, edges)
            oracle = shortest_path(matrix.astype(float), directed=False, unweighted=True, method='FW')
            for i in range(n):
                self.assertEqual(fourth_shell(graph, i), np.flatnonzero(oracle[i] == 4).tolist())

    def test_input_guards_and_cli_snapshot(self):
        with self.assertRaises(ValueError):
            classify(line(), [(0, 8)])
        with self.assertRaises(ValueError):
            classify(line(), CHAIN, [[10, 0, 0]]*3, [True]*3)
        with self.assertRaises(ValueError):
            analyze_snapshot({'units': 'nm'})
        data = json.loads((P/'example_chain.json').read_text())
        out = analyze_snapshot(data)
        self.assertEqual(out['layers']['all']['classified'], 2)
        self.assertEqual(len(out['hydrogen_bonds']), 4)
        json.dumps(out, allow_nan=False)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TopologyTests)
    with (P/'test_log.txt').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    summary = dict(status='passed' if result.wasSuccessful() else 'failed',
                   tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                   independent_oracle_graphs=5, independent_oracle_molecule_checks=175,
                   type='synthetic analytic and software verification; no MD or measurement validation',
                   source_sha256=hashlib.sha256((P/'water_topology.py').read_bytes()).hexdigest())
    (P/'verification.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
