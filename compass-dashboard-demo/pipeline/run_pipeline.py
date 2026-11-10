"""
Ejecuta el pipeline completo:
  inputs/ (módulo, clave, sesiones)  ->  data/diagnosticos.json + data/diagnosticos.js  ->  reports/*.pdf

Uso (desde la raíz del repositorio):
  python pipeline/run_pipeline.py                 # usa config/scoring_config.json
  python pipeline/run_pipeline.py --method rank_ordering
  python pipeline/run_pipeline.py --sessions all --no-pdf
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from compass_diag.build import build  # noqa: E402


def _np(o):
    import numpy as np
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if np.isnan(o) else round(float(o), 4)
    raise TypeError(type(o))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/scoring_config.json")
    ap.add_argument("--method", choices=["expert_judgment", "rank_ordering"])
    ap.add_argument("--sessions", help="'all' o lista separada por comas")
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args()
    cfg = json.loads((ROOT / a.config).read_text(encoding="utf-8"))
    if a.method:
        cfg["scoring"]["method"] = a.method
    if a.sessions:
        cfg["export"]["sessions"] = "all" if a.sessions == "all" else a.sessions.split(",")
    data = json.loads(json.dumps(build(ROOT, cfg), default=_np))
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    (ROOT / cfg["export"]["out_json"]).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / cfg["export"]["out_js"]).write_text("/* Generado por pipeline/run_pipeline.py — no editar a mano */\nwindow.COMPASS_DATA = " + js + ";\n", encoding="utf-8")
    print(f"diagnosticos: {len(data['sessions'])} sesiones · métodos {data['methods_available']}")
    if not a.no_pdf:
        from compass_diag.report import build_reports
        files = build_reports(ROOT, data, cfg)
        print("informes:", ", ".join(str(f.relative_to(ROOT)) for f in files))


if __name__ == "__main__":
    main()
