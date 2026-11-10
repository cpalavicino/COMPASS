"""
Generador de datos SINTÉTICOS para la demo del dashboard de diagnóstico COMPASS.

Produce, en inputs/:
  module.json          estructura del módulo (nodos, alternativas, efectos, compromisos)
  experts_raw.json     panel experto sintético (10 jueces x 84 bloques x 9 dimensiones, escala 0-4)
  rank_key.json        clave sintética de rank ordering (orden de alternativas por nodo y dimensión)
  sessions/*.json      60 sesiones sintéticas con decisiones, datos de proceso y compromisos

Nada de esto proviene de participantes reales. Los textos de nodos/alternativas se toman de
synthetic/module_source.json (tabla derivada sin datos identificatorios); su campo lean_TrP
solo orienta la dirección general de la clave sintética para que el texto y el puntaje sean coherentes.

Uso:  python synthetic/generate_synthetic.py   (desde la raíz del repositorio)
"""
import json
import math
import os
import random
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261122
rng = np.random.default_rng(SEED)
random.seed(SEED)

DIMS = ["IIA", "IIC", "MI", "EI", "CI", "RC", "DPE-A", "DPE-P", "LF"]
DIM_STYLE = {"IIA": 0, "IIC": 0, "MI": 0, "EI": 0, "CI": 0, "RC": 1, "DPE-A": 1, "DPE-P": 2, "LF": 2}

# ----------------------------------------------------------------- anotaciones del módulo
DAYS = (["Lunes"] * 15) + (["Martes"] * 4) + (["Miércoles"] * 3) + (["Jueves"] * 3) + (["Viernes"] * 3)
BLOCKS = (["Mañana"] * 12 + ["Tarde"] * 3 + ["Mañana", "Mañana", "Tarde", "Tarde"]
          + ["Mañana", "Mañana", "Tarde"] + ["Mañana", "Tarde", "Tarde"] + ["Mañana", "Mañana", "Tarde"])
TYPES = {}
for n in [1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 18, 19, 20, 23, 26]:
    TYPES[n] = "obligatorio"
for n in [6, 7, 8, 10, 16, 17, 21, 22, 25, 27, 28]:
    TYPES[n] = "proactivo"
for n in [9, 24]:
    TYPES[n] = "contingente"
CONDITIONS = {
    9: {"node_id": "N07", "alt_in": ["A"], "descripcion": "Se activa si en N07 se respaldó la decisión clínica de la enfermera."},
    24: {"node_id": "N18", "alt_in": ["B", "C"], "descripcion": "Se activa si el doble agendamiento de boxes (N18) no se resolvió el mismo día."},
}
THEMES = {1: "vision", 2: "docencia", 3: "protocolos", 4: "protocolos", 5: "recursos", 6: "docencia",
          7: "protocolos", 8: "protocolos", 9: "protocolos", 10: "protocolos", 11: "crisis", 12: "vision",
          13: "vision", 14: "personas", 15: "personas", 16: "vision", 17: "docencia", 18: "recursos",
          19: "recursos", 20: "protocolos", 21: "docencia", 22: "docencia", 23: "personas", 24: "recursos",
          25: "personas", 26: "protocolos", 27: "protocolos", 28: "protocolos"}
NPCS = {1: ["Guzmán", "Soto", "Ríos"], 2: ["Guzmán"], 3: ["Ríos"], 4: ["Soto"], 5: ["Asistente"],
        6: ["Guzmán"], 7: ["Ríos"], 8: ["Ríos"], 9: ["Soto"], 10: ["Soto"], 11: ["Asistente", "Soto"],
        12: ["Soto"], 13: ["Guzmán", "Soto", "Ríos"], 14: ["Ríos"], 15: ["Ríos"], 16: ["Guzmán"],
        17: ["Guzmán"], 18: ["Asistente"], 19: ["Asistente"], 20: ["Ríos", "Soto"], 21: ["Guzmán"],
        22: ["Guzmán"], 23: ["TENS"], 24: ["Guzmán"], 25: ["Ríos"], 26: ["Asistente"], 27: ["Soto"], 28: ["Ríos"]}
