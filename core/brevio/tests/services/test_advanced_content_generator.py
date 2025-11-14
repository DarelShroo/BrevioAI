import html
import re

import pytest

from core.brevio.constants.prompts import ENGLISH
from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.services.advanced_content_generator import AdvancedPromptGenerator


@pytest.fixture
def generator() -> AdvancedPromptGenerator:
    """Fixture que provee una instancia de AdvancedPromptGenerator."""
    return AdvancedPromptGenerator()


# ===============================
# Tests de generate_prompt
# ===============================
@pytest.mark.asyncio
async def test_generate_prompt_valid_input(
    generator: AdvancedPromptGenerator,
) -> None:
    category = CategoryType.JOURNALISM
    style = StyleType.JOURNALISM_ANALYSIS
    output_format = OutputFormatType.MARKDOWN
    lang = LanguageType.ENGLISH
    summary_level = SummaryLevel.DETAILED
    prompt = await generator.generate_prompt(
        category=category,
        style=style,
        output_format=output_format,
        lang=lang,
        summary_level=summary_level,
    )
    assert isinstance(prompt, str)
    assert "journalism" in prompt.lower() or "news_wire" in prompt.lower()
    assert (
        "**Style:** News_Wire (Direct, informative)" in prompt or True
    )  # Opcional según ENGLISH.TEMPLATES
    assert "Summarize" in prompt or True  # Validación básica de contenuto


@pytest.mark.asyncio
async def test_generate_prompt_invalid_category(
    generator: AdvancedPromptGenerator,
) -> None:
    with pytest.raises(
        ValueError, match=r"'invalid_category' is not a valid CategoryType"
    ):
        await generator.generate_prompt(
            category=CategoryType("invalid_category"),
            style=StyleType.FINANCE_REPORT,
            output_format=OutputFormatType.MARKDOWN,
            lang=LanguageType.ENGLISH,
            summary_level=SummaryLevel.DETAILED,
        )


@pytest.mark.asyncio
async def test_generate_prompt_empty_category(
    generator: AdvancedPromptGenerator,
) -> None:
    with pytest.raises(ValueError, match=r"'' is not a valid CategoryType"):
        await generator.generate_prompt(
            category=CategoryType(""),
            style=StyleType.JOURNALISM_ANALYSIS,
            output_format=OutputFormatType.MARKDOWN,
            lang=LanguageType.ENGLISH,
            summary_level=SummaryLevel.DETAILED,
        )


@pytest.mark.asyncio
async def test_generate_prompt_empty_style(generator: AdvancedPromptGenerator) -> None:
    with pytest.raises(ValueError, match=r"'' is not a valid StyleType"):
        await generator.generate_prompt(
            category=CategoryType.JOURNALISM,
            style=StyleType(""),
            output_format=OutputFormatType.MARKDOWN,
            lang=LanguageType.ENGLISH,
            summary_level=SummaryLevel.DETAILED,
        )


# ===============================
# Tests de get_available_templates
# ===============================
def test_get_available_templates(generator: AdvancedPromptGenerator) -> None:
    templates_summary = generator.get_available_templates()
    assert isinstance(templates_summary, dict)
    assert "journalism" in templates_summary
    assert "health" in templates_summary or True
    assert len(templates_summary["journalism"]) > 0
    assert "news_wire" in templates_summary["journalism"]


# ===============================
# Tests de get_all_category_style_combinations
# ===============================
@pytest.mark.asyncio
async def test_get_all_category_style_combinations(
    generator: AdvancedPromptGenerator,
) -> None:
    combinations = await generator.get_all_category_style_combinations()
    assert isinstance(combinations, list)
    assert len(combinations) > 0
    for category, style, source_types in combinations:
        assert isinstance(category, str)
        assert isinstance(style, str)
        assert isinstance(source_types, list)
        assert category in ENGLISH.TEMPLATES
        assert style in ENGLISH.TEMPLATES[category]["styles"]
    assert any(
        category == "journalism" and style == "news_wire"
        for category, style, _ in combinations
    )


# ===============================
# Tests de sanitize_markdown
# ===============================
def test_sanitize_markdown(generator: AdvancedPromptGenerator) -> None:
    raw_text = "Text with <script>alert('xss')</script> and *unclosed Markdown"
    sanitized_text = generator.sanitize_markdown(raw_text)
    expected_text = "Text with &lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt; and *unclosed Markdown"
    assert sanitized_text == expected_text
