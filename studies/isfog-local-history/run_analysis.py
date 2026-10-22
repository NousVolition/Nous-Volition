"""Separate training-only selection and locked retrospective evaluation commands."""
import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import model as m

ROOT = Path(__file__).resolve().parent
SOURCE_SHA = '565f5cdd872ec98d2ec9dd73bf7493a5ecf2e2dc1e6751295c05af2de361ff17'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def code_hashes():
    return {p: digest(ROOT / p) for p in ('PROTOCOL.md', 'model.py', 'run_analysis.py')}


def load_data(path):
    if digest(path) != SOURCE_SHA:
        raise ValueError('Unexpected source CSV hash; changes require an explicit new protocol')
    return pd.read_csv(path)


def select(data_path, out):
    results = out / 'results'
    results.mkdir(parents=True, exist_ok=True)
    if (results / 'model_lock.json').exists():
        raise FileExistsError('Selection is already locked; use a new output directory for a rerun')
    # No features, targets or statistics from the seven enter this frame.
    raw_train = m.training_partition(load_data(data_path))
    if raw_train[m.GROUP].nunique() != 87:
        raise AssertionError('Expected 87 fitting piles')
    train = m.make_features(raw_train)
    if len(train) != 4257 or train[m.GROUP].nunique() != 87:
        raise AssertionError('Unexpected eligible training coverage')
    spacing = np.concatenate([np.diff(g[m.DEPTH]) for _, g in raw_train.groupby(m.GROUP)])
    if not np.allclose(spacing, .5, atol=1e-10):
        raise AssertionError('Expected source 0.5 m sampling for prefix means')
    print('Training only: 87 piles, 4257 rows, 33 candidates', flush=True)
    scores, pile_scores, assignments = m.grouped_cv(train)
    selected = m.choose(scores)
    pd.DataFrame(scores).sort_values('mean_pile_mae').to_csv(results / 'training_cv_candidates.csv', index=False)
    pd.DataFrame(pile_scores).to_csv(results / 'training_cv_per_pile.csv', index=False)
    write_json(results / 'selection_folds.json', assignments)
    winners = {family: m.choose(scores, family) for family in m.FAMILIES}
    winners['selected'] = selected
    fitted = {family: m.fit(train, candidate) for family, candidate in winners.items()}
    print('Primary training-only choice: ' + selected['name'], flush=True)

    # Nested comparison assesses the selection procedure, not the same fitted model.
    nested_predictions = {family: np.full(len(train), np.nan) for family in winners}
    nested_assignments, inner_score_rows = [], []
    for k, (tr, va, valid_ids) in enumerate(m.folds(train[m.GROUP].to_numpy())):
        outer_train, outer_valid = train.iloc[tr], train.iloc[va]
        inner_scores, _, inner_folds = m.grouped_cv(outer_train, n=4, seed=m.SEED + 100 + k)
        choices = {family: m.choose(inner_scores, family) for family in m.FAMILIES}
        choices['selected'] = m.choose(inner_scores)
        for name, candidate in choices.items():
            nested_predictions[name][va] = m.predict(m.fit(outer_train, candidate), outer_valid)
        nested_assignments.append({'outer_fold': k, 'validation_piles': valid_ids,
                                   'fitting_piles': sorted(outer_train[m.GROUP].unique()),
                                   'inner_folds': inner_folds, 'choices': choices})
        inner_score_rows.extend({'outer_fold': k, **s} for s in inner_scores)
        print(f'Nested outer fold {k + 1}/5 complete: {choices["selected"]["name"]}', flush=True)
    nested_rows, nested_summary = [], {}
    for family, p in nested_predictions.items():
        individual = m.per_pile(train, p)
        nested_rows.extend({'procedure': family, **row} for row in individual)
        nested_summary[family] = {**m.metrics(train[m.TARGET], p),
                                 'mean_pile_mae': float(np.mean([r['mae'] for r in individual])),
                                 'mean_pile_rmse': float(np.mean([r['rmse'] for r in individual]))}
    pd.DataFrame(nested_rows).to_csv(results / 'nested_cv_per_pile.csv', index=False)
    pd.DataFrame(inner_score_rows).to_csv(results / 'nested_inner_candidates.csv', index=False)
    write_json(results / 'nested_folds.json', nested_assignments)
    write_json(results / 'nested_cv_summary.json', nested_summary)
    sensitivity, _, sensitivity_folds = m.grouped_cv(train, seed=m.SEED + 1)
    pd.DataFrame(sensitivity).sort_values('mean_pile_mae').to_csv(results / 'split_sensitivity.csv', index=False)
    write_json(results / 'sensitivity_folds.json', sensitivity_folds)
    lock = {'status': 'frozen_before_this_iteration_seven_pile_evaluation',
            'created_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': SOURCE_SHA,
            'code_sha256': code_hashes(), 'training_piles': sorted(train[m.GROUP].unique()),
            'excluded_piles': list(m.HELDOUT), 'training_rows': len(train),
            'candidate_count': len(m.candidates()), 'primary_seed': m.SEED,
            'selection_metric': 'mean whole-pile MAE, blows/m', 'selected': selected,
            'family_winners': winners, 'fitted_models': fitted,
            'sensitivity_winner_not_used_to_change_selection': m.choose(sensitivity),
            'provenance': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
                           'data_source': 'https://www.kaggle.com/competitions/isfog2020-pile-driving-predictions/data',
                           'reference_study': 'https://github.com/NousVolition/Nous-Volition/tree/main/studies/isfog-pile-tests',
                           'interpretation': 'Previously inspected seven-pile set; new selection restricted to 87 piles.'}}
    write_json(results / 'model_lock.json', lock)
    (results / 'model_lock.sha256').write_text(digest(results / 'model_lock.json') + '\n', encoding='utf-8')
    print(json.dumps({'selected': selected, 'model_lock_sha256': digest(results / 'model_lock.json'),
                      'nested': nested_summary, 'sensitivity_choice': m.choose(sensitivity)}, indent=2), flush=True)