NPC_INFO = {
    "Guzmán": {"rol": "Jefe del sector azul", "sector": "azul"},
    "Soto": {"rol": "Jefa del sector rojo", "sector": "rojo"},
    "Ríos": {"rol": "Jefe del sector amarillo", "sector": "amarillo"},
    "Asistente": {"rol": "Asistente administrativa", "sector": "dirección"},
    "TENS": {"rol": "Técnico en enfermería (TENS)", "sector": "amarillo"},
}
EXPECTED = {  # (nodo, alternativa) -> (mecánica, acción esperada)
    (7, "A"): ("Documentos", "Redactar un protocolo formal de derivación sin médico presente"),
    (9, "A"): ("Documentos", "Publicar el protocolo formal de actuación"),
    (11, "A"): ("Consultas", "Coordinar con el jefe del sector amarillo la absorción de pacientes"),
    (14, "A"): ("Agenda", "Reforzar la dotación del sector amarillo en la propuesta del viernes"),
    (14, "B"): ("Agenda", "Incluir al sector amarillo en la propuesta de horario del viernes"),
    (15, "A"): ("Agenda", "Revisar los turnos del sector amarillo para la próxima semana"),
    (17, "A"): ("Correo", "Responder a la coordinación de prácticas confirmando los cupos"),
    (17, "B"): ("Agenda", "Asignar boxes para la labor docente"),
    (18, "A"): ("Agenda", "Resolver hoy los dos conflictos de doble agendamiento"),
    (19, "A"): ("Mapa", "Convocar a los jefes de sector para revisar el uso del ecógrafo"),
    (21, "A"): ("Documentos", "Formalizar el registro de los internos de intercambio"),
    (22, "A"): ("Delegación", "Delegar al jefe del sector azul el proceso del convenio"),
    (22, "B"): ("Agenda", "Reservar el Box 1 para el sector azul"),
    (23, "A"): ("Agenda", "Reducir la carga horaria del TENS en la propuesta semanal"),
    (23, "B"): ("Agenda", "Ajustar la carga del TENS en la propuesta de hoy"),
    (24, "A"): ("Agenda", "Garantizar el Box 1 para el sector azul la próxima semana"),
    (24, "C"): ("Agenda", "Asignar el Box 1 al sector azul la próxima semana"),
    (26, "A"): ("Consultas", "Avisar directamente al jefe del sector amarillo para corregir el registro"),
    (27, "A"): ("Consultas", "Notificar a Guzmán para regularizar el reporte"),
    (27, "B"): ("Consultas", "Revisar el reporte con Guzmán el lunes"),
    (28, "C"): ("Delegación", "Entregar el borrador a Soto para revisión técnica"),
}


def lean_vec(lean):
    v = np.array(lean, dtype=float)
    return v / v.sum()


def build_module():
    src = json.loads((ROOT / "synthetic/module_source.json").read_text(encoding="utf-8"))
    nodes = []
    for i, n in enumerate(src["nodes"], start=1):
        alts = []
        for a in n["alternatives"]:
            lv = lean_vec(a["lean_TrP"])
            rep = int(round(8 * (lv[0] - lv[2])))
            trust = {}
            for npc in NPCS[i]:
                t = 10 * (lv[0] - lv[2]) + (3 if (npc == "Soto" and lv[1] > 0.36) else 0)
                trust[npc] = int(round(t + rng.normal(0, 1.5)))
            alt = {"alt_id": a["alt_id"], "text": a["text"],
                   "effects": {"reputacion": rep, "confianza": trust}}
            if (i, a["alt_id"]) in EXPECTED:
                mech, act = EXPECTED[(i, a["alt_id"])]
                alt["expected_action"] = {"mechanic": mech, "action": act}
            alts.append(alt)
        node = {"node_id": n["node_id"], "order": i, "title": n["title"], "context": n["context"],
                "day": DAYS[i - 1], "block": BLOCKS[i - 1], "type": TYPES[i], "theme": THEMES[i],
                "npcs": NPCS[i], "mechanic": "Oficina", "alternatives": alts}
        if i in CONDITIONS:
            node["condition"] = CONDITIONS[i]
        nodes.append(node)
    return {"module_id": "gestion_salud_cesfam", "module_version": "1.0-demo",
            "title": "Gestión en Salud (CESFAM)",
            "description": "Alinea a tres sectores en un centro de salud primaria de alta complejidad.",
            "role": "Director/a del CESFAM", "week": "Semana 1", "synthetic": True,
            "npcs": NPC_INFO, "nodes": nodes}, src


