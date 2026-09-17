# Procesamiento Map / Reduce

El patrón Map/Reduce es la solución técnica para resumir textos infinitamente grandes sin superar el contexto del LLM.

## 1. Fase MAP (Mapeo)

*   **Entrada:** Una lista de Chunks de texto.
*   **Proceso:** El sistema lanza múltiples peticiones concurrentes (`asyncio.gather` con control de concurrencia límite) al LLM. Cada petición le dice al LLM: *"Resume este fragmento manteniendo la información clave"*.
*   **Salida:** Una lista de "Sub-Resúmenes" o "MAP Extracts".
*   **Optimizaciones:**
    *   Si el sistema detecta que un chunk es puramente el "Índice" o "Tabla de Contenidos", se descarta inteligentemente sin llamar al LLM (`is_table_of_contents_chunk`), ahorrando tiempo y créditos.
    *   **Control de Presupuesto:** Cada chunk tiene un presupuesto de tokens asignado. Si el LLM se queda sin tokens a mitad de respuesta (`finish_reason="length"`), el sistema implementa una función de salvamento (`_salvage_unsplittable_reduce`) para intentar quedarse con el texto que sí logró escribirse de forma coherente, en lugar de fallar todo el proceso.

## 2. Fase REDUCE (Reducción / Síntesis)

*   **Entrada:** Los "Sub-Resúmenes" generados en la fase MAP.
*   **Proceso:** Se empaquetan (`_pack_reduce_chunks`) tantos sub-resúmenes como quepan dentro de un límite de tokens (conocido como `reduce_batch_tokens`). Se envían al LLM con la instrucción: *"Combina estos resúmenes parciales en un documento único y fluido"*.
*   **Rondas Intermedias (Intermediate Reduce):** Si después del MAP aún tenemos, por ejemplo, 50 sub-resúmenes, no cabrán todos en una sola llamada de REDUCE. El sistema hará "Rondas". Tomará 10, los resumirá en 1; otros 10, los resumirá en 1, etc. Ahora tiene 5. Este proceso iterativo (jerárquico) continúa hasta que queden pocos.
*   **Ronda Final (Final Reduce):** Cuando todos los fragmentos consolidados caben finalmente en un solo paquete, se realiza la síntesis final, aplicando el "Estilo" y "Formato" que el usuario haya solicitado.

## 3. Circuit Breakers (Evitar bucles infinitos)

El código contiene protecciones explícitas (`REDUCE_SPLIT_SAFETY_CAP`, `MAX_INTERMEDIATE_REDUCE_ROUNDS`). Si el modelo LLM, por algún motivo, decide expandir el texto en lugar de resumirlo (haciendo que el resultado del Reduce sea más largo que la entrada), el sistema abortará el trabajo (`ReduceConvergenceError`) para evitar que el proceso se quede atascado en un bucle infinito gastando créditos.
