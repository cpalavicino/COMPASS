"""
Claves de puntuación. Cada clave expone la misma interfaz para que el resto del pipeline
no dependa del método:

    key.method            -> "expert_judgment" | "rank_ordering"
    key.matrix[node_id]   -> np.ndarray (n_alternativas x n_dimensiones), alternativas en key.alt_ids[node_id]
    key.replicates(B)     -> np.ndarray (B, n_nodos, n_alt, n_dims) o None si el método no tiene
                             una fuente de incertidumbre propia (p. ej., no hay jueces individuales)
    key.quality           -> dict con métricas de calidad de la clave (acuerdo, exclusiones...)

Para conectar la clave definitiva de rank ordering basta con entregar inputs/rank_key.json en el
formato documentado (docs/contrato_datos.md) o, si existen rankings individuales por juez,
implementar `replicates` remuestreando jueces igual que en ExpertJudgmentKey.
"""
import json

import numpy as np

from .stats import icc2, pearson


class BaseKey:
    method = "base"

    def __init__(self, dims, nodes):
        self.dims = dims
        self.node_ids = [n["node_id"] for n in nodes]
        self.alt_ids = {n["node_id"]: [a["alt_id"] for a in n["alternatives"]] for n in nodes}
        self.matrix = {}
        self.quality = {}
        self.meta = {}

    def replicates(self, B, rng):
        return None

    def stack(self):
        return np.stack([self.matrix[n] for n in self.node_ids])


# ---------------------------------------------------------------------------- juicio experto
def _aggregate(R, how, tie_rule, scale_max):
    """R: (E, blocks, D) enteros. Devuelve (blocks, D)."""
    if how == "mean":
        return R.mean(axis=0)
    med = np.median(R, axis=0)
    if how == "median":
        return med
    vals = np.arange(scale_max + 1)
    counts = (R[..., None] == vals).sum(axis=0)              # (blocks, D, V)
    maxc = counts.max(axis=-1, keepdims=True)
    cand = counts == maxc
    if tie_rule == "lower":
        score = np.where(cand, vals, np.inf)
    else:  # closest_to_median_then_lower
        score = np.where(cand, np.abs(vals - med[..., None]) + vals * 1e-3, np.inf)
    return vals[np.argmin(score, axis=-1)].astype(float)


