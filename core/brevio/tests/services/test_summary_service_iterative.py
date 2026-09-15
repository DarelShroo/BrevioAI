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
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.services.summary_service import (
    MapChunkResult,
    ReduceConvergenceError,
    SummaryService,
)
from core.shared.enums.model import ModelType
from core.shared.utils.model_tokens_utils import get_encoder


def _maps(*texts: str) -> list[MapChunkResult]:
    return [
        MapChunkResult(i, f"original-{i} {text}", "SUCCESS", text)
        for i, text in enumerate(texts)
    ]


@pytest.fixture(autouse=True)
def force_hierarchical_route():
    """Document orchestration tests exercise MAP→REDUCE, not single-pass DIRECT."""
    from core.shared.utils.adaptive_salience_policy import (
        AdaptiveSaliencePolicy as RealPolicy,
    )

    decision = MagicMock()
    decision.route = "hierarchical"
    decision.output_target_tokens = 500
    decision.output_min_tokens = 200
    decision.output_hard_limit = 8192
    decision.requires_section_assembly = False
    decision.section_keep_ratio = 0.55
    with patch("core.brevio.services.summary_service.AdaptiveSaliencePolicy") as pol:
        pol.return_value.budget.return_value = decision
        pol.calculate_map_safety_ceiling = staticmethod(
            RealPolicy.calculate_map_safety_ceiling
        )
        yield


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
    monkeypatch.setenv("BREVIO_MIN_TOKENS_FOR_POSTPROCESS", "0")
    monkeypatch.setenv("BREVIO_ENABLE_FORMAT_PHASE", "1")


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
        service.token_bucket = 200_000
        service.tokens_per_minute = 200_000
        return service


def make_mock_response(
    content: str,
    total_tokens: int = 100,
    completion_tokens: int = 50,
    finish_reason: str = "stop",
) -> MagicMock:
    mock = MagicMock(spec=ChatCompletion)
    mock_choice = MagicMock()
    mock_choice.message = MagicMock(spec=ChatCompletionMessage, content=content)
    mock_choice.finish_reason = finish_reason
    mock.choices = [mock_choice]
    mock.usage = MagicMock(
        spec=CompletionUsage,
        total_tokens=total_tokens,
        completion_tokens=completion_tokens,
        prompt_tokens=total_tokens - completion_tokens,
    )
    return mock


