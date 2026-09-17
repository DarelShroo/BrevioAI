"""Job terminal status: COMPLETED/FAILED, persist transitions, download gate, cleanup."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import HTTPException

from core.brevio.generate import Generate, _ResultWriter
from core.brevio.models.response_model import SummaryResponse
from core.brevio.services.summary_pipeline import (
    PipelineDocumentError,
    PipelinePhase,
    job_phase_for,
    job_status_for,
)
from core.brevio_api.models.user.folder_entry import FolderEntry
from core.brevio_api.services.brevio_service import BrevioService
from core.shared.enums.job_status import JobPhase, JobStatus, can_transition_status
from core.shared.models.user.data_result import DataResult


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    monkeypatch.setattr(
        "core.brevio_api.core.database.AsyncDB.database", lambda self: MagicMock()
    )


def test_can_transition_status_idempotent_and_terminal():
    assert can_transition_status(None, JobStatus.PROCESSING.value) is True
    assert can_transition_status(None, JobStatus.QUEUED.value) is True
    assert (
        can_transition_status(JobStatus.QUEUED.value, JobStatus.PROCESSING.value)
        is True
    )
    assert (
        can_transition_status(JobStatus.PROCESSING.value, JobStatus.COMPLETED.value)
        is True
    )
    assert (
        can_transition_status(JobStatus.PROCESSING.value, JobStatus.FAILED.value)
        is True
    )
    assert (
        can_transition_status(JobStatus.COMPLETED.value, JobStatus.COMPLETED.value)
        is True
    )
    assert can_transition_status(JobStatus.FAILED.value, JobStatus.FAILED.value) is True
    assert (
        can_transition_status(JobStatus.COMPLETED.value, JobStatus.FAILED.value)
        is False
    )
    assert (
        can_transition_status(JobStatus.FAILED.value, JobStatus.COMPLETED.value)
        is False
    )
    assert (
        can_transition_status(JobStatus.COMPLETED.value, JobStatus.PROCESSING.value)
        is False
    )
    assert (
        can_transition_status(JobStatus.FAILED.value, JobStatus.PROCESSING.value)
        is False
    )
    assert (
        can_transition_status(JobStatus.QUEUED.value, JobStatus.COMPLETED.value)
        is False
    )


def test_job_phase_mapping():
    assert job_status_for(success=True) is JobStatus.COMPLETED
    assert job_status_for(success=False) is JobStatus.FAILED
    assert job_phase_for(PipelinePhase.MAP_FAILED, success=False) is JobPhase.MAP
    assert job_phase_for(PipelinePhase.REDUCE_FAILED, success=False) is JobPhase.REDUCE
    assert job_phase_for(PipelinePhase.FORMAT_FAILED, success=False) is JobPhase.FORMAT
    assert job_phase_for(PipelinePhase.DIRECT_FAILED, success=False) is JobPhase.DIRECT
    assert job_phase_for(PipelinePhase.MAP_RUNNING, success=True) is JobPhase.COMPLETED
    assert job_phase_for(PipelinePhase.SUCCESS, success=True) is JobPhase.COMPLETED


def test_legacy_data_result_with_location_is_completed():
    result = DataResult.model_construct(download_location="data/u/f/0")
    assert result.is_completed() is True


def test_processing_result_is_not_completed():
    result = DataResult.model_construct(
        download_location="data/u/f/0",
        status=JobStatus.PROCESSING.value,
        success=False,
    )
    assert result.is_completed() is False


def test_failed_result_is_not_completed_even_with_path():
    result = DataResult.model_construct(
        download_location="data/u/f/0",
        status=JobStatus.FAILED.value,
        success=False,
        phase=JobPhase.MAP.value,
    )
    assert result.is_completed() is False


class _FakeUserService:
    def __init__(self) -> None:
        self.store: dict[str, DataResult] = {}
        self.history: list[str] = []

    async def create_data_result(self, user_id, folder_id, result: DataResult):
        self.store[str(result.id)] = result
        self.history.append(result.status or "")
        return result

    async def update_data_result_status(
        self,
        user_id,
        folder_id,
        result: DataResult,
        *,
        status: str,
        phase: str,
        success: bool,
        error_type=None,
        error_code=None,
        error_message=None,
        download_location=None,
        name=None,
        index=None,
    ):
        from core.shared.enums.job_status import can_transition_status

        current = self.store.get(str(result.id))
        current_status = current.status if current else None
        if not can_transition_status(current_status, status):
            return result
        result.status = status
        result.phase = phase
        result.success = success
        result.error_type = error_type
        result.error_code = error_code
        result.error_message = error_message
        if download_location:
            result.download_location = download_location
        self.store[str(result.id)] = result
        self.history.append(status)
        return result


@pytest.mark.asyncio
async def test_result_writer_success_history_is_processing_then_completed():
    svc = _FakeUserService()
    writer = _ResultWriter(svc.create_data_result)
    result = DataResult(
        name="Document 0",
        index=0,
        download_location="data/u/f/0",
        status=JobStatus.PROCESSING.value,
        phase=JobPhase.QUEUED.value,
        success=False,
    )
    await writer.start("u", "f", result)
    await writer.finish(
        "u",
        "f",
        result,
        success=True,
        phase=JobPhase.COMPLETED.value,
        download_location="data/u/f/0",
        index=0,
    )
    assert svc.history == [JobStatus.PROCESSING.value, JobStatus.COMPLETED.value]
    assert svc.store[str(result.id)].success is True


@pytest.mark.asyncio
async def test_result_writer_failure_never_completed():
    svc = _FakeUserService()
    writer = _ResultWriter(svc.create_data_result)
    result = DataResult(
        name="Document 0",
        index=0,
        download_location="data/u/f/0",
        status=JobStatus.PROCESSING.value,
        phase=JobPhase.QUEUED.value,
        success=False,
    )
    await writer.start("u", "f", result)
    await writer.finish(
        "u",
        "f",
        result,
        success=False,
        phase=JobPhase.MAP.value,
        error_type="MapPhaseFailedError",
        error_code="MAP_FAILED",
        error_message="MAP failed",
    )
    assert JobStatus.COMPLETED.value not in svc.history
    assert svc.history[-1] == JobStatus.FAILED.value
    assert svc.store[str(result.id)].phase == JobPhase.MAP.value


@pytest.mark.asyncio
async def test_result_writer_idempotent_completed():
    svc = _FakeUserService()
    writer = _ResultWriter(svc.create_data_result)
    result = DataResult(
        name="Document 0",
        download_location="data/u/f/0",
        status=JobStatus.PROCESSING.value,
        phase=JobPhase.QUEUED.value,
        success=False,
    )
    await writer.start("u", "f", result)
    await writer.finish("u", "f", result, success=True, phase=JobPhase.COMPLETED.value)
    await writer.finish("u", "f", result, success=True, phase=JobPhase.COMPLETED.value)
    await writer.finish(
        "u",
        "f",
        result,
        success=False,
        phase=JobPhase.MAP.value,
        error_type="should-not-apply",
    )
    assert svc.store[str(result.id)].status == JobStatus.COMPLETED.value
    assert svc.store[str(result.id)].success is True


@pytest.mark.asyncio
async def test_generate_persists_failed_map_before_raising(tmp_path):
    svc = _FakeUserService()
    generate = Generate.__new__(Generate)
    generate._directory_manager = SimpleNamespace(createFolder=AsyncMock())
    generate._summary_service = SimpleNamespace(
        generate_summary_document=AsyncMock(
            return_value=SummaryResponse(
                success=False,
                message="MAP failed",
                error_message="MAP failed",
                phase=PipelinePhase.MAP_FAILED.value,
                error_type="MapPhaseFailedError",
                status=JobStatus.FAILED.value,
                job_phase=JobPhase.MAP.value,
            )
        )
    )
    data = SimpleNamespace(prompt_config=object())
    with pytest.raises(PipelineDocumentError):
        await generate._process_single_document(
            0,
            str(tmp_path / "doc.pdf"),
            data,
            str(ObjectId()),
            str(ObjectId()),
            str(ObjectId()),
            svc.create_data_result,
        )
    assert svc.history[-1] == JobStatus.FAILED.value
    stored = next(iter(svc.store.values()))
    assert stored.phase == JobPhase.MAP.value
    assert stored.success is False


@pytest.mark.asyncio
async def test_download_rejects_failed_and_processing(tmp_path):
    from core.brevio_api.services.brevio_service import BrevioService

    service = BrevioService()
    user_id = str(ObjectId())
    folder_entry_id = str(ObjectId())
    summary_dir = tmp_path / "summary_output"
    summary_dir.mkdir()
    (summary_dir / "summary.md").write_text("# leftover\n", encoding="utf-8")

    failed = DataResult.model_construct(
        download_location=str(summary_dir),
        status=JobStatus.FAILED.value,
        success=False,
        phase=JobPhase.FORMAT.value,
    )
    folder_entry = FolderEntry(
        _id=ObjectId(folder_entry_id),
        user_id=ObjectId(user_id),
        results=[failed],
    )
    mock_repo = AsyncMock()
    mock_repo.get_folder_entry_by_id.return_value = folder_entry
    with patch.object(service, "_get_user_service") as mock_get:
        mock_user_service = MagicMock()
        mock_user_service._folder_entry_repo = mock_repo
        mock_get.return_value = mock_user_service
        with pytest.raises(HTTPException) as exc:
            await service.download_summary_file(user_id, folder_entry_id, "md")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_intermediate_retry_does_not_mark_failed():
    svc = _FakeUserService()
    writer = _ResultWriter(svc.create_data_result)
    result = DataResult(
        name="Document 0",
        index=0,
        download_location="data/u/f/0",
        status=JobStatus.PROCESSING.value,
        phase=JobPhase.QUEUED.value,
        success=False,
    )
    await writer.start("u", "f", result)
    assert svc.history == [JobStatus.PROCESSING.value]
    assert svc.store[str(result.id)].status == JobStatus.PROCESSING.value
    assert svc.store[str(result.id)].success is False
    await writer.finish(
        "u",
        "f",
        result,
        success=True,
        phase=JobPhase.COMPLETED.value,
        download_location="data/u/f/0",
    )
    assert JobStatus.FAILED.value not in svc.history
    assert svc.history == [JobStatus.PROCESSING.value, JobStatus.COMPLETED.value]
    assert svc.store[str(result.id)].status == JobStatus.COMPLETED.value
    assert svc.store[str(result.id)].success is True


@pytest.mark.asyncio
async def test_exhausted_retry_marks_failed_only_at_end():
    svc = _FakeUserService()
    writer = _ResultWriter(svc.create_data_result)
    result = DataResult(
        name="Document 0",
        index=0,
        download_location="data/u/f/0",
        status=JobStatus.PROCESSING.value,
        phase=JobPhase.MAP.value,
        success=False,
    )
    await writer.start("u", "f", result)
    assert svc.store[str(result.id)].status == JobStatus.PROCESSING.value
    await writer.finish(
        "u",
        "f",
        result,
        success=False,
        phase=JobPhase.MAP.value,
        error_type="RateLimitError",
        error_code="MAP_FAILED",
        error_message="429 exhausted",
    )
    assert svc.history == [JobStatus.PROCESSING.value, JobStatus.FAILED.value]
    stored = svc.store[str(result.id)]
    assert stored.status == JobStatus.FAILED.value
    assert stored.phase == JobPhase.MAP.value
    assert stored.success is False
    assert stored.error_type == "RateLimitError"


@pytest.mark.asyncio
async def test_result_writer_idempotent_failed_not_promoted_to_completed():
    svc = _FakeUserService()
    writer = _ResultWriter(svc.create_data_result)
    result = DataResult(
        name="Document 0",
        download_location="data/u/f/0",
        status=JobStatus.PROCESSING.value,
        phase=JobPhase.QUEUED.value,
        success=False,
    )
    await writer.start("u", "f", result)
    await writer.finish(
        "u",
        "f",
        result,
        success=False,
        phase=JobPhase.REDUCE.value,
        error_type="ReduceConvergenceError",
        error_code="REDUCE_FAILED",
        error_message="reduce failed",
    )
    await writer.finish("u", "f", result, success=True, phase=JobPhase.COMPLETED.value)
    stored = svc.store[str(result.id)]
    assert stored.status == JobStatus.FAILED.value
    assert stored.success is False
    assert stored.phase == JobPhase.REDUCE.value


@pytest.mark.asyncio
async def test_fail_processing_results_skips_terminal_rows():
    from core.brevio_api.services.user_service import UserService

    completed = DataResult(
        name="done",
        download_location="data/u/f/0",
        status=JobStatus.COMPLETED.value,
        phase=JobPhase.COMPLETED.value,
        success=True,
    )
    processing = DataResult(
        name="running",
        download_location="data/u/f/1",
        status=JobStatus.PROCESSING.value,
        phase=JobPhase.MAP.value,
        success=False,
    )
    failed = DataResult(
        name="dead",
        download_location="data/u/f/2",
        status=JobStatus.FAILED.value,
        phase=JobPhase.FORMAT.value,
        success=False,
    )
    folder_entry = FolderEntry(
        _id=ObjectId(),
        user_id=ObjectId(),
        results=[completed, processing, failed],
    )
    repo = AsyncMock()
    repo.get_folder_entry_by_id.return_value = folder_entry
    repo.update_data_result = AsyncMock()
    user_service = UserService(AsyncMock(), repo)
    await user_service.fail_processing_results(
        str(folder_entry.id), RuntimeError("boom"), phase="FAILED"
    )
    assert repo.update_data_result.await_count == 1
    args, kwargs = repo.update_data_result.call_args
    assert args[1] == processing.id
    assert args[2]["status"] == JobStatus.FAILED.value
    assert args[2]["phase"] == JobPhase.MAP.value
    assert args[2]["success"] is False
