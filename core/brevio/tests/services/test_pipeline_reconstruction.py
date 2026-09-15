"""Regression tests for the reconstructed summary pipeline."""

from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.models.file_config_model import FileConfig
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio.services.summary_pipeline import PipelinePhase
from core.brevio.services.summary_service import SummaryService
from core.shared.enums.model import ModelType
from core.shared.utils.adaptive_salience_policy import AdaptiveSaliencePolicy
from core.shared.utils.chunking_utils import (
    extract_document_outline,
    format_coverage_checklist,
    outline_for_chunk,
)


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    monkeypatch.setattr(
        "core.brevio_api.core.database.AsyncDB.database", lambda self: MagicMock()
    )


@pytest.fixture
def service():
    return SummaryService()


def _prompt_config(level: SummaryLevel = SummaryLevel.MODERATE) -> PromptConfig:
    return PromptConfig(
        model=ModelType.DEEPSEEK_V4_PRO,
        category=CategoryType.SIMPLE_SUMMARY.value,
        style=StyleType.SIMPLE_SUMMARY_DEFAULT.value,
        format=OutputFormatType.MARKDOWN,
        language=LanguageType.ENGLISH,
        summary_level=level,
    )


def _file_config(tmp_path) -> FileConfig:
    return FileConfig(
        document_path=str(tmp_path / "doc.pdf"),
        summary_path=str(tmp_path / "summary.md"),
        transcription_path=str(tmp_path / "t.txt"),
    )


SECTIONED_DOC = """# Main Title

## Alpha Section
Alpha unique concept ALPHA_TOKEN with essential details.

## Beta Section
Beta unique concept BETA_TOKEN explaining methodology.

## Gamma Section
Gamma unique concept GAMMA_TOKEN and final conclusions.
"""


def test_outline_extraction_preserves_structure():
    from core.brevio.constants.prompts import ENGLISH

    outline = extract_document_outline(SECTIONED_DOC)
    assert "# Main Title" in outline
    assert "## Alpha Section" in outline
    assert "## Beta Section" in outline
    assert "## Gamma Section" in outline
    checklist = format_coverage_checklist(outline, ENGLISH)
    assert "Alpha Section" in checklist
    assert "Coverage checklist" in checklist


def test_outline_for_chunk_filters_locally():
    outline = extract_document_outline(SECTIONED_DOC)
    matched = outline_for_chunk(
        "## Beta Section\nBeta unique concept BETA_TOKEN", outline
    )
    assert any("Beta" in item for item in matched)
    assert not any("Gamma" in item for item in matched)


def test_very_concise_not_destructive_and_levels_monotonic():
    policy = AdaptiveSaliencePolicy()
    model = ModelType.GPT_4O_MINI
    # Keep below document-size and native caps so levels remain distinguishable.
    doc_tokens = 5000
    levels = [
        SummaryLevel.VERY_CONCISE,
        SummaryLevel.CONCISE,
        SummaryLevel.MODERATE,
        SummaryLevel.DETAILED,
        SummaryLevel.VERY_DETAILED,
    ]
    budgets = [
        policy.budget(model, level, doc_tokens, LanguageType.ENGLISH)
        for level in levels
    ]
    for i in range(len(budgets) - 1):
        assert budgets[i].output_target_tokens < budgets[i + 1].output_target_tokens

    vc = budgets[0]
    assert vc.output_target_tokens >= 600
    assert "absolute minimum" not in vc.length_instruction.lower()
    assert "extremely short" not in vc.length_instruction.lower()
    assert (
        "main" in vc.semantic_profile.lower() or "thesis" in vc.semantic_profile.lower()
    )
    assert "COVERAGE GUARANTEE" in vc.coverage_instruction


def test_direct_route_for_fitting_docs_hierarchical_when_overflow():
    policy = AdaptiveSaliencePolicy()
    assert (
        policy.budget(
            ModelType.GPT_4O_MINI, SummaryLevel.MODERATE, 1500, LanguageType.ENGLISH
        ).route
        == "direct"
    )
    assert (
        policy.budget(
            ModelType.GPT_4O_MINI, SummaryLevel.MODERATE, 8000, LanguageType.ENGLISH
        ).route
        == "hierarchical"
    )
    assert (
        policy.budget(
            ModelType.GPT_4, SummaryLevel.MODERATE, 6000, LanguageType.ENGLISH
        ).route
        == "hierarchical"
    )


