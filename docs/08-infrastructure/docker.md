# Gestión de Contenedores (Docker)

La orquestación principal ocurre en el archivo `docker-compose.yml`. 
El despliegue está optimizado para garantizar que los contenedores arranquen en el orden correcto y con los permisos adecuados.

## 1. El problema de los Permisos (Host vs Container)

En entornos Docker, los volúmenes montados (bind mounts) desde el sistema operativo anfitrión (Host) hacia el contenedor pueden sufrir problemas de permisos. Si el Backend (que se ejecuta como un usuario sin privilegios, ej. UID 10001) intenta guardar un PDF subido por el usuario en `/app/data`, el sistema operativo lo denegará.

Para solucionar esto de forma automatizada (sin obligar al DevOps a ejecutar comandos manuales `chown`), BrevioAI incluye el servicio **`data-init`**.
Este contenedor arranca como `root`, monta la carpeta compartida, le cambia el dueño a `10001:10001`, y luego muere. El `backend` y `celery` tienen un `depends_on: data-init`, asegurando que no arranquen hasta que la carpeta sea segura para escribir.

## 2. Worker / Beat Separados

En BrevioAI, la tarea de Celery (`celery -A core.brevio_api.celery worker`) y el planificador (`celery -A core.brevio_api.celery beat`) se ejecutan en **contenedores separados**.
*   **Motivo:** Esto permite escalar horizontalmente. Si el sistema necesita más potencia para resumir, se pueden desplegar 5 réplicas del contenedor `celery` (`docker compose up --scale celery=5 -d`), pero debe existir estrictamente **UN SOLO** contenedor `celery-beat` para evitar que las tareas periódicas se disparen por duplicado.

## 3. Limitaciones por Diseño (Soft & Hard Limits)

El comando del worker incluye `--time-limit=7200 --soft-time-limit=3600`.
Esto es una medida de seguridad a nivel de infraestructura: si un resumen se atasca (ej. la API de Anthropic nunca responde, o hay un bucle infinito en el Reduce), el Worker de Celery matará el proceso de forma "suave" (lanzando una excepción `SoftTimeLimitExceeded`) a la hora (3600s). Si a las 2 horas (7200s) el proceso sigue zombi, lo matará a nivel de sistema operativo (`SIGKILL`).
