from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId

from core.brevio_api.models.user.folder_entry import FolderEntry
from core.brevio_api.services.user_service import UserService
from core.shared.enums.job_status import JobPhase, JobStatus
from core.shared.models.user.data_result import DataResult


def _service_with_entry(entry: FolderEntry) -> tuple[UserService, AsyncMock]:
    repo = AsyncMock()
    repo.get_folder_entry_by_id.return_value = entry
    repo.update_data_result = AsyncMock()
    return UserService(AsyncMock(), repo), repo


@pytest.mark.asyncio
async def test_completed_status_emits_summary_completed() -> None:
    result = DataResult(
        name="Doc.pdf",
        download_location="data/u/f/0",
        status=JobStatus.PROCESSING.value,
        phase=JobPhase.MAP.value,
        success=False,
    )
    entry = FolderEntry(
        _id=ObjectId(),
        user_id=ObjectId(),
        name="Quarterly report",
        results=[result],
    )
    service, repo = _service_with_entry(entry)
    with patch(
        "core.brevio_api.services.user_service.publish_summary_job_event"
    ) as publish:
        publish.return_value = None
        await service.update_data_result_status(
            str(entry.user_id),
            str(entry.id),
            result,
            status=JobStatus.COMPLETED.value,
            phase=JobPhase.COMPLETED.value,
            success=True,
            name="Doc.pdf",
        )
    publish.assert_called_once()
    kwargs = publish.call_args.kwargs
    assert kwargs["user_id"] == str(entry.user_id)
    assert kwargs["job_id"] == str(entry.id)
    assert kwargs["document_id"] == str(result.id)
    assert kwargs["status"] == JobStatus.COMPLETED.value
    assert kwargs["document_name"] == "Doc.pdf"
    repo.update_data_result.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_status_emits_summary_failed() -> None:
    result = DataResult(
        name="Doc.pdf",
        download_location="data/u/f/0",
        status=JobStatus.PROCESSING.value,
        phase=JobPhase.MAP.value,
        success=False,
    )
    entry = FolderEntry(_id=ObjectId(), user_id=ObjectId(), results=[result])
    service, _repo = _service_with_entry(entry)
    with patch(
        "core.brevio_api.services.user_service.publish_summary_job_event"
    ) as publish:
        await service.update_data_result_status(
            str(entry.user_id),
            str(entry.id),
            result,
            status=JobStatus.FAILED.value,
            phase=JobPhase.MAP.value,
            success=False,
            error_code="MAP_FAILED",
            error_message="MAP failed",
        )
    kwargs = publish.call_args.kwargs
    assert kwargs["status"] == JobStatus.FAILED.value
    assert kwargs["error_code"] == "MAP_FAILED"
    assert kwargs["error_message"] == "MAP failed"


@pytest.mark.asyncio
async def test_idempotent_completed_does_not_reemit() -> None:
    result = DataResult(
        name="Doc.pdf",
        download_location="data/u/f/0",
        status=JobStatus.COMPLETED.value,
        phase=JobPhase.COMPLETED.value,
        success=True,
    )
    entry = FolderEntry(_id=ObjectId(), user_id=ObjectId(), results=[result])
    service, _repo = _service_with_entry(entry)
    with patch(
        "core.brevio_api.services.user_service.publish_summary_job_event"
    ) as publish:
        await service.update_data_result_status(
            str(entry.user_id),
            str(entry.id),
            result,
            status=JobStatus.COMPLETED.value,
            phase=JobPhase.COMPLETED.value,
            success=True,
        )
    publish.assert_not_called()


@pytest.mark.asyncio
async def test_processing_status_does_not_emit() -> None:
    result = DataResult(
        name="Doc.pdf",
        status=None,
        phase=JobPhase.QUEUED.value,
        success=False,
    )
    entry = FolderEntry(_id=ObjectId(), user_id=ObjectId(), results=[result])
    service, _repo = _service_with_entry(entry)
    with patch(
        "core.brevio_api.services.user_service.publish_summary_job_event"
    ) as publish:
        await service.update_data_result_status(
            str(entry.user_id),
            str(entry.id),
            result,
            status=JobStatus.PROCESSING.value,
            phase=JobPhase.MAP.value,
            success=False,
        )
    publish.assert_not_called()


@pytest.mark.asyncio
async def test_fail_processing_results_emits_failed_for_open_rows() -> None:
    processing = DataResult(
        name="running.pdf",
        download_location="data/u/f/1",
        status=JobStatus.PROCESSING.value,
        phase=JobPhase.MAP.value,
        success=False,
    )
    completed = DataResult(
        name="done.pdf",
        download_location="data/u/f/0",
        status=JobStatus.COMPLETED.value,
        phase=JobPhase.COMPLETED.value,
        success=True,
    )
    entry = FolderEntry(
        _id=ObjectId(),
        user_id=ObjectId(),
        name="Bundle",
        results=[completed, processing],
    )
    service, repo = _service_with_entry(entry)
    with patch(
        "core.brevio_api.services.user_service.publish_summary_job_event"
    ) as publish:
        await service.fail_processing_results(
            str(entry.id), RuntimeError("worker died"), phase="FAILED"
        )
    publish.assert_called_once()
    kwargs = publish.call_args.kwargs
    assert kwargs["document_id"] == str(processing.id)
    assert kwargs["status"] == JobStatus.FAILED.value
    assert kwargs["document_name"] == "running.pdf"
    assert repo.update_data_result.await_count == 1


@pytest.mark.asyncio
async def test_concurrent_jobs_emit_independent_events() -> None:
    user_id = ObjectId()
    first = DataResult(
        name="one.pdf",
        download_location="data/u/f/0",
        status=JobStatus.PROCESSING.value,
        success=False,
    )
    second = DataResult(
        name="two.pdf",
        download_location="data/u/f/1",
        status=JobStatus.PROCESSING.value,
        success=False,
    )
    entry_a = FolderEntry(_id=ObjectId(), user_id=user_id, results=[first])
    entry_b = FolderEntry(_id=ObjectId(), user_id=user_id, results=[second])
    repo = AsyncMock()

    async def get_entry(folder_id: str) -> FolderEntry:
        return entry_a if folder_id == str(entry_a.id) else entry_b

    repo.get_folder_entry_by_id.side_effect = get_entry
    repo.update_data_result = AsyncMock()
    service = UserService(AsyncMock(), repo)
    published: list[dict] = []

    def capture(**kwargs):
        published.append(kwargs)
        return None

    with patch(
        "core.brevio_api.services.user_service.publish_summary_job_event",
        side_effect=capture,
    ):
        await service.update_data_result_status(
            str(user_id),
            str(entry_a.id),
            first,
            status=JobStatus.COMPLETED.value,
            phase=JobPhase.COMPLETED.value,
            success=True,
        )
        await service.update_data_result_status(
            str(user_id),
            str(entry_b.id),
            second,
            status=JobStatus.FAILED.value,
            phase=JobPhase.MAP.value,
            success=False,
            error_code="MAP_FAILED",
            error_message="nope",
        )
    assert [item["job_id"] for item in published] == [str(entry_a.id), str(entry_b.id)]
    assert published[0]["status"] == JobStatus.COMPLETED.value
    assert published[1]["status"] == JobStatus.FAILED.value
