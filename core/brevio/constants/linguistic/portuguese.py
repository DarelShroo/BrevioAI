"""Portuguese linguistic resources for AI pipeline cleaning, quality gates, and postprocessing."""

from __future__ import annotations

from core.brevio.constants.linguistic.base import LinguisticResource

PORTUGUESE_LINGUISTIC = LinguisticResource(
    language_code="pt",
    pdf_default_title="Resumo",
    help_phrases=(
        "do que você precisa?",
        "do que precisas?",
        "como posso ajudar",
        "estou aqui para ajudar",
        "opções para ajudar",
        "gostaria que eu continuasse?",
        "posso continuar se quiser",
        "aqui está o seu resumo",
        "vamos continuar",
    ),
    menu_headings=(
        "opções para ajudar",
        "menu de opções",
        "como posso ajudar hoje",
    ),
    greeting_prefixes=(
        "olá",
        "ola",
        "bom dia",
        "boa tarde",
    ),
    continuation_phrases=(
        "continuar...",
        "vamos continuar",
        "quer continuar?",
    ),
    intro_heading_regex=r"(?i)^#+\s*(?:1\.\s*)?introdu[çc][ãa]o",
    conclusion_heading_regex=r"(?i)^#+\s*(?:\d+\.\s*)?conclus[ãa]o",
    final_points_replacement="Pontos Finais",
    toc_markers=(
        "sumário",
        "sumario",
        "índice",
        "indice",
        "tabela de conteúdos",
    ),
    caption_markers=(
        "figura",
        "tabela",
        "foto",
        "imagem",
    ),
    truncated_markers=(
        "[texto truncado]",
        "[truncado]",
    ),
)
