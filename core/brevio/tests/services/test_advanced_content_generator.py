import pytest

from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.services.advanced_content_generator import AdvancedPromptGenerator


@pytest.fixture
def generator() -> AdvancedPromptGenerator:
    """Fixture that provides an AdvancedPromptGenerator instance."""
    return AdvancedPromptGenerator()


@pytest.mark.asyncio
async def test_generate_prompt_valid_input(generator: AdvancedPromptGenerator) -> None:
    """Should generate a prompt successfully with valid inputs."""
    category = "journalism"
    style = "news_wire"
    output_format = OutputFormatType.MARKDOWN
    lang = LanguageType.ENGLISH
    source_type = SourceType.TEXT
    summary_level = SummaryLevel.DETAILED  # Use DETAILED for a longer summary

    prompt = await generator.generate_prompt(
        category=category,
        style=style,
        output_format=output_format,
        lang=lang,
        source_type=source_type,
        summary_level=summary_level,
    )

    assert isinstance(prompt, str)
    assert f"# Prompt for {category.title()} - {style.title()}" in prompt
    assert "**Style:** News_Wire (Direct, informative)" in prompt
    assert (
        "- Summarize the document comprehensively, capturing main themes, key points, and overall purpose in approximately 400 words."
        in prompt
    )


@pytest.mark.asyncio
async def test_generate_prompt_invalid_category(
    generator: AdvancedPromptGenerator,
) -> None:
    """Should raise an error when an invalid category is provided."""
    with pytest.raises(ValueError, match="Category 'invalid_category' not found"):
        await generator.generate_prompt(
            category="invalid_category",
            style="news_wire",
            output_format=OutputFormatType.MARKDOWN,
            lang=LanguageType.ENGLISH,
        )


@pytest.mark.asyncio
async def test_generate_prompt_empty_category(
    generator: AdvancedPromptGenerator,
) -> None:
    """Should raise an error when an empty category is provided."""
    with pytest.raises(ValueError, match="Category cannot be empty"):
        await generator.generate_prompt(
            category="",
            style="news_wire",
            output_format=OutputFormatType.MARKDOWN,
            lang=LanguageType.ENGLISH,
            source_type=SourceType.TEXT,
        )


@pytest.mark.asyncio
async def test_generate_prompt_invalid_style(
    generator: AdvancedPromptGenerator,
) -> None:
    """Should raise an error when an invalid style is provided for the given category."""
    with pytest.raises(
        ValueError, match="Style 'invalid_style' not valid for 'Journalism'"
    ):
        await generator.generate_prompt(
            category="journalism",
            style="invalid_style",
            output_format=OutputFormatType.MARKDOWN,
            lang=LanguageType.ENGLISH,
            source_type=SourceType.TEXT,
        )


@pytest.mark.asyncio
async def test_generate_prompt_empty_style(generator: AdvancedPromptGenerator) -> None:
    """Should raise an error when an empty style is provided."""
    with pytest.raises(ValueError, match="Style cannot be empty"):
        await generator.generate_prompt(
            category="journalism",
            style="",
            output_format=OutputFormatType.MARKDOWN,
            lang=LanguageType.ENGLISH,
            source_type=SourceType.TEXT,
        )


@pytest.mark.asyncio
async def test_generate_prompt_invalid_source_type(
    generator: AdvancedPromptGenerator,
) -> None:
    """Should raise an error when an unsupported source type is provided."""
    with pytest.raises(ValueError) as exc_info:
        await generator.generate_prompt(
            category="journalism",
            style="news_wire",
            output_format=OutputFormatType.MARKDOWN,
            lang=LanguageType.ENGLISH,
            source_type=SourceType.MEDIA,
        )
    error_message = str(exc_info.value)
    assert f"Source type '{SourceType.MEDIA}'" in error_message
    assert "not supported" in error_message
    assert "news_wire" in error_message
    assert "journalism" in error_message


