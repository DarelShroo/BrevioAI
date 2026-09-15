from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.services.summary_pipeline import ContextOverflowError
from core.brevio.services.summary_service import SummaryService
from core.shared.enums.model import ModelType
from core.shared.utils.model_capabilities import ModelCapabilities
from core.shared.utils.model_tokens_utils import completion_extra_kwargs


@pytest.fixture
def summary_service() -> SummaryService:
    service = SummaryService()
    service.api_service = MagicMock()
    service.api_service._initialize_client = AsyncMock(return_value=MagicMock())
    return service


def test_dynamic_token_limits(summary_service: SummaryService):
    mock_caps = ModelCapabilities(
        model=ModelType.DEEPSEEK_V4_PRO,
        provider="deepseek",
        context_window=2000,
        native_max_output_tokens=500,
        max_tokens_per_chunk=1000,
        reduce_batch_tokens=800,
        chunk_overlap=50,
        safe_percent=0.05,
        tokenizer="tiktoken",
        supports_json=True,
        supports_mermaid=False,
        supports_chunking=True,
        reduce_input_token_budget=800,
        reduce_safety_margin=100,
        reduce_min_batch_tokens=50,
        output_padding_tokens=50,
        format_safety_margin=150,
        min_tokens_for_postprocess=200,
        global_map_safety_cap=400,
        overhead=100,
        min_chunk_tokens=80,
    )

    with patch(
        "core.brevio.services.summary_service.get_model_capabilities",
        return_value=mock_caps,
    ):
        limit = summary_service._safe_completion_token_limit(
            ModelType.DEEPSEEK_V4_PRO,
            system_tokens=100,
            user_tokens=1500,
            requested_output_tokens=500,
            reserved_tokens=100,
        )
        assert limit == 300

        with pytest.raises(ContextOverflowError):
            summary_service._safe_completion_token_limit(
                ModelType.DEEPSEEK_V4_PRO,
                system_tokens=100,
                user_tokens=2500,
                requested_output_tokens=500,
                reserved_tokens=100,
            )


def test_qwen3_8b_sends_native_ollama_context_options() -> None:
    kwargs = completion_extra_kwargs(ModelType.QWEN3_8B)

    assert kwargs["extra_body"]["think"] is False
    assert kwargs["extra_body"]["options"]["num_ctx"] == 32768
    assert kwargs["extra_body"]["options"]["num_predict"] == 8192


def test_qwen3_num_predict_stays_at_native_max() -> None:
    kwargs = completion_extra_kwargs(ModelType.QWEN3_8B, max_tokens=1500)
    assert kwargs["extra_body"]["options"]["num_predict"] == 8192
    assert kwargs["extra_body"]["options"]["num_ctx"] == 32768
