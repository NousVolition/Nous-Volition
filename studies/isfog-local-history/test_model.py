"""Scientific safeguards, independent numerical checks and leakage controls."""
import json
import unittest
import numpy as np
import pandas as pd
import model as m


def example_frame():
    rng = np.random.default_rng(123)
    frame = pd.DataFrame(rng.normal(size=(60, len(m.OPERATING))), columns=m.OPERATING)
    frame[m.TARGET] = 3 + frame[m.DEPTH] * 2 - frame[m.ENERGY] + rng.normal(size=60) * .1
    frame[m.GROUP] = np.repeat(['AA', 'BB', 'CC', 'DD', 'EE', 'FF'], 10)
    return frame


class ScientificChecks(unittest.TestCase):
    def test_candidate_count_and_uniqueness(self):
        self.assertEqual(len(m.candidates()), 33)
        self.assertEqual(len({c['name'] for c in m.candidates()}), 33)

    def test_no_target_or_id_features(self):
        forbidden = {m.TARGET, 'Number of blows', 'ID', m.GROUP, 'Pile penetration [m]'}
        for features in m.FAMILIES.values():
            self.assertFalse(forbidden & set(features))

    def test_history_known_prefix(self):
        h = m.depth_history([0, .5, 1], [2, 6, 999])
        np.testing.assert_allclose(h[:, 0], [2, 2, 4])
        self.assertAlmostEqual(h[2, 1], np.exp(-.5) * 2 + (1 - np.exp(-.5)) * 6)

    def test_history_future_and_current_unchanged(self):
        z = np.arange(20) / 2
        a = np.arange(20, dtype=float)
        b = a.copy()
        b[8:] = -1e6
        np.testing.assert_array_equal(m.depth_history(z, a)[:9], m.depth_history(z, b)[:9])

    def test_history_constant(self):
        np.testing.assert_allclose(m.depth_history(np.arange(8) / 2, np.full(8, 7.)), 7.)

    def test_history_rejects_bad_order(self):
        for z in ([0, 1, 1], [0, 2, 1]):
            with self.assertRaises(ValueError):
                m.depth_history(z, [1, 2, 3])

    def test_excluded_data_cannot_change_training_partition(self):
        a = example_frame()
        extra = a.iloc[:3].copy()
        extra[m.GROUP] = ['EL', 'CB', 'BM']
        raw = pd.concat([a, extra], ignore_index=True)
        poisoned = raw.copy()
        mask = poisoned[m.GROUP].isin(m.HELDOUT)
        poisoned.loc[mask, m.TARGET] = 1e100
        poisoned.loc[mask, m.ENERGY] = -1e100
        pd.testing.assert_frame_equal(m.training_partition(raw), m.training_partition(poisoned))

    def test_selection_rejects_excluded_group(self):
        a = example_frame()
        a.loc[0, m.GROUP] = 'EL'
        with self.assertRaises(ValueError):
            m.grouped_cv(a)

    def test_whole_group_folds(self):
        a = example_frame()
        seen = []
        for tr, va, _ in m.folds(a[m.GROUP].to_numpy(), n=5):
            self.assertFalse(set(a.iloc[tr][m.GROUP]) & set(a.iloc[va][m.GROUP]))
            seen.extend(va.tolist())
        self.assertEqual(sorted(seen), list(range(len(a))))

    def test_group_weight_equal_mass(self):
        groups = np.array(['A', 'A', 'B', 'C', 'C', 'C'])
        w = m.group_weights(groups)
        for g in set(groups):
            self.assertAlmostEqual(w[groups == g].sum(), 1 / 3)

    def test_ridge_against_augmented_least_squares(self):
        a = example_frame()
        c = next(c for c in m.candidates() if c['name'] == 'operating_linear_a0.01')
        model = m.fit(a, c)
        x = a[m.OPERATING].to_numpy()
        w = m.group_weights(a[m.GROUP])
        x = (x - model['raw_mean']) / model['raw_scale']
        x = (x - model['basis_mean']) / model['basis_scale']
        design = np.column_stack([np.ones(len(a)), x])
        penalty = np.column_stack([np.zeros(x.shape[1]), np.sqrt(c['alpha']) * np.eye(x.shape[1])])
        augmented = np.vstack([np.sqrt(w)[:, None] * design, penalty])
        y = np.r_[np.sqrt(w) * a[m.TARGET], np.zeros(x.shape[1])]
        reference = np.linalg.lstsq(augmented, y, rcond=None)[0]
        np.testing.assert_allclose(m.predict(model, a), design @ reference, atol=1e-11)

    def test_fit_only_preprocessing(self):
        a = example_frame()
        c = next(c for c in m.candidates() if c['name'] == 'operating_hinge_a0.1')
        model = m.fit(a.iloc[:40], c)
        before = json.dumps(model, sort_keys=True)
        extreme = a.iloc[40:].copy()
        extreme[m.OPERATING] *= 1e10
        m.predict(model, extreme)
        self.assertEqual(before, json.dumps(model, sort_keys=True))
        w = m.group_weights(a.iloc[:40][m.GROUP])
        np.testing.assert_allclose(model['raw_mean'], w @ a.iloc[:40][m.OPERATING].to_numpy())

    def test_stored_model_roundtrip(self):
        a = example_frame()
        c = m.candidates()[6]
        model = m.fit(a, c)
        np.testing.assert_array_equal(m.predict(model, a), m.predict(json.loads(json.dumps(model)), a))

    def test_original_ols_independent_solution(self):
        a = example_frame()
        a[m.ORIGINAL] = a[m.OPERATING[:3]].to_numpy()
        model = m.fit(a, m.candidates()[0])
        x = np.column_stack([np.ones(len(a)), a[m.ORIGINAL]])
        coef = np.linalg.lstsq(x, a[m.TARGET], rcond=None)[0]
        np.testing.assert_allclose(m.predict(model, a), x @ coef, atol=1e-11)

    def test_metric_known_values(self):
        score = m.metrics([1, 3], [2, 2])
        self.assertEqual(score['mae'], 1.)
        self.assertEqual(score['rmse'], 1.)
        self.assertEqual(score['r2'], 0.)
        self.assertEqual(score['bias'], 0.)

    def test_constant_target_r2_unavailable(self):
        self.assertIsNone(m.metrics([1, 1], [1, 2])['r2'])

    def test_folds_deterministic(self):
        groups = example_frame()[m.GROUP].to_numpy()
        first = [v for _, _, v in m.folds(groups)]
        second = [v for _, _, v in m.folds(groups)]
        self.assertEqual(first, second)

    def test_choice_tie_rule(self):
        a = {'name': 'a', 'family': 'local', 'basis': 'linear', 'alpha': .01, 'mean_pile_mae': 1.}
        b = {**a, 'name': 'b', 'alpha': .1}
        self.assertEqual(m.choose([a, b])['name'], 'b')

    def test_constant_column_finite(self):
        a = example_frame()
        a['Diameter [m]'] = 2.
        c = next(c for c in m.candidates() if c['name'] == 'operating_hinge_a0.001')
        self.assertTrue(np.isfinite(m.predict(m.fit(a, c), a)).all())


if __name__ == '__main__':
    unittest.main()
