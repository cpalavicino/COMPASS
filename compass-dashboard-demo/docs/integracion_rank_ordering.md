# Integración de la clave rank ordering

El pipeline ya incluye un adaptador funcional (`pipeline/compass_diag/keys.py → RankOrderingKey`) y
la interfaz permite alternar entre claves. Hoy la clave rank es **sintética**; para conectarla:

## Opción A — clave consensuada (lo mínimo)

1. Entregar `inputs/rank_key.json` con el orden de alternativas por nodo y dimensión (ver `contrato_datos.md` §4).
2. En `config/scoring_config.json`: `"scoring": {"method": "rank_ordering", ...}`.
3. Definir con Investigación la regla de puntos (`rank_ordering.points`). Por defecto `k − rango`
   (mejor = 2, segundo = 1, peor = 0; los empates comparten rango medio).
4. `python pipeline/run_pipeline.py`. Todo lo demás (estandarización intra-nodo, % por estilo,
   fortalezas, oportunidades, informe) funciona igual porque consume la matriz `nodo × alternativa × dimensión`.

## Opción B — rankings individuales por juez (recomendado)

Si cada juez entrega su ranking, se puede estimar también la incertidumbre de la clave:

1. Guardar en formato largo `[juez, nodo, dim, alt, rango]`.
2. En `RankOrderingKey`, agregar los rankings (p. ej., rango medio o Borda) y implementar
   `replicates(B, rng)` remuestreando jueces, igual que `ExpertJudgmentKey.replicates`.
3. Con eso el dashboard mostrará automáticamente el IC95 «clave» y «combinado» y el ICC/W de Kendall
   que se añada en `quality`.

## Agregar otro método

Crear una clase que herede de `BaseKey`, llene `self.matrix[node_id]` (alternativas × 9 dimensiones),
opcionalmente `replicates` y `quality`, y registrarla en `load_key`. La interfaz no requiere cambios:
la etiqueta del método se toma de `methods.<metodo>.label`.

## Pendientes de validación (Investigación)

- Agregación entre expertos y regla de empate.
- Mapeo dimensión → estilo y pesos (hoy iguales).
- Comparabilidad entre estilos (hoy: promedio de puntos por dimensión).
- Tratamiento de nodos sin contraste o sin discriminación (hoy: se informan, no se excluyen; `profile.excluded_nodes` permite excluirlos).
- Dependencia entre nodos de una misma secuencia en el bootstrap (IC posiblemente optimistas).
