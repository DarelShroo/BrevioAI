# FASE 8 — Production Hardening + Attack Testing

## 1. Threat model (summary)

| Layer | Threats |
| --- | --- |
| Auth | brute force, OTP grind, refresh race, access after logout |
| AuthZ / IDOR | cross-tenant job/folder/entry/credential access |
| Upload | path traversal, extension spoof, zip bombs |
| SSRF | YouTube/media outbound to internal hosts |
| Billing | double reserve/settle/release, crash between settle insert and refund |
| Product limits | concurrent slot double-release, rolling period key drift |
| Capacity / RL | multi-replica oversubscription, XFF spoof |
| Infra | weak secrets, open docs, published Mongo/Redis, CORS `*` |

## 2. Attacks performed

- Concurrent credit reservation (100×1, balance=50) on real Mongo
- Double settlement / double release / settlement crash recovery
- Capacity acquire 20 vs global=5 on real Redis
- Rate-limit 2 processes × 50 vs limit 50 on real Redis
- Path traversal filename variants
- Magic-byte spoof (`.pdf` shell script)
- YouTube SSRF + unconstrained path
- Production config guards (CORS, TRUSTED_PROXY, weak keys)
- Access JWT denial after logout
- IDOR ownership → uniform 404

## 3–6. Findings → fixes

See report section 3. High-severity items fixed with regression tests in
`core/brevio_api/tests/security/test_attack_fase8.py`.

## 7. Production configuration

Required when `ENVIRONMENT=production`:

- strong `API_KEY` (≥24), `SECRET_TOKEN_KEY` (≥32)
- `CREDENTIAL_ENCRYPTION_KEY`
- explicit `CORS_ORIGINS` (no `*`)
- explicit `TRUSTED_PROXY` (ingress CIDR only; `*` refused)
- `COOKIE_SECURE` inferred true unless overridden
- OpenAPI/`/docs` disabled unless `EXPOSE_API_DOCS=true`

## 8. Redis failure modes

| Subsystem | Mode | Reason |
| --- | --- | --- |
| Rate limit (expensive) | fail-closed | prevent unlimited abuse |
| Account mutation RL | fail-open | availability for profile edits |
| Access revoke check | fail-open | Redis outage must not lock all users; refresh still revoked in Mongo |
| Capacity / scheduler | unavailable reason | do not admit without slots |
| Billing balance | N/A | Mongo authority |

## 9. Mongo failure modes

Admit/reserve/settle fail closed on write errors. Unique indexes on
`job_id` (reservation, settlement, product usage) prevent double commercial
effects. Indexes ensured at API startup.

## 10. Celery failure modes

FASE 2 reconciler + capacity lease TTL recover orphan PROCESSING/QUEUED.
Duplicate task delivery is idempotent via job status CAS + settlement unique.

## 11–13. Invariants

- `balance >= 0` (atomic `$gte` debit)
- `settlements(job_id) <= 1`
- `reservation(job_id) <= 1`
- capacity holders ≤ global/user max (Lua)
- rate-limit counters shared across processes (Lua)
- BYOK still subject to product + rate + capacity limits

## 14. Dependencies

- `npm audit --omit=dev`: 0 vulnerabilities (FASE 8)
- `pip-audit` (P0): **executed** against Python 3.12 production install of `core/requirements.txt`
  - See `docs/DEPENDENCY_SECURITY.md`
  - Status: `DEPENDENCY SECURITY VERIFICATION: FINDINGS PRESENT`
  - Remaining: `starlette` (needs FastAPI bump); `transformers` removed from prod requirements

## Residual risks

- Redis without `requirepass` on `app_network` (sibling container risk) → **addressed in P0** via ACL when `REDIS_PASSWORD` is set
- yt-dlp may still follow YouTube CDN redirects (host allowlist + path constraint; no DNS pin)
- Overrun policy default `clamp` can undercharge platform vs provider spend
- Product `credits_hold=1` is coarse vs real CreditAccount consume
- Access revoke check fails open if Redis is down
- Dependency findings remain for `starlette` (see `docs/DEPENDENCY_SECURITY.md`); HF/transformers no longer in prod
- External CDN/LB CIDRs for `TRUSTED_PROXY` are not knowable from this repo alone

## Status legend used in findings

- **fixed** — code change + regression test
- **tested** — attack covered, already safe
- **residual** — real remaining risk
- **not tested** — out of controlled scope (full DNS rebinding, destructive DoS)
