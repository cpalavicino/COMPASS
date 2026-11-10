# Contrato de datos

El flujo es siempre el mismo y cada etapa se comunica solo por archivos:

```
simulador ──► inputs/sessions/*.json ─┐
módulo    ──► inputs/module.json     ├─► pipeline/run_pipeline.py ──► data/diagnosticos.json/.js ──► index.html
clave     ──► inputs/experts_raw.json│                                                   └──────► reports/*.pdf
              inputs/rank_key.json  ─┘        (config/scoring_config.json, config/narrativas.json)
```

## 1. Sesión (`inputs/sessions/<codigo>.json`, schema `compass-session/0.1`)

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| `participant_code` | string | sí | seudónimo; nunca nombre ni correo |
| `session_id`, `module_id`, `module_version` | string | sí | `module_id` debe coincidir con `inputs/module.json` |
| `decisions[]` | lista | sí | una por nodo encontrado, en orden |
| `decisions[].node_id`, `.alt_id` | string | sí | identificador de nodo y alternativa (A/B/C) |
| `decisions[].t_presented_ms`, `.t_decided_ms` | int | no | Timelogger |
| `decisions[].process.dwell_ms` | {alt: ms} | no | permanencia del cursor por alternativa (mecánica Oficina) |
| `decisions[].process.considerations`, `.alternations`, `.first_considered`, `.last_considered` | — | no | indicadores de proceso |
| `commitments[]` | lista | no | salida del ComparisonEngine: `node_id`, `alt_id`, `mechanic`, `expected_action`, `result` ∈ {cumplido, parcial, no_cumplido}, `evidence` |
| `global_attributes[]` | lista | no | `{day, block, reputacion}` por bloque horario |
| `npc_final` | {npc: {confianza}} | no | atributos internos al cierre |

Si faltan datos de proceso o compromisos, el dashboard oculta esos bloques; el perfil se calcula igual.
Decisiones cuyo nodo/alternativa no existe en la clave se excluyen del cálculo.

## 2. Módulo (`inputs/module.json`)

`nodes[]` con `node_id`, `order`, `title`, `context`, `day`, `block`, `type` (obligatorio/proactivo/contingente),
`theme`, `npcs[]`, `condition` (contingentes) y `alternatives[]` (`alt_id`, `text`, `effects`, `expected_action`).

## 3. Clave de juicio experto (`inputs/experts_raw.json`)

```json
{ "scale": [0,4],
  "experts": [{"expert_id":"E01","formacion":"Psicología"}],
  "ratings": [["E01","N01","A","IIA",3], ...] }
```
Formato largo: juez, nodo, alternativa, dimensión, valor. Los IDs de juez deben ser seudónimos.

## 4. Clave de rank ordering (`inputs/rank_key.json`)

```json
{ "method":"rank_ordering", "k":3,
  "key": { "N01": { "IIA": [["A"],["C","B"]], "IIC": [["A"],["B"],["C"]], ... } } }
```
Por nodo y dimensión: grupos de alternativas de mayor a menor correspondencia (mismo grupo = empate).

## 5. Salida (`data/diagnosticos.json`, schema `compass-diagnostico/0.3`)

```
schema_version, generated_at, synthetic, default_method, methods_available
styles{}, dimensions{} (incluye textos de narrativas), themes{}, module{… nodes_index[]}
status{funcional, juicio_experto, proyectado}, assumptions[], evidence_context{}
methods.<metodo>: key_quality, key (nodo→alt→dim), cohort{shares, z_media, fiabilidad_mitades, informatividad[]}
sessions.<codigo>:
   encabezado (session_id, n_decisiones, global_attributes, npc_final)
   sensibilidad_metodo
   by_method.<metodo>:
      profile        predominant[], empate, shares, points, shares_ci_{nodos,clave,combinado},
                     estabilidad_predominio, bootstrap_hist, rel_style, percentil_cohorte
      dimensions.<d> z_mean, z_ci, rel, rel_ci, points, percentil_cohorte
      strengths[]    id, dim, title, conducta, evidencia, rel, z_ci, nodos[] (node_id, chosen_text, points_*, z …)
      opportunities[] … + pregunta, accion, nodos[].alt_mayor_aporte(_text), gap_points
      decisions[]    contexto, alternatives[] (points por dim, style_points, effects), z, influencia_pp,
                     process, ritmo, commitment, links{strengths, opportunities}
      por_tema, por_dia, process, commitments, commitments_detail
   (o by_method.<metodo> = {sin_puntaje:true, motivo})
```

`data/diagnosticos.js` contiene el mismo objeto como `window.COMPASS_DATA = …` para que `index.html`
funcione abriéndolo directamente (sin servidor). En la plataforma React/FastAPI, el endpoint del
diagnóstico puede devolver exactamente este JSON por sesión.

## Reglas

- Predominio calculado antes de redondear; empate exacto → se listan los estilos empatados.
- Total de puntos = 0 → `sin_puntaje` y la interfaz muestra «Sin puntaje disponible».
- Porcentajes solo con puntajes no negativos y comparables (promedio por dimensión del estilo).