# ─────────────────────────────────────────────────────────────────────────────
# 1. Normal document reduction
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_normal_document_reduction(
    summary_service: SummaryService, tmp_path
) -> None:
    """Case 1: Standard reduction where the first reduce yields an acceptable ratio."""
    full_text = "word " * 5000  # Large document

    with patch.object(
        summary_service, "chunk_text", return_value=["chunk1", "chunk2"]
    ), patch.object(
        summary_service, "run_map_phase", return_value=(_maps("map1", "map2"), 100)
    ), patch.object(
        summary_service, "run_reduce_phase", return_value=("Short summary", 50)
    ), patch.object(
        summary_service, "run_formatting_phase", return_value=("Formatted summary", 60)
    ), patch.object(
        summary_service, "detect_language_with_retry_safe", return_value="en"
    ), patch(
        "core.brevio.services.summary_service.get_encoder"
    ) as mock_get_encoder, patch.object(
        summary_service.api_service,
        "_initialize_client",
        return_value=summary_service.client,
    ), patch.object(
        summary_service.directory_manager, "write_summary", new_callable=AsyncMock
    ), patch.object(
        summary_service.directory_manager,
        "read_pdf",
        new_callable=AsyncMock,
        return_value=[full_text],
    ), patch.object(
        summary_service.directory_manager, "validate_paths", new_callable=AsyncMock
    ):
        mock_encoder = MagicMock()
        # file tokens = 5000, reduced summary tokens = 500, ratio = 10%
        mock_encoder.encode.side_effect = (
            lambda text: [1] * 5000 if "word " in text else [1] * 500
        )
        mock_get_encoder.return_value = mock_encoder

        mock_file_config = MagicMock()
        mock_file_config.content = full_text
        mock_file_config.summary_path = str(tmp_path / "output.md")
        mock_file_config.token_count = 5000
        mock_file_config.document_path = "test.pdf"

        # Test the iterative compression loop
        summary_service.advanced_prompt_generator.get_map_prompt = AsyncMock(
            return_value="map prompt"
        )
        summary_service.advanced_prompt_generator.get_reduce_prompt = AsyncMock(
            return_value="reduce prompt"
        )
        summary_service.advanced_prompt_generator.get_format_prompt = AsyncMock(
            return_value="format prompt"
        )

        mock_prompt_config = MagicMock(language=LanguageType.ENGLISH)
        await summary_service._process_single_document(
            "prompt", mock_file_config, ModelType.DEEPSEEK_V4_PRO, mock_prompt_config
        )

        summary_service.run_reduce_phase.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Long document (Iterative) & 9. Too long result triggering a second pass
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
@pytest.mark.skip(reason="Obsolete architecture")
async def test_long_document_iterative_reduction(
    summary_service: SummaryService,
) -> None:
    """Case 2 & 9: First reduce yields a large text, triggering a second reduce."""
    full_text = "word " * 5000

    mock_run_reduce = AsyncMock()
    # First call returns 3000 tokens (ratio 0.60 > target 0.40)
    # Second call returns 1000 tokens (ratio 0.20 <= target 0.40)
    mock_run_reduce.side_effect = [
        ("Long summary text", 100),
        ("Short summary text", 50),
    ]

    with patch.object(
        summary_service, "chunk_text", return_value=["chunk1", "chunk2"]
    ), patch.object(
        summary_service, "run_map_phase", return_value=(_maps("map1", "map2"), 100)
    ), patch.object(
        summary_service, "run_reduce_phase", mock_run_reduce
    ), patch.object(
        summary_service, "run_formatting_phase", return_value=("Formatted summary", 60)
    ), patch.object(
        summary_service, "detect_language_with_retry_safe", return_value="en"
    ), patch(
        "core.brevio.services.summary_service.get_encoder"
    ) as mock_get_encoder, patch.object(
        summary_service.api_service,
        "_initialize_client",
        return_value=summary_service.client,
    ), patch.object(
        summary_service.directory_manager, "write_summary", new_callable=AsyncMock
    ), patch.object(
        summary_service.directory_manager,
        "read_pdf",
        new_callable=AsyncMock,
        return_value=[full_text],
    ), patch.object(
        summary_service.directory_manager, "validate_paths", new_callable=AsyncMock
    ):

        def encode_mock(text):
            if text == full_text:
                return [1] * 5000
            elif text == "Long summary text":
                return [1] * 3000
            elif text == "Short summary text":
                return [1] * 1000
            else:
                return [1] * 500

        mock_encoder = MagicMock()
        mock_encoder.encode.side_effect = encode_mock
        mock_get_encoder.return_value = mock_encoder

        mock_file_config = MagicMock()
        mock_file_config.content = full_text
        mock_file_config.token_count = 5000
        mock_file_config.document_path = "test.pdf"

        summary_service.advanced_prompt_generator.get_map_prompt = AsyncMock(
            return_value="map prompt"
        )
        summary_service.advanced_prompt_generator.get_reduce_prompt = AsyncMock(
            return_value="reduce prompt"
        )
        summary_service.advanced_prompt_generator.get_format_prompt = AsyncMock(
            return_value="format prompt"
        )

        mock_prompt_config = MagicMock(language=LanguageType.ENGLISH)
        await summary_service._process_single_document(
            "prompt", mock_file_config, ModelType.DEEPSEEK_V4_PRO, mock_prompt_config
        )

        assert mock_run_reduce.call_count == 2

        # Second call must have force_reduce=True
        call_args = mock_run_reduce.call_args_list[1]
        assert call_args[1].get("force_reduce") is True


