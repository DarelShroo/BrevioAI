# Cálculo de Costes y Control (Nivel Summary)

El Motor de Summary y el Sistema de Billing están desacoplados pero se comunican a través de los metadatos de tokens.

## 1. La Transacción de Resumen

1.  **Presupuesto (Budget):** El `SummaryService` no manipula saldos de base de datos directamente (eso lo hace Billing en la Fase 3 y 8). Sin embargo, el Service recibe un `JobRequestBudget` asociado a las iteraciones (cuántas llamadas físicas a OpenAI puede hacer).
2.  **Ejecución y Conteo Físico:** Durante las llamadas al LLM, la API del proveedor devuelve cuántos `prompt_tokens` y `completion_tokens` se consumieron realmente en cada petición individual (cada chunk de MAP y cada ronda de REDUCE).
3.  **`HistoryTokenModel`:** BrevioAI utiliza este modelo en memoria para ir sumando cada token en tiempo real (`total_tokens_summary_input`, `total_tokens_summary_output`).
4.  **Asentamiento (Settlement):** Cuando el pipeline de `SummaryService` termina, reporta el total neto de tokens consumidos. El Backend llama a `settle_job_credits`, quien toma los tokens, busca los precios en dólares (o créditos) en la tabla de `PricingRegistry` correspondiente al modelo (ej. GPT-4o), calcula el coste en créditos de plataforma, y cobra al usuario.

## 2. Prevención de Costes Infinitos (Circuit Breakers)

Para evitar que un documento "buggeado" haga que el LLM empiece a alucinar texto infinito y gastar miles de dólares:

*   **Capacidad por Tarea (`max_tokens` restrictivo):** Ninguna llamada al LLM se hace sin un `max_tokens` ajustado (calculado en funciones como `_map_completion_token_limit`).
*   **Fallo Rápido (Fail Fast):** Si el LLM no es capaz de resumir un texto (el texto generado es más largo que el de entrada en un REDUCE), salta el error `ReduceConvergenceError`.
*   **Limitación de Rondas:** Existen límites duros de cuántas rondas de reducción se pueden hacer (`MAX_INTERMEDIATE_REDUCE_ROUNDS`, `MAX_FINAL_REDUCE_ROUNDS`).

## 3. Backpressure Local (Tokens Per Minute - TPM)

Para no ser baneados por el proveedor (ej. HTTP 429 de OpenAI), BrevioAI simula localmente un `token_bucket`. Cada instancia del Worker tiene asignado un límite (ej. 150,000 TPM).
Si el motor intenta mandar un Chunk de 100,000 tokens pero solo le quedan 50,000 en el bucket local, esperará (`asyncio.sleep(5)`) y volverá a comprobar, logrando un caudal constante sin errores de la API externa.
