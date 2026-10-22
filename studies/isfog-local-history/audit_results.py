"""Audit saved results and optionally verify a separate numerical rerun."""
import argparse
import hashlib
import io
import json
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
import model as m
import test_model


def audit(out, rerun=None):
    results = out / 'results'
    checks = []

    def check(name, condition):
        checks.append({'check': name, 'passed': bool(condition)})
        if not condition:
            raise AssertionError(name)

    def read(name):
        return json.loads((results / name).read_text())

    lock = read('model_lock.json')
    receipt = read('evaluation_receipt.json')
    cv = pd.read_csv(results / 'training_cv_candidates.csv')
    per = pd.read_csv(results / 'training_cv_per_pile.csv')
    nested = read('nested_cv_summary.json')
    test = pd.read_csv(results / 'seven_pile_metrics.csv')
    test_summary = read('seven_pile_summary.json')
    check('87 distinct fitting piles', len(set(lock['training_piles'])) == 87)
    check('Seven excluded from model lock fitting IDs', not (set(lock['training_piles']) & set(m.HELDOUT)))
    check('All 33 candidates evaluated', len(cv) == 33 and cv['name'].nunique() == 33)
    check('Every candidate has scores for 87 whole piles', len(per) == 33 * 87 and per.groupby('candidate')['pile'].nunique().eq(87).all())
    check('4257 rows per candidate in grouped validation', per.groupby('candidate')['n'].sum().eq(4257).all())
    check('Stored selection matches declared primary score', m.choose(cv.to_dict('records')) == lock['selected'])
    for family in m.FAMILIES:
        check('Family choice uses training scores: ' + family,
              m.choose(cv.to_dict('records'), family) == lock['family_winners'][family])
    seen_outer = []
    for entry in read('nested_folds.json'):
        tr, va = set(entry['fitting_piles']), set(entry['validation_piles'])
        check('Outer groups disjoint: ' + str(entry['outer_fold']), not tr & va)
        seen_inner = []
        for inner in entry['inner_folds']:
            a, b = set(inner['fitting_piles']), set(inner['validation_piles'])
            if a & b or a | b != tr or (a | b) & va:
                raise AssertionError('Nested fitting boundary violated')
            seen_inner.extend(b)
        check('Nested groups contained, disjoint and exhaustive: ' + str(entry['outer_fold']),
              len(seen_inner) == len(tr) and set(seen_inner) == tr)
        seen_outer.extend(va)
    check('All 87 piles scored once by outer validation', len(seen_outer) == 87 and set(seen_outer) == set(lock['training_piles']))
    check('Selected nested procedure and selected family identical here', nested['selected'] == nested['local_history'])
    check('Lock checksum matches evaluation receipt', hashlib.sha256((results / 'model_lock.json').read_bytes()).hexdigest() == receipt['model_lock_sha256'])
    check('Selection timestamp precedes evaluation timestamp', receipt['selection_created_utc'] < receipt['evaluated_utc'])
    check('No training-test overlap', not receipt['training_test_overlap'])
    check('Source hashes agree', receipt['source_sha256'] == lock['source_sha256'])
    for file, sha in lock['code_sha256'].items():
        check('Locked scientific file unchanged: ' + file, hashlib.sha256((Path(__file__).parent / file).read_bytes()).hexdigest() == sha)
    coverage = pd.read_csv(results / 'seven_pile_coverage.csv')
    check('All seven piles represented', set(coverage['pile']) == set(m.HELDOUT))
    check('All 353 observed targets scored', coverage['scored_rows'].sum() == 353 and coverage['scored_rows'].equals(coverage['observed_targets']))
    for family in lock['family_winners']:
        rows = test[test['model'] == family]
        check('Seven scores for ' + family, len(rows) == 7 and set(rows['pile']) == set(m.HELDOUT))
        s = test_summary[family]
        check('Pooled MAE reconciles: ' + family, np.isclose(np.average(rows['mae'], weights=rows['n']), s['mae'], rtol=1e-13))
        check('Pooled RMSE reconciles: ' + family, np.isclose(np.sqrt(np.average(rows['rmse'] ** 2, weights=rows['n'])), s['rmse'], rtol=1e-13))
        check('Equal-pile MAE reconciles: ' + family, np.isclose(rows['mae'].mean(), s['mean_pile_mae'], rtol=1e-13))
    check('Original published RMSE reproduced', np.isclose(test_summary['original']['rmse'], 18.103647630024593, rtol=1e-13))
    check('Original published MAE reproduced', np.isclose(test_summary['original']['mae'], 13.908667597807762, rtol=1e-13))
    check('Stored selected family predictions agree in summary', test_summary['selected'] == test_summary[lock['selected']['family']])
    # These are outcome-specific audit assertions, not criteria used for selection.
    check('Negative cross-validated predictions disclosed', nested['selected']['negative_predictions'] == 19)
    check('No seven-pile negatives in selected predictions', test_summary['selected']['negative_predictions'] == 0)

    if rerun:
        other = rerun / 'results'
        for file in sorted(results.glob('*')):
            if file.suffix not in ('.json', '.csv') or file.name in ('model_lock.json', 'evaluation_receipt.json', 'audit.json'):
                continue
            check('Independent rerun exact: ' + file.name, file.read_bytes() == (other / file.name).read_bytes())
        a, b = lock.copy(), json.loads((other / 'model_lock.json').read_text())
        a.pop('created_utc'); b.pop('created_utc')
        check('Rerun model and selection identical except timestamp', a == b)

    output = io.StringIO()
    run = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_model))
    (results / 'unit_tests.txt').write_text(output.getvalue(), encoding='utf-8')
    check('Scientific unit tests pass', run.wasSuccessful())
    document = {'checks_passed': len(checks), 'unit_tests_passed': run.testsRun,
                'independent_rerun_compared': rerun is not None, 'checks': checks}
    (results / 'audit.json').write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'checks_passed': len(checks), 'unit_tests_passed': run.testsRun}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path(__file__).parent)
    parser.add_argument('--rerun', type=Path)
    args = parser.parse_args()
    audit(args.out, args.rerun)
