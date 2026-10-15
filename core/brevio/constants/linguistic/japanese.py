"""Japanese linguistic resources for AI pipeline cleaning, quality gates, and postprocessing."""

from __future__ import annotations

from core.brevio.constants.linguistic.base import LinguisticResource

JAPANESE_LINGUISTIC = LinguisticResource(
    language_code="ja",
    pdf_default_title="要約",
    help_phrases=(
        "何かお手伝いできますか？",
        "ご用件は何でしょうか？",
        "どのようなご用件でしょうか",
        "続けてよろしいですか？",
        "こちらが要約です",
        "続けましょう",
    ),
    menu_headings=(
        "サポートオプション",
        "オプションメニュー",
    ),
    greeting_prefixes=(
        "こんにちは",
        "おはようございます",
    ),
    continuation_phrases=(
        "続ける...",
        "続き",
        "継続しますか",
    ),
    intro_heading_regex=r"(?i)^#+\s*(?:1\.\s*)?はじめに|導入",
    conclusion_heading_regex=r"(?i)^#+\s*(?:\d+\.\s*)?結論|まとめ",
    final_points_replacement="最終まとめ",
    toc_markers=(
        "目次",
        "内容目次",
        "図表目次",
    ),
    caption_markers=(
        "図",
        "表",
        "写真",
    ),
    truncated_markers=(
        "[省略]",
        "[切り捨て]",
    ),
)