# ─────────────────────────────────────────────────────────────────────────────
# 3. Already compact document
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_compact_document_skips_iteration(
    summary_service: SummaryService, tmp_path
) -> None:
    """Case 3: Short document where initial reduce produces < 1000 tokens."""
    full_text = "word " * 500

    with patch.object(
        summary_service, "chunk_text", return_value=["chunk1"]
    ), patch.object(
        summary_service, "run_map_phase", return_value=(_maps("map1"), 100)
    ), patch.object(
        summary_service, "run_reduce_phase", return_value=("Compact summary", 50)
    ), patch.object(
        summary_service, "run_formatting_phase", return_value=("Formatted summary", 60)
    ), patch.object(
        summary_service, "detect_language_with_retry_safe", return_value="en"
    ), patch(
        "core.brevio.services.summary_service.get_encoder"
    ) as mock_get_encoder, patch.object(
        summary_service.api_service,
        "_initialize_client",
        return_value=summary_service.client,
    ), patch.object(
        summary_service.directory_manager, "write_summary", new_callable=AsyncMock
    ), patch.object(
        summary_service.directory_manager,
        "read_pdf",
        new_callable=AsyncMock,
        return_value=[full_text],
    ), patch.object(
        summary_service.directory_manager, "validate_paths", new_callable=AsyncMock
    ):
        mock_encoder = MagicMock()
        # Even if ratio is high, if tokens < 1000, it breaks.
        mock_encoder.encode.side_effect = (
            lambda text: [1] * 500 if "word " in text else [1] * 400
        )
        mock_get_encoder.return_value = mock_encoder

        mock_file_config = MagicMock()
        mock_file_config.content = full_text
        mock_file_config.token_count = 5000
        mock_file_config.document_path = "test.pdf"
        mock_file_config.summary_path = str(tmp_path / "summary.md")

        summary_service.advanced_prompt_generator.get_map_prompt = AsyncMock()
        summary_service.advanced_prompt_generator.get_reduce_prompt = AsyncMock()
        summary_service.advanced_prompt_generator.get_format_prompt = AsyncMock()

        mock_prompt_config = MagicMock(language=LanguageType.ENGLISH)
        await summary_service._process_single_document(
            "prompt", mock_file_config, ModelType.DEEPSEEK_V4_PRO, mock_prompt_config
        )

        summary_service.run_reduce_phase.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Code preservation (Dynamic max_tokens)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
@pytest.mark.skip(reason="Obsolete architecture")
async def test_map_dynamic_max_tokens(summary_service: SummaryService) -> None:
    """Case 4: `generate_summary_chunk` limits max_tokens."""
    mock_resp = make_mock_response("Summary.", total_tokens=120, completion_tokens=40)

    with patch.object(
        summary_service.client.chat.completions,
        "create",
        new=AsyncMock(return_value=mock_resp),
    ) as mock_create, patch(
        "core.brevio.services.summary_service.get_encoder"
    ) as mock_get_encoder:
        mock_encoder = MagicMock()
        # Prompt tokens = 10, Chunk tokens = 1000
        mock_encoder.encode.side_effect = (
            lambda text: [1] * 1000 if text == "Chunk" else [1] * 10
        )
        mock_get_encoder.return_value = mock_encoder

        mock_prompt_config = MagicMock(language=LanguageType.ENGLISH)
        await summary_service.generate_summary_chunk(
            0, "Chunk", "Prompt", ModelType.DEEPSEEK_V4_PRO, mock_prompt_config
        )

        # Max tokens should be min(4096, 1000 * 0.6 + 200) = 800
        call_args = mock_create.call_args[1]
        assert call_args["max_tokens"] == 800


