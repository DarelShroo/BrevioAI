from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.models.prompt_config_model import PromptConfig
from core.shared.enums.model import ModelType


def _base(**extra):
    payload = dict(
        model=ModelType.GPT_4O_MINI,
        category="education",
        style="quick_ref",
        format=OutputFormatType.MARKDOWN,
        language=LanguageType.SPANISH,
        summary_level=SummaryLevel.CONCISE,
    )
    payload.update(extra)
    return payload


def test_prompt_config_ignores_user_max_output_tokens() -> None:
    config = PromptConfig(**_base(max_output_tokens=999_999_999))
    assert config.max_output_tokens is None


def test_prompt_config_ignores_user_sampling() -> None:
    config = PromptConfig(**_base(max_output_tokens=16384, temperature=0.2))
    assert config.max_output_tokens is None
    assert config.temperature is None


def test_prompt_config_ignores_temperature_on_gpt_5_6() -> None:
    config = PromptConfig(**_base(model=ModelType.GPT_5_6, temperature=0.4))
    assert config.temperature is None
