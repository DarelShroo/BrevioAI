"""Incremental .partial writing and memory-release contract tests."""

from __future__ import annotations

import os
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
from core.brevio.services.summary_pipeline import PipelinePhase, SummaryArtifactManager
from core.brevio.services.summary_service import MapChunkResult, SummaryService
from core.shared.enums.model import ModelType


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    monkeypatch.setattr(
        "core.brevio_api.core.database.AsyncDB.database", lambda self: MagicMock()
    )
    monkeypatch.setenv("BREVIO_KEEP_PARTIALS", "false")


@pytest.fixture
def service():
    return SummaryService()


def _prompt_config() -> PromptConfig:
    return PromptConfig(
        model=ModelType.DEEPSEEK_V4_PRO,
        category=CategoryType.SIMPLE_SUMMARY.value,
        style=StyleType.SIMPLE_SUMMARY_DEFAULT.value,
        format=OutputFormatType.MARKDOWN,
        language=LanguageType.ENGLISH,
        summary_level=SummaryLevel.MODERATE,
    )


def _file_config(tmp_path) -> FileConfig:
    return FileConfig(
        document_path=str(tmp_path / "doc.pdf"),
        summary_path=str(tmp_path / "summary.md"),
        transcription_path=str(tmp_path / "t.txt"),
    )


@pytest.mark.asyncio
async def test_append_partial_is_incremental_not_full_rewrite(tmp_path):
    manager = SummaryArtifactManager(str(tmp_path / "summary.md"))
    await manager.reset_partial()
    await manager.append_partial("ALPHA_FRAGMENT", separator="\n\n")
    await manager.append_partial("BETA_FRAGMENT", separator="\n\n")
    await manager.append_partial("GAMMA_FRAGMENT", separator="\n\n")

    assert manager.partial_fragment_count == 3
    text = (tmp_path / "summary.md.partial").read_text(encoding="utf-8")
    assert text.index("ALPHA_FRAGMENT") < text.index("BETA_FRAGMENT")
    assert text.index("BETA_FRAGMENT") < text.index("GAMMA_FRAGMENT")
    assert manager.partial_bytes_written == os.path.getsize(
        tmp_path / "summary.md.partial"
    )


@pytest.mark.asyncio
async def test_never_creates_map_partial(tmp_path):
    """Only summary.md.partial exists during the job; never summary.md.map.partial."""
    manager = SummaryArtifactManager(str(tmp_path / "summary.md"))
    await manager.reset_partial()
    await manager.append_partial("MAP_CHUNK_A", separator="\n\n")
    assert (tmp_path / "summary.md.partial").exists()
    assert not (tmp_path / "summary.md.map.partial").exists()
    await manager.append_partial("MAP_CHUNK_B", separator="\n\n")
    assert not (tmp_path / "summary.md.map.partial").exists()
    await manager.replace_partial("REDUCED_FINAL")
    assert (tmp_path / "summary.md.partial").exists()
    assert not (tmp_path / "summary.md.map.partial").exists()
    await manager.commit_from_partial()
    assert (tmp_path / "summary.md").exists()
    assert not (tmp_path / "summary.md.partial").exists()
    assert not (tmp_path / "summary.md.map.partial").exists()


@pytest.mark.asyncio
async def test_commit_from_partial_promotes_and_removes_partial(tmp_path):
    manager = SummaryArtifactManager(str(tmp_path / "summary.md"))
    await manager.replace_partial("FINAL BODY ON DISK")
    await manager.commit_from_partial()

    assert (tmp_path / "summary.md").exists()
    assert not (tmp_path / "summary.md.partial").exists()
    assert "FINAL BODY ON DISK" in (tmp_path / "summary.md").read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_commit_final_without_content_uses_existing_partial(tmp_path):
    manager = SummaryArtifactManager(str(tmp_path / "summary.md"))
    await manager.append_partial("only partial", separator="")
    await manager.commit_final()  # content=None → promote

    assert (tmp_path / "summary.md").exists()
    assert not (tmp_path / "summary.md.partial").exists()


