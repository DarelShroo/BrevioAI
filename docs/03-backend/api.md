# API y Endpoints Principales

La API de BrevioAI está dividida en varios enrutadores (`routers`), cada uno enfocado en un dominio específico. A continuación, se documentan los flujos más importantes.

## 1. Generación de Resúmenes (`/brevio`)

### `POST /brevio/summary-documents`
*   **Quién lo utiliza:** Frontend (Pestaña "Documentos").
*   **Entrada:** Archivos binarios (`multipart/form-data`) + Parámetros de configuración (`model`, `language`, `format`, `summary_level`).
*   **Proceso:**
    1.  Verifica los rate limits (Redis).
    2.  Verifica extensiones y tamaño.
    3.  Calcula los costes y verifica/reserva el saldo del usuario (`Preflight` + Admisión Comercial).
    4.  Guarda los archivos en disco/almacenamiento.
    5.  Crea el registro en MongoDB (`FolderEntry`).
    6.  Encola el trabajo vía el Fair Scheduler (`process_summary_task.delay`).
*   **Salida (202 Accepted):** `task_id` y `job_id`.

### `POST /brevio/estimate-documents`
*   **Quién lo utiliza:** Frontend (Botón "Estimar").
*   **Entrada:** Archivos y parámetros (similar al anterior).
*   **Proceso:**
    1.  Extrae texto de forma rápida en memoria.
    2.  Cuenta los tokens de entrada usando `tiktoken`.
    3.  Proyecta el consumo máximo de salida dependiendo del nivel de resumen.
    4.  Simula el coste en créditos de acuerdo al plan del usuario.
*   **Salida (200 OK):** Desglose detallado de tokens, coste estimado, y si se requiere o no chunking.
*   **Nota Crítica:** No consume saldo, no llama a LLMs externos.

## 2. Eventos en Tiempo Real (`/events`)

### `GET /events/stream`
*   **Quién lo utiliza:** Frontend (EventSource para SSE).
*   **Entrada:** Token JWT.
*   **Proceso:**
    1.  Establece una conexión HTTP persistente.
    2.  Se suscribe a un canal de Redis (`user_{id}_events`).
    3.  A medida que los workers de Celery reportan progreso, el servidor emite eventos al cliente.
*   **Salida:** Stream de eventos `text/event-stream`.

## 3. Facturación y Suscripciones (`/plans`)

### `GET /plans/current`
*   **Entrada:** (Autenticado).
*   **Proceso:** Recupera el plan activo del usuario y sus límites (uso consumido vs límite mensual).
*   **Salida:** Detalles del plan y barra de progreso de consumo.

## 4. Autenticación (`/auth`)

### `POST /auth/login`
*   **Entrada:** Correo y contraseña.
*   **Proceso:** Verifica credenciales en MongoDB, emite JWT (Access Token) de corta duración y Refresh Token en cookie HTTP-Only.

## 5. Catálogos y Metadatos (`/brevio/models`, `/brevio/languages`)
*   **Proceso:** Devuelve configuraciones estáticas o cacheadas que el Frontend utiliza para poblar los selectores (dropdowns). Se basan en diccionarios hardcodeados (`ModelType`, `LanguageType`) que actúan como Feature Flags.
