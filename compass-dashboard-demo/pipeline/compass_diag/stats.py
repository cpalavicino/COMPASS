"""Utilidades estadísticas sin dependencias más allá de numpy."""
import math

import numpy as np


def percentile_ci(samples, level=0.95):
    a = np.asarray(samples, dtype=float)
    a = a[~np.isnan(a)]
    if a.size == 0:
        return [None, None]
    lo = (1 - level) / 2 * 100
    return [float(np.percentile(a, lo)), float(np.percentile(a, 100 - lo))]


def wilson_ci(successes, n, level=0.95):
    """IC de Wilson para una proporción. Devuelve [p, lo, hi]."""
    if n == 0:
        return [None, None, None]
    z = 1.959963984540054 if level == 0.95 else _z(level)
    p = successes / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [p, max(0.0, centre - half), min(1.0, centre + half)]


def _z(level):
    # aproximación de Acklam para el cuantil normal
    from statistics import NormalDist
    return NormalDist().inv_cdf(0.5 + level / 2)


def icc2(matrix):
    """ICC(2,1) e ICC(2,k) (Shrout & Fleiss). matrix: n objetivos x k jueces, sin NaN."""
    Y = np.asarray(matrix, dtype=float)
    n, k = Y.shape
    if n < 2 or k < 2:
        return {"icc21": None, "icc2k": None, "n": n, "k": k}
    gm = Y.mean()
    ssr = k * ((Y.mean(axis=1) - gm) ** 2).sum()
    ssc = n * ((Y.mean(axis=0) - gm) ** 2).sum()
    sst = ((Y - gm) ** 2).sum()
    sse = sst - ssr - ssc
    msr = ssr / (n - 1)
    msc = ssc / (k - 1)
    mse = sse / ((n - 1) * (k - 1))
    d1 = msr + (k - 1) * mse + k * (msc - mse) / n
    d2 = msr + (msc - mse) / n
    return {"icc21": float((msr - mse) / d1) if d1 else None,
            "icc2k": float((msr - mse) / d2) if d2 else None, "n": n, "k": k,
            "msr": float(msr), "msc": float(msc), "mse": float(mse)}


def spearman_brown(r):
    if r is None or np.isnan(r):
        return None
    return float(2 * r / (1 + r)) if r > -1 else None


def pearson(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    if x.size < 3 or x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def rankdata(a):
    a = np.asarray(a, float)
    order = a.argsort()
    ranks = np.empty(len(a))
    ranks[order] = np.arange(1, len(a) + 1)
    # promediar empates
    for v in np.unique(a):
        m = a == v
        if m.sum() > 1:
            ranks[m] = ranks[m].mean()
    return ranks


def spearman(x, y):
    return pearson(rankdata(x), rankdata(y))


def percentile_rank(value, population):
    p = np.asarray(population, float)
    if p.size == 0:
        return None
    return float(((p < value).sum() + 0.5 * (p == value).sum()) / p.size * 100)


def wilcoxon_r(diffs):
    """Tamaño de efecto r = Z / sqrt(N) del test de rangos con signo (aprox. normal)."""
    d = np.asarray([x for x in diffs if x != 0], float)
    n = d.size
    if n < 5:
        return None
    r = rankdata(np.abs(d))
    w_pos = r[d > 0].sum()
    mean = n * (n + 1) / 4
    sd = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    z = (w_pos - mean) / sd
    return float(z / math.sqrt(n))


def r2(x, nd=3):
    if x is None:
        return None
    if isinstance(x, (list, tuple)):
        return [r2(v, nd) for v in x]
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return round(float(x), nd)
