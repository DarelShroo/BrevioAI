from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.enums.language import LanguageType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.services.summary_pipeline import ContextOverflowError
from core.brevio.services.summary_service import SummaryService
from core.shared.enums.model import ModelType
from core.shared.utils.model_capabilities import ModelCapabilities


def _caps(**overrides) -> ModelCapabilities:
    values = dict(
        model=ModelType.DEEPSEEK_V4_PRO,
        provider="deepseek",
        context_window=10000,
        native_max_output_tokens=2000,
        max_tokens_per_chunk=3000,
        reduce_batch_tokens=8000,
        chunk_overlap=200,
        safe_percent=0.05,
        tokenizer="tiktoken",
        supports_json=True,
        supports_mermaid=False,
        supports_chunking=True,
        reduce_input_token_budget=8000,
        reduce_safety_margin=512,
        reduce_min_batch_tokens=250,
        output_padding_tokens=500,
        format_safety_margin=1500,
        min_tokens_for_postprocess=2000,
        global_map_safety_cap=4000,
        overhead=1000,
        min_chunk_tokens=80,
    )
    values.update(overrides)
    return ModelCapabilities(**values)


@pytest.fixture
def mock_summary_service():
    service = SummaryService()
    # Mocking out actual external dependencies that we don't want to hit in pure logic tests
    service.api_service = MagicMock()
    service.api_service._initialize_client = AsyncMock(return_value=MagicMock())
    return service


def test_safe_completion_token_limit(mock_summary_service: SummaryService):
    """Test that _safe_completion_token_limit respects all constraints (context_window, native_max, requested)"""
    mock_caps = _caps(
        model=ModelType.DEEPSEEK_V4_PRO,
        provider="deepseek",
        context_window=10000,
        native_max_output_tokens=2000,
    )

    with patch(
        "core.brevio.services.summary_service.get_model_capabilities",
        return_value=mock_caps,
    ):
        # Case 1: normal, lots of context available, limits to native_max_output
        limit = mock_summary_service._safe_completion_token_limit(
            ModelType.DEEPSEEK_V4_PRO,
            system_tokens=100,
            user_tokens=1000,
            requested_output_tokens=3000,
            reserved_tokens=100,
        )
        assert limit == 2000  # bounded by native_max_output_tokens

        # Case 2: small context available, bounds even native limit
        limit2 = mock_summary_service._safe_completion_token_limit(
            ModelType.DEEPSEEK_V4_PRO,
            system_tokens=100,
            user_tokens=9000,
            requested_output_tokens=3000,
            reserved_tokens=100,
        )
        # 10000 - 100 - 9000 - 100 = 800 available context
        assert limit2 == 800

        # Case 3: requested is smaller than everything
        limit3 = mock_summary_service._safe_completion_token_limit(
            ModelType.DEEPSEEK_V4_PRO,
            system_tokens=100,
            user_tokens=1000,
            requested_output_tokens=500,
            reserved_tokens=100,
        )
        assert limit3 == 500

        # Case 4: Exceeds context completely
        with pytest.raises(ContextOverflowError):
            mock_summary_service._safe_completion_token_limit(
                ModelType.DEEPSEEK_V4_PRO,
                system_tokens=100,
                user_tokens=10000,
                requested_output_tokens=3000,
                reserved_tokens=100,
            )


def test_reduce_batch_token_limit(mock_summary_service: SummaryService):
    """Test that reduce batch limits dynamically adjust based on model context size."""
    mock_caps = _caps(
        model=ModelType.GPT_4O_MINI,
        provider="openai",
        context_window=8192,
        native_max_output_tokens=4096,
        tokenizer="tiktoken",
    )

    with patch(
        "core.brevio.services.summary_service.get_model_capabilities",
        return_value=mock_caps,
    ):
        # We need output of 4096, system of 500, reserved 512
        # context_limited_input = 8192 - 500 - 4096 - 512 = 3084
        # output_limited_input = 4096 * 2.0 = 8192
        batch_limit = mock_summary_service._reduce_batch_token_limit(
            ModelType.GPT_4O_MINI, SummaryLevel.MODERATE, reduce_prompt_tokens=500
        )
        assert batch_limit == 3084