def paired_bootstrap(frame, p_new, p_reference):
    totals = []
    for pile in m.HELDOUT:
        mask = frame[m.GROUP].to_numpy() == pile
        y = frame.loc[mask, m.TARGET].to_numpy()
        en, er = p_new[mask] - y, p_reference[mask] - y
        totals.append([len(y), np.abs(en).sum(), (en ** 2).sum(), np.abs(er).sum(), (er ** 2).sum()])
    totals = np.array(totals)
    samples = np.random.default_rng(m.SEED).integers(0, 7, (10000, 7))
    draw = totals[samples]
    combined = draw.sum(axis=1)
    changes = {
        'mean_pile_mae': np.mean(draw[:, :, 1] / draw[:, :, 0] - draw[:, :, 3] / draw[:, :, 0], axis=1),
        'pooled_mae': (combined[:, 1] - combined[:, 3]) / combined[:, 0],
        'pooled_rmse': np.sqrt(combined[:, 2] / combined[:, 0]) - np.sqrt(combined[:, 4] / combined[:, 0])}
    return {'change_direction': 'new minus reference; negative favors new', 'seed': m.SEED, 'replicates': 10000,
            'percentile_95': {key: np.quantile(value, [.025, .975]).tolist() for key, value in changes.items()},
            'limitation': 'Descriptive paired resampling of seven selected piles, fixed models; no refitting or selection uncertainty.'}


def evaluate(data_path, out, private_out):
    results = out / 'results'
    lock_path = results / 'model_lock.json'
    expected = (results / 'model_lock.sha256').read_text().strip()
    if digest(lock_path) != expected:
        raise ValueError('Model lock checksum mismatch')
    lock = json.loads(lock_path.read_text())
    if lock['code_sha256'] != code_hashes():
        raise ValueError('Scientific code or protocol changed after selection')
    data = load_data(data_path)
    raw_test = data.loc[data[m.GROUP].isin(m.HELDOUT)].copy()
    test = m.make_features(raw_test)
    if len(test) != 353 or set(test[m.GROUP]) != set(m.HELDOUT):
        raise AssertionError('Expected all seven piles and 353 eligible measurements')
    predictions = {name: m.predict(model, test) for name, model in lock['fitted_models'].items()}
    rows, summary, coverage = [], {}, []
    for name, p in predictions.items():
        individual = m.per_pile(test, p)
        rows.extend({'model': name, 'candidate': lock['family_winners'][name]['name'], **r} for r in individual)
        summary[name] = {**m.metrics(test[m.TARGET], p),
                         'mean_pile_mae': float(np.mean([r['mae'] for r in individual])),
                         'mean_pile_rmse': float(np.mean([r['rmse'] for r in individual]))}
    for pile in m.HELDOUT:
        r = raw_test[raw_test[m.GROUP] == pile]
        coverage.append({'pile': pile, 'source_rows': len(r), 'observed_targets': int(r[m.TARGET].notna().sum()),
                         'scored_rows': int((test[m.GROUP] == pile).sum())})
    if any(r['observed_targets'] != r['scored_rows'] for r in coverage):
        raise AssertionError('Not all observed test targets were scored')
    pd.DataFrame(rows).to_csv(results / 'seven_pile_metrics.csv', index=False)
    pd.DataFrame(coverage).to_csv(results / 'seven_pile_coverage.csv', index=False)
    write_json(results / 'seven_pile_summary.json', summary)
    intervals = {'selected_vs_original': paired_bootstrap(test, predictions['selected'], predictions['original']),
                 'local_history_vs_local': paired_bootstrap(test, predictions['local_history'], predictions['local'])}
    write_json(results / 'paired_intervals.json', intervals)
    write_json(results / 'evaluation_receipt.json', {
        'model_lock_sha256': expected, 'evaluated_utc': datetime.now(timezone.utc).isoformat(),
        'selection_created_utc': lock['created_utc'], 'code_unchanged': True,
        'source_sha256': digest(data_path), 'all_observed_targets_scored': True,
        'training_test_overlap': sorted(set(lock['training_piles']) & set(test[m.GROUP])),
        'selection_changed_after_test': False})
    private_out.mkdir(parents=True, exist_ok=True)
    private = test[['ID', m.GROUP, m.DEPTH, m.TARGET]].copy()
    for name, p in predictions.items():
        private[name] = p
    private.to_csv(private_out / 'seven_pile_predictions.csv', index=False)
    print(json.dumps({'summary': summary, 'intervals': intervals}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['select', 'evaluate'])
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=ROOT)
    parser.add_argument('--private-out', type=Path)
    args = parser.parse_args()
    if args.stage == 'select':
        select(args.data, args.out)
    else:
        if args.private_out is None:
            parser.error('Evaluation requires --private-out outside the publication directory')
        if args.out.resolve() == args.private_out.resolve() or args.out.resolve() in args.private_out.resolve().parents:
            parser.error('Private predictions must stay outside publication directory')
        evaluate(args.data, args.out, args.private_out)


if __name__ == '__main__':
    main()
