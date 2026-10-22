"""Grouped empirical ISFOG predictors; depth history uses strict CPT prefixes."""
import numpy as np
import pandas as pd

HELDOUT = ('EL', 'CB', 'AV', 'BV', 'EF', 'DL', 'BM')
GROUP = 'Location ID'
TARGET = 'Blowcount [Blows/m]'
DEPTH = 'z [m]'
ENERGY = 'Normalised ENTRHU [-]'
SOIL = ['qc [MPa]', 'fs [MPa]', 'u2 [MPa]']
OPERATING = [DEPTH, ENERGY, 'Diameter [m]', 'Bottom wall thickness [mm]']
ORIGINAL = ['tanh_energy', 'tanh_cone_proxy', 'tanh_depth']
HISTORY = [f'{s} {suffix}' for s in SOIL for suffix in ('prior_mean', 'prior_ew1m', 'prior_ew5m')]
FAMILIES = {'original': ORIGINAL, 'operating': OPERATING,
            'local': OPERATING + SOIL, 'history': OPERATING + HISTORY,
            'local_history': OPERATING + SOIL + HISTORY}
SEED = 20261021


def training_partition(raw):
    """The only source of rows for selection; seven excluded before derivation."""
    return raw.loc[~raw[GROUP].isin(HELDOUT)].copy()


def depth_history(z, values):
    z, v = np.asarray(z, float), np.asarray(values, float)
    if len(z) != len(v) or not len(z) or not np.isfinite(v).all():
        raise ValueError('Invalid soil history inputs')
    if not np.isfinite(z).all() or np.any(np.diff(z) <= 0):
        raise ValueError('Strictly ascending, finite depths required')
    out = np.empty((len(z), 3))
    out[0] = v[0]
    if len(z) > 1:
        out[1:, 0] = np.cumsum(v[:-1]) / np.arange(1, len(v))
    for k, length in enumerate((1., 5.), 1):
        for i in range(1, len(z)):
            decay = np.exp(-(z[i] - z[i - 1]) / length)
            out[i, k] = decay * out[i - 1, k] + (1 - decay) * v[i - 1]
    return out


def make_features(raw):
    if raw['ID'].duplicated().any() or raw['ID'].isna().any():
        raise ValueError('Duplicate or missing row IDs')
    if raw[GROUP].isna().any():
        raise ValueError('Missing pile IDs')
    frames = []
    for name, group in raw.groupby(GROUP, sort=False):
        frame = group.copy()
        z = frame[DEPTH].to_numpy(float)
        for soil in SOIL:
            h = depth_history(z, frame[soil].to_numpy(float))
            for i, suffix in enumerate(('prior_mean', 'prior_ew1m', 'prior_ew5m')):
                frame[f'{soil} {suffix}'] = h[:, i]
        proxy = (np.pi * frame['Diameter [m]'] * frame[DEPTH].diff() * frame[SOIL[0]]).cumsum()
        frame[ORIGINAL[0]] = np.tanh(5 * frame[ENERGY] - .5)
        frame[ORIGINAL[1]] = np.tanh(.001 * proxy - 1)
        frame[ORIGINAL[2]] = np.tanh(.1 * frame[DEPTH] - .5)
        frames.append(frame)
    return pd.concat(frames).dropna().reset_index(drop=True)


def candidates():
    result = [{'name': 'original', 'family': 'original', 'basis': 'original', 'alpha': 0.}]
    for family in ('operating', 'local', 'history', 'local_history'):
        for basis in ('linear', 'hinge'):
            for alpha in (.001, .01, .1, 1.):
                result.append({'name': f'{family}_{basis}_a{alpha:g}',
                               'family': family, 'basis': basis, 'alpha': alpha})
    return result


def group_weights(groups):
    _, inverse, counts = np.unique(np.asarray(groups), return_inverse=True, return_counts=True)
    return 1. / (len(counts) * counts[inverse])


def folds(groups, n=5, seed=SEED):
    names = np.unique(np.asarray(groups))
    if len(names) < n:
        raise ValueError('Too few groups')
    shuffled = np.random.default_rng(seed).permutation(names)
    for valid in np.array_split(shuffled, n):
        mask = np.isin(groups, valid)
        yield np.flatnonzero(~mask), np.flatnonzero(mask), valid.tolist()


def moments(x, w):
    mean = w @ x
    scale = np.sqrt(w @ (x - mean) ** 2)
    scale[scale < 1e-12] = 1.
    return mean, scale


def expand(x, basis, knots):
    if basis == 'linear':
        return x
    return np.column_stack([x] + [np.maximum(x - knot, 0) for knot in knots])


