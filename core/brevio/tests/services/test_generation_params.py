import pytest

from core.shared.enums.model import ModelType
from core.shared.utils.generation_params import (
    GenerationParamError,
    chat_completion_kwargs,
    validate_generation_params,
)
from core.shared.utils.model_capabilities import (
    MODEL_CAPABILITIES,
    generation_temperature,
    get_model_capabilities,
)


def test_gpt_5_6_uses_max_completion_tokens_and_omits_temperature() -> None:
    caps = get_model_capabilities(ModelType.GPT_5_6)
    assert caps.output_token_param == "max_completion_tokens"
    assert caps.supports_temperature is False
    assert caps.context_window == 1_050_000
    assert caps.native_max_output_tokens == 128_000
    assert generation_temperature(caps) == 0.0
    kwargs = chat_completion_kwargs(
        ModelType.GPT_5_6,
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=128,
        temperature=0.2,
    )
    assert "max_completion_tokens" in kwargs
    assert "max_tokens" not in kwargs
    assert "temperature" not in kwargs
    validate_generation_params(ModelType.GPT_5_6, temperature=0.2)


def test_grok_chat_kwargs_include_reasoning_effort() -> None:
    kwargs = chat_completion_kwargs(
        ModelType.GROK_4_6,
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=64,
        temperature=0.2,
        extra={"reasoning_effort": "low"},
    )
    assert kwargs["reasoning_effort"] == "low"
    assert "temperature" not in kwargs
    assert kwargs["max_tokens"] == 64


def test_user_sampling_params_are_ignored() -> None:
    validate_generation_params(ModelType.GPT_4O_MINI, max_output_tokens=10**9)
    validate_generation_params(ModelType.GPT_4O_MINI, temperature=1.7)
    validate_generation_params(ModelType.CLAUDE_SONNET_5, temperature=0.4)
    validate_generation_params(ModelType.GROK_4_6, temperature=0.7)


def test_claude_sonnet_accepts_effort_not_user_temperature() -> None:
    validate_generation_params(ModelType.CLAUDE_SONNET_5, reasoning_effort="high")
    with pytest.raises(GenerationParamError):
        validate_generation_params(ModelType.CLAUDE_HAIKU_4_5, reasoning_effort="high")
    kwargs = chat_completion_kwargs(
        ModelType.CLAUDE_SONNET_5,
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=64,
        temperature=1.0,
    )
    assert "temperature" not in kwargs


def test_grok_and_gemini_expose_official_reasoning_values() -> None:
    grok = get_model_capabilities(ModelType.GROK_4_6)
    gemini = get_model_capabilities(ModelType.GEMINI_3_1_FLASH_LITE)
    assert grok.reasoning == "reasoning_effort"
    assert grok.reasoning_values == ("low", "medium", "high", "xhigh")
    assert grok.supports_temperature is False
    validate_generation_params(ModelType.GROK_4_6, reasoning_effort="xhigh")
    validate_generation_params(ModelType.GROK_4_6, temperature=0.7)
    with pytest.raises(GenerationParamError):
        validate_generation_params(ModelType.GROK_4_6, reasoning_effort="none")
    assert gemini.reasoning == "reasoning_effort"
    assert gemini.reasoning_values == ("minimal", "low", "medium", "high")
    validate_generation_params(
        ModelType.GEMINI_3_1_FLASH_LITE, reasoning_effort="minimal"
    )
    with pytest.raises(GenerationParamError):
        validate_generation_params(
            ModelType.GEMINI_3_1_FLASH_LITE, reasoning_effort="none"
        )


def test_official_default_temperatures() -> None:
    expected = {
        ModelType.GPT_4O_MINI: 1.0,
        ModelType.GPT_4: 1.0,
        ModelType.DEEPSEEK_V4_PRO: 1.0,
        ModelType.DEEPSEEK_FLASH: 1.0,
        ModelType.GEMINI_3_1_FLASH_LITE: 1.0,
        ModelType.CLAUDE_HAIKU_4_5: 1.0,
        ModelType.QWEN3_8B: 0.7,
        ModelType.QWEN3_14B: 0.7,
        ModelType.QWEN3_14B_BASE: 0.7,
        ModelType.QWEN3_32B: 0.7,
        ModelType.DEEPSEEK_R1_LOCAL_IQ3_XS: 0.6,
        ModelType.GPT_OSS_20B: 1.0,
        ModelType.GEMMA4_31B_IQ3: 1.0,
    }
    for model, temperature in expected.items():
        caps = get_model_capabilities(model)
        assert caps.supports_temperature is True
        assert generation_temperature(caps) == temperature
    for model in (ModelType.GPT_5_6, ModelType.GROK_4_6, ModelType.CLAUDE_SONNET_5):
        caps = get_model_capabilities(model)
        assert caps.supports_temperature is False
        assert generation_temperature(caps) == 0.0
    assert set(MODEL_CAPABILITIES) >= set(expected)


def test_gpt_4_official_limits_and_status() -> None:
    caps = get_model_capabilities(ModelType.GPT_4)
    assert caps.context_window == 8192
    assert caps.native_max_output_tokens == 8192
    assert caps.status == "deprecated"
    assert caps.recommended is False
    assert caps.retirement == "2026-10-23"
