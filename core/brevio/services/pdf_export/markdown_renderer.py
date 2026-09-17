"""Markdown → semantic HTML for PDF export.

Uses markdown-it-py, the Python port of the frontend's markdown-it parser, so
headings, emphasis, lists, fences, tables and quotes stay real HTML elements
instead of flattened text.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

from bs4 import BeautifulSoup, Tag
from markdown_it import MarkdownIt

from core.brevio.services.pdf_export.highlight import render_fenced_block

logger = logging.getLogger(__name__)

ALLOWED_TAGS = frozenset(
    {
        "a",
        "abbr",
        "b",
        "blockquote",
        "br",
        "code",
        "del",
        "div",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "i",
        "img",
        "li",
        "ol",
        "p",
        "pre",
        "s",
        "span",
        "strong",
        "sub",
        "sup",
        "table",
        "tbody",
        "td",
        "th",
        "thead",
        "tr",
        "ul",
    }
)

GLOBAL_ATTRS = frozenset({"class", "id", "style"})
ALLOWED_ATTRS: dict[str, frozenset[str]] = {
    "a": frozenset({"href", "title", "rel", "target"}),
    "img": frozenset({"src", "alt", "title"}),
    "td": frozenset({"align", "colspan", "rowspan"}),
    "th": frozenset({"align", "colspan", "rowspan"}),
    "ol": frozenset({"start", "type"}),
    "div": frozenset({"data-lang"}),
    "span": frozenset({"aria-hidden"}),
    "code": frozenset(),
    "pre": frozenset(),
}


@dataclass(frozen=True)
class MarkdownRenderResult:
    html: str
    element_count: int
    markdown_chars: int


def _is_safe_href(value: str) -> bool:
    href = value.strip()
    lowered = href.lower()
    if lowered.startswith(("javascript:", "vbscript:", "data:")):
        return False
    return True


def _is_safe_src(value: str) -> bool:
    src = value.strip()
    lowered = src.lower()
    if lowered.startswith(("javascript:", "vbscript:")):
        return False
    if lowered.startswith("data:") and not lowered.startswith("data:image/"):
        return False
    return True


def sanitize_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in list(soup.find_all(True)):
        if not isinstance(tag, Tag):
            continue
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
            continue
        allowed = GLOBAL_ATTRS | ALLOWED_ATTRS.get(tag.name, frozenset())
        for attr in list(tag.attrs):
            if attr.startswith("data-") and tag.name == "div":
                continue
            if attr not in allowed:
                del tag.attrs[attr]
                continue
            if attr.startswith("on"):
                del tag.attrs[attr]

        if tag.name == "a":
            href = tag.get("href")
            if href and not _is_safe_href(str(href)):
                tag.attrs.pop("href", None)
            elif href and (
                str(href).startswith(("http://", "https://", "//"))
            ):
                tag["target"] = "_blank"
                tag["rel"] = "noopener noreferrer"
            else:
                tag.attrs.pop("target", None)

        if tag.name == "img":
            src = tag.get("src")
            if src and not _is_safe_src(str(src)):
                tag.attrs.pop("src", None)
            if not tag.get("alt"):
                tag["alt"] = ""
            classes = tag.get("class") or []
            if isinstance(classes, str):
                classes = [classes]
            if "md-img" not in classes:
                tag["class"] = [*classes, "md-img"]

    body = soup.body
    if body is not None:
        return body.decode_contents()
    return str(soup)


@lru_cache(maxsize=1)
def _build_parser() -> MarkdownIt:
    md = MarkdownIt(
        "commonmark",
        {
            "html": True,
            "linkify": md_linkify_available(),
            "typographer": True,
            "breaks": False,
        },
    )
    md.enable(["table", "strikethrough"])

    def render_fence(tokens, idx, options, env) -> str:  # type: ignore[no-untyped-def]
        token = tokens[idx]
        info = md.utils.unescapeAll(token.info).strip() if token.info else ""
        lang = info.split()[0] if info else ""
        return render_fenced_block(token.content, lang)

    def render_code_block(tokens, idx, options, env) -> str:  # type: ignore[no-untyped-def]
        return render_fenced_block(tokens[idx].content, "")

    default_image = md.renderer.rules["image"]

    def render_image(tokens, idx, options, env) -> str:  # type: ignore[no-untyped-def]
        tokens[idx].attrSet("class", "md-img")
        return default_image(tokens, idx, options, env)

    md.renderer.rules["fence"] = render_fence
    md.renderer.rules["code_block"] = render_code_block
    md.renderer.rules["image"] = render_image
    md.renderer.rules["table_open"] = (
        lambda tokens, idx, options, env: '<div class="md-table-wrap"><table class="md-table">\n'
    )
    md.renderer.rules["table_close"] = (
        lambda tokens, idx, options, env: "</table></div>\n"
    )
    return md


def md_linkify_available() -> bool:
    try:
        import linkify_it  # noqa: F401

        return True
    except ModuleNotFoundError:
        return False


def render_markdown_to_html(markdown: str) -> MarkdownRenderResult:
    source = markdown if isinstance(markdown, str) else ""
    if not source.strip():
        return MarkdownRenderResult(html="", element_count=0, markdown_chars=len(source))

    raw = _build_parser().render(source)
    html = sanitize_html(raw)
    soup = BeautifulSoup(html, "html.parser")
    element_count = len(soup.find_all(True))
    logger.info(
        "PDF_MARKDOWN_PARSED markdown_chars=%s html_chars=%s html_elements=%s parser=markdown-it-py",
        len(source),
        len(html),
        element_count,
    )
    logger.info(
        "PDF_HTML_GENERATED html_chars=%s html_elements=%s",
        len(html),
        element_count,
    )
    return MarkdownRenderResult(
        html=html,
        element_count=element_count,
        markdown_chars=len(source),
    )
