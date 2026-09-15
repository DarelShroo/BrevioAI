import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio.services.summary_service import MapChunkResult, SummaryService
from core.shared.enums.model import ModelType
from core.shared.utils.adaptive_salience_policy import (
    AdaptiveSaliencePolicy,
    SummaryPolicyDecision,
)


@pytest.fixture
def summary_service():
    service = SummaryService()
    return service


@pytest.mark.asyncio
async def test_cleanup_temp_files_removes_partial_and_bak(summary_service, tmp_path):
    summary_path = str(tmp_path / "summary.md")
    partial_file = summary_path + ".partial"
    bak_file = summary_path + ".partial.bak"

    # Create dummy temp files
    with open(partial_file, "w", encoding="utf-8") as f:
        f.write("partial content")
    with open(bak_file, "w", encoding="utf-8") as f:
        f.write("backup content")

    assert os.path.exists(partial_file)
    assert os.path.exists(bak_file)

    mock_file_config = MagicMock()
    mock_file_config.content = "Texto de prueba para el resumen. " * 30
    mock_file_config.summary_path = summary_path
    mock_file_config.token_count = 100
    mock_file_config.document_path = str(tmp_path / "doc.pdf")

    prompt_config = PromptConfig(
        language=LanguageType.SPANISH,
        category=CategoryType.SIMPLE_SUMMARY.value,
        style=StyleType.SIMPLE_SUMMARY_DEFAULT.value,
        format=OutputFormatType.MARKDOWN,
        summary_level=SummaryLevel.DETAILED,
        model=ModelType.GPT_4O_MINI,
    )

    clean_summary = "# Resumen\n\nContenido de prueba coherente y completo."

    with patch.object(
        summary_service, "chunk_text", new=AsyncMock(return_value=["chunk1"])
    ), patch.object(
        summary_service,
        "run_direct_summary",
        new=AsyncMock(return_value=(clean_summary, 50)),
    ), patch.object(
        summary_service,
        "run_map_phase",
        new=AsyncMock(
            return_value=(
                [MapChunkResult(0, "chunk1 original", "SUCCESS", "chunk summary")],
                50,
            )
        ),
    ), patch.object(
        summary_service,
        "run_reduce_phase",
        new=AsyncMock(return_value=(clean_summary, 50)),
    ), patch.object(
        summary_service,
        "run_formatting_phase",
        new=AsyncMock(return_value=(clean_summary, 50)),
    ), patch.object(
        summary_service.directory_manager, "write_summary", new=AsyncMock()
    ), patch.object(
        summary_service.directory_manager, "create_docx_version", new=AsyncMock()
    ), patch.object(
        summary_service.directory_manager,
        "read_pdf",
        new=AsyncMock(return_value=[mock_file_config.content]),
    ), patch.object(
        summary_service.directory_manager, "validate_paths", new=AsyncMock()
    ):
        response = await summary_service._process_single_document(
            prompt="prompt",
            file_config=mock_file_config,
            model=ModelType.GPT_4O_MINI,
            prompt_config=prompt_config,
        )

        assert response.success is True
        # Both .partial and .partial.bak must be deleted from disk
        assert not os.path.exists(partial_file)
        assert not os.path.exists(bak_file)


@pytest.mark.asyncio
async def test_map_callback_does_not_create_bak_file(summary_service, tmp_path):
    summary_path = str(tmp_path / "summary.md")
    partial_file = summary_path + ".partial"
    bak_file = summary_path + ".partial.bak"

    captured_callback = None

    async def fake_run_map_phase(*args, **kwargs):
        nonlocal captured_callback
        captured_callback = kwargs.get("callback")
        if captured_callback:
            await captured_callback("parcial intermedio")
            assert os.path.exists(partial_file)
            assert not os.path.exists(bak_file), ".partial.bak should never be created"
        return [MapChunkResult(0, "chunk1 original", "SUCCESS", "chunk summary")], 50

    mock_file_config = MagicMock()
    mock_file_config.content = "Texto de prueba para el resumen. " * 30
    mock_file_config.summary_path = summary_path
    mock_file_config.token_count = 100
    mock_file_config.document_path = str(tmp_path / "doc.pdf")

    prompt_config = PromptConfig(
        language=LanguageType.SPANISH,
        category=CategoryType.SIMPLE_SUMMARY.value,
        style=StyleType.SIMPLE_SUMMARY_DEFAULT.value,
        format=OutputFormatType.MARKDOWN,
        summary_level=SummaryLevel.DETAILED,
        model=ModelType.GPT_4O_MINI,
    )

    clean_summary = "# Resumen\n\nContenido de prueba coherente y completo."
    hierarchical = SummaryPolicyDecision(
        level=SummaryLevel.DETAILED,
        semantic_profile="",
        length_instruction="",
        coverage_instruction="",
        output_min_tokens=10,
        output_target_tokens=50,
        output_max_tokens=100,
        output_hard_limit=100,
        route="hierarchical",
        requires_hierarchical_reduce=True,
        requires_section_assembly=False,
        section_keep_ratio=0.55,
    )

    with patch.object(
        AdaptiveSaliencePolicy, "budget", return_value=hierarchical
    ), patch.object(
        summary_service, "chunk_text", new=AsyncMock(return_value=["chunk1"])
    ), patch.object(
        summary_service,
        "run_direct_summary",
        new=AsyncMock(return_value=(clean_summary, 50)),
    ), patch.object(
        summary_service, "run_map_phase", side_effect=fake_run_map_phase
    ), patch.object(
        summary_service,
        "run_reduce_phase",
        new=AsyncMock(return_value=(clean_summary, 50)),
    ), patch.object(
        summary_service,
        "run_formatting_phase",
        new=AsyncMock(return_value=(clean_summary, 50)),
    ), patch.object(
        summary_service.directory_manager, "write_summary", new=AsyncMock()
    ), patch.object(
        summary_service.directory_manager, "create_docx_version", new=AsyncMock()
    ), patch.object(
        summary_service.directory_manager,
        "read_pdf",
        new=AsyncMock(return_value=[mock_file_config.content]),
    ), patch.object(
        summary_service.directory_manager, "validate_paths", new=AsyncMock()
    ):
        response = await summary_service._process_single_document(
            prompt="prompt",
            file_config=mock_file_config,
            model=ModelType.GPT_4O_MINI,
            prompt_config=prompt_config,
        )

        assert response.success is True
        # Upon completion, even .partial must be cleaned up
        assert not os.path.exists(partial_file)
        assert not os.path.exists(bak_file)
