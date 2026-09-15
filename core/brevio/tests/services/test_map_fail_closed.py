"""Failed MAP chunks must not silently enter REDUCE as original_text."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.enums.language import LanguageType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.services.summary_pipeline import MapPhaseFailedError, PipelinePhase
from core.brevio.services.summary_service import MapChunkResult, SummaryService
from core.shared.enums.model import ModelType


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    monkeypatch.setattr(
        "core.brevio_api.core.database.AsyncDB.database", lambda self: MagicMock()
    )
    monkeypatch.setenv("BREVIO_ALLOW_MAP_ORIGINAL_TEXT_FALLBACK", "false")


@pytest.fixture
def service():
    return SummaryService()


@pytest.mark.asyncio
async def test_map_quota_failure_does_not_enter_reduce(service):
    mapped = [
        MapChunkResult(0, "summarized ok", "SUCCESS", "MAP SUMMARY 0"),
        MapChunkResult(
            1, "ORIGINAL PDF CHUNK MUST NOT ENTER REDUCE", "FAILED", None, "429"
        ),
    ]
    with patch.object(
        service, "_execute_reduce_call", new=AsyncMock()
    ) as mock_reduce, patch.object(
        service, "_check_token_limit", return_value=True
    ), patch.object(
        service.api_service, "_initialize_client", new=AsyncMock()
    ):
        service.history_token_model.summary_level = SummaryLevel.MODERATE.value
        with pytest.raises(MapPhaseFailedError) as exc:
            await service.run_reduce_phase(
                mapped,
                "reduce",
                ModelType.DEEPSEEK_V4_PRO,
                LanguageType.ENGLISH,
                force_reduce=True,
            )
        mock_reduce.assert_not_called()
    assert (
        "original_text fallback" in str(exc.value).lower()
        or "failed" in str(exc.value).lower()
    )
    assert exc.value.phase == PipelinePhase.MAP_FAILED.value


@pytest.mark.asyncio
async def test_explicit_fallback_still_allows_original_text(service, monkeypatch):
    monkeypatch.setenv("BREVIO_ALLOW_MAP_ORIGINAL_TEXT_FALLBACK", "true")
    mapped = [
        MapChunkResult(0, "orig-ok", "SUCCESS", "sum-ok-text"),
        MapChunkResult(1, "keep-me-original-failed-chunk", "FAILED", None, "boom"),
    ]
    captured = []

    async def capture_reduce(batch_text, *args, **kwargs):
        captured.append(batch_text)
        return "out", 1, "stop"

    with patch.object(
        service.api_service, "_initialize_client", new=AsyncMock()
    ), patch.object(
        service, "_execute_reduce_call", side_effect=capture_reduce
    ), patch.object(
        service, "_check_token_limit", return_value=True
    ):
        service.history_token_model.summary_level = SummaryLevel.MODERATE.value
        await service.run_reduce_phase(
            mapped,
            "r",
            ModelType.DEEPSEEK_V4_PRO,
            LanguageType.ENGLISH,
            force_reduce=True,
        )

    blob = "\n".join(captured)
    assert "keep-me-original-failed-chunk" in blob
    assert "sum-ok-text" in blob
