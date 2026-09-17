"""Syntax highlighting for PDF/HTML export.

Token colors follow the frontend highlight.js theme in
``frontend/src/assets/styles/markdown-viewer.css`` so code blocks keep the
same visual language in print.
"""

from __future__ import annotations

from html import escape as html_escape

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.style import Style
from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
)
from pygments.util import ClassNotFound

LANGUAGE_ALIASES = {
    "js": "javascript",
    "jsx": "javascript",
    "mjs": "javascript",
    "cjs": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
    "py": "python",
    "sh": "bash",
    "shell": "bash",
    "zsh": "bash",
    "console": "bash",
    "yml": "yaml",
    "html": "html",
    "htm": "html",
    "svg": "xml",
    "rs": "rust",
    "golang": "go",
    "cplusplus": "cpp",
    "c++": "cpp",
    "md": "markdown",
}


class BrevioCodeStyle(Style):
    name = "brevio-pdf"
    background_color = "#0f172a"
    highlight_color = "#1e293b"
    styles = {
        Text: "#e2e8f0",
        Comment: "italic #94a3b8",
        Comment.Preproc: "#fbbf24",
        Keyword: "#fb7185",
        Keyword.Type: "#c4b5fd",
        Name: "#e2e8f0",
        Name.Attribute: "#86efac",
        Name.Builtin: "#67e8f9",
        Name.Builtin.Pseudo: "#67e8f9",
        Name.Class: "bold #c4b5fd",
        Name.Constant: "#7dd3fc",
        Name.Decorator: "#fbbf24",
        Name.Exception: "#fb7185",
        Name.Function: "#c4b5fd",
        Name.Namespace: "#c4b5fd",
        Name.Tag: "#86efac",
        Name.Variable: "#7dd3fc",
        Number: "#7dd3fc",
        Operator: "#e2e8f0",
        Operator.Word: "#fb7185",
        Punctuation: "#e2e8f0",
        String: "#a5b4fc",
        String.Doc: "italic #94a3b8",
        String.Escape: "#fdba74",
        String.Regex: "#a5b4fc",
        String.Symbol: "#fdba74",
        Generic.Deleted: "#fb7185",
        Generic.Inserted: "#86efac",
        Generic.Heading: "bold #c4b5fd",
        Generic.Subheading: "#c4b5fd",
        Generic.Error: "#fb7185",
        Error: "#fb7185",
    }


_FORMATTER = HtmlFormatter(
    style=BrevioCodeStyle,
    nowrap=True,
    noclasses=False,
    nobackground=True,
    classprefix="mdh-",
)


def pygments_css() -> str:
    return HtmlFormatter(
        style=BrevioCodeStyle,
        classprefix="mdh-",
        nobackground=True,
    ).get_style_defs(".md-code")


def normalize_language(lang: str | None) -> str:
    if not lang:
        return ""
    key = lang.strip().lower()
    return LANGUAGE_ALIASES.get(key, key)


def escape_html(value: str) -> str:
    return html_escape(value, quote=True)


def highlight_code(code: str, lang_hint: str = "") -> tuple[str, str]:
    """Return (highlighted_html, language). Never raises."""
    language = normalize_language(lang_hint)
    lexer = None
    if language:
        try:
            lexer = get_lexer_by_name(language, stripall=False)
        except ClassNotFound:
            lexer = None
    if lexer is None:
        try:
            lexer = guess_lexer(code)
            language = language or (lexer.aliases[0] if lexer.aliases else "")
        except ClassNotFound:
            return escape_html(code), language
    try:
        return highlight(code, lexer, _FORMATTER), language
    except Exception:
        return escape_html(code), language


def render_fenced_block(code: str, lang_hint: str = "") -> str:
    highlighted, language = highlight_code(code, lang_hint)
    label = language or lang_hint.strip().lower()
    lang_attr = f' data-lang="{escape_html(label)}"' if label else ""
    lang_badge = (
        f'<span class="md-code__lang">{escape_html(label)}</span>'
        if label
        else '<span class="md-code__lang" aria-hidden="true"></span>'
    )
    code_class = f' class="language-{escape_html(label)}"' if label else ""
    return (
        f'<div class="md-code"{lang_attr}>'
        f'<div class="md-code__toolbar">{lang_badge}</div>'
        f'<pre class="md-code__pre"><code{code_class}>{highlighted}</code></pre>'
        "</div>\n"
    )
