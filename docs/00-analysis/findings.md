# Hallazgos e Inconsistencias

Durante el análisis del código de BrevioAI, se han encontrado las siguientes inconsistencias o diferencias entre el comportamiento real y lo que podría esperarse o estar documentado previamente. Este documento sirve como registro vivo durante el proceso de auditoría y documentación.

## 1. Arquitectura de Billing y Límites (Fases 5, 6 y 7)

El código muestra una evolución reciente y compleja en el sistema de gestión de cuotas y ejecución (referenciado en comentarios internos como "FASE 5", "FASE 6", "FASE 7").

*   **Comportamiento Real:** Existe un "Fair Scheduler" (`FairScheduler` en `capacity_store.py`) que intermedia antes de enviar los trabajos a Celery. La admisión comercial (`ProductLimitService.admit`) ocurre **antes** de que el documento se inserte definitivamente en MongoDB como un trabajo, para evitar llenado de base de datos con trabajos fallidos (spam de fallos).
*   **Inconsistencia:** Posibles documentos antiguos de arquitectura sugerían que un trabajo se guardaba, se encolaba en Celery directamente (`.delay()`), y luego Celery comprobaba el saldo. Ahora el flujo es más seguro: *Estimación -> Admisión Comercial (Reserva) -> Guardado MongoDB -> Fair Scheduler -> Celery Dispatch*.

## 2. Gestión Idempotente de Trabajos

*   **Comportamiento Real:** `BrevioService.admit_summary_job_with_files` utiliza un `idempotency_key` provisto por el frontend/cliente. Si una petición se repite (ej. error de red), el sistema intercepta la clave, evita descontar créditos por duplicado y devuelve el `job_id` previamente creado.
*   **Relevancia:** Esta es una defensa robusta contra abusos de red o errores de UX que no suele estar bien documentada.

## 3. Asignación de Plan por Defecto

*   **Comportamiento Real:** En `BrevioService.ensure_user_plan`, si un usuario no tiene un `plan_id` asignado en MongoDB, el sistema le asigna **silenciosamente** el plan `free` por defecto sin tocar la contabilidad subyacente de `CreditAccount` hasta que haya consumo.
*   **Relevancia:** Asegura retrocompatibilidad con cuentas antiguas, pero implica que la base de datos puede estar mutando su estado pasivamente en operaciones de lectura.

## 4. Bring Your Own Key (BYOK) y Estimaciones

*   **Comportamiento Real:** El sistema diferencia estrictamente el coste estimado en créditos dependiendo de si el usuario aporta su propia clave API. Si es BYOK, `CreditService.resolve_billing_mode` puede alterar el coste (típicamente cobrando 0 o una tarifa plana muy reducida por uso de infraestructura, en vez del coste por token de OpenAI/Anthropic).
