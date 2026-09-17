# Migración FASE 6 — Capacity Admission + Fairness mínima

## Arquitectura (Option A)

```
HTTP admit (product + credits) → QUEUED + Redis wait queue
       ↓
Fair dispatcher (Celery beat + Redis lock)
       ↓ acquire global+user capacity lease
Celery (job_id only) → claim QUEUED→PROCESSING → execute
       ↓
release capacity (idempotent) + settle
```

Celery no se reemplaza. Prefetch multiplier permanece en `1`.

## Capacidad

| Capa | Autoridad | Mecanismo |
| --- | --- | --- |
| Product concurrency | Mongo PlanSnapshot | FASE 5 (cuánto puede) |
| Platform capacity | Redis Lua slots | `GLOBAL_MAX_CONCURRENT_JOBS` + per-user max from snapshot |
| Provider capacity | Redis quota existente | sin cambios |

Leases Redis con TTL; heartbeat de FASE 2 refresca el lease. Worker crash → TTL expira → reconciler/`reclaim_expired_holders`.

## Fairness

Unidad = `user_id`. Política documentada en `fair_scheduler.py`:

1. Elegibles = usuarios con cola + `user_active < max_concurrent_jobs` (snapshot).
2. Cada ciclo: `deficit += scheduler_weight`.
3. Selección: max `(scheduler_priority, deficit, age)`.
4. Priority es soft (no starve Free).

## credits_per_period (fix FASE 5)

Campo atómico `credits_budget` (= used + hold). Admit: `credits_hold=1` en el mismo
`find_one_and_update` que docs/páginas (también aplica cuando el job es BYOK; la
reserva de cartera `CreditAccount` sigue el modo LOCAL/BYOK/PLATFORM en
`CreditService`). Release/settle liberan hold.

## Redis down

Fail-closed: no register / no dispatch / no claim sin lease.

## Rollback

Quitar beat `dispatch-capacity-jobs` y volver a `.delay()` directo; colecciones Redis son efímeras.
