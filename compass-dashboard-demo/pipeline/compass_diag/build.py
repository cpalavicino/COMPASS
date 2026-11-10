"""
Ensambla el diagnóstico de cada sesión en un único contrato JSON (data/diagnosticos.json)
que consume el dashboard y el informe técnico. Ver docs/contrato_datos.md.
"""
import datetime as _dt
import json
from pathlib import Path

import numpy as np

from . import scoring as sc
from .keys import load_key
from .stats import (percentile_ci, percentile_rank, pearson, r2, spearman, spearman_brown,
                    wilcoxon_r, wilson_ci)

SCHEMA_VERSION = "compass-diagnostico/0.3"


# ----------------------------------------------------------------------------- carga
def load_inputs(root, cfg):
    module = json.loads((root / "inputs/module.json").read_text(encoding="utf-8"))
    narr = json.loads((root / "config/narrativas.json").read_text(encoding="utf-8"))
    sessions = {}
    for f in sorted((root / "inputs/sessions").glob("*.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        if s.get("module_id") == module["module_id"]:
            sessions[s["participant_code"]] = s
    return module, narr, sessions


# ----------------------------------------------------------------------------- proceso
def decision_process(d):
    p = d.get("process") or {}
    dwell = p.get("dwell_ms") or {}
    chosen = d["alt_id"]
    if not dwell:
        return None
    most = max(dwell, key=dwell.get)
    disc = [v for a, v in dwell.items() if a != chosen]
    return {"dwell_ms": dwell, "considerations": p.get("considerations"), "alternations": p.get("alternations"),
            "first_considered": p.get("first_considered"), "last_considered": p.get("last_considered"),
            "most_considered": most, "coincide_mas_considerada": most == chosen,
            "dwell_elegida_ms": dwell.get(chosen), "dwell_descartadas_media_ms": float(np.mean(disc)) if disc else None,
            "duracion_ms": (d.get("t_decided_ms") or 0) - (d.get("t_presented_ms") or 0)}


def process_summary(dec_proc, cohort_node_dur, rng, B):
    rows = [p for p in dec_proc if p]
    if not rows:
        return {"disponible": False}
    ch = np.array([p["dwell_elegida_ms"] for p in rows], float)
    di = np.array([p["dwell_descartadas_media_ms"] for p in rows], float)
    diff = ch - di
    boots = [np.median(diff[rng.integers(0, len(diff), len(diff))]) for _ in range(B)]
    coin = sum(p["coincide_mas_considerada"] for p in rows)
    durs = np.array([p["duracion_ms"] for p in rows], float)
    return {"disponible": True, "n": len(rows),
            "dwell_elegida_mediana_ms": float(np.median(ch)), "dwell_descartadas_mediana_ms": float(np.median(di)),
            "diferencia_mediana_ms": float(np.median(diff)), "diferencia_ic95": percentile_ci(boots),
            "wilcoxon_r": wilcoxon_r(diff),
            "coincidencia": wilson_ci(coin, len(rows)), "coincidencia_n": coin,
            "alternancias_media": float(np.mean([p["alternations"] or 0 for p in rows])),
            "duracion_mediana_ms": float(np.median(durs))}


def commitments_summary(commitments):
    n = len(commitments)
    if n == 0:
        return {"n": 0}
    c = sum(1 for x in commitments if x["result"] == "cumplido")
    pa = sum(1 for x in commitments if x["result"] == "parcial")
    w = wilson_ci(c, n)
    return {"n": n, "cumplidos": c, "parciales": pa, "no_cumplidos": n - c - pa,
            "proporcion_cumplidos": w, "indice_ponderado": (c + 0.5 * pa) / n,
            "regla": "cumplido = 1, parcial = 0,5, no cumplido = 0 (índice ponderado). IC de Wilson sobre 'cumplido'."}


# ----------------------------------------------------------------------------- narrativa
def evidence_level(n_support, ci, point, sign, cfg_ev):
    lo, hi = ci if ci else (None, None)
    lo_s = (lo if sign > 0 else (-hi if hi is not None else None))
    if n_support >= cfg_ev["solida"]["min_nodes"] and lo_s is not None and lo_s > cfg_ev["solida"]["ci_lower_gt"]:
        return "sólida"
    if n_support >= cfg_ev["moderada"]["min_nodes"] and sign * point > cfg_ev["moderada"]["point_gt"]:
        return "moderada"
    return "tentativa"


def pick_items(cands, nmax, style_of, cap_per_style=2, cap_inverse=1, active_first=True):
    """Prioriza dimensiones activas; como máximo `cap_inverse` dimensiones pasivas leídas en sentido inverso."""
    out, per = [], {}
    for c in sorted(cands, key=lambda x: ((x["inverse"] if active_first else 0), -x["score"])):
        s = style_of[c["dim"]]
        cap = cap_inverse if c["inverse"] else cap_per_style
        if per.get(s, 0) >= cap:
            continue
        out.append(c)
        per[s] = per.get(s, 0) + 1
        if len(out) >= nmax:
            break
    return out


# ----------------------------------------------------------------------------- principal
def build(root: Path, cfg: dict):
    module, narr, sessions = load_inputs(root, cfg)
    for d, info in cfg["dimensions"].items():
        narr["dimensions"].setdefault(d, {})["label"] = info["label"]
    smap = sc.StyleMap(cfg)
    dims, styles = smap.dims, smap.styles
    style_of = {d: cfg["dimensions"][d]["style"] for d in dims}
    nodes = module["nodes"]
    node_by_id = {n["node_id"]: n for n in nodes}
    unc = cfg["uncertainty"]
    prof_cfg = cfg["profile"]
    min_total = prof_cfg.get("min_total_points", 1e-6)
    tol = prof_cfg.get("tie_tolerance_pct", 0.0)
    excluded_nodes = prof_cfg.get("excluded_nodes", [])
    ncfg = cfg["narrative"]
    passive = set(cfg["styles"]["pasivo"]["dims"]) if ncfg.get("passive_dims_are_inverse") else set()

    methods = [cfg["scoring"]["method"]]
    if cfg["scoring"].get("compare_methods"):
        methods += [m for m in ("expert_judgment", "rank_ordering") if m not in methods]

    export_codes = cfg["export"]["sessions"]
    if export_codes == "all":
        export_codes = list(sessions)

    out = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "synthetic": any(s.get("synthetic") for s in sessions.values()),
        "config_version": cfg.get("config_version"),
        "default_method": cfg["scoring"]["method"],
        "methods_available": methods,
        "styles": {s: cfg["styles"][s] for s in styles},
        "dimensions": {d: {**cfg["dimensions"][d], **{k: v for k, v in narr["dimensions"][d].items()}} for d in dims},
        "themes": narr.get("themes", {}),
        "module": {k: v for k, v in module.items() if k != "nodes"} | {"n_nodes": len(nodes),
                   "nodes_by_type": {t: sum(1 for n in nodes if n["type"] == t) for t in ("obligatorio", "proactivo", "contingente")},
                   "nodes_index": [{k: n.get(k) for k in ("node_id", "order", "title", "day", "block", "type", "theme", "npcs", "condition")} for n in nodes]},
        "status": status_block(),
        "assumptions": assumptions_block(cfg),
        "evidence_context": evidence_context(),
        "methods": {}, "cohort": {"n": len(sessions)}, "sessions": {},
    }

    # duración por nodo en la cohorte (para marcar decisiones rápidas / deliberadas)
    node_dur = {}
    for s in sessions.values():
        for d in s["decisions"]:
            pr = decision_process(d)
            if pr:
                node_dur.setdefault(d["node_id"], []).append(pr["duracion_ms"])
    node_q = {n: (np.percentile(v, 25), np.percentile(v, 75)) for n, v in node_dur.items() if len(v) >= 5}

    for method in methods:
        rng = np.random.default_rng(unc["seed"])
        key = load_key(method, dims, nodes, cfg["scoring"], root)
        Kst = key.stack()
        Krep = key.replicates(unc["bootstrap_combined_B"], rng)

        # --- cohorte
        coh = {}
        for code, s in sessions.items():
            ni, ai, used, missing = sc.session_index(s, key, excluded_nodes)
            if len(ni) == 0:
                continue
            r = sc.score(Kst, ni, ai, smap, min_total)
            coh[code] = {"ni": ni, "ai": ai, "r": r, "used": used}
        sh_mat = np.array([c["r"]["shares"] for c in coh.values()])
        z_mat = np.array([c["r"]["z_mean"] for c in coh.values()])
        pred_counts = {s: 0 for s in styles}
        for c in coh.values():
            for p in sc.predominant(c["r"]["shares"], styles, tol):
                pred_counts[p] += 1
        # fiabilidad por división en mitades (nodos pares / impares) en la cohorte
        split = {}
        halves = []
        for c in coh.values():
            order = np.argsort([node_by_id[key.node_ids[i]]["order"] for i in c["ni"]])
            odd, even = order[0::2], order[1::2]
            r1 = sc.score(Kst, c["ni"][odd], c["ai"][odd], smap, min_total)
            r2_ = sc.score(Kst, c["ni"][even], c["ai"][even], smap, min_total)
            halves.append((r1, r2_))
        for j, d in enumerate(dims):
            r = pearson([h[0]["z_mean"][j] for h in halves], [h[1]["z_mean"][j] for h in halves])
            split[d] = {"r_mitades": r2(r), "spearman_brown": r2(spearman_brown(r))}
        for k_, s in enumerate(styles):
            r = pearson([h[0]["shares"][k_] for h in halves], [h[1]["shares"][k_] for h in halves])
            split[s] = {"r_mitades": r2(r), "spearman_brown": r2(spearman_brown(r))}
        # contraste de la clave y discriminación observada por nodo y dimensión
        inform = []
        for i, nid in enumerate(key.node_ids):
            zs = [c["r"]["z"][list(c["ni"]).index(i)] for c in coh.values() if i in c["ni"]]
            n_users = len(zs)
            row = {"node_id": nid, "n_usuarios": n_users, "C": {}, "S": {}}
            for j, d in enumerate(dims):
                C = float(Kst[i, :, j].max() - Kst[i, :, j].min())
                Sv = float(np.std([z[j] for z in zs], ddof=1)) if n_users > 1 else None
                row["C"][d] = r2(C, 2)
                row["S"][d] = r2(Sv, 2)
            choice = {a: 0 for a in key.alt_ids[nid]}
            for c in coh.values():
                if i in c["ni"]:
                    choice[key.alt_ids[nid][c["ai"][list(c["ni"]).index(i)]]] += 1
            row["eleccion_cohorte"] = choice
            inform.append(row)
        n_noinfo = sum(1 for r in inform for d in dims if r["C"][d] == 0)
        n_nodisc = sum(1 for r in inform for d in dims if r["C"][d] and r["C"][d] > 0 and (r["S"][d] or 0) == 0)

        out["methods"][method] = {
            "label": "Juicio experto (moda del panel)" if method == "expert_judgment" else "Rank ordering",
            "estado": "vigente_demo" if method == "expert_judgment" else "proyectado",
            "key_quality": _clean(key.quality),
            "key": {nid: {a: {d: r2(float(key.matrix[nid][ia, j]), 2) for j, d in enumerate(dims)}
                          for ia, a in enumerate(key.alt_ids[nid])} for nid in key.node_ids},
            "cohort": {
                "n": len(coh),
                "shares_media": {s: r2(float(np.nanmean(sh_mat[:, k]))) for k, s in enumerate(styles)},
                "shares_p25_p75": {s: [r2(float(np.nanpercentile(sh_mat[:, k], 25))), r2(float(np.nanpercentile(sh_mat[:, k], 75)))] for k, s in enumerate(styles)},
                "shares_todas": {s: [r2(float(v), 2) for v in sh_mat[:, k]] for k, s in enumerate(styles)},
                "z_media": {d: r2(float(np.nanmean(z_mat[:, j]))) for j, d in enumerate(dims)},
                "predominante_conteo": pred_counts,
                "fiabilidad_mitades": split,
                "informatividad": inform,
                "celdas_sin_contraste": n_noinfo, "celdas_contraste_sin_discriminacion": n_nodisc,
            },
        }

        # --- sesiones exportadas
        for code in export_codes:
            if code not in sessions:
                continue
            s = sessions[code]
            entry = out["sessions"].setdefault(code, session_header(s, module))
            if code not in coh:
                entry.setdefault("by_method", {})[method] = {"sin_puntaje": True, "motivo": "Sin decisiones puntuables"}
                continue
            c = coh[code]
            entry.setdefault("by_method", {})[method] = session_diag(
                s, c, key, Kst, Krep, smap, dims, styles, style_of, node_by_id, narr, ncfg, passive,
                unc, min_total, tol, sh_mat, z_mat, list(coh.keys()), node_q, rng)

    # sensibilidad al método (cuando hay más de uno)
    if len(methods) > 1:
        a, b = methods[0], methods[1]
        for code, e in out["sessions"].items():
            A, Bm = e["by_method"].get(a), e["by_method"].get(b)
            if not A or not Bm or A.get("sin_puntaje") or Bm.get("sin_puntaje"):
                continue
            za = [A["dimensions"][d]["z_mean"] for d in dims]
            zb = [Bm["dimensions"][d]["z_mean"] for d in dims]
            e["sensibilidad_metodo"] = {"metodos": [a, b],
                                        "mismo_predominante": A["profile"]["predominant"] == Bm["profile"]["predominant"],
                                        "spearman_dimensiones": r2(spearman(za, zb)),
                                        "diferencia_pp": {s: r2(A["profile"]["shares"][s] - Bm["profile"]["shares"][s], 1) for s in styles}}
    return out


def session_header(s, module):
    return {"participant_code": s["participant_code"], "session_id": s["session_id"],
            "synthetic": s.get("synthetic", False), "module_version": s.get("module_version"),
            "started_at": s.get("started_at"), "duration_ms": s.get("duration_ms"),
            "n_decisiones": len(s["decisions"]),
            "nodos_disponibles": module and len(module["nodes"]),
            "global_attributes": s.get("global_attributes", []), "npc_final": s.get("npc_final", {})}


def session_diag(s, c, key, Kst, Krep, smap, dims, styles, style_of, node_by_id, narr, ncfg, passive,
                 unc, min_total, tol, sh_mat, z_mat, coh_codes, node_q, rng):
    ni, ai, used = c["ni"], c["ai"], c["used"]
    r = c["r"]
    level = unc["ci_level"]
    shares = r["shares"]
    pred = sc.predominant(shares, styles, tol)
    if not pred:
        return {"sin_puntaje": True, "motivo": "Total de puntos igual a cero: «Sin puntaje disponible»"}

    bn = sc.bootstrap_nodes(Kst, ni, ai, smap, unc["bootstrap_nodes_B"], rng, min_total)
    stab = {s: 0.0 for s in styles}
    for row in bn["shares"]:
        for p in sc.predominant(row, styles, tol):
            stab[p] += 1 / len(bn["shares"])
    comb, keyonly = None, None
    if Krep is not None:
        comb = sc.bootstrap_combined(Krep, ni, ai, smap, rng, min_total)["shares"]
        keyonly = sc.key_replicate_shares(Krep, ni, ai, smap, min_total)
    stab_pred = stab[pred[0]]
    th = unc["stability_label_thresholds"]
    stab_label = "estable" if stab_pred >= th["estable"] else ("moderada" if stab_pred >= th["moderada"] else "inestable")

    idx_coh = coh_codes.index(s["participant_code"])
    profile = {
        "predominant": pred, "empate": len(pred) > 1,
        "shares": {st: r2(float(shares[k]), 2) for k, st in enumerate(styles)},
        "points": {st: r2(float(r["style_totals"][k]), 2) for k, st in enumerate(styles)},
        "total_points": r2(float(r["style_totals"].sum()), 2),
        "shares_ci_nodos": {st: r2(percentile_ci(bn["shares"][:, k], level), 2) for k, st in enumerate(styles)},
        "shares_ci_clave": ({st: r2(percentile_ci(keyonly[:, k], level), 2) for k, st in enumerate(styles)} if keyonly is not None else None),
        "shares_ci_combinado": ({st: r2(percentile_ci(comb[:, k], level), 2) for k, st in enumerate(styles)} if comb is not None else None),
        "estabilidad_predominio": {st: r2(v) for st, v in stab.items()},
        "estabilidad_etiqueta": stab_label,
        "bootstrap_hist": {st: np.histogram(bn["shares"][:, k], bins=24, range=(0, 100))[0].tolist() for k, st in enumerate(styles)},
        "rel_style": {st: r2(float(r["rel_style"][k])) for k, st in enumerate(styles)},
        "percentil_cohorte": {st: r2(percentile_rank(shares[k], np.delete(sh_mat[:, k], idx_coh)), 1) for k, st in enumerate(styles)},
        "n_decisiones": int(len(ni)),
    }
    dim_out = {}
    for j, d in enumerate(dims):
        ci = percentile_ci(bn["z_mean"][:, j], level)
        dim_out[d] = {"z_mean": r2(float(r["z_mean"][j])), "z_ci": r2(ci),
                      "rel": r2(float(r["rel_dim"][j])), "rel_ci": r2(percentile_ci(bn["rel_dim"][:, j], level)),
                      "points": r2(float(r["points"][:, j].sum()), 2),
                      "percentil_cohorte": r2(percentile_rank(r["z_mean"][j], np.delete(z_mat[:, j], idx_coh)), 1)}

    # --- decisiones
    pidx = styles.index(pred[0])
    infl = sc.leave_one_out(Kst, ni, ai, smap, pidx, min_total)
    decisions = []
    commit_by_node = {x["node_id"]: x for x in s.get("commitments", [])}
    proc_rows = []
    for j, d in enumerate(used):
        nid = d["node_id"]
        node = node_by_id[nid]
        i = ni[j]
        alts = []
        for ia, a in enumerate(key.alt_ids[nid]):
            na = node["alternatives"][ia]
            sp = smap.style_means(Kst[i, ia])
            alts.append({"alt_id": a, "text": na["text"], "is_chosen": ia == ai[j],
                         "points": {dd: r2(float(Kst[i, ia, jj]), 2) for jj, dd in enumerate(dims)},
                         "style_points": {st: r2(float(sp[k]), 2) for k, st in enumerate(styles)},
                         "effects": na.get("effects"), "expected_action": na.get("expected_action")})
        pr = decision_process(d)
        proc_rows.append(pr)
        ritmo = None
        if pr and nid in node_q:
            q1, q3 = node_q[nid]
            ritmo = "rápida" if pr["duracion_ms"] < q1 else ("deliberada" if pr["duracion_ms"] > q3 else "habitual")
        sp_ch = smap.style_means(Kst[i, ai[j]])
        decisions.append({
            "node_id": nid, "order": node["order"], "title": node["title"], "context": node["context"],
            "day": node["day"], "block": node["block"], "type": node["type"], "theme": node["theme"],
            "npcs": node["npcs"], "condition": node.get("condition"),
            "chosen": key.alt_ids[nid][ai[j]], "alternatives": alts,
            "z": {dd: r2(float(r["z"][j, jj])) for jj, dd in enumerate(dims)},
            "style_points": {st: r2(float(sp_ch[k]), 2) for k, st in enumerate(styles)},
            "estilo_dominante_aporte": styles[int(np.argmax(sp_ch))],
            "influencia_pp": r2(infl[j], 2),
            "process": pr, "ritmo": ritmo,
            "commitment": commit_by_node.get(nid),
            "links": {"strengths": [], "opportunities": []},
        })

    # --- fortalezas y oportunidades
    D = {dd: j for j, dd in enumerate(dims)}
    cands_s, cands_o = [], []
    for dd in dims:
        rel = dim_out[dd]["rel"]
        if rel is None:
            continue
        inv = dd in passive
        sscore = (1 - rel) if inv else rel
        if sscore >= ncfg["strength_min_relative_index"]:
            cands_s.append({"dim": dd, "score": sscore, "inverse": inv})
        oscore = rel if inv else (1 - rel)
        if (inv and rel >= 1 - ncfg["opportunity_max_relative_index"]) or (not inv and rel <= ncfg["opportunity_max_relative_index"]):
            cands_o.append({"dim": dd, "score": oscore, "inverse": inv})
    strengths = pick_items(cands_s, ncfg["max_strengths"], style_of)
    taken = {x["dim"] for x in strengths}
    opps = pick_items([x for x in cands_o if x["dim"] not in taken], ncfg["max_opportunities"], style_of, active_first=False)
    if not strengths:   # sin dimensiones sobre el umbral: mostrar la posición relativa más alta, marcada como bajo umbral
        best = sorted([dd for dd in dims if dd not in passive and dim_out[dd]["rel"] is not None], key=lambda dd: -dim_out[dd]["rel"])
        if best:
            strengths = [{"dim": best[0], "score": dim_out[best[0]]["rel"], "inverse": False, "bajo_umbral": True}]
            taken = {best[0]}
            opps = [o for o in opps if o["dim"] not in taken]
    if not opps:   # siempre ofrecer al menos un foco de conversación
        fallback = sorted([dd for dd in dims if dd not in taken and dd not in passive], key=lambda dd: dim_out[dd]["rel"])
        if fallback:
            opps = [{"dim": fallback[0], "score": 1 - dim_out[fallback[0]]["rel"], "inverse": False, "bajo_umbral": True}]

    def item(c, kind, k):
        dd = c["dim"]
        j = D[dd]
        inv = c["inverse"]
        sign = (-1 if inv else 1) * (1 if kind == "F" else -1)
        nodes_ev = []
        for jj, dec in enumerate(decisions):
            i = ni[jj]
            col = Kst[i, :, j]
            ch = Kst[i, ai[jj], j]
            if kind == "F":
                good = (col.min() == ch and col.max() > col.min()) if inv else (ch == col.max() and col.max() > col.min())
                if good:
                    nodes_ev.append((jj, float(abs(r["z"][jj, j])), None))
            else:
                if inv:
                    gap = ch - col.min()
                    best = int(np.argmin(col))
                else:
                    gap = col.max() - ch
                    best = int(np.argmax(col))
                if gap > 0:
                    nodes_ev.append((jj, float(gap), best))
        nodes_ev.sort(key=lambda x: -x[1])
        ev = []
        for jj, w, best in nodes_ev[:6]:
            dec = decisions[jj]
            i = ni[jj]
            e = {"node_id": dec["node_id"], "title": dec["title"], "day": dec["day"], "block": dec["block"],
                 "chosen": dec["chosen"], "chosen_text": dec["alternatives"][ai[jj]]["text"],
                 "points_chosen": r2(float(Kst[i, ai[jj], j]), 2),
                 "points_max": r2(float(Kst[i, :, j].max()), 2), "points_min": r2(float(Kst[i, :, j].min()), 2),
                 "z": r2(float(r["z"][jj, j])),
                 "dwell_elegida_ms": dec["process"]["dwell_elegida_ms"] if dec["process"] else None,
                 "alternations": dec["process"]["alternations"] if dec["process"] else None,
                 "ritmo": dec["ritmo"]}
            if kind == "O":
                e["gap_points"] = r2(w, 2)
                e["alt_mayor_aporte"] = key.alt_ids[dec["node_id"]][best]
                e["alt_mayor_aporte_text"] = dec["alternatives"][best]["text"]
            ev.append(e)
        dinfo = narr["dimensions"][dd]
        n_sup = len(nodes_ev)
        lvl = evidence_level(n_sup, dim_out[dd]["z_ci"], dim_out[dd]["z_mean"], sign, ncfg["evidence_levels"])
        iid = f"{kind}{k + 1}"
        for e in ev:
            for dec in decisions:
                if dec["node_id"] == e["node_id"]:
                    dec["links"]["strengths" if kind == "F" else "opportunities"].append(iid)
        themes = {}
        for e in ev:
            t = node_by_id[e["node_id"]]["theme"]
            themes[t] = themes.get(t, 0) + 1
        base = {"id": iid, "dim": dd, "dim_label": narr_label(dd, narr, smap), "style": style_of[dd], "inverse": inv,
                "rel": dim_out[dd]["rel"], "rel_ci": dim_out[dd]["rel_ci"], "z_mean": dim_out[dd]["z_mean"],
                "z_ci": dim_out[dd]["z_ci"], "percentil_cohorte": dim_out[dd]["percentil_cohorte"],
                "n_nodos_evidencia": n_sup, "n_decisiones": int(len(ni)), "evidencia": lvl,
                "temas": themes, "nodos": ev, "bajo_umbral": c.get("bajo_umbral", False)}
        if kind == "F":
            base |= {"title": dinfo["fortaleza"],
                     "conducta": dinfo.get("conducta_inversa") if inv else dinfo["conducta"]}
        else:
            base |= {"title": dinfo.get("oportunidad", dinfo["fortaleza"]),
                     "conducta": dinfo["conducta"], "pregunta": dinfo["pregunta"], "accion": dinfo["accion"]}
        return base

    strengths_out = [item(c, "F", k) for k, c in enumerate(strengths)]
    opps_out = [item(c, "O", k) for k, c in enumerate(opps)]

    # --- variación situacional (por tema y por día)
    def grouped(field):
        g = {}
        for jj, dec in enumerate(decisions):
            g.setdefault(dec[field], []).append(jj)
        res = {}
        for k_, idxs in g.items():
            sh = sc.shares_from_points(r["style_points"][idxs], min_total)
            res[k_] = {"n": len(idxs), "shares": {st: r2(float(sh[q]), 1) for q, st in enumerate(styles)}}
        return res

    proc = process_summary(proc_rows, None, rng, 1000)
    com = commitments_summary(s.get("commitments", []))
    top = sorted(range(len(decisions)), key=lambda q: -(decisions[q]["influencia_pp"] or 0))
    return {
        "method": key.method, "profile": profile, "dimensions": dim_out,
        "strengths": strengths_out, "opportunities": opps_out, "decisions": decisions,
        "decision_destacada": decisions[top[0]]["node_id"] if decisions else None,
        "por_tema": grouped("theme"), "por_dia": grouped("day"),
        "process": proc, "commitments": com, "commitments_detail": s.get("commitments", []),
        "faltantes": [], "nodos_excluidos": [],
    }


def narr_label(dd, narr, smap):
    return narr["dimensions"][dd].get("label") or dd


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return r2(float(o))
    if isinstance(o, np.integer):
        return int(o)
    return o


def status_block():
    return {
        "funcional": ["Registro de elecciones por nodo y alternativa", "Cálculo de % por estilo con la clave vigente",
                      "Trazabilidad decisión → dimensión MLQ → estilo", "Intervalos bootstrap y estabilidad del predominio",
                      "Datos de proceso (permanencia, alternancias, coincidencia)", "Coherencia declarado–ejecutado"],
        "juicio_experto": ["Interpretación del perfil: aplicable cuando se replique y verifique la regla vigente",
                           "Fortalezas y oportunidades derivadas de la clave", "Textos de pregunta y acción de desarrollo"],
        "proyectado": ["Clave de rank ordering", "Percentiles poblacionales (cohorte de referencia)",
                       "Métricas de autoconciencia (contraste con MLQ-5X)"],
    }


def assumptions_block(cfg):
    sc_cfg = cfg["scoring"]["expert_judgment"]
    return [
        {"id": "S1", "tema": "Clave", "texto": f"La clave vigente es la {sc_cfg['aggregation']} de las valoraciones 0–4 del panel, conservando ceros; empate modal → valor más cercano a la mediana y, si persiste, el menor."},
        {"id": "S2", "tema": "Clave", "texto": "Se excluyen jueces con desviación media absoluta respecto del consenso > {0} o correlación con el consenso < {1}.".format(sc_cfg["exclusion"]["max_mad_from_consensus"], sc_cfg["exclusion"]["min_corr_with_consensus"])},
        {"id": "S3", "tema": "Mapeo", "texto": "Estilos según el Modelo de Rango Completo: Transformacional (IIA, IIC, MI, EI, CI), Transaccional (RC, DPE-A), Pasivo/evitativo (DPE-P, LF)."},
        {"id": "S4", "tema": "Comparabilidad", "texto": "Para comparar estilos con distinto número de dimensiones se usa el promedio de puntos por dimensión; los pesos entre dimensiones son iguales."},
        {"id": "S5", "tema": "Porcentaje", "texto": "% del estilo = puntos del estilo / total × 100. Describe la distribución del puntaje del recorrido; no es percentil ni probabilidad."},
        {"id": "S6", "tema": "Predominio", "texto": "El predominio se calcula antes de redondear; con empate exacto se muestran los estilos empatados; con total cero se muestra «Sin puntaje disponible»."},
        {"id": "S7", "tema": "Independencia", "texto": "El bootstrap por decisiones trata los nodos encontrados como intercambiables; ignora la dependencia entre nodos de una misma secuencia, por lo que los IC pueden ser optimistas."},
        {"id": "S8", "tema": "Recorrido", "texto": "Nodos proactivos y contingentes cambian el conjunto de decisiones de cada persona; el índice relativo compara contra lo alcanzable en su propio recorrido."},
        {"id": "S9", "tema": "Proceso", "texto": "La permanencia del cursor se interpreta como consideración, no como preferencia; la coincidencia con la elegida es descriptiva."},
        {"id": "S10", "tema": "Datos", "texto": "En esta versión todos los datos son sintéticos (generados con semilla fija). Ninguna cifra describe a una persona real."},
    ]


def evidence_context():
    return {
        "_nota": "Resultados reportados con datos reales en los documentos de COMPASS. Se muestran como contexto, NO se recalculan aquí.",
        "items": [
            {"fuente": "Memoria de título (Lara, 2026)", "dato": "Acuerdo del panel ICC(2,k) = 0,746 con 8 jueces"},
            {"fuente": "Memoria de título (Lara, 2026)", "dato": "Alfa de las dimensiones COMPASS entre −0,223 y 0,420 (MLQ-5X: 0,437 a 0,831)"},
            {"fuente": "Memoria de título (Lara, 2026)", "dato": "Varianza atribuible al participante entre 0,12 % y 1,95 %; nodos y residuo concentran la variabilidad"},
            {"fuente": "Memoria de título (Lara, 2026)", "dato": "Sin evidencia de validez convergente con MLQ-5X (|r| < 0,25 en las 9 dimensiones)"},
            {"fuente": "Paper COMPASS", "dato": "Permanencia del cursor: mediana 5.414 ms (elegida) vs 3.114 ms (descartadas), r = 0,43; coincidencia 72,4 %"},
            {"fuente": "Paper COMPASS", "dato": "Usabilidad SUS = 78,1 (n = 60)"},
        ],
        "implicancia": "Con la fiabilidad observada en datos reales, el perfil debe leerse como descripción del recorrido en la simulación y punto de partida para una conversación de retroalimentación, no como medición del rasgo.",
    }