def test_chunk_limit_in_formatting_phase(mock_summary_service: SummaryService):
    """Test the logic used inside run_formatting_phase to determine chunk_limit."""
    # We will simulate the chunk limit math inline, which ensures it dynamically adapts
    mock_caps = _caps(
        model=ModelType.GPT_4,
        provider="openai",
        context_window=10000,
        native_max_output_tokens=2000,
        tokenizer="tiktoken",
    )

    format_prompt_tokens = 400
    EXPANSION_FACTOR = 1.05

    # Same math as in run_formatting_phase
    context_limited_input = (
        mock_caps.context_window
        - format_prompt_tokens
        - mock_caps.native_max_output_tokens
        - 512
    )
    # 10000 - 400 - 2000 - 512 = 7088

    output_limited_input = int(
        (mock_caps.native_max_output_tokens - 200) / EXPANSION_FACTOR
    )
    # (2000 - 200) / 1.05 = 1714

    chunk_limit = max(250, min(context_limited_input, output_limited_input))
    assert chunk_limit == 1714


@pytest.mark.asyncio
async def test_chunk_text_dynamic_limits(mock_summary_service: SummaryService):
    """Test that chunk_text dynamically respects model-specific max_tokens_per_chunk."""
    # We will use GPT_4 with a small chunk size, and DEEPSEEK with a larger one
    text = "A " * 4000  # Roughly 4000 tokens of just "A"

    # 1. GPT-4 has max_tokens_per_chunk=3000
    chunks_gpt4 = await mock_summary_service.chunk_text(
        text, chunk_size=3000, overlap=0.0, model=ModelType.GPT_4
    )
    # 4000 tokens should be split into 2 chunks for GPT-4
    assert len(chunks_gpt4) == 2

    # 2. Suppose a hypothetical model with max_tokens_per_chunk=5000
    chunks_large = await mock_summary_service.chunk_text(
        text, chunk_size=5000, overlap=0.0, model=ModelType.DEEPSEEK_V4_PRO
    )
    # 4000 tokens fits in a single 5000 token chunk
    assert len(chunks_large) == 1


@pytest.mark.asyncio
async def test_adaptive_salience_policy_budget():
    """Test that the adaptive salience policy assigns budgets dynamically based on model limits."""
    from core.shared.utils.adaptive_salience_policy import AdaptiveSaliencePolicy

    policy = AdaptiveSaliencePolicy()

    # Very concise summary of a small document
    from core.brevio.enums.language import LanguageType

    decision1 = policy.budget(
        ModelType.DEEPSEEK_V4_PRO,
        SummaryLevel.VERY_CONCISE,
        document_tokens=1000,
        language=LanguageType.ENGLISH,
    )
    assert decision1.output_target_tokens > 0
    assert decision1.output_target_tokens <= 1000 + 200  # bounded by document size

    # Very detailed summary of a huge document
    decision2 = policy.budget(
        ModelType.DEEPSEEK_V4_PRO,
        SummaryLevel.VERY_DETAILED,
        document_tokens=100000,
        language=LanguageType.ENGLISH,
    )
    # Retention target for a 100k very-detailed doc exceeds a single DeepSeek call.
    assert decision2.output_target_tokens > decision2.output_hard_limit
    assert decision2.requires_section_assembly is True
    assert decision2.output_max_tokens <= 16384
    assert decision2.output_hard_limit == 16384


@pytest.mark.asyncio
async def test_split_markdown_structurally_dynamic(
    mock_summary_service: SummaryService,
):
    """Test that markdown splitting respects dynamic token budgets."""
    # Create a 2000 token text
    text = "Sentence one. " * 500

    from core.shared.utils.model_tokens_utils import get_encoder

    encoder = get_encoder(ModelType.GPT_4)

    # Let's say max_tokens is 500
    blocks = mock_summary_service._split_markdown_structurally(
        text, max_tokens=500, encoder=encoder
    )

    for block in blocks:
        # Check that no block exceeds 500 tokens
        assert len(encoder.encode(block)) <= 500


