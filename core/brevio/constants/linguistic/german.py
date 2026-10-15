"""German linguistic resources for AI pipeline cleaning, quality gates, and postprocessing."""

from __future__ import annotations

from core.brevio.constants.linguistic.base import LinguisticResource

GERMAN_LINGUISTIC = LinguisticResource(
    language_code="de",
    pdf_default_title="Zusammenfassung",
    help_phrases=(
        "was brauchst du?",
        "was benötigen sie?",
        "wie kann ich helfen",
        "wie kann ich ihnen helfen",
        "ich bin hier um zu helfen",
        "optionen um ihnen zu helfen",
        "möchten sie dass ich fortfahre?",
        "kann ich fortfahren?",
        "hier ist ihre zusammenfassung",
        "lassen sie uns fortfahren",
    ),
    menu_headings=(
        "optionen zur hilfe",
        "auswahlmenü",
        "wie kann ich ihnen heute helfen",
    ),
    greeting_prefixes=(
        "hallo",
        "guten tag",
        "guten morgen",
    ),
    continuation_phrases=(
        "fortsetzen...",
        "weitergehen",
        "möchten sie fortfahren?",
    ),
    intro_heading_regex=r"(?i)^#+\s*(?:1\.\s*)?einleitung",
    conclusion_heading_regex=r"(?i)^#+\s*(?:\d+\.\s*)?fazit|schlussfolgerung",
    final_points_replacement="Abschließende Punkte",
    toc_markers=(
        "inhaltsverzeichnis",
        "inhaltsübersicht",
        "abbildungsverzeichnis",
        "tabellenverzeichnis",
    ),
    caption_markers=(
        "abbildung",
        "tabelle",
        "foto",
        "bild",
    ),
    truncated_markers=(
        "[text abgeschnitten]",
        "[gekürzt]",
        "...[abgeschnitten]",
    ),
)