# ─────────────────────────────────────────────────────────────────────────────
# 5. Overlap calculation fix
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_overlap_calculation(summary_service: SummaryService, tmp_path) -> None:
    """Case 5: chunk_text receives _percent_chunk_overlap directly."""
    full_text = "word " * 5000

    with patch.object(
        summary_service, "chunk_text", return_value=["chunk1"]
    ) as mock_chunk_text, patch.object(
        summary_service, "run_map_phase", return_value=(_maps("map1"), 100)
    ), patch.object(
        summary_service, "run_reduce_phase", return_value=("Compact summary", 50)
    ), patch.object(
        summary_service, "run_formatting_phase", return_value=("Formatted", 60)
    ), patch.object(
        summary_service, "detect_language_with_retry_safe", return_value="en"
    ), patch.object(
        summary_service.directory_manager, "write_summary", new_callable=AsyncMock
    ), patch.object(
        summary_service.directory_manager,
        "read_pdf",
        new_callable=AsyncMock,
        return_value=[full_text],
    ), patch.object(
        summary_service.directory_manager, "validate_paths", new_callable=AsyncMock
    ):
        mock_file_config = MagicMock()
        mock_file_config.content = full_text
        mock_file_config.token_count = 5000
        mock_file_config.document_path = "test.pdf"
        mock_file_config.summary_path = str(tmp_path / "summary.md")

        summary_service.advanced_prompt_generator.get_map_prompt = AsyncMock()
        summary_service.advanced_prompt_generator.get_reduce_prompt = AsyncMock()
        summary_service.advanced_prompt_generator.get_format_prompt = AsyncMock()

        mock_prompt_config = MagicMock(language=LanguageType.ENGLISH)
        await summary_service._process_single_document(
            "prompt", mock_file_config, ModelType.DEEPSEEK_V4_PRO, mock_prompt_config
        )

        mock_chunk_text.assert_called_once()
        # Args: full_text, chunk_size, overlap
        assert mock_chunk_text.call_args[0][2] == pytest.approx(
            summary_service._chunk_overlap_ratio(ModelType.DEEPSEEK_V4_PRO)
        )


@pytest.mark.asyncio
async def test_transcription_uses_document_pipeline(
    summary_service: SummaryService,
) -> None:
    from core.brevio.models.file_config_model import FileConfig
    from core.brevio.models.response_model import SummaryResponse

    file_config = FileConfig(
        transcription_path="/tmp/transcription.txt",
        summary_path="/tmp/summary.md",
    )
    prompt_config = MagicMock()
    expected = SummaryResponse(success=True, summary="ok")
    with patch.object(
        summary_service,
        "generate_summary_document",
        new=AsyncMock(return_value=expected),
    ) as mock_generate:
        result = await summary_service._process_single_transcription(
            prompt_config,
            file_config,
            MagicMock(),
            folder_id="folder",
            user_id="user",
        )
    mock_generate.assert_awaited_once()
    assert file_config.document_path == "/tmp/transcription.txt"
    assert result.success is True


# ─────────────────────────────────────────────────────────────────────────────
# 6. Single element reduce execution
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_single_element_force_reduce(summary_service: SummaryService) -> None:
    """Case 6: force_reduce bypasses the len <= 1 check."""
    summaries = ["Single large summary"]

    with patch.object(
        summary_service,
        "_execute_reduce_call",
        return_value=("Compressed summary", 100, "stop"),
    ) as mock_exec, patch.object(
        summary_service.api_service,
        "_initialize_client",
        return_value=summary_service.client,
    ):
        # Without force_reduce
        res, tokens = await summary_service.run_reduce_phase(
            summaries, "p", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )
        assert res == "Single large summary"
        mock_exec.assert_not_called()

        # With force_reduce
        res, tokens = await summary_service.run_reduce_phase(
            summaries,
            "p",
            ModelType.DEEPSEEK_V4_PRO,
            LanguageType.ENGLISH,
            force_reduce=True,
        )
        assert res == "Compressed summary"
        mock_exec.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 7. Recovery from finish_reason=length & 8. Fail during REDUCE
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_reduce_batch_failure_modes(summary_service: SummaryService) -> None:
    """finish_reason=length on an unsplittable leftover must not commit the truncated stub."""
    batch_text = "Huge text block" * 1000

    async def always_length(*args, **kwargs):
        return "Truncated text", 10, "length"

    with patch.object(
        summary_service, "_execute_reduce_call", side_effect=always_length
    ), patch.object(
        summary_service.api_service,
        "_initialize_client",
        return_value=summary_service.client,
    ), patch.object(
        summary_service, "_check_token_limit", return_value=True
    ):
        result = await summary_service.run_reduce_phase(
            [batch_text],
            "p",
            ModelType.DEEPSEEK_V4_PRO,
            LanguageType.ENGLISH,
            force_reduce=True,
        )
    assert "Huge text block" in result.text
    assert result.text.strip() != "Truncated text"

    with patch.object(
        summary_service, "_execute_reduce_call", side_effect=Exception("API Down")
    ), patch.object(
        summary_service.api_service,
        "_initialize_client",
        return_value=summary_service.client,
    ), patch.object(
        summary_service, "_check_token_limit", return_value=True
    ):
        with pytest.raises(Exception, match="API Down"):
            await summary_service.run_reduce_phase(
                [batch_text],
                "p",
                ModelType.DEEPSEEK_V4_PRO,
                LanguageType.ENGLISH,
                force_reduce=True,
            )


