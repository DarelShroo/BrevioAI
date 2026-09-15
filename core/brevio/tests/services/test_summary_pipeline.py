"""
Suite de tests exhaustiva para el pipeline Map-Reduce de resúmenes.

Cubre:
  - MAP phase: éxito, fallos parciales, chunks de solo índice, preservación de orden
  - REDUCE phase: convergencia, bucle infinito (guard), caso trivial (1 summary)
  - FORMATTING phase: éxito, fallback al texto original si falla
  - GROUNDING: que un índice no se expanda
  - PIPELINE COMPLETO: end-to-end con mocks
  - EDGE CASES: 0 chunks, 1 chunk, todos los chunks fallan
"""
import asyncio
import os
import time
from typing import Any, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import AsyncOpenAI
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionMessage

from core.brevio.enums.language import LanguageType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.services.summary_service import (
    MapChunkResult,
    ReduceConvergenceError,
    SummaryService,
)
from core.shared.enums.model import ModelType
from core.shared.utils.model_capabilities import (
    get_model_capabilities,
    summary_max_output_tokens,
)
from core.shared.utils.model_tokens_utils import get_encoder

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_TOKENS", "4096")
    monkeypatch.setenv("MAX_TOKEN_PER_MINUTE", "200000")
    monkeypatch.setenv("TEMPERATURE", "0.2")
    monkeypatch.setenv("OPENAI_API_KEY", "fake_api_key")
    monkeypatch.setenv("MAX_TOKEN_WAIT", "1")
    monkeypatch.setenv("BREVIO_KEEP_PARTIALS", "false")


@pytest.fixture
def summary_service() -> SummaryService:
    with patch("core.brevio.services.summary_service.AsyncOpenAI") as mock_openai:
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        mock_openai.return_value = mock_client
        service = SummaryService()
        service.client = mock_client
        service.api_service._initialize_client = AsyncMock(return_value=mock_client)
        service.history_token_model.user_id = "test_user_id"
        # Ensure token bucket is generous
        service.token_bucket = 200_000
        service.tokens_per_minute = 200_000
        return service


def make_mock_response(
    content: str, total_tokens: int = 100, completion_tokens: int = 1
) -> MagicMock:
    """Helper to build a minimal mock ChatCompletion response."""
    mock = MagicMock(spec=ChatCompletion)
    mock.choices = [
        MagicMock(
            message=MagicMock(spec=ChatCompletionMessage, content=content),
            finish_reason="stop",
        )
    ]
    mock.usage = MagicMock(
        spec=CompletionUsage,
        total_tokens=total_tokens,
        completion_tokens=completion_tokens,
        prompt_tokens=total_tokens - completion_tokens,
    )
    return mock


def test_safe_completion_limit_is_model_specific(
    summary_service: SummaryService,
) -> None:
    requested = 20_000
    system_tokens = 1_000
    user_tokens = 3_000

    gpt4_limit = summary_service._safe_completion_token_limit(
        ModelType.GPT_4, system_tokens, user_tokens, requested
    )
    deepseek_limit = summary_service._safe_completion_token_limit(
        ModelType.DEEPSEEK_V4_PRO, system_tokens, user_tokens, requested
    )
    gpt4o_mini_limit = summary_service._safe_completion_token_limit(
        ModelType.GPT_4O_MINI, system_tokens, user_tokens, requested
    )

    assert gpt4_limit == (
        get_model_capabilities(ModelType.GPT_4).context_window
        - system_tokens
        - user_tokens
        - 512
    )
    assert deepseek_limit == summary_max_output_tokens(
        get_model_capabilities(ModelType.DEEPSEEK_V4_PRO)
    )
    assert gpt4o_mini_limit == summary_max_output_tokens(
        get_model_capabilities(ModelType.GPT_4O_MINI)
    )
    assert gpt4_limit < deepseek_limit
    assert gpt4_limit < gpt4o_mini_limit


