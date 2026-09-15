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
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.protocols.language_prompt_protocol import LanguagePromptProtocol

PROMPT_LANGUAGES: Dict[str, LanguagePromptProtocol] = {
    LanguageType.ARABIC.name: ARABIC,
    LanguageType.ENGLISH.name: ENGLISH,
    LanguageType.CHINESE.name: CHINESE,
    LanguageType.CHINESE_SIMPLIFIED.name: CHINESE,
    LanguageType.CHINESE_TRADITIONAL.name: CHINESE,
    LanguageType.SPANISH.name: SPANISH,
    LanguageType.FRENCH.name: FRENCH,
    LanguageType.GERMAN.name: GERMAN,
    LanguageType.HINDI.name: HINDI,
    LanguageType.ITALIAN.name: ITALIAN,
    LanguageType.JAPANESE.name: JAPANESE,
    LanguageType.KOREAN.name: KOREAN,
    LanguageType.PORTUGUESE_PORTUGAL.name: PORTUGUESE,
    LanguageType.PORTUGUESE_BRAZIL.name: PORTUGUESE,
    LanguageType.RUSSIAN.name: RUSSIAN,
}


class UnsupportedPromptLanguageError(KeyError):
    """Raised when the selected language has no prompt implementation."""


def resolve_language_prompts(
    target_language: LanguageType | str,
) -> LanguagePromptProtocol:
    """Return the i18n prompt module for the *target* (output) language.

    This must never be called with the document/source language. Document
    content stays in its original language; only model instructions and the
    generated summary use ``target_language``.

    Never falls back to another language. Unsupported languages raise
    ``UnsupportedPromptLanguageError``.
    """
    resolved: LanguageType | None = None
    if isinstance(target_language, str):
        key = target_language.strip().upper()
        for lang in LanguageType:
            if lang.name == key or lang.value == target_language:
                resolved = lang
                break
        if resolved is None:
            raise UnsupportedPromptLanguageError(
                f"Unsupported language key: {target_language!r}"
            )
    else:
        resolved = target_language

    try:
        return PROMPT_LANGUAGES[resolved.name]
    except KeyError as exc:
        raise UnsupportedPromptLanguageError(
            f"No prompt implementation for language {resolved.name} ({resolved.value}). "
            "Configure a language prompt module instead of falling back to another language."
        ) from exc


