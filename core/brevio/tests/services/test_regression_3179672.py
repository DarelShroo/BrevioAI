import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.brevio.enums.language import LanguageType
from core.brevio.services.summary_service import ReduceConvergenceError, SummaryService
from core.shared.enums.model import ModelType
from core.shared.models.history_token_model import HistoryTokenModel


@pytest.fixture
def summary_service():
    service = SummaryService()
    service.api_service = AsyncMock()
    service.api_service._initialize_client.return_value = AsyncMock()

    token_model = HistoryTokenModel(
        user_id="test_user",
        summary_level="MODERATE",
        num_tokens_file=1000,
        content_type="ARTICLE",
    )
    service.history_token_model = token_model
    service.max_concurrent_chunks = 1

    service.token_limiter = AsyncMock()
    service.token_bucket = 200000
    service.tokens_per_minute = 200000

    return service


@pytest.mark.asyncio
async def test_regression_3179672_no_raw_fallback(summary_service):
    """
    Test that REDUCE coverage failure throws ReduceConvergenceError instead of
    appending all RAW chunks and leading to massive requested_output.
    """
    # Force the reduce calls to fail with length, which will cause splitting and eventually error out
    # without entering the destructive fallback RAW mode that used to exist.
    summary_service._execute_reduce_call = AsyncMock(return_value=("", 0, "length"))

    mapped_summaries = ["Chunk 1", "Chunk 2", "Chunk 3"]

    with pytest.raises(ReduceConvergenceError) as exc_info:
        await summary_service.run_reduce_phase(
            mapped_summaries=mapped_summaries,
            reduce_prompt="Test prompt",
            model=ModelType.DEEPSEEK_FLASH,
            language=LanguageType.ENGLISH,
        )

    assert "ReduceConvergenceError" in str(exc_info.type)
    # Ensure token bucket hasn't exploded
    assert summary_service.token_bucket > 0


@pytest.mark.asyncio
async def test_native_max_vs_requested_output(summary_service):
    """
    Verify that _safe_completion_token_limit uses requested_output correctly
    and separates it from native max.
    """
    limit = summary_service._safe_completion_token_limit(
        model=ModelType.DEEPSEEK_FLASH,
        system_tokens=100,
        user_tokens=100,
        requested_output_tokens=5000,
        reserved_tokens=500,
    )
    assert limit == 5000

    limit = summary_service._safe_completion_token_limit(
        model=ModelType.GEMINI_3_1_FLASH_LITE,
        system_tokens=100,
        user_tokens=100,
        requested_output_tokens=100000,
        reserved_tokens=500,
    )
    assert limit == 16384