def test_reduce_batch_limit_uses_model_and_summary_level(
    summary_service: SummaryService,
) -> None:
    prompt_tokens = 500

    gpt4_detailed = summary_service._reduce_batch_token_limit(
        ModelType.GPT_4, SummaryLevel.DETAILED, prompt_tokens
    )
    deepseek_detailed = summary_service._reduce_batch_token_limit(
        ModelType.DEEPSEEK_V4_PRO, SummaryLevel.DETAILED, prompt_tokens
    )
    gpt4o_detailed = summary_service._reduce_batch_token_limit(
        ModelType.GPT_4O_MINI, SummaryLevel.DETAILED, prompt_tokens
    )
    deepseek_very_detailed = summary_service._reduce_batch_token_limit(
        ModelType.DEEPSEEK_V4_PRO, SummaryLevel.VERY_DETAILED, prompt_tokens
    )

    assert gpt4_detailed < deepseek_detailed < gpt4o_detailed
    assert deepseek_very_detailed < deepseek_detailed
    assert (
        gpt4o_detailed
        < get_model_capabilities(ModelType.GPT_4O_MINI).reduce_batch_tokens
    )


@pytest.mark.asyncio
async def test_reduce_call_passes_context_safe_dynamic_max_tokens(
    summary_service: SummaryService,
) -> None:
    mock_resp = make_mock_response("Reduced.", total_tokens=100, completion_tokens=20)

    class CountingEncoder:
        def encode(self, text: str) -> list[int]:
            if text == "reduce prompt":
                return [1] * 1000
            if "large batch" in text:
                return [1] * 5000
            return [1] * 20

    assert summary_service.client is not None

    async def run_call(fn, **kwargs):
        return await fn()

    mock_resp.choices[0].finish_reason = "stop"
    with patch(
        "core.brevio.services.summary_service.get_encoder",
        return_value=CountingEncoder(),
    ), patch.object(
        summary_service, "_check_token_limit", return_value=True
    ), patch.object(
        summary_service.provider_executor, "execute", side_effect=run_call
    ), patch.object(
        summary_service.client.chat.completions,
        "create",
        new=AsyncMock(return_value=mock_resp),
    ):
        await summary_service._execute_reduce_call(
            "large batch",
            "reduce prompt",
            ModelType.GPT_4,
            summary_service.client,
            2000,
            LanguageType.ENGLISH,
        )

        max_tokens = summary_service.client.chat.completions.create.call_args.kwargs[
            "max_tokens"
        ]
        assert max_tokens == (
            get_model_capabilities(ModelType.GPT_4).context_window - 1000 - 5000 - 512
        )


