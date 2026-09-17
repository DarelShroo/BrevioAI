# Ciclo de Vida de un Trabajo (Job Lifecycle)

El procesamiento de un resumen desde que el Worker de Celery lo toma hasta que termina pasa por una **Máquina de Estados Finita** (FSM) controlada por `DocumentPipelineState`.

## Fases del Pipeline (`PipelinePhase`)

1.  **QUEUED / INITIALIZING**: El Worker acaba de tomar el trabajo. Lee los metadatos de MongoDB y prepara el cliente API (OpenAI/Anthropic).
2.  **DIRECT_RUNNING**: Ocurre si el documento es lo suficientemente corto como para caber en una sola llamada (single-pass). No se hace map-reduce.
    *   *Transiciones:* `SUCCESS`, `DIRECT_FAILED`.
3.  **MAP_RUNNING**: El documento es grande. Se divide en fragmentos (Chunks) y se llama a la IA para resumir cada uno en paralelo.
    *   *Transiciones:* `MAP_COMPLETED`, `MAP_FAILED`.
4.  **REDUCE_RUNNING**: Se toman todos los resúmenes del paso MAP y se combinan (sintetizan). Si el resultado sigue siendo muy grande, se hace en múltiples rondas intermedias.
    *   *Transiciones:* `REDUCE_COMPLETED`, `REDUCE_FAILED`.
5.  **FORMAT_RUNNING** (Opcional): Si está habilitado (`BREVIO_ENABLE_FORMAT_PHASE`), se hace una pasada final para asegurar que el Markdown/estilo es perfecto.
6.  **FINALIZING / SUCCESS**: El documento de Markdown se da por válido. Se generan los exportables (PDF, DOCX) y se guarda el `DataResult` como exitoso.

## Artefactos Temporales (`SummaryArtifactManager`)

BrevioAI nunca guarda todo el texto en la RAM al mismo tiempo para no ahogar al servidor. Utiliza archivos temporales en disco:

*   `summary.md.partial`: Guarda los resultados parciales a medida que ocurren.
*   `summary.md`: El archivo final que se entrega al usuario. Solo se crea mediante un renombrado atómico una vez el Pipeline reporta `SUCCESS`.

## Fallos y Recuperación

Si una petición a la API falla (ej. *RateLimitError*), el sistema utiliza la librería `tenacity` o un control manual de reintentos (`provider_executor.execute`). Si el error es insalvable (ej. el texto es basura incomprensible), el trabajo se marca como `FAILED` con la sub-fase en la que ocurrió (ej. `MAP_FAILED`).
