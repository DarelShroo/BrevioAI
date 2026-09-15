import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.services.rate_limiter import BrevioRateLimiter
from core.brevio.services.summary_service import SummaryService
from core.shared.enums.model import ModelType


@pytest.fixture
def summary_service():
    with patch("core.brevio.services.summary_service.ApiService"):
        service = SummaryService()
        return service


@pytest.mark.asyncio
async def test_rate_limiter_concurrency():
    """
    Test that the BrevioRateLimiter respects max_concurrency and RPM limits.
    """
    limiter = BrevioRateLimiter(
        requests_per_minute=5, tokens_per_minute=1000, max_concurrency=2
    )

    # We acquire 5 requests successfully
    for _ in range(5):
        await limiter.acquire(100)

    # The 6th request should block and wait because we ran out of requests per minute
    # We will simulate this using asyncio.wait_for and expect a timeout if it blocks properly.

    async def acquire_blocked():
        await limiter.acquire(100)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(acquire_blocked(), timeout=0.5)


@pytest.mark.asyncio
async def test_chunk_text_phantom_bug_fixed(summary_service):
    """
    Test that chunk_text does not produce a redundant trailing chunk when the
    document size perfectly matches the chunk size boundaries.
    """
    # Create a string that simulates exact bounds.
    # For testing, we mock get_encoder to just split by words or characters.
    with patch("core.brevio.services.summary_service.get_encoder") as mock_get_encoder:
        mock_encoder = MagicMock()

        # Simulate an encoder that works with lists of tokens (characters for simplicity)
        tokens = list(range(100))
        mock_encoder.encode.return_value = tokens
        # decode just joins the numbers for mock
        mock_encoder.decode.side_effect = lambda t: ",".join(map(str, t))
        mock_get_encoder.return_value = mock_encoder

        # chunk size = 50, overlap = 0.1 (5 tokens)
        chunks = await summary_service.chunk_text(
            "dummy text",
            chunk_size=50,
            overlap=0.1,
            model=ModelType.GEMINI_3_1_FLASH_LITE,
        )

        # Expected behavior:
        # chunk 1: 0 to 50
        # start = 50 - 5 = 45
        # chunk 2: 45 to 95
        # start = 95 - 5 = 90
        # chunk 3: 90 to 100
        # start = 100 - 5 = 95 -> end == len(tokens), so it should break and not create a chunk 4!

        assert len(chunks) == 3


@pytest.mark.asyncio
async def test_detect_language_with_retry_safe_falls_back_to_english(summary_service):
    """Language detection failure is a legitimate fallback to English, not a pipeline crash."""
    with patch("langdetect.detect", side_effect=Exception("Mocked langdetect failure")):
        detected = await summary_service.detect_language_with_retry_safe("Hola mundo")
    assert detected == "en"