# ----------------------------------------------------------------- clave sintética
def latent_mu(src):
    """mu[nodo][alt][dim] en escala 0-4, coherente con la orientación del texto."""
    mu = {}
    for n in src["nodes"]:
        mu[n["node_id"]] = {}
        for a in n["alternatives"]:
            lv = np.array(a["lean_TrP"], dtype=float)
            row = {}
            for d in DIMS:
                base = lv[DIM_STYLE[d]]
                v = 0.2 + 1.15 * base + rng.normal(0, 0.45)
                row[d] = float(np.clip(v, 0, 4))
            mu[n["node_id"]][a["alt_id"]] = row
    return mu


def build_experts(mu):
    profiles = ["Psicología"] * 6 + ["Ing. Civil Industrial"] * 4
    experts = []
    ratings = []
    for e in range(10):
        eid = f"E{e + 1:02d}"
        experts.append({"expert_id": eid, "formacion": profiles[e]})
        bias = rng.normal(0, 0.25)
        scale = rng.uniform(0.85, 1.15)
        for nid, alts in mu.items():
            for aid, row in alts.items():
                for d, m in row.items():
                    if e == 9:   # juez con sesgo de respuesta (escala comprimida en el extremo alto)
                        v = int(rng.choice([2, 3, 3, 4, 4, 4]))
                    else:
                        v = int(np.clip(round(scale * m + bias + rng.normal(0, 1.0)), 0, 4))
                    ratings.append([eid, nid, aid, d, v])
    return {"_nota": "Panel experto SINTÉTICO. Formato largo: [expert_id, node_id, alt_id, dim, valor 0-4].",
            "scale": [0, 4], "experts": experts, "columns": ["expert_id", "node_id", "alt_id", "dim", "value"],
            "ratings": ratings}


def build_rank_key(mu):
    key = {}
    for nid, alts in mu.items():
        key[nid] = {}
        for d in DIMS:
            vals = {a: alts[a][d] + rng.normal(0, 0.3) for a in alts}
            order = sorted(vals, key=lambda a: -vals[a])
            groups = [[order[0]]]
            for a in order[1:]:
                if abs(vals[groups[-1][-1]] - vals[a]) < 0.15:
                    groups[-1].append(a)
                else:
                    groups.append([a])
            key[nid][d] = groups
    return {"_nota": "Clave SINTÉTICA de rank ordering: por nodo y dimensión, grupos de alternativas de mayor a menor correspondencia. Alternativas en un mismo grupo están empatadas.",
            "method": "rank_ordering", "k": 3, "key": key}


# ----------------------------------------------------------------- sesiones sintéticas
FOCAL = {
    "P-0142": {"theta": [0.78, 0.17, 0.05], "beta": 7.0, "engagement": 0.85, "follow": 0.8},
    "P-0087": {"theta": [0.22, 0.70, 0.08], "beta": 7.0, "engagement": 0.6, "follow": 0.75},
    "P-0203": {"theta": [0.45, 0.42, 0.13], "beta": 5.0, "engagement": 0.7, "follow": 0.6},
    "P-0311": {"theta": [0.25, 0.20, 0.55], "beta": 6.0, "engagement": 0.35, "follow": 0.35},
}


