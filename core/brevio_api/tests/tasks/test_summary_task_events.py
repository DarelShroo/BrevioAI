"""FASE 2 task contract: job_id transport, no PDF bytes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio_api.tasks import generate_summary_task, process_summary_task


def test_process_summary_task_success_path_uses_service() -> None:
    service = MagicMock()
    service.claim_summary_job = AsyncMock(return_value=MagicMock())
    service.execute_stored_summary_job = AsyncMock(return_value={"summary": "ok"})
    service.release_capacity_for_job = AsyncMock()
    with patch("core.brevio_api.tasks.BrevioService", return_value=service), patch(
        "core.brevio_api.tasks.JobHeartbeat"
    ):
        result = process_summary_task.run(job_id="folder-1")
    service.execute_stored_summary_job.assert_awaited_once_with("folder-1")
    assert result["job_id"] == "folder-1"
    assert result["status"] == "ok"


def test_process_summary_task_ignores_uncclaimed() -> None:
    service = MagicMock()
    service.claim_summary_job = AsyncMock(return_value=None)
    service.execute_stored_summary_job = AsyncMock()
    service.release_capacity_for_job = AsyncMock()
    with patch("core.brevio_api.tasks.BrevioService", return_value=service), patch(
        "core.brevio_api.tasks.JobHeartbeat"
    ):
        result = process_summary_task.run(job_id="folder-1")
    service.execute_stored_summary_job.assert_not_awaited()
    assert result["status"] == "ignored"


def test_process_summary_task_rejects_files_kwarg() -> None:
    with pytest.raises(ValueError, match="no longer accepts file bytes"):
        process_summary_task.run(job_id="folder-1", files=[("doc.pdf", b"%PDF")])


def test_generate_summary_task_requires_job_id() -> None:
    with pytest.raises(ValueError, match="job_id is required"):
        generate_summary_task.run(job_id="")


def test_generate_summary_task_runs_claimed_job() -> None:
    service = MagicMock()
    service.claim_summary_job = AsyncMock(return_value=MagicMock())
    service.execute_stored_summary_job = AsyncMock(return_value={"ok": True})
    service.release_capacity_for_job = AsyncMock()
    with patch("core.brevio_api.tasks.BrevioService", return_value=service), patch(
        "core.brevio_api.tasks.JobHeartbeat"
    ):
        result = generate_summary_task.run(job_id="yt-job-1")
    assert result["status"] == "ok"
    assert result["job_id"] == "yt-job-1"
