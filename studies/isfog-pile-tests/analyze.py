"""Run: python analyze.py --data /path/training_data.csv --notebook /path/source.ipynb"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import platform
import sys
import unittest
import io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analysis_core import (HELDOUT, TARGET, ENERGY, GROUP, DEPTH, PROXY, FEATURES,
                           validate_input, build_features, eligible, fit_primary,
                           fit_ols, predict, metrics, cluster_intervals)

HERE = Path(__file__).resolve().parent
URL = 'https://www.kaggle.com/competitions/isfog2020-pile-driving-predictions/data'
LABELS = {'notebook': 'Notebook model', 'mean': 'Training mean',
          'depth': 'Depth only', 'energy': 'Energy only'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data', type=Path, required=True)
    ap.add_argument('--notebook', type=Path, help='Optional original notebook for local hash verification; not executed')
    ap.add_argument('--out', type=Path, default=HERE)
    args = ap.parse_args()
    out = args.out
    for sub in ('results', 'figures'):
        (out / sub).mkdir(parents=True, exist_ok=True)
    audit = []

    def check(name, ok, details=None):
        audit.append({'check': name, 'passed': bool(ok), 'details': details})

    data = pd.read_csv(args.data)
    validate_input(data)
    check('Input matches original notebook shape', data.shape == (7374, 13), list(data.shape))
    check('94 locations', data[GROUP].nunique() == 94, int(data[GROUP].nunique()))
    check('4610 observed targets', data[TARGET].notna().sum() == 4610,
          int(data[TARGET].notna().sum()))
    model, train = fit_primary(data)
    enhanced = build_features(data[data[GROUP].isin(HELDOUT)])
    test = eligible(enhanced)
    models = {'notebook': model}
    columns = {'notebook': FEATURES, 'mean': [], 'depth': [FEATURES[2]], 'energy': [FEATURES[0]]}
    for name in ('mean', 'depth', 'energy'):
        models[name] = fit_ols(train[columns[name]], train[TARGET])
    check('Training and evaluation locations disjoint', set(train[GROUP]).isdisjoint(test[GROUP]))
    check('All seven piles evaluated', set(test[GROUP]) == set(HELDOUT))
    check('87 fitting piles', train[GROUP].nunique() == 87, int(train[GROUP].nunique()))
    check('No duplicate IDs', not data['ID'].duplicated().any())
    check('All source depth increments are 0.5 m', all(
        np.allclose(g[DEPTH].diff().dropna(), .5) for _, g in data.groupby(GROUP)))
    check('No missing cone resistance', not data['qc [MPa]'].isna().any())
    prefix_missing = 0
    for _, group in data.groupby(GROUP):
        last_observation = group.loc[group[TARGET].notna(), DEPTH].max()
        prefix_missing += int(group.loc[group[DEPTH] <= last_observation, 'Diameter [m]'].isna().sum())
    check('Diameter present throughout every scored integral prefix', prefix_missing == 0, prefix_missing)
    missing_diameter = data['Diameter [m]'].isna()
    intake = {'initial_check': 'No missing cone resistance or diameter anywhere in raw CSV',
              'initial_passed': bool(not data[['qc [MPa]', 'Diameter [m]']].isna().any().any()),
              'missing_cone_resistance': int(data['qc [MPa]'].isna().sum()),
              'missing_diameter_rows': int(missing_diameter.sum()),
              'missing_diameter_rows_with_observed_target': int((missing_diameter & data[TARGET].notna()).sum()),
              'missing_diameter_in_scored_integral_prefixes': prefix_missing,
              'resolution': 'Raw CPT extends beyond installed pile geometry. Check diameter completeness along each scored integral prefix instead. Preserve missing values. No predictions changed.'}
    write_json(out / 'results/intake_audit.json', intake)
    check('No negative observed blowcounts', bool((data[TARGET].dropna() >= 0).all()))

    coverage = []
    for loc in ['TRAIN_87', *HELDOUT]:
        raw = data[~data[GROUP].isin(HELDOUT)] if loc == 'TRAIN_87' else data[data[GROUP] == loc]
        scored = train if loc == 'TRAIN_87' else test[test[GROUP] == loc]
        available = int(raw[TARGET].notna().sum())
        coverage.append({'pile': loc, 'source_rows': len(raw), 'observed_target_rows': available,
                         'target_missing_rows': int(raw[TARGET].isna().sum()),
                         'scored_rows': len(scored), 'observed_but_unscored': available - len(scored),
                         'scored_fraction_of_observed': len(scored) / available,
                         'scored_min_depth_m': float(scored[DEPTH].min()),
                         'scored_max_depth_m': float(scored[DEPTH].max())})
    pd.DataFrame(coverage).to_csv(out / 'results/coverage.csv', index=False)

    per_pile, pooled, predictions = [], {}, {}
    for name, fitted in models.items():
        pred = predict(fitted, test[columns[name]])
        predictions[name] = pd.Series(pred, index=test.index)
        pooled[name] = metrics(test[TARGET], pred)
        for loc in HELDOUT:
            mask = test[GROUP] == loc
            per_pile.append({'model': name, 'pile': loc,
                             **metrics(test.loc[mask, TARGET], pred[mask.to_numpy()])})
    table = pd.DataFrame(per_pile)
    table.to_csv(out / 'results/per_pile_metrics.csv', index=False, float_format='%.12g')
    equal_pile = {name: {'mean_pile_rmse_blows_per_m': float(g['rmse_blows_per_m'].mean()),
                         'mean_pile_mae_blows_per_m': float(g['mae_blows_per_m'].mean())}
                  for name, g in table.groupby('model', sort=False)}
    bootstrap = cluster_intervals(test[TARGET], predictions['notebook'], test[GROUP])

    # Reproduce all saved training scores, including the early model rows.
    raw_train = data[~data[GROUP].isin(HELDOUT)].dropna()
    reproduction = []
    candidates = [
        ('Linear energy training', raw_train[[ENERGY]], raw_train[TARGET], .46415658013693784),
        ('Transformed energy training', np.tanh(5 * raw_train[[ENERGY]] - .5), raw_train[TARGET], .5536524756394534),
        ('Cone proxy training', train[[FEATURES[1]]], train[TARGET], .6039306763425601),
        ('Three-feature training', train[FEATURES], train[TARGET], .6226585770981692)]
    for title, x, y, expected in candidates:
        actual = metrics(y, predict(fit_ols(x, y), x))['r2']
        reproduction.append({'check': title, 'saved_r2': expected, 'reproduced_r2': actual,
                             'absolute_difference': abs(actual - expected)})
        check(title + ' R2 reproduces within 1e-8', abs(actual - expected) < 1e-8)
    cb = table[(table.model == 'notebook') & (table.pile == 'CB')].iloc[0]
    reproduction.append({'check': 'CB test', 'saved_r2': .7595697386847187,
                         'reproduced_r2': float(cb.r2), 'absolute_difference': abs(cb.r2 - .7595697386847187)})
    check('Saved CB test R2 reproduces within 1e-8', abs(cb.r2 - .7595697386847187) < 1e-8)
    check('Saved rounded coefficients reproduced', np.allclose(model['coefficients'],
          [2.61421619, 19.8869918, 39.17286467], atol=1e-7, rtol=0))
    check('Saved intercept reproduced', abs(model['intercept'] - 24.574230770198618) < 1e-8)

    # Independent augmented-design least squares verification on actual fitting data.
    augmented = np.c_[np.ones(len(train)), train[FEATURES].to_numpy()]
    other = np.linalg.lstsq(augmented, train[TARGET], rcond=None)[0]
    independent_error = float(np.max(abs(augmented @ other - predict(model, train[FEATURES]))))
    check('Independent OLS implementation agrees below 1e-9 blows/m', independent_error < 1e-9,
          independent_error)
    mutated = data.copy()
    mutated.loc[mutated[GROUP].isin(HELDOUT), TARGET] += 1e6
    check('Changing test outcomes cannot change coefficients', fit_primary(mutated)[0] == model)
    check('Deterministic refit', fit_primary(data)[0] == model)
    required_model, required_train = fit_primary(data, 'required_only')
    required_test = eligible(enhanced, 'required_only')
    sensitivity = {'policy': 'Only required fields must be present',
                   'training_rows': len(required_train), 'test_rows': len(required_test),
                   'extra_training_rows': len(required_train) - len(train),
                   'extra_test_rows': len(required_test) - len(test),
                   'model': required_model,
                   'pooled': metrics(required_test[TARGET], predict(required_model, required_test[FEATURES])),
                   'same_rows_max_prediction_change': float(np.max(abs(
                       predict(required_model, test[FEATURES]) - predictions['notebook'])))}
    check('Coverage accounts for every source row', sum(x['source_rows'] for x in coverage) == len(data))
    check('Coverage accounts for every observed target', sum(x['observed_target_rows'] for x in coverage) == data[TARGET].notna().sum())
    check('Every observed target is scored', len(train) + len(test) == data[TARGET].notna().sum())
    check('Primary results contain all models and all requested piles', len(table) == 4 * 7)

    # Execute deterministic scientific unit tests; retain complete pass/fail output.
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern='test_analysis.py')
    stream = io.StringIO()
    unit = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (out / 'results/unit_tests.txt').write_text(stream.getvalue(), encoding='utf-8')
    check('Scientific unit tests pass', unit.wasSuccessful(), {'run': unit.testsRun})
    write_json(out / 'results/checks.json', audit)
    pd.DataFrame(reproduction).to_csv(out / 'results/notebook_reproduction.csv', index=False)
    write_json(out / 'results/missingness_sensitivity.json', sensitivity)
    write_json(out / 'results/model_coefficients.json', models)
    provenance = {'analysis_date_local': '2026-10-21', 'timezone': 'America/Los_Angeles',
                  'data_source': URL, 'download': 'Kaggle signed-in browser after user accepted rules',
                  'data_filename': args.data.name, 'data_bytes': args.data.stat().st_size,
                  'data_sha256': sha(args.data),
                  'reference_notebook_filename': 'isfog-2020-linear-model-demo.ipynb',
                  'reference_notebook_sha256': '0264e99c3e2d07cff94c6d7fb658bc2955fb22d084b0834b24492dca41159bca',
                  'supplied_notebook_sha256': sha(args.notebook) if args.notebook else None,
                  'notebook_executed': False,
                  'protocol_sha256': sha(HERE / 'PROTOCOL.md'),
                  'python': platform.python_version(), 'numpy': np.__version__,
                  'pandas': pd.__version__, 'matplotlib': matplotlib.__version__,
                  'input_columns': list(data.columns),
                  'missing_by_column': {k: int(v) for k, v in data.isna().sum().items()},
                  'raw_data_redistributed': False,
                  'source_code_sha256': {p.name: sha(p) for p in (HERE / 'analysis_core.py', HERE / 'analyze.py', HERE / 'test_analysis.py')}}
    write_json(out / 'results/provenance.json', provenance)
    summary = {'status': 'completed' if all(x['passed'] for x in audit) else 'completed_with_failed_checks',
               'raw_rows': len(data), 'observed_target_rows': int(data[TARGET].notna().sum()),
               'training_rows': len(train), 'test_rows': len(test), 'excluded_piles': list(HELDOUT),
               'pooled': pooled, 'equal_pile': equal_pile, 'cluster_bootstrap': bootstrap,
               'unit_tests': unit.testsRun, 'checks': len(audit),
               'failed_checks': [x for x in audit if not x['passed']],
               'holdout_status': 'Excluded from fitting; not untouched during historical model selection.'}
    write_json(out / 'results/summary.json', summary)
    make_plots(out, test, predictions, table)
    make_reports(out, summary, table, coverage, reproduction, sensitivity)
    print(json.dumps(summary, indent=2))
    if summary['failed_checks']:
        sys.exit(1)


def make_plots(out, test, predictions, table):
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'savefig.dpi': 160})
    fig, axs = plt.subplots(2, 4, figsize=(14, 9), sharex=True, sharey=True)
    max_x = max(float(test[TARGET].max()), float(predictions['notebook'].max())) * 1.08
    for ax, loc in zip(axs.flat, HELDOUT):
        mask = test[GROUP] == loc
        z = test.loc[mask, DEPTH]
        ax.plot(test.loc[mask, TARGET], z, 'o-', color='#216e91', ms=3, lw=1, label='Measured')
        ax.plot(predictions['notebook'].loc[mask], z, color='#d2691e', lw=2, label='Notebook prediction')
        ax.plot(predictions['depth'].loc[mask], z, '--', color='#666666', lw=1, label='Depth-only control')
        row = table[(table.model == 'notebook') & (table.pile == loc)].iloc[0]
        ax.set_title(f'{loc}: n={int(row.n)}, R²={row.r2:.3f}\nRMSE={row.rmse_blows_per_m:.2f} blows/m')
        ax.grid(alpha=.2)
        ax.set_xlim(min(0., float(predictions['notebook'].min()) * 1.1), max_x)
        ax.set_ylim(float(test[DEPTH].max()) + 1, 0)
        ax.set_xlabel('Blowcount (blows/m)')
        ax.set_ylabel('Depth below mudline (m)')
    axs.flat[-1].axis('off')
    handles, labels = axs.flat[0].get_legend_handles_labels()
    axs.flat[-1].legend(handles, labels, loc='upper left', frameon=False)
    axs.flat[-1].text(.02, .62, 'All seven piles excluded from fitting.\nThe source explored these data\nduring feature development.\n\nActual source measurements,\nresampled to 0.5 m intervals.\nNo outlier removal or clipping.',
                      transform=axs.flat[-1].transAxes, va='top', linespacing=1.6)
    fig.suptitle('ISFOG2020: fixed-model predictions on seven excluded piles', fontsize=16)
    fig.tight_layout(rect=(0, 0, 1, .95))
    fig.savefig(out / 'figures/seven_piles.png')
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5.8))
    xx = np.arange(7)
    for j, (key, color) in enumerate(zip(LABELS, ['#d2691e', '#999999', '#216e91', '#8b65a8'])):
        sub = table[table.model == key].set_index('pile').loc[list(HELDOUT)]
        ax.bar(xx + (j - 1.5) * .2, sub.rmse_blows_per_m, width=.19, label=LABELS[key], color=color)
    ax.set_xticks(xx, HELDOUT)
    ax.set_ylabel('RMSE (blows/m); lower is better')
    ax.set_title('Added complexity does not guarantee a better prediction on every pile')
    ax.legend(ncol=2, frameon=False)
    ax.grid(axis='y', alpha=.2)
    fig.tight_layout()
    fig.savefig(out / 'figures/baseline_comparison.png')
    plt.close(fig)


def make_reports(out, s, table, coverage, reproduction, sensitivity):
    p = s['pooled']['notebook']
    primary = table[table.model == 'notebook'].set_index('pile').loc[list(HELDOUT)]
    lines = ['| Pile | Scored rows | RMSE (blows/m) | MAE (blows/m) | Bias (blows/m) | R² |',
             '|---|---:|---:|---:|---:|---:|']
    for loc, r in primary.iterrows():
        lines.append(f'| {loc} | {int(r.n)} | {r.rmse_blows_per_m:.2f} | {r.mae_blows_per_m:.2f} | {r.bias_blows_per_m:+.2f} | {r.r2:.3f} |')
    result_table = '\n'.join(lines)
    baselines = ['| Model | Pooled RMSE | Pooled MAE | Pooled R² | Mean pile RMSE |',
                 '|---|---:|---:|---:|---:|']
    for key, label in LABELS.items():
        m = s['pooled'][key]
        baselines.append(f'| {label} | {m["rmse_blows_per_m"]:.2f} | {m["mae_blows_per_m"]:.2f} | {m["r2"]:.3f} | {s["equal_pile"][key]["mean_pile_rmse_blows_per_m"]:.2f} |')
    depth_wins = int(sum(primary.loc[loc, 'rmse_blows_per_m'] < table[(table.model == 'depth') & (table.pile == loc)].iloc[0].rmse_blows_per_m for loc in HELDOUT))
    ci = s['cluster_bootstrap']
    text = f'''# Actual pile-driving measurements: all seven excluded piles

Completed 2026-10-21. The unchanged three-feature notebook model was fitted on 87 piles ({s['training_rows']:,} eligible depth records) and tested on EL, CB, AV, BV, EF, DL and BM ({s['test_rows']:,} eligible records). These are field measurements supplied by the ISFOG2020 competition, resampled by the source to 0.5 m, rather than generated scenarios.

Across the seven piles, **RMSE is {p['rmse_blows_per_m']:.2f} blows/m, MAE is {p['mae_blows_per_m']:.2f} blows/m, and R² is {p['r2']:.3f}**. Mean prediction bias is {p['bias_blows_per_m']:+.2f} blows/m. The notebook model has lower RMSE than the depth-only control on {depth_wins} of 7 piles. Every pile is shown below; no unsuccessful cases were discarded.

{result_table}

Positive bias means overprediction. Negative R², if present, means worse squared error than predicting that test pile's observed mean; that diagnostic reference is not a deployable fitted baseline. RMSE gives greater weight to large errors. Individual depth samples within a pile are correlated.

![Measured depth profiles and fixed predictions](figures/seven_piles.png)

## What the comparison establishes

This independently reruns the notebook and extends its one displayed test pile (CB) to all seven fitting exclusions. All four saved training R² values and the saved CB R² reproduce within 1e-8. The code passed {s['unit_tests']} scientific unit tests and {s['checks'] - len(s['failed_checks'])} of {s['checks']} saved-data checks. Full-precision coefficients, per-pile metrics, row coverage, hashes and checks are in [results](results/summary.json).

**EL and EF expose important failures.** Their negative R² values mean the model misses their depth-profile variation badly enough to lose to each pile's own observed mean. It underpredicts EL by 15.34 and EF by 13.32 blows/m on average. Opposite errors in other piles make the pooled bias look almost zero. A small pooled bias does not establish reliable predictions for every pile.

**These are fitting exclusions, not untouched model-selection holdouts.** The source notebook inspected the whole dataset before splitting and used it during feature exploration. CB's result was already visible. Running the fixed model on these seven piles is useful retrospective evidence, but it does not restore blindness or demonstrate transfer to a new offshore site. A future model revision needs separate, previously unused site/pile outcomes and a frozen evaluation plan.

## Controls and uncertainty

All controls use the same primary fitting and evaluation rows, with coefficients fitted only on the other 87 piles. The mean control predicts the fitting-set mean. Depth and energy controls use the notebook's fixed tanh transformations. No replacement model was selected or tuned from these test outcomes.

{chr(10).join(baselines)}

Error units are blows/m. Pooled metrics weight every eligible depth record equally; mean pile RMSE weights each of the seven piles equally and is not the square root of mean pile MSE. Pooled R² uses the overall test mean and can differ substantially from within-pile R².

![Per-pile comparison with simple controls](figures/baseline_comparison.png)

The fixed-model, whole-pile bootstrap (10,000 resamples, seed 20261021) gives a descriptive 95% percentile interval of {ci['rmse_percentile_95'][0]:.2f}–{ci['rmse_percentile_95'][1]:.2f} blows/m for pooled RMSE and {ci['mae_percentile_95'][0]:.2f}–{ci['mae_percentile_95'][1]:.2f} for MAE. Only seven deliberately selected piles are available, spatial independence is unverified, and fitting uncertainty is excluded. These intervals are not a population validation guarantee or a prediction interval for a future pile.

## Inputs, missing records and physical meaning

The CSV contains {s['raw_rows']:,} depth rows from 94 piles, with {s['observed_target_rows']:,} recorded blowcounts. Shallow self-weight penetration and depths below the final installed pile can lack driving observations. Missing targets were never converted to zero. The main evaluation reproduces the notebook's all-column complete-case rule after feature construction. [Coverage](results/coverage.csv) accounts for observed but unscored rows. There are {p['negative_predictions']} negative predictions in the seven-pile primary results; predictions were not clipped.

The predeclared required-fields-only sensitivity adds {sensitivity['extra_training_rows']} fitting rows and {sensitivity['extra_test_rows']} test rows. Its pooled RMSE is {sensitivity['pooled']['rmse_blows_per_m']:.2f} blows/m. [Full sensitivity](results/missingness_sensitivity.json).

The initial intake check incorrectly required diameter at every CPT depth. It flagged 2,052 missing diameters in rows without target measurements. Investigation found zero missing cone-resistance values and zero missing diameters anywhere in the integration prefixes used for scored records. All 4,610 observed targets are scored. The broad failed assumption and its resolution are preserved in [the intake audit](results/intake_audit.json). No measurement was filled in and the model predictions did not change.

The predictors are normalized transmitted hammer energy E, depth z in metres, and an integrated cone-resistance proxy S. At each pile, S is the cumulative sum of pi × diameter × depth increment × cone resistance. The source's first increment remains missing. The three transformations are tanh(5E − 0.5), tanh(0.001S − 1) and tanh(0.1z − 0.5), with an OLS intercept. The original numerical feature scale is preserved.

**Unit correction:** cone resistance in MPa times diameter and depth in metres gives MPa m², equivalent to MN. The notebook labels its raw proxy kN without a factor of 1,000 or a specified shaft-friction factor. This report calls it a proxy, not a measured shaft force. Multiplying by 1,000 while keeping the transformation coefficient unchanged would alter the model. No shaft-force law is validated here.

The energy input was recorded during driving. These predictions are conditional on supplied operating data; they are not complete preinstallation predictions or proof that increasing hammer energy causes a particular change in blowcount. Cumulative number of blows is never a predictor. The competition's other 20 piles have no supplied target in validation_data.csv and are outside this seven-pile test.

## Reproduce and inspect

Download `training_data.csv` through the [official competition data page]({URL}) after signing in and accepting its rules. Exact SHA-256 hashes and environment versions are recorded in [provenance](results/provenance.json). The competition CSV and source notebook are not republished here. The supplied notebook is the reference for the features and saved scores; its contents are not executed, and it is not required to rerun the analysis.

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s . -p test_analysis.py -v
python analyze.py --data /path/to/training_data.csv
```

Run from this study directory. Add `--notebook /path/to/isfog-2020-linear-model-demo.ipynb` to record the hash of a local reference copy, as in the published run. Without it, that provenance field is null; numerical results are identical. The analysis uses centered NumPy least squares, checked independently against an augmented intercept-column solution, to reproduce the source's dense scikit-learn LinearRegression. Outputs overwrite only this study's results, figures and generated report. An optional `--out /path/to/new-output` writes a separate rerun. No authentication, uploads or network calls occur in the analysis script.

- [Fixed protocol](PROTOCOL.md)
- [Per-pile metrics for all four models](results/per_pile_metrics.csv)
- [Notebook score reproduction](results/notebook_reproduction.csv)
- [Unit-test output](results/unit_tests.txt) and [saved-data checks](results/checks.json)
- [Illustrated offline report](report.html)

## Connection to Streams and Rocks

This adds a real physical-data prediction test to the project. It shows how to freeze a rule, compare it with observed outcomes, retain failures and distinguish parameter fitting from model selection. Pile-driving records do not test whether equivalent wording receives unequal moderation or whether past penalties change later treatment. Those community questions still require their own matched human encounter data.

Sources: Bruno Stuyts's [ISFOG2020 competition]({URL}), its [rules](https://www.kaggle.com/competitions/isfog2020-pile-driving-predictions/rules), and the supplied notebook (code cells 24, 28, 53, 57, 67–85, with whole-data depth exploration in cell 65). The official description supplies dataset provenance and field definitions; the equations and saved score checks come from the notebook. The aggregate statistics and plots are newly computed here.
'''
    (out / 'README.md').write_text(text, encoding='utf-8')
    # Minimal self-contained HTML renderer for the generated Markdown subset.
    body, paragraph, listing, code, rows = [], [], [], False, []
    def flush():
        if paragraph:
            body.append('<p>' + ' '.join(paragraph) + '</p>')
            paragraph.clear()
        if listing:
            body.append('<ul>' + ''.join('<li>' + x + '</li>' for x in listing) + '</ul>')
            listing.clear()
        if rows:
            body.append('<div class="table"><table>' + ''.join(rows) + '</table></div>')
            rows.clear()
    import re
    def inline(line):
        line = html.escape(line)
        line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
        line = re.sub(r'`([^`]+)`', r'<code>\1</code>', line)
        line = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', line)
        return line
    for line in text.splitlines():
        if line.startswith('```'):
            flush()
            body.append('</code></pre>' if code else '<pre><code>')
            code = not code
        elif code:
            body.append(html.escape(line) + '\n')
        elif line.startswith('#'):
            flush()
            n = len(line) - len(line.lstrip('#'))
            body.append(f'<h{n}>' + inline(line[n:].strip()) + f'</h{n}>')
        elif line.startswith('!['):
            flush()
            m = re.match(r'!\[(.+)\]\((.+)\)', line)
            body.append(f'<img src="{m[2]}" alt="{html.escape(m[1])}">')
        elif line.startswith('|'):
            if not re.fullmatch(r'[|:\- ]+', line):
                tag = 'th' if not rows else 'td'
                rows.append('<tr>' + ''.join(f'<{tag}>{inline(x.strip())}</{tag}>' for x in line.strip('|').split('|')) + '</tr>')
        elif line.startswith('- '):
            listing.append(inline(line[2:]))
        elif not line.strip():
            flush()
        else:
            paragraph.append(inline(line))
    flush()
    doc = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ISFOG: seven excluded piles</title><style>body{font:17px/1.65 system-ui,sans-serif;color:#20313b;max-width:1120px;margin:auto;padding:36px 24px;background:#fafbf9}h1{font-size:2.1em;line-height:1.2}h2{margin-top:2.2em}a{color:#145f83}img{width:100%;height:auto;background:white}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;background:white}th,td{padding:9px 12px;border-bottom:1px solid #d5dee2;text-align:right}th:first-child,td:first-child{text-align:left}th{background:#e6eef0}.table{overflow:auto}pre{overflow:auto;background:#e6eef0;padding:18px}code{font-size:.9em}</style><main>'''
    (out / 'report.html').write_text(doc + '\n'.join(body) + '</main></html>', encoding='utf-8')


if __name__ == '__main__':
    main()
