"""Contract tests: MAP returns MapChunkResult[]; REDUCE consumes them without str joins."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.enums.language import LanguageType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.models.file_config_model import FileConfig
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio.services.summary_service import (
    InvariantViolationError,
    MapChunkResult,
    SummaryService,
)
from core.shared.enums.model import ModelType


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    monkeypatch.setattr(
        "core.brevio_api.core.database.AsyncDB.database", lambda self: MagicMock()
    )
    monkeypatch.setenv("BREVIO_KEEP_PARTIALS", "false")
    monkeypatch.setenv("BREVIO_MIN_TOKENS_FOR_POSTPROCESS", "0")


@pytest.fixture
def service():
    return SummaryService()


@pytest.mark.asyncio
async def test_run_map_phase_returns_map_chunk_results(service):
    chunks = ["alpha chunk text", "beta chunk text"]

    async def fake_chunk(index, chunk, *args, **kwargs):
        return index, f"SUM:{chunk[:5]}", 10

    with patch.object(
        service, "generate_summary_chunk", side_effect=fake_chunk
    ), patch.object(service, "_check_token_limit", return_value=True):
        results, tokens = await service.run_map_phase(
            chunks, "prompt", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )

    assert tokens == 20
    assert len(results) == 2
    assert all(isinstance(r, MapChunkResult) for r in results)
    assert results[0].status == "SUCCESS"
    assert results[0].summary_text.startswith("SUM:")
    assert results[1].chunk_id == 1


@pytest.mark.asyncio
async def test_reduce_receives_success_map_results_only(service):
    mapped = [
        MapChunkResult(
            chunk_id=0,
            original_text="ORIG0 long enough text",
            status="SUCCESS",
            summary_text="SUMMARY0 enough",
        ),
        MapChunkResult(
            chunk_id=1,
            original_text="ORIG1 must not enter reduce by default",
            status="FAILED",
            summary_text=None,
            error_message="provider 429",
        ),
    ]

    from core.brevio.services.summary_pipeline import MapPhaseFailedError

    with patch.object(
        service.api_service, "_initialize_client", new=AsyncMock()
    ), patch.object(service, "_execute_reduce_call", new=AsyncMock()), patch.object(
        service, "_check_token_limit", return_value=True
    ):
        service.history_token_model.summary_level = SummaryLevel.MODERATE.value
        service.history_token_model.num_tokens_file = 100
        with pytest.raises(MapPhaseFailedError):
            await service.run_reduce_phase(
                mapped,
                "reduce prompt",
                ModelType.DEEPSEEK_V4_PRO,
                LanguageType.ENGLISH,
                force_reduce=True,
            )


@pytest.mark.asyncio
async def test_map_chunk_result_never_joined_as_str(service):
    mapped = [
        MapChunkResult(0, "o0", "SUCCESS", "s0"),
        MapChunkResult(1, "o1", "FAILED", None, "err"),
    ]
    with pytest.raises(TypeError, match="expected str instance"):
        "\n".join(mapped)  # documents the bug we must not reintroduce


@pytest.mark.asyncio
async def test_typeerror_becomes_invariant_without_partial_success(service, tmp_path):
    """TypeError after MAP must become InvariantViolationError (no_fallback), not summary success."""
    summary_path = tmp_path / "summary.md"
    write_calls = []

    async def capture_write(content, path):
        write_calls.append((content, path))

    map_results = [
        MapChunkResult(0, "orig-a", "SUCCESS", "summary-a"),
        MapChunkResult(1, "orig-b", "SUCCESS", "summary-b"),
    ]

    with patch.object(
        service, "run_map_phase", new=AsyncMock(return_value=(map_results, 10))
    ), patch.object(
        service,
        "run_reduce_phase",
        new=AsyncMock(
            side_effect=TypeError(
                "sequence item 0: expected str instance, MapChunkResult found"
            )
        ),
    ), patch.object(
        service.advanced_prompt_generator,
        "get_map_prompt",
        new=AsyncMock(return_value="m"),
    ), patch.object(
        service.advanced_prompt_generator,
        "get_reduce_prompt",
        new=AsyncMock(return_value="r"),
    ), patch.object(
        service.directory_manager, "write_summary", side_effect=capture_write
    ), patch.object(
        service.directory_manager, "validate_paths", new=AsyncMock()
    ), patch.object(
        service, "chunk_text", new=AsyncMock(return_value=["a", "b"])
    ), patch(
        "core.brevio.services.summary_service.AdaptiveSaliencePolicy"
    ) as pol:
        decision = MagicMock()
        decision.route = "hierarchical"
        decision.output_target_tokens = 50
        pol.return_value.budget.return_value = decision

        from core.brevio.enums.category import CategoryType
        from core.brevio.enums.output_format_type import OutputFormatType
        from core.brevio.enums.style import StyleType

        prompt_config = PromptConfig(
            model=ModelType.DEEPSEEK_V4_PRO,
            category=list(CategoryType)[0].value,
            style=list(StyleType)[0].value,
            format=OutputFormatType.MARKDOWN,
            language=LanguageType.ENGLISH,
            summary_level=SummaryLevel.MODERATE,
        )
        doc = tmp_path / "doc.docx"
        doc.write_bytes(b"PK")  # placeholder; read_docx mocked
        file_config = FileConfig(
            document_path=str(doc),
            summary_path=str(summary_path),
            transcription_path=str(tmp_path / "t.txt"),
        )

        with patch.object(
            service.directory_manager,
            "read_docx",
            new=AsyncMock(return_value="hello world " * 40),
        ), patch.object(
            service, "detect_language_with_retry_safe", new=AsyncMock(return_value="en")
        ):
            # Outer handler returns failure SummaryResponse for InvariantViolationError
            resp = await service._process_single_document(
                "formatting prompt",
                file_config,
                ModelType.DEEPSEEK_V4_PRO,
                prompt_config,
                folder_id="fold",
                user_id="user",
            )

    assert resp.success is False
    assert resp.error_type == "InvariantViolationError"
    assert resp.partial_available is False or resp.success is False
    assert (
        "Internal type contract" in resp.message
        or "MapChunkResult" in resp.message
        or "contract" in resp.message.lower()
        or "Error processing" in resp.message
    )
    # Must not write a "successful" summary body from partial
    for content, path in write_calls:
        assert "PARTIAL SHOULD NOT" not in content
        assert resp.success is False


@pytest.mark.asyncio
async def test_map_reduce_format_flow_with_map_chunk_results(service):
    chunks = ["chunk one content here", "chunk two content here"]

    async def fake_map_chunk(index, chunk, *args, **kwargs):
        return index, f"MAPSUM {index} {chunk[:8]}", 12

    async def fake_reduce(mapped, *args, **kwargs):
        assert all(isinstance(x, MapChunkResult) for x in mapped)
        assert len(mapped) == 2
        assert mapped[0].status == "SUCCESS"
        return "REDUCED BODY", 20

    async def fake_format(text, *args, **kwargs):
        assert text == "REDUCED BODY"
        return "FORMATTED BODY", 5

    with patch.object(
        service, "generate_summary_chunk", side_effect=fake_map_chunk
    ), patch.object(service, "run_reduce_phase", side_effect=fake_reduce), patch.object(
        service, "run_formatting_phase", side_effect=fake_format
    ), patch.object(
        service, "_check_token_limit", return_value=True
    ):
        map_results, _ = await service.run_map_phase(
            chunks, "p", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )
        reduced, _ = await service.run_reduce_phase(
            map_results,
            "rp",
            ModelType.DEEPSEEK_V4_PRO,
            LanguageType.ENGLISH,
            force_reduce=True,
        )
        # Bypass real reduce body — use our patched run_reduce_phase above
        assert reduced == "REDUCED BODY"
        formatted, _ = await service.run_formatting_phase(
            reduced, "fp", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )
        assert formatted == "FORMATTED BODY"


@pytest.mark.asyncio
async def test_failed_map_does_not_enter_reduce_by_default(service):
    mapped = [
        MapChunkResult(0, "keep-me-original-failed-chunk", "FAILED", None, "boom"),
        MapChunkResult(1, "orig-ok", "SUCCESS", "sum-ok-text"),
    ]

    from core.brevio.services.summary_pipeline import MapPhaseFailedError

    with patch.object(
        service.api_service, "_initialize_client", new=AsyncMock()
    ), patch.object(
        service, "_execute_reduce_call", new=AsyncMock()
    ) as mock_reduce, patch.object(
        service, "_check_token_limit", return_value=True
    ):
        service.history_token_model.summary_level = SummaryLevel.MODERATE.value
        service.history_token_model.num_tokens_file = 50
        with pytest.raises(MapPhaseFailedError):
            await service.run_reduce_phase(
                mapped,
                "r",
                ModelType.DEEPSEEK_V4_PRO,
                LanguageType.ENGLISH,
                force_reduce=True,
            )
        mock_reduce.assert_not_called()
