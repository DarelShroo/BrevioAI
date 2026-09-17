"""Persisted summary job status and logical phase.

PipelinePhase remains the in-process state machine (MAP_RUNNING, MAP_FAILED, …).
These values are what Mongo stores so clients can ask: finished? ok? which stage?

Job-level and DataResult-level status share this enum. Billing states
(RESERVED/SETTLED) must NOT be added here — they belong to later phases.
"""

from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobPhase(str, Enum):
    QUEUED = "QUEUED"
    TRANSCRIBING = "TRANSCRIBING"
    TRANSCRIBED = "TRANSCRIBED"
    DIRECT = "DIRECT"
    MAP = "MAP"
    REDUCE = "REDUCE"
    FORMAT = "FORMAT"
    FINALIZING = "FINALIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


_TERMINAL = frozenset({JobStatus.COMPLETED.value, JobStatus.FAILED.value})
_OPEN = frozenset(
    {
        JobStatus.QUEUED.value,
        JobStatus.PROCESSING.value,
    }
)


def can_transition_status(current: str | None, new: str) -> bool:
    """Idempotent terminal writes; never demote COMPLETED/FAILED.

    Allowed:
      None → QUEUED | PROCESSING | COMPLETED | FAILED
      QUEUED → PROCESSING | FAILED | QUEUED (idempotent)
      PROCESSING → COMPLETED | FAILED | PROCESSING (idempotent)
      COMPLETED → COMPLETED only
      FAILED → FAILED only
    """
    if current == new:
        return True
    if not current:
        return True
    if current in _TERMINAL:
        return False
    if current == JobStatus.QUEUED.value:
        return new in {
            JobStatus.PROCESSING.value,
            JobStatus.FAILED.value,
            JobStatus.QUEUED.value,
        }
    if current == JobStatus.PROCESSING.value:
        return new in {
            JobStatus.COMPLETED.value,
            JobStatus.FAILED.value,
            JobStatus.PROCESSING.value,
            # FASE 6: yield capacity before work starts (rare safety path).
            JobStatus.QUEUED.value,
        }
    # Unknown legacy values: allow only identical or terminal promotion.
    if new in _TERMINAL or new in _OPEN:
        return True
    return False
