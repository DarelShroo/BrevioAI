# Planes de Usuario (Plan Registry)

BrevioAI no codifica ("hardcodea") los planes de suscripción directamente en el código de los servicios. Utiliza un registro configurable basado en un archivo YAML (`commercial_plans.yaml`).

## Carga Dinámica (`PlanRegistry`)

El servicio `PlanRegistryConfig` se encarga de leer el archivo YAML en el arranque y cachear las reglas de negocio. Esto permite cambiar los límites de un plan (ej. subir los créditos mensuales del plan PRO) sin tener que recompilar o modificar el código fuente de Python.

### Definición de un Plan (`PlanDefinition`)

Cada plan tiene asociados límites estrictos (`ProductLimitService` los utiliza para evaluar cada petición):

*   `documents_per_period`: Cuántos documentos puede subir al mes/año.
*   `pages_per_document`: Cuántas páginas máximas por documento (o peso).
*   `bytes_per_document`: Límite duro en MB de la subida (FastAPI también valida esto).
*   `credits_per_period`: Cuántos créditos se asignan por ciclo (para calcular el agotamiento del saldo de la suscripción).
*   `max_concurrent_jobs`: Cuántos resúmenes puede lanzar en paralelo. El *Fair Scheduler* usa este número; si es `1`, y el usuario lanza dos, el segundo entra en estado `WAITING` hasta que el primero termine.
*   `brevio_funded_models`: Qué modelos LLM cubre este plan. (Ej. el plan "free" podría no cubrir GPT-4o, requiriendo que el usuario pague por él).
*   `byok_allowed`: Si el usuario puede introducir su propia clave de API de OpenAI/Anthropic.

## Asignación por Defecto

Si un usuario en MongoDB no tiene un plan asignado (`plan_id` nulo o vacío), la API (`BrevioService.ensure_user_plan`) le asignará automáticamente de forma silenciosa el plan definido como `default_plan_id` (normalmente `free`).
