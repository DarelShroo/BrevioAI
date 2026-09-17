# 05 - Sistema de Billing y Planes

## Visión General

El sistema de facturación y límites (conocido como *Billing* o *Fase 3/5/6*) es uno de los componentes más críticos y robustos de BrevioAI. Su objetivo principal es proteger la infraestructura de la empresa frente a abusos, controlar los gastos de la API de proveedores externos (OpenAI, Anthropic), y monetizar el uso.

### Principios Fundamentales del Billing

1.  **Fail-Closed (Cierre por defecto):** Si la base de datos no responde, o hay un error calculando el coste, el sistema rechaza el trabajo (`HTTP 402 Payment Required` o `503 Service Unavailable`). Nunca permite ejecuciones gratuitas por fallo del sistema.
2.  **Inmutabilidad (Ledger):** Todos los movimientos de créditos (reservas, consumos, devoluciones) se registran en un libro mayor (`CreditLedgerEntry`) inmutable.
3.  **Idempotencia:** Las operaciones de reserva y asentamiento (settlement) están diseñadas para ejecutarse de forma segura varias veces (por reintentos de red o caídas de Celery) sin cobrarle al usuario dos veces por el mismo trabajo.
4.  **Consumo Preciso:** A los usuarios se les cobra por el uso real (tokens), no por el uso estimado.

### Sub-módulos

*   [Planes de Usuario](plans.md)
*   [Créditos y Libro Mayor (Ledger)](credits.md)
*   [Cálculo de Costes](cost-calculation.md)
*   [Registro de Uso (Usage)](usage.md)
*   [Bring Your Own Key (BYOK)](byok.md)
*   [Límites de Producto (Anti-Abuso)](limits.md)
