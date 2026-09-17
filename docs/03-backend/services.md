# Servicios Core (Capa Lógica)

El backend de BrevioAI organiza la lógica de negocio en la capa de servicios (`services/`).

## 1. `BrevioService`
Es el orquestador principal del proceso de generación desde el punto de vista de la API.

*   **`admit_summary_job_with_files`:** Recibe los archivos, verifica la admisión comercial (créditos), guarda el estado incial en base de datos (`QUEUED`) y maneja la idempotencia (evitar trabajos duplicados por reintentos de red).
*   **`reserve_credits_for_admitted_job`:** Estima el coste del trabajo, determina el modo de facturación (BYOK o Plataforma) y bloquea el saldo en MongoDB atómicamente.
*   **`settle_job_credits`:** Invocado cuando un trabajo finaliza (con éxito o error). Libera la reserva y asienta el consumo real extraído del uso real del proveedor LLM.
*   **`dispatch_waiting_jobs`:** Se comunica con el *Fair Scheduler* para desencolar trabajos y pasarlos efectivamente a Celery (`process_summary_task.delay`).

## 2. Servicios de Capacidad (`capacity/`)

Previenen el colapso de la plataforma cuando hay picos masivos de trabajos.

*   **`FairScheduler`:** Cuando llegan muchos trabajos, no se envían todos a Celery de golpe. El Scheduler gestiona una "sala de espera" distribuida mediante Redis, asegurando que:
    1.  El sistema en global no supere un máximo de trabajos simultáneos (`GLOBAL_INFLIGHT_LIMIT`).
    2.  Ningún usuario monopolice los workers (`PER_USER_LIMIT`).

## 3. Servicios Financieros (`billing/`)

Manejan las matemáticas y reglas de negocio del consumo.

*   **`CreditService`:** Gestiona el saldo monetario o virtual del usuario (`CreditAccount`). Usa transacciones (o bloqueos en Redis) para evitar que dos peticiones simultáneas gasten el mismo saldo.
*   **`ProductLimitService`:** Verifica si el plan actual del usuario permite utilizar un modelo en particular (ej. GPT-4o) y si no ha superado límites temporales (ej. trabajos por hora).

## 4. `EstimationService`

*   Responsable de la pre-evaluación algorítmica de los documentos sin usar IA.
*   Extrae páginas (PDF) e invoca utilidades de tokenización (librería `tiktoken`) para contar tokens precisos.
*   Genera un margen de error y simula cuántas llamadas Map/Reduce serán necesarias.

## 5. `AntiAbuse` (Rate Limiters)

*   Utilizan contadores en Redis (`INCR`, `EXPIRE`) para establecer límites duros en el servidor HTTP.
*   Ejemplo: `enforce_job_create_rate_limit` (evita spam de solicitudes de resumen).
*   Si se supera el umbral, devuelve un HTTP 429 (Too Many Requests).
