"""Persisted summary job status and logical phase.

PipelinePhase remains the in-process state machine (MAP_RUNNING, MAP_FAILED, …).
These values are what Mongo stores so clients can ask: finished? ok? which stage?
"""

from enum import Enum


class JobStatus(str, Enum):
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


def can_transition_status(current: str | None, new: str) -> bool:
    """Idempotent terminal writes; never demote COMPLETED/FAILED to each other or back to PROCESSING."""
    if not current or current == JobStatus.PROCESSING.value:
        return True
    if current == new:
        return True
    if current in _TERMINAL and new == JobStatus.PROCESSING.value:
        return False
    if current == JobStatus.COMPLETED.value and new == JobStatus.FAILED.value:
        return False
    if current == JobStatus.FAILED.value and new == JobStatus.COMPLETED.value:
        return False
    return True