def fit(frame, candidate):
    features = FAMILIES[candidate['family']]
    x = frame[features].to_numpy(float)
    y = frame[TARGET].to_numpy(float)
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Nonfinite fitting input')
    result = {'candidate': candidate, 'features': features}
    if candidate['family'] == 'original':
        xm, ym = x.mean(0), y.mean()
        beta = np.linalg.lstsq(x - xm, y - ym, rcond=None)[0]
        result.update(intercept=float(ym - xm @ beta), coefficients=beta.tolist())
        return result
    w = group_weights(frame[GROUP])
    raw_mean, raw_scale = moments(x, w)
    xs = (x - raw_mean) / raw_scale
    knots = np.quantile(xs, [.25, .5, .75], axis=0) if candidate['basis'] == 'hinge' else np.empty((0, x.shape[1]))
    xb = expand(xs, candidate['basis'], knots)
    basis_mean, basis_scale = moments(xb, w)
    design = (xb - basis_mean) / basis_scale
    ym = float(w @ y)
    beta = np.linalg.solve(design.T @ (w[:, None] * design) + candidate['alpha'] * np.eye(design.shape[1]),
                           design.T @ (w * (y - ym)))
    result.update(intercept=ym, coefficients=beta.tolist(), raw_mean=raw_mean.tolist(),
                  raw_scale=raw_scale.tolist(), knots=knots.tolist(),
                  basis_mean=basis_mean.tolist(), basis_scale=basis_scale.tolist())
    return result


def predict(model, frame):
    x = frame[model['features']].to_numpy(float)
    if model['candidate']['family'] != 'original':
        xs = (x - model['raw_mean']) / model['raw_scale']
        x = (expand(xs, model['candidate']['basis'], model['knots']) - model['basis_mean']) / model['basis_scale']
    return x @ np.asarray(model['coefficients']) + model['intercept']


def metrics(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    if y.shape != p.shape or y.ndim != 1 or not len(y) or not np.isfinite(y + p).all():
        raise ValueError('Invalid evaluation arrays')
    error = p - y
    sst = np.sum((y - y.mean()) ** 2)
    return {'n': len(y), 'mae': float(np.mean(abs(error))), 'rmse': float(np.sqrt(np.mean(error ** 2))),
            'bias': float(error.mean()), 'r2': float(1 - np.sum(error ** 2) / sst) if sst else None,
            'negative_predictions': int((p < 0).sum())}


def per_pile(frame, p):
    records = []
    for name in sorted(frame[GROUP].unique()):
        mask = frame[GROUP].to_numpy() == name
        records.append({'pile': name, **metrics(frame.loc[mask, TARGET], p[mask])})
    return records


def grouped_cv(frame, n=5, seed=SEED):
    """Never accepts excluded piles, including for final split sensitivity."""
    if set(frame[GROUP]) & set(HELDOUT):
        raise ValueError('Excluded piles forbidden in selection')
    all_candidates = candidates()
    predictions = {c['name']: np.full(len(frame), np.nan) for c in all_candidates}
    assignments = []
    for k, (tr, va, ids) in enumerate(folds(frame[GROUP].to_numpy(), n, seed)):
        assignments.append({'fold': k, 'validation_piles': ids,
                            'fitting_piles': sorted(frame.iloc[tr][GROUP].unique())})
        for c in all_candidates:
            predictions[c['name']][va] = predict(fit(frame.iloc[tr], c), frame.iloc[va])
    rows, scores = [], []
    for c in all_candidates:
        values = predictions[c['name']]
        if not np.isfinite(values).all():
            raise AssertionError('CV rows not covered')
        individual = per_pile(frame, values)
        rows.extend({'candidate': c['name'], **r} for r in individual)
        scores.append({**c, 'mean_pile_mae': float(np.mean([r['mae'] for r in individual])),
                       'mean_pile_rmse': float(np.mean([r['rmse'] for r in individual])),
                       'pooled_mae': metrics(frame[TARGET], values)['mae'],
                       'pooled_rmse': metrics(frame[TARGET], values)['rmse']})
    return scores, rows, assignments


def choose(scores, family=None):
    eligible = [s for s in scores if family is None or s['family'] == family]
    best = min(s['mean_pile_mae'] for s in eligible)
    ties = [s for s in eligible if s['mean_pile_mae'] <= best + 1e-10]
    s = min(ties, key=lambda s: (len(FAMILIES[s['family']]), s['basis'] == 'hinge', -s['alpha'], s['name']))
    return {k: s[k] for k in ('name', 'family', 'basis', 'alpha')}
