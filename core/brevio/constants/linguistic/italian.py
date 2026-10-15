"""Italian linguistic resources for AI pipeline cleaning, quality gates, and postprocessing."""

from __future__ import annotations

from core.brevio.constants.linguistic.base import LinguisticResource

ITALIAN_LINGUISTIC = LinguisticResource(
    language_code="it",
    pdf_default_title="Riassunto",
    help_phrases=(
        "di cosa hai bisogno?",
        "come posso aiutarti",
        "come posso aiutarvi",
        "sono qui per aiutarti",
        "opzioni per aiutarti",
        "desideri che continui?",
        "posso continuare se vuoi",
        "ecco il tuo riassunto",
        "continuiamo",
    ),
    menu_headings=(
        "opzioni di aiuto",
        "menu di opzioni",
        "come posso aiutarti oggi",
    ),
    greeting_prefixes=(
        "ciao",
        "buongiorno",
        "buonasera",
    ),
    continuation_phrases=(
        "continua...",
        "continuiamo",
        "vuoi continuare?",
    ),
    intro_heading_regex=r"(?i)^#+\s*(?:1\.\s*)?introduzione",
    conclusion_heading_regex=r"(?i)^#+\s*(?:\d+\.\s*)?conclusione",
    final_points_replacement="Punti Finali",
    toc_markers=(
        "sommario",
        "indice",
        "tavola dei contenuti",
    ),
    caption_markers=(
        "figura",
        "tabella",
        "foto",
        "immagine",
    ),
    truncated_markers=(
        "[testo troncato]",
        "[troncato]",
    ),
)
