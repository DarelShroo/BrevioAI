# Migration: Job lifecycle FASE 2 (non-destructive)

Idempotent indexes created via `FolderEntryRepository.ensure_indexes()`
on first admit/idempotency lookup (and library folder flows that already
call `ensure_indexes`).

New fields on `entries` (all optional / backward compatible):

- `status` (`QUEUED` | `PROCESSING` | `COMPLETED` | `FAILED`)
- `queued_at`, `claimed_at`, `enqueued_at`, `heartbeat_at`
- `idempotency_key` (sparse unique with `user_id`)
- `file_manifest` (list of `{index, filename, relative_path}`)
- `job_payload` (YouTube request snapshot)
- `transcription_provider`, `transcription_model`, `reasoning_effort`
- `enqueue_attempts`

Legacy documents without `status` continue to work: DataResult-level
status remains the UI source of truth for older rows.

No data deletion is performed.
