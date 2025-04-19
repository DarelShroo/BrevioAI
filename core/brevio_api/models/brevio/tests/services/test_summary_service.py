import logging
import time
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

import pytest

from core.brevio.services.summary_service import SummaryService


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should set necessary environment variables for SummaryService."""
    monkeypatch.setenv("MAX_TOKENS", "1000")
    monkeypatch.setenv("MAX_TOKENS_PER_CHUNK", "250")
    monkeypatch.setenv("TOKENS_PER_MINUTE", "500")
    monkeypatch.setenv("TEMPERATURE", "0.7")
    monkeypatch.setenv("OPENAI_API_KEY", "fake_api_key")


@pytest.fixture
def summary_service() -> SummaryService:
    """Should provide an instance of SummaryService for testing."""
    return SummaryService()


def test_chunk_text(summary_service: SummaryService) -> None:
    """Should correctly split text into chunks."""
    text = "0123456789" * 10  # 100 characters
    chunk_size = 30
    overlap = 5
    chunks = summary_service.chunk_text(text, chunk_size, overlap)

    # Should produce 5 chunks
    assert len(chunks) == 5
    # Should ensure each chunk (except possibly the last) does not exceed the chunk size
    for chunk in chunks[:-1]:
        assert len(chunk) <= chunk_size
    assert len(chunks[-1]) <= chunk_size

    # Should reconstruct the original text from the chunks considering the overlap
    reconstructed = chunks[0]
    for chunk in chunks[1:]:
        reconstructed += chunk[overlap:]
    assert text.startswith(reconstructed[: len(text)])


@pytest.mark.asyncio
async def test_check_token_limit_true(summary_service: SummaryService) -> None:
    """Should return True when there are enough tokens."""
    summary_service.token_bucket = 1000
    summary_service.last_token_reset = time.time()
    result = await summary_service._check_token_limit(200)
    assert result is True


@pytest.mark.asyncio
async def test_check_token_limit_false(summary_service: SummaryService) -> None:
    """Should return False when there are not enough tokens."""
    summary_service.token_bucket = 50
    summary_service.last_token_reset = time.time()
    result = await summary_service._check_token_limit(200)
    assert result is False


@pytest.mark.asyncio
async def test_generate_summary_chunk_success(
    summary_service: SummaryService, caplog: pytest.LogCaptureFixture
) -> None:
    """Should successfully generate a summary for a chunk with a mocked response."""
    logger = logging.getLogger("core.brevio.services.summary_service")
    logger.setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG)

    class MockResponse:
        def __init__(self) -> None:
            self.choices = [MockChoice()]
            self.usage = MockUsage()

    class MockChoice:
        def __init__(self) -> None:
            self.message = MockMessage()

    class MockMessage:
        content: str = "Resumen de prueba"

    class MockUsage:
        total_tokens: int = 150

    mock_response = MockResponse()

    async def mock_create(*args: Any, **kwargs: Any) -> MockResponse:
        return mock_response

    with patch.object(
        summary_service.client.chat.completions, "create", new=mock_create
    ):
        index, summary, tokens_used = await summary_service.generate_summary_chunk(
            0, "Texto de prueba", "Prompt de prueba", "Resumen acumulado"
        )
        # Should return index 0, the expected summary, and tokens used equal to 150
        assert index == 0
        assert summary == "Resumen de prueba"
        assert tokens_used == 150
        # Should reduce the token bucket by the tokens used
        assert summary_service.token_bucket == summary_service.tokens_per_minute - 150


@pytest.mark.asyncio
async def test_generate_summary_chunk_failure(
    summary_service: SummaryService,
) -> None:
    """Should handle errors in generate_summary_chunk and return appropriate values."""
    with patch.object(
        summary_service.client.chat.completions,
        "create",
        side_effect=Exception("Error API"),
    ):
        index, summary, tokens_used = await summary_service.generate_summary_chunk(
            1, "Otro texto", "Prompt", "Acumulado"
        )
        # Should return index 1, an error message in summary, and tokens_used as 0
        assert index == 1
        assert "Error procesando chunk" in summary
        assert tokens_used == 0


@pytest.mark.asyncio
async def test_process_chunks_in_groups(
    summary_service: SummaryService,
) -> None:
    """Should process text chunks in groups and aggregate the summaries correctly."""
    chunks = ["Chunk 1", "Chunk 2"]
    prompt = "Prompt de prueba"

    async def fake_generate_summary_chunk(
        index: int, chunk: str, prompt: str, acc: str
    ) -> Tuple[int, str, int]:
        # Should simulate generating a summary by returning a formatted summary and token count equal to the length of the chunk
        return index, f"Resumen: {chunk}", len(chunk)

    with patch.object(
        summary_service,
        "generate_summary_chunk",
        side_effect=fake_generate_summary_chunk,
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        (
            full_summary,
            total_tokens_used,
        ) = await summary_service.process_chunks_in_groups(chunks, prompt)

        # Should include the summaries from both chunks
        assert "Resumen: Chunk 1" in full_summary
        assert "Resumen: Chunk 2" in full_summary
        # Should sum the tokens used from both chunks correctly
        assert total_tokens_used == len("Chunk 1") + len("Chunk 2")
