"""Document summary pipeline: states, diagnostics, artifacts, and cancellation."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

import aiofiles

from core.shared.enums.job_status import JobPhase, JobStatus
from core.shared.utils.environment import keep_partials_enabled

logger = logging.getLogger(__name__)


class PipelinePhase(str, Enum):
    QUEUED = "QUEUED"
    INITIALIZING = "INITIALIZING"
    DIRECT_RUNNING = "DIRECT_RUNNING"
    DIRECT_COMPLETED = "DIRECT_COMPLETED"
    DIRECT_FAILED = "DIRECT_FAILED"
    MAP_RUNNING = "MAP_RUNNING"
    MAP_COMPLETED = "MAP_COMPLETED"
    REDUCE_RUNNING = "REDUCE_RUNNING"
    REDUCE_COMPLETED = "REDUCE_COMPLETED"
    FORMAT_RUNNING = "FORMAT_RUNNING"
    FINALIZING = "FINALIZING"
    SUCCESS = "SUCCESS"
    MAP_FAILED = "MAP_FAILED"
    REDUCE_FAILED = "REDUCE_FAILED"
    FORMAT_FAILED = "FORMAT_FAILED"
    CANCELLED = "CANCELLED"
    INVARIANT_FAILED = "INVARIANT_FAILED"
    QUALITY_FAILED = "QUALITY_FAILED"


class PipelineOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED_DIRECT = "FAILED_DIRECT"
    FAILED_MAP = "FAILED_MAP"
    FAILED_REDUCE = "FAILED_REDUCE"
    FAILED_FORMAT = "FAILED_FORMAT"
    FAILED_INVARIANT = "FAILED_INVARIANT"
    CANCELLED = "CANCELLED"
    FAILED_INITIALIZING = "FAILED_INITIALIZING"


PHASE_TO_OUTCOME = {
    PipelinePhase.SUCCESS: PipelineOutcome.SUCCESS,
    PipelinePhase.DIRECT_FAILED: PipelineOutcome.FAILED_DIRECT,
    PipelinePhase.MAP_FAILED: PipelineOutcome.FAILED_MAP,
    PipelinePhase.REDUCE_FAILED: PipelineOutcome.FAILED_REDUCE,
    PipelinePhase.FORMAT_FAILED: PipelineOutcome.FAILED_FORMAT,
    PipelinePhase.INVARIANT_FAILED: PipelineOutcome.FAILED_INVARIANT,
    PipelinePhase.QUALITY_FAILED: PipelineOutcome.FAILED_INVARIANT,
    PipelinePhase.CANCELLED: PipelineOutcome.CANCELLED,
    PipelinePhase.INITIALIZING: PipelineOutcome.FAILED_INITIALIZING,
    PipelinePhase.QUEUED: PipelineOutcome.FAILED_INITIALIZING,
    PipelinePhase.FINALIZING: PipelineOutcome.FAILED_INVARIANT,
}


_PIPELINE_TO_JOB_PHASE = {
    PipelinePhase.QUEUED: JobPhase.QUEUED,
    PipelinePhase.INITIALIZING: JobPhase.QUEUED,
    PipelinePhase.DIRECT_RUNNING: JobPhase.DIRECT,
    PipelinePhase.DIRECT_COMPLETED: JobPhase.DIRECT,
    PipelinePhase.DIRECT_FAILED: JobPhase.DIRECT,
    PipelinePhase.MAP_RUNNING: JobPhase.MAP,
    PipelinePhase.MAP_COMPLETED: JobPhase.MAP,
    PipelinePhase.MAP_FAILED: JobPhase.MAP,
    PipelinePhase.REDUCE_RUNNING: JobPhase.REDUCE,
    PipelinePhase.REDUCE_COMPLETED: JobPhase.REDUCE,
    PipelinePhase.REDUCE_FAILED: JobPhase.REDUCE,
    PipelinePhase.FORMAT_RUNNING: JobPhase.FORMAT,
    PipelinePhase.FORMAT_FAILED: JobPhase.FORMAT,
    PipelinePhase.FINALIZING: JobPhase.FINALIZING,
    PipelinePhase.SUCCESS: JobPhase.COMPLETED,
    PipelinePhase.CANCELLED: JobPhase.FAILED,
    PipelinePhase.INVARIANT_FAILED: JobPhase.FAILED,
    PipelinePhase.QUALITY_FAILED: JobPhase.FAILED,
}


def job_status_for(*, success: bool) -> JobStatus:
    return JobStatus.COMPLETED if success else JobStatus.FAILED


def job_phase_for(phase: PipelinePhase | str, *, success: bool) -> JobPhase:
    if success:
        return JobPhase.COMPLETED
    if isinstance(phase, str):
        try:
            phase = PipelinePhase(phase)
        except ValueError:
            return JobPhase.FAILED
    return _PIPELINE_TO_JOB_PHASE.get(phase, JobPhase.FAILED)


@dataclass
class PipelineDiagnostics:
    phase: str = PipelinePhase.INITIALIZING.value
    error_type: str = ""
    error_message: str = ""
    partial_available: bool = False
    batch_index: Optional[int] = None
    reduce_level: Optional[int] = None
    split_depth: Optional[int] = None
    max_split_depth: Optional[int] = None
    finish_reason: Optional[str] = None
    map_success_count: int = 0
    map_failed_count: int = 0
    input_estimated_tokens: Optional[int] = None
    number_of_chunks: Optional[int] = None
    output_token_limit: Optional[int] = None
    actual_output_tokens: Optional[int] = None
    left_size: Optional[int] = None
    right_size: Optional[int] = None
    left_estimated_tokens: Optional[int] = None
    right_estimated_tokens: Optional[int] = None
    reason: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "phase": self.phase,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "partial_available": self.partial_available,
            "map_success_count": self.map_success_count,
            "map_failed_count": self.map_failed_count,
        }
        optional = (
            "batch_index",
            "reduce_level",
            "split_depth",
            "max_split_depth",
            "finish_reason",
            "input_estimated_tokens",
            "number_of_chunks",
            "output_token_limit",
            "actual_output_tokens",
            "left_size",
            "right_size",
            "left_estimated_tokens",
            "right_estimated_tokens",
            "reason",
        )
        for key in optional:
            value = getattr(self, key)
            if value is not None:
                payload[key] = value
        if self.extra:
            payload.update(self.extra)
        return payload


class PipelineError(Exception):
    """Structured pipeline failure that preserves type, phase, and diagnostics."""

    no_fallback = True
    phase: str = PipelinePhase.INVARIANT_FAILED.value

    def __init__(self, message: str, **diagnostics: Any) -> None:
        super().__init__(message)
        self.diagnostics: Dict[str, Any] = dict(diagnostics)
        for key, value in diagnostics.items():
            setattr(self, key, value)

    def as_diagnostics(self) -> PipelineDiagnostics:
        diag = PipelineDiagnostics(
            phase=self.diagnostics.get("phase", self.phase),
            error_type=type(self).__name__,
            error_message=str(self),
        )
        for key, value in self.diagnostics.items():
            if hasattr(diag, key) and key not in {"extra"}:
                setattr(diag, key, value)
            elif key not in {"phase"}:
                diag.extra[key] = value
        return diag


class ReduceConvergenceError(PipelineError):
    phase = PipelinePhase.REDUCE_FAILED.value


class InvariantViolationError(PipelineError):
    phase = PipelinePhase.INVARIANT_FAILED.value


class ImpossibleRequestError(PipelineError):
    phase = PipelinePhase.REDUCE_FAILED.value


class ContextOverflowError(PipelineError):
    phase = PipelinePhase.MAP_FAILED.value


class MapPhaseFailedError(PipelineError):
    """MAP chunk(s) failed and original_text fallback into REDUCE is disabled."""

    phase = PipelinePhase.MAP_FAILED.value


class ArtifactQualityError(PipelineError):
    """Final artifact failed the quality contract and cannot be COMPLETED."""

    phase = PipelinePhase.QUALITY_FAILED.value


class PipelineDocumentError(Exception):
    """Raised by Generate when a document finishes without SUCCESS."""

    def __init__(self, result: Any, cause: Optional[BaseException] = None) -> None:
        message = getattr(result, "message", None) or str(result)
        super().__init__(message)
        self.result = result
        self.phase = getattr(result, "phase", "")
        self.error_type = getattr(result, "error_type", "")
        self.partial_available = bool(getattr(result, "partial_available", False))
        self.diagnostics = getattr(result, "diagnostics", {}) or {}
        if cause is not None:
            self.__cause__ = cause


class DocumentPipelineState:
    def __init__(self) -> None:
        self.phase = PipelinePhase.INITIALIZING
        self.outcome: Optional[PipelineOutcome] = None
        self.diagnostics = PipelineDiagnostics()
        self.final_committed = False

    def set_phase(self, phase: PipelinePhase) -> None:
        self.phase = phase
        self.diagnostics.phase = phase.value

    def fail(self, phase: PipelinePhase, error: BaseException) -> None:
        self.phase = phase
        self.outcome = PHASE_TO_OUTCOME.get(phase, PipelineOutcome.FAILED_INITIALIZING)
        self.diagnostics.phase = phase.value
        self.diagnostics.error_type = type(error).__name__
        self.diagnostics.error_message = str(error)
        if isinstance(error, PipelineError):
            structured = error.as_diagnostics()
            self.diagnostics.error_type = type(error).__name__
            for key, value in structured.to_dict().items():
                if key in {"error_message"}:
                    continue
                if hasattr(self.diagnostics, key):
                    setattr(self.diagnostics, key, value)
                else:
                    self.diagnostics.extra[key] = value
            self.diagnostics.error_message = str(error)

    def succeed(self) -> None:
        self.phase = PipelinePhase.SUCCESS
        self.outcome = PipelineOutcome.SUCCESS
        self.diagnostics.phase = PipelinePhase.SUCCESS.value
        self.diagnostics.error_type = ""
        self.diagnostics.error_message = ""
        self.final_committed = True


class SummaryArtifactManager:
    """Single owner of summary.md and temporary artifacts for one document job.

    Incremental contract:
      generate fragment → append_partial / replace_partial → drop RAM reference
      … → commit_from_partial (atomic rename) → only summary.md remains

    On disk during a job there is at most ``summary.md.partial`` (plus an optional
    ``.partial.bak``). There is no separate MAP snapshot file.
    """

    def __init__(self, summary_path: str) -> None:
        self.summary_path = summary_path
        self.partial_path = f"{summary_path}.partial"
        self.bak_path = f"{summary_path}.partial.bak"
        self._committed = False
        self._finalized = False
        self._partial_bytes = 0
        self._partial_fragments = 0
        self._partial_started = False

    def _keep_partials(self) -> bool:
        return keep_partials_enabled()

    def temporary_paths(self) -> tuple[str, ...]:
        # Include legacy ``.map.partial`` so old debug snapshots are cleaned up.
        return (
            self.partial_path,
            self.bak_path,
            f"{self.summary_path}.map.partial",
        )

    @property
    def partial_bytes_written(self) -> int:
        return self._partial_bytes

    @property
    def partial_fragment_count(self) -> int:
        return self._partial_fragments

    @staticmethod
    def is_recoverable_text(text: Optional[str]) -> bool:
        return bool(text and str(text).strip())

    async def _ensure_parent(self, path: str) -> None:
        directory = os.path.dirname(path)
        if directory:
            await asyncio.to_thread(os.makedirs, directory, exist_ok=True)

    async def reset_partial(self) -> None:
        """Truncate/create an empty .partial for a new incremental write session."""
        await self._ensure_parent(self.partial_path)

        def _truncate() -> None:
            with open(self.partial_path, "w", encoding="utf-8"):
                pass

        await asyncio.to_thread(_truncate)
        self._partial_bytes = 0
        self._partial_fragments = 0
        self._partial_started = True
        logger.debug("Partial reset at %s", self.partial_path)

    async def append_partial(self, fragment: str, *, separator: str = "\n\n") -> bool:
        """Append one fragment to .partial and return; caller should drop the fragment.

        Memory goal: only the current fragment needs to be alive, not the full summary.
        """
        if not fragment:
            return False
        if not self._partial_started:
            await self.reset_partial()

        payload = fragment
        if self._partial_bytes > 0 and separator and not fragment.startswith(separator):
            # Avoid doubling separators if the fragment already starts with one.
            if separator == "\n\n" and fragment.startswith("\n"):
                payload = fragment
            else:
                payload = separator + fragment

        encoded = payload.encode("utf-8")

        def _append() -> None:
            with open(self.partial_path, "ab") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())

        await asyncio.to_thread(_append)
        self._partial_bytes += len(encoded)
        self._partial_fragments += 1
        logger.debug(
            "Partial append path=%s fragments=%s bytes=%s frag_len=%s",
            self.partial_path,
            self._partial_fragments,
            self._partial_bytes,
            len(encoded),
        )
        return True

    async def replace_partial(self, content: str) -> bool:
        """Overwrite .partial with a complete replacement (e.g. REDUCE replaces MAP)."""
        if not self.is_recoverable_text(content):
            logger.debug("Skipping empty partial replace for %s", self.partial_path)
            return False
        await self._ensure_parent(self.partial_path)
        body = content if content.endswith("\n") else content + "\n"
        encoded = body.encode("utf-8")

        def _replace() -> None:
            with open(self.partial_path, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())

        await asyncio.to_thread(_replace)
        self._partial_bytes = len(encoded)
        self._partial_fragments = 1
        self._partial_started = True
        logger.debug(
            "Partial replaced path=%s bytes=%s",
            self.partial_path,
            self._partial_bytes,
        )
        return True

    async def write_partial(self, content: str) -> bool:
        """Legacy alias: full rewrite of .partial."""
        return await self.replace_partial(content)

    async def has_recoverable_partial(self) -> bool:
        exists = await asyncio.to_thread(os.path.exists, self.partial_path)
        if not exists:
            return False
        try:
            size = await asyncio.to_thread(os.path.getsize, self.partial_path)
        except Exception as exc:
            logger.error("Failed to stat partial %s: %s", self.partial_path, exc)
            return False
        if size <= 0:
            await self._remove_file(self.partial_path)
            return False
        # Avoid loading the whole file: non-empty file is treated as recoverable.
        # Confirm it is not only whitespace for tiny files.
        if size > 64:
            self._partial_bytes = max(self._partial_bytes, size)
            return True
        try:
            async with aiofiles.open(
                self.partial_path, "r", encoding="utf-8"
            ) as handle:
                content = await handle.read()
        except Exception as exc:
            logger.error("Failed to read partial %s: %s", self.partial_path, exc)
            return False
        if self.is_recoverable_text(content):
            self._partial_bytes = max(self._partial_bytes, size)
            return True
        await self._remove_file(self.partial_path)
        return False

    async def read_partial_text(self) -> str:
        """Load the text that would be committed. Required for the quality gate."""
        exists = await asyncio.to_thread(os.path.exists, self.partial_path)
        if not exists:
            return ""
        try:
            async with aiofiles.open(
                self.partial_path, "r", encoding="utf-8"
            ) as handle:
                return await handle.read()
        except Exception as exc:
            logger.error("Failed to read partial text %s: %s", self.partial_path, exc)
            return ""

    async def read_committed_text(self) -> str:
        exists = await asyncio.to_thread(os.path.exists, self.summary_path)
        if not exists:
            return ""
        async with aiofiles.open(self.summary_path, "r", encoding="utf-8") as handle:
            return await handle.read()

    async def _ensure_trailing_newline(self) -> None:
        def _fix() -> None:
            if not os.path.exists(self.partial_path):
                return
            size = os.path.getsize(self.partial_path)
            if size <= 0:
                return
            with open(self.partial_path, "rb+") as handle:
                handle.seek(-1, os.SEEK_END)
                last = handle.read(1)
                if last != b"\n":
                    handle.write(b"\n")
                    handle.flush()
                    os.fsync(handle.fileno())

        await asyncio.to_thread(_fix)

    async def commit_from_partial(self) -> None:
        """Promote .partial → summary.md via atomic rename. Does not load content into RAM."""
        if not await self.has_recoverable_partial():
            raise InvariantViolationError(
                "Cannot commit final summary.md: SUCCESS requires non-empty .partial",
                phase=PipelinePhase.INVARIANT_FAILED.value,
            )
        await self._ensure_parent(self.summary_path)
        await self._ensure_trailing_newline()

        def _promote() -> None:
            os.replace(self.partial_path, self.summary_path)

        await asyncio.to_thread(_promote)
        self._committed = True
        self._partial_started = False
        self._partial_bytes = 0
        logger.info(
            "Committed summary via atomic rename to %s (partial promoted)",
            self.summary_path,
        )
        if self._keep_partials():
            logger.info(
                "BREVIO_KEEP_PARTIALS enabled; preserving remaining temps after commit of %s",
                self.summary_path,
            )
            return
        # partial already renamed away; clean leftover .partial.bak if any
        await self.cleanup_temporaries(strict=False)

    async def commit_final(self, content: Optional[str] = None) -> None:
        """Commit final summary.md.

        Preferred path: content is None and .partial already holds the result
        (commit_from_partial). Legacy path: write content to .partial then promote.
        """
        if content is not None:
            if not self.is_recoverable_text(content):
                raise InvariantViolationError(
                    "Cannot commit final summary.md: SUCCESS requires non-empty text",
                    phase=PipelinePhase.INVARIANT_FAILED.value,
                )
            await self.replace_partial(content)
        await self.commit_from_partial()

    async def discard_empty_partials(self) -> None:
        if await self.has_recoverable_partial():
            return
        await self._remove_file(self.partial_path)
        await self._remove_file(self.bak_path)

    async def cleanup_temporaries(self, *, strict: bool = False) -> None:
        for path in self.temporary_paths():
            try:
                await self._remove_file(path)
            except Exception as exc:
                logger.error(
                    "Failed to remove temporary file %s: %s",
                    path,
                    exc,
                    exc_info=True,
                )
                if strict:
                    raise

    async def finalize(
        self, outcome: Optional[PipelineOutcome], final_committed: bool = False
    ) -> None:
        """Remove all temporary artifacts. Terminal jobs leave at most summary.md.

        Idempotent. BREVIO_KEEP_PARTIALS skips deletion (debug only).
        Uncommitted summary.md is removed on failure so FAILED never looks downloadable.
        """
        committed = (
            self._committed or final_committed or outcome == PipelineOutcome.SUCCESS
        )
        try:
            if self._keep_partials():
                logger.info(
                    "BREVIO_KEEP_PARTIALS enabled; skipping temp cleanup for %s",
                    self.summary_path,
                )
                self._finalized = True
                return
            await self.cleanup_temporaries(strict=not committed)
            if not committed:
                await self._remove_file(self.summary_path)
            self._finalized = True
        except Exception as exc:
            logger.error(
                "Artifact finalize failed (outcome=%s, final_committed=%s): %s",
                outcome,
                final_committed,
                exc,
                exc_info=True,
            )
            if committed:
                self._finalized = True
                return
            raise

    async def _remove_file(self, path: str) -> None:
        try:
            if await asyncio.to_thread(os.path.exists, path):
                await asyncio.to_thread(os.remove, path)
                logger.debug("Removed temporary file %s", path)
        except Exception as exc:
            logger.error("Failed to remove temporary file %s: %s", path, exc)
            raise


async def cancel_pending_tasks(tasks: Sequence[asyncio.Task]) -> List[BaseException]:
    """Cancel unfinished tasks and drain them. Returns unexpected secondary exceptions."""
    pending = [task for task in tasks if not task.done()]
    for task in pending:
        task.cancel()
    if not tasks:
        return []
    results = await asyncio.gather(*tasks, return_exceptions=True)
    secondary: List[BaseException] = []
    for result in results:
        if isinstance(result, asyncio.CancelledError):
            continue
        if isinstance(result, BaseException):
            secondary.append(result)
    return secondary


async def gather_or_cancel(*awaitables: Any) -> List[Any]:
    """
    asyncio.gather that cancels siblings on the first real failure.

    Expected cancellation is drained and not re-raised as the root cause.
    Unexpected sibling exceptions are attached as `secondary_exceptions`.
    """
    tasks = [
        item if isinstance(item, asyncio.Task) else asyncio.create_task(item)
        for item in awaitables
    ]
    if not tasks:
        return []
    try:
        return await asyncio.gather(*tasks)
    except BaseException as exc:
        secondary = await cancel_pending_tasks(tasks)
        real_secondary = [item for item in secondary if item is not exc]
        if real_secondary:
            logger.error(
                "Cancelled sibling tasks after root failure %s; secondary=%s",
                type(exc).__name__,
                [repr(item) for item in real_secondary],
            )
            setattr(exc, "secondary_exceptions", real_secondary)
        raise
