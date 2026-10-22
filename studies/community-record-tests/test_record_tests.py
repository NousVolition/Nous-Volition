"""Checks of outcome-independent selection, frozen audit and record accounting."""
import csv, hashlib, json, math, tempfile, unittest
from pathlib import Path
import numpy as np
from record_core import candidate, normalize, reason_key, nonoverlap, confusion, window_pairs, require_audit
from compare_wording import verify_lock
from block_episodes import episodes, expiry, paired_duration

ROOT = Path(__file__).parent


class RecordTests(unittest.TestCase):
    def test_html_whitespace(self):
        self.assertEqual(normalize(' A &amp; B\n  C '), 'A & B C')

    def test_reason_only_allowed_normalization(self):
        self.assertEqual(reason_key(' VANDALISM &amp;  disruption '), 'vandalism & disruption')
        self.assertNotEqual(reason_key('Evidence 2020-01-01'), reason_key('Evidence 2020-01-02'))
        self.assertNotEqual(reason_key('https://x/a'), reason_key('https://x/b'))

    def test_exact_control(self):
        a = 'This is a sufficiently long text with several distinct words.'
        self.assertEqual(candidate(a, a)['kind'], 'exact')

    def test_similarity_is_not_equivalence(self):
        a = 'I support this proposed plan for our local community and its schools.'
        b = 'I do not support this proposed plan for our local community and its schools.'
        self.assertEqual(candidate(a, b)['kind'], 'changed')

    def test_short_text_excluded(self):
        self.assertIsNone(candidate('Yes!', 'Yes!'))

    def test_candidate_has_no_outcome_input(self):
        import inspect
        self.assertEqual(list(inspect.signature(candidate).parameters), ['a', 'b'])
        source = (ROOT / 'find_wording.py').read_text()
        query = source.split("query = '''")[1].split("'''")[0]
        self.assertNotIn('Status', query)

    def test_greedy_disjoint(self):
        pairs = [{'earlier': 1, 'later': 2, 'similarity': .9},
                 {'earlier': 2, 'later': 3, 'similarity': .99},
                 {'earlier': 4, 'later': 5, 'similarity': .95}]
        self.assertEqual([(p['earlier'], p['later']) for p in nonoverlap(pairs)], [(2, 3), (4, 5)])

    def test_time_window_inclusive(self):
        p = [{'gap_hours': t} for t in [-.1, 0, 1/6, 1, 24, 25]]
        self.assertEqual(len(window_pairs(p, 1/6)), 2)
        self.assertEqual(len(window_pairs(p, 24)), 4)

    def test_status_accounting(self):
        rows = [{'earlier_status': a, 'later_status': b} for a in ('online', 'deleted') for b in ('online', 'deleted')]
        self.assertEqual(confusion(rows)['discordant'], 2)
        self.assertEqual(confusion(rows)['n'], 4)

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            confusion([{'earlier_status': 'unknown', 'later_status': 'online'}])

    def test_empty_summary(self):
        self.assertIsNone(confusion([])['discordant_fraction'])
        self.assertEqual(paired_duration([]), {'n': 0})

    def test_audit_missing_or_duplicate_rejected(self):
        p = [{'pair_hash': 'a'}]; d = [{'pair_hash': 'a', 'verdict': 'pass', 'reason': 'same claim'}]
        require_audit(p, d)
        for bad in ([], d + d):
            with self.assertRaises(ValueError):
                require_audit(p, bad)

    def test_audit_tampering_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            self.assertIn(ROOT.resolve(), Path(td).resolve().parents)
            a, lock = Path(td) / 'audit.json', Path(td) / 'lock.json'
            a.write_text('[]')
            lock.write_text(json.dumps({'audit_sha256': hashlib.sha256(a.read_bytes()).hexdigest(), 'verdicts_frozen_before_status_join': True}))
            verify_lock(a, lock)
            a.write_text('[1]')
            with self.assertRaises(ValueError):
                verify_lock(a, lock)

    def test_saved_audit_locked(self):
        d, lock = verify_lock(ROOT / 'results/semantic_audit.json', ROOT / 'results/semantic_audit_lock.json')
        self.assertEqual(len(d), 40)
        self.assertEqual(sum(r['verdict'] == 'pass' for r in d), 8)
        receipt = json.loads((ROOT / 'results/status_join_receipt.json').read_text())
        self.assertLess(lock['created_utc'], receipt['first_join_completed_utc'])

    def test_episode_extension_preserves_initial_assignment(self):
        eps, issues = episodes([(0, 1, 'block', 10, 'a', 0), (5, 2, 'reblock', 20, 'b', 1), (25, 3, 'block', 45, 'b', 1)])
        self.assertFalse(issues); self.assertEqual(len(eps), 2)
        self.assertEqual(eps[0]['initial_duration'], 10)
        self.assertEqual(eps[0]['end'], 20)

    def test_orphan_not_new_penalty(self):
        eps, issues = episodes([(5, 2, 'reblock', 20, 'b', 1)])
        self.assertFalse(eps); self.assertIn('orphan_reblock', issues)

    def test_unblock_changes_end_not_assignment(self):
        eps, issues = episodes([(0, 1, 'block', 20, 'a', 0), (5, 2, 'unblock', None, 'a', 0)])
        self.assertFalse(issues); self.assertEqual(eps[0]['end'], 5)
        self.assertEqual(eps[0]['initial_duration'], 20)

    def test_expiry_does_not_invent_unknown_duration(self):
        self.assertIsNone(expiry({'duration': 'until tomorrow'}, 0))
        self.assertTrue(math.isinf(expiry({'duration': 'indefinite'}, 0)))
        self.assertEqual(expiry({'duration': '2 hours'}, 10), 7210)

    def test_paired_summary_known_values(self):
        s = paired_duration([(1, 2), (2, 4), (4, 8)], reps=50)
        self.assertEqual(s['median_ratio'], 2); self.assertEqual(s['longer'], 3)
        self.assertAlmostEqual(s['sign_test_p'], .25)
        self.assertEqual(s['median_log2_ratio_ci95'], [1, 1])

    def test_ties_not_directional_evidence(self):
        s = paired_duration([(1, 1), (2, 2)], reps=30)
        self.assertEqual(s['sign_test_p'], 1); self.assertEqual(s['equal'], 2)

    def test_bootstrap_order_independent(self):
        a = [(1, 4), (2, 3), (3, 2), (5, 10)]
        self.assertEqual(paired_duration(a, reps=50), paired_duration(list(reversed(a)), reps=50))

    def test_saved_cohort_conservation(self):
        c = json.loads((ROOT / 'results/history_results.json').read_text())['cohort']
        self.assertEqual(c['finite_pairs'] + c['second_indefinite'], c['repeated_within_180_days'])

    def test_published_wording_rows_reproduce_counts(self):
        w = json.loads((ROOT / 'results/wording_results.json').read_text())['groups']
        rows = list(csv.DictReader((ROOT / 'results/audited_status_pairs.csv').read_text().splitlines()))
        self.assertEqual(confusion(rows), w['all_changed']['status_pairs'])
        for v in ('pass', 'fail', 'uncertain'):
            self.assertEqual(confusion([r for r in rows if r['verdict'] == v]), w[v]['status_pairs'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