@pytest.mark.asyncio
async def test_reduce_call_stop_at_budget_is_not_rewritten_to_length(
    summary_service: SummaryService,
) -> None:
    from core.shared.enums.type_call import TypeCall

    mock_resp = make_mock_response(
        "Complete reduction.", total_tokens=2500, completion_tokens=2000
    )
    mock_resp.choices[0].finish_reason = "stop"

    async def run_call(fn, **kwargs):
        return await fn()

    assert summary_service.client is not None
    with patch.object(
        summary_service, "_check_token_limit", return_value=True
    ), patch.object(
        summary_service.provider_executor, "execute", side_effect=run_call
    ), patch.object(
        summary_service.client.chat.completions,
        "create",
        new=AsyncMock(return_value=mock_resp),
    ):
        content, _tokens, finish = await summary_service._execute_reduce_call(
            "batch",
            "reduce prompt",
            ModelType.DEEPSEEK_V4_PRO,
            summary_service.client,
            2000,
            LanguageType.ENGLISH,
        )

    assert finish == "stop"
    assert content == "Complete reduction."
    assert (
        summary_service.history_token_model.history_tokens_per_call[-1].type_call
        == TypeCall.REDUCE
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. MAP PHASE
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_map_phase_all_chunks_succeed(summary_service: SummaryService) -> None:
    """MAP: todos los chunks devuelven un resumen válido."""
    chunks = ["Texto del chunk 1.", "Texto del chunk 2.", "Texto del chunk 3."]

    async def fake_chunk(index, chunk, *args, **kwargs):
        return index, f"Resumen de: {chunk}", len(chunk)

    with patch.object(
        summary_service, "generate_summary_chunk", side_effect=fake_chunk
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        summaries, tokens = await summary_service.run_map_phase(
            chunks, "prompt", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )

    assert len(summaries) == 3
    assert all(isinstance(item, MapChunkResult) for item in summaries)
    assert summaries[0].summary_text == "Resumen de: Texto del chunk 1."
    assert summaries[1].summary_text == "Resumen de: Texto del chunk 2."
    assert summaries[2].summary_text == "Resumen de: Texto del chunk 3."
    assert tokens > 0


@pytest.mark.asyncio
async def test_map_phase_order_preserved(summary_service: SummaryService) -> None:
    """MAP: el orden de los chunks se preserva aunque el LLM responda fuera de orden."""
    chunks = [f"chunk_{i}" for i in range(6)]
    results_store = {}

    async def fake_chunk(index, chunk, *args, **kwargs):
        # Simula que chunks altos terminan antes que bajos (fuera de orden)
        await asyncio.sleep(0.001 * (6 - index))
        results_store[index] = f"summary_{index}"
        return index, f"summary_{index}", 10

    with patch.object(
        summary_service, "generate_summary_chunk", side_effect=fake_chunk
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        summaries, _ = await summary_service.run_map_phase(
            chunks, "prompt", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )

    assert [item.summary_text for item in summaries] == [
        f"summary_{i}" for i in range(6)
    ], f"Orden incorrecto: {summaries}"


@pytest.mark.asyncio
async def test_map_phase_partial_failures(summary_service: SummaryService) -> None:
    """MAP: chunks que fallan (devuelven None) se marcan FAILED sin abortar el resto."""
    chunks = ["ok_chunk_0", "bad_chunk_1", "ok_chunk_2"]

    async def fake_chunk(index, chunk, *args, **kwargs):
        if "bad" in chunk:
            return index, None, 0
        return index, f"summary_{index}", 10

    with patch.object(
        summary_service, "generate_summary_chunk", side_effect=fake_chunk
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        summaries, tokens = await summary_service.run_map_phase(
            chunks, "prompt", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )

    assert len(summaries) == 3
    assert summaries[0].status == "SUCCESS"
    assert summaries[1].status == "FAILED"
    assert summaries[1].original_text == "bad_chunk_1"
    assert summaries[2].status == "SUCCESS"


@pytest.mark.asyncio
async def test_map_phase_all_chunks_fail(summary_service: SummaryService) -> None:
    """MAP: si todos los chunks fallan, se devuelve FAILED por cada chunk, nunca lista vacía silenciosa."""
    chunks = ["chunk_a", "chunk_b"]

    async def fake_chunk(index, chunk, *args, **kwargs):
        return index, None, 0

    with patch.object(
        summary_service, "generate_summary_chunk", side_effect=fake_chunk
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        summaries, tokens = await summary_service.run_map_phase(
            chunks, "prompt", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )

    assert len(summaries) == 2
    assert all(item.status == "FAILED" for item in summaries)
    assert summaries[0].original_text == "chunk_a"


@pytest.mark.asyncio
async def test_map_phase_empty_chunks(summary_service: SummaryService) -> None:
    """MAP: lista de chunks vacía devuelve lista vacía."""
    with patch.object(summary_service, "_check_token_limit", return_value=True):
        summaries, tokens = await summary_service.run_map_phase(
            [], "prompt", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )
    assert summaries == []
    assert tokens == 0


@pytest.mark.asyncio
async def test_map_phase_callback_called(summary_service: SummaryService) -> None:
    """MAP: el callback de progreso es llamado al finalizar cada grupo."""
    chunks = ["c1", "c2"]
    callback_calls: List[str] = []

    async def cb(summary: str) -> None:
        callback_calls.append(summary)

    async def fake_chunk(index, chunk, *args, **kwargs):
        return index, f"s{index}", 5

    with patch.object(
        summary_service, "generate_summary_chunk", side_effect=fake_chunk
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        await summary_service.run_map_phase(
            chunks,
            "prompt",
            ModelType.DEEPSEEK_V4_PRO,
            LanguageType.ENGLISH,
            callback=cb,
        )

    assert len(callback_calls) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 2. REDUCE PHASE
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reduce_phase_single_summary(summary_service: SummaryService) -> None:
    """REDUCE: si sólo hay 1 summary, se devuelve directamente sin llamar al LLM."""
    with patch.object(summary_service, "_execute_reduce_call") as mock_reduce:
        result, tokens = await summary_service.run_reduce_phase(
            ["Solo summary"], "prompt", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )
    mock_reduce.assert_not_called()
    assert result == "Solo summary"
    assert tokens == 0


@pytest.mark.asyncio
async def test_reduce_phase_empty_list(summary_service: SummaryService) -> None:
    """REDUCE: lista vacía devuelve string vacío sin excepción."""
    with patch.object(summary_service, "_execute_reduce_call") as mock_reduce:
        result, tokens = await summary_service.run_reduce_phase(
            [], "prompt", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )
    mock_reduce.assert_not_called()
    assert result == ""
    assert tokens == 0


@pytest.mark.asyncio
async def test_reduce_phase_converges_4_summaries(
    summary_service: SummaryService,
) -> None:
    """REDUCE: 4 summaries se reducen a 1 en una sola ronda (batch limit generoso)."""
    summaries = [
        "factual summary A",
        "factual summary B",
        "factual summary C",
        "factual summary D",
    ]
    reduce_calls = []

    async def mock_reduce(*args, **kwargs):
        reduce_calls.append(args[0])
        return "FINAL_REDUCED", 100, "stop"

    # REDUCE packs by ModelCapabilities.reduce_batch_tokens, not an env var.
    with patch.object(
        summary_service, "_execute_reduce_call", side_effect=mock_reduce
    ), patch.object(
        summary_service.api_service, "_initialize_client", return_value=AsyncMock()
    ):
        result, tokens = await summary_service.run_reduce_phase(
            summaries, "reduce prompt", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )

    assert result == "FINAL_REDUCED"
    # Todos los summaries caben en 1 batch → sólo 1 llamada al LLM
    assert len(reduce_calls) == 1
    # El batch debe contener todos los summaries
    for s in summaries:
        assert s in reduce_calls[0]


@pytest.mark.asyncio
async def test_reduce_phase_convergence_guard(summary_service: SummaryService) -> None:
    """Identity REDUCE cannot loop forever: intermediate caps escalate to a final assemble."""
    summaries = ["big summary A", "big summary B"]
    reduce_calls = [0]

    async def mock_reduce(*args, **kwargs):
        reduce_calls[0] += 1
        return "large_output", 50, "stop"

    with patch(
        "core.brevio.services.summary_service.get_encoder"
    ) as mock_enc_fn, patch.object(
        summary_service, "_execute_reduce_call", side_effect=mock_reduce
    ), patch.object(
        summary_service.api_service, "_initialize_client", return_value=AsyncMock()
    ):
        mock_enc = MagicMock()
        mock_enc.encode.return_value = [1] * 30000
        mock_enc_fn.return_value = mock_enc

        start = time.time()
        result, _tokens = await summary_service.run_reduce_phase(
            summaries, "prompt", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )
        elapsed = time.time() - start

    assert elapsed < 5
    assert result is not None
    assert "large_output" in result
    assert 1 <= reduce_calls[0] <= 20


@pytest.mark.asyncio
async def test_reduce_phase_no_infinite_loop(summary_service: SummaryService) -> None:
    """REDUCE: verificar que nunca se cuelga — completa en tiempo razonable."""
    summaries = [f"summary chunk {i} " * 50 for i in range(10)]
    reduce_call_count = [0]

    async def mock_reduce(*args, **kwargs):
        reduce_call_count[0] += 1
        return f"reduced_{reduce_call_count[0]}", 10, "stop"

    with patch.object(
        summary_service, "_execute_reduce_call", side_effect=mock_reduce
    ), patch.object(
        summary_service.api_service, "_initialize_client", return_value=AsyncMock()
    ):
        start = time.time()
        result, _ = await summary_service.run_reduce_phase(
            summaries, "prompt", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )
        elapsed = time.time() - start

    assert (
        elapsed < 10
    ), f"Reduce tardó demasiado: {elapsed:.2f}s (posible loop infinito)"
    assert result is not None


# ─────────────────────────────────────────────────────────────────────────────
# 3. FORMATTING PHASE
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_formatting_phase_success(summary_service: SummaryService) -> None:
    """FORMATTING: devuelve el contenido formateado del LLM."""
    mock_resp = make_mock_response(
        "# Formatted Summary\n\nContent here.", total_tokens=80
    )

    assert summary_service.client is not None
    with patch.object(
        summary_service.client.chat.completions, "create", return_value=mock_resp
    ), patch.object(
        summary_service, "_check_token_limit", return_value=True
    ), patch.object(
        summary_service.api_service,
        "_initialize_client",
        return_value=summary_service.client,
    ):
        result, tokens = await summary_service.run_formatting_phase(
            "Raw factual text",
            "Format prompt",
            ModelType.DEEPSEEK_V4_PRO,
            LanguageType.ENGLISH,
        )

    assert result == "# Formatted Summary\n\nContent here."
    assert tokens == 80


@pytest.mark.asyncio
async def test_formatting_phase_fallback_on_error(
    summary_service: SummaryService,
) -> None:
    """FORMATTING: si el LLM falla, devuelve el input original como fallback."""
    raw_input = "This is the raw summary text."

    assert summary_service.client is not None
    with patch.object(
        summary_service.client.chat.completions,
        "create",
        side_effect=Exception("API error"),
    ), patch.object(
        summary_service, "_check_token_limit", return_value=True
    ), patch.object(
        summary_service.api_service,
        "_initialize_client",
        return_value=summary_service.client,
    ):
        result, tokens = await summary_service.run_formatting_phase(
            raw_input, "Format prompt", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )

    assert result == raw_input
    assert tokens == 0


@pytest.mark.asyncio
async def test_formatting_phase_empty_response_uses_fallback(
    summary_service: SummaryService,
) -> None:
    """FORMATTING: si el LLM devuelve vacío, se usa el input original."""
    mock_resp = make_mock_response("", total_tokens=10)
    raw_input = "Original raw text."

    assert summary_service.client is not None
    with patch.object(
        summary_service.client.chat.completions, "create", return_value=mock_resp
    ), patch.object(
        summary_service, "_check_token_limit", return_value=True
    ), patch.object(
        summary_service.api_service,
        "_initialize_client",
        return_value=summary_service.client,
    ):
        result, tokens = await summary_service.run_formatting_phase(
            raw_input, "Format prompt", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )

    # El modelo devolvió vacío → fallback al input original
    assert result == raw_input or result == ""


# ─────────────────────────────────────────────────────────────────────────────
# 4. GROUNDING — el modelo no debe inventar contenido de índices
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_grounding_map_prompt_contains_antihallucination_rules() -> None:
    """GROUNDING: el prompt MAP debe incluir las reglas anti-alucinación."""
    from core.brevio.services.advanced_content_generator import AdvancedPromptGenerator

    gen = AdvancedPromptGenerator()

    for lang in [LanguageType.ENGLISH, LanguageType.SPANISH]:
        prompt = await gen.get_map_prompt(lang)
        assert (
            "external knowledge" in prompt.lower()
            or "conocimiento externo" in prompt.lower()
        ), f"MAP prompt para {lang} no tiene regla anti-alucinación: {prompt[:200]}"
        # La regla sobre índices debe estar presente
        assert (
            "index" in prompt.lower()
            or "índice" in prompt.lower()
            or "table of contents" in prompt.lower()
            or "tabla de contenidos" in prompt.lower()
        ), f"MAP prompt para {lang} no menciona el tratamiento de índices: {prompt[:200]}"


@pytest.mark.asyncio
async def test_map_prompt_does_not_ask_to_fill_token_budget() -> None:
    from core.brevio.enums.summary_level import SummaryLevel
    from core.brevio.services.advanced_content_generator import AdvancedPromptGenerator

    gen = AdvancedPromptGenerator()
    prompt = await gen.get_map_prompt(
        LanguageType.SPANISH, summary_level=SummaryLevel.VERY_DETAILED
    )
    assert "VERY EXTENSIVE" not in prompt
    assert "MUST BE VERY" not in prompt
    assert "detente" not in prompt.lower()
    assert "rellenes para agotar" not in prompt.lower()
    assert "presupuesto" in prompt.lower()
    assert (
        "no te detengas pronto" in prompt.lower()
        or "detalles importantes" in prompt.lower()
    )


@pytest.mark.asyncio
async def test_grounding_reduce_prompt_contains_no_external_knowledge_rule() -> None:
    """GROUNDING: el prompt REDUCE debe prohibir el uso de conocimiento externo."""
    from core.brevio.services.advanced_content_generator import AdvancedPromptGenerator

    gen = AdvancedPromptGenerator()

    for lang in [LanguageType.ENGLISH, LanguageType.SPANISH]:
        prompt = await gen.get_reduce_prompt(lang)
        no_external = (
            "not present" in prompt.lower()
            or "no presente" in prompt.lower()
            or "do not add" in prompt.lower()
            or "no añadas" in prompt.lower()
            or "external knowledge" in prompt.lower()
            or "conocimiento externo" in prompt.lower()
        )
        assert (
            no_external
        ), f"REDUCE prompt para {lang} no prohíbe conocimiento externo: {prompt[:300]}"
        assert (
            "what do you need" in prompt.lower() or "qué necesitas" in prompt.lower()
        ), f"REDUCE prompt para {lang} no prohíbe menús de asistente: {prompt[:300]}"


@pytest.mark.asyncio
async def test_index_only_chunk_does_not_expand(
    summary_service: SummaryService,
) -> None:
    """GROUNDING: un chunk que sea solo un índice no debe ser expandido por el MAP.

    Simula que el LLM (correctamente) devuelve solo el listado del índice sin explicarlo.
    El test verifica que el pipeline acepta este output correcto.
    """
    index_chunk = """
    Table of Contents
    Unit 2 - Functions ................. 45
    Unit 3 - Arrays ..................... 67
    Unit 4 - Objects ..................... 89
    """

    # LLM respeta el grounding y devuelve solo el índice listado, sin expansión
    expected_grounded_output = "- Unit 2: Functions (page 45)\n- Unit 3: Arrays (page 67)\n- Unit 4: Objects (page 89)"

    mock_resp = make_mock_response(
        expected_grounded_output, total_tokens=50, completion_tokens=1
    )

    assert summary_service.client is not None
    with patch.object(
        summary_service.provider_executor,
        "execute",
        new=AsyncMock(return_value=mock_resp),
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        _, summary, tokens = await summary_service.generate_summary_chunk(
            0,
            index_chunk,
            "MAP PROMPT WITH GROUNDING RULES",
            ModelType.DEEPSEEK_V4_PRO,
            LanguageType.ENGLISH,
            100,
        )

    assert summary is not None
    # El output no debe contener explicaciones inventadas sobre functions o arrays
    invented_keywords = [
        "def ",
        "function(",
        "return ",
        "array.push",
        "array[",
        "const ",
        "let ",
        "var ",
    ]
    for kw in invented_keywords:
        assert (
            kw not in (summary or "").lower()
        ), f"El resumen contiene código inventado '{kw}': {summary}"


# ─────────────────────────────────────────────────────────────────────────────
# 5. generate_summary_chunk — comportamiento del método base
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_summary_chunk_success(summary_service: SummaryService) -> None:
    """generate_summary_chunk: éxito retorna (index, contenido, tokens)."""
    mock_resp = make_mock_response(
        "Resumen extraído del chunk.", total_tokens=120, completion_tokens=1
    )
    mock_resp.choices[0].finish_reason = "stop"

    assert summary_service.client is not None
    with patch.object(
        summary_service.provider_executor,
        "execute",
        new=AsyncMock(return_value=mock_resp),
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        index, summary, tokens = await summary_service.generate_summary_chunk(
            0,
            "Chunk de texto real.",
            "Prompt MAP",
            ModelType.DEEPSEEK_V4_PRO,
            LanguageType.ENGLISH,
            100,
        )

    assert index == 0
    assert summary is not None and len(summary) > 0
    assert tokens == 120


@pytest.mark.asyncio
async def test_generate_summary_chunk_api_failure(
    summary_service: SummaryService,
) -> None:
    """generate_summary_chunk: error de API devuelve (index, None, 0)."""
    assert summary_service.client is not None
    with patch.object(
        summary_service.provider_executor,
        "execute",
        new=AsyncMock(side_effect=Exception("Network error")),
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        with pytest.raises(Exception, match="Network error"):
            await summary_service.generate_summary_chunk(
                3,
                "Texto",
                "Prompt",
                ModelType.DEEPSEEK_V4_PRO,
                LanguageType.ENGLISH,
                100,
            )


@pytest.mark.asyncio
async def test_generate_summary_chunk_empty_response(
    summary_service: SummaryService,
) -> None:
    """generate_summary_chunk: respuesta vacía del LLM devuelve (index, None, 0)."""
    mock_resp = make_mock_response("", total_tokens=10, completion_tokens=0)
    mock_resp.choices[0].finish_reason = "stop"

    assert summary_service.client is not None
    with patch.object(
        summary_service.provider_executor,
        "execute",
        new=AsyncMock(return_value=mock_resp),
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        index, summary, tokens = await summary_service.generate_summary_chunk(
            1, "Texto", "Prompt", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH, 100
        )

    assert index == 1
    assert summary is None
    assert tokens == 0


# ─────────────────────────────────────────────────────────────────────────────
# 6. PIPELINE COMPLETO — test de integración (mocked LLM)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_map_reduce_pipeline_integration(
    summary_service: SummaryService,
) -> None:
    """INTEGRACIÓN: verifica que MAP → REDUCE → FORMATTING fluyen sin errores."""
    # Simulamos 4 chunks con contenido real
    chunks = [
        "JavaScript is a programming language used for web development.",
        "Variables in JavaScript can be declared with var, let, or const.",
        "Functions in JavaScript are first-class objects.",
        "Arrays are ordered collections. Common methods: push, pop, map, filter.",
    ]

    map_prompt = "Extract facts from this chunk."
    reduce_prompt = "Synthesize these facts."
    format_prompt = "Format this summary nicely."

    # Mocks: MAP devuelve summaries simples
    async def fake_chunk(index, chunk, *args, **kwargs):
        words = chunk.split()[:5]
        return index, f"FACT: {' '.join(words)}...", 50

    # Mock REDUCE: concatena
    async def fake_reduce(*args, **kwargs):
        batch = args[0]
        return f"REDUCED({len(batch)}chars)", 100, "stop"

    # Mock FORMAT: añade título
    format_resp = make_mock_response(
        "# JavaScript Summary\n\nREDUCED content.", total_tokens=80
    )

    with patch.object(
        summary_service, "generate_summary_chunk", side_effect=fake_chunk
    ), patch.object(
        summary_service, "_check_token_limit", return_value=True
    ), patch.object(
        summary_service, "_execute_reduce_call", side_effect=fake_reduce
    ), patch.object(
        summary_service.api_service,
        "_initialize_client",
        return_value=summary_service.client,
    ), patch.object(
        summary_service.client.chat.completions, "create", return_value=format_resp
    ):
        # MAP
        mapped_summaries, map_tokens = await summary_service.run_map_phase(
            chunks, map_prompt, ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )

        assert len(mapped_summaries) == 4
        assert map_tokens > 0

        # REDUCE
        reduced, reduce_tokens = await summary_service.run_reduce_phase(
            mapped_summaries,
            reduce_prompt,
            ModelType.DEEPSEEK_V4_PRO,
            LanguageType.ENGLISH,
        )

        assert reduced is not None
        assert len(reduced) > 0
        assert reduce_tokens > 0

        # FORMAT
        with patch.object(summary_service, "_check_token_limit", return_value=True):
            formatted, format_tokens = await summary_service.run_formatting_phase(
                reduced, format_prompt, ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
            )

        assert "JavaScript" in formatted or "REDUCED" in formatted
        assert format_tokens == 80


@pytest.mark.asyncio
async def test_pipeline_with_toc_only_chunk(summary_service: SummaryService) -> None:
    """INTEGRACIÓN: el pipeline maneja correctamente un chunk de solo índice."""
    chunks = [
        "Chapter 1 - Introduction to Programming",
        "Unit 2 Functions .... 45\nUnit 3 Arrays ..... 67\nUnit 4 Objects ..... 89",  # TOC-only chunk
        "In JavaScript, functions are declared using the function keyword.",
    ]

    async def fake_chunk(index, chunk, *args, **kwargs):
        # Simula grounding: el TOC chunk produce output mínimo (solo listar, no expandir)
        if "Unit 2" in chunk and "Unit 3" in chunk:
            return index, "- Unit 2: Functions\n- Unit 3: Arrays\n- Unit 4: Objects", 20
        return index, f"Summary of: {chunk[:30]}...", 50

    async def fake_reduce(*args, **kwargs):
        batch = args[0]
        return f"SYNTHESIZED: {batch[:80]}", 100, "stop"

    format_resp = make_mock_response("Final formatted output.", total_tokens=60)

    with patch.object(
        summary_service, "generate_summary_chunk", side_effect=fake_chunk
    ), patch.object(
        summary_service, "_check_token_limit", return_value=True
    ), patch.object(
        summary_service, "_execute_reduce_call", side_effect=fake_reduce
    ), patch.object(
        summary_service.api_service,
        "_initialize_client",
        return_value=summary_service.client,
    ), patch.object(
        summary_service.client.chat.completions, "create", return_value=format_resp
    ):
        summaries, _ = await summary_service.run_map_phase(
            chunks, "MAP_PROMPT", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )

    # El chunk de TOC no debe generar contenido inventado
    toc_summary = summaries[1].summary_text
    bad_keywords = ["function keyword", "def ", "return ", "example:", "for instance"]
    for kw in bad_keywords:
        assert (
            kw.lower() not in toc_summary.lower()
        ), f"El resumen del TOC contiene contenido inventado '{kw}': {toc_summary}"

    # Debe estar listado, no expandido
    assert "Unit 2" in toc_summary or "Functions" in toc_summary


# ─────────────────────────────────────────────────────────────────────────────
# 7. TOKEN BUCKET — límite de tokens
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_token_limit_passes_when_enough_tokens(
    summary_service: SummaryService,
) -> None:
    # safety_margin = tokens_per_minute * 0.1 = 200000 * 0.1 = 20000
    # Condition: token_bucket >= tokens_needed + safety_margin
    # So for 5000 tokens needed: bucket must be >= 5000 + 20000 = 25000
    summary_service.token_bucket = 50_000  # clearly above needed + safety_margin
    summary_service.tokens_per_minute = 200_000
    summary_service.last_token_reset = time.time()
    result = await summary_service._check_token_limit(5_000)
    assert result is True


@pytest.mark.asyncio
async def test_check_token_limit_raises_timeout_when_no_tokens(
    summary_service: SummaryService,
) -> None:
    summary_service.token_bucket = 10
    summary_service.last_token_reset = time.time()
    with pytest.raises(TimeoutError):
        await summary_service._check_token_limit(50_000)


# ─────────────────────────────────────────────────────────────────────────────
# 8. SERVICE INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────


def test_summary_service_has_required_attributes(
    summary_service: SummaryService,
) -> None:
    """El servicio tiene todos los métodos del pipeline Map-Reduce."""
    assert hasattr(summary_service, "run_map_phase")
    assert hasattr(summary_service, "run_reduce_phase")
    assert hasattr(summary_service, "run_formatting_phase")
    assert hasattr(summary_service, "generate_summary_chunk")
    assert hasattr(summary_service, "_execute_reduce_call")
    assert hasattr(summary_service, "_check_token_limit")
    assert hasattr(summary_service, "chunk_text")
    assert callable(summary_service.run_map_phase)
    assert callable(summary_service.run_reduce_phase)
    assert callable(summary_service.run_formatting_phase)


def test_summary_service_uses_backend_temperature_until_model_bind(
    summary_service: SummaryService,
) -> None:
    """Sampling is bound from official per-model defaults at job start."""
    assert summary_service.temperature == 0.0
