import pytest
from backend.brevio.enums.source_type import SourceType
from backend.brevio.services.advanced_content_generator import AdvancedContentGenerator

@pytest.fixture
def generator():
    """Fixture para instanciar AdvancedContentGenerator."""
    return AdvancedContentGenerator()

@pytest.mark.asyncio
async def test_generate_prompt_valid_input(generator):
    """Prueba que generate_prompt funcione correctamente con entradas válidas."""
    category = "journalism"
    style = "news_wire"
    output_format = "markdown"
    lang = "en"
    source_type = SourceType.TEXT
    content_length = 5

    prompt = await generator.generate_prompt(
        category=category,
        style=style,
        output_format=output_format,
        lang=lang,
        source_type=source_type,
        content_length=content_length
    )

    assert isinstance(prompt, str)
    assert f"# Prompt for {category.title()} - {style.title()}" in prompt
    assert "**Style:** News_Wire (Direct, informative)" in prompt
    assert "- Summarize a 5-page document comprehensively" in prompt

@pytest.mark.asyncio
async def test_generate_prompt_invalid_category(generator):
    """Prueba que generate_prompt lance un error para una categoría inválida."""
    with pytest.raises(ValueError, match="Category 'invalid_category' not found"):
        await generator.generate_prompt(
            category="invalid_category",
            style="news_wire",
            output_format="markdown",
            lang="en",
            source_type=SourceType.TEXT
        )

@pytest.mark.asyncio
async def test_generate_prompt_empty_category(generator):
    """Prueba que generate_prompt lance un error para una categoría vacía."""
    with pytest.raises(ValueError, match="Category cannot be empty"):
        await generator.generate_prompt(
            category="",
            style="news_wire",
            output_format="markdown",
            lang="en",
            source_type=SourceType.TEXT
        )

@pytest.mark.asyncio
async def test_generate_prompt_invalid_style(generator):
    """Prueba que generate_prompt lance un error para un estilo inválido."""
    with pytest.raises(ValueError, match="Style 'invalid_style' not valid for 'Journalism'"):
        await generator.generate_prompt(
            category="journalism",
            style="invalid_style",
            output_format="markdown",
            lang="en",
            source_type=SourceType.TEXT
        )

@pytest.mark.asyncio
async def test_generate_prompt_empty_style(generator):
    """Prueba que generate_prompt lance un error para un estilo vacío."""
    with pytest.raises(ValueError, match="Style cannot be empty"):
        await generator.generate_prompt(
            category="journalism",
            style="",
            output_format="markdown",
            lang="en",
            source_type=SourceType.TEXT
        )

@pytest.mark.asyncio
async def test_generate_prompt_invalid_source_type(generator):
    """Prueba que generate_prompt lance un error para un tipo de fuente no soportado."""
    with pytest.raises(ValueError, match="Source type 'INVALID_SOURCE_TYPE' not supported"):
        await generator.generate_prompt(
            category="journalism",
            style="news_wire",
            output_format="markdown",
            lang="en",
            source_type="INVALID_SOURCE_TYPE"
        )

@pytest.mark.asyncio
async def test_generate_prompt_invalid_content_length(generator):
    """Prueba que generate_prompt maneje correctamente un content_length inválido."""
    with pytest.raises(ValueError, match="Content length must be a positive integer"):
        await generator.generate_prompt(
            category="journalism",
            style="news_wire",
            output_format="markdown",
            lang="en",
            source_type=SourceType.TEXT,
            content_length=-1
        )

def test_get_available_templates(generator):
    """Prueba que get_available_templates devuelva un resumen correcto de las plantillas disponibles."""
    templates_summary = generator.get_available_templates()
    assert isinstance(templates_summary, dict)
    assert "journalism" in templates_summary
    assert "health" in templates_summary
    assert len(templates_summary["journalism"]) > 0
    assert any(style["category"] == "news_wire" for style in templates_summary["journalism"])

def test_add_custom_template(generator):
    """Prueba que add_custom_template agregue una nueva plantilla correctamente."""
    category = "custom_category"
    structures = {
        "custom_structure": ["# Custom Structure"]
    }
    styles = {
        "custom_style": {"tone": "Neutral", "elements": [], "source_types": [SourceType.TEXT]}
    }
    rules = ["Custom rule"]
    examples = {
        "custom_style": "# Custom Example"
    }
    needs = "Custom needs"

    result = generator.add_custom_template(
        category=category,
        structures=structures,
        styles=styles,
        rules=rules,
        examples=examples,
        needs=needs
    )

    assert result == "Template 'custom_category' successfully created with 1 structures and 1 styles."
    assert category in generator.TEMPLATES
    assert "custom_structure" in generator.TEMPLATES[category]["structures"]
    assert "custom_style" in generator.TEMPLATES[category]["styles"]

def test_add_custom_template_empty_structures(generator):
    """Prueba que add_custom_template lance un error si structures está vacío."""
    with pytest.raises(ValueError, match="Structures cannot be empty"):
        generator.add_custom_template(
            category="empty_structures",
            structures={},
            styles={"some_style": {"tone": "Neutral", "elements": [], "source_types": [SourceType.TEXT]}},
            rules=["Some rule"],
            examples={"some_style": "# Example"},
            needs="Some needs"
        )

def test_add_custom_template_empty_styles(generator):
    """Prueba que add_custom_template lance un error si styles está vacío."""
    with pytest.raises(ValueError, match="Styles cannot be empty"):
        generator.add_custom_template(
            category="empty_styles",
            structures={"some_structure": ["# Structure"]},
            styles={},
            rules=["Some rule"],
            examples={},
            needs="Some needs"
        )

def test_add_custom_template_duplicate_category(generator):
    """Prueba que add_custom_template lance un error si se intenta agregar una categoría duplicada."""
    category = "journalism"
    structures = {
        "duplicate_structure": ["# Duplicate Structure"]
    }
    styles = {
        "duplicate_style": {"tone": "Neutral", "elements": [], "source_types": [SourceType.TEXT]}
    }

    with pytest.raises(ValueError, match=f"The category '{category}' already exists"):
        generator.add_custom_template(
            category=category,
            structures=structures,
            styles=styles
        )

def test_get_all_category_style_combinations(generator):
    """Prueba que get_all_category_style_combinations devuelva todas las combinaciones válidas."""
    combinations = generator.get_all_category_style_combinations()
    assert isinstance(combinations, list)
    assert len(combinations) > 0
    for category, style in combinations:
        assert category in generator.TEMPLATES
        assert style["category"] in generator.TEMPLATES[category]["styles"]
    assert ("journalism", "news_wire") in [(cat, sty["category"]) for cat, sty in combinations]

def test_sanitize_markdown(generator):
    """Prueba que sanitize_markdown limpie correctamente el texto Markdown."""
    raw_text = "Text with <script>alert('xss')</script> and *unclosed Markdown"
    sanitized_text = generator.sanitize_markdown(raw_text)
    expected_text = "Text with &lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt; and *unclosed Markdown"
    assert sanitized_text == expected_text