"""
Informe técnico PDF por sesión y método, generado desde el contrato data/diagnosticos.json
(los mismos números que muestra el dashboard). Requiere reportlab y matplotlib.
"""
import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,  # noqa: E402
                                Spacer, Table, TableStyle)

NAVY = colors.HexColor("#0f2436")
INK = colors.HexColor("#1b2a38")
MUTED = colors.HexColor("#5d6f7f")
LINE = colors.HexColor("#d5dee6")
SOFT = colors.HexColor("#f2f5f8")


def _fmt(v, nd=1, pct=False):
    if v is None:
        return "—"
    s = f"{v:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s + (" %" if pct else "")


def _ci(c, nd=1):
    if not c or c[0] is None:
        return "—"
    return f"[{_fmt(c[0], nd)} ; {_fmt(c[1], nd)}]"


def _styles():
    ss = getSampleStyleSheet()
    base = ParagraphStyle("b", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.4, leading=13, textColor=INK, alignment=TA_LEFT)
    return {
        "body": base,
        "small": ParagraphStyle("s", parent=base, fontSize=8, leading=10.5, textColor=MUTED),
        "h1": ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=NAVY, spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=NAVY, spaceBefore=12, spaceAfter=6),
        "h3": ParagraphStyle("h3", parent=base, fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=NAVY, spaceBefore=6, spaceAfter=3),
        "cell": ParagraphStyle("c", parent=base, fontSize=8.2, leading=10.4),
        "warn": ParagraphStyle("w", parent=base, backColor=colors.HexColor("#fff6dc"), borderColor=colors.HexColor("#e0b341"),
                               borderWidth=0.6, borderPadding=6, spaceBefore=4, spaceAfter=8),
    }


