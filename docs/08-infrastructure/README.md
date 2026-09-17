# 08 - Infraestructura y Despliegue (Infrastructure)

## Visión General

BrevioAI está diseñado para ser agnóstico del proveedor de la nube (Cloud-Agnostic). Todo el stack se empaqueta y distribuye utilizando Docker y Docker Compose, asegurando que el entorno de desarrollo sea idéntico al de producción.

### Componentes del Stack

La infraestructura completa consta de 7 contenedores interconectados:

1.  **`frontend`:** Contenedor basado en Nginx que sirve los archivos estáticos de Vue 3 construidos previamente y actúa como reverse-proxy para la API.
2.  **`backend`:** Instancia de Uvicorn (FastAPI) sirviendo la API REST de Python síncrona/asíncrona.
3.  **`celery`:** Worker(s) dedicado(s) al procesamiento de resúmenes (Map/Reduce y llamadas al LLM).
4.  **`celery-beat`:** Planificador (Scheduler) que lanza tareas periódicas (ej. limpieza de reservas expiradas, `CreditService.reconcile_expired_reservations`).
5.  **`database`:** Base de datos NoSQL MongoDB.
6.  **`redis`:** Almacenamiento en memoria ultrarrápido para Celery y mitigación de abusos.
7.  **`data-init`:** Contenedor efímero (busybox) que inicializa y asegura los permisos de lectura/escritura de los volúmenes del Host antes de que el Backend arranque.

### Sub-módulos

*   [Gestión de Contenedores (Docker)](docker.md)
*   [Redes y Seguridad (Networking)](networking.md)
