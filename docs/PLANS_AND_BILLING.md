# Plans, limits, credits, and billing (current architecture)

Source of truth for commercial **product limits** is:

`core/brevio/config/commercial_plans.yaml`

(optional override: `COMMERCIAL_PLANS_PATH`)

## Architecture (as implemented)

```text
commercial_plans.yaml
        ↓
PlanRegistry (plan_registry.py)
        ↓
User.plan_id / plan_version  ──► ProductLimitService.admit
        ↓                              ↓
CreditAccount.balance          PlanSnapshot on FolderEntry
(+ period grant / rollover)            ↓
        ↓                      product_period_usage counters
CreditService.reserve/settle
        ↓
Fair scheduler (weight/priority from plan)
        ↓
Frontend /plans + /users/me entitlements
```

## Commercial contract (mandatory)

| Limit | FREE | PRO | BUSINESS |
| --- | ---: | ---: | ---: |
| Credits / period | 100 | 4.000 | 20.000 |
| Rollover max | 200 | 8.000 | 40.000 |
| Documents / period | 10 | 100 | 500 |
| Pages / document | 200 | 1.000 | 5.000 |
| Pages / period | 1.000 | 10.000 | 50.000 |
| Document size | 25 MiB | 100 MiB | 500 MiB |
| Audio size | 50 MiB | 250 MiB | 1 GiB |
| Video size | 250 MiB | 2 GiB | 10 GiB |
| Concurrent jobs | 5 | 20 | 50 |
| BYOK | yes | yes | yes |

Do **not** change these values to make tests pass. Fix the implementation instead.

## Period renewal and rollover

On each period grant (calendar for Free; Stripe `invoice.paid` for paid):

```text
final_balance = min(current_balance + credits_per_period, rollover_max)
```

Grants are idempotent (`last_period_grant_key` / ledger `period_grant_key`).

## Stripe

Price IDs come from env (`STRIPE_PRICE_PRO_*`, `STRIPE_PRICE_BUSINESS_*`).
Unknown Price IDs must not grant a plan or credits.

## Infrastructure ceilings

Nginx `client_max_body_size` and upload defaults must allow Business video (10 GiB).
Commercial plan checks still enforce per-plan caps after the file is received.

## BYOK

All plans allow BYOK. BYOK does **not** bypass documents/pages/bytes/concurrency/credit quotas.
