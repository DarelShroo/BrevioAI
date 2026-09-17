# Arquitectura del Sistema

BrevioAI sigue una arquitectura distribuida clásica orientada a microservicios lógicos y procesamiento en segundo plano (Background Processing). 

Aunque el código backend está alojado en un solo repositorio de Python (`core`), en producción se ejecuta separadamente como **Servidores API** (FastAPI) y **Workers Asíncronos** (Celery).

## Diagrama de Arquitectura Global

```mermaid
flowchart TD
    %% Entidades Externas
    User([Usuario / Navegador])
    LLMs([Proveedores LLM<br>OpenAI, Anthropic, etc.])
    Youtube([YouTube API])

    %% Frontend
    subgraph Frontend [Capa de Presentación]
        Vue[Vue 3 SPA<br>Pinia / Vue Router]
    end

    %% Backend API
    subgraph BackendAPI [Capa de Aplicación (FastAPI)]
        Router[Routers<br>Autenticación, Brevio, Billing]
        Services[Services<br>BrevioService, CreditService, etc.]
        Dependencies[Dependencias<br>Validación, API Keys]
        Capacity[Fair Scheduler<br>Gestión de Capacidad]
    end

    %% Message Broker & Cache
    subgraph BrokerCache [Gestión de Estado y Colas]
        Redis[(Redis)]
        Mongo[(MongoDB)]
    end

    %% Workers
    subgraph Workers [Capa de Procesamiento Asíncrono (Celery)]
        Task[Celery Tasks<br>process_summary_task]
        Pipeline[Summary Pipeline<br>Map-Reduce, Chunking]
        Transcriber[Servicio de Transcripción]
    end

    %% Relaciones
    User -->|HTTP / SPA| Vue
    Vue -->|REST API / SSE| Router
    Router --> Dependencies
    Dependencies --> Services
    
    Services -->|Validación / Costes| Mongo
    Services -->|Rate Limits / Admisión| Redis
    Services -->|Encolado (dispatch)| Capacity
    Capacity -->|Encola Trabajo| Redis
    
    Redis -.->|Consume Colas| Task
    
    Task -->|Lee / Escribe Estado| Mongo
    Task --> Pipeline
    Task --> Transcriber
    
    Transcriber -->|Descarga Audio| Youtube
    Pipeline -->|Llamadas API LLM| LLMs
```

## Componentes Principales

### 1. Frontend (Capa de Presentación)
Aplicación Single Page (SPA) desarrollada en **Vue 3**. Utiliza **Pinia** para la gestión del estado local (autenticación, carrito/planes, estado de trabajos en tiempo real mediante *Polling* o *SSE*). Se comunica exclusivamente a través de la API REST del backend.

### 2. Backend API (Capa de Aplicación)
Aplicación web síncrona/asíncrona construida con **FastAPI**.
*   **Responsabilidades:** Autenticación (JWT), validación de archivos (extensiones, peso), estimación preliminar de tokens/costes (sin llamar a la IA), reserva de créditos, y registro del trabajo.
*   **Comportamiento Crítico:** El servidor API **nunca llama directamente a un LLM** para tareas pesadas. Todas las tareas de generación se delegan a la cola asíncrona tras pasar estrictos controles de capacidad (Fair Scheduler).

### 3. Redis (Caché, Rate Limiting y Message Broker)
Redis actúa como la "médula espinal" de la aplicación para operaciones ultrarrápidas y sincronización distribuida.
*   **Broker de Celery:** Transporta los mensajes desde el servidor API hasta los Workers.
*   **Rate Limiting & Anti-Abuso:** Mantiene contadores para evitar que un usuario sature la plataforma haciendo múltiples peticiones por segundo.
*   **Capacity Store (Fairness):** Gestiona bloqueos (locks) y cuotas de concurrencia globales para asegurar que la infraestructura de IA no se sature.

### 4. MongoDB (Fuente de Verdad Persistente)
Almacena todo el estado definitivo del sistema.
*   Usuarios, contraseñas (hasheadas), credenciales BYOK encriptadas, planes activos.
*   `FolderEntries` (Trabajos): El estado persistente de un resumen (Pendiente, Procesando, Completado, Fallido), junto con la configuración del prompt y los enlaces a los archivos resultantes.
*   `CreditAccounts` y `UsageRecords`: Registro contable auditable de cuántos créditos tiene un usuario y en qué se los ha gastado con precisión de tokens.

### 5. Workers Asíncronos (Celery)
Procesos en segundo plano que ejecutan la lógica pesada (el "Core" de Brevio).
*   **Procesamiento:** Leen archivos PDF/DOCX (extraen el texto) o audios/vídeos de YouTube (descargan y transcriben).
*   **Pipeline (Map/Reduce):** Dividen el texto masivo, interactúan repetidamente con los LLMs, calculan el consumo real de tokens y escriben los resultados finales.
*   **Asentamiento (Settlement):** Una vez finalizado el trabajo con éxito o error, asientan la reserva de créditos contra el saldo real del usuario en MongoDB.
