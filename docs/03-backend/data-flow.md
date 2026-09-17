# Flujo de Datos Interno

Este diagrama muestra cómo fluye la información dentro de las capas del backend desde que se recibe una petición HTTP hasta que un trabajo es despachado al Worker de Celery.

```mermaid
sequenceDiagram
    participant Frontend
    participant FastAPIRouter as FastAPI Router
    participant AntiAbuse as Rate Limiter (Redis)
    participant Estimation as Estimation Service
    participant Billing as Billing & Credits
    participant Mongo as MongoDB
    participant Scheduler as Fair Scheduler
    participant Celery as Celery Queue

    Frontend->>FastAPIRouter: POST /brevio/summary-documents (Archivos + Params)
    
    %% 1. Anti-Abuse
    FastAPIRouter->>AntiAbuse: Check limits (IP/User)
    alt Límite excedido
        AntiAbuse-->>FastAPIRouter: Rate Limit Exceeded
        FastAPIRouter-->>Frontend: HTTP 429 Too Many Requests
    end
    
    %% 2. Estimación y Admisión Comercial
    FastAPIRouter->>Estimation: estimate(files, params)
    Estimation-->>FastAPIRouter: tokens_estimados, chunks_estimados
    
    FastAPIRouter->>Billing: admit(user, model, coste_estimado)
    Billing->>Mongo: Bloquear Créditos (Reserva Temporal)
    alt Sin saldo
        Billing-->>FastAPIRouter: Error de Fondos
        FastAPIRouter-->>Frontend: HTTP 402 Payment Required
    end
    Billing-->>FastAPIRouter: Admisión OK
    
    %% 3. Almacenamiento
    FastAPIRouter->>Mongo: Crear FolderEntry (Status: QUEUED)
    
    %% 4. Fair Scheduler
    FastAPIRouter->>Scheduler: Registrar Trabajo (Redis)
    Scheduler->>Scheduler: Evaluar capacidad global y del usuario
    alt Capacidad Disponible
        Scheduler->>Celery: process_summary_task.delay(job_id)
        Scheduler-->>FastAPIRouter: Dispatched
    else Infraestructura Llena
        Scheduler-->>FastAPIRouter: En Espera (Waiting)
    end
    
    FastAPIRouter-->>Frontend: HTTP 202 Accepted (job_id)
```

## Persistencia vs Volatilidad

*   **Base de Datos (MongoDB):** Fuente de la verdad absoluta. Si Redis se borra accidentalmente, los trabajos en estado `PROCESSING` o `QUEUED` en Mongo no se pierden, aunque podrían necesitar una intervención manual o un script de reconciliación para volver a encolarlos en Celery.
*   **Caché (Redis):** Es totalmente volátil y efímero. Se asume que cualquier registro aquí tiene un TTL (Time To Live). Guarda las reservas temporales (inflight requests), rate limits y el estado temporal de SSE.
