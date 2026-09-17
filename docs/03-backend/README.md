# 03 - Backend API

## Visión General

El Backend de BrevioAI está desarrollado en **Python** utilizando el framework **FastAPI**. Actúa como el punto de entrada principal para el cliente web, gestionando la autenticación, la validación de peticiones, la gestión financiera (facturación/créditos) y la delegación de trabajos de IA a la capa de procesamiento asíncrono (Workers).

### Principios Fundamentales del Backend

1.  **FastAPI Asíncrono:** Todas las rutas (endpoints) y el acceso a la base de datos (Motor/MongoDB) y caché (Redis) se realizan de forma no bloqueante (`async/await`).
2.  **Delegación Crítica:** La API en sí **nunca** realiza llamadas pesadas a los LLMs (OpenAI, Anthropic) ni extrae texto de PDFs. Todo trabajo pesado se encola para evitar bloqueos en el hilo principal del servidor HTTP.
3.  **Seguridad por Defecto (Fail-Closed):** Las operaciones de *Billing* y Admisión comercial siempre fallan cerrando el acceso si hay un error en la base de datos o en la caché, protegiendo los recursos económicos de la plataforma.
4.  **Inyección de Dependencias:** FastAPI se utiliza exhaustivamente para inyectar servicios (ej. `BrevioService`, `CreditService`), el usuario actual (`get_current_user`), y validadores (ej. `verify_api_key`) en cada ruta.

### Estructura de Paquetes (`core/`)

El backend está dividido lógicamente en:

*   `core/brevio_api/`: Contiene la lógica exclusiva del servidor HTTP (FastAPI).
    *   `routers/`: Controladores de los endpoints.
    *   `services/`: Lógica de negocio (Billing, Capacidad, JWT, etc.).
    *   `dependencies/`: Componentes inyectables (Auth, DB).
    *   `models/`: Esquemas Pydantic para validación de entrada/salida.
*   `core/brevio/`: Contiene la "Lógica de Dominio" profunda (Generación de IA, Transcripción, Map-Reduce). Es agnóstica de FastAPI y es la que ejecutan mayormente los Workers de Celery.
*   `core/shared/`: Modelos, Enums y utilidades compartidas entre la API y los Workers (ej. configuraciones de Modelos).
