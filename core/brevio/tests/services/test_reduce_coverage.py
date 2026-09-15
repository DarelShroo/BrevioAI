import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.enums.language import LanguageType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.services.summary_service import (
    ReduceChunk,
    ReduceResult,
    SummaryService,
)
from core.shared.enums.model import ModelType
from core.shared.utils.model_capabilities import ModelCapabilities


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set necessary environment variables for SummaryService."""
    monkeypatch.setenv("MAX_TOKENS", "1000000")
    monkeypatch.setenv("MAX_TOKEN_PER_MINUTE", "1000000")
    monkeypatch.setenv("TEMPERATURE", "0.7")
    monkeypatch.setenv("OPENAI_API_KEY", "fake_api_key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake_api_key")
    monkeypatch.setenv("MAX_TOKEN_WAIT", "1")


@pytest.fixture
def summary_service() -> SummaryService:
    with patch("core.brevio.services.summary_service.AsyncOpenAI") as mock_openai:
        mock_client = AsyncMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        mock_openai.return_value = mock_client
        service = SummaryService()
        service.client = mock_client
        service.api_service._initialize_client = AsyncMock(return_value=mock_client)
        service.token_bucket = 1000000
        service.rpm_bucket = 1000000
        service.history_token_model.user_id = "test_user_id"
        return service


@pytest.mark.asyncio
async def test_reduce_small_single_batch(summary_service):
    """Test 1: A small set of chunks that fits in a single batch (100% coverage)."""
    chunks = [
        "Capítulo 1: Introducción a la ciencia y el método experimental.",
        "Capítulo 2: Pautas para la investigación científica rigurosa.",
        "Capítulo 3: La formulación de hipótesis comprobables.",
    ]

    async def mock_execute(
        batch_text,
        prompt,
        model,
        client,
        target_max_tokens=None,
        language=None,
        *args,
        **kwargs,
    ):
        return "Resumen integral de los tres capítulos iniciales.", 150, "stop"

    with patch.object(
        summary_service, "_execute_reduce_call", new=AsyncMock(side_effect=mock_execute)
    ):
        result = await summary_service.run_reduce_phase(
            mapped_summaries=chunks,
            reduce_prompt="Sintetiza la información.",
            model=ModelType.DEEPSEEK_V4_PRO,
            language=LanguageType.SPANISH,
            force_reduce=True,
        )

    assert isinstance(result, ReduceResult)
    # Check 100% coverage of all 3 chunks
    assert result.source_chunk_indices == [0, 1, 2]
    assert "Resumen integral" in result.text
    # Check backwards compatibility tuple unpacking
    text, tokens = result
    assert text == result.text
    assert tokens == result.tokens


@pytest.mark.asyncio
async def test_reduce_large_multi_batch_hierarchical(summary_service):
    """Test 2: A large set of chunks exceeding a single batch input budget (hierarchical reduction, 100% coverage)."""
    # 10 chunks, each ~1,000 tokens
    # Total ~10,000 tokens > deepseek-v4-pro reduce_input_token_budget (6,000 tokens)
    chunk_text = (
        "Contenido científico extenso sobre teoría y experimentación filosófica. " * 60
    )
    chunks = [f"Chunk {i}: {chunk_text}" for i in range(10)]

    call_count = 0

    async def mock_execute(
        batch_text,
        prompt,
        model,
        client,
        target_max_tokens=None,
        language=None,
        *args,
        **kwargs,
    ):
        nonlocal call_count
        call_count += 1
        return f"Resumen del lote reducción llamada {call_count}.", 200, "stop"

    with patch.object(
        summary_service, "_execute_reduce_call", new=AsyncMock(side_effect=mock_execute)
    ):
        result = await summary_service.run_reduce_phase(
            mapped_summaries=chunks,
            reduce_prompt="Sintetiza la información.",
            model=ModelType.DEEPSEEK_V4_PRO,
            language=LanguageType.SPANISH,
            force_reduce=True,
        )

    assert isinstance(result, ReduceResult)
    # All 10 original chunks (0 to 9) must be represented in the final result
    assert result.source_chunk_indices == list(range(10))
    # Must have required more than 1 call because of hierarchical reduction
    assert call_count > 1


@pytest.mark.asyncio
async def test_reduce_output_limited_truncation_detection_and_recovery(summary_service):
    """Test 3: Simulated truncation with finish_reason='length' triggers batch splitting and recovers 100% coverage."""
    chunk_a = "Parte 1: Epistemología y lógica de la ciencia moderna. " * 10
    chunk_b = "Parte 2: Metodología experimental y contrastación de hipótesis. " * 10
    chunks = [chunk_a, chunk_b]

    attempts = 0

    async def mock_execute(
        batch_text,
        prompt,
        model,
        client,
        target_max_tokens=None,
        language=None,
        *args,
        **kwargs,
    ):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            # First attempt: model hits token limit prematurely (finish_reason='length')
            return "Parte 1 resumida pero cortada a la mitad...", 100, "length"
        else:
            # Subdivided attempts: succeed cleanly
            return f"Sub-resumen exitoso intento {attempts}.", 60, "stop"

    with patch.object(
        summary_service, "_execute_reduce_call", new=AsyncMock(side_effect=mock_execute)
    ):
        result = await summary_service.run_reduce_phase(
            mapped_summaries=chunks,
            reduce_prompt="Sintetiza la información.",
            model=ModelType.DEEPSEEK_V4_PRO,
            language=LanguageType.SPANISH,
            force_reduce=False,
        )

    assert isinstance(result, ReduceResult)
    # Both chunks must be preserved despite first attempt truncation
    assert result.source_chunk_indices == [0, 1]
    assert attempts >= 3  # Initial + 2 split batches


@pytest.mark.asyncio
async def test_bunge_simulation_23_chunks_coverage(summary_service):
    """Test 4: Bunge simulation with 23 MAP chunks totaling ~17.6k tokens with deepseek-v4-pro.
    Validates that:
    1. It splits into multiple batches in Level 1 (since 17.6k > 6k budget).
    2. Hierarchical reduction finishes with 23/23 chunks represented (100% coverage).
    """
    chunk_body = (
        "Conceptos de Mario Bunge sobre ciencia formal, ciencia fáctica y método experimental. "
        * 35
    )
    chunks = [f"[Chunk MAP {i}] {chunk_body}" for i in range(23)]

    call_records = []

    async def mock_execute(
        batch_text,
        prompt,
        model,
        client,
        target_max_tokens=None,
        language=None,
        *args,
        **kwargs,
    ):
        call_records.append(len(batch_text))
        return (
            f"Resumen sintetizado del nivel correspondiente (llamada {len(call_records)}).",
            400,
            "stop",
        )

    with patch.object(
        summary_service, "_execute_reduce_call", new=AsyncMock(side_effect=mock_execute)
    ):
        result = await summary_service.run_reduce_phase(
            mapped_summaries=chunks,
            reduce_prompt="Sintetiza la información.",
            model=ModelType.DEEPSEEK_V4_PRO,
            language=LanguageType.SPANISH,
            force_reduce=True,
        )

    assert isinstance(result, ReduceResult)
    # The crucial invariant: all 23 chunks must be preserved without silent loss
    assert result.source_chunk_indices == list(range(23))
    assert len(result.source_chunk_indices) == 23

    # Must have executed hierarchical reduction across multiple batches (level 1 + level 2)
    # 17.6k tokens / 6k batch limit = ~3-4 batches at level 1, then level 2
    assert len(call_records) >= 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "level",
    [
        SummaryLevel.VERY_CONCISE,
        SummaryLevel.MODERATE,
        SummaryLevel.VERY_DETAILED,
    ],
)
async def test_summary_levels_maintain_full_coverage(summary_service, level):
    """Test 5: Check that summary_levels (very_concise, moderate, very_detailed) maintain 100% coverage without collapse."""
    summary_service.history_token_model.summary_level = level.value
    chunk_text = (
        "Desarrollo filosófico y metodológico sobre epistemología científica. " * 30
    )
    chunks = [f"Bloque {i}: {chunk_text}" for i in range(12)]

    call_count = 0

    async def mock_execute(
        batch_text,
        prompt,
        model,
        client,
        target_max_tokens=None,
        language=None,
        *args,
        **kwargs,
    ):
        nonlocal call_count
        call_count += 1
        return f"Síntesis de bloque llamada {call_count}.", 150, "stop"

    with patch.object(
        summary_service, "_execute_reduce_call", new=AsyncMock(side_effect=mock_execute)
    ):
        result = await summary_service.run_reduce_phase(
            mapped_summaries=chunks,
            reduce_prompt="Sintetiza la información.",
            model=ModelType.DEEPSEEK_V4_PRO,
            language=LanguageType.SPANISH,
            force_reduce=True,
        )

    assert isinstance(result, ReduceResult)
    assert result.source_chunk_indices == list(range(12))
    assert len(result.source_chunk_indices) == 12


def test_reduce_batch_token_limit_calculation(summary_service):
    """Verify that _reduce_batch_token_limit accurately respects reduce_input_token_budget."""
    # For deepseek-v4-pro: context=64000, native_max_output=8192, reduce_input_token_budget=6000
    limit_moderate = summary_service._reduce_batch_token_limit(
        ModelType.DEEPSEEK_V4_PRO, SummaryLevel.MODERATE, 200
    )
    assert 5000 <= limit_moderate <= 7000

    # Very detailed has a smaller input budget multiplier (0.85) to allow more detail per token
    limit_detailed = summary_service._reduce_batch_token_limit(
        ModelType.DEEPSEEK_V4_PRO, SummaryLevel.VERY_DETAILED, 200
    )
    assert limit_detailed < limit_moderate

    # Very concise has a larger multiplier (1.1)
    limit_concise = summary_service._reduce_batch_token_limit(
        ModelType.DEEPSEEK_V4_PRO, SummaryLevel.VERY_CONCISE, 200
    )
    assert limit_concise > limit_moderate


@pytest.mark.asyncio
async def test_intermediate_reduce_prompt_does_not_force_heavy_undershoot(
    summary_service,
):
    """L1 must aim for ~55% remaining length, not 'compress heavily' / never-more."""
    chunk_text = (
        "Conceptos de Mario Bunge sobre ciencia formal, ciencia fáctica y método experimental. "
        * 60
    )
    chunks = [f"Chunk {i}: {chunk_text}" for i in range(10)]
    captured_prompts = []

    async def mock_execute(
        batch_text,
        prompt,
        model,
        client,
        target_max_tokens=None,
        language=None,
        *args,
        **kwargs,
    ):
        captured_prompts.append(prompt)
        return f"Resumen sintetizado llamada {len(captured_prompts)}.", 400, "stop"

    with patch.object(
        summary_service, "_execute_reduce_call", new=AsyncMock(side_effect=mock_execute)
    ):
        result = await summary_service.run_reduce_phase(
            mapped_summaries=chunks,
            reduce_prompt="Sintetiza la información.",
            model=ModelType.GEMINI_3_1_FLASH_LITE,
            language=LanguageType.SPANISH,
            force_reduce=True,
        )

    assert result.source_chunk_indices == list(range(10))
    intermediate_prompts = [
        p
        for p in captured_prompts
        if "intermediate reduction step" in p or "paso de reducción intermedio" in p
    ]
    final_prompts = [
        p
        for p in captured_prompts
        if "FINAL synthesis step" in p or "paso FINAL de síntesis" in p
    ]
    assert intermediate_prompts, "hierarchical REDUCE must issue an intermediate prompt"
    assert final_prompts, "hierarchical REDUCE must issue a final prompt"

    for prompt in intermediate_prompts:
        lowered = prompt.lower()
        assert "heavily" not in lowered
        assert "maximum " not in lowered
        assert "nunca más" not in lowered
        assert "never more" not in lowered
        assert "approximately 55%" in lowered or "aproximadamente el 55%" in lowered
        assert (
            "do not compress substantially below" in lowered
            or "no comprimas sustancialmente por debajo" in lowered
        )

    for prompt in final_prompts:
        lowered = prompt.lower()
        assert "nunca más" not in lowered
        assert "never more" not in lowered
        assert (
            "preserve all remaining" in lowered
            or "conserva todo el contenido" in lowered
        )
        assert "do not compress further" in lowered or "no comprimas más" in lowered


@pytest.mark.asyncio
async def test_language_reduce_prompts_drop_never_more_ceiling():
    from core.brevio.services.advanced_content_generator import AdvancedPromptGenerator

    gen = AdvancedPromptGenerator()
    for language in (LanguageType.SPANISH, LanguageType.ENGLISH):
        prompt = await gen.get_reduce_prompt(language)
        lowered = prompt.lower()
        assert "nunca más" not in lowered
        assert "never more" not in lowered
        assert "conocimiento externo" in lowered or "external knowledge" in lowered
        assert (
            "no comprimas por debajo" in lowered or "do not compress below" in lowered
        )


@pytest.mark.asyncio
async def test_format_prompt_does_not_ask_to_summarize():
    from core.brevio.services.advanced_content_generator import AdvancedPromptGenerator

    gen = AdvancedPromptGenerator()
    for language in (LanguageType.SPANISH, LanguageType.ENGLISH):
        prompt = await gen.get_format_prompt(language)
        lowered = prompt.lower()
        assert "resumir de manera concisa" not in lowered
        assert "summarize the document" not in lowered
        assert "no resumas" in lowered or "do not summarize" in lowered
        assert "formato" in lowered or "formatting" in lowered
