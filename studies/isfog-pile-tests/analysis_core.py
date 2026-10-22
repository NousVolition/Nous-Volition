"""Frozen ISFOG notebook features and whole-pile evaluation; no network I/O."""
import numpy as np
import pandas as pd

HELDOUT = ('EL', 'CB', 'AV', 'BV', 'EF', 'DL', 'BM')
TARGET = 'Blowcount [Blows/m]'
ENERGY = 'Normalised ENTRHU [-]'  # Exact spelling in the CSV.
DEPTH = 'z [m]'
GROUP = 'Location ID'
PROXY = 'Integrated cone proxy [MPa m2]'
FEATURES = ['tanh_energy', 'tanh_cone_proxy', 'tanh_depth']
COLUMNS = [DEPTH, 'qc [MPa]', 'fs [MPa]', 'u2 [MPa]', 'ID', GROUP,
           TARGET, ENERGY, 'Normalised hammer energy [-]', 'Number of blows',
           'Diameter [m]', 'Bottom wall thickness [mm]', 'Pile penetration [m]']


def validate_input(data):
    if list(data.columns) != COLUMNS:
        raise ValueError('Input must have the original 13 columns in source order.')
    if data['ID'].isna().any() or data['ID'].duplicated().any():
        raise ValueError('Missing or duplicate row IDs.')
    if data[GROUP].isna().any():
        raise ValueError('Missing location IDs.')
    if not set(HELDOUT).issubset(data[GROUP].unique()):
        raise ValueError('One or more requested test piles are absent.')
    if data.duplicated([GROUP, DEPTH]).any():
        raise ValueError('Duplicate location/depth pairs.')
    numeric = data.select_dtypes(include='number').to_numpy()
    if np.isinf(numeric).any():
        raise ValueError('Infinite input values.')


def build_features(data):
    """Replicate source cumsum exactly, retaining its missing first interval.

    Reject reordered depths instead of quietly producing a different integral.
    Missing qc increments are skipped by pandas cumsum as in the source.
    """
    pieces = []
    for name, raw in data.groupby(GROUP, sort=False):
        frame = raw.copy()
        z = frame[DEPTH].to_numpy(float)
        if not np.isfinite(z).all() or np.any(np.diff(z) <= 0):
            raise ValueError(f'Depths must be finite and strictly ascending: {name}')
        frame[PROXY] = (np.pi * frame['Diameter [m]'] *
                        frame[DEPTH].diff() * frame['qc [MPa]']).cumsum()
        frame[FEATURES[0]] = np.tanh(5 * frame[ENERGY] - .5)
        frame[FEATURES[1]] = np.tanh(.001 * frame[PROXY] - 1)
        frame[FEATURES[2]] = np.tanh(.1 * frame[DEPTH] - .5)
        pieces.append(frame)
    return pd.concat(pieces)


def eligible(data, policy='notebook'):
    if policy == 'notebook':
        return data.dropna()
    if policy == 'required_only':
        return data.dropna(subset=['ID', GROUP, DEPTH, TARGET, *FEATURES])
    raise ValueError('Unknown missingness policy')


def fit_ols(x, y):
    """Centered least squares with intercept, equivalent to dense LinearRegression."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if x.ndim != 2 or len(x) != len(y) or not len(y):
        raise ValueError('Invalid fitting shapes')
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Nonfinite fitting data')
    xm, ym = x.mean(axis=0), y.mean()
    beta, _, rank, _ = np.linalg.lstsq(x - xm, y - ym, rcond=None)
    return {'intercept': float(ym - xm @ beta), 'coefficients': beta.tolist(),
            'rank': int(rank)}


def predict(model, x):
    return np.asarray(x, float) @ np.asarray(model['coefficients']) + model['intercept']


def fit_primary(data, policy='notebook'):
    # Exclude whole locations before computing training features or fitting.
    train = eligible(build_features(data[~data[GROUP].isin(HELDOUT)]), policy)
    return fit_ols(train[FEATURES], train[TARGET]), train


def metrics(y, prediction):
    y, p = np.asarray(y, float), np.asarray(prediction, float)
    if y.shape != p.shape or y.ndim != 1 or not len(y):
        raise ValueError('Invalid evaluation arrays')
    if not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ValueError('Nonfinite evaluation values')
    error = p - y
    sst = float(np.sum((y - y.mean()) ** 2))
    return {'n': len(y), 'rmse_blows_per_m': float(np.sqrt(np.mean(error ** 2))),
            'mae_blows_per_m': float(np.mean(abs(error))),
            'bias_blows_per_m': float(error.mean()),
            'r2': float(1 - np.sum(error ** 2) / sst) if sst else None,
            'negative_predictions': int((p < 0).sum())}


def cluster_intervals(y, p, groups, seed=20261021, repetitions=10000):
    """Percentile bootstrap of entire test piles; fixed fitted model."""
    y, p, groups = np.asarray(y), np.asarray(p), np.asarray(groups)
    totals = []
    for name in HELDOUT:
        e = p[groups == name] - y[groups == name]
        if not len(e):
            raise ValueError(f'No evaluable observations for {name}')
        totals.append([len(e), np.sum(e ** 2), np.sum(abs(e))])
    totals = np.asarray(totals)
    draws = np.random.default_rng(seed).integers(0, len(totals), (repetitions, len(totals)))
    sample = totals[draws].sum(axis=1)
    return {'seed': seed, 'repetitions': repetitions,
            'rmse_percentile_95': np.quantile(np.sqrt(sample[:, 1] / sample[:, 0]), [.025, .975]).tolist(),
            'mae_percentile_95': np.quantile(sample[:, 2] / sample[:, 0], [.025, .975]).tolist(),
            'interpretation': 'Descriptive whole-pile bootstrap, fixed model; seven selected piles, spatial independence not established.'}