@pytest.mark.asyncio
async def test_direct_route_makes_one_llm_call(service, tmp_path):
    """Documents that fit context must not run MAP/REDUCE/FORMAT."""
    calls = {"direct": 0, "map": 0, "reduce": 0, "format": 0}

    async def fake_direct(*args, **kwargs):
        calls["direct"] += 1
        return (
            "# Main Title\n\n## Alpha Section\nALPHA_TOKEN\n\n"
            "## Beta Section\nBETA_TOKEN\n\n## Gamma Section\nGAMMA_TOKEN",
            42,
        )

    async def boom_map(*args, **kwargs):
        calls["map"] += 1
        raise AssertionError("MAP must not run on DIRECT route")

    async def boom_reduce(*args, **kwargs):
        calls["reduce"] += 1
        raise AssertionError("REDUCE must not run on DIRECT route")

    async def boom_format(*args, **kwargs):
        calls["format"] += 1
        raise AssertionError("FORMAT must not run on DIRECT route")

    decision = MagicMock()
    decision.route = "direct"
    decision.output_target_tokens = 800

    with ExitStack() as stack:
        stack.enter_context(
            patch.object(service.directory_manager, "validate_paths", new=AsyncMock())
        )
        stack.enter_context(
            patch.object(
                service.directory_manager,
                "read_pdf",
                new=AsyncMock(return_value=[SECTIONED_DOC]),
            )
        )
        stack.enter_context(
            patch.object(
                service,
                "detect_language_with_retry_safe",
                new=AsyncMock(return_value="en"),
            )
        )
        stack.enter_context(
            patch.object(service, "run_direct_summary", side_effect=fake_direct)
        )
        stack.enter_context(
            patch.object(service, "run_map_phase", side_effect=boom_map)
        )
        stack.enter_context(
            patch.object(service, "run_reduce_phase", side_effect=boom_reduce)
        )
        stack.enter_context(
            patch.object(service, "run_formatting_phase", side_effect=boom_format)
        )
        stack.enter_context(
            patch.object(
                service.advanced_prompt_generator,
                "get_direct_summary_prompt",
                new=AsyncMock(return_value="direct prompt"),
            )
        )
        pol = stack.enter_context(
            patch("core.brevio.services.summary_service.AdaptiveSaliencePolicy")
        )
        pol.return_value.budget.return_value = decision
        resp = await service._process_single_document(
            "p",
            _file_config(tmp_path),
            ModelType.DEEPSEEK_V4_PRO,
            _prompt_config(SummaryLevel.VERY_CONCISE),
            folder_id="fold",
            user_id="user",
        )

    assert resp.success is True
    assert calls == {"direct": 1, "map": 0, "reduce": 0, "format": 0}
    text = (tmp_path / "summary.md").read_text()
    assert "ALPHA_TOKEN" in text
    assert "BETA_TOKEN" in text
    assert "GAMMA_TOKEN" in text
    assert resp.phase == PipelinePhase.SUCCESS.value
    assert resp.status == "COMPLETED"


@pytest.mark.asyncio
async def test_hierarchical_skips_format_by_default(service, tmp_path):
    from core.brevio.services.summary_service import MapChunkResult

    map_results = [
        MapChunkResult(0, "orig a", "SUCCESS", "## Alpha\nALPHA_TOKEN details"),
        MapChunkResult(1, "orig b", "SUCCESS", "## Beta\nBETA_TOKEN details"),
    ]

    async def fake_map(*args, **kwargs):
        return map_results, 10

    async def fake_reduce(*args, **kwargs):
        return "## Alpha\nALPHA_TOKEN\n\n## Beta\nBETA_TOKEN", 8

    async def boom_format(*args, **kwargs):
        raise AssertionError("FORMAT must be skipped by default")

    decision = MagicMock()
    decision.route = "hierarchical"
    decision.output_target_tokens = 900

    with ExitStack() as stack:
        stack.enter_context(
            patch.object(service.directory_manager, "validate_paths", new=AsyncMock())
        )
        stack.enter_context(
            patch.object(
                service.directory_manager,
                "read_pdf",
                new=AsyncMock(return_value=[SECTIONED_DOC * 20]),
            )
        )
        stack.enter_context(
            patch.object(
                service,
                "detect_language_with_retry_safe",
                new=AsyncMock(return_value="en"),
            )
        )
        stack.enter_context(
            patch.object(service, "chunk_text", new=AsyncMock(return_value=["a", "b"]))
        )
        stack.enter_context(
            patch.object(service, "run_map_phase", side_effect=fake_map)
        )
        stack.enter_context(
            patch.object(service, "run_reduce_phase", side_effect=fake_reduce)
        )
        stack.enter_context(
            patch.object(service, "run_formatting_phase", side_effect=boom_format)
        )
        stack.enter_context(
            patch.object(
                service.advanced_prompt_generator,
                "get_map_prompt",
                new=AsyncMock(return_value="m"),
            )
        )
        stack.enter_context(
            patch.object(
                service.advanced_prompt_generator,
                "get_reduce_prompt",
                new=AsyncMock(return_value="r"),
            )
        )
        pol = stack.enter_context(
            patch("core.brevio.services.summary_service.AdaptiveSaliencePolicy")
        )
        pol.return_value.budget.return_value = decision
        resp = await service._process_single_document(
            "p",
            _file_config(tmp_path),
            ModelType.DEEPSEEK_V4_PRO,
            _prompt_config(),
            folder_id="fold",
            user_id="user",
        )

    assert resp.success is True
    text = (tmp_path / "summary.md").read_text()
    assert "ALPHA_TOKEN" in text and "BETA_TOKEN" in text


def test_format_skipped_unless_explicitly_enabled(service, monkeypatch):
    monkeypatch.delenv("BREVIO_ENABLE_FORMAT_PHASE", raising=False)
    monkeypatch.setenv("BREVIO_MIN_TOKENS_FOR_POSTPROCESS", "0")
    long_text = "word " * 500
    assert service._should_skip_formatting(long_text, ModelType.GPT_4O_MINI) is True

    monkeypatch.setenv("BREVIO_ENABLE_FORMAT_PHASE", "1")
    monkeypatch.setenv("BREVIO_MIN_TOKENS_FOR_POSTPROCESS", "100000")
    assert service._should_skip_formatting(long_text, ModelType.GPT_4O_MINI) is True

    monkeypatch.setenv("BREVIO_MIN_TOKENS_FOR_POSTPROCESS", "1")
    assert service._should_skip_formatting(long_text, ModelType.GPT_4O_MINI) is False
