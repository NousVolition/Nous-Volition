"""Transparent paired-label and randomized-count calculations; no fitted model."""
from collections import defaultdict
import hashlib
import math
import numpy as np
from scipy.stats import fisher_exact, norm, chi2_contingency

def parse_bool(value):
    if value not in ('True', 'False'):
        raise ValueError(f'Unexpected boolean: {value!r}')
    return value == 'True'

def pair_id(a, b):
    return hashlib.sha256((a + '\0' + b).encode('utf-8')).hexdigest()

def label_index(rows, keys, label):
    groups = defaultdict(set)
    for row in rows:
        groups[tuple(row[k] for k in keys)].add(parse_bool(row[label]))
    unambiguous = {k: next(iter(v)) for k, v in groups.items() if len(v) == 1}
    conflicts = {k for k, v in groups.items() if len(v) != 1}
    return unambiguous, conflicts, len(rows) - sum(len(v) for v in groups.values())

def cluster_interval(cluster_n, cluster_sum, draws=2000, seed=20261021):
    n = np.asarray(cluster_n, dtype=float)
    sums = np.asarray(cluster_sum, dtype=float)
    if len(n) != len(sums) or len(n) == 0 or np.any(n <= 0):
        raise ValueError('Nonempty aligned positive cluster sizes required')
    rng = np.random.default_rng(seed)
    samples = np.empty(draws)
    for i in range(draws):
        take = rng.integers(0, len(n), len(n))
        samples[i] = sums[take].sum() / n[take].sum()
    return dict(estimate=float(sums.sum()/n.sum()), low=float(np.quantile(samples,.025)),
                high=float(np.quantile(samples,.975)), clusters=len(n), draws=draws, seed=seed)

def wilson(k, n):
    if n <= 0 or not 0 <= k <= n:
        raise ValueError('Invalid binomial counts')
    z = float(norm.ppf(.975)); p = k/n; den = 1+z*z/n
    mid = (p+z*z/(2*n))/den
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return max(0.,mid-half), min(1.,mid+half)

def randomized_counts(k1, n1, k0, n0):
    lo1, hi1 = wilson(k1,n1); lo0, hi0 = wilson(k0,n0)
    p1,p0=k1/n1,k0/n0; d=p1-p0
    lower=d-math.sqrt((p1-lo1)**2+(hi0-p0)**2)
    upper=d+math.sqrt((hi1-p1)**2+(p0-lo0)**2)
    table=[[k1,n1-k1],[k0,n0-k0]]
    rr=p1/p0 if p0 else None
    rr_ci=None
    if k1>0 and k0>0:
        se=math.sqrt(1/k1-1/n1+1/k0-1/n0)
        rr_ci=[math.exp(math.log(rr)-1.959963984540054*se),math.exp(math.log(rr)+1.959963984540054*se)]
    return dict(table=table, treatment_rate=p1,control_rate=p0,risk_difference=d,
                risk_difference_ci=[lower,upper],risk_ratio=rr,risk_ratio_log_ci=rr_ci,
                fisher_two_sided_p=float(fisher_exact(table,alternative='two-sided').pvalue),
                pearson_p=float(chi2_contingency(table,correction=False).pvalue),
                treatment_wilson=[lo1,hi1],control_wilson=[lo0,hi0])