@pytest.mark.asyncio
async def test_reduce_phase_assembles_when_not_converging(
    summary_service: SummaryService,
) -> None:
    """When hierarchical rounds stay multi-chunk through the final round, assemble with coverage."""
    summaries = ["bloque A completo.", "bloque B completo."]

    async def mock_reduce(*args, **kwargs):
        batch = args[0]
        return f"reducido: {batch}", 50, "stop"

    with patch(
        "core.brevio.services.summary_service.get_encoder"
    ) as mock_enc_fn, patch.object(
        summary_service, "_execute_reduce_call", side_effect=mock_reduce
    ), patch.object(
        summary_service.api_service,
        "_initialize_client",
        return_value=summary_service.client,
    ):
        mock_enc = MagicMock()
        mock_enc.encode.return_value = [1] * 30000
        mock_enc_fn.return_value = mock_enc

        result = await summary_service.run_reduce_phase(
            summaries, "p", ModelType.DEEPSEEK_V4_PRO, LanguageType.ENGLISH
        )

    assert "reducido:" in result.text
    assert result.source_chunk_indices == [0, 1]
    assert result.finish_reason != "length"


# ─────────────────────────────────────────────────────────────────────────────
# 10. Stagnation detection
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
@pytest.mark.skip(reason="Obsolete architecture")
async def test_stagnation_detection(summary_service: SummaryService) -> None:
    """Case 10: If tokens drop by less than 5%, iteration stops early."""
    full_text = "word " * 5000

    mock_run_reduce = AsyncMock()
    # First returns 3000 tokens
    # Second returns 2900 tokens (ratio > 0.95 of 3000 -> stagnation!)
    mock_run_reduce.side_effect = [
        ("Long summary text 1", 100),
        ("Long summary text 2", 50),
    ]

    with patch.object(
        summary_service, "chunk_text", return_value=["chunk1", "chunk2"]
    ), patch.object(
        summary_service, "run_map_phase", return_value=(_maps("map1", "map2"), 100)
    ), patch.object(
        summary_service, "run_reduce_phase", mock_run_reduce
    ), patch.object(
        summary_service, "run_formatting_phase", return_value=("Formatted summary", 60)
    ), patch.object(
        summary_service, "detect_language_with_retry_safe", return_value="en"
    ), patch(
        "core.brevio.services.summary_service.get_encoder"
    ) as mock_get_encoder, patch.object(
        summary_service.api_service,
        "_initialize_client",
        return_value=summary_service.client,
    ), patch.object(
        summary_service.directory_manager, "write_summary", new_callable=AsyncMock
    ), patch.object(
        summary_service.directory_manager,
        "read_pdf",
        new_callable=AsyncMock,
        return_value=[full_text],
    ), patch.object(
        summary_service.directory_manager, "validate_paths", new_callable=AsyncMock
    ):

        def encode_mock(text):
            if text == full_text:
                return [1] * 5000
            elif text == "Long summary text 1":
                return [1] * 3000
            elif text == "Long summary text 2":
                return [1] * 2900
            else:
                return [1] * 500

        mock_encoder = MagicMock()
        mock_encoder.encode.side_effect = encode_mock
        mock_get_encoder.return_value = mock_encoder

        mock_file_config = MagicMock()
        mock_file_config.content = full_text
        mock_file_config.token_count = 5000
        mock_file_config.document_path = "test.pdf"

        summary_service.advanced_prompt_generator.get_map_prompt = AsyncMock(
            return_value="map prompt"
        )
        summary_service.advanced_prompt_generator.get_reduce_prompt = AsyncMock(
            return_value="reduce prompt"
        )
        summary_service.advanced_prompt_generator.get_format_prompt = AsyncMock(
            return_value="format prompt"
        )

        mock_prompt_config = MagicMock(language=LanguageType.ENGLISH)
        await summary_service._process_single_document(
            "prompt", mock_file_config, ModelType.DEEPSEEK_V4_PRO, mock_prompt_config
        )

        # Expect exactly 2 calls because the second one stagnates
        assert mock_run_reduce.call_count == 2