@pytest.mark.asyncio
async def test_direct_success_leaves_only_summary_md(service, tmp_path):
    decision = MagicMock()
    decision.route = "direct"
    decision.output_target_tokens = 200

    async def fake_direct(*args, **kwargs):
        return ("# Title\n\nDIRECT_BODY_TOKEN", 10)

    with ExitStack() as stack:
        stack.enter_context(
            patch.object(service.directory_manager, "validate_paths", new=AsyncMock())
        )
        stack.enter_context(
            patch.object(
                service.directory_manager,
                "read_pdf",
                new=AsyncMock(return_value=["hello world " * 40]),
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
            patch.object(
                service.advanced_prompt_generator,
                "get_direct_summary_prompt",
                new=AsyncMock(return_value="direct"),
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
    assert resp.phase == PipelinePhase.SUCCESS.value
    assert (tmp_path / "summary.md").exists()
    assert not (tmp_path / "summary.md.partial").exists()
    assert "DIRECT_BODY_TOKEN" in (tmp_path / "summary.md").read_text(encoding="utf-8")
    # Response must not retain a second full copy of the body.
    assert resp.summary == ""


@pytest.mark.asyncio
async def test_hierarchical_map_appends_fragments_then_reduce_replaces(
    service, tmp_path, monkeypatch
):
    monkeypatch.setenv("BREVIO_ENABLE_FORMAT_PHASE", "0")
    append_sizes: list[int] = []
    original_append = SummaryArtifactManager.append_partial
    original_replace = SummaryArtifactManager.replace_partial

    async def tracking_append(self, fragment, *, separator="\n\n"):
        append_sizes.append(len(fragment))
        return await original_append(self, fragment, separator=separator)

    replace_calls: list[int] = []

    async def tracking_replace(self, content):
        replace_calls.append(len(content))
        return await original_replace(self, content)

    map_results = [
        MapChunkResult(0, "orig-a", "SUCCESS", "MAP_FRAG_A unique"),
        MapChunkResult(1, "orig-b", "SUCCESS", "MAP_FRAG_B unique"),
    ]

    async def fake_map(chunks, prompt, model, language, callback=None):
        # Mimic real MAP: flush one fragment at a time (not a full join).
        if callback:
            for item in map_results:
                await callback(item.summary_text)
        return map_results, 20

    async def fake_reduce(*args, **kwargs):
        return "REDUCED_FINAL_UNIQUE_TOKEN", 8

    decision = MagicMock()
    decision.route = "hierarchical"
    decision.output_target_tokens = 400
    decision.output_min_tokens = 100
    decision.output_hard_limit = 8192
    decision.requires_section_assembly = False
    decision.section_keep_ratio = 0.55

    with ExitStack() as stack:
        stack.enter_context(
            patch.object(SummaryArtifactManager, "append_partial", new=tracking_append)
        )
        stack.enter_context(
            patch.object(
                SummaryArtifactManager, "replace_partial", new=tracking_replace
            )
        )
        stack.enter_context(
            patch.object(service.directory_manager, "validate_paths", new=AsyncMock())
        )
        stack.enter_context(
            patch.object(
                service.directory_manager,
                "read_pdf",
                new=AsyncMock(return_value=["page " * 500]),
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
            patch.object(
                service, "chunk_text", new=AsyncMock(return_value=["c0", "c1"])
            )
        )
        stack.enter_context(
            patch.object(service, "run_map_phase", side_effect=fake_map)
        )
        stack.enter_context(
            patch.object(service, "run_reduce_phase", side_effect=fake_reduce)
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
    # Two MAP fragments appended individually (not one giant join of both).
    assert len(append_sizes) == 2
    assert all(size < 100 for size in append_sizes)
    # REDUCE replaced the partial with the final synthesis.
    assert any(size >= len("REDUCED_FINAL_UNIQUE_TOKEN") for size in replace_calls)
    assert (tmp_path / "summary.md").exists()
    assert not (tmp_path / "summary.md.partial").exists()
    assert "REDUCED_FINAL_UNIQUE_TOKEN" in (tmp_path / "summary.md").read_text(
        encoding="utf-8"
    )


@pytest.mark.asyncio
async def test_failure_does_not_leave_summary_md_as_success(service, tmp_path):
    decision = MagicMock()
    decision.route = "direct"
    decision.output_target_tokens = 100

    async def boom_direct(*args, **kwargs):
        raise RuntimeError("provider exploded mid-generation")

    with ExitStack() as stack:
        stack.enter_context(
            patch.object(service.directory_manager, "validate_paths", new=AsyncMock())
        )
        stack.enter_context(
            patch.object(
                service.directory_manager,
                "read_pdf",
                new=AsyncMock(return_value=["hello world " * 40]),
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
            patch.object(service, "run_direct_summary", side_effect=boom_direct)
        )
        stack.enter_context(
            patch.object(
                service.advanced_prompt_generator,
                "get_direct_summary_prompt",
                new=AsyncMock(return_value="direct"),
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

    assert resp.success is False
    assert resp.status == "FAILED"
    assert not (tmp_path / "summary.md").exists()
    # Default policy: temps cleaned on failure (BREVIO_KEEP_PARTIALS=false).
    assert not (tmp_path / "summary.md.partial").exists()
