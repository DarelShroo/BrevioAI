"""REDUCE output contract: finish_reason=length is never SUCCESS."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest

from core.brevio.enums.language import LanguageType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.services.summary_service import (
    ReduceConvergenceError,
    ReduceResult,
    SummaryService,
)
from core.shared.enums.model import ModelType


@pytest.fixture(autouse=True)
def set_env_vars(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("MAX_TOKENS", "1000000")
    monkeypatch.setenv("MAX_TOKEN_PER_MINUTE", "1000000")
    monkeypatch.setenv("TEMPERATURE", "0.7")
    monkeypatch.setenv("OPENAI_API_KEY", "fake_api_key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake_api_key")
    monkeypatch.setenv("MAX_TOKEN_WAIT", "1")
    # summary_service logger uses propagate=False + its own StreamHandler.
    log = logging.getLogger("core.brevio.services.summary_service")
    log.addHandler(caplog.handler)
    caplog.set_level(logging.INFO, logger="core.brevio.services.summary_service")
    yield
    log.removeHandler(caplog.handler)


@pytest.fixture
def summary_service() -> SummaryService:
    with patch("core.brevio.services.summary_service.AsyncOpenAI") as mock_openai:
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock()
        mock_client.chat.completions = AsyncMock()
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
async def test_reduce_length_is_not_success_triggers_recovery(summary_service, caplog):
    """Test 1: finish_reason=length is TRUNCATED, not SUCCESS; activates split recovery."""
    chunks = [
        "Essay 1 epistemology and scientific method. " * 20,
        "Essay 2 experimental contrastation and hypotheses. " * 20,
    ]
    attempts = 0
    finishes = []

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
            finishes.append("length")
            return "Essay 1 cut mid-sente", 80, "length"
        finishes.append("stop")
        return f"Complete reduction part {attempts}.", 50, "stop"

    with patch.object(
        summary_service, "_execute_reduce_call", new=AsyncMock(side_effect=mock_execute)
    ):
        with caplog.at_level("INFO"):
            result = await summary_service.run_reduce_phase(
                mapped_summaries=chunks,
                reduce_prompt="Synthesize.",
                model=ModelType.DEEPSEEK_V4_PRO,
                language=LanguageType.ENGLISH,
                force_reduce=False,
            )

    assert isinstance(result, ReduceResult)
    assert result.finish_reason != "length"
    assert result.source_chunk_indices == [0, 1]
    assert attempts >= 3
    assert "status=TRUNCATED" in caplog.text
    assert "recovery strategy=split" in caplog.text
    assert "recovery status=SUCCESS" in caplog.text


@pytest.mark.asyncio
async def test_reduce_consecutive_length_keeps_recovering(summary_service, caplog):
    """Test 2: consecutive length truncations keep recovering instead of propagating."""
    chunks = [
        "Block A scientific realism content. " * 25,
        "Block B methodology content. " * 25,
        "Block C ethics of science content. " * 25,
        "Block D late essay content that must survive. " * 25,
    ]
    call_finishes = []

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
        # Truncate only while multiple sections are packed together.
        packed = sum(
            1
            for marker in ("Block A", "Block B", "Block C", "Block D")
            if marker in batch_text
        )
        if packed >= 3:
            call_finishes.append("length")
            return "Early blocks only and then cut...", 120, "length"
        if packed == 2 and "Block A" in batch_text and "Block B" in batch_text:
            # Simulate a second truncation on a still-large left half once.
            if call_finishes.count("length") < 2:
                call_finishes.append("length")
                return "Block A and start of B cut...", 90, "length"
        call_finishes.append("stop")
        return f"OK reduce covering markers in: {batch_text[:80]}", 60, "stop"

    with patch.object(
        summary_service, "_execute_reduce_call", new=AsyncMock(side_effect=mock_execute)
    ):
        with caplog.at_level("WARNING"):
            result = await summary_service.run_reduce_phase(
                mapped_summaries=chunks,
                reduce_prompt="Synthesize.",
                model=ModelType.DEEPSEEK_V4_PRO,
                language=LanguageType.ENGLISH,
                force_reduce=True,
            )

    assert isinstance(result, ReduceResult)
    assert result.source_chunk_indices == [0, 1, 2, 3]
    assert result.finish_reason != "length"
    assert call_finishes.count("length") >= 2
    assert "recovery strategy=split" in caplog.text
    assert "Block D" in result.text or 3 in result.source_chunk_indices


@pytest.mark.asyncio
async def test_reduce_stop_remains_valid_success(summary_service):
    """Test 3: finish_reason=stop continues to work as a normal SUCCESS path."""
    chunks = [
        "Short essay one about science.",
        "Short essay two about method.",
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
        return "Full synthesis of both essays.", 40, "stop"

    with patch.object(
        summary_service, "_execute_reduce_call", new=AsyncMock(side_effect=mock_execute)
    ):
        result = await summary_service.run_reduce_phase(
            mapped_summaries=chunks,
            reduce_prompt="Synthesize.",
            model=ModelType.DEEPSEEK_V4_PRO,
            language=LanguageType.ENGLISH,
            force_reduce=True,
        )

    assert result.text.startswith("Full synthesis")
    assert result.finish_reason == "stop"
    assert result.source_chunk_indices == [0, 1]


@pytest.mark.asyncio
async def test_reduce_empty_response_rejected(summary_service):
    """Test 4: empty REDUCE output is never accepted as a valid summary."""
    chunks = [
        "Content that must not collapse into emptiness. " * 30,
        "Second block that should force a split path. " * 30,
    ]
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
            return "   ", 0, "stop"
        return f"Recovered content {attempts}.", 40, "stop"

    with patch.object(
        summary_service, "_execute_reduce_call", new=AsyncMock(side_effect=mock_execute)
    ):
        result = await summary_service.run_reduce_phase(
            mapped_summaries=chunks,
            reduce_prompt="Synthesize.",
            model=ModelType.DEEPSEEK_V4_PRO,
            language=LanguageType.ENGLISH,
            force_reduce=False,
        )

    assert result.text.strip()
    assert "Recovered" in result.text
    assert attempts >= 3


@pytest.mark.asyncio
async def test_reduce_recovery_split_then_synthesis_preserves_tail(summary_service):
    """Test 5: oversized input → split → reduce parts → assemble preserves late content."""
    chunks = [
        "FRONT matter about early chapters. " * 40,
        "MIDDLE matter about middle chapters. " * 40,
        "TAIL matter essay four theses (4)(5)(6)(7) must survive. " * 40,
    ]
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
        has_front = "FRONT" in batch_text
        has_tail = "TAIL" in batch_text
        if has_front and has_tail:
            return "FRONT only then clif", 100, "length"
        if has_tail:
            return "Preserved TAIL theses (4)(5)(6)(7).", 50, "stop"
        return "Preserved FRONT and MIDDLE.", 50, "stop"

    with patch.object(
        summary_service, "_execute_reduce_call", new=AsyncMock(side_effect=mock_execute)
    ):
        result = await summary_service.run_reduce_phase(
            mapped_summaries=chunks,
            reduce_prompt="Synthesize.",
            model=ModelType.DEEPSEEK_V4_PRO,
            language=LanguageType.ENGLISH,
            force_reduce=True,
        )

    assert result.source_chunk_indices == [0, 1, 2]
    assert "TAIL" in result.text or "(4)" in result.text or "(7)" in result.text
    assert result.finish_reason != "length"
    assert attempts >= 3


@pytest.mark.asyncio
async def test_reduce_filled_budget_length_never_accepted(summary_service):
    """Filled output budget with finish_reason=length must still recover, not accept."""
    chunks = [
        "Alpha section dense content. " * 30,
        "Omega section late content. " * 30,
    ]
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
        # Simulate "filled" truncation (many output tokens) — previously wrongly accepted.
        if attempts == 1:
            long_truncated = ("Alpha " * 2000) + "cut-"
            return long_truncated, max(100, (target_max_tokens or 200) - 5), "length"
        marker = "Omega" if "Omega" in batch_text else "Alpha"
        return f"Complete {marker} summary.", 40, "stop"

    with patch.object(
        summary_service, "_execute_reduce_call", new=AsyncMock(side_effect=mock_execute)
    ):
        result = await summary_service.run_reduce_phase(
            mapped_summaries=chunks,
            reduce_prompt="Synthesize.",
            model=ModelType.DEEPSEEK_V4_PRO,
            language=LanguageType.ENGLISH,
            force_reduce=True,
        )

    assert result.source_chunk_indices == [0, 1]
    assert result.finish_reason != "length"
    assert "cut-" not in result.text
    assert attempts >= 3


@pytest.mark.asyncio
async def test_reduce_filled_budget_stop_is_success_not_split(summary_service):
    """finish_reason=stop at the instruction budget must be accepted, not split."""
    chunks = [
        "Alpha section dense content. " * 30,
        "Omega section late content. " * 30,
    ]
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
        return (
            "Complete synthesis covering Alpha and Omega with a proper ending.",
            max(10, (target_max_tokens or 200) - 1),
            "stop",
        )

    with patch.object(
        summary_service, "_execute_reduce_call", new=AsyncMock(side_effect=mock_execute)
    ):
        result = await summary_service.run_reduce_phase(
            mapped_summaries=chunks,
            reduce_prompt="Synthesize.",
            model=ModelType.DEEPSEEK_V4_PRO,
            language=LanguageType.ENGLISH,
            force_reduce=True,
        )

    assert result.source_chunk_indices == [0, 1]
    assert result.finish_reason == "stop"
    assert "Alpha" in result.text and "Omega" in result.text
    assert attempts == 1


def test_looks_incomplete_tail_accepts_markdown_lists(summary_service):
    complete_list = (
        "La ciencia es falible.\n\n"
        "**15) Es útil:** busca la verdad y provee herramientas para el bien y para el mal\n"
    )
    assert summary_service._looks_incomplete_tail(complete_list) is False
    assert summary_service._looks_incomplete_tail("# Conclusión") is False
    assert summary_service._looks_incomplete_tail("- item without period") is False
    truncated = ("word " * 50) + "cut-"
    assert summary_service._looks_incomplete_tail(truncated) is True


def test_flash_final_pack_limit_allows_single_synthesis(summary_service):
    limit = summary_service._final_reduce_pack_limit(
        ModelType.DEEPSEEK_FLASH,
        SummaryLevel.MODERATE,
        reduce_prompt_tokens=400,
        output_target_tokens=7000,
    )
    assert limit >= 14000
    intermediate = summary_service._reduce_batch_token_limit(
        ModelType.DEEPSEEK_FLASH,
        SummaryLevel.MODERATE,
        400,
        is_intermediate=True,
    )
    # Catalog packs FLASH intermediate REDUCE at reduce_batch_tokens=8000.
    assert intermediate == 8000
    assert limit > intermediate


def test_chunk_overlap_ratio_uses_model_capabilities(summary_service):
    flash = summary_service._chunk_overlap_ratio(ModelType.DEEPSEEK_FLASH)
    v4 = summary_service._chunk_overlap_ratio(ModelType.DEEPSEEK_V4_PRO)
    assert flash == pytest.approx(500 / 4000)
    assert v4 == pytest.approx(200 / 3000)
    assert flash <= summary_service._percent_chunk_overlap
    assert v4 <= summary_service._percent_chunk_overlap


@pytest.mark.asyncio
async def test_unsplittable_length_keeps_original_coverage(summary_service):
    """Indivisible finish_reason=length must not commit the truncated stub."""
    huge = "Indivisible monolith without markdown structure word " * 80

    async def always_length(*args, **kwargs):
        return "Truncated monolith mid-w", 20, "length"

    with patch.object(
        summary_service, "_execute_reduce_call", side_effect=always_length
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        result = await summary_service.run_reduce_phase(
            [huge],
            "p",
            ModelType.DEEPSEEK_V4_PRO,
            LanguageType.ENGLISH,
            force_reduce=True,
        )
    assert "Indivisible monolith" in result.text
    assert "mid-w" not in result.text
    assert result.finish_reason != "length"


@pytest.mark.asyncio
async def test_tiny_final_leftover_length_keeps_original(summary_service):
    """A tiny leftover that hits max_tokens must keep the MAP extract, not fail the job."""
    leftover = "Equilibrio a 155 euros por tonelada de trigo. " * 5

    async def always_length(*args, **kwargs):
        return "padded until cap without a complete economic argument", 80, "length"

    def no_split(text, *args, **kwargs):
        return [text]

    with patch.object(
        summary_service, "_execute_reduce_call", side_effect=always_length
    ), patch.object(
        summary_service, "_split_markdown_structurally", side_effect=no_split
    ), patch.object(
        summary_service, "_check_token_limit", return_value=True
    ):
        result = await summary_service.run_reduce_phase(
            [leftover],
            "p",
            ModelType.DEEPSEEK_V4_PRO,
            LanguageType.ENGLISH,
            force_reduce=True,
        )

    assert "155 euros" in result.text
    assert "padded until cap" not in result.text
    assert result.finish_reason == "stop"


@pytest.mark.asyncio
async def test_unsplittable_complete_length_is_salvaged(summary_service):
    """Complete leftover text with finish_reason=length must not fail the job."""
    dense = "Distinctive market-equilibrium claim with numbers and names. " * 80
    complete = (
        "The wheat market reaches equilibrium at 155 euros per tonne when quantity "
        "supplied equals quantity demanded. Opportunity cost of Facebook use is "
        "estimated from hourly wages. Free-rider problems appear in shared cleaning "
        "and public parks. Empiricism tests causal claims with observable data."
    )

    async def always_length(*args, **kwargs):
        return complete, 120, "length"

    def no_split(text, *args, **kwargs):
        return [text]

    with patch.object(
        summary_service, "_execute_reduce_call", side_effect=always_length
    ), patch.object(
        summary_service, "_split_markdown_structurally", side_effect=no_split
    ), patch.object(
        summary_service, "_check_token_limit", return_value=True
    ):
        result = await summary_service.run_reduce_phase(
            [dense],
            "p",
            ModelType.DEEPSEEK_V4_PRO,
            LanguageType.ENGLISH,
            force_reduce=True,
        )

    assert result.finish_reason == "stop"
    assert "155 euros" in result.text
    assert "Free-rider" in result.text


def test_reduce_output_budget_caps_tiny_leftover(summary_service):
    capped = summary_service._reduce_output_budget_for_batch(
        instruction_target=3000,
        batch_input_tokens=153,
        native_max=8192,
        output_padding_tokens=500,
        is_final=True,
    )
    assert capped < 3000
    assert capped <= 500
    assert capped >= int(153 * 1.35)
    assert capped > 153


def test_tiny_final_leftover_has_stop_headroom(summary_service):
    """asyncio L3 leftovers requested 128 tokens == output and always hit length."""
    leftover = 85
    capped = summary_service._reduce_output_budget_for_batch(
        instruction_target=8192,
        batch_input_tokens=leftover,
        native_max=8192,
        output_padding_tokens=500,
        is_final=True,
    )
    assert capped > leftover
    assert capped >= int(leftover * 1.5 * 1.35) - 1
    assert capped < 8192


def test_intermediate_leftover_budget_allows_stop_without_hitting_cap(summary_service):
    """asyncio 166p leftovers of ~470–2000 tokens must not request max_tokens ~= output."""
    leftover = 900
    capped = summary_service._reduce_output_budget_for_batch(
        instruction_target=int(leftover * 0.55) + 500,
        batch_input_tokens=leftover,
        native_max=8192,
        output_padding_tokens=500,
        is_final=False,
    )
    assert capped >= leftover
    assert capped > int(leftover * 0.55) + 128
    assert capped <= 8192


@pytest.mark.asyncio
async def test_section_assembly_does_not_run_ten_intermediate_rounds(summary_service):
    """One intermediate pass, then a real final REDUCE — not 10 is_final=False rounds or leftover concat."""
    chunks = [
        f"Sección {idx}: principios de economía, optimización y equilibrio empírico. "
        * 40
        for idx in range(8)
    ]
    flags: list[bool] = []

    async def always_stop(
        batch_text,
        prompt,
        model,
        client,
        target_max_tokens=None,
        language=None,
        *args,
        **kwargs,
    ):
        is_final = bool(kwargs.get("is_final_reduce"))
        flags.append(is_final)
        tag = "FINAL" if is_final else "INTERMEDIATE"
        # Return enough tokens to avoid COLLAPSED during intermediate (batch_text itself is large enough)
        return f"{tag} {len(flags)}: {batch_text[:4000]}", 300, "stop"

    with patch.object(
        summary_service, "_execute_reduce_call", side_effect=always_stop
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        result = await summary_service.run_reduce_phase(
            chunks,
            "Integra los bloques.",
            ModelType.QWEN3_14B_BASE,
            LanguageType.SPANISH,
            force_reduce=True,
            assemble_sections=True,
        )

    assert flags
    assert flags.count(False) <= 8
    assert flags.count(True) >= 1
    assert len(flags) <= 12
    assert "FINAL" in result.text
    assert result.source_chunk_indices == list(range(8))
    assert result.finish_reason == "stop"


@pytest.mark.asyncio
async def test_final_sibling_batches_cap_output_to_fit_next_pack(summary_service):
    """Parallel finals must not each emit ~5k tokens or join-cap concatenates (asyncio 003)."""
    chunks = [
        f"Sección {idx}: create_task gather CancelledError event loop. " * 80
        for idx in range(8)
    ]
    final_caps: list[int] = []

    async def record(
        batch_text,
        prompt,
        model,
        client,
        target_max_tokens=None,
        language=None,
        *args,
        **kwargs,
    ):
        cap = int(target_max_tokens or 0)
        if kwargs.get("is_final_reduce"):
            final_caps.append(cap)
        return (
            f"Síntesis {len(final_caps)}: {batch_text[:100]}",
            min(80, max(20, cap // 20 or 20)),
            "stop",
        )

    with patch.object(
        summary_service, "_execute_reduce_call", side_effect=record
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        result = await summary_service.run_reduce_phase(
            chunks,
            "Integra los bloques.",
            ModelType.QWEN3_14B_BASE,
            LanguageType.SPANISH,
            force_reduce=True,
            assemble_sections=True,
        )

    assert result.source_chunk_indices == list(range(8))
    assert final_caps
    # When several finals run together, each cap must be merge-sized, not native 8k.
    if len(final_caps) > 1:
        assert max(final_caps) <= 4000
    assert "Síntesis" in result.text


@pytest.mark.asyncio
async def test_section_assembly_final_chatbot_keeps_coverage(summary_service):
    """Final REDUCE after section-assembly must not replace coverage with a help menu."""
    chunks = [
        "Asyncio create_task schedules coroutines on the running loop. " * 20,
        "CancelledError must be re-raised after cleanup in finally blocks. " * 20,
    ]

    async def mixed(
        batch_text,
        prompt,
        model,
        client,
        target_max_tokens=None,
        language=None,
        *args,
        **kwargs,
    ):
        if kwargs.get("is_final_reduce"):
            return (
                "¿Qué necesitas? Estoy aquí para ayudarte.\n1. Resumen\n2. Temas",
                80,
                "stop",
            )
        return f"EXTRACT {batch_text}", 90, "stop"

    with patch.object(
        summary_service, "_execute_reduce_call", side_effect=mixed
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        result = await summary_service.run_reduce_phase(
            chunks,
            "Integra los bloques.",
            ModelType.QWEN3_14B_BASE,
            LanguageType.SPANISH,
            force_reduce=True,
            assemble_sections=True,
        )

    assert "create_task" in result.text
    assert "CancelledError" in result.text
    assert "¿Qué necesitas?" not in result.text


@pytest.mark.asyncio
async def test_chatbot_reduce_keeps_source_instead_of_help_menu(summary_service):
    """A stop-finished assistant menu must not replace MAP coverage (asyncio 34-line failure)."""
    source_a = (
        "Asyncio create_task schedules coroutines on the running loop. "
        "CancelledError must be re-raised after cleanup in finally blocks."
    )
    source_b = (
        "asyncpg LISTEN/NOTIFY invalidates LRU caches across Sanic workers. "
        "aiofiles avoids blocking disk I/O inside the event loop."
    )
    menu = (
        "¿Qué necesitas? Estoy aquí para ayudarte.\n"
        "1. Resumen del libro\n"
        "2. Explicación de temas específicos\n"
        "Opciones para ayudarte: especifica una."
    )
    calls = {"n": 0}

    async def always_menu(*args, **kwargs):
        calls["n"] += 1
        return menu, 80, "stop"

    with patch.object(
        summary_service, "_execute_reduce_call", side_effect=always_menu
    ), patch.object(summary_service, "_check_token_limit", return_value=True):
        result = await summary_service.run_reduce_phase(
            [source_a, source_b],
            "Integra los bloques.",
            ModelType.DEEPSEEK_V4_PRO,
            LanguageType.SPANISH,
            force_reduce=True,
        )

    assert calls["n"] >= 2
    assert "create_task" in result.text
    assert "asyncpg" in result.text
    assert "¿Qué necesitas?" not in result.text
    assert result.finish_reason == "stop"

@pytest.mark.asyncio
async def test_reduce_collapse_is_rejected_and_recovers(summary_service, caplog):
    """Test 6: intermediate REDUCE that collapses output below 50% target is rejected and split."""
    chunks = [
        "Detail block 1 with lots of information to preserve. " * 30,
        "Detail block 2 with lots of information to preserve. " * 30,
    ]
    attempts = 0
    call_finishes = []

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
        # The input is ~500 tokens. r_comp=0.55. Target=275. 50% of target=137.
        # If output is < 137, it is COLLAPSED.
        if attempts == 1:
            call_finishes.append("stop")
            return "Collapsed summary.", 20, "stop" # 20 is < 137
        call_finishes.append("stop")
        return f"OK recovered summary part {attempts}.", 150, "stop"

    with patch.object(
        summary_service, "_execute_reduce_call", new=AsyncMock(side_effect=mock_execute)
    ):
        with caplog.at_level("INFO"):
            result = await summary_service.run_reduce_phase(
                mapped_summaries=chunks,
                reduce_prompt="Synthesize.",
                model=ModelType.DEEPSEEK_V4_PRO,
                language=LanguageType.ENGLISH,
                force_reduce=False,
                assemble_sections=True,
            )

    assert isinstance(result, ReduceResult)
    assert result.source_chunk_indices == [0, 1]
    assert attempts >= 2
    assert "status=COLLAPSED" in caplog.text
    assert "recovery strategy=split" in caplog.text
    assert "recovered summary" in result.text
