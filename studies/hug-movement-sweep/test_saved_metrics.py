"""Regression for the captured Linux phase mismatch; reject substantive drift."""
import unittest
import numpy as np
from verify_saved import assert_pair_value

class SavedMetricComparisonTests(unittest.TestCase):
    def test_observed_cross_platform_phase_difference(self):
        error=assert_pair_value('max_phase_offset_cycles',7.2416217521542595e-06,7.2416217522249385e-06)
        self.assertGreater(error,0)
        self.assertLess(error,1e-16)

    def test_larger_phase_discrepancy_rejected(self):
        with self.assertRaises(AssertionError):
            assert_pair_value('max_phase_offset_cycles',7.2416217522249385e-06+1e-12,7.2416217522249385e-06)

    def test_nonfinite_phase_never_accepted(self):
        for actual,saved in [(np.nan,np.nan),(np.inf,np.inf),(np.nan,0),(0,-np.inf)]:
            with self.subTest(actual=actual,saved=saved),self.assertRaises(AssertionError):
                assert_pair_value('max_phase_offset_cycles',actual,saved)

    def test_outcome_flags_still_exact(self):
        assert_pair_value('flags',['phase_offset'],['phase_offset'])
        with self.assertRaises(AssertionError):
            assert_pair_value('flags',['phase_offset'],[])

    def test_other_numeric_comparisons_remain_exact(self):
        with self.assertRaises(AssertionError):
            assert_pair_value('relative_period_change',np.nextafter(1.,2.),1.)

if __name__=='__main__':unittest.main()
