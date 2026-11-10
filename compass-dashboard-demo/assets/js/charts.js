/* COMPASS · gráficos SVG sin dependencias. Cada función devuelve un string SVG.
   Todas las marcas llevan data-tip para el tooltip global (ver app.js). */
(function () {
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const f1 = v => (v == null || isNaN(v)) ? "—" : (Math.round(v * 10) / 10).toLocaleString("es-CL", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const f2 = v => (v == null || isNaN(v)) ? "—" : v.toLocaleString("es-CL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const INK = "#eaf2f8", INK2 = "#b4c6d4", INK3 = "#7f97aa", GRID = "rgba(140,190,220,.16)", TRACK = "rgba(255,255,255,.07)";

  // Barra 0-100 con intervalo (bigotes) — perfil por estilo
  function styleBar(share, ci, color, tip) {
    const W = 1000, H = 30, y = 8, h = 14;
    const x = v => Math.max(0, Math.min(100, v)) / 100 * W;
    let s = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${esc(tip)}">`;
    s += `<rect x="0" y="${y}" width="${W}" height="${h}" rx="7" fill="${TRACK}"/>`;
    s += `<rect x="0" y="${y}" width="${Math.max(6, x(share))}" height="${h}" rx="7" fill="${color}" data-tip="${esc(tip)}"/>`;
    if (ci && ci[0] != null) {
      const a = x(ci[0]), b = x(ci[1]);
      s += `<g stroke="${INK}" stroke-width="2" vector-effect="non-scaling-stroke" opacity=".9">
        <line x1="${a}" x2="${b}" y1="${y + h / 2}" y2="${y + h / 2}" vector-effect="non-scaling-stroke"/>
        <line x1="${a}" x2="${a}" y1="${y - 3}" y2="${y + h + 3}" vector-effect="non-scaling-stroke"/>
        <line x1="${b}" x2="${b}" y1="${y - 3}" y2="${y + h + 3}" vector-effect="non-scaling-stroke"/></g>`;
    }
    return s + `</svg>`;
  }

  // Fila apilada (aporte de una decisión por estilo), con separación de 2px entre segmentos
  function stackRow(parts, max, opts = {}) {
    const W = opts.w || 300, H = opts.h || 16;
    let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" preserveAspectRatio="none">`;
    s += `<rect x="0" y="0" width="${W}" height="${H}" rx="4" fill="${TRACK}"/>`;
    let x = 0;
    parts.forEach((p, i) => {
      const w = Math.max(0, p.v / max * W - (i < parts.length - 1 ? 2 : 0));
      if (w > 0) s += `<rect x="${x}" y="0" width="${w}" height="${H}" rx="3" fill="${p.color}" data-tip="${esc(p.tip)}"/>`;
      x += p.v / max * W;
    });
    return s + `</svg>`;
  }

  // Gráfico de puntos con IC para las 9 dimensiones (z intra-nodo), línea 0 = alternativa promedio del nodo
  function dotPlot(rows, opts = {}) {
    const W = 760, rowH = 34, top = 26, left = 250, right = 30, H = top + rows.length * rowH + 30;
    const lo = opts.min ?? -1.5, hi = opts.max ?? 1.5;
    const x = v => left + (Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo) * (W - left - right);
    let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Puntaje por dimensión con intervalo de confianza">`;
    for (let t = Math.ceil(lo * 2) / 2; t <= hi + 1e-9; t += 0.5) {
      s += `<line x1="${x(t)}" x2="${x(t)}" y1="${top - 8}" y2="${H - 24}" stroke="${t === 0 ? "rgba(234,242,248,.55)" : GRID}" stroke-width="${t === 0 ? 1.5 : 1}" ${t === 0 ? "" : 'stroke-dasharray="2 4"'}/>`;
      s += `<text x="${x(t)}" y="${H - 8}" fill="${INK3}" font-size="11" text-anchor="middle">${t > 0 ? "+" : ""}${f1(t)}</text>`;
    }
    s += `<text x="${x(lo)}" y="14" fill="${INK3}" font-size="11">◀ menor aporte que el promedio del nodo</text>`;
    s += `<text x="${x(hi)}" y="14" fill="${INK3}" font-size="11" text-anchor="end">mayor aporte ▶</text>`;
    rows.forEach((r, i) => {
      const cy = top + i * rowH + rowH / 2;
      if (r.groupStart && i > 0) s += `<line x1="10" x2="${W - 10}" y1="${cy - rowH / 2}" y2="${cy - rowH / 2}" stroke="${GRID}"/>`;
      s += `<rect x="0" y="${cy - rowH / 2}" width="${W}" height="${rowH}" fill="transparent" data-tip="${esc(r.tip)}"/>`;
      s += `<rect x="10" y="${cy - 5}" width="10" height="10" rx="3" fill="${r.color}"/>`;
      s += `<text x="28" y="${cy + 4}" fill="${INK}" font-size="12.5" font-weight="700">${esc(r.code)}</text>`;
      s += `<text x="78" y="${cy + 4}" fill="${INK2}" font-size="12">${esc(r.label)}</text>`;
      if (r.ci && r.ci[0] != null) s += `<line x1="${x(r.ci[0])}" x2="${x(r.ci[1])}" y1="${cy}" y2="${cy}" stroke="${r.color}" stroke-width="4" stroke-linecap="round" opacity=".55" pointer-events="none"/>`;
      if (r.cohort != null) s += `<line x1="${x(r.cohort)}" x2="${x(r.cohort)}" y1="${cy - 9}" y2="${cy + 9}" stroke="${INK2}" stroke-width="2" pointer-events="none"/>`;
      s += `<circle cx="${x(r.z)}" cy="${cy}" r="6.5" fill="${r.color}" stroke="#0b1b2b" stroke-width="2" pointer-events="none"/>`;
    });
    return s + `</svg>`;
  }

  // Índice relativo 0-100 con banda de IC
  function relBar(rel, ci, color, opts = {}) {
    const W = 300, H = opts.h || 22, y = (H - 10) / 2;
    const x = v => Math.max(0, Math.min(1, v)) * W;
    let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" preserveAspectRatio="none">`;
    s += `<rect x="0" y="${y}" width="${W}" height="10" rx="5" fill="${TRACK}"/>`;
    if (ci && ci[0] != null) s += `<rect x="${x(ci[0])}" y="${y - 3}" width="${Math.max(2, x(ci[1]) - x(ci[0]))}" height="16" rx="5" fill="${color}" opacity=".22"/>`;
    s += `<rect x="0" y="${y}" width="${Math.max(4, x(rel))}" height="10" rx="5" fill="${color}" data-tip="${esc(opts.tip || "")}"/>`;
    s += `<line x1="${W / 2}" x2="${W / 2}" y1="0" y2="${H}" stroke="rgba(234,242,248,.35)" stroke-dasharray="2 3"/>`;
    return s + `</svg>`;
  }

  // Histograma de réplicas bootstrap (0-100 en 24 clases)
  function hist(counts, color, marker, opts = {}) {
    const W = 320, H = opts.h || 90, b = counts.length, mx = Math.max(1, ...counts), bw = W / b;
    let s = `<svg viewBox="0 0 ${W} ${H + 18}" width="100%">`;
    counts.forEach((c, i) => {
      const h = c / mx * H;
      if (c > 0) s += `<rect x="${i * bw + 1}" y="${H - h}" width="${bw - 2}" height="${h}" rx="2" fill="${color}" data-tip="${esc(`${Math.round(i * 100 / b)}–${Math.round((i + 1) * 100 / b)} %: ${c} réplicas`)}"/>`;
    });
    s += `<line x1="0" x2="${W}" y1="${H}" y2="${H}" stroke="${GRID}"/>`;
    if (marker != null) s += `<line x1="${marker / 100 * W}" x2="${marker / 100 * W}" y1="0" y2="${H}" stroke="${INK}" stroke-width="2"/>`;
    [0, 25, 50, 75, 100].forEach(t => s += `<text x="${t / 100 * W}" y="${H + 14}" fill="${INK3}" font-size="10" text-anchor="${t === 0 ? "start" : t === 100 ? "end" : "middle"}">${t}%</text>`);
    return s + `</svg>`;
  }

  // Línea simple (reputación a lo largo de la semana)
  function line(points, color, opts = {}) {
    const W = 620, H = opts.h || 150, l = 34, r = 12, t = 12, bt = 34;
    const n = points.length;
    const x = i => l + (n === 1 ? 0 : i / (n - 1) * (W - l - r));
    const y = v => t + (1 - v / 100) * (H - t - bt);
    let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${esc(opts.label || "")}">`;
    [0, 50, 100].forEach(v => s += `<line x1="${l}" x2="${W - r}" y1="${y(v)}" y2="${y(v)}" stroke="${GRID}"/><text x="${l - 6}" y="${y(v) + 4}" fill="${INK3}" font-size="10" text-anchor="end">${v}</text>`);
    s += `<polyline fill="none" stroke="${color}" stroke-width="2" points="${points.map((p, i) => `${x(i)},${y(p.v)}`).join(" ")}"/>`;
    points.forEach((p, i) => {
      s += `<circle cx="${x(i)}" cy="${y(p.v)}" r="4" fill="${color}" stroke="#0b1b2b" stroke-width="2"/>`;
      s += `<rect x="${x(i) - 14}" y="${t}" width="28" height="${H - t - bt}" fill="transparent" data-tip="${esc(p.tip)}"/>`;
      if (p.label) s += `<text x="${x(i)}" y="${H - 14}" fill="${INK3}" font-size="10" text-anchor="middle">${esc(p.label)}</text>`;
    });
    return s + `</svg>`;
  }

  // Barras horizontales simples
  function hbars(items, opts = {}) {
    const W = opts.w || 520, rowH = opts.rowH || 26, l = opts.left || 120, r = 60, H = items.length * rowH + 6;
    const mx = opts.max ?? Math.max(...items.map(i => i.v));
    let s = `<svg viewBox="0 0 ${W} ${H}" width="100%">`;
    if (opts.ref != null) { const rx = l + opts.ref / mx * (W - l - r); s += `<line x1="${rx}" x2="${rx}" y1="0" y2="${H}" stroke="rgba(234,242,248,.4)" stroke-dasharray="3 3"/>`; }
    items.forEach((it, i) => {
      const y = i * rowH + 4, w = Math.max(3, it.v / mx * (W - l - r));
      s += `<text x="${l - 8}" y="${y + rowH / 2 + 1}" fill="${it.strong ? INK : INK2}" font-size="12" text-anchor="end" font-weight="${it.strong ? 800 : 600}">${esc(it.label)}</text>`;
      s += `<rect x="${l}" y="${y + 4}" width="${W - l - r}" height="${rowH - 12}" rx="4" fill="${TRACK}"/>`;
      s += `<rect x="${l}" y="${y + 4}" width="${w}" height="${rowH - 12}" rx="4" fill="${it.color}" data-tip="${esc(it.tip || "")}"/>`;
      s += `<text x="${l + w + 6}" y="${y + rowH / 2 + 1}" fill="${INK}" font-size="12" font-weight="700">${esc(it.text ?? it.v)}</text>`;
    });
    return s + `</svg>`;
  }

  // Mapa de calor nodo x dimensión (contraste de la clave), con marca de "sin discriminación observada"
  function heat(rows, dims, color, opts = {}) {
    const cw = 30, ch = 16, l = 46, t = 22, W = l + dims.length * cw + 8, H = t + rows.length * ch + 4;
    const mx = opts.max || 4;
    let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W * 1.25}px">`;
    dims.forEach((d, j) => s += `<text x="${l + j * cw + cw / 2}" y="14" fill="${INK3}" font-size="9" text-anchor="middle" font-weight="700">${esc(d)}</text>`);
    rows.forEach((r, i) => {
      const y = t + i * ch;
      s += `<text x="${l - 6}" y="${y + ch - 4}" fill="${INK2}" font-size="9.5" text-anchor="end">${esc(r.id)}</text>`;
      dims.forEach((d, j) => {
        const v = r.C[d] ?? 0, sd = r.S[d];
        const a = v <= 0 ? 0 : 0.15 + 0.85 * Math.min(1, v / mx);
        s += `<rect x="${l + j * cw + 1}" y="${y + 1}" width="${cw - 2}" height="${ch - 2}" rx="3" fill="${v <= 0 ? "rgba(229,101,107,.25)" : color}" fill-opacity="${v <= 0 ? 1 : a}" data-tip="${esc(`${r.id} · ${d}: contraste C = ${f2(v)} · discriminación S = ${sd == null ? "—" : f2(sd)}`)}"/>`;
        if (v > 0 && (sd === 0)) s += `<circle cx="${l + j * cw + cw / 2}" cy="${y + ch / 2}" r="3" fill="#e0b341" pointer-events="none"/>`;
      });
    });
    return s + `</svg>`;
  }

  // Flujo didáctico: alternativa elegida -> 9 dimensiones -> 3 estilos
  function flow(dec, dims, dimInfo, styles, styleInfo) {
    const W = 760, H = 330, ch = dec.alternatives.find(a => a.is_chosen);
    const dx = 300, sx = 600;
    const rowH = (H - 40) / dims.length;
    let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Cómo una decisión se transforma en puntaje por estilo">`;
    s += `<rect x="6" y="${H / 2 - 52}" width="190" height="104" rx="14" fill="rgba(242,201,76,.08)" stroke="rgba(242,201,76,.5)"/>`;
    s += `<text x="20" y="${H / 2 - 28}" fill="#f2c94c" font-size="11" font-weight="800" letter-spacing="1.5">ALTERNATIVA ${esc(ch.alt_id)}</text>`;
    wrap(ch.text, 26).slice(0, 4).forEach((ln, i) => s += `<text x="20" y="${H / 2 - 8 + i * 16}" fill="${INK}" font-size="12">${esc(ln)}${i === 3 ? "…" : ""}</text>`);
    const sy = {};
    styles.forEach((st, k) => sy[st] = 50 + k * 100);
    dims.forEach((d, j) => {
      const y = 24 + j * rowH + rowH / 2, v = ch.points[d], st = dimInfo[d].style, c = styleInfo[st].color;
      const w = v / 4 * 120;
      s += `<path d="M196 ${H / 2} C 250 ${H / 2}, 240 ${y}, ${dx - 6} ${y}" fill="none" stroke="${c}" stroke-opacity="${0.1 + v / 4 * 0.6}" stroke-width="${1 + v * 1.2}"/>`;
      s += `<text x="${dx}" y="${y + 4}" fill="${INK}" font-size="11.5" font-weight="700">${esc(d)}</text>`;
      s += `<rect x="${dx + 46}" y="${y - 6}" width="120" height="12" rx="4" fill="${TRACK}"/>`;
      s += `<rect x="${dx + 46}" y="${y - 6}" width="${Math.max(2, w)}" height="12" rx="4" fill="${c}" data-tip="${esc(`${dimInfo[d].label}: ${f2(v)} de 4 puntos`)}"/>`;
      s += `<text x="${dx + 172}" y="${y + 4}" fill="${INK2}" font-size="11">${f1(v)}</text>`;
      s += `<path d="M${dx + 196} ${y} C ${sx - 40} ${y}, ${sx - 60} ${sy[st] + 20}, ${sx - 4} ${sy[st] + 20}" fill="none" stroke="${c}" stroke-opacity=".28" stroke-width="1.5"/>`;
    });
    styles.forEach(st => {
      const y = sy[st], c = styleInfo[st].color, v = ch.style_points[st];
      s += `<rect x="${sx}" y="${y}" width="150" height="44" rx="12" fill="rgba(0,0,0,.25)" stroke="${c}"/>`;
      s += `<text x="${sx + 12}" y="${y + 18}" fill="${INK}" font-size="12" font-weight="800">${esc(styleInfo[st].label)}</text>`;
      s += `<text x="${sx + 12}" y="${y + 35}" fill="${INK2}" font-size="11.5">promedio ${f2(v)} pts/dim.</text>`;
    });
    return s + `</svg>`;
  }

  function wrap(text, n) {
    const words = String(text).split(/\s+/), out = [];
    let cur = "";
    words.forEach(w => { if ((cur + " " + w).trim().length > n) { out.push(cur.trim()); cur = w; } else cur += " " + w; });
    if (cur.trim()) out.push(cur.trim());
    return out;
  }

  // Tira de cohorte: puntos de la cohorte de referencia + marcador de la sesión
  function strip(values, mark, color, opts = {}) {
    const W = 520, H = 46, l = 10, r = 10;
    const lo = opts.min ?? 0, hi = opts.max ?? 100;
    const x = v => l + (v - lo) / (hi - lo) * (W - l - r);
    let s = `<svg viewBox="0 0 ${W} ${H + 14}" width="100%">`;
    s += `<line x1="${l}" x2="${W - r}" y1="${H / 2}" y2="${H / 2}" stroke="${GRID}"/>`;
    values.forEach((v, i) => s += `<circle cx="${x(v)}" cy="${H / 2 + ((i * 7) % 15) - 7}" r="3.2" fill="${INK3}" opacity=".7"/>`);
    s += `<line x1="${x(mark)}" x2="${x(mark)}" y1="4" y2="${H - 4}" stroke="${color}" stroke-width="3" data-tip="${esc(opts.tip || "")}"/>`;
    s += `<circle cx="${x(mark)}" cy="${H / 2}" r="7" fill="${color}" stroke="#0b1b2b" stroke-width="2"/>`;
    [lo, (lo + hi) / 2, hi].forEach(t => s += `<text x="${x(t)}" y="${H + 12}" fill="${INK3}" font-size="10" text-anchor="middle">${Math.round(t)}${opts.unit || ""}</text>`);
    return s + `</svg>`;
  }

  window.C = { styleBar, stackRow, dotPlot, relBar, hist, line, hbars, heat, flow, strip, esc, f1, f2 };
})();
