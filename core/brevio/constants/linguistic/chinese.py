"""Chinese linguistic resources for AI pipeline cleaning, quality gates, and postprocessing."""

from __future__ import annotations

from core.brevio.constants.linguistic.base import LinguisticResource

CHINESE_LINGUISTIC = LinguisticResource(
    language_code="zh",
    pdf_default_title="摘要",
    help_phrases=(
        "你需要什么？",
        "我能帮您什么",
        "我能帮你什么",
        "我在这里为您提供帮助",
        "需要我继续吗？",
        "这是您的总结",
        "让我们继续",
    ),
    menu_headings=(
        "帮助选项",
        "选项菜单",
        "今天我能如何帮助您",
    ),
    greeting_prefixes=(
        "你好",
        "您好",
    ),
    continuation_phrases=(
        "继续...",
        "继续",
        "是否继续",
    ),
    intro_heading_regex=r"(?i)^#+\s*(?:1\.\s*)?引言|介绍|前言",
    conclusion_heading_regex=r"(?i)^#+\s*(?:\d+\.\s*)?结论|总结",
    final_points_replacement="要点总结",
    toc_markers=(
        "目录",
        "内容列表",
        "图表目录",
    ),
    caption_markers=(
        "图",
        "表",
        "图片",
        "插图",
    ),
    truncated_markers=(
        "[文本被截断]",
        "[截断]",
    ),
)
