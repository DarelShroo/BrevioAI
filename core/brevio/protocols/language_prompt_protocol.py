# core/brevio/protocols/language_prompt.py

from typing import Any, Dict, List, Protocol

from core.brevio.enums.category import CategoryType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.style import StyleType


class LanguagePromptProtocol(Protocol):
    """
    Protocolo que define la interfaz común que deben cumplir todos los módulos
    de prompts por idioma (ENGLISH, ARABIC, etc.).

    Permite que AdvancedPromptGenerator interactúe con cualquier idioma
    sin depender de una clase base concreta, solo de la estructura esperada.
    """

    # --- Atributos requeridos ---

    TEMPLATES: Dict[str, Any]
    """
    Diccionario con plantillas por categoría. Cada categoría contiene estilos y reglas.
    Ejemplo:
    {
        "article": {
            "styles": {
                "executive": {
                    "source_types": [...],
                    ...
                }
            },
            "rules": [...]
        }
    }
    """

    EXAMPLES: Dict[str, Dict[str, str]]
    """
    Ejemplos predefinidos por categoría y estilo.
    Ejemplo:
    {
        "article": {
            "executive": "Este es un ejemplo en español..."
        }
    }
    """

    INSTRUCTIONS_TITLE: str
    """Título para la sección de instrucciones (ej: 'Instrucciones')."""

    SPECIFIC_LANGUAGE_TITLE: str
    """Título para indicar el idioma específico (ej: 'Idioma')."""

    SPECIFIC_LANGUAGE: str
    """Nombre del idioma en sí (ej: 'Español', 'English')."""

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

    def get_summary_level_prompt(self, generator: Any, word_limit: str) -> str:
        """
        Devuelve el texto del prompt que indica el límite de palabras según el nivel de resumen.
        """
        ...

    async def get_summary_chunk_prompt(
        self, generator: Any, previous_context: str
    ) -> str:
        """
        Genera un prompt para resumir un fragmento en contexto de resúmenes previos.
        """
        ...

    async def get_postprocess_prompt(self, generator: Any) -> str:
        """
        Genera un prompt para la etapa de postprocesamiento (pulir, formatear, etc.).
        """
        ...