def simulate_session(module, src, code, prof, idx):
    lean = {n["node_id"]: {a["alt_id"]: lean_vec(a["lean_TrP"]) for a in n["alternatives"]} for n in src["nodes"]}
    theta = np.array(prof["theta"])
    chosen = {}
    decisions = []
    commitments = []
    t = 0
    rep = 50.0
    trust = {"Guzmán": 50.0, "Soto": 50.0, "Ríos": 50.0, "Asistente": 50.0, "TENS": 50.0}
    attr_timeline = [{"day": "Lunes", "block": "Inicio", "reputacion": rep}]
    last_key = None
    for node in module["nodes"]:
        nid = node["node_id"]
        if node["type"] == "proactivo" and rng.random() > prof["engagement"]:
            continue
        cond = node.get("condition")
        if cond and chosen.get(cond["node_id"]) not in cond["alt_in"]:
            continue
        util = {a: prof["beta"] * float(theta @ lean[nid][a]) + rng.gumbel(0, 1) for a in lean[nid]}
        pick = max(util, key=util.get)
        chosen[nid] = pick
        # datos de proceso
        dwell, cons = {}, {}
        for a in "ABC":
            base = rng.lognormal(math.log(3100), 0.55)
            dwell[a] = int(base * (1.75 if a == pick else 1.0))
            cons[a] = int(1 + rng.poisson(1.6 if a == pick else 1.0))
        alternations = int(max(0, sum(cons.values()) - 1 - rng.integers(0, 2)))
        order = sorted("ABC", key=lambda a: rng.random())
        duration = int(sum(dwell.values()) + rng.lognormal(math.log(6000), 0.4))
        t += duration + int(rng.integers(20000, 90000))
        decisions.append({"node_id": nid, "alt_id": pick, "day": node["day"], "block": node["block"],
                          "t_presented_ms": t - duration, "t_decided_ms": t,
                          "process": {"dwell_ms": dwell, "considerations": cons, "alternations": alternations,
                                      "first_considered": order[0], "last_considered": pick if rng.random() < 0.8 else order[-1]}})
        alt = next(a for a in node["alternatives"] if a["alt_id"] == pick)
        rep = float(np.clip(rep + alt["effects"]["reputacion"], 0, 100))
        for npc, dv in alt["effects"]["confianza"].items():
            trust[npc] = float(np.clip(trust[npc] + dv, 0, 100))
        key = (node["day"], node["block"])
        if key != last_key:
            attr_timeline.append({"day": node["day"], "block": node["block"], "reputacion": rep})
            last_key = key
        else:
            attr_timeline[-1]["reputacion"] = rep
        if "expected_action" in alt:
            p = prof["follow"]
            r = rng.random()
            res = "cumplido" if r < p else ("parcial" if r < p + (1 - p) * 0.45 else "no_cumplido")
            ev = {"cumplido": "Acción canónica registrada dentro de la ventana esperada",
                  "parcial": "Acción registrada fuera de plazo o incompleta",
                  "no_cumplido": "Sin acción canónica correspondiente en el registro"}[res]
            commitments.append({"commit_id": f"C-{nid}{pick}", "node_id": nid, "alt_id": pick,
                                "mechanic": alt["expected_action"]["mechanic"],
                                "expected_action": alt["expected_action"]["action"],
                                "result": res, "evidence": ev})
    return {"schema_version": "compass-session/0.1", "synthetic": True,
            "session_id": f"S-2026-{idx:04d}", "participant_code": code,
            "module_id": module["module_id"], "module_version": module["module_version"],
            "started_at": "2026-11-05T10:00:00-03:00", "duration_ms": t,
            "decisions": decisions, "commitments": commitments,
            "global_attributes": attr_timeline,
            "npc_final": {k: {"confianza": round(v, 1)} for k, v in trust.items()}}


def main():
    module, src = build_module()
    mu = latent_mu(src)
    out = ROOT / "inputs"
    (out / "sessions").mkdir(parents=True, exist_ok=True)
    for f in (out / "sessions").glob("*.json"):
        f.unlink()
    (out / "module.json").write_text(json.dumps(module, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "experts_raw.json").write_text(json.dumps(build_experts(mu), ensure_ascii=False), encoding="utf-8")
    (out / "rank_key.json").write_text(json.dumps(build_rank_key(mu), ensure_ascii=False, indent=1), encoding="utf-8")
    codes = list(FOCAL)
    while len(codes) < 60:
        c = f"P-{int(rng.integers(1000, 9999)):04d}"
        if c not in codes:
            codes.append(c)
    for i, code in enumerate(codes, start=1):
        prof = FOCAL.get(code) or {"theta": list(rng.dirichlet([2.2, 1.6, 0.9])), "beta": float(rng.uniform(3, 7)),
                                    "engagement": float(rng.uniform(0.3, 0.95)), "follow": float(rng.uniform(0.35, 0.85))}
        s = simulate_session(module, src, code, prof, i)
        (out / "sessions" / f"{code}.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: módulo con {len(module['nodes'])} nodos, 10 jueces, {len(codes)} sesiones sintéticas en {out}")


if __name__ == "__main__":
    main()