def _table(rows, widths, st, header=True):
    data = [[Paragraph(str(c), st["cell"]) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    sty = [("GRID", (0, 0), (-1, -1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        sty += [("BACKGROUND", (0, 0), (-1, 0), SOFT), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(sty))
    return t


def _fig(fig, w_cm):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    img = Image(buf)
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth = w_cm * cm
    img.drawHeight = w_cm * cm * ratio
    return img


def chart_styles(p, styles_meta):
    fig, ax = plt.subplots(figsize=(7, 2.2))
    keys = list(styles_meta)
    ci = p.get("shares_ci_combinado") or p["shares_ci_nodos"]
    for i, k in enumerate(keys):
        y = len(keys) - 1 - i
        ax.barh(y, p["shares"][k], color=styles_meta[k]["color"], height=0.5)
        lo, hi = ci[k]
        ax.plot([lo, hi], [y, y], color="#1b2a38", lw=1.6)
        ax.plot([lo, lo], [y - .15, y + .15], color="#1b2a38", lw=1.6)
        ax.plot([hi, hi], [y - .15, y + .15], color="#1b2a38", lw=1.6)
        ax.text(101, y, f"{_fmt(p['shares'][k])} %  IC95 {_ci(ci[k])}", va="center", fontsize=8.5)
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels([styles_meta[k]["label"] for k in reversed(keys)], fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% de los puntos del recorrido", fontsize=8.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", alpha=.25)
    return fig


def chart_dims(m, data):
    dims = list(data["dimensions"])
    fig, ax = plt.subplots(figsize=(7, 3.4))
    for i, d in enumerate(dims):
        y = len(dims) - 1 - i
        c = data["styles"][data["dimensions"][d]["style"]]["color"]
        z = m["dimensions"][d]["z_mean"]
        lo, hi = m["dimensions"][d]["z_ci"]
        ax.plot([lo, hi], [y, y], color=c, lw=4, alpha=.45, solid_capstyle="round")
        ax.plot(z, y, "o", color=c, ms=8, mec="white", mew=1.5)
    ax.axvline(0, color="#1b2a38", lw=1)
    ax.set_yticks(range(len(dims)))
    ax.set_yticklabels([f"{d} · {data['dimensions'][d]['label']}" for d in reversed(dims)], fontsize=8)
    ax.set_xlabel("z prom. intra-nodo (0 = alternativa promedio del nodo) · IC95 bootstrap", fontsize=8.5)
    ax.grid(axis="x", alpha=.25)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return fig


def chart_boot(p, styles_meta):
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 1.9), sharey=True)
    for ax, k in zip(axes, styles_meta):
        h = p["bootstrap_hist"][k]
        ax.bar([i * 100 / len(h) + 100 / len(h) / 2 for i in range(len(h))], h, width=100 / len(h) * .9, color=styles_meta[k]["color"])
        ax.axvline(p["shares"][k], color="#1b2a38", lw=1.4)
        ax.set_title(f"{styles_meta[k]['label']} · predom. {round(p['estabilidad_predominio'][k] * 100)} %", fontsize=8.5)
        ax.set_xlim(0, 100)
        ax.tick_params(labelsize=7)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("réplicas", fontsize=8)
    return fig


def chart_contrib(m, styles_meta):
    decs = m["decisions"]
    fig, ax = plt.subplots(figsize=(7.2, max(2.5, len(decs) * 0.2)))
    keys = list(styles_meta)
    for i, d in enumerate(decs):
        y = len(decs) - 1 - i
        x = 0
        for k in keys:
            v = d["style_points"][k]
            ax.barh(y, v, left=x, color=styles_meta[k]["color"], height=.7, edgecolor="white", linewidth=.8)
            x += v
    ax.set_yticks(range(len(decs)))
    ax.set_yticklabels([f"{d['node_id']} {d['title'][:34]}" for d in reversed(decs)], fontsize=6.6)
    ax.set_xlabel("puntos por decisión (promedio por dimensión de cada estilo)", fontsize=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return fig


def build_report(path: Path, data, code, method):
    st = _styles()
    sess = data["sessions"][code]
    m = sess["by_method"][method]
    q = data["methods"][method]
    styles_meta = data["styles"]
    keys = list(styles_meta)
    lab = {k: styles_meta[k]["label"] for k in keys}
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                            title=f"Informe técnico COMPASS · {code}", author="COMPASS · Equipo de Investigación")
    W = A4[0] - 3.6 * cm
    E = []

    def footer(c, d):
        c.saveState()
        c.setFont("Helvetica", 7.5)
        c.setFillColor(MUTED)
        c.drawString(1.8 * cm, 1 * cm, f"COMPASS · Informe técnico · {code} · {q['label']} · {'DATOS SINTÉTICOS' if data['synthetic'] else ''}")
        c.drawRightString(A4[0] - 1.8 * cm, 1 * cm, f"pág. {d.page}")
        c.restoreState()

    meth_label = "Juicio experto (moda del panel)" if method == "expert_judgment" else "Rank ordering (proyectado)"
    E.append(Paragraph("COMPASS · Informe técnico de diagnóstico de liderazgo", st["h1"]))
    E.append(Paragraph(f"Módulo <b>{data['module']['title']}</b> · Participante <b>{code}</b> · Sesión {sess['session_id']} · Clave: <b>{meth_label}</b>", st["body"]))
    E.append(Paragraph(f"Contrato {data['schema_version']} · configuración {data['config_version']} · generado {data['generated_at']}", st["small"]))
    if data["synthetic"]:
        E.append(Paragraph("<b>Vista previa con datos sintéticos.</b> Todas las cifras provienen de un generador con semilla fija; no describen a ninguna persona. "
                           "El documento valida el cálculo, la trazabilidad y el formato del informe que se emitirá con datos reales.", st["warn"]))
    if m.get("sin_puntaje"):
        E.append(Paragraph(f"Sin puntaje disponible: {m.get('motivo')}", st["body"]))
        doc.build(E, onFirstPage=footer, onLaterPages=footer)
        return

    p = m["profile"]
    pred = p["predominant"]
    # 1. resumen
    E.append(Paragraph("1. Resumen", st["h2"]))
    E.append(Paragraph(
        f"Perfil predominante en esta simulación: <b>{' = '.join(lab[x] for x in pred)}</b> con {_fmt(p['shares'][pred[0]])} % de los puntos "
        f"({_fmt(p['points'][pred[0]])} de {_fmt(p['total_points'])}). El estilo se mantiene predominante en "
        f"{round(p['estabilidad_predominio'][pred[0]] * 100)} % de las réplicas bootstrap (estabilidad <b>{p['estabilidad_etiqueta']}</b>). "
        f"Se puntuaron {p['n_decisiones']} decisiones de {data['module']['n_nodes']} nodos del módulo.", st["body"]))
    E.append(_fig(chart_styles(p, styles_meta), 16.5))
    E.append(Paragraph("El porcentaje describe la distribución del puntaje del recorrido; no es percentil ni probabilidad. Bigotes: IC95 "
                       + ("combinado (jueces × decisiones)." if p.get("shares_ci_combinado") else "por remuestreo de decisiones."), st["small"]))
    rows = [["Fortalezas observadas", "Dimensión", "Evidencia", "Índice relativo", "Decisiones"]]
    for f in m["strengths"]:
        rows.append([f["title"], f["dim"], f["evidencia"], f"{round(f['rel'] * 100)} % {_ci([v * 100 for v in f['rel_ci']], 0)}", f"{f['n_nodos_evidencia']}/{f['n_decisiones']}"])
    E.append(_table(rows, [7 * cm, 2 * cm, 2.2 * cm, 3.2 * cm, 2 * cm], st))
    E.append(Spacer(1, 6))
    rows = [["Oportunidades de mejora", "Dimensión", "Evidencia", "Pregunta para explorar"]]
    for o in m["opportunities"]:
        rows.append([o["title"], o["dim"], o["evidencia"], o["pregunta"]])
    E.append(_table(rows, [5 * cm, 2 * cm, 2 * cm, 7.4 * cm], st))

    # 2. datos
    E.append(Paragraph("2. Datos y procedencia", st["h2"]))
    E.append(_table([
        ["Elemento", "Valor"],
        ["Fuente de decisiones", "Sesión JSON del simulador (schema compass-session/0.1): nodo, alternativa, tiempos y datos de proceso"],
        ["Clave de puntuación", f"{q['label']} · estado {q['estado']}"],
        ["Cohorte de referencia", f"{q['cohort']['n']} sesiones {'sintéticas' if data['synthetic'] else ''}"],
        ["Nodos del módulo", f"{data['module']['n_nodes']} ({', '.join(f'{v} {k}s' for k, v in data['module']['nodes_by_type'].items())})"],
        ["Datos faltantes", "Decisiones con nodo/alternativa ausente en la clave se excluyen y se reportan; juicios faltantes se imputan con la mediana del panel"],
    ], [4.5 * cm, 12 * cm], st))

    # 3. método
    E.append(Paragraph("3. Método de puntuación", st["h2"]))
    if method == "expert_judgment":
        kq = q["key_quality"]
        E.append(Paragraph(
            f"Cada alternativa fue valorada por {kq['n_jueces_total']} jueces en una escala 0–4 para las nueve dimensiones MLQ-5X. Tras aplicar los criterios de exclusión "
            f"quedaron {kq['n_jueces_incluidos']}. La clave es la <b>{kq['agregacion']}</b> por alternativa y dimensión, conservando los ceros; en empate modal se toma el valor más cercano a la mediana "
            f"y, si persiste, el menor.", st["body"]))
    else:
        E.append(Paragraph("La clave de rank ordering ordena las alternativas de cada nodo por su correspondencia con cada dimensión. Los puntos son k − rango (k = 3), con rango medio en empates. "
                           "Este método está proyectado: la clave de esta demo es sintética.", st["body"]))
    E.append(Paragraph("Fórmulas", st["h3"]))
    for f in ["Puntos del estilo s en la decisión n: P(s,n) = promedio de w(a_elegida, d, n) para d en s",
              "% estilo s = Σ_n P(s,n) / Σ_s Σ_n P(s,n) × 100   (predominio calculado antes de redondear)",
              "Estandarización intra-nodo: z(d,n) = (w_elegida − media_alternativas) / desv_alternativas; z = 0 si desv = 0",
              "Índice relativo de d = (Σ w_elegida − Σ mín) / (Σ máx − Σ mín) sobre los nodos encontrados",
              "IC95: percentiles 2,5 y 97,5 de 2.000 réplicas bootstrap de decisiones; combinado: 1.000 réplicas remuestreando jueces y decisiones"]:
        E.append(Paragraph("• " + f, st["body"]))
    E.append(Paragraph("Mapeo: Transformacional = IIA, IIC, MI, EI, CI · Transaccional = RC, DPE-A · Pasivo/evitativo = DPE-P, LF. Pesos iguales entre dimensiones.", st["small"]))

    # 4. resultados
    E.append(PageBreak())
    E.append(Paragraph("4. Resultados por estilo y dimensión", st["h2"]))
    rows = [["Estilo", "%", "Puntos", "IC95 decisiones", "IC95 clave", "IC95 combinado", "Índ. relativo", "Predominio"]]
    for k in keys:
        rows.append([lab[k], _fmt(p["shares"][k]), _fmt(p["points"][k]), _ci(p["shares_ci_nodos"][k]),
                     _ci(p["shares_ci_clave"][k]) if p.get("shares_ci_clave") else "n/d",
                     _ci(p["shares_ci_combinado"][k]) if p.get("shares_ci_combinado") else "n/d",
                     f"{round(p['rel_style'][k] * 100)} %", f"{round(p['estabilidad_predominio'][k] * 100)} %"])
    E.append(_table(rows, [3.2 * cm, 1.4 * cm, 1.5 * cm, 2.4 * cm, 2.2 * cm, 2.4 * cm, 1.8 * cm, 1.7 * cm], st))
    E.append(Spacer(1, 6))
    E.append(_fig(chart_dims(m, data), 16.5))
    rows = [["Dim.", "Nombre", "z prom.", "IC95 z prom.", "Índ. rel.", "IC95 índ.", "Puntos", "Percentil cohorte*"]]
    for d, info in data["dimensions"].items():
        x = m["dimensions"][d]
        rows.append([d, info["label"], _fmt(x["z_mean"], 2), _ci(x["z_ci"], 2), f"{round(x['rel'] * 100)} %",
                     _ci([v * 100 for v in x["rel_ci"]], 0), _fmt(x["points"]), f"P{round(x['percentil_cohorte'])}"])
    E.append(_table(rows, [1.3 * cm, 5 * cm, 1.3 * cm, 2.5 * cm, 1.5 * cm, 2 * cm, 1.4 * cm, 1.6 * cm], st))
    E.append(Paragraph("* Percentiles proyectados: calculados contra la cohorte de referencia disponible, no contra una población normativa.", st["small"]))

    # 5. incertidumbre
    E.append(Paragraph("5. Incertidumbre y estabilidad", st["h2"]))
    E.append(_fig(chart_boot(p, styles_meta), 16.5))
    E.append(Paragraph("Distribución del % de cada estilo en 2.000 réplicas bootstrap de las decisiones (línea = valor observado). "
                       "Etiquetas: estable ≥ 80 % de réplicas con el mismo predominante; moderada 60–80 %; inestable < 60 %.", st["small"]))

    # 6. calidad de la clave
    E.append(Paragraph("6. Calidad de la clave", st["h2"]))
    kq = q["key_quality"]
    if method == "expert_judgment":
        E.append(Paragraph(f"ICC(2,1) = {_fmt(kq['icc_global']['icc21'], 3)} (juez individual) · ICC(2,k) = {_fmt(kq['icc_global']['icc2k'], 3)} (panel) · "
                           f"acuerdo exacto con la mediana {round(kq['acuerdo_exacto_con_mediana'] * 100)} % · dentro de ±1 punto {round(kq['acuerdo_dentro_de_1'] * 100)} %.", st["body"]))
        rows = [["Juez", "Formación", "Media", "DMA consenso", "r consenso", "Estado"]]
        for j in kq["jueces"]:
            rows.append([j["expert_id"], j["formacion"], _fmt(j["media"], 2), _fmt(j["mad_consenso"], 2), _fmt(j["r_consenso"], 2),
                         ("Excluido: " + ", ".join(j["flags"]).replace("_", " ")) if j["excluido"] else "Incluido"])
        E.append(_table(rows, [1.4 * cm, 3.4 * cm, 1.5 * cm, 2.4 * cm, 2 * cm, 5.8 * cm], st))
        rows = [["Dim."] + list(data["dimensions"]), ["ICC(2,k)"] + [_fmt(kq["icc_por_dimension"][d]["icc2k"], 2) for d in data["dimensions"]]]
        E.append(Spacer(1, 4))
        E.append(_table(rows, [2 * cm] + [1.6 * cm] * 9, st))
    else:
        E.append(Paragraph(f"{kq['n_celdas']} celdas nodo × dimensión; {kq['celdas_con_empate']} con empates; {len(kq['celdas_sin_clave'])} sin clave. {kq['nota']}", st["body"]))
    coh = q["cohort"]
    E.append(Paragraph(f"Informatividad: {coh['celdas_sin_contraste']} celdas sin contraste en la clave (C = 0) y {coh['celdas_contraste_sin_discriminacion']} con contraste pero sin "
                       f"discriminación observada en la cohorte, de {len(coh['informatividad']) * 9}.", st["body"]))
    rows = [["Fiabilidad por mitades"] + list(data["dimensions"]),
            ["Spearman-Brown"] + [_fmt(coh["fiabilidad_mitades"][d]["spearman_brown"], 2) for d in data["dimensions"]]]
    E.append(_table(rows, [3.2 * cm] + [1.47 * cm] * 9, st))
    E.append(Paragraph("Fiabilidad calculada sobre la cohorte disponible (sintética en esta versión): solo verifica el procedimiento.", st["small"]))

    # 7. proceso
    E.append(Paragraph("7. Datos de proceso y coherencia declarado–ejecutado", st["h2"]))
    pr = m["process"]
    com = m["commitments"]
    E.append(_table([
        ["Indicador", "Valor", "Intervalo / nota"],
        ["Permanencia mediana elegida vs descartadas", f"{_fmt(pr['dwell_elegida_mediana_ms'] / 1000)} s vs {_fmt(pr['dwell_descartadas_mediana_ms'] / 1000)} s",
         f"diferencia {_fmt(pr['diferencia_mediana_ms'] / 1000)} s IC95 {_ci([v / 1000 for v in pr['diferencia_ic95']])} · r = {_fmt(pr['wilcoxon_r'], 2)}"],
        ["Alternativa más considerada = elegida", f"{round(pr['coincidencia'][0] * 100)} % ({pr['coincidencia_n']}/{pr['n']})",
         f"IC95 Wilson [{round(pr['coincidencia'][1] * 100)} ; {round(pr['coincidencia'][2] * 100)}] %"],
        ["Alternancias medias por nodo", _fmt(pr["alternancias_media"]), "—"],
        ["Duración mediana por nodo", f"{_fmt(pr['duracion_mediana_ms'] / 1000)} s", "—"],
        ["Compromisos cumplidos", f"{com.get('cumplidos', 0)}/{com.get('n', 0)}",
         f"IC95 Wilson [{round(com['proporcion_cumplidos'][1] * 100)} ; {round(com['proporcion_cumplidos'][2] * 100)}] % · índice ponderado {_fmt(com['indice_ponderado'], 2)}" if com.get("n") else "—"],
    ], [5.6 * cm, 4 * cm, 6.9 * cm], st))
    if m["commitments_detail"]:
        rows = [["Nodo", "Acción esperada", "Mecánica", "Resultado"]]
        for c in m["commitments_detail"]:
            rows.append([c["node_id"], c["expected_action"], c["mechanic"], c["result"].replace("_", " ")])
        E.append(Spacer(1, 4))
        E.append(_table(rows, [1.5 * cm, 9.5 * cm, 2.5 * cm, 3 * cm], st))

    # 8. trazabilidad de fortalezas y oportunidades
    E.append(PageBreak())
    E.append(Paragraph("8. Trazabilidad de fortalezas y oportunidades", st["h2"]))
    for kind, items in (("Fortaleza", m["strengths"]), ("Oportunidad", m["opportunities"])):
        for it in items:
            block = [Paragraph(f"{kind} {it['id']} · {it['title']} ({it['dim']} · evidencia {it['evidencia']}{' · bajo umbral' if it.get('bajo_umbral') else ''})", st["h3"]),
                     Paragraph(f"Conducta: {it['conducta']}. Índice relativo {round(it['rel'] * 100)} %; z prom. {_fmt(it['z_mean'], 2)} IC95 {_ci(it['z_ci'], 2)}; "
                               f"{it['n_nodos_evidencia']} de {it['n_decisiones']} decisiones.", st["body"])]
            if kind == "Oportunidad":
                block.append(Paragraph(f"<b>Pregunta:</b> {it['pregunta']} <b>Acción:</b> {it['accion']}", st["body"]))
            rows = [["Nodo", "Alternativa elegida", "Pts elegida (rango)", "Detalle"]]
            for e in it["nodos"]:
                det = f"z {_fmt(e['z'], 2)}" if kind == "Fortaleza" else f"brecha {_fmt(e['gap_points'])} · alt. {e['alt_mayor_aporte']}"
                rows.append([e["node_id"], e["chosen_text"], f"{_fmt(e['points_chosen'])} ({_fmt(e['points_min'])}–{_fmt(e['points_max'])})", det])
            block.append(_table(rows, [1.4 * cm, 10 * cm, 2.6 * cm, 2.5 * cm], st))
            E.append(KeepTogether(block))
            E.append(Spacer(1, 6))

    # 9. sensibilidad
    sens = sess.get("sensibilidad_metodo")
    if sens:
        E.append(Paragraph("9. Sensibilidad a la clave", st["h2"]))
        E.append(Paragraph(f"Comparación {sens['metodos'][0]} vs {sens['metodos'][1]}: mismo predominante = {'sí' if sens['mismo_predominante'] else 'no'}; "
                           f"Spearman entre las 9 dimensiones = {_fmt(sens['spearman_dimensiones'], 2)}; diferencias en pp: "
                           + ", ".join(f"{lab[k]} {_fmt(v)}" for k, v in sens["diferencia_pp"].items()) + ".", st["body"]))

    # 10. supuestos
    E.append(Paragraph("10. Supuestos, reglas y limitaciones", st["h2"]))
    E.append(_table([["ID", "Tema", "Supuesto / regla"]] + [[a["id"], a["tema"], a["texto"]] for a in data["assumptions"]], [1.2 * cm, 2.6 * cm, 12.7 * cm], st))
    E.append(Paragraph("Contexto de evidencia con datos reales (reportado, no recalculado)", st["h3"]))
    E.append(_table([["Fuente", "Resultado"]] + [[x["fuente"], x["dato"]] for x in data["evidence_context"]["items"]], [4.5 * cm, 12 * cm], st))
    E.append(Paragraph(data["evidence_context"]["implicancia"], st["warn"]))
    E.append(Paragraph("Estado de los componentes", st["h3"]))
    E.append(_table([["Funcional", "Basado en juicio experto", "Proyectado"],
                     ["<br/>".join(data["status"]["funcional"]), "<br/>".join(data["status"]["juicio_experto"]), "<br/>".join(data["status"]["proyectado"])]],
                    [5.5 * cm] * 3, st))

    # anexo
    E.append(PageBreak())
    E.append(Paragraph("Anexo A. Traza de decisiones", st["h2"]))
    E.append(_fig(chart_contrib(m, styles_meta), 16.5))
    rows = [["Nodo", "Día · bloque", "Tipo", "Alt.", "T", "Tr", "P", "Δ pp*", "Permanencia", "Ritmo"]]
    for d in m["decisions"]:
        pr_ = d.get("process") or {}
        rows.append([f"{d['node_id']} {d['title']}", f"{d['day']} · {d['block']}", d["type"], d["chosen"],
                     _fmt(d["style_points"]["transformacional"], 2), _fmt(d["style_points"]["transaccional"], 2), _fmt(d["style_points"]["pasivo"], 2),
                     _fmt(d["influencia_pp"], 2), f"{_fmt((pr_.get('dwell_elegida_ms') or 0) / 1000)} s", d.get("ritmo") or "—"])
    E.append(_table(rows, [4.6 * cm, 2.4 * cm, 1.9 * cm, 0.9 * cm, 1 * cm, 1 * cm, 1 * cm, 1.2 * cm, 1.6 * cm, 1.4 * cm], st))
    E.append(Paragraph(f"* Variación del % {lab[pred[0]]} si se eliminara la decisión (leave-one-out).", st["small"]))
    doc.build(E, onFirstPage=footer, onLaterPages=footer)


def build_reports(root: Path, data, cfg):
    out = root / cfg["export"]["reports_dir"]
    out.mkdir(exist_ok=True)
    files = []
    for code, sess in data["sessions"].items():
        for method in sess["by_method"]:
            f = out / f"informe_tecnico_{code}_{method}.pdf"
            build_report(f, data, code, method)
            files.append(f)
    return files
