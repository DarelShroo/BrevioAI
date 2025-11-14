import html
import re
from typing import Any, Dict

from core.brevio.constants.prompts import (
    ARABIC,
    CHINESE,
    ENGLISH,
    FRENCH,
    GERMAN,
    HINDI,
    ITALIAN,
    JAPANESE,
    KOREAN,
    PORTUGUESE,
    RUSSIAN,
    SPANISH,
)
from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import WORD_LIMITS_BY_SUMMARY_LEVEL, SummaryLevel
from core.brevio.protocols.language_prompt_protocol import LanguagePromptProtocol

PROMPT_LANGUAGES: Dict[str, LanguagePromptProtocol] = {
    LanguageType.ARABIC.name: ARABIC,
    LanguageType.ENGLISH.name: ENGLISH,
    LanguageType.CHINESE.name: CHINESE,
    LanguageType.SPANISH.name: SPANISH,
    LanguageType.FRENCH.name: FRENCH,
    LanguageType.GERMAN.name: GERMAN,
    LanguageType.HINDI.name: HINDI,
    LanguageType.ITALIAN.name: ITALIAN,
    LanguageType.JAPANESE.name: JAPANESE,
    LanguageType.KOREAN.name: KOREAN,
    LanguageType.PORTUGUESE_PORTUGAL.name: PORTUGUESE,
    LanguageType.RUSSIAN.name: RUSSIAN,
}


class AdvancedPromptGenerator:
    templates: Dict[str, Any] = {}
    examples: Dict[str, Any] = {}

    async def generate_prompt(
        self,
        category: CategoryType,
        style: StyleType,
        output_format: OutputFormatType,
        lang: LanguageType,
        summary_level: SummaryLevel,
    ) -> str:
        language_prompts = PROMPT_LANGUAGES[lang.name]
        templates: Dict[str, Dict[str, Any]] = language_prompts.TEMPLATES
        examples = language_prompts.EXAMPLES

        # Validate and normalize category
        if category is None or (isinstance(category, str) and category.strip() == ""):
            raise ValueError("Category cannot be empty")
        if isinstance(category, CategoryType):
            category_key = category.value
        else:
            category_key = category
        if category_key not in templates:
            raise ValueError(f"Category '{category_key}' not found")
        if not isinstance(category, CategoryType):
            try:
                category = CategoryType[category_key.upper()]
            except KeyError:
                pass

        # Validate and normalize style
        if style is None or (isinstance(style, str) and style.strip() == ""):
            raise ValueError("Style cannot be empty")
        spec: dict = templates[category_key]
        if isinstance(style, StyleType):
            style_key = style.value
        else:
            style_key = style
        if style_key not in spec.get("styles", {}):
            raise ValueError(
                f"Style '{style_key}' not valid for category '{category_key}'"
            )
        if not isinstance(style, StyleType):
            try:
                enum_name = f"{category.name}_{style_key.upper()}"
                style = StyleType[enum_name]
            except KeyError:
                pass
        style_info = spec["styles"][style_key]
        prompt: list[str] = []
        prompt.append(language_prompts.INSTRUCTIONS_TITLE)

        prompt.append(
            f"# {language_prompts.SPECIFIC_LANGUAGE_TITLE} - {language_prompts.SPECIFIC_LANGUAGE}"
        )
        base_prompt: list[str] = language_prompts.get_prompt_base(
            category, style, output_format, spec, style_info
        )
        prompt.extend(base_prompt)
        # Include overview of available styles and their tones
        prompt.append("")
        prompt.append("**Available Styles and Tones:**")
        for st_name, st_props in spec.get("styles", {}).items():
            tone = st_props.get("tone", "")
            prompt.append(f"- {st_name}: {tone}")

        all_rules = spec.get("rules", [])

        mandatory_rules = language_prompts.get_mandatory_rules_prompt(self)

        for rule in mandatory_rules:
            if rule not in all_rules:
                all_rules.append(rule)

        prompt.extend([f"- {rule}" for rule in all_rules])

        if summary_level:
            word_limit = WORD_LIMITS_BY_SUMMARY_LEVEL[summary_level]
            prompt.append(language_prompts.get_summary_level_prompt(self, word_limit))

        prompt.append("**Example**:")
        prompt.append(examples[category.value][style.value])

        # Manejo de fuentes
        """prompt.append("\n**Source Handling**:")

        source_rules = {
            "video": "- Use timestamps [MM:SS] for key events",
            "audio": "- Include relevant quotes with timestamps if applicable",
            "text": "- Summarize main ideas with references if applicable",
            None: "- Adapt to the original content",
        }"""

        # Añadir ejemplo si existe
        if category.value in examples and style.value in examples[category.value]:
            prompt.append("\n" + language_prompts.EXAMPLE_TITLE)
            example = examples[category.value][style.value]
            if output_format == "markdown":
                prompt.append(f"```markdown\n{example}\n```")
            else:
                prompt.append(example.replace("#", "").replace("*", "").strip())

        prompt_text = "\n".join(prompt)

        return prompt_text

    def sanitize_markdown(
        self,
        prompt_text: str,
        # Remove extra spaces before and after the double asterisks in headers (e.g., | **Indicator** |)
    ) -> str:
        # Remove extra spaces before and after the double asterisks in headers (e.g., | **Indicator** |)
        prompt_text = re.sub(r"\| \*\*([^*]+)\*\* \|", r"| **\1** |", prompt_text)

        # Remove extra spaces after asterisks in other areas (like **text**)
        prompt_text = re.sub(r"\*\*([^*]+)\*\*", r"**\1**", prompt_text)

        # Ensure no spaces before and after double asterisks in any other places
        prompt_text = re.sub(r" \*\*([^*]+)\*\* ", r"**\1**", prompt_text)

        # Escapar caracteres HTML para prevenir XSS
        return html.escape(prompt_text)

    def get_available_templates(self) -> dict:
        summary: Dict[str, Any] = {}
        TEMPLATES = PROMPT_LANGUAGES[LanguageType.ENGLISH.name].TEMPLATES
        for category_key, data in TEMPLATES.items():
            summary[category_key] = {}
            for style_name, style_data in data.get("styles", {}).items():
                summary[category_key][style_name] = {
                    "tone": style_data.get("tone"),
                    "source_types": style_data.get("source_types", []),
                }
        return summary

    async def get_all_category_style_combinations(self) -> list:
        combinations = []
        TEMPLATES = PROMPT_LANGUAGES[LanguageType.ENGLISH.name].TEMPLATES
        for category_key, template_data in TEMPLATES.items():
            for style_name, style_data in template_data.get("styles", {}).items():
                source_types = style_data.get("source_types", [])
                combinations.append((category_key, style_name, source_types))
        return combinations

    async def get_summary_chunk_prompt(
        self,
        previous_context: str,
        language: LanguageType,
    ) -> str:
        return await PROMPT_LANGUAGES[language.name].get_summary_chunk_prompt(
            self, previous_context
        )

    async def get_postprocess_prompt(self, language: LanguageType) -> str:
        return await PROMPT_LANGUAGES[language.name].get_postprocess_prompt(self)
