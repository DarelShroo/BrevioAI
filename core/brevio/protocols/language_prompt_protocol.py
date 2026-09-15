# core/brevio/protocols/language_prompt.py

from typing import Any, Dict, List, Protocol, Sequence

from core.brevio.enums.category import CategoryType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel


class LanguagePromptProtocol(Protocol):
    """
    Protocolo que define la interfaz común que deben cumplir todos los módulos
    de prompts por idioma (ENGLISH, ARABIC, etc.).

    Permite que AdvancedPromptGenerator interactúe con cualquier idioma
    sin depender de una clase base concreta, solo de la estructura esperada.

    Single source of truth for ALL model-bound prompts/instructions.

    Selection key is always ``target_language`` (output / instruction language).
    Never select a module from the document/source language.
    """

    # --- Atributos requeridos ---

    TEMPLATES: Dict[str, Any]
    """
    Diccionario con plantillas por categoría. Cada categoría contiene estilos y reglas.
    """

    EXAMPLES: Dict[str, Dict[str, str]]
    """
    Ejemplos predefinidos por categoría y estilo.
    """

    INSTRUCTIONS_TITLE: str
    """Título para la sección de instrucciones (ej: 'Instrucciones')."""

    SPECIFIC_LANGUAGE_TITLE: str
    """Título para indicar el idioma objetivo de salida (ej: 'Idioma')."""

    SPECIFIC_LANGUAGE: str
    """Directiva de idioma objetivo (ej: 'Español', 'English'). Never document language."""

    EXAMPLE_TITLE: str
    """Título para la sección de ejemplo (ej: 'Ejemplo', 'Example')."""

    # --- Métodos requeridos ---

    def get_prompt_base(
        self,
        category: CategoryType,
        style: StyleType,
        output_format: OutputFormatType,
        spec: Dict[str, Any],
        style_info: Dict[str, Any],
    ) -> List[str]:
        """
        Devuelve las líneas base del prompt para la combinación categoría+estilo.
        """
        ...

    def get_mandatory_rules_prompt(self, generator: Any) -> List[str]:
        """
        Devuelve una lista de reglas obligatorias que deben aplicarse siempre,
        independientemente de la categoría o estilo.
        """
        ...

    async def get_map_prompt(
        self, generator: Any, category: Any = None, style: Any = None
    ) -> str:
        """
        Genera un prompt para resumir un fragmento en contexto de resúmenes previos.
        """
        ...

    async def get_reduce_prompt(
        self, generator: Any, category: Any = None, style: Any = None
    ) -> str:
        """
        Genera un prompt para la etapa de postprocesamiento (pulir, formatear, etc.).
        """
        ...

    def get_available_styles_title(self) -> str:
        """Section title for available styles in generate_prompt."""
        ...

    def get_semantic_profile_title(self) -> str:
        """Section title when injecting a semantic profile into a prompt."""
        ...

    def get_length_instruction_title(self) -> str:
        """Section title when injecting a length/density instruction."""
        ...

    def get_semantic_profile(self, summary_level: SummaryLevel) -> str:
        """Semantic preservation profile for a summary level."""
        ...

    def get_length_instruction(self, summary_level: SummaryLevel) -> str:
        """Length/density instruction for a summary level."""
        ...

    def get_coverage_guarantee(self) -> str:
        """Coverage guarantee appended to MAP/REDUCE/DIRECT prompts."""
        ...

    def get_coverage_checklist(self, outline: Sequence[str]) -> str:
        """Outline-based coverage checklist for the model."""
        ...

    def get_toc_map_stub(self, entry_labels: Sequence[str]) -> str:
        """Compact MAP output when the source chunk is only a table of contents."""
        ...

    def get_map_closing_instruction(self) -> str:
        """MAP closing instruction (do not pad token budget)."""
        ...

    def get_direct_summary_intro(self) -> str:
        """Intro for single-pass DIRECT summary prompts."""
        ...

    def get_format_prompt(self) -> str:
        """FORMAT phase system instructions."""
        ...

    def get_format_strict_rules(self) -> str:
        """Strict formatting rules appended to the FORMAT system prompt."""
        ...

    def get_format_user_content(self, text_block: str) -> str:
        """FORMAT phase user message wrapping the text to format."""
        ...

    def get_format_position_hint(self, index: int, total_blocks: int) -> str:
        """Positional hint when formatting a multi-block document."""
        ...

    def get_reduce_user_content(self, batch_text: str) -> str:
        """REDUCE phase user message wrapping batch text."""
        ...

    def format_reduce_block_header(self, block_index: int, chunk_ids_str: str) -> str:
        """Header label for a REDUCE input block."""
        ...

    def get_intermediate_reduce_instruction(
        self, batch_input_tokens: int, remaining_ratio: float
    ) -> str:
        """CRITICAL instruction prepended for intermediate REDUCE."""
        ...

    def get_final_reduce_instruction(self, target_max_tokens: int) -> str:
        """CRITICAL instruction prepended for final REDUCE."""
        ...

    def get_reduce_quality_retry_instruction(self) -> str:
        """Instruction prepended when REDUCE final output fails the quality gate."""
        ...
