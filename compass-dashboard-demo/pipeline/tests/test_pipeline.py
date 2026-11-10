"""Pruebas mínimas del checklist: porcentajes verificables, empate, total cero, regla modal, rank ordering.
Ejecutar desde la raíz:  python -m pytest pipeline/tests  (o  python pipeline/tests/test_pipeline.py)"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from compass_diag import scoring as sc  # noqa: E402
from compass_diag.keys import RankOrderingKey, _aggregate  # noqa: E402
from compass_diag.stats import icc2, wilson_ci  # noqa: E402

CFG = json.loads((ROOT / "config/scoring_config.json").read_text(encoding="utf-8"))
SMAP = sc.StyleMap(CFG)
STY = SMAP.styles


def key_from_styles(rows):
    """rows: lista de nodos; cada nodo = lista de 3 alternativas (T, Tr, P) -> matriz 9 dims."""
    K = np.zeros((len(rows), 3, 9))
    for n, alts in enumerate(rows):
        for a, (t, tr, p) in enumerate(alts):
            K[n, a, 0:5] = t
            K[n, a, 5:7] = tr
            K[n, a, 7:9] = p
    return K


def test_ejemplo_guia_60_30_10():
    # Ejemplo ficticio de la guía: decisiones con aportes 7/2/1 y 5/4/1 -> 12/6/2 -> 60/30/10 %
    K = key_from_styles([[(7, 2, 1), (0, 0, 0), (0, 0, 0)], [(5, 4, 1), (0, 0, 0), (0, 0, 0)]])
    r = sc.score(K, np.array([0, 1]), np.array([0, 0]), SMAP)
    assert np.allclose(r["style_totals"], [12, 6, 2])
    assert np.allclose(r["shares"], [60, 30, 10])
    assert sc.predominant(r["shares"], STY) == ["transformacional"]


def test_empate_exacto():
    K = key_from_styles([[(3, 3, 1), (0, 0, 0), (0, 0, 0)]])
    r = sc.score(K, np.array([0]), np.array([0]), SMAP)
    assert sc.predominant(r["shares"], STY) == ["transformacional", "transaccional"]


def test_total_cero_sin_puntaje():
    K = key_from_styles([[(0, 0, 0), (0, 0, 0), (0, 0, 0)]])
    r = sc.score(K, np.array([0]), np.array([0]), SMAP)
    assert np.all(np.isnan(r["shares"]))
    assert sc.predominant(r["shares"], STY) == []


def test_z_intra_nodo_sin_variacion_es_neutro():
    K = key_from_styles([[(2, 2, 2), (2, 2, 2), (2, 2, 2)]])
    assert np.allclose(sc.zscores(K, np.array([0]), np.array([1])), 0)


def test_moda_con_empate_usa_mediana():
    R = np.array([1, 1, 3, 3, 2]).reshape(5, 1, 1)   # moda empatada 1 y 3; mediana 2 -> empate de distancia -> menor (1)
    assert _aggregate(R, "mode", "closest_to_median_then_lower", 4)[0, 0] == 1
    R = np.array([0, 0, 4, 4, 4, 0, 3]).reshape(7, 1, 1)  # moda 0 y 4 empatadas; mediana 3 -> 4
    assert _aggregate(R, "mode", "closest_to_median_then_lower", 4)[0, 0] == 4


def test_rank_ordering_puntos_y_empates():
    nodes = [{"node_id": "N01", "alternatives": [{"alt_id": "A"}, {"alt_id": "B"}, {"alt_id": "C"}]}]
    dims = list(CFG["dimensions"])
    raw = {"key": {"N01": {d: [["A"], ["C", "B"]] for d in dims}}}
    k = RankOrderingKey(dims, nodes, raw, {})
    assert np.allclose(k.matrix["N01"][:, 0], [2, 0.5, 0.5])


def test_icc_perfecto_y_wilson():
    Y = np.array([[1, 1], [2, 2], [3, 3], [4, 4.0]])
    assert abs(icc2(Y)["icc2k"] - 1) < 1e-9
    p, lo, hi = wilson_ci(19, 26)
    assert lo < p < hi and 0 <= lo and hi <= 1


def test_contrato_generado():
    f = ROOT / "data/diagnosticos.json"
    if not f.exists():
        return
    d = json.loads(f.read_text(encoding="utf-8"))
    for code, s in d["sessions"].items():
        for m, x in s["by_method"].items():
            if x.get("sin_puntaje"):
                continue
            assert abs(sum(x["profile"]["shares"].values()) - 100) < 0.05
            for dec in x["decisions"]:   # lo visible coincide con lo elegido
                ch = [a for a in dec["alternatives"] if a["is_chosen"]]
                assert len(ch) == 1 and ch[0]["alt_id"] == dec["chosen"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
