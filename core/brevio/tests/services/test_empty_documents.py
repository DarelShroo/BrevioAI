"""Tests for empty, unextractable, and corrupt documents, and credit refunds."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pypdf import PdfWriter

from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.models.file_config_model import FileConfig
from core.brevio.services.summary_pipeline import PipelinePhase
from core.brevio.services.summary_service import SummaryService
from core.shared.enums.model import ModelType
from core.shared.models.history_token_model import HistoryTokenModel
from core.shared.utils.summary_quality import (
    ArtifactVerdict,
    QualitySignals,
    count_words,
    evaluate_artifact,
)


@pytest.fixture
def directory_manager():
    return DirectoryManager()


@pytest.mark.asyncio
async def test_empty_docx_raises_value_error(directory_manager, tmp_path):
    from docx import Document

    doc_path = str(tmp_path / "empty.docx")
    doc = Document()
    doc.save(doc_path)

    with pytest.raises(ValueError, match="está vacío o no contiene texto legible"):
        await directory_manager.read_docx(doc_path)


@pytest.mark.asyncio
async def test_encrypted_pdf_raises_value_error(directory_manager, tmp_path):
    pdf_path = str(tmp_path / "encrypted.pdf")
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("secret_password")
    with open(pdf_path, "wb") as f:
        writer.write(f)

    with pytest.raises(ValueError, match="protegido con contraseña o encriptado"):
        await directory_manager.read_pdf(pdf_path, None)


@pytest.mark.asyncio
async def test_zero_page_pdf_raises_value_error(directory_manager, tmp_path):
    pdf_path = str(tmp_path / "zero_pages.pdf")
    writer = PdfWriter()
    with open(pdf_path, "wb") as f:
        writer.write(f)

    with pytest.raises(ValueError, match="está vacío o no contiene páginas"):
        await directory_manager.read_pdf(pdf_path, None)


@pytest.mark.asyncio
async def test_image_only_pdf_without_ocr_raises_value_error(directory_manager, tmp_path):
    """When PDF pages have no extractable text and OCR yields nothing."""
    pdf_path = str(tmp_path / "blank_pages.pdf")
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)
    with open(pdf_path, "wb") as f:
        writer.write(f)

    with pytest.raises(ValueError, match="no contiene texto extraíble o procesable"):
        await directory_manager.read_pdf(pdf_path, None)


def test_placeholder_no_content_marked_invalid():
    signals = QualitySignals(
        source_tokens=50,
        source_words=10,
        map_tokens=0,
        map_words=0,
        output_min_tokens=0,
        output_target_tokens=100,
        output_hard_limit=500,
        summary_level="moderate",
        route="direct",
    )
    report = evaluate_artifact("No hay contenido disponible para resumir en este archivo.", signals)
    assert not report.deliverable
    assert report.verdict == ArtifactVerdict.INVALID
    assert any("placeholder_no_content" in r or "trivial_artifact" in r for r in report.reasons)


def test_trivial_short_artifact_rejected():
    signals = QualitySignals(
        source_tokens=300,
        source_words=200,
        map_tokens=0,
        map_words=0,
        output_min_tokens=0,
        output_target_tokens=100,
        output_hard_limit=500,
        summary_level="moderate",
        route="direct",
    )
    report = evaluate_artifact("Resumen muy breve.", signals)
    assert not report.deliverable
    assert report.verdict == ArtifactVerdict.INVALID
    assert any(
        "trivial_artifact_too_short" in r
        or "below_min_words" in r
        or "placeholder_no_content" in r
        for r in report.reasons
    )


@pytest.mark.asyncio
async def test_summary_service_fails_early_on_insufficient_text():
    service = SummaryService.__new__(SummaryService)
    service.history_token_model = HistoryTokenModel()
    service._pipeline_t0 = None
    service.directory_manager = MagicMock()
    service.directory_manager.validate_paths = AsyncMock()
    service.directory_manager.read_transcription = AsyncMock(return_value="   hola   ")
    service._document_result = AsyncMock()

    file_config = FileConfig(
        document_path="/tmp/fake.txt",
        summary_path="/tmp/fake_summary.md",
    )

    from core.brevio.enums.category import CategoryType
    from core.brevio.enums.language import LanguageType
    from core.brevio.enums.output_format_type import OutputFormatType
    from core.brevio.enums.style import StyleType
    from core.brevio.enums.summary_level import SummaryLevel
    from core.brevio.models.prompt_config_model import PromptConfig

    prompt_config = PromptConfig(
        model=ModelType.GPT_4O_MINI,
        category=CategoryType.SIMPLE_SUMMARY.value,
        style=StyleType.SIMPLE_SUMMARY_DEFAULT.value,
        format=OutputFormatType.MARKDOWN,
        language=LanguageType.ENGLISH,
        summary_level=SummaryLevel.MODERATE,
    )

    await service._process_single_document(
        prompt="dummy",
        file_config=file_config,
        model=prompt_config.model,
        prompt_config=prompt_config,
    )

    service._document_result.assert_awaited_once()
    kwargs = service._document_result.await_args.kwargs
    assert kwargs["success"] is False
    assert "insuficiente" in kwargs["message"] or "no contiene" in kwargs["message"]


@pytest.mark.asyncio
async def test_settle_job_credits_releases_full_amount_on_failure():
    """Verify that a failed job does NOT charge any credits and releases the reservation."""
    from core.brevio_api.services.brevio_service import BrevioService

    service = BrevioService()
    mock_credits = MagicMock()
    mock_settle_result = MagicMock()
    mock_settle_result.settlement = MagicMock(consumed_credits=0, released_credits=50, user_id="user1")
    mock_credits.settle_job = AsyncMock(return_value=mock_settle_result)
    service._get_credit_service = AsyncMock(return_value=mock_credits)

    mock_product_service = MagicMock()
    mock_product_service.records = MagicMock(get_by_job=AsyncMock(return_value=MagicMock(status="RESERVED")))
    mock_product_service.record_settled_credits = AsyncMock()
    mock_product_service.release_admission = AsyncMock()
    service._get_product_limit_service = AsyncMock(return_value=mock_product_service)

    mock_user_service = MagicMock()
    mock_user_service._folder_entry_repo.get_folder_entry_by_id = AsyncMock(return_value=MagicMock(plan_snapshot={}))
    service._get_user_service = AsyncMock(return_value=mock_user_service)

    job_id = "job-failed-123"
    await service.settle_job_credits(job_id, success=False)

    # Must call settle_job with consumed_credits = 0
    mock_credits.settle_job.assert_awaited_once_with(
        job_id=job_id, consumed_credits=0, metadata={"reason": "job_failed"}
    )
    # Must NOT record settled credits against product limits
    mock_product_service.record_settled_credits.assert_not_called()
    # Must release admission
    mock_product_service.release_admission.assert_awaited_once_with(job_id)