def test_get_available_templates(generator: AdvancedPromptGenerator) -> None:
    """Should return a correct summary of the available templates."""
    templates_summary = generator.get_available_templates()
    assert isinstance(templates_summary, dict)
    assert "journalism" in templates_summary
    assert "health" in templates_summary
    assert len(templates_summary["journalism"]) > 0
    assert any(
        style["category"] == "news_wire" for style in templates_summary["journalism"]
    )


def test_add_custom_template(generator: AdvancedPromptGenerator) -> None:
    """Should add a new custom template correctly."""
    category = "custom_category"
    structures = {"custom_structure": ["# Custom Structure"]}
    styles = {
        "custom_style": {
            "tone": "Neutral",
            "elements": [],
            "source_types": [SourceType.TEXT],
        }
    }
    rules = ["Custom rule"]
    examples = {"custom_style": "# Custom Example"}
    needs = "Custom needs"

    result = generator.add_custom_template(
        category=category,
        structures=structures,
        styles=styles,
        rules=rules,
        examples=examples,
        needs=needs,
    )

    assert (
        result
        == "Template 'custom_category' successfully created with 1 structures and 1 styles."
    )
    assert category in generator.TEMPLATES
    assert "custom_structure" in generator.TEMPLATES[category]["structures"]
    assert "custom_style" in generator.TEMPLATES[category]["styles"]


def test_add_custom_template_empty_structures(
    generator: AdvancedPromptGenerator,
) -> None:
    """Should raise an error if the provided structures are empty."""
    with pytest.raises(ValueError, match="Structures cannot be empty"):
        generator.add_custom_template(
            category="empty_structures",
            structures={},
            styles={
                "some_style": {
                    "tone": "Neutral",
                    "elements": [],
                    "source_types": [SourceType.TEXT],
                }
            },
            rules=["Some rule"],
            examples={"some_style": "# Example"},
            needs="Some needs",
        )


def test_add_custom_template_empty_styles(generator: AdvancedPromptGenerator) -> None:
    """Should raise an error if the provided styles are empty."""
    with pytest.raises(ValueError, match="Styles cannot be empty"):
        generator.add_custom_template(
            category="empty_styles",
            structures={"some_structure": ["# Structure"]},
            styles={},
            rules=["Some rule"],
            examples={},
            needs="Some needs",
        )


def test_add_custom_template_duplicate_category(
    generator: AdvancedPromptGenerator,
) -> None:
    """Should raise an error when attempting to add a template with an existing category."""
    category = "journalism"
    structures = {"duplicate_structure": ["# Duplicate Structure"]}
    styles = {
        "duplicate_style": {
            "tone": "Neutral",
            "elements": [],
            "source_types": [SourceType.TEXT],
        }
    }

    with pytest.raises(ValueError, match=f"The category '{category}' already exists"):
        generator.add_custom_template(
            category=category, structures=structures, styles=styles
        )


def test_get_all_category_style_combinations(
    generator: AdvancedPromptGenerator,
) -> None:
    """Should return all valid combinations of categories and styles."""
    combinations = generator.get_all_category_style_combinations()
    assert isinstance(combinations, list)
    assert len(combinations) > 0
    for category, style, source_types in combinations:
        assert isinstance(category, str)
        assert isinstance(style, str)
        assert isinstance(source_types, list)
        assert category in generator.TEMPLATES
        assert style in generator.TEMPLATES[category]["styles"]
    assert any(
        category == "journalism" and style == "news_wire"
        for category, style, _ in combinations
    )


def test_sanitize_markdown(generator: AdvancedPromptGenerator) -> None:
    """Should sanitize the Markdown text by escaping potentially harmful tags."""
    raw_text = "Text with <script>alert('xss')</script> and *unclosed Markdown"
    sanitized_text = generator.sanitize_markdown(raw_text)
    expected_text = "Text with &lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt; and *unclosed Markdown"
    assert sanitized_text == expected_text
