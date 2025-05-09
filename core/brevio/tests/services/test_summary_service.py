import logging
import time
from typing import Any, Tuple
from unittest.mock import AsyncMock, patch

import pytest

from core.brevio.services.summary_service import SummaryService
from core.shared.enums.model import ModelType
from core.shared.utils.model_tokens_utils import get_encoder


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set necessary environment variables for SummaryService."""
    monkeypatch.setenv("MAX_TOKENS", "1000")
    monkeypatch.setenv("MAX_TOKENS_PER_CHUNK", "250")
    monkeypatch.setenv("TOKENS_PER_MINUTE", "500")
    monkeypatch.setenv("TEMPERATURE", "0.7")
    monkeypatch.setenv("OPENAI_API_KEY", "fake_api_key")


@pytest.fixture
def summary_service() -> SummaryService:
    """Provide an instance of SummaryService for testing."""
    return SummaryService()


def test_chunk_text(summary_service: SummaryService) -> None:
    """Test that text is correctly split into chunks."""
    text = "0123456789" * 10  # 100 characters, ~34 tokens
    chunk_size = 10  # Token-based chunk size
    overlap = 0.2  # 20% overlap
    chunks = summary_service.chunk_text(text, chunk_size, overlap, ModelType.GPT_4)

    # Verify approximately 5 chunks are produced (34 tokens / (10 - 2) ≈ 4.25, rounded up)
    assert len(chunks) >= 4  # Adjust expectation based on token splitting
    # Ensure each chunk (except possibly the last) does not exceed chunk_size in tokens
    encoder = get_encoder(ModelType.GPT_4)
    for chunk in chunks[:-1]:
        assert len(encoder.encode(chunk)) <= chunk_size
    assert len(encoder.encode(chunks[-1])) <= chunk_size

    # Reconstruct the original text from chunks considering overlap
    reconstructed = chunks[0]
    overlap_chars = int(chunk_size * overlap * 3)  # Approximate chars per token
    for chunk in chunks[1:]:
        reconstructed += chunk[overlap_chars:]
    assert text.startswith(reconstructed[: len(text)])


@pytest.mark.asyncio
async def test_check_token_limit_true(summary_service: SummaryService) -> None:
    """Test that _check_token_limit returns True when enough tokens are available."""
    summary_service.tokens_per_minute = 500
    summary_service.token_bucket = 300
    summary_service.last_token_reset = time.time()
    result = await summary_service._check_token_limit(200)
    assert result is True


@pytest.mark.asyncio
async def test_check_token_limit_false(summary_service: SummaryService) -> None:
    """Test that _check_token_limit returns False when insufficient tokens are available."""
    summary_service.token_bucket = 50
    summary_service.last_token_reset = time.time()
    result = await summary_service._check_token_limit(200)
    assert result is False


@pytest.mark.asyncio
async def test_generate_summary_chunk_success(
    summary_service: SummaryService, caplog: pytest.LogCaptureFixture
) -> None:
    """Test successful summary generation for a chunk with a mocked response."""
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
        prompt_tokens: int = 100
        completion_tokens: int = 50

    mock_response = MockResponse()

    with patch(
        "core.brevio.services.summary_service.AsyncOpenAI", autospec=True
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.chat = AsyncMock()
        mock_client.chat.completions = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(
            summary_service, "_initialize_client", return_value=mock_client
        ):
            index, summary, tokens_used = await summary_service.generate_summary_chunk(
                0,
                "Texto de prueba",
                "Prompt de prueba",
                "Resumen acumulado",
                ModelType.DEEPSEEK_CHAT,
            )
            assert index == 0
            assert summary == "Resumen de prueba"
            assert tokens_used == 150
            assert (
                summary_service.token_bucket == summary_service.tokens_per_minute - 150
            )


@pytest.mark.asyncio
async def test_generate_summary_chunk_failure(
    summary_service: SummaryService,
) -> None:
    """Test error handling in generate_summary_chunk."""
    with patch(
        "core.brevio.services.summary_service.AsyncOpenAI", autospec=True
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.chat = AsyncMock()
        mock_client.chat.completions = AsyncMock()
        mock_client.chat.completions.create.side_effect = Exception("Error API")

        with patch.object(
            summary_service, "_initialize_client", return_value=mock_client
        ):
            index, summary, tokens_used = await summary_service.generate_summary_chunk(
                1, "Otro texto", "Prompt", "Acumulado", ModelType.DEEPSEEK_CHAT
            )
            assert index == 1
            assert "Error procesando chunk" in summary
            assert tokens_used == 0


@pytest.mark.asyncio
async def test_process_chunks_in_groups(
    summary_service: SummaryService,
) -> None:
    """Test processing text chunks in groups and aggregating summaries."""
    chunks = ["Chunk 1", "Chunk 2"]
    prompt = "Prompt de prueba"

    async def fake_generate_summary_chunk(
        index: int, chunk: str, prompt: str, acc: str, model: ModelType
    ) -> Tuple[int, str, int]:
        return index, f"Resumen: {chunk}", len(chunk)

    with patch.object(
        summary_service,
        "generate_summary_chunk",
        side_effect=fake_generate_summary_chunk,
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        (
            full_summary,
            total_tokens_used,
        ) = await summary_service.process_chunks_in_groups(
            chunks, prompt, ModelType.DEEPSEEK_CHAT
        )
        assert "Resumen: Chunk 1" in full_summary
        assert "Resumen: Chunk 2" in full_summary
        assert total_tokens_used == len("Chunk 1") + len("Chunk 2")