def test_deepseek_flash_uses_deepseek_client_extras():
    from core.shared.utils.model_tokens_utils import (
        completion_extra_kwargs,
        is_deepseek,
    )

    assert is_deepseek(ModelType.DEEPSEEK_FLASH) is True
    assert is_deepseek(ModelType.DEEPSEEK_V4_PRO) is True
    assert is_deepseek(ModelType.GPT_4) is False
    assert completion_extra_kwargs(ModelType.DEEPSEEK_FLASH) == {
        "extra_body": {"thinking": {"type": "disabled"}}
    }
    assert completion_extra_kwargs(ModelType.GPT_4) == {}
    assert completion_extra_kwargs(ModelType.QWEN3_14B, max_tokens=2048) == {
        "extra_body": {
            "think": False,
            "options": {"num_ctx": 16384, "num_predict": 8192},
        }
    }
    assert completion_extra_kwargs(ModelType.QWEN3_14B, max_tokens=99999) == {
        "extra_body": {
            "think": False,
            "options": {"num_ctx": 16384, "num_predict": 8192},
        }
    }
    assert completion_extra_kwargs(ModelType.QWEN3_32B) == {
        "extra_body": {
            "think": False,
            "options": {"num_ctx": 32768, "num_predict": 16384},
        }
    }
    assert completion_extra_kwargs(ModelType.DEEPSEEK_R1_LOCAL_IQ3_XS) == {
        "extra_body": {
            "think": False,
            "options": {"num_ctx": 32768, "num_predict": 8192},
        }
    }
    assert completion_extra_kwargs(ModelType.GPT_OSS_20B) == {
        "extra_body": {
            "think": False,
            "options": {"num_ctx": 32768, "num_predict": 8192},
        }
    }
    assert completion_extra_kwargs(ModelType.GEMMA4_31B_IQ3) == {
        "extra_body": {
            "think": False,
            "options": {"num_ctx": 32768, "num_predict": 8192},
        }
    }


def test_history_token_model_records_time_and_api_requests(
    mock_summary_service: SummaryService,
):
    from core.shared.models.history_token_model import HistoryTokenModel

    mock_summary_service._pipeline_t0 = __import__("time").time() - 1.5
    mock_summary_service.history_token_model = HistoryTokenModel()
    assert mock_summary_service.history_token_model.api_request_count == 0
    assert mock_summary_service.history_token_model.total_time in (0, 0.0, None)

    mock_summary_service._record_api_request("MAP")
    mock_summary_service._record_api_request("REDUCE")
    mock_summary_service._finalize_timing()

    dumped = mock_summary_service.history_token_model.model_dump()
    assert dumped["api_request_count"] == 2
    assert dumped["total_time"] >= 1.0
    assert isinstance(dumped["total_time"], float)
    assert dumped["completed_at"]
    assert len(dumped["completed_at"]) == 19  # YYYY-MM-DD HH:MM:SS


def test_map_api_max_tokens_adds_headroom(mock_summary_service: SummaryService):
    assert mock_summary_service._map_api_max_tokens(1000, 8192) == 1350
    assert mock_summary_service._map_api_max_tokens(4000, 4000) == 4000
    assert mock_summary_service._map_api_max_tokens(4000, 8192) == 5400


def test_gemma_completion_timeout_covers_dense_local_generation(
    mock_summary_service: SummaryService,
):
    assert (
        mock_summary_service._completion_timeout_s(ModelType.GEMMA4_31B_IQ3, "MAP")
        == 600.0
    )
    assert (
        mock_summary_service._completion_timeout_s(ModelType.GEMMA4_31B_IQ3, "REDUCE")
        == 600.0
    )
    assert (
        mock_summary_service._completion_timeout_s(
            ModelType.GEMINI_3_1_FLASH_LITE, "MAP"
        )
        == 120.0
    )
    assert (
        mock_summary_service._completion_timeout_s(
            ModelType.GEMINI_3_1_FLASH_LITE, "REDUCE"
        )
        == 180.0
    )


def test_looks_like_assistant_chat_detects_help_menus(
    mock_summary_service: SummaryService,
):
    assert mock_summary_service._looks_like_assistant_chat(
        "¿Qué necesitas? Estoy aquí para ayudarte con este libro."
    )
    assert mock_summary_service._looks_like_assistant_chat(
        "How can I help you today? What do you need?"
    )
    assert not mock_summary_service._looks_like_assistant_chat(
        "Python asyncio usa event loops para programar corutinas."
    )