# ─────────────────────────────────────────────────────────────────────────────
# 11. Spanish language detection
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("langdetect"),
    reason="langdetect module not installed in this environment",
)
async def test_spanish_language_detection(summary_service: SummaryService) -> None:
    """Case 11: verify langdetect correctly identifies Spanish."""
    spanish_text = "Este es un texto en español para probar que el sistema puede detectar el idioma correctamente."

    lang = await summary_service.detect_language_with_retry_safe(spanish_text)
    assert lang == "es"

    english_text = (
        "This is an english text to prove that the system can detect the language."
    )
    lang2 = await summary_service.detect_language_with_retry_safe(english_text)
    assert lang2 == "en"


# ─────────────────────────────────────────────────────────────────────────────
# 12. FORMAT phase not reintroducing content
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_global_validation_truncation(
    summary_service: SummaryService, tmp_path
) -> None:
    """finish_reason=length must never commit; truncated REDUCE is not a valid summary."""
    full_text = "word " * 50

    async def fake_reduce(*args, **kwargs):
        summary_service.last_reduce_result = MagicMock(finish_reason="length")
        return "Compact", 10

    with patch.object(
        summary_service, "chunk_text", return_value=["chunk1"]
    ), patch.object(
        summary_service, "run_map_phase", return_value=(_maps("map1"), 10)
    ), patch.object(
        summary_service, "run_reduce_phase", side_effect=fake_reduce
    ), patch.object(
        summary_service, "run_formatting_phase", return_value=("Formatted summary", 10)
    ), patch.object(
        summary_service, "detect_language_with_retry_safe", return_value="en"
    ), patch.object(
        summary_service.api_service,
        "_initialize_client",
        return_value=summary_service.client,
    ), patch.object(
        summary_service.directory_manager, "write_summary", new_callable=AsyncMock
    ), patch.object(
        summary_service.directory_manager,
        "read_pdf",
        new_callable=AsyncMock,
        return_value=[full_text],
    ), patch.object(
        summary_service.directory_manager, "validate_paths", new_callable=AsyncMock
    ), patch.object(
        summary_service, "_validate_global_structure", return_value=(True, [])
    ):
        mock_file_config = MagicMock()
        mock_file_config.content = full_text
        mock_file_config.token_count = 5000
        mock_file_config.document_path = "test.pdf"
        mock_file_config.summary_path = str(tmp_path / "summary.md")

        summary_service.advanced_prompt_generator.get_map_prompt = AsyncMock()
        summary_service.advanced_prompt_generator.get_reduce_prompt = AsyncMock()
        summary_service.advanced_prompt_generator.get_format_prompt = AsyncMock()

        mock_prompt_config = MagicMock(language=LanguageType.ENGLISH)
        res = await summary_service._process_single_document(
            "prompt", mock_file_config, ModelType.DEEPSEEK_V4_PRO, mock_prompt_config
        )
        assert res.success is False
        assert not (tmp_path / "summary.md").exists()
        assert res.error_type == "ReduceConvergenceError" or (
            res.diagnostics and res.diagnostics.get("finish_reason") == "length"
        )
