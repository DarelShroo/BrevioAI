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
from core.brevio.utils.text_chunker import TextChunker
from core.shared.enums.model import ModelType
from core.brevio.models.dtos import ChunkProcessingRequest

@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set necessary environment variables for SummaryService."""
    monkeypatch.setenv("MAX_TOKENS", "1000")
    monkeypatch.setenv("MAX_TOKENS_PER_CHUNK", "250")
    monkeypatch.setenv("TOKENS_PER_MINUTE", "500")
    monkeypatch.setenv("TEMPERATURE", "0.7")
    monkeypatch.setenv("OPENAI_API_KEY", "fake_api_key")
    monkeypatch.setenv("MAX_TOKEN_WAIT", "1")


@pytest.fixture
def summary_service() -> SummaryService:
    """Provide an instance of SummaryService with a mocked AsyncOpenAI client."""
    with patch("core.brevio.services.summary_service.AsyncOpenAI") as mock_openai:
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        mock_openai.return_value = mock_client
        service = SummaryService()
        service.client = mock_client
        return service


def test_chunk_text() -> None:
    """Test that text is correctly split into chunks."""
    text = "0123456789" * 10
    chunk_size = 10
    overlap = 0.2
    chunks = TextChunker.chunk_text(
        text, chunk_size, overlap, ModelType.GPT_4
    )
    assert len(chunks) > 0
    for chunk in chunks:
        assert len(chunk) > 0


@pytest.mark.asyncio
async def test_check_token_limit_true(summary_service: SummaryService) -> None:
    """Test that check_token_limit returns True when enough tokens are available."""
    summary_service.token_manager.tokens_per_minute = 500
    summary_service.token_manager.token_bucket = 300
    summary_service.token_manager.last_token_reset = time.time()
    result = await summary_service.token_manager.check_token_limit(200)
    assert result is True


@pytest.mark.asyncio
async def test_generate_summary_chunk_success(
    summary_service: SummaryService, caplog: pytest.LogCaptureFixture
) -> None:
    """Test successful summary generation for a chunk via chunk_generator."""
    logger = logging.getLogger("core.brevio.services.summary_chunk_generator")
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
        request = ChunkProcessingRequest(
            index=0,
            chunk="Texto de prueba",
            prompt="Prompt de prueba",
            accumulated_summary="Resumen acumulado",
            model=ModelType.DEEPSEEK_CHAT,
            language=LanguageType.SPANISH
        )
        index, summary, tokens_used = await summary_service.chunk_generator.generate_chunk(
            request, summary_service.client
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
        request = ChunkProcessingRequest(
            index=1,
            chunk="Otro texto",
            prompt="Prompt",
            accumulated_summary="Acumulado",
            model=ModelType.DEEPSEEK_CHAT,
            language=LanguageType.SPANISH
        )
        index, summary, tokens_used = await summary_service.chunk_generator.generate_chunk(
            request, summary_service.client
        )

    assert index == 1
    assert summary is None
    assert tokens_used == 0


@pytest.mark.asyncio
async def test_process_chunks_in_groups(
    summary_service: SummaryService,
) -> None:
    """Test processing text chunks in groups and aggregating summaries."""
    chunks = ["Chunk 1", "Chunk 2"]
    prompt = "Prompt de prueba"

    async def fake_generate_chunk(
        request: ChunkProcessingRequest,
        client: AsyncOpenAI
    ) -> Tuple[int, str, int]:
        return request.index, f"Resumen: {request.chunk}", len(request.chunk)

    with patch.object(
        summary_service.chunk_generator,
        "generate_chunk",
        new=AsyncMock(side_effect=fake_generate_chunk),
    ), patch.object(summary_service.token_manager, "check_token_limit", return_value=True):
        (
            full_summary,
            total_tokens_used,
        ) = await summary_service.process_chunks_in_groups(
            chunks, prompt, ModelType.DEEPSEEK_CHAT, LanguageType.SPANISH
        )
        assert "Resumen: Chunk 1" in full_summary
        assert "Resumen: Chunk 2" in full_summary
        assert total_tokens_used == len("Chunk 1") + len("Chunk 2")


def test_summary_service_initialization(summary_service: SummaryService) -> None:
    """Test that SummaryService is initialized correctly."""
    assert summary_service is not None
    assert hasattr(summary_service, "max_tokens")
    assert hasattr(summary_service, "max_tokens_per_chunk")
    assert hasattr(summary_service, "temperature")
    assert summary_service.client is not None
    assert hasattr(summary_service, "chunk_generator")
    assert hasattr(summary_service, "post_processor")
    assert hasattr(summary_service, "document_processor")