class AdvancedPromptGenerator:
    templates: Dict[str, Any] = {}
    examples: Dict[str, Any] = {}

    @staticmethod
    def target_language_directive(language_prompts: LanguagePromptProtocol) -> str:
        """Instruction header that forces all model output into target_language.

        Text comes from the selected language module (not a fixed English/Spanish
        wrapper). Source/document language is independent and must not be used here.
        """
        return (
            f"{language_prompts.SPECIFIC_LANGUAGE_TITLE}\n"
            f"{language_prompts.SPECIFIC_LANGUAGE}"
        )

    def _with_target_language_directive(
        self, language_prompts: LanguagePromptProtocol, body: str
    ) -> str:
        directive = self.target_language_directive(language_prompts)
        body = (body or "").strip()
        if not body:
            return directive
        if directive in body:
            return body
        return f"{directive}\n\n{body}"

    def _normalize_category_style(self, language_prompts, category, style):
        if category is None or style is None:
            return None
        templates: Dict[str, Dict[str, Any]] = language_prompts.TEMPLATES
        category_key = (
            category.value if isinstance(category, CategoryType) else str(category)
        )
        spec = templates.get(category_key)
        if not spec:
            return None
        style_key = style.value if isinstance(style, StyleType) else str(style)
        style_info = (spec.get("styles") or {}).get(style_key)
        if not style_info:
            return None
        if not isinstance(category, CategoryType):
            try:
                category = CategoryType(category_key)
            except ValueError:
                return None
        if not isinstance(style, StyleType):
            try:
                style = StyleType[f"{category.name}_{style_key.upper()}"]
            except KeyError:
                return None
        return spec, style_info, category, style

    def _category_style_block(
        self, language_prompts, category, style, *, phase: str
    ) -> str:
        """Tone/structure/rules from TEMPLATES. Never copies EXAMPLES."""
        resolved = self._normalize_category_style(language_prompts, category, style)
        if not resolved:
            return ""
        spec, style_info, category, style = resolved
        lines = list(
            language_prompts.get_prompt_base(
                category, style, OutputFormatType.MARKDOWN, spec, style_info
            )
        )
        if phase == "reduce":
            structure = (spec.get("structures") or {}).get(style.value) or []
            if structure:
                lines.append("")
                lines.extend(str(item) for item in structure[:12])
            for rule in (spec.get("rules") or [])[:6]:
                lines.append(f"- {rule}")
        else:
            elements = style_info.get("elements") or []
            if elements:
                lines.append("- " + ", ".join(str(item) for item in elements))
            for rule in (spec.get("rules") or [])[:3]:
                lines.append(f"- {rule}")
        return "\n".join(line for line in lines if str(line).strip()).strip()

    async def generate_prompt(
        self,
        category: CategoryType,
        style: StyleType,
        output_format: OutputFormatType,
        lang: LanguageType,
        summary_level: SummaryLevel,
    ) -> str:
        # ``lang`` is the user-configured target/output language, never the
        # detected document language.
        language_prompts = resolve_language_prompts(lang)
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
        prompt.append("")
        prompt.append(language_prompts.get_available_styles_title())
        for st_name, st_props in spec.get("styles", {}).items():
            tone = st_props.get("tone", "")
            prompt.append(f"- {st_name}: {tone}")

        all_rules = list(spec.get("rules", []))

        mandatory_rules = language_prompts.get_mandatory_rules_prompt(self)

        for rule in mandatory_rules:
            if rule not in all_rules:
                all_rules.append(rule)

        prompt.extend([f"- {rule}" for rule in all_rules])

        if summary_level:
            semantic_profile = language_prompts.get_semantic_profile(summary_level)
            if semantic_profile:
                prompt.append("\n" + language_prompts.get_semantic_profile_title())
                prompt.append(semantic_profile)

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
    ) -> str:
        prompt_text = re.sub(r"\| \*\*([^*]+)\*\* \|", r"| **\1** |", prompt_text)
        prompt_text = re.sub(r"\*\*([^*]+)\*\*", r"**\1**", prompt_text)
        prompt_text = re.sub(r" \*\*([^*]+)\*\* ", r"**\1**", prompt_text)
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

    async def get_map_prompt(
        self,
        target_language: LanguageType,
        category: CategoryType = None,
        style: StyleType = None,
        summary_level: SummaryLevel = None,
    ) -> str:
        """MAP system instructions in ``target_language`` (not document language)."""
        language_prompts = resolve_language_prompts(target_language)
        prompt = await language_prompts.get_map_prompt(self, category, style)
        contract = self._category_style_block(
            language_prompts, category, style, phase="map"
        )
        if contract:
            prompt += f"\n\n{contract}"

        if summary_level:
            semantic_profile = language_prompts.get_semantic_profile(summary_level)
            length_instruction = language_prompts.get_length_instruction(summary_level)
            if semantic_profile:
                prompt += (
                    f"\n\n{language_prompts.get_semantic_profile_title()}\n"
                    f"{semantic_profile}"
                )
            if length_instruction:
                prompt += (
                    f"\n\n{language_prompts.get_length_instruction_title()}\n"
                    f"{length_instruction}"
                )
            prompt += f"\n\n{language_prompts.get_map_closing_instruction()}"

        return self._with_target_language_directive(language_prompts, prompt)

    async def get_reduce_prompt(
        self,
        target_language: LanguageType,
        category: CategoryType = None,
        style: StyleType = None,
        summary_level: SummaryLevel = None,
    ) -> str:
        """REDUCE system instructions in ``target_language`` (not document language)."""
        language_prompts = resolve_language_prompts(target_language)
        prompt = await language_prompts.get_reduce_prompt(self, category, style)
        contract = self._category_style_block(
            language_prompts, category, style, phase="reduce"
        )
        if contract:
            prompt += f"\n\n{contract}"

        if summary_level:
            semantic_profile = language_prompts.get_semantic_profile(summary_level)
            length_instruction = language_prompts.get_length_instruction(summary_level)
            if semantic_profile:
                prompt += (
                    f"\n\n{language_prompts.get_semantic_profile_title()}\n"
                    f"{semantic_profile}"
                )
            if length_instruction:
                prompt += (
                    f"\n\n{language_prompts.get_length_instruction_title()}\n"
                    f"{length_instruction}"
                )
            prompt += f"\n\n{language_prompts.get_coverage_guarantee()}"

        return self._with_target_language_directive(language_prompts, prompt)

    async def get_direct_summary_prompt(
        self,
        target_language: LanguageType,
        category: CategoryType = None,
        style: StyleType = None,
        summary_level: SummaryLevel = None,
    ) -> str:
        """Single-pass summary prompt in ``target_language`` (no MAP/REDUCE)."""
        language_prompts = resolve_language_prompts(target_language)
        base = await language_prompts.get_reduce_prompt(self, category, style)
        contract = self._category_style_block(
            language_prompts, category, style, phase="reduce"
        )
        prompt = language_prompts.get_direct_summary_intro() + base
        if contract:
            prompt += f"\n\n{contract}"
        if summary_level:
            semantic_profile = language_prompts.get_semantic_profile(summary_level)
            length_instruction = language_prompts.get_length_instruction(summary_level)
            if semantic_profile:
                prompt += (
                    f"\n\n{language_prompts.get_semantic_profile_title()}\n"
                    f"{semantic_profile}"
                )
            if length_instruction:
                prompt += (
                    f"\n\n{language_prompts.get_length_instruction_title()}\n"
                    f"{length_instruction}"
                )
            prompt += f"\n\n{language_prompts.get_coverage_guarantee()}"
        return self._with_target_language_directive(language_prompts, prompt)

    async def get_format_prompt(self, target_language: LanguageType) -> str:
        """Format-only instructions in ``target_language``. Do not re-summarize."""
        language_prompts = resolve_language_prompts(target_language)
        return self._with_target_language_directive(
            language_prompts, language_prompts.get_format_prompt()
        )
