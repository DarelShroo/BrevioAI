"""HTML + CSS → PDF via WeasyPrint."""

from __future__ import annotations

import html
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from core.brevio.services.pdf_export.markdown_renderer import (
    MarkdownRenderResult,
    render_markdown_to_html,
)
from core.brevio.services.pdf_export.pdf_stylesheet import load_pdf_stylesheet

logger = logging.getLogger(__name__)

RENDERER_NAME = "weasyprint"
PARTIAL_SUFFIX = ".partial"


class PdfExportError(RuntimeError):
    """Raised when a summary cannot be exported to PDF."""


@dataclass(frozen=True)
class PdfRenderResult:
    pdf_path: str
    page_count: int
    markdown_chars: int
    html_elements: int
    duration_ms: float
    renderer: str = RENDERER_NAME


def _renderer_label() -> str:
    try:
        import weasyprint

        return f"{RENDERER_NAME}-{weasyprint.__version__}"
    except Exception:
        return RENDERER_NAME


def build_html_document(inner_html: str, title: str = "Resumen") -> str:
    css = load_pdf_stylesheet()
    safe_title = html.escape(title or "Resumen", quote=True)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="es">\n'
        "<head>\n"
        '<meta charset="utf-8"/>\n'
        f"<title>{safe_title}</title>\n"
        f"<style>\n{css}\n</style>\n"
        "</head>\n"
        "<body>\n"
        f'<article class="markdown-body">\n{inner_html}\n</article>\n'
        "</body>\n"
        "</html>\n"
    )


def _validate_pdf(path: Path) -> int:
    if not path.is_file() or path.stat().st_size < 64:
        raise PdfExportError("PDF_VALIDATED failed: empty or missing file")
    header = path.read_bytes()[:8]
    if not header.startswith(b"%PDF"):
        raise PdfExportError("PDF_VALIDATED failed: file is not a PDF")
    try:
        reader = PdfReader(str(path))
        pages = len(reader.pages)
    except Exception as exc:
        raise PdfExportError(f"PDF_VALIDATED failed: unreadable PDF ({exc})") from exc
    if pages < 1:
        raise PdfExportError("PDF_VALIDATED failed: PDF has no pages")
    return pages


def _write_pdf(document_html: str, output_path: Path, base_url: str | None) -> int:
    from weasyprint import HTML
    from weasyprint.text.fonts import FontConfiguration

    font_config = FontConfiguration()
    html_doc = HTML(string=document_html, base_url=base_url)
    document = html_doc.render(font_config=font_config)
    page_count = len(document.pages)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        suffix=".pdf", prefix=".summary-", dir=str(output_path.parent)
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        document.write_pdf(tmp_path)
        os.replace(tmp_path, output_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return page_count


def render_markdown_to_pdf(
    markdown: str,
    output_path: str | Path,
    *,
    base_url: str | None = None,
    document_id: str | None = None,
    title: str = "Resumen",
    parsed: MarkdownRenderResult | None = None,
) -> PdfRenderResult:
    started = time.perf_counter()
    dest = Path(output_path)
    renderer = _renderer_label()
    markdown_chars = len(markdown or "")
    logger.info(
        "PDF_RENDER_START document_id=%s markdown_chars=%s renderer=%s",
        document_id or dest.stem,
        markdown_chars,
        renderer,
    )
    try:
        if not (markdown or "").strip():
            raise PdfExportError("Cannot render PDF from empty markdown")
        result = parsed or render_markdown_to_html(markdown)
        if not result.html.strip():
            raise PdfExportError("Markdown produced empty HTML")
        document_html = build_html_document(result.html, title=title)
        resolved_base = base_url
        if resolved_base:
            base_path = Path(resolved_base)
            if base_path.exists():
                resolved_base = base_path.resolve().as_uri() + "/"
        page_count = _write_pdf(document_html, dest, resolved_base)
        validated_pages = _validate_pdf(dest)
        duration_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "PDF_RENDERED document_id=%s pages=%s bytes=%s duration_ms=%.1f renderer=%s",
            document_id or dest.stem,
            page_count,
            dest.stat().st_size,
            duration_ms,
            renderer,
        )
        logger.info(
            "PDF_VALIDATED document_id=%s pages=%s bytes=%s",
            document_id or dest.stem,
            validated_pages,
            dest.stat().st_size,
        )
        return PdfRenderResult(
            pdf_path=str(dest),
            page_count=validated_pages,
            markdown_chars=result.markdown_chars,
            html_elements=result.element_count,
            duration_ms=duration_ms,
            renderer=renderer,
        )
    except Exception as exc:
        duration_ms = (time.perf_counter() - started) * 1000
        logger.exception(
            "PDF_RENDER_FAILED document_id=%s markdown_chars=%s duration_ms=%.1f renderer=%s error=%s",
            document_id or dest.stem,
            markdown_chars,
            duration_ms,
            renderer,
            exc,
        )
        raise


def export_markdown_file_to_pdf(
    md_path: str | Path,
    pdf_path: str | Path | None = None,
    *,
    document_id: str | None = None,
    title: str = "Resumen",
) -> str:
    source = Path(md_path)
    if source.name.endswith(PARTIAL_SUFFIX) or source.suffix == PARTIAL_SUFFIX:
        raise PdfExportError(
            "PDF must be generated from the final summary.md, not a partial artifact"
        )
    if not source.is_file():
        raise FileNotFoundError(f"Markdown source not found: {source}")
    markdown = source.read_text(encoding="utf-8")
    dest = Path(pdf_path) if pdf_path else source.with_suffix(".pdf")
    result = render_markdown_to_pdf(
        markdown,
        dest,
        base_url=str(source.resolve().parent),
        document_id=document_id or source.parent.name,
        title=title,
    )
    return result.pdf_path
