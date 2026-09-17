# Modelos y Proveedores

BrevioAI no es un producto atado a OpenAI; utiliza un diseño de registro agnóstico (`SummaryProviderRegistry`) que permite integrar múltiples LLMs (Anthropic, Google, Modelos Locales, etc.).

## 1. El Registro de Proveedores (`SummaryProviderRegistry`)

Este patrón permite añadir un nuevo proveedor simplemente creando una clase que implemente la interfaz necesaria (con el método `complete()`).

*   **OpenAI Provider:** Maneja llamadas a `gpt-3.5-turbo`, `gpt-4o`, `o1-mini`.
*   **Anthropic Provider (Opcional):** Maneja Claude.
*   **Local / Ollama:** El sistema tiene lógicas preparadas (ej. `_completion_timeout_s` detectando `ollama`) para modelos locales, asumiendo tiempos de espera más largos (hasta 600 segundos).

## 2. `ModelCapabilities` (Capacidades Dinámicas)

Para que el motor de `SummaryService` funcione sin importar el modelo, necesita saber las matemáticas de este. Esto se define en `ModelCapabilities`.

Cada modelo tiene una configuración estática (o cacheada) que indica:
*   `context_window`: Cuántos tokens caben (ej. 128,000 para GPT-4o).
*   `max_tokens_per_chunk`: El límite rígido recomendado por chunk de MAP.
*   `reduce_batch_tokens`: Cuántos tokens agrupar en cada ronda de reducción.
*   `reduce_safety_margin`: Un margen de error (ej. 500 tokens) para evitar overflows.
*   `packing_token_multiplier`: Un multiplicador empírico porque los tokenizadores (ej. `tiktoken` vs `cl100k_base`) pueden variar de lo que el proveedor realmente cobra.

## 3. Selección Dinámica en el Frontend (Catálogo)

El Frontend nunca asume qué modelos existen. Llama a la API (`/brevio/models`) y obtiene la lista de modelos "activos". Esto permite al administrador apagar un modelo desde el Backend (ej. porque la API de Anthropic está caída) e inmediatamente dejará de ser una opción para el usuario en toda la plataforma.
