# Migración FASE 5 — Planes + Product Limits + PlanSnapshot

## Objetivo

Separar **créditos** (FASE 3/4) de **límites de producto** (documentos, páginas, bytes, concurrencia, flags media/youtube, modelos financiados).

## Fuente de planes

Archivo único (no hardcodear ramas `if plan == "PRO"`):

- `core/brevio/config/commercial_plans.yaml`
- Override opcional: `COMMERCIAL_PLANS_PATH`

Planes iniciales: `free`, `pro`, `business` (sin precios Stripe; ver `docs/PLANS_AND_BILLING.md`).

Catálogo HTTP (solo lectura): `GET /plans` → límites del YAML + `checkout_enabled=false`.

## Periodos

- Modo por defecto: `calendar_month` (UTC: `period_start` = día 1 00:00, `period_end` = día 1 del mes siguiente).
- Alternativa configurable: `rolling_days` vía YAML (`period_mode` / `rolling_days`).
- Cambiar el modo no requiere reescribir el servicio de límites; solo la abstracción `current_period_bounds()`.

## Política de cambio de plan

YAML: `plan_change_usage_policy: keep_period_counters`

- Al cambiar `User.plan_id` / `plan_version`, los **Jobs futuros** usan el plan nuevo.
- Los Jobs ya admitidos conservan `FolderEntry.plan_snapshot` + `ProductUsageRecord.snapshot` inmutables.
- Los contadores del periodo (`documents_used`, `pages_used`, `bytes_used`, `credits_used`) **se mantienen** en el mismo periodo; no se reinician automáticamente ni se inventa prorrateo monetario.
- `credits_used` solo crece con settlement real (no con reserva).

## Migración de usuarios

- `User.plan_id` default `"free"`, `plan_version` `"1"`.
- Usuarios sin `plan_id` se migran lazy en `ensure_user_plan` / `/users/me` → `default_plan_id` del YAML.
- **No** se altera `CreditAccount.balance`.

## Colecciones Mongo

| Colección | Uso |
| --- | --- |
| `product_period_usage` | Contadores por `(user_id, period_start, period_end)` — unique |
| `product_usage_records` | Consumo idempotente por `job_id` — unique |

Índices: ver `plan_repositories.ensure_indexes`.

## Admission

```
AUTH → PLAN → PRODUCT LIMITS (atomic reserve) → CREDIT RESERVATION → STORE → QUEUED
```

BYOK: créditos Brevio = 0; product limits aplican igual.

## Rollback

Sin migración destructiva. Desactivar comprobaciones requeriría revertir wiring en `brevio_service` / router YouTube; los campos `plan_*` en User son aditivos.
