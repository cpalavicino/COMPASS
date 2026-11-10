"""
Puntuación de una sesión a partir de cualquier clave (ver keys.py).

Trazabilidad: alternativa elegida -> vector de 9 dimensiones MLQ (clave) -> estilo.
  * Distribución por estilo (lo que muestra el gráfico principal): promedio de puntos de la clave por
    dimensión del estilo, sumado sobre las decisiones; % = puntos del estilo / total x 100.
  * Puntaje dimensional analítico (memoria de título): estandarización intra-nodo z_udn y promedio por dimensión.
  * Índice relativo: posición entre el mínimo y el máximo alcanzable con las decisiones encontradas (0-1).
"""
import numpy as np


class StyleMap:
    def __init__(self, cfg):
        self.dims = list(cfg["dimensions"].keys())
        self.styles = list(cfg["styles"].keys())
        self.style_dims = {s: [self.dims.index(d) for d in cfg["styles"][s]["dims"]] for s in self.styles}

    def style_means(self, X):
        """X (..., D) -> (..., S): promedio por dimensión dentro de cada estilo."""
        return np.stack([X[..., self.style_dims[s]].mean(axis=-1) for s in self.styles], axis=-1)


def session_index(session, key, excluded_nodes=()):
    """Mapea decisiones a índices de nodo/alternativa de la clave. Registra faltantes."""
    ni, ai, used, missing = [], [], [], []
    for d in session["decisions"]:
        n = d["node_id"]
        if n in excluded_nodes:
            continue
        if n not in key.node_ids or d.get("alt_id") not in key.alt_ids.get(n, []):
            missing.append(n)
            continue
        ni.append(key.node_ids.index(n))
        ai.append(key.alt_ids[n].index(d["alt_id"]))
        used.append(d)
    return np.array(ni, int), np.array(ai, int), used, missing


def shares_from_points(S, min_total):
    """S (..., m, Sty) puntos por decisión y estilo -> % por estilo (..., Sty). NaN si total ~ 0."""
    tot = S.sum(axis=-2)
    den = tot.sum(axis=-1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        sh = np.where(den > min_total, tot / den * 100, np.nan)
    return sh


def predominant(shares, styles, tol=0.0):
    if shares is None or np.any(np.isnan(shares)):
        return []
    mx = shares.max()
    return [styles[i] for i, v in enumerate(shares) if mx - v <= tol + 1e-12]


def zscores(Kst, ni, ai):
    mean = Kst.mean(axis=1)
    sd = Kst.std(axis=1)            # desviación poblacional entre las alternativas del nodo (memoria, ec. 3.4)
    P = Kst[ni, ai]
    with np.errstate(invalid="ignore", divide="ignore"):
        Z = np.where(sd[ni] > 0, (P - mean[ni]) / sd[ni], 0.0)
    return Z


def relative_index(Kst, ni, ai):
    P = Kst[ni, ai].sum(axis=0)
    mx = Kst.max(axis=1)[ni].sum(axis=0)
    mn = Kst.min(axis=1)[ni].sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(mx - mn > 0, (P - mn) / (mx - mn), np.nan)


def score(Kst, ni, ai, smap, min_total=1e-6):
    P = Kst[ni, ai]                         # (m, D) puntos por decisión y dimensión
    S = smap.style_means(P)                 # (m, Sty)
    sh = shares_from_points(S, min_total)
    Z = zscores(Kst, ni, ai)
    Kst_style = smap.style_means(Kst)       # (N, 3, Sty)
    return {
        "points": P, "style_points": S, "shares": sh,
        "z": Z, "z_mean": Z.mean(axis=0) if len(ni) else np.full(P.shape[1], np.nan),
        "rel_dim": relative_index(Kst, ni, ai),
        "rel_style": relative_index(Kst_style, ni, ai),
        "style_totals": S.sum(axis=0),
    }


def bootstrap_nodes(Kst, ni, ai, smap, B, rng, min_total=1e-6):
    m = len(ni)
    idx = rng.integers(0, m, size=(B, m))
    P = Kst[ni[idx], ai[idx]]               # (B, m, D)
    S = smap.style_means(P)
    sh = shares_from_points(S, min_total)
    mean = Kst.mean(axis=1)
    sd = Kst.std(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        Z = np.where(sd[ni[idx]] > 0, (P - mean[ni[idx]]) / sd[ni[idx]], 0.0)
    mx = Kst.max(axis=1)[ni[idx]].sum(axis=1)
    mn = Kst.min(axis=1)[ni[idx]].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        rel = np.where(mx - mn > 0, (P.sum(axis=1) - mn) / (mx - mn), np.nan)
    return {"shares": sh, "z_mean": Z.mean(axis=1), "rel_dim": rel}


def bootstrap_combined(Krep, ni, ai, smap, rng, min_total=1e-6):
    """Remuestrea simultáneamente jueces (vía réplicas de la clave) y decisiones."""
    B = Krep.shape[0]
    m = len(ni)
    out = np.empty((B, len(smap.styles)))
    for b in range(B):
        idx = rng.integers(0, m, size=m)
        P = Krep[b][ni[idx], ai[idx]]
        out[b] = shares_from_points(smap.style_means(P), min_total)
    return {"shares": out}


def key_replicate_shares(Krep, ni, ai, smap, min_total=1e-6):
    """Solo incertidumbre de la clave (decisiones fijas)."""
    P = Krep[:, ni, ai]                     # (B, m, D)
    return shares_from_points(smap.style_means(P), min_total)


def leave_one_out(Kst, ni, ai, smap, style_idx, min_total=1e-6):
    full = score(Kst, ni, ai, smap, min_total)["shares"][style_idx]
    out = []
    for j in range(len(ni)):
        keep = np.arange(len(ni)) != j
        sh = score(Kst, ni[keep], ai[keep], smap, min_total)["shares"][style_idx]
        out.append(float(full - sh))        # cuánto sube el % del estilo gracias a esta decisión
    return out
