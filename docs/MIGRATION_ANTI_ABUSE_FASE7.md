# Migración FASE 7 — Rate limiting distribuido + anti-abuse

## Arquitectura

```
HTTP
 ↓ auth (si aplica)
 ↓ anti-abuse cooldown + Redis rate limit (IP / user / bucket)
 ↓ product admission (Mongo)
 ↓ credit reservation (Mongo)
 ↓ QUEUED + fair wait queue
 ↓ capacity lease → Celery → provider quota → execute
```

Capas independientes:

| Capa | Autoridad | Recurso |
| --- | --- | --- |
| RateLimit | Redis | requests HTTP |
| ProductLimit | Mongo | docs/páginas/bytes periodo |
| CreditReservation | Mongo | saldo créditos |
| CapacityLease | Redis | slots Job |
| ProviderQuota | Redis | RPM/TPM/in-flight |

## Algoritmo

Fixed window atómico (Lua `INCR` + `EXPIRE` en la misma evaluación).

## Buckets (env)

- `auth_*` — login/register/refresh/OTP (por IP + acción)
- `job_create`, `upload`, `estimation`, `youtube`, `media`
- `account_mutation` — credenciales
- `ip_global` — techo por IP

## Claves Redis

```
antiabuse:rl:{identity}:{bucket}
antiabuse:violations:{subject}
antiabuse:cooldown:{subject}
```

TTL en todas. No se almacenan IPs indefinidamente.

## Trusted proxy

Solo peers en `TRUSTED_PROXY` (CIDRs) pueden aportar `X-Forwarded-For` / `X-Real-IP`.
Sin match → `request.client.host`.

## Fail-safe

- Endpoints caros (`fail_closed=True`): Redis down → deny (429/503).
- `account_mutation` (`fail_closed=False`): Redis down → allow (disponibilidad).

## Cooldown

Tras `ANTI_ABUSE_VIOLATION_THRESHOLD` denegaciones en ventana TTL → cooldown temporal.
No es suspensión permanente de cuenta.

## Planes

Sin `if plan == PRO`. Rate limits son env globales; límites comerciales siguen en YAML/PlanSnapshot.

## BYOK

Rate limits + product + capacity aplican igual (`credits=0` no abre la API).

## Corrección FASE 6

- `GLOBAL_QUEUED` register ahora es Lua atómico (check + ZADD + INCR).
- YouTube: `ProductLimitService.admit` **antes** de insertar `FolderEntry`.

## Idempotency

Misma `Idempotency-Key` → Job existente (FASE 2). Rate limit cuenta requests HTTP; no crea Jobs extra.

## Privacidad

Buckets y violaciones con TTL. No logs de API keys / passwords / documentos.
