from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio_api.tasks import generate_summary_task, process_summary_task
from core.shared.enums.job_status import JobStatus
from core.shared.enums.model import ModelType


def test_process_summary_task_success_path_uses_service() -> None:
    service = MagicMock()
    service.generate_summary_documents = AsyncMock(return_value={"summary": "ok"})
    with patch("core.brevio_api.tasks.BrevioService", return_value=service):
        result = process_summary_task.run(
            files=[("doc.pdf", b"%PDF")],
            language=LanguageType.SPANISH.value,
            model=ModelType.GPT_4O_MINI.value,
            category="education",
            style="quick_ref",
            format=OutputFormatType.MARKDOWN.value,
            summary_level=SummaryLevel.MODERATE.value,
            _current_user="user-1",
            is_media=False,
            folder_entry_id="folder-1",
        )
    service.generate_summary_documents.assert_awaited_once()
    assert result["folder_entry_id"] == "folder-1"


def test_process_summary_task_passes_generation_params() -> None:
    service = MagicMock()
    service.generate_summary_documents = AsyncMock(return_value={"summary": "ok"})
    with patch("core.brevio_api.tasks.BrevioService", return_value=service):
        process_summary_task.run(
            files=[("doc.pdf", b"%PDF")],
            language=LanguageType.SPANISH.value,
            model=ModelType.GPT_4O_MINI.value,
            category="education",
            style="quick_ref",
            format=OutputFormatType.MARKDOWN.value,
            summary_level=SummaryLevel.MODERATE.value,
            _current_user="user-1",
            is_media=False,
            folder_entry_id="folder-1",
            max_output_tokens=1024,
            temperature=0.2,
        )
    prompt = service.generate_summary_documents.await_args.args[2]
    assert prompt.max_output_tokens is None
    assert prompt.temperature is None


def test_process_summary_task_accepts_media_mvp_formats() -> None:
    service = MagicMock()
    service.generate_summary_media_upload = AsyncMock(return_value={"summary": "ok"})
    with patch("core.brevio_api.tasks.BrevioService", return_value=service):
        result = process_summary_task.run(
            files=[
                ("a.mp3", b"x"),
                ("b.m4a", b"x"),
                ("c.wav", b"x"),
                ("d.mp4", b"x"),
                ("bad.avi", b"x"),
            ],
            language=LanguageType.SPANISH.value,
            model=ModelType.GPT_4O_MINI.value,
            category="education",
            style="quick_ref",
            format=OutputFormatType.MARKDOWN.value,
            summary_level=SummaryLevel.MODERATE.value,
            _current_user="user-1",
            is_media=True,
            folder_entry_id="folder-1",
            transcription_provider="local_whisper",
        )
    service.generate_summary_media_upload.assert_awaited_once()
    uploaded = service.generate_summary_media_upload.await_args.args[0]
    names = [name for name, _ in uploaded]
    assert names == ["a.mp3", "b.m4a", "c.wav", "d.mp4"]
    assert "api_key" not in service.generate_summary_media_upload.await_args.kwargs
    assert result["folder_entry_id"] == "folder-1"
    with pytest.raises(ValueError, match="No se encontraron archivos válidos"):
        process_summary_task.run(
            files=[("notes.txt", b"hello")],
            language=LanguageType.SPANISH.value,
            model=ModelType.GPT_4O_MINI.value,
            category="education",
            style="quick_ref",
            format=OutputFormatType.MARKDOWN.value,
            summary_level=SummaryLevel.MODERATE.value,
            _current_user="user-1",
        )


def test_generate_summary_task_invalid_object_id() -> None:
    with pytest.raises(ValueError, match="ObjectId"):
        generate_summary_task.run(
            {
                "prompt_config": {"id": "not-an-object-id"},
                "data": [],
            },
            "user-1",
        )


def test_terminal_publish_covers_completed_and_failed_routes() -> None:
    from core.brevio_api.events.broker import InMemoryEventBroker, reset_event_broker
    from core.brevio_api.events.publisher import publish_summary_job_event

    broker = InMemoryEventBroker()
    reset_event_broker(broker)
    done = publish_summary_job_event(
        user_id="user-1",
        job_id="job-1",
        document_id="doc-1",
        status=JobStatus.COMPLETED.value,
    )
    failed = publish_summary_job_event(
        user_id="user-1",
        job_id="job-2",
        document_id="doc-2",
        status=JobStatus.FAILED.value,
        error_code="FAILED",
        error_message="worker died",
    )
    assert done is not None and done.type.value == "summary.completed"
    assert failed is not None and failed.type.value == "summary.failed"
