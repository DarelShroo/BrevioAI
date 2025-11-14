import asyncio
import logging
import time
from typing import Any, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import AsyncOpenAI
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionMessage

from core.brevio.enums.language import LanguageType
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
    monkeypatch.setenv(
        "MAX_TOKEN_WAIT", "1"
    )  # Set a short wait time for testing timeouts


@pytest.fixture
def summary_service() -> SummaryService:
    """Provide an instance of SummaryService with a mocked AsyncOpenAI client."""
    with patch("core.brevio.services.summary_service.AsyncOpenAI") as mock_openai:
        # Create a properly structured mock client
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        mock_openai.return_value = mock_client
        service = SummaryService()
        service.client = mock_client
        return service


async def test_chunk_text(summary_service: SummaryService) -> None:
    """Test that text is correctly split into chunks."""
    text = "0123456789" * 10  # 100 characters, ~34 tokens
    chunk_size = 10  # Token-based chunk size
    overlap = 0.2  # 20% overlap
    chunks = await summary_service.chunk_text(
        text, chunk_size, overlap, ModelType.GPT_4
    )
    # Verificar que se crean chunks
    assert len(chunks) > 0
    # Verificar que cada chunk tiene contenido
    for chunk in chunks:
        assert len(chunk) > 0


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
    """Test that _check_token_limit raises TimeoutError when insufficient tokens are available and max_wait is exceeded."""
    summary_service.token_bucket = 50
    summary_service.last_token_reset = time.time()
    with pytest.raises(TimeoutError):
        await summary_service._check_token_limit(200)


@pytest.mark.asyncio
async def test_generate_summary_chunk_success(
    summary_service: SummaryService, caplog: pytest.LogCaptureFixture
) -> None:
    """Test successful summary generation for a chunk with a mocked response."""
    logger = logging.getLogger("core.brevio.services.summary_service")
    logger.setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock(spec=ChatCompletion)
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                spec=ChatCompletionMessage,
                content="Este es un resumen de prueba con suficientes palabras para pasar la validación",
            )
        )
    ]
    mock_response.usage = MagicMock(
        spec=CompletionUsage, total_tokens=150, prompt_tokens=100, completion_tokens=50
    )

    assert summary_service.client is not None

    with patch.object(
        summary_service.client.chat.completions,
        "create",
        new=AsyncMock(return_value=mock_response),
    ):
        index, summary, tokens_used = await summary_service.generate_summary_chunk(
            0,
            "Texto de prueba",
            "Prompt de prueba",
            "Resumen acumulado",
            ModelType.DEEPSEEK_CHAT,
            LanguageType.SPANISH,
        )

    assert index == 0
    assert (
        summary
        == "Este es un resumen de prueba con suficientes palabras para pasar la validación\n\n\u200b"
    )
    assert tokens_used == 150


@pytest.mark.asyncio
async def test_generate_summary_chunk_failure(
    summary_service: SummaryService,
) -> None:
    """Test error handling in generate_summary_chunk."""
    assert summary_service.client is not None
    with patch.object(
        summary_service.client.chat.completions,
        "create",
        new=AsyncMock(side_effect=Exception("Error API")),
    ):
        index, summary, tokens_used = await summary_service.generate_summary_chunk(
            1,
            "Otro texto",
            "Prompt",
            "Acumulado",
            ModelType.DEEPSEEK_CHAT,
            LanguageType.SPANISH,
        )

    assert index == 1
    assert summary is None  # Should return None on failure
    assert tokens_used == 0


@pytest.mark.asyncio
async def test_generate_summary_chunk_timeout(
    summary_service: SummaryService,
) -> None:
    """Test timeout handling in generate_summary_chunk."""
    assert summary_service.client is not None
    with patch.object(
        summary_service.client.chat.completions,
        "create",
        new=AsyncMock(side_effect=asyncio.TimeoutError("Timeout")),
    ):
        index, summary, tokens_used = await summary_service.generate_summary_chunk(
            2,
            "Texto con timeout",
            "Prompt",
            "Acumulado",
            ModelType.DEEPSEEK_CHAT,
            LanguageType.SPANISH,
        )

    assert index == 2
    assert summary is None  # Should return None on timeout
    assert tokens_used == 0


