# COMPASS · Dashboard de diagnóstico (demo con datos sintéticos)

Mockup navegable del diagnóstico de liderazgo del módulo **Gestión en Salud (CESFAM)**.
Toma las decisiones registradas por la simulación, las puntúa con la clave vigente (juicio experto)
o con la clave proyectada (rank ordering) y muestra el perfil con sus subcapas, su trazabilidad
y un informe técnico descargable.

> **Todos los datos son sintéticos** (semilla fija `20261122`). Ninguna cifra describe a una persona real.
> La planilla original de juicio experto **no** está en este repositorio: solo se usó una tabla
> derivada de textos de nodos y alternativas, sin datos identificatorios (`synthetic/module_source.json`).

## Arranque rápido

```bash
# 1) Ver el dashboard: abrir index.html con doble clic (funciona sin servidor ni internet)
#    o, si se prefiere, servirlo:
python -m http.server 8000      # → http://localhost:8000

# 2) Regenerar todo (datos sintéticos → métricas → dashboard → PDFs)
pip install -r requirements.txt
python synthetic/generate_synthetic.py
python pipeline/run_pipeline.py
python pipeline/tests/test_pipeline.py
```

## Recorrido sugerido (feria)

1. **Módulos** → «Gestión en Salud · Disponible en la demo».
2. **Resumen** → perfil predominante, % por estilo con IC95, fortaleza, oportunidad, coherencia declarado–ejecutado y la decisión de mayor peso.
3. **Fortalezas** → elegir una → ver los nodos y alternativas que la sustentan → abrir un nodo (3.ª capa).
4. **Oportunidades** → pregunta para explorar, acción de desarrollo y, por nodo, la alternativa elegida frente a la de mayor aporte.
5. **Decisiones en contexto** → semana completa, filtros por tema/tipo/estilo/compromiso; cada nodo abre su ficha: alternativas con su vector de 9 dimensiones, flujo alternativa → dimensión → estilo, datos de proceso y consecuencias.
6. **Validez y confianza** → qué es funcional / experto / proyectado, bootstrap, ICC de jueces, informatividad de nodos, supuestos.
7. **Informe técnico** → PDF, CSV de métricas y JSON de la sesión.

Arriba se puede cambiar de **participante** (4 sesiones de ejemplo) y de **clave** (juicio experto ↔ rank ordering).

| Sesión | Perfil (juicio experto) | Para qué sirve en la demo |
|---|---|---|
| P-0142 | Transformacional, estabilidad moderada | caso base |
| P-0087 | Transformacional, estable | contraste de fortalezas |
| P-0203 | Transaccional, estabilidad moderada | perfil disputado |
| P-0311 | Pasivo/evitativo; 19 decisiones | recorrido corto, sin fortalezas sobre el umbral |

## Estructura

```
index.html                 interfaz (vanilla JS, sin compilación)
assets/css, assets/js      estilos (estética de la simulación) y gráficos SVG propios
data/diagnosticos.(json|js)  CONTRATO DE SALIDA que consume la interfaz y el informe
reports/                   informes técnicos PDF (sesión × clave)
config/scoring_config.json método, agregación, mapeo dims→estilos, umbrales, bootstrap
config/narrativas.json     textos por dimensión (fortaleza, pregunta, acción) — editable sin código
inputs/                    ENTRADAS: módulo, clave experta (jueces), clave rank, sesiones
pipeline/compass_diag/     keys.py (claves) · scoring.py · stats.py · build.py · report.py
pipeline/tests/            empate, total cero, regla modal, 60/30/10 de la guía, rank ordering
synthetic/                 generador de datos sintéticos
docs/                      contrato de datos, integración del rank ordering, capturas
```

Separación narrativa / insumos de puntuación / interfaz: `inputs/module.json` (narrativa),
`inputs/experts_raw.json` + `inputs/rank_key.json` + `config/` (puntuación), `index.html` + `assets/` (interfaz).

## Conectar datos reales

1. Exportar cada sesión del simulador a `inputs/sessions/<codigo>.json` (formato en `docs/contrato_datos.md`).
2. Reemplazar `inputs/experts_raw.json` por la matriz real **seudonimizada** de jueces, o entregar `inputs/rank_key.json`.
3. Elegir método en `config/scoring_config.json → scoring.method` y sesiones en `export.sessions`.
4. `python pipeline/run_pipeline.py`. La interfaz no cambia.

Detalle de la migración a rank ordering: `docs/integracion_rank_ordering.md`.

## Estado de la puntuación

- **Funcional en la demo:** registro de elecciones, cálculo de % con insumos de ejemplo, trazabilidad, IC bootstrap, proceso, coherencia.
- **Basado en juicio experto:** interpretación del perfil, fortalezas/oportunidades — aplicable cuando Investigación replique y verifique la regla vigente (agregación entre expertos, mapeo, pesos, comparabilidad entre estilos).
- **Proyectado:** rank ordering, percentiles poblacionales, métricas de autoconciencia (contraste MLQ-5X).

Versión de datos: contrato `compass-diagnostico/0.3`, configuración `0.3-demo`, sesiones `compass-session/0.1`.
