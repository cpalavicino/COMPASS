/* COMPASS · Dashboard de diagnóstico (vanilla JS, sin compilación).
   Toda la información proviene de window.COMPASS_DATA (data/diagnosticos.js), generado por el pipeline.
   La interfaz no calcula puntajes: solo presenta el contrato de datos (docs/contrato_datos.md). */
(function () {
  const D = window.COMPASS_DATA;
  const { esc, f1, f2 } = window.C;
  const $ = s => document.querySelector(s);
  const view = $("#view"), drawer = $("#drawer"), scrim = $("#scrim"), tip = $("#tip");
  if (!D) { view.innerHTML = `<div class="panel empty">No se encontró <code>data/diagnosticos.js</code>. Ejecute <code>python pipeline/run_pipeline.py</code>.</div>`; return; }

  const STY = Object.keys(D.styles);
  const DIMS = Object.keys(D.dimensions);
  const SCL = { transformacional: "t", transaccional: "tr", pasivo: "p" };
  const col = s => D.styles[s].color;
  const lab = s => D.styles[s].label;
  const pct = v => v == null ? "—" : `${f1(v)} %`;
  const ci = c => (c && c[0] != null) ? `[${f1(c[0])} – ${f1(c[1])}]` : "—";
  const ci2 = c => (c && c[0] != null) ? `[${f2(c[0])} ; ${f2(c[1])}]` : "—";
  const themeLabel = t => D.themes[t] || t;
  const ms = v => v == null ? "—" : `${(v / 1000).toLocaleString("es-CL", { maximumFractionDigits: 1 })} s`;
  const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) { } } };

  const codes = Object.keys(D.sessions);
  const state = {
    code: codes.includes(store.get("compass.code")) ? store.get("compass.code") : codes[0],
    method: D.methods_available.includes(store.get("compass.method")) ? store.get("compass.method") : D.default_method,
    filters: { theme: "", type: "", style: "", commit: "" },
  };
  const S = () => D.sessions[state.code];
  const M = () => S().by_method[state.method];
  const MQ = () => D.methods[state.method];

  // ------------------------------------------------------------------ íconos
  const I = {
    target: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/></svg>',
    bars: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M5 20V11M12 20V5M19 20v-6"/></svg>',
    star: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/></svg>',
    aim: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="13" r="8"/><circle cx="11" cy="13" r="4"/><path d="M11 13l8-8M16 5h3v3"/></svg>',
    layers: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/></svg>',
    shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/></svg>',
    doc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h7M9 17h7"/></svg>',
    grid: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="7" height="7" rx="2"/><rect x="13" y="4" width="7" height="7" rx="2"/><rect x="4" y="13" width="7" height="7" rx="2"/><rect x="13" y="13" width="7" height="7" rx="2"/></svg>',
    leader: '<svg viewBox="0 0 48 48" fill="#cfc6ff"><circle cx="24" cy="21" r="6"/><path d="M13 39c0-6 5-10 11-10s11 4 11 10z"/><circle cx="11" cy="25" r="4" opacity=".7"/><circle cx="37" cy="25" r="4" opacity=".7"/><path d="M4 39c0-4 3-7 7-7 2 0 3 .5 4 1.2-1.6 1.6-2.4 3.6-2.6 5.8zM44 39c0-4-3-7-7-7-2 0-3 .5-4 1.2 1.6 1.6 2.4 3.6 2.6 5.8z" opacity=".7"/><path d="M24 4v6M15 7l2.5 5M33 7l-2.5 5" stroke="#cfc6ff" stroke-width="2.4" stroke-linecap="round"/></svg>',
    check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
    ext: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M14 4h6v6M20 4l-9 9M18 14v5H5V6h5"/></svg>',
    arrow: '→',
  };
  const NAV = [
    ["resumen", "Resumen", I.target], ["perfil", "Perfil por estilo", I.bars], ["fortalezas", "Fortalezas observadas", I.star],
    ["oportunidades", "Oportunidades de mejora", I.aim], ["decisiones", "Decisiones en contexto", I.layers],
    ["validez", "Validez y confianza", I.shield], ["informe", "Informe técnico", I.doc], ["modulos", "Módulos", I.grid],
  ];

  // ------------------------------------------------------------------ router
  function parse() {
    const h = location.hash.replace(/^#\/?/, "");
    const [path, q] = h.split("?");
    const parts = (path || "resumen").split("/").filter(Boolean);
    const params = new URLSearchParams(q || "");
    return { view: parts[0] || "resumen", id: parts[1] || null, n: params.get("n") };
  }
  const base = () => { const r = parse(); return `#/${r.view}${r.id ? "/" + r.id : ""}`; };
  const nodeHref = nid => `${base()}?n=${nid}`;

  function render() {
    const r = parse();
    renderTop();
    renderRail(r.view);
    const m = M();
    const V = { resumen: vResumen, perfil: vPerfil, fortalezas: vFortalezas, oportunidades: vOportunidades, decisiones: vDecisiones, validez: vValidez, informe: vInforme, modulos: vModulos }[r.view] || vResumen;
    view.innerHTML = (m && m.sin_puntaje && !["modulos", "informe", "validez"].includes(r.view)) ? vSinPuntaje(m) : V(r);
    bindView();
    if (r.n) openDrawer(r.n); else closeDrawer(true);
    document.querySelectorAll(".step").forEach(b => b.classList.toggle("on", (b.dataset.go === "#/modulos" && r.view === "modulos") || (b.dataset.go === "#/decisiones" && false) || (b.dataset.go === "#/resumen" && r.view !== "modulos")));
  }

  // ------------------------------------------------------------------ barra superior
  function renderTop() {
    const sel = $("#sessionSel");
    if (!sel.options.length) {
      sel.innerHTML = codes.map(c => {
        const m = D.sessions[c].by_method[D.default_method];
        const p = m && m.profile ? m.profile.predominant.map(lab).join(" = ") : "sin puntaje";
        return `<option value="${c}">${c} · ${p}</option>`;
      }).join("");
      sel.addEventListener("change", e => { state.code = e.target.value; store.set("compass.code", state.code); render(); });
    }
    sel.value = state.code;
    const s = S(), ga = s.global_attributes || [], rep = ga.length ? ga[ga.length - 1].reputacion : null;
    $("#repPill").innerHTML = `<div class="ring"><i></i></div><div><div class="k">Reputación final</div><div class="meter"><b style="width:${rep ?? 0}%"></b></div><div class="v" style="font-size:12px">${rep == null ? "—" : Math.round(rep) + " %"}</div></div>`;
    const last = ga.length ? ga[ga.length - 1] : {};
    $("#weekPill").innerHTML = `<span class="k">${esc(D.module.week || "Semana 1")} · ${esc(last.day || "")} ${esc(last.block || "")}</span><span class="v">${s.n_decisiones} decisiones · ${Math.round((s.duration_ms || 0) / 60000)} min</span>`;
    $("#moduleName").textContent = D.module.title;
    $("#methodSeg").innerHTML = D.methods_available.map(m => `<button aria-pressed="${m === state.method}" data-method="${m}">${m === "expert_judgment" ? "Juicio experto" : "Rank ordering <small>proyectado</small>"}</button>`).join("");
    $("#methodSeg").querySelectorAll("button").forEach(b => b.onclick = () => { state.method = b.dataset.method; store.set("compass.method", state.method); render(); });
  }
  function renderRail(cur) {
    const m = M() || {};
    const cnt = { fortalezas: (m.strengths || []).length, oportunidades: (m.opportunities || []).length, decisiones: (m.decisions || []).length };
    $("#rail").innerHTML = NAV.map(([k, l, ic]) => `<a href="#/${k}" ${k === cur ? 'aria-current="page"' : ""} aria-label="${l}">${ic}<span class="lbl">${l}</span>${cnt[k] ? `<span class="count">${cnt[k]}</span>` : ""}</a>`).join("");
  }
  const crumbs = items => `<nav class="crumbs" aria-label="Ruta"><a href="#/resumen">Diagnóstico</a>${items.map(([t, h]) => `<span class="sep">›</span>${h ? `<a href="${h}">${esc(t)}</a>` : `<b>${esc(t)}</b>`}`).join("")}</nav>`;
  const styleTag = s => `<span class="tag ${SCL[s]}"><span class="sw" style="background:${col(s)}"></span>${esc(lab(s))}</span>`;
  const dimTag = d => `<span class="tag ${SCL[D.dimensions[d].style]}" data-tip="${esc(D.dimensions[d].glosario || "")}"><span class="sw" style="background:${col(D.dimensions[d].style)}"></span>${esc(d)} · ${esc(D.dimensions[d].label)}</span>`;
  const lvl = l => `<span class="lvl ${l === "sólida" ? "solida" : l}" data-tip="Nivel de evidencia: considera el número de decisiones que la sustentan y si el intervalo de confianza excluye el promedio del nodo.">Evidencia ${esc(l)}</span>`;
  const methodNote = () => state.method === "rank_ordering" ? `<span class="tag" style="border-color:rgba(138,120,255,.6)">Clave rank ordering · proyectada</span>` : `<span class="tag">Clave: juicio experto (moda)</span>`;

  function predLabel(p) {
    if (!p || !p.predominant || !p.predominant.length) return "Sin puntaje disponible";
    return p.predominant.map(lab).join(" = ");
  }
  const shareCI = p => p.shares_ci_combinado || p.shares_ci_nodos;

  // ------------------------------------------------------------------ vistas
  function vSinPuntaje(m) {
    return crumbs([["Sin puntaje"]]) + `<section class="panel empty"><h2>Sin puntaje disponible</h2><p>${esc(m.motivo || "")}</p></section>`;
  }

  function hero(m) {
    const p = m.profile, top = p.predominant[0];
    const stab = p.estabilidad_predominio[top];
    const s = S();
    return `<section class="panel hero" aria-label="Perfil predominante">
      <div class="hero-icon" style="border-color:${col(top)};background:linear-gradient(145deg,${col(top)}55,${col(top)}14)">${I.leader}</div>
      <div>
        <div class="lead">Perfil predominante en esta simulación</div>
        <h1>${esc(predLabel(p))}</h1>
        <div class="meta">
          <span class="tag" style="color:var(--ink)">${I.check.replace("<svg", '<svg width="14" height="14" style="color:#cfc6ff"')} ${p.n_decisiones} de ${p.n_decisiones} situaciones completadas · ${D.module.n_nodes} en el módulo</span>
          <span class="tag" data-tip="Se muestra «Perfil ilustrativo» mientras el cálculo use datos sintéticos o una regla provisional.">Perfil ilustrativo</span>
          <span class="tag" data-tip="Proporción de remuestreos bootstrap de las decisiones en que este estilo sigue siendo el predominante.">Estabilidad ${esc(p.estabilidad_etiqueta)} · ${Math.round(stab * 100)} % de réplicas</span>
          ${p.empate ? `<span class="tag" style="border-color:var(--warn)">Empate exacto</span>` : ""}
          ${methodNote()}
        </div>
      </div>
      <div class="hero-side">
        <div class="big-num">${f1(p.shares[top])}<small> %</small></div>
        <div class="ink2">de los puntos del recorrido<br><span class="muted">${f1(p.points[top])} de ${f1(p.total_points)} pts · IC95 ${ci(shareCI(p)[top])}</span></div>
      </div>
    </section>`;
  }

  function styleBars(p, opts = {}) {
    const c = shareCI(p);
    return `<div class="sbars">${STY.map(s => `<div class="sbar">
        <div class="name"><span class="sw" style="background:${col(s)};margin-right:8px"></span>${esc(lab(s))}</div>
        ${C.styleBar(p.shares[s], c[s], col(s), `${lab(s)}: ${f1(p.shares[s])} % (${f1(p.points[s])} pts) · IC95 ${ci(c[s])}`)}
        <div class="val">${f1(p.shares[s])} %<small>${f1(p.points[s])} pts · IC ${c[s] ? `${f1(c[s][0])}–${f1(c[s][1])}` : "—"}</small></div></div>`).join("")}</div>
      <p class="footnote">La barra usa una escala común de 0 a 100 %. Los bigotes blancos muestran el intervalo de confianza del 95 % (${p.shares_ci_combinado ? "remuestreando jueces y decisiones" : "remuestreando decisiones"}). El porcentaje describe la distribución del puntaje; no es percentil ni probabilidad.</p>`;
  }

  function howProfile() {
    return `<details class="how"><summary>¿Cómo se calcula este porcentaje?</summary>
      <ol><li>Cada alternativa tiene en la clave un vector de 9 puntajes (0–4), uno por dimensión MLQ.</li>
      <li>Por cada decisión se promedian los puntos de las dimensiones de cada estilo (5 transformacionales, 2 transaccionales, 2 pasivas), para que ningún estilo gane solo por tener más dimensiones.</li>
      <li>Se suman los aportes de todas las decisiones y se divide cada estilo por el total.</li></ol>
      <code class="formula">% estilo = Σ_decisiones promedio(puntos dims del estilo) ÷ Σ_estilos (…) × 100</code>
      <p>El predominio se determina antes de redondear. Con empate exacto se muestran ambos estilos; con total cero, «Sin puntaje disponible».</p></details>`;
  }

  function vResumen() {
    const m = M(), p = m.profile;
    const F = m.strengths[0], O = m.opportunities[0];
    const dec = m.decisions.find(d => d.node_id === m.decision_destacada) || m.decisions[0];
    const ch = dec.alternatives.find(a => a.is_chosen);
    const com = m.commitments;
    const topInfl = [...m.decisions].sort((a, b) => b.influencia_pp - a.influencia_pp).slice(0, 3);
    return crumbs([["Resumen"]]) + hero(m) + `
    <section class="panel"><div class="panel-head"><div><h2>Distribución del puntaje por estilo</h2><p class="sub">Suma de los aportes de tus ${p.n_decisiones} decisiones según la clave de puntuación.</p></div>
      <a class="btn ghost" href="#/perfil">Ver detalle por dimensión ${I.arrow}</a></div>
      ${styleBars(p)}${howProfile()}</section>
    <div class="grid g3">
      ${F ? `<a class="panel icard" href="#/fortalezas/${F.id}"><div class="ic">${I.star.replace("<svg", '<svg style="color:#cfc6ff"')}</div><div>
        <div class="t1">Fortaleza observada</div><div class="t2">${esc(F.title)}</div>
        <div class="row" style="display:flex;gap:6px;flex-wrap:wrap">${dimTag(F.dim)} ${lvl(F.evidencia)}</div>
        <div class="ink2" style="margin-top:8px">${F.n_nodos_evidencia} decisiones la sustentan${F.bajo_umbral ? " · bajo el umbral: posición relativa más alta" : ""}</div>
        <span class="more">Ver nodos y decisiones ${I.arrow}</span></div></a>` : `<div class="panel empty">Sin fortalezas sobre el umbral.</div>`}
      ${O ? `<a class="panel icard" href="#/oportunidades/${O.id}"><div class="ic o">${I.aim.replace("<svg", '<svg style="color:#3fd6c6"')}</div><div>
        <div class="t1">Oportunidad de mejora</div><div class="t2">${esc(O.title)}</div>
        <div class="row" style="display:flex;gap:6px;flex-wrap:wrap">${dimTag(O.dim)} ${lvl(O.evidencia)}</div>
        <div class="ink2" style="margin-top:8px">«${esc(O.pregunta)}»</div>
        <span class="more">Ver pregunta y acción de desarrollo ${I.arrow}</span></div></a>` : `<div class="panel empty">Sin oportunidades bajo el umbral.</div>`}
      <a class="panel icard" href="#/validez"><div class="ic c">${I.shield.replace("<svg", '<svg style="color:#f2c94c"')}</div><div>
        <div class="t1">Coherencia declarado–ejecutado</div>
        <div class="t2">${com.n ? `${com.cumplidos} de ${com.n} compromisos cumplidos` : "Sin compromisos registrados"}</div>
        ${com.n ? C.stackRow([{ v: com.cumplidos, color: "#3ecf8e", tip: `Cumplidos: ${com.cumplidos}` }, { v: com.parciales, color: "#e0b341", tip: `Parciales: ${com.parciales}` }, { v: com.no_cumplidos, color: "#e5656b", tip: `No cumplidos: ${com.no_cumplidos}` }], com.n, { h: 12 }) : ""}
        <div class="legend" style="margin-top:6px"><span><span class="sw" style="background:#3ecf8e"></span>cumplido</span><span><span class="sw" style="background:#e0b341"></span>parcial</span><span><span class="sw" style="background:#e5656b"></span>no cumplido</span></div>
        <span class="more">Lo que dijiste vs. lo que hiciste ${I.arrow}</span></div></a>
    </div>
    <section class="panel"><div class="panel-head"><div><span class="kicker">Decisiones en contexto</span><h2 style="margin-top:4px">${esc(dec.title)}</h2>
      <p class="sub">${esc(dec.day)} · ${esc(dec.block)} · ${esc(themeLabel(dec.theme))} — la decisión que más elevó el % ${esc(lab(p.predominant[0]))} (+${f2(dec.influencia_pp)} pp).</p></div>
      <a class="btn" href="${nodeHref(dec.node_id)}">Ver aporte al perfil ${I.ext}</a></div>
      <div class="grid g-main"><div><div class="quote ch"><b>Decisión elegida:</b> ${esc(ch.text)}</div>
        <p class="footnote">Otras decisiones con alto peso:</p>
        <div class="items">${topInfl.filter(d => d.node_id !== dec.node_id).slice(0, 2).map(d => decItem(d)).join("")}</div>
        <p style="margin-top:12px"><a href="#/decisiones">Ver las ${m.decisions.length} decisiones en la semana ${I.arrow}</a></p></div>
      <div><h3>Cómo se construye tu perfil</h3>
        <div class="flow" style="grid-template-columns:1fr 24px 1fr 24px 1fr">
          <div class="fx"><span class="muted">1 · Decides</span><b>${p.n_decisiones}</b><span class="ink2">situaciones</span></div><div class="arrow">→</div>
          <div class="fx"><span class="muted">2 · La clave asigna</span><b>9</b><span class="ink2">dimensiones MLQ</span></div><div class="arrow">→</div>
          <div class="fx"><span class="muted">3 · Se agrupan en</span><b>3</b><span class="ink2">estilos</span></div></div>
        <p class="footnote">Abre cualquier decisión para ver el recorrido completo: alternativa → dimensiones → estilo.</p></div></div>
    </section>`;
  }

  function decItem(d) {
    const ch = d.alternatives.find(a => a.is_chosen);
    return `<a class="item" href="${nodeHref(d.node_id)}"><span class="chip-id">${d.node_id}</span>
      <div><div class="ttl">${esc(d.title)}</div><div class="ink2" style="font-size:13px">«${esc(ch.text.slice(0, 120))}${ch.text.length > 120 ? "…" : ""}»</div></div>
      <span class="tag">+${f2(d.influencia_pp)} pp</span></a>`;
  }

  function vPerfil() {
    const m = M(), p = m.profile, coh = MQ().cohort;
    let prev = null;
    const rows = DIMS.map(d => {
      const st = D.dimensions[d].style, r = { code: d, label: D.dimensions[d].label, z: m.dimensions[d].z_mean, ci: m.dimensions[d].z_ci, color: col(st), cohort: coh.z_media[d], groupStart: st !== prev,
        tip: `${d} · ${D.dimensions[d].label}: z̄ = ${f2(m.dimensions[d].z_mean)} IC95 ${ci2(m.dimensions[d].z_ci)} · índice relativo ${Math.round((m.dimensions[d].rel || 0) * 100)} % · media cohorte ${f2(coh.z_media[d])}` };
      prev = st; return r;
    });
    const maxPts = Math.max(...m.decisions.map(d => STY.reduce((a, s) => a + d.style_points[s], 0)));
    const pred = p.predominant[0];
    return crumbs([["Perfil por estilo"]]) + `
    <section class="panel"><div class="panel-head"><div><h2>Perfil por estilo</h2><p class="sub">Porcentaje y puntos de cada estilo, con intervalos de confianza.</p></div>${methodNote()}</div>
      ${styleBars(p)}
      <table class="t" style="margin-top:12px"><thead><tr><th>Estilo</th><th class="n">% puntos</th><th class="n">Puntos</th><th class="n">IC95 decisiones</th><th class="n">IC95 clave</th><th class="n">IC95 combinado</th><th class="n">Índice relativo</th><th class="n">Predominio en réplicas</th></tr></thead>
      <tbody>${STY.map(s => `<tr><td>${styleTag(s)}</td><td class="n">${f1(p.shares[s])}</td><td class="n">${f1(p.points[s])}</td><td class="n">${ci(p.shares_ci_nodos[s])}</td><td class="n">${p.shares_ci_clave ? ci(p.shares_ci_clave[s]) : "n/d"}</td><td class="n">${p.shares_ci_combinado ? ci(p.shares_ci_combinado[s]) : "n/d"}</td><td class="n">${Math.round(p.rel_style[s] * 100)} %</td><td class="n">${Math.round(p.estabilidad_predominio[s] * 100)} %</td></tr>`).join("")}</tbody></table>
      <p class="footnote">Índice relativo: posición entre el mínimo (0 %) y el máximo (100 %) de puntos alcanzables con las decisiones que encontraste.</p>
    </section>
    <section class="panel"><div class="panel-head"><div><h2>Las 9 dimensiones del Modelo de Rango Completo</h2>
      <p class="sub">Cada punto es el promedio de tus decisiones estandarizadas dentro de cada nodo (0 = alternativa promedio del nodo). Barra = IC95 %; trazo vertical gris = media de la cohorte sintética.</p></div>
      <div class="legend">${STY.map(s => `<span><span class="sw" style="background:${col(s)}"></span>${lab(s)}</span>`).join("")}<span><span class="sw" style="background:#b4c6d4;width:3px"></span>media cohorte</span></div></div>
      ${C.dotPlot(rows)}
      <details class="how"><summary>¿Qué es la estandarización intra-nodo?</summary><p>Para cada nodo y dimensión se compara el puntaje de la alternativa elegida con el promedio y la desviación de las tres alternativas disponibles. Así, elegir la alternativa con más aporte en un nodo donde todas aportan poco también cuenta. Si las tres alternativas tienen el mismo puntaje, el aporte es neutro (0).</p>
      <code class="formula">z = (w_elegida − media_alternativas) / desv_alternativas ;  z = 0 si desv = 0</code></details>
    </section>
    <section class="panel"><div class="panel-head"><div><h2>Aporte de cada decisión en puntos</h2><p class="sub">Cada segmento conserva el color de su estilo. Selecciona una fila para abrir el contexto, la alternativa elegida y las dimensiones asociadas.</p></div>
      <div class="legend">${STY.map(s => `<span><span class="sw" style="background:${col(s)}"></span>${lab(s)}</span>`).join("")}</div></div>
      <div class="items">${m.decisions.map(d => `<a class="item" href="${nodeHref(d.node_id)}" style="grid-template-columns:52px minmax(160px,1.2fr) minmax(140px,2fr) 80px;padding:10px 14px">
        <span class="chip-id">${d.node_id}</span><div><div class="ttl" style="font-size:13.5px">${esc(d.title)}</div><div class="muted" style="font-size:12px">${esc(d.day)} · ${esc(d.block)} · alt. ${d.chosen}</div></div>
        ${C.stackRow(STY.map(s => ({ v: d.style_points[s], color: col(s), tip: `${lab(s)}: ${f2(d.style_points[s])} pts` })), maxPts)}
        <span class="ink2" style="text-align:right;font-size:12px" data-tip="Variación del % ${esc(lab(pred))} si se quitara esta decisión">${d.influencia_pp >= 0 ? "+" : ""}${f2(d.influencia_pp)} pp</span></a>`).join("")}</div>
    </section>
    <div class="grid g2">
      <section class="panel"><h2>Variación entre situaciones</h2><p class="sub">Distribución por estilo según el tema de la situación. La variación de una persona entre situaciones también es información para la retroalimentación.</p>
        <div class="items">${Object.entries(m.por_tema).sort((a, b) => b[1].n - a[1].n).map(([t, v]) => `<div class="item" style="cursor:default;grid-template-columns:150px 1fr 50px;padding:10px 14px"><div><b>${esc(themeLabel(t))}</b></div>
          ${C.stackRow(STY.map(s => ({ v: v.shares[s] || 0, color: col(s), tip: `${lab(s)}: ${f1(v.shares[s])} %` })), 100, { h: 14 })}<span class="muted" style="text-align:right">n=${v.n}</span></div>`).join("")}</div>
        <p class="footnote">Con pocas decisiones por tema (n), las diferencias son descriptivas y no deben interpretarse como estables.</p></section>
      <section class="panel"><div class="panel-head"><div><h2>Referencia de cohorte</h2><p class="sub">% ${esc(lab(pred))} de las ${coh.n} sesiones sintéticas (puntos grises) y de esta sesión.</p></div><span class="tag" style="border-color:rgba(138,120,255,.6)">Proyectado</span></div>
        ${C.strip(coh.shares_todas[pred], p.shares[pred], col(pred), { min: Math.floor(Math.min(p.shares[pred], ...coh.shares_todas[pred]) / 5) * 5, max: Math.ceil(Math.max(p.shares[pred], ...coh.shares_todas[pred]) / 5) * 5, unit: "%", tip: `Esta sesión: ${f1(p.shares[pred])} %` })}
        <div class="stats" style="grid-template-columns:repeat(3,1fr)">${STY.map(s => `<div class="stat"><div class="k">${esc(lab(s))}</div><div class="v">P${Math.round(p.percentil_cohorte[s])}</div><div class="d">media cohorte ${f1(coh.shares_media[s])} %</div></div>`).join("")}</div>
        <p class="footnote">Los percentiles poblacionales están proyectados: requieren una muestra de referencia real y validada.</p></section>
    </div>`;
  }

  // ---- subcapa: fortalezas / oportunidades
  function listItems(items, kind) {
    const base = kind === "F" ? "fortalezas" : "oportunidades";
    return `<div class="items">${items.map(it => `<a class="item" href="#/${base}/${it.id}">
      <span class="chip-id">${it.id}</span>
      <div><div class="ttl">${esc(it.title)}</div><div class="row">${dimTag(it.dim)} ${lvl(it.evidencia)} ${Object.keys(it.temas).map(t => `<span class="tag">${esc(themeLabel(t))}</span>`).join("")}</div></div>
      <div style="width:180px"><div class="muted" style="font-size:11px;text-align:right">índice relativo ${Math.round(it.rel * 100)} %</div>${C.relBar(it.rel, it.rel_ci, col(it.style), { tip: `Índice relativo ${Math.round(it.rel * 100)} % · IC95 ${ci(it.rel_ci.map(v => v * 100))}` })}</div></a>`).join("")}</div>`;
  }

  function itemDetail(it, kind, all) {
    const base = kind === "F" ? "fortalezas" : "oportunidades";
    const name = kind === "F" ? "Fortalezas observadas" : "Oportunidades de mejora";
    const inv = it.inverse;
    return crumbs([[name, `#/${base}`], [it.title]]) + `
    <section class="panel">
      <div class="detail-head"><div><span class="kicker">${kind === "F" ? "Fortaleza observada" : "Oportunidad de mejora"} · ${it.id}</span><h2 style="margin-top:6px">${esc(it.title)}</h2>
        <div class="row" style="display:flex;gap:6px;flex-wrap:wrap">${dimTag(it.dim)} ${styleTag(it.style)} ${lvl(it.evidencia)} ${it.bajo_umbral ? `<span class="tag" style="border-color:var(--warn)">Bajo el umbral</span>` : ""} ${inv ? `<span class="tag" data-tip="En las dimensiones pasivas un índice bajo es deseable: se leen en sentido inverso.">Dimensión pasiva · lectura inversa</span>` : ""}</div></div>
        <div class="seg">${all.map(x => `<button aria-pressed="${x.id === it.id}" onclick="location.hash='#/${base}/${x.id}'">${x.id}</button>`).join("")}</div></div>
      <p class="ink2" style="font-size:15px;margin:14px 0 0"><b style="color:var(--ink)">Qué observamos:</b> ${esc(it.conducta)}.</p>
      <div class="stats">
        <div class="stat"><div class="k">Índice relativo</div><div class="v">${Math.round(it.rel * 100)} %</div><div class="d">IC95 ${ci(it.rel_ci.map(v => v * 100))}</div></div>
        <div class="stat"><div class="k">z̄ intra-nodo</div><div class="v">${it.z_mean > 0 ? "+" : ""}${f2(it.z_mean)}</div><div class="d">IC95 ${ci2(it.z_ci)}</div></div>
        <div class="stat"><div class="k">${kind === "F" ? "Decisiones que la sustentan" : "Decisiones con brecha"}</div><div class="v">${it.n_nodos_evidencia}<small class="muted" style="font-size:14px"> / ${it.n_decisiones}</small></div><div class="d">${kind === "F" ? "eligió la alternativa de mayor aporte" : "existía una alternativa con más aporte"}</div></div>
        <div class="stat"><div class="k">Percentil cohorte</div><div class="v">P${Math.round(it.percentil_cohorte)}</div><div class="d">proyectado · cohorte sintética</div></div>
      </div>
      ${C.relBar(it.rel, it.rel_ci, col(it.style), { h: 26, tip: "Línea punteada = 50 % del rango alcanzable" })}
      <div class="legend" style="justify-content:space-between;margin-top:4px"><span>0 % · mínimo alcanzable</span><span>50 %</span><span>100 % · máximo alcanzable</span></div>
      ${kind === "O" ? `<div class="grid g2" style="margin-top:16px"><div class="callout q"><div class="k">Pregunta para explorar</div><p>${esc(it.pregunta)}</p></div><div class="callout a"><div class="k">Acción de desarrollo</div><p>${esc(it.accion)}</p></div></div>` : ""}
      <details class="how" style="margin-top:14px"><summary>¿Cómo se identificó?</summary>
        <p>${kind === "F" ? `Se seleccionan dimensiones con índice relativo ≥ 60 % (en dimensiones pasivas, ≤ 40 %). Una decisión la «sustenta» cuando la alternativa elegida tiene el mayor ${inv ? "aporte inverso (menor puntaje pasivo)" : "puntaje"} de su nodo en esta dimensión.` : `Se seleccionan dimensiones con índice relativo ≤ 50 % (en dimensiones pasivas, ≥ 50 %). La brecha de cada decisión es la diferencia entre la alternativa de ${inv ? "menor" : "mayor"} aporte del nodo y la elegida.`}
        Nivel de evidencia: <b>sólida</b> con ≥ 4 decisiones y un IC95 que excluye 0; <b>moderada</b> con ≥ 2 decisiones y |z̄| > 0,15; en otro caso <b>tentativa</b>.</p></details>
    </section>
    <section class="panel"><h2>${kind === "F" ? "Nodos y decisiones que la sustentan" : "Nodos donde aparece la brecha"}</h2><p class="sub">Ordenadas por ${kind === "F" ? "magnitud del aporte (|z|)" : "tamaño de la brecha"}. Abre una decisión para ver su contexto completo.</p>
      <div class="items">${it.nodos.map(e => `<a class="evrow" href="${nodeHref(e.node_id)}">
        <div><span class="chip-id">${e.node_id}</span><div class="when" style="margin-top:6px">${esc(e.day)} · ${esc(e.block)}</div></div>
        <div><div class="nt">${esc(nodeTitle(e.node_id))}</div><div class="quote ch">${esc(e.chosen_text)}</div>
          ${kind === "O" ? `<div class="quote alt2"><span class="muted">Alternativa ${e.alt_mayor_aporte} (${inv ? "menor aporte pasivo" : "mayor aporte"}):</span> ${esc(e.alt_mayor_aporte_text)}</div>` : ""}</div>
        <div><div class="muted" style="font-size:11.5px">${esc(it.dim)}: elegida ${f1(e.points_chosen)} · rango ${f1(e.points_min)}–${f1(e.points_max)}</div>
          ${miniRange(e, col(it.style))}
          <div class="row" style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">${kind === "O" ? `<span class="tag">brecha ${f1(e.gap_points)} pts</span>` : `<span class="tag">z ${e.z > 0 ? "+" : ""}${f2(e.z)}</span>`}
          <span class="tag" data-tip="Permanencia del cursor sobre la alternativa elegida">${ms(e.dwell_elegida_ms)}</span>${e.ritmo ? `<span class="tag" data-tip="Duración de la decisión comparada con la cohorte en el mismo nodo">${esc(e.ritmo)}</span>` : ""}</div></div></a>`).join("") || `<div class="empty">Sin decisiones asociadas.</div>`}</div>
      <p class="footnote">${it.n_nodos_evidencia > it.nodos.length ? `Se muestran ${it.nodos.length} de ${it.n_nodos_evidencia}. ` : ""}La alternativa «de mayor aporte» lo es según la clave de puntuación; no implica que sea la única respuesta adecuada en la situación.</p></section>`;
  }
  function miniRange(e, color) {
    const W = 220, x = v => v / 4 * W;
    return `<svg viewBox="0 0 ${W} 18" width="100%" height="18"><rect x="0" y="6" width="${W}" height="6" rx="3" fill="rgba(255,255,255,.07)"/>
      <rect x="${x(e.points_min)}" y="6" width="${Math.max(2, x(e.points_max) - x(e.points_min))}" height="6" rx="3" fill="${color}" opacity=".3"/>
      <circle cx="${x(e.points_chosen)}" cy="9" r="6" fill="${color}" stroke="#0b1b2b" stroke-width="2"/></svg>`;
  }
  const nodeTitle = id => (D.module.nodes_index.find(n => n.node_id === id) || {}).title || id;

  function vFortalezas(r) {
    const m = M(), items = m.strengths;
    if (r.id) { const it = items.find(x => x.id === r.id); if (it) return itemDetail(it, "F", items); }
    return crumbs([["Fortalezas observadas"]]) + `<section class="panel"><h2>Fortalezas observadas</h2><p class="sub">Conductas que aparecen de forma consistente en tus decisiones. Cada una se vincula con los nodos y alternativas que la sustentan.</p>
      ${items.length ? listItems(items, "F") : `<div class="empty">No se identifican fortalezas con evidencia suficiente en este recorrido.</div>`}</section>`;
  }
  function vOportunidades(r) {
    const m = M(), items = m.opportunities;
    if (r.id) { const it = items.find(x => x.id === r.id); if (it) return itemDetail(it, "O", items); }
    return crumbs([["Oportunidades de mejora"]]) + `<section class="panel"><h2>Oportunidades de mejora</h2><p class="sub">Dimensiones donde existían alternativas con mayor aporte. Cada una propone una pregunta para la conversación de retroalimentación y una acción concreta.</p>
      ${items.length ? listItems(items, "O") : `<div class="empty">No se identifican oportunidades bajo el umbral.</div>`}</section>`;
  }

  // ---- decisiones en contexto
  function vDecisiones() {
    const m = M(), f = state.filters, s = S();
    const byNode = Object.fromEntries(m.decisions.map(d => [d.node_id, d]));
    const days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"];
    const pass = d => (!f.theme || d.theme === f.theme) && (!f.type || d.type === f.type) && (!f.style || d.estilo_dominante_aporte === f.style) && (!f.commit || (d.commitment && d.commitment.result === f.commit));
    const ccol = { cumplido: "#3ecf8e", parcial: "#e0b341", no_cumplido: "#e5656b" };
    const opts = (k, list, l) => `<select data-f="${k}" aria-label="${l}"><option value="">${l}: todos</option>${list.map(([v, t]) => `<option value="${v}" ${f[k] === v ? "selected" : ""}>${esc(t)}</option>`).join("")}</select>`;
    const ga = s.global_attributes || [];
    const npc = Object.entries(s.npc_final || {});
    return crumbs([["Decisiones en contexto"]]) + `
    <section class="panel"><div class="panel-head"><div><h2>Decisiones en contexto · ${esc(D.module.week || "Semana 1")}</h2><p class="sub">${m.decisions.length} decisiones de ${D.module.n_nodes} nodos del módulo. El borde de color indica el estilo que más aportó cada decisión. Los nodos no encontrados en tu recorrido aparecen atenuados.</p></div></div>
      <div class="filters" style="margin-bottom:12px">
        ${opts("theme", Object.entries(D.themes), "Tema")}
        ${opts("type", [["obligatorio", "Obligatorio"], ["proactivo", "Proactivo"], ["contingente", "Contingente"]], "Tipo")}
        ${opts("style", STY.map(s => [s, lab(s)]), "Estilo del aporte")}
        ${opts("commit", [["cumplido", "Cumplido"], ["parcial", "Parcial"], ["no_cumplido", "No cumplido"]], "Compromiso")}
        <button class="btn ghost" id="clearF">Limpiar filtros</button>
        <div class="legend" style="margin-left:auto">${STY.map(s => `<span><span class="sw" style="background:${col(s)}"></span>${lab(s)}</span>`).join("")}<span><span class="sw" style="background:#3ecf8e;border-radius:50%"></span>compromiso</span></div>
      </div>
      <div class="week">${days.map(day => `<div class="day"><h4>${day}</h4>${D.module.nodes_index.filter(n => n.day === day).map(n => {
        const d = byNode[n.node_id];
        if (!d) return `<div class="node dim" style="--c:#445" data-tip="${esc(n.type === "contingente" ? (n.condition || {}).descripcion || "Nodo contingente no activado" : "Nodo proactivo no iniciado en este recorrido")}"><div class="nt">${esc(n.title)}</div><div class="nm"><span class="chip-id">${n.node_id}</span>${esc(n.type)} · no encontrado</div></div>`;
        const links = [...d.links.strengths, ...d.links.opportunities];
        return `<button class="node ${pass(d) ? "" : "dim"}" style="--c:${col(d.estilo_dominante_aporte)}" data-node="${d.node_id}">
          ${d.commitment ? `<span class="flag" style="background:${ccol[d.commitment.result]}" data-tip="Compromiso: ${esc(d.commitment.expected_action)} → ${esc(d.commitment.result.replace("_", " "))}"></span>` : ""}
          <div class="nt">${esc(d.title)}</div>
          <div class="nm"><span class="chip-id">${d.node_id}</span>${esc(d.block)} · alt. ${d.chosen}${links.length ? ` · ${links.join(" ")}` : ""}${d.type !== "obligatorio" ? ` · ${esc(d.type)}` : ""}</div></button>`;
      }).join("")}</div>`).join("")}</div>
    </section>
    <div class="grid g2">
      <section class="panel"><h2>Reputación a lo largo de la semana</h2><p class="sub">Atributo global de la organización tras cada bloque horario (efecto acumulado de tus decisiones).</p>
        ${C.line(ga.map(g => ({ v: g.reputacion, label: g.block === "Inicio" ? "Inicio" : `${g.day.slice(0, 2)} ${g.block[0]}`, tip: `${g.day} ${g.block}: ${Math.round(g.reputacion)} %` })), "#f2c94c", { label: "Reputación por bloque" })}</section>
      <section class="panel"><h2>Confianza final de los actores</h2><p class="sub">Atributo interno de cada NPC al cerrar la simulación (inicio = 50).</p>
        ${C.hbars(npc.map(([k, v]) => ({ label: (D.module.npcs[k] || {}).rol || k, v: v.confianza, text: Math.round(v.confianza), color: "#3fd6c6", tip: `${k}: ${v.confianza}` })), { max: 100, ref: 50, left: 190 })}</section>
    </div>`;
  }

  // ---- cajón de nodo (subcapa 3)
  function openDrawer(nid) {
    const m = M(); if (!m || !m.decisions) return;
    const d = m.decisions.find(x => x.node_id === nid);
    if (!d) return closeDrawer(true);
    const inf = (MQ().cohort.informatividad || []).find(x => x.node_id === nid) || {};
    const choiceTot = Object.values(inf.eleccion_cohorte || {}).reduce((a, b) => a + b, 0);
    const maxSP = Math.max(...d.alternatives.map(a => STY.reduce((x, s) => x + a.style_points[s], 0)));
    const pr = d.process;
    const pred = m.profile.predominant[0];
    const ccol = { cumplido: ["#3ecf8e", "✓"], parcial: ["#e0b341", "½"], no_cumplido: ["#e5656b", "✕"] };
    drawer.innerHTML = `<button class="btn x" id="closeD" aria-label="Cerrar">✕ Cerrar</button>
      <span class="kicker">${d.node_id} · ${esc(d.day)} · ${esc(d.block)} · ${esc(d.type)} · ${esc(themeLabel(d.theme))}</span>
      <h2 id="drawerTitle">${esc(d.title)}</h2>
      <p class="ink2">${esc(d.context)}</p>
      <div class="row" style="display:flex;gap:6px;flex-wrap:wrap">${d.npcs.map(n => `<span class="tag">${esc((D.module.npcs[n] || {}).rol || n)}${["Asistente", "TENS"].includes(n) ? "" : ` · ${esc(n)}`}</span>`).join("")}
        ${d.condition ? `<span class="tag" style="border-color:var(--warn)" data-tip="${esc(d.condition.descripcion)}">Contingente: ${esc(d.condition.node_id)}</span>` : ""}
        ${[...d.links.strengths.map(id => `<a class="tag t" href="#/fortalezas/${id}?n=${d.node_id}">★ ${id}</a>`), ...d.links.opportunities.map(id => `<a class="tag tr" href="#/oportunidades/${id}?n=${d.node_id}">◎ ${id}</a>`)].join("")}</div>

      <h3 style="margin-top:20px">Alternativas y su perfil en la clave</h3>
      <div class="alts">${d.alternatives.map(a => {
        const n = (inf.eleccion_cohorte || {})[a.alt_id] || 0;
        return `<div class="alt ${a.is_chosen ? "ch" : ""}"><div class="ah"><b>Alternativa ${a.alt_id}${a.is_chosen ? ' · <span style="color:#f2c94c">Elegida</span>' : ""}</b>
          <span class="muted" style="font-size:12px" data-tip="Proporción de la cohorte sintética que eligió esta alternativa">cohorte: ${choiceTot ? Math.round(n / choiceTot * 100) : 0} %</span></div>
          <p>${esc(a.text)}</p>
          ${C.stackRow(STY.map(s => ({ v: a.style_points[s], color: col(s), tip: `${lab(s)}: ${f2(a.style_points[s])} pts/dim` })), maxSP, { h: 12 })}
          <div class="heat" style="margin-top:8px">${DIMS.map(dd => { const v = a.points[dd], c = col(D.dimensions[dd].style); return `<div style="background:${c}${Math.round((0.12 + 0.88 * v / 4) * 255).toString(16).padStart(2, "0")}" data-tip="${esc(dd)} · ${esc(D.dimensions[dd].label)}: ${f1(v)} de 4">${f1(v)}</div>`; }).join("")}</div>
          <div class="heat-l">${DIMS.map(dd => `<span>${dd}</span>`).join("")}</div>
          ${a.effects ? `<div class="muted" style="font-size:12px;margin-top:6px">Consecuencias: reputación ${a.effects.reputacion >= 0 ? "+" : ""}${a.effects.reputacion} · ${Object.entries(a.effects.confianza || {}).map(([k, v]) => `confianza ${esc(k)} ${v >= 0 ? "+" : ""}${v}`).join(" · ")}</div>` : ""}
          ${a.expected_action ? `<div class="muted" style="font-size:12px">Compromiso implícito: ${esc(a.expected_action.action)} (${esc(a.expected_action.mechanic)})</div>` : ""}</div>`;
      }).join("")}</div>

      <h3 style="margin-top:22px">Aporte de esta decisión al perfil</h3>
      ${C.flow(d, DIMS, D.dimensions, STY, D.styles)}
      <div class="kv"><div class="stat"><div class="k">Peso en el % ${esc(lab(pred))}</div><div class="v">${d.influencia_pp >= 0 ? "+" : ""}${f2(d.influencia_pp)} pp</div><div class="d">cambio si se quitara esta decisión</div></div>
        <div class="stat"><div class="k">Estilo con mayor aporte</div><div class="v" style="font-size:18px">${esc(lab(d.estilo_dominante_aporte))}</div><div class="d">${STY.map(s => `${lab(s).split(" ")[0]} ${f2(d.style_points[s])}`).join(" · ")}</div></div>
        <div class="stat"><div class="k">z intra-nodo destacado</div><div class="v" style="font-size:18px">${(() => { const e = Object.entries(d.z).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))[0]; return `${e[0]} ${e[1] > 0 ? "+" : ""}${f2(e[1])}`; })()}</div><div class="d">frente a las otras alternativas del nodo</div></div></div>

      <h3 style="margin-top:22px">Datos de proceso</h3>
      ${pr ? `${C.hbars(["A", "B", "C"].map(a => ({ label: `Alternativa ${a}${a === d.chosen ? " ✓" : ""}`, v: pr.dwell_ms[a], text: ms(pr.dwell_ms[a]), color: a === d.chosen ? "#f2c94c" : "#7f97aa", strong: a === d.chosen, tip: `Permanencia del cursor: ${pr.dwell_ms[a]} ms · ${pr.considerations ? pr.considerations[a] : "—"} consideraciones` })), { left: 130, w: 900, rowH: 30 })}
        <div class="kv" style="margin-top:8px"><div class="stat"><div class="k">Alternancias</div><div class="v">${pr.alternations}</div><div class="d">primera: ${pr.first_considered} · última: ${pr.last_considered}</div></div>
        <div class="stat"><div class="k">Más considerada = elegida</div><div class="v">${pr.coincide_mas_considerada ? "Sí" : "No"}</div><div class="d">más considerada: ${pr.most_considered}</div></div>
        <div class="stat"><div class="k">Duración del nodo</div><div class="v">${ms(pr.duracion_ms)}</div><div class="d">ritmo ${esc(d.ritmo || "—")} frente a la cohorte</div></div></div>` : `<p class="muted">Sin datos de proceso para este nodo.</p>`}

      ${d.commitment ? `<h3 style="margin-top:22px">Declarado vs. ejecutado</h3><div class="callout" style="border-color:${ccol[d.commitment.result][0]}"><div class="k">${ccol[d.commitment.result][1]} ${esc(d.commitment.result.replace("_", " "))} · mecánica ${esc(d.commitment.mechanic)}</div>
        <p>${esc(d.commitment.expected_action)}</p><div class="muted" style="font-size:12.5px;margin-top:4px">${esc(d.commitment.evidence)}</div></div>` : ""}
      <p class="footnote">Datos sintéticos. La alternativa con mayor aporte lo es según la clave de puntuación vigente (${state.method === "expert_judgment" ? "juicio experto" : "rank ordering, proyectada"}).</p>`;
    drawer.classList.add("on"); scrim.classList.add("on");
    drawer.scrollTop = 0;
    $("#closeD").onclick = () => { location.hash = base(); };
    $("#closeD").focus({ preventScroll: true });
  }
  function closeDrawer() { drawer.classList.remove("on"); scrim.classList.remove("on"); }
  scrim.onclick = () => { location.hash = base(); };
  document.addEventListener("keydown", e => { if (e.key === "Escape" && drawer.classList.contains("on")) location.hash = base(); });

  // ---- validez
  function vValidez() {
    const m = M(), q = MQ(), kq = q.key_quality, coh = q.cohort, st = D.status, s = S();
    if (!m || m.sin_puntaje) return crumbs([["Validez y confianza"]]) + `<div class="panel empty">Sin puntaje disponible.</div>`;
    const p = m.profile, pr = m.process, com = m.commitments, sens = s.sensibilidad_metodo;
    const isEJ = state.method === "expert_judgment";
    return crumbs([["Validez y confianza"]]) + `
    <section class="panel"><h2>Qué es funcional, qué depende del juicio experto y qué está proyectado</h2><p class="sub">Estado de cada componente del diagnóstico en esta versión.</p>
      <div class="statusband"><div class="sb f"><h4>● Funcional en la demo</h4><ul>${st.funcional.map(x => `<li>${esc(x)}</li>`).join("")}</ul></div>
        <div class="sb e"><h4>½ Basado en juicio experto</h4><ul>${st.juicio_experto.map(x => `<li>${esc(x)}</li>`).join("")}</ul></div>
        <div class="sb p"><h4>○ Proyectado</h4><ul>${st.proyectado.map(x => `<li>${esc(x)}</li>`).join("")}</ul></div></div></section>

    <section class="panel"><div class="panel-head"><div><h2>Intervalos de confianza y estabilidad del perfil</h2><p class="sub">${p.n_decisiones} decisiones · bootstrap de decisiones (B = 2.000)${isEJ ? " y bootstrap combinado jueces × decisiones (B = 1.000)" : ""}.</p></div>${methodNote()}</div>
      <div class="grid g3">${STY.map(sy => `<div><div style="display:flex;justify-content:space-between;align-items:baseline"><b>${esc(lab(sy))}</b><span class="ink2">${f1(p.shares[sy])} % ${ci(p.shares_ci_nodos[sy])}</span></div>
        ${C.hist(p.bootstrap_hist[sy], col(sy), p.shares[sy])}<div class="muted" style="font-size:12px">Predominante en ${Math.round(p.estabilidad_predominio[sy] * 100)} % de las réplicas</div></div>`).join("")}</div>
      <p class="footnote">Cada histograma muestra el % del estilo en 2.000 recorridos remuestreados de tus propias decisiones; la línea blanca es el valor observado. Estabilidad del predominio: <b>${esc(p.estabilidad_etiqueta)}</b> (≥ 80 % estable; 60–80 % moderada; &lt; 60 % inestable).</p></section>

    <div class="grid g2">
      <section class="panel"><h2>Calidad de la clave de puntuación</h2>
        ${isEJ ? `<p class="sub">${kq.n_jueces_incluidos} de ${kq.n_jueces_total} jueces incluidos · agregación: ${esc(kq.agregacion)} conservando ceros.</p>
        <div class="stats" style="grid-template-columns:repeat(3,1fr)"><div class="stat"><div class="k">ICC(2,k) panel</div><div class="v">${f2(kq.icc_global.icc2k)}</div><div class="d">acuerdo del promedio</div></div>
          <div class="stat"><div class="k">ICC(2,1) juez</div><div class="v">${f2(kq.icc_global.icc21)}</div><div class="d">juez individual</div></div>
          <div class="stat"><div class="k">Acuerdo ±1 punto</div><div class="v">${Math.round(kq.acuerdo_dentro_de_1 * 100)} %</div><div class="d">respecto de la mediana</div></div></div>
        <h3>ICC(2,k) por dimensión</h3>${C.hbars(DIMS.map(d => ({ label: d, v: kq.icc_por_dimension[d].icc2k, text: f2(kq.icc_por_dimension[d].icc2k), color: col(D.dimensions[d].style) })), { max: 1, ref: 0.75, left: 60 })}
        <p class="footnote">Línea punteada: 0,75 (referencia convencional de acuerdo bueno).</p>
        <h3 style="margin-top:12px">Jueces y criterios de exclusión</h3>
        <table class="t"><thead><tr><th>Juez</th><th>Formación</th><th class="n">DMA consenso</th><th class="n">r consenso</th><th>Estado</th></tr></thead><tbody>
        ${kq.jueces.map(j => `<tr><td>${j.expert_id}</td><td>${esc(j.formacion)}</td><td class="n">${f2(j.mad_consenso)}</td><td class="n">${f2(j.r_consenso)}</td><td>${j.excluido ? `<span style="color:var(--bad)">✕ excluido</span> <span class="muted">${j.flags.join(", ").replace(/_/g, " ")}</span>` : `<span style="color:var(--good)">✓ incluido</span>`}</td></tr>`).join("")}</tbody></table>`
        : `<p class="sub">Clave de rank ordering (proyectada). ${kq.n_celdas} celdas nodo × dimensión · ${kq.celdas_con_empate} con empates · ${kq.celdas_sin_clave.length} sin clave.</p><div class="callout"><p>${esc(kq.nota)}</p></div>`}
      </section>
      <section class="panel"><h2>Informatividad de los nodos</h2><p class="sub">Contraste de la clave C = máx − mín entre alternativas, por nodo y dimensión. Celdas rojas: sin contraste (C = 0); punto amarillo: contraste sin discriminación observada en la cohorte.</p>
        ${C.heat(coh.informatividad.map(r => ({ id: r.node_id, C: r.C, S: r.S })), DIMS, "#8a78ff", { max: isEJ ? 4 : 2 })}
        <p class="footnote">${coh.celdas_sin_contraste} celdas sin contraste · ${coh.celdas_contraste_sin_discriminacion} con contraste pero sin discriminación observada (de ${coh.informatividad.length * DIMS.length}).</p></section>
    </div>

    <div class="grid g2">
      <section class="panel"><h2>Fiabilidad por mitades (cohorte sintética)</h2><p class="sub">Correlación entre nodos pares e impares en ${coh.n} sesiones, corregida con Spearman-Brown.</p>
        ${C.hbars(DIMS.map(d => ({ label: d, v: Math.max(0, coh.fiabilidad_mitades[d].spearman_brown || 0), text: f2(coh.fiabilidad_mitades[d].spearman_brown), color: col(D.dimensions[d].style) })), { max: 1, ref: 0.7, left: 60 })}
        <p class="footnote">Con datos sintéticos estos valores solo prueban el cálculo. En datos reales la memoria de título reporta alfas entre −0,22 y 0,42: interpretar el perfil como descripción del recorrido.</p></section>
      <section class="panel"><h2>Datos de proceso y coherencia</h2>
        <div class="stats" style="grid-template-columns:repeat(2,1fr)">
          <div class="stat"><div class="k">Permanencia elegida vs descartadas</div><div class="v">${ms(pr.dwell_elegida_mediana_ms)} <small class="muted" style="font-size:14px">vs ${ms(pr.dwell_descartadas_mediana_ms)}</small></div><div class="d">diferencia mediana ${ms(pr.diferencia_mediana_ms)} IC95 [${ms(pr.diferencia_ic95[0])} ; ${ms(pr.diferencia_ic95[1])}] · r = ${f2(pr.wilcoxon_r)}</div></div>
          <div class="stat"><div class="k">Más considerada = elegida</div><div class="v">${Math.round(pr.coincidencia[0] * 100)} %</div><div class="d">IC95 Wilson [${Math.round(pr.coincidencia[1] * 100)} – ${Math.round(pr.coincidencia[2] * 100)}] % · ${pr.coincidencia_n} de ${pr.n}</div></div>
          <div class="stat"><div class="k">Compromisos cumplidos</div><div class="v">${com.n ? Math.round(com.proporcion_cumplidos[0] * 100) + " %" : "—"}</div><div class="d">${com.n ? `IC95 [${Math.round(com.proporcion_cumplidos[1] * 100)} – ${Math.round(com.proporcion_cumplidos[2] * 100)}] % · ${com.cumplidos}/${com.n}` : "sin compromisos"}</div></div>
          <div class="stat"><div class="k">Índice ponderado de coherencia</div><div class="v">${com.n ? f2(com.indice_ponderado) : "—"}</div><div class="d">cumplido 1 · parcial 0,5 · no 0</div></div></div>
        ${m.commitments_detail.length ? `<table class="t"><thead><tr><th>Nodo</th><th>Acción esperada</th><th>Mecánica</th><th>Resultado</th></tr></thead><tbody>${m.commitments_detail.map(c => `<tr><td><a href="${nodeHref(c.node_id)}">${c.node_id}</a></td><td>${esc(c.expected_action)}</td><td>${esc(c.mechanic)}</td><td>${{ cumplido: "✓ cumplido", parcial: "½ parcial", no_cumplido: "✕ no cumplido" }[c.result]}</td></tr>`).join("")}</tbody></table>` : ""}
      </section>
    </div>

    ${sens ? `<section class="panel"><h2>Sensibilidad a la clave de puntuación</h2><p class="sub">Mismo recorrido puntuado con juicio experto y con rank ordering (proyectado).</p>
      <div class="stats" style="grid-template-columns:repeat(${2 + STY.length},1fr)"><div class="stat"><div class="k">Mismo predominante</div><div class="v">${sens.mismo_predominante ? "Sí" : "No"}</div></div>
      <div class="stat"><div class="k">Spearman 9 dims</div><div class="v">${f2(sens.spearman_dimensiones)}</div></div>
      ${STY.map(sy => `<div class="stat"><div class="k">Δ ${esc(lab(sy))}</div><div class="v">${sens.diferencia_pp[sy] > 0 ? "+" : ""}${f1(sens.diferencia_pp[sy])} pp</div><div class="d">juicio experto − rank</div></div>`).join("")}</div></section>` : ""}

    <div class="grid g2">
      <section class="panel"><h2>Supuestos y reglas</h2><table class="t"><tbody>${D.assumptions.map(a => `<tr><td style="width:44px"><span class="chip-id">${a.id}</span></td><td style="width:120px"><b>${esc(a.tema)}</b></td><td class="ink2">${esc(a.texto)}</td></tr>`).join("")}</tbody></table></section>
      <section class="panel"><h2>Contexto de evidencia con datos reales</h2><p class="sub">${esc(D.evidence_context._nota)}</p>
        <table class="t"><tbody>${D.evidence_context.items.map(x => `<tr><td class="muted" style="width:170px">${esc(x.fuente)}</td><td>${esc(x.dato)}</td></tr>`).join("")}</tbody></table>
        <div class="callout a" style="margin-top:12px"><div class="k">Implicancia</div><p style="font-size:14px">${esc(D.evidence_context.implicancia)}</p></div></section>
    </div>`;
  }

  // ---- informe
  function vInforme() {
    const s = S(), m = M();
    const pdf = `reports/informe_tecnico_${state.code}_${state.method}.pdf`;
    const sections = ["Resumen del diagnóstico y advertencias de uso", "Datos, procedencia y versión (sintéticos)", "Método: clave, agregación, exclusión de jueces, mapeo a estilos, fórmulas",
      "Resultados: perfil por estilo y 9 dimensiones con IC95", "Incertidumbre: bootstrap de decisiones, de jueces y combinado; estabilidad del predominio", "Calidad de la clave: ICC(2,1), ICC(2,k), jueces excluidos, informatividad de nodos",
      "Datos de proceso y coherencia declarado–ejecutado (IC de Wilson)", "Fortalezas y oportunidades con su trazabilidad a nodos", "Sensibilidad a la clave (juicio experto vs rank ordering)", "Supuestos, reglas (empate, total cero, faltantes) y limitaciones", "Anexo: traza completa de decisiones"];
    return crumbs([["Informe técnico"]]) + `
    <section class="panel"><div class="panel-head"><div><span class="kicker">Descargable</span><h2 style="margin-top:4px">Informe técnico · ${esc(state.code)}</h2>
      <p class="sub">Generado por el pipeline desde los mismos datos que muestra este dashboard. Clave: ${state.method === "expert_judgment" ? "juicio experto" : "rank ordering (proyectada)"}.</p></div></div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <a class="btn primary" href="${pdf}" download>${I.doc} Descargar informe PDF</a>
        <button class="btn" id="dlCsv">Descargar métricas (CSV)</button>
        <button class="btn" id="dlJson">Descargar diagnóstico (JSON)</button></div>
      <p class="footnote">Si el PDF no existe para esta combinación, ejecute <code>python pipeline/run_pipeline.py</code>. CSV y JSON se generan en el navegador a partir de los datos cargados.</p></section>
    <div class="grid g2"><section class="panel"><h2>Contenido</h2><ol class="ink2">${sections.map(x => `<li style="margin:4px 0">${esc(x)}</li>`).join("")}</ol></section>
      <section class="panel"><h2>Ficha de la sesión</h2><table class="t"><tbody>
        <tr><td class="muted">Participante (seudónimo)</td><td>${esc(s.participant_code)}</td></tr><tr><td class="muted">Sesión</td><td>${esc(s.session_id)}</td></tr>
        <tr><td class="muted">Módulo</td><td>${esc(D.module.title)} · v${esc(s.module_version)}</td></tr><tr><td class="muted">Decisiones puntuadas</td><td>${m.profile ? m.profile.n_decisiones : "—"}</td></tr>
        <tr><td class="muted">Perfil</td><td>${m.profile ? esc(predLabel(m.profile)) + " · " + f1(m.profile.shares[m.profile.predominant[0]]) + " %" : "Sin puntaje"}</td></tr>
        <tr><td class="muted">Contrato de datos</td><td>${esc(D.schema_version)} · config ${esc(D.config_version)}</td></tr>
        <tr><td class="muted">Generado</td><td>${esc(D.generated_at)}</td></tr><tr><td class="muted">Datos</td><td>${D.synthetic ? "Sintéticos" : "Reales"}</td></tr></tbody></table></section></div>`;
  }

  function download(name, text, type) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type }));
    a.download = name; document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }
  function csv() {
    const m = M(), p = m.profile, rows = [["seccion", "clave", "valor", "ic_inf", "ic_sup", "nota"]];
    STY.forEach(s => { const c = shareCI(p)[s]; rows.push(["perfil_pct", s, p.shares[s], c[0], c[1], "IC95 " + (p.shares_ci_combinado ? "combinado" : "decisiones")]); rows.push(["estabilidad", s, p.estabilidad_predominio[s], "", "", "proporción de réplicas"]); });
    DIMS.forEach(d => { const x = m.dimensions[d]; rows.push(["z_dim", d, x.z_mean, x.z_ci[0], x.z_ci[1], ""]); rows.push(["rel_dim", d, x.rel, x.rel_ci[0], x.rel_ci[1], ""]); });
    m.decisions.forEach(d => rows.push(["decision", d.node_id, d.chosen, d.influencia_pp, "", STY.map(s => `${s}=${d.style_points[s]}`).join(" ")]));
    const pr = m.process; rows.push(["proceso", "coincidencia", pr.coincidencia[0], pr.coincidencia[1], pr.coincidencia[2], "Wilson"]);
    return rows.map(r => r.map(v => `"${String(v ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  }

  function vModulos() {
    const mods = [["Brújula: Ley Karin", "Gestión preventiva y resolución de conflictos laborales bajo la normativa de la Ley Karin.", "#d6b04a"], [D.module.title, D.module.description, null], ["Innovatec (Proyecto Quantum Leap)", "Lidera un proyecto de IA corporativa con decisiones éticas, presupuestarias y de talento.", "#8a78ff"], ["Gestión PyME (SERCOTEC)", "Asesora a emprendedores y gestiona fondos concursables para el desarrollo regional.", null], ["Gestión Municipal", "Equilibra comunidad, presupuesto público y tiempos políticos.", null]];
    return crumbs([["Módulos"]]) + `<section class="panel" style="text-align:center"><h2>Selecciona la versión de COMPASS</h2><p class="sub">En esta demo solo el módulo Gestión en Salud tiene diagnóstico disponible.</p></section>
      <div class="mods">${mods.map(([t, d, c], i) => `<div class="mod ${i === 1 ? "on" : "off"}" style="${c ? `border-color:${c}` : ""}"><h3 style="${c ? `color:${c}` : ""}">${esc(t)}</h3><p>${esc(d)}</p>
        ${i === 1 ? `<a class="btn primary" href="#/resumen">Disponible en la demo · ver diagnóstico ${I.arrow}</a>` : `<span class="muted">Próximamente</span>`}</div>`).join("")}</div>`;
  }

  // ------------------------------------------------------------------ eventos
  function bindView() {
    view.querySelectorAll("[data-node]").forEach(b => b.onclick = () => { location.hash = nodeHref(b.dataset.node); });
    view.querySelectorAll("select[data-f]").forEach(sel => sel.onchange = () => { state.filters[sel.dataset.f] = sel.value; render(); });
    const cf = $("#clearF"); if (cf) cf.onclick = () => { state.filters = { theme: "", type: "", style: "", commit: "" }; render(); };
    const dc = $("#dlCsv"); if (dc) dc.onclick = () => download(`metricas_${state.code}_${state.method}.csv`, "﻿" + csv(), "text/csv;charset=utf-8");
    const dj = $("#dlJson"); if (dj) dj.onclick = () => download(`diagnostico_${state.code}_${state.method}.json`, JSON.stringify({ meta: { schema_version: D.schema_version, generated_at: D.generated_at, synthetic: D.synthetic }, session: { ...S(), by_method: { [state.method]: M() } } }, null, 1), "application/json");
  }
  document.querySelectorAll(".step").forEach(b => b.onclick = () => { location.hash = b.dataset.go; });
  document.addEventListener("mouseover", e => {
    const t = e.target.closest("[data-tip]");
    if (!t || !t.getAttribute("data-tip")) { tip.classList.remove("on"); return; }
    tip.textContent = t.getAttribute("data-tip"); tip.classList.add("on");
  });
  document.addEventListener("mousemove", e => {
    if (!tip.classList.contains("on")) return;
    const w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = Math.min(window.innerWidth - w - 10, e.clientX + 14) + "px";
    tip.style.top = (e.clientY + h + 24 > window.innerHeight ? e.clientY - h - 12 : e.clientY + 16) + "px";
  });
  let lastView = null;
  window.addEventListener("hashchange", () => { const v = parse().view + (parse().id || ""); render(); if (v !== lastView) { if (!parse().n) window.scrollTo(0, 0); lastView = v; } });
  lastView = parse().view + (parse().id || "");
  render();
})();
