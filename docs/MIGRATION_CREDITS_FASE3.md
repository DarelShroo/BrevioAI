# Migration: Credits FASE 3 (non-destructive)

Idempotent indexes are created via `CreditService.ensure_indexes()` on
first balance/reserve/settle call.

## New collections

- `credit_accounts` — unique `user_id`; `balance: int >= 0`
- `credit_reservations` — unique `job_id`; statuses `PENDING|COMMITTED|RELEASED`
- `credit_ledger` — append-only; sparse unique `(reservation_id, reason)`
- `job_settlements` — unique `job_id`

## Legacy field

`User.user_credit` (float) is **not deleted**. On first `ensure_account(user_id)`:

1. If `CreditAccount` exists → reuse (no double credit).
2. Else create account with `floor(user_credit)` when valid and ≥ 0.
3. Corrupt / negative / NaN values raise and are logged
   (`credit_migration_corrupt` / `credit_migration_negative`).

After FASE 3, `CreditAccount.balance` is the only authority for job admission.

## Guarantees (standalone Mongo)

No multi-document transactions required. Atomic pieces:

- Debit: `find_one_and_update({balance: {$gte: amount}}, {$inc: {balance: -amount}})`
- Reservation uniqueness: unique `job_id` (+ debit refund on loser race)
- Settlement uniqueness: unique `job_id`
- Release: atomic `PENDING → RELEASED|COMMITTED` before crediting

Ledger never updates/deletes rows; corrections are compensating inserts.

## Commercial flow

```
create QUEUED job (job_id)
→ estimate maximum_credits (documents) or default
→ atomic reserve (BYOK/LOCAL amount=0)
→ store files / payload
→ Celery enqueue
→ complete/fail → settle(job_id, consumed)
```

Client-supplied credit amounts are ignored.
