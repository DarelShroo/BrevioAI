"""French linguistic resources for AI pipeline cleaning, quality gates, and postprocessing."""

from __future__ import annotations

from core.brevio.constants.linguistic.base import LinguisticResource

FRENCH_LINGUISTIC = LinguisticResource(
    language_code="fr",
    pdf_default_title="Résumé",
    help_phrases=(
        "de quoi avez-vous besoin ?",
        "de quoi as-tu besoin ?",
        "comment puis-je vous aider",
        "comment puis-je t'aider",
        "je suis là pour vous aider",
        "options pour vous aider",
        "dites-moi ce dont vous avez besoin",
        "merci d'avoir partagé",
        "souhaitez-vous que je continue ?",
        "puis-je continuer ?",
        "voici votre résumé",
        "continuons",
    ),
    menu_headings=(
        "options pour vous aider",
        "menu d'options",
        "comment puis-je vous aider aujourd'hui",
    ),
    greeting_prefixes=(
        "bonjour",
        "bonsoir",
        "salut",
    ),
    continuation_phrases=(
        "continuer...",
        "continuons",
        "souhaitez-vous continuer ?",
    ),
    intro_heading_regex=r"(?i)^#+\s*(?:1\.\s*)?introduction",
    conclusion_heading_regex=r"(?i)^#+\s*(?:\d+\.\s*)?conclusion",
    final_points_replacement="Points Finaux",
    toc_markers=(
        "table des matières",
        "sommaire",
        "table des illustrations",
        "index général",
    ),
    caption_markers=(
        "figure",
        "tableau",
        "photo",
        "image",
        "illustration",
    ),
    truncated_markers=(
        "[texte tronqué]",
        "[tronqué]",
        "...[coupé]",
    ),
)
