import unittest
import numpy as np
import pandas as pd
from analysis_core import (HELDOUT, TARGET, ENERGY, GROUP, DEPTH, PROXY, FEATURES,
                           build_features, eligible, fit_ols, fit_primary, predict, metrics,
                           cluster_intervals)


def fixture():
    rows = []
    for g in ['TRAIN', *HELDOUT]:
        for z in [1., 2., 3., 4., 5.]:
            rows.append({GROUP: g, 'ID': f'{g}_{z}', DEPTH: z, 'qc [MPa]': 2.,
                         'Diameter [m]': 1., ENERGY: z / 10, TARGET: z * 3,
                         'unused': 1.})
    return pd.DataFrame(rows)


class ScientificChecks(unittest.TestCase):
    def test_ols_known_solution(self):
        x = np.array([[0., 1.], [1., 0.], [2., 1.], [1., 3.]])
        m = fit_ols(x, 7 + x @ [2., -3.])
        np.testing.assert_allclose(m['coefficients'], [2., -3.], atol=1e-12)
        self.assertAlmostEqual(m['intercept'], 7.)

    def test_independent_augmented_design(self):
        rng = np.random.default_rng(91)
        x, y = rng.normal(size=(50, 3)), rng.normal(size=50)
        m = fit_ols(x, y)
        b = np.linalg.lstsq(np.c_[np.ones(len(y)), x], y, rcond=None)[0]
        np.testing.assert_allclose(predict(m, x), np.c_[np.ones(len(y)), x] @ b, atol=1e-12)

    def test_constant_control(self):
        m = fit_ols(np.empty((3, 0)), [1., 4., 7.])
        np.testing.assert_allclose(predict(m, np.empty((2, 0))), [4., 4.])

    def test_known_errors_and_bias_direction(self):
        r = metrics([1., 3.], [2., 5.])
        self.assertAlmostEqual(r['rmse_blows_per_m'], np.sqrt(2.5))
        self.assertEqual(r['mae_blows_per_m'], 1.5)
        self.assertEqual(r['bias_blows_per_m'], 1.5)
        self.assertEqual(r['r2'], -1.5)

    def test_constant_target_r2_undefined(self):
        self.assertIsNone(metrics([2., 2.], [2., 2.])['r2'])

    def test_missing_outcome_not_zero(self):
        d = build_features(fixture())
        d.loc[1, TARGET] = np.nan
        self.assertNotIn(1, eligible(d).index)

    def test_group_integrals_reset(self):
        d = build_features(fixture())
        for _, g in d.groupby(GROUP):
            self.assertTrue(np.isnan(g[PROXY].iloc[0]))
            np.testing.assert_allclose(g[PROXY].iloc[1:], 2 * np.pi * np.arange(1, 5))

    def test_dimensional_conversion(self):
        # qc=2 MPa, diameter=1 m, interval=1 m -> 2*pi MN = 2000*pi kN.
        s = build_features(fixture())[PROXY].iloc[1]
        self.assertAlmostEqual(s * 1000, 2000 * np.pi)

    def test_reverse_depth_rejected(self):
        with self.assertRaises(ValueError):
            build_features(fixture().iloc[::-1])

    def test_other_pile_cannot_change_features(self):
        a = fixture()
        b = a.copy()
        b.loc[b[GROUP] == 'BM', 'qc [MPa]'] *= 100
        fa, fb = build_features(a), build_features(b)
        mask = fa[GROUP] == 'EL'
        np.testing.assert_allclose(fa.loc[mask, FEATURES], fb.loc[mask, FEATURES], equal_nan=True)

    def test_heldout_outcomes_cannot_change_fit(self):
        a = fixture()
        b = a.copy()
        b.loc[b[GROUP].isin(HELDOUT), TARGET] += 1e6
        ma, ta = fit_primary(a)
        mb, _ = fit_primary(b)
        self.assertEqual(ma, mb)
        self.assertTrue(set(ta[GROUP]).isdisjoint(HELDOUT))

    def test_unused_missingness_sensitivity(self):
        a = build_features(fixture())
        a.loc[1, 'unused'] = np.nan
        self.assertEqual(len(eligible(a, 'required_only')), len(eligible(a)) + 1)

    def test_negative_predictions_not_clipped(self):
        self.assertEqual(metrics([1., 2.], [-1., 1.])['negative_predictions'], 1)

    def test_bootstrap_reproducible_and_clustered(self):
        y = np.tile([1., 2.], 7)
        g = np.repeat(HELDOUT, 2)
        a = cluster_intervals(y, y + 3, g, repetitions=100)
        self.assertEqual(a, cluster_intervals(y, y + 3, g, repetitions=100))
        np.testing.assert_allclose(a['rmse_percentile_95'], [3., 3.])


if __name__ == '__main__':
    unittest.main(verbosity=2)
