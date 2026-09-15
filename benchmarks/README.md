# Benchmark de resúmenes Brevio

El harness vive en `benchmarks/summary_pipeline/`. No usa `overall` heurístico
como calidad. Un job entra en el ranking solo si su estado es `VALID`.

## Qué responde

¿Hay evidencia comparable de que esta versión produce mejores resúmenes, sin
perder fidelidad, cobertura o robustez, y con un coste conocido?

Decisiones: `KEEP` / `REVERT` / `INCONCLUSIVE` / `INVALID`.

## Ejecutar

Desde la raíz del repositorio, con API y Celery ya levantados:

```text
python benchmark.py --suite matrix --iteration iteration_010_matrix
```

Opciones útiles:

* `--resume` reutiliza un job solo si el `experiment_fingerprint` coincide
  (git, código del benchmark, prompts, gold, dataset, matriz, modelo, contexto, juez).
* `--baseline path/to/iteration.json` compara y escribe KEEP/REVERT/INCONCLUSIVE.
* `--judge-model` está desactivado por defecto. No uses el mismo modelo que el generador.
* `--rescore path/to/iteration.json` reevalúa artefactos y escribe `*_rescored.json`.
  Nunca promociona `results/latest.json`.

Salida:

* `benchmark/iterations/<id>.json` siempre
* `benchmark/results/last_run.json` siempre
* `benchmark/results/latest.json` **solo** si `valid_for_comparison=true`

## Matriz

`document × model × idioma nativo × level × category × style`

La suite `matrix` usa las mismas celdas para cada documento
(`very_concise|moderate|very_detailed` × `education` × `guide`).
La traducción es un caso aparte: `--suite single --language english`.

Dos iteraciones solo son comparables si `SET(cells_A) == SET(cells_B)` y
coinciden scorer, dataset y matriz.

## Evaluación

1. Validación de job (artefacto, runtime, telemetría, idioma, chatbot, truncación)
2. Lint heurístico (formato, copia, señales de chatbot) — no es calidad
3. Claims contra el source
4. Gold facts por documento (`dataset/gold/`); si no hay gold, `gold_coverage=unavailable`
5. Agregación estratificada (un documento no domina la media)
6. Coste: telemetría ausente → `null`, nunca `0`

## Runtime (H1)

Si `requested_context != effective_loaded_context_length` el job es
`INVALID_RUNTIME` y no entra en el ranking.

H1 está **confirmada** como modo de fallo histórico (`effective=4096` con
petición 16384). El proceso actual de Ollama debe medirse en cada iteración.

## Caso asyncio (H2)

El artefacto real de `6aa8359c7fdf55f93dee04c0` es un menú de chatbot
(`¿Qué necesitas?`). La deriva aparece en REDUCE L2, no en el MAP de la
cubierta. El fixture `tests/benchmarks/fixtures/asyncio_chatbot.md` debe
clasificarse como `CHATBOT_OUTPUT`, nunca PASS.

## Tests

```text
pytest tests/benchmarks -q
```

Incluyen la suite de sabotaje (vacío, chatbot, copia, alucinación, idioma,
cortos/largos, contradicción, level, telemetría, runtime, matriz, fingerprint,
scorer) y el fail-closed de `latest.json`.
