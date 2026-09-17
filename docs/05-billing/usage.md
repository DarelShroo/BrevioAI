# Registro de Uso (Usage Service)

El `UsageBillingService` es el encargado de trazar hasta el nivel más bajo (el request HTTP físico) qué ha hecho el sistema y registrarlo. Esto es vital para auditorías y para entender cómo gasta el dinero el algoritmo de Map/Reduce.

## 1. `UsageRecord` y `CostRecord`

Cada trabajo (`job_id`) genera al terminar un volcado de métricas de uso:

*   **`CostRecord`:** Representa una transacción atómica contra el proveedor. Cada llamada física a la API de OpenAI (ej. procesando el Chunk 3 del MAP) genera un `CostRecord` detallando tokens de entrada, salida, fase, duración y coste exacto en dólares según el modelo.
*   **`UsageRecord`:** Es la agregación a nivel de trabajo de todos los `CostRecords`. Resume cuánto costó el trabajo entero, diferenciando entre coste físico (lo que paga la empresa al proveedor) y coste de facturación (lo que paga el usuario en créditos).

## 2. Reconciliación

¿Qué pasa si Celery crashea o el servidor se reinicia a la mitad de un resumen? La reserva de créditos del usuario se quedaría bloqueada para siempre.

Para evitar esto, `CreditService.reconcile_expired_reservations` se ejecuta como una tarea periódica de limpieza.
Busca reservas que lleven en estado `PENDING` más del tiempo máximo permitido (ej. 6 horas). Si el trabajo ya no está en `PROCESSING`, asienta los tokens consumidos hasta el momento del crash (leyendo los `CostRecords` parciales guardados) y devuelve el resto del dinero al usuario, liberando el estado inconsistente.