class ExpertJudgmentKey(BaseKey):
    method = "expert_judgment"

    def __init__(self, dims, nodes, raw, cfg):
        super().__init__(dims, nodes)
        self.cfg = cfg
        self.scale_max = int(cfg.get("scale", [0, 4])[1])
        self.blocks = [(n, a) for n in self.node_ids for a in self.alt_ids[n]]
        bidx = {b: i for i, b in enumerate(self.blocks)}
        didx = {d: i for i, d in enumerate(dims)}
        experts = [e["expert_id"] for e in raw["experts"]]
        eidx = {e: i for i, e in enumerate(experts)}
        R = np.full((len(experts), len(self.blocks), len(dims)), np.nan)
        for e, n, a, d, v in raw["ratings"]:
            if (n, a) in bidx and d in didx:
                R[eidx[e], bidx[(n, a)], didx[d]] = v
        missing = int(np.isnan(R).sum())
        if missing:
            # Los faltantes se imputan con la mediana del resto del panel (documentado como supuesto).
            med = np.nanmedian(R, axis=0)
            R = np.where(np.isnan(R), med[None], R)
        self.R_all = R.astype(int)
        self.experts = experts
        self.expert_info = raw["experts"]

        # --- criterios de exclusión (sesgo de respuesta / divergencia de contenido)
        ex_cfg = cfg.get("exclusion", {})
        report = []
        keep = []
        for i, e in enumerate(experts):
            others = np.delete(self.R_all, i, axis=0)
            cons = np.median(others, axis=0)
            mad = float(np.abs(self.R_all[i] - cons).mean())
            corr = pearson(self.R_all[i].ravel(), cons.ravel())
            mean = float(self.R_all[i].mean())
            flags = []
            if ex_cfg.get("enabled", True):
                if mad > ex_cfg.get("max_mad_from_consensus", 9):
                    flags.append("sesgo_de_respuesta")
                if corr < ex_cfg.get("min_corr_with_consensus", -9):
                    flags.append("divergencia_de_contenido")
            excluded = bool(flags) if ex_cfg.get("rule", "any") == "any" else len(flags) == 2
            report.append({"expert_id": e, "formacion": raw["experts"][i].get("formacion"),
                           "media": round(mean, 2), "mad_consenso": round(mad, 3), "r_consenso": round(corr, 3),
                           "flags": flags, "excluido": excluded})
            if not excluded:
                keep.append(i)
        self.keep = keep
        self.R = self.R_all[keep]
        agg = _aggregate(self.R, cfg.get("aggregation", "mode"), cfg.get("mode_tie_rule"), self.scale_max)
        for n in self.node_ids:
            rows = [bidx[(n, a)] for a in self.alt_ids[n]]
            self.matrix[n] = agg[rows]

        # --- acuerdo entre jueces: ICC(2,1) e ICC(2,k) global, por dimensión y por nodo
        k = self.R.shape[0]
        flat = self.R.reshape(k, -1).T
        per_dim = {}
        for j, d in enumerate(dims):
            per_dim[d] = icc2(self.R[:, :, j].T)
        per_node = {}
        for n in self.node_ids:
            rows = [bidx[(n, a)] for a in self.alt_ids[n]]
            per_node[n] = icc2(self.R[:, rows, :].reshape(k, -1).T)
        exact = (self.R == np.round(np.median(self.R, axis=0))).mean()
        within1 = (np.abs(self.R - np.median(self.R, axis=0)) <= 1).mean()
        self.quality = {
            "n_jueces_total": len(experts), "n_jueces_incluidos": k,
            "agregacion": cfg.get("aggregation", "mode"), "regla_empate_modal": cfg.get("mode_tie_rule"),
            "conserva_ceros": cfg.get("keep_zeros", True), "faltantes_imputados": missing,
            "icc_global": icc2(flat), "icc_por_dimension": per_dim, "icc_por_nodo": per_node,
            "acuerdo_exacto_con_mediana": float(exact), "acuerdo_dentro_de_1": float(within1),
            "jueces": report,
        }

    def replicates(self, B, rng):
        """Remuestrea jueces con reemplazo y recalcula la clave (incertidumbre de la clave)."""
        k = self.R.shape[0]
        out = np.empty((B, len(self.node_ids), 3, len(self.dims)))
        how = self.cfg.get("aggregation", "mode")
        tie = self.cfg.get("mode_tie_rule")
        for b in range(B):
            idx = rng.integers(0, k, size=k)
            agg = _aggregate(self.R[idx], how, tie, self.scale_max)
            out[b] = agg.reshape(len(self.node_ids), 3, len(self.dims))
        return out


# ---------------------------------------------------------------------------- rank ordering
class RankOrderingKey(BaseKey):
    method = "rank_ordering"

    def __init__(self, dims, nodes, raw, cfg):
        super().__init__(dims, nodes)
        self.cfg = cfg
        missing = []
        for n in self.node_ids:
            alts = self.alt_ids[n]
            k = len(alts)
            M = np.zeros((k, len(dims)))
            for j, d in enumerate(dims):
                groups = raw.get("key", {}).get(n, {}).get(d)
                if not groups:
                    missing.append(f"{n}:{d}")
                    M[:, j] = (k - 1) / 2   # aporte neutro
                    continue
                pos = 1
                for g in groups:
                    rank = pos + (len(g) - 1) / 2   # rango medio para empates
                    for a in g:
                        M[alts.index(a), j] = k - rank
                    pos += len(g)
            self.matrix[n] = M
        ties = sum(1 for n in self.node_ids for d in dims
                   if any(len(g) > 1 for g in raw.get("key", {}).get(n, {}).get(d, [])))
        self.quality = {"celdas_sin_clave": missing, "celdas_con_empate": ties,
                        "n_celdas": len(self.node_ids) * len(dims),
                        "puntos": cfg.get("points", "k_minus_rank"),
                        "nota": "La clave de rank ordering no incluye rankings por juez en esta demo; la incertidumbre se estima solo remuestreando decisiones."}


def load_key(method, dims, nodes, cfg_scoring, root):
    c = cfg_scoring[method]
    raw = json.loads((root / c["key_file"]).read_text(encoding="utf-8"))
    if method == "expert_judgment":
        return ExpertJudgmentKey(dims, nodes, raw, c)
    if method == "rank_ordering":
        return RankOrderingKey(dims, nodes, raw, c)
    raise ValueError(f"Método de puntuación desconocido: {method}")