@pytest.mark.asyncio
async def test_process_chunks_in_groups(
    summary_service: SummaryService,
) -> None:
    """Test processing text chunks in groups and aggregating summaries."""
    chunks = ["Chunk 1", "Chunk 2"]
    prompt = "Prompt de prueba"

    async def fake_generate_summary_chunk(
        index: int,
        chunk: str,
        prompt: str,
        acc: str,
        model: ModelType,
        language: LanguageType,
    ) -> Tuple[int, str, int]:
        return index, f"Resumen: {chunk}", len(chunk)

    with patch.object(
        summary_service,
        "generate_summary_chunk",
        new=AsyncMock(side_effect=fake_generate_summary_chunk),
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        (
            full_summary,
            total_tokens_used,
        ) = await summary_service.process_chunks_in_groups(
            chunks, prompt, ModelType.DEEPSEEK_CHAT, LanguageType.SPANISH
        )
        assert "Resumen: Chunk 1" in full_summary
        assert "Resumen: Chunk 2" in full_summary
        assert total_tokens_used == len("Chunk 1") + len("Chunk 2")


@pytest.mark.asyncio
async def test_process_chunks_in_groups_with_callback(
    summary_service: SummaryService,
) -> None:
    """Test processing text chunks with callback function."""
    chunks = ["Chunk 1", "Chunk 2"]
    prompt = "Prompt de prueba"

    callback_calls = []

    async def mock_callback(summary: str) -> None:
        callback_calls.append(summary)

    async def fake_generate_summary_chunk(
        index: int,
        chunk: str,
        prompt: str,
        acc: str,
        model: ModelType,
        language: LanguageType,
    ) -> Tuple[int, str, int]:
        return index, f"Resumen: {chunk}", len(chunk)

    with patch.object(
        summary_service,
        "generate_summary_chunk",
        new=AsyncMock(side_effect=fake_generate_summary_chunk),
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        (
            full_summary,
            total_tokens_used,
        ) = await summary_service.process_chunks_in_groups(
            chunks, prompt, ModelType.DEEPSEEK_CHAT, LanguageType.SPANISH, mock_callback
        )
        assert "Resumen: Chunk 1" in full_summary
        assert "Resumen: Chunk 2" in full_summary
        assert len(callback_calls) > 0  # Callback should have been called


def test_summary_service_initialization(summary_service: SummaryService) -> None:
    """Test that SummaryService is initialized correctly."""
    assert summary_service is not None
    assert hasattr(summary_service, "max_tokens")
    assert hasattr(summary_service, "max_tokens_per_chunk")
    assert hasattr(summary_service, "temperature")
    assert summary_service.client is not None
    assert hasattr(summary_service.client, "chat")
    assert hasattr(summary_service.client.chat, "completions")
    assert hasattr(summary_service.client.chat.completions, "create")


@pytest.mark.asyncio
async def test_generate_summary_chunk_with_mock_patching(
    summary_service: SummaryService,
) -> None:
    """Test generate_summary_chunk using mock patching."""
    mock_response = MagicMock(spec=ChatCompletion)
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                spec=ChatCompletionMessage,
                content="Este es un resumen simulado con suficientes palabras para validación",
            )
        )
    ]
    mock_response.usage = MagicMock(
        spec=CompletionUsage, total_tokens=100, prompt_tokens=70, completion_tokens=30
    )

    assert summary_service.client is not None

    with patch.object(
        summary_service.client.chat.completions,
        "create",
        new=AsyncMock(return_value=mock_response),
    ):
        index, summary, tokens_used = await summary_service.generate_summary_chunk(
            0,
            "Test text",
            "Test prompt",
            "Accumulated summary",
            ModelType.DEEPSEEK_CHAT,
            LanguageType.SPANISH,
        )

    assert index == 0
    assert (
        summary
        == "Este es un resumen simulado con suficientes palabras para validación\n\n\u200b"
    )
    assert tokens_used == 100
