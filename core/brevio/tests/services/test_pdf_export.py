from __future__ import annotations

import logging
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.services.pdf_export import (
    PdfExportError,
    build_html_document,
    export_markdown_file_to_pdf,
    render_markdown_to_html,
    render_markdown_to_pdf,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SAMPLE_MD = (FIXTURES / "pdf_export_sample.md").read_text(encoding="utf-8")


def _as_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def test_headings_produce_heading_elements() -> None:
    soup = _as_soup(render_markdown_to_html(SAMPLE_MD).html)
    assert soup.find("h1").get_text(strip=True) == "Título principal"
    assert soup.find("h2").get_text(strip=True) == "Sección"
    assert soup.find("h3").get_text(strip=True) == "Subsección"


def test_inline_emphasis_and_code() -> None:
    soup = _as_soup(render_markdown_to_html(SAMPLE_MD).html)
    assert soup.find("strong").get_text(strip=True) == "negrita"
    assert soup.find("em").get_text(strip=True) == "cursiva"
    inline = [c.get_text() for c in soup.find_all("code") if not c.find_parent("pre")]
    assert any("código inline" in text for text in inline)


def test_lists_produce_ul_and_ol() -> None:
    soup = _as_soup(render_markdown_to_html(SAMPLE_MD).html)
    ul_items = [li.get_text(" ", strip=True) for li in soup.select("ul > li")]
    assert any(item.startswith("Lista") for item in ul_items)
    nested = soup.select("ul ul li")
    assert any("Lista anidada" in li.get_text() for li in nested)
    ol_items = [li.get_text(strip=True) for li in soup.select("ol > li")]
    assert ol_items[:2] == ["Lista numerada", "Segundo elemento"]


def test_code_block_is_pre_code_not_paragraph() -> None:
    soup = _as_soup(render_markdown_to_html(SAMPLE_MD).html)
    pre = soup.select_one("pre.md-code__pre, .md-code pre")
    assert pre is not None
    code = pre.find("code")
    assert code is not None
    text = code.get_text()
    assert "async def main():" in text
    assert "    print(" in text or "    print(" in text.replace("\xa0", " ")
    assert "await asyncio.sleep(1)" in text
    assert code.find_parent("p") is None
    assert "mdh-" in str(code)


def test_table_blockquote_link_and_hr() -> None:
    soup = _as_soup(render_markdown_to_html(SAMPLE_MD).html)
    table = soup.find("table")
    assert table is not None
    assert table.find("thead") is not None or table.find("th") is not None
    cells = [td.get_text(strip=True) for td in table.find_all(["th", "td"])]
    assert "Modelo" in cells
    assert "8192" in cells
    assert "Esto es una cita." in soup.find("blockquote").get_text()
    assert soup.find("a", href="https://example.com") is not None
    assert soup.find("hr") is not None


def test_sanitizer_strips_scripts_and_keeps_content() -> None:
    html = render_markdown_to_html(
        "# Safe\n\n<script>alert(1)</script>\n\n[x](javascript:alert(1))\n"
    ).html
    soup = _as_soup(html)
    assert soup.find("script") is None
    link = soup.find("a")
    if link is not None:
        href = (link.get("href") or "").lower()
        assert "javascript:" not in href


def test_pdf_from_sample_contains_text_unicode_and_structure(tmp_path: Path) -> None:
    pdf_path = tmp_path / "summary.pdf"
    result = render_markdown_to_pdf(SAMPLE_MD, pdf_path, document_id="sample")
    assert pdf_path.is_file()
    data = pdf_path.read_bytes()
    assert data.startswith(b"%PDF")
    assert result.page_count >= 1
    assert result.html_elements > 10
    assert result.markdown_chars == len(SAMPLE_MD)

    from pypdf import PdfReader

    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(pdf_path)).pages)
    compact = "".join(text.split())
    assert "Título principal" in text
    assert "Párrafo normal" in text
    assert "negrita" in text
    assert "cursiva" in text
    assert "Lista numerada" in text
    assert "Esto es una cita" in text
    assert "asyncdefmain" in compact
    assert "awaitasyncio.sleep" in compact
    assert "print(" in compact
    assert "Modelo" in text
    assert "8192" in text
    assert "Fin del documento" in text
    assert "ñ" in text
    assert "áéíóú" in text
    assert "Español" in text or "español" in text
    # Extraction concatenates adjacent spans; the PDF must still have
    # multiple blocks rather than one flattened paragraph.
    assert text.count("\n") >= 8
    assert "Campo" in text and "Valor" in text


def test_pdf_long_document_spans_multiple_pages(tmp_path: Path) -> None:
    parts = ["# Documento largo\n"]
    for i in range(1, 61):
        parts.append(
            f"## Capítulo {i}\n\nPárrafo {i} con contenido suficiente para ocupar espacio.\n"
        )
        parts.append("\n".join(f"Línea extra {i}.{j} del capítulo." for j in range(8)))
        parts.append("\n")
    markdown = "\n".join(parts)
    pdf_path = tmp_path / "long.pdf"
    result = render_markdown_to_pdf(markdown, pdf_path, document_id="long")
    assert result.page_count >= 2
    from pypdf import PdfReader

    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(pdf_path)).pages)
    assert "Capítulo 1" in text
    assert "Capítulo 60" in text
    assert text.count("Párrafo") >= 40


def test_export_rejects_partial_and_empty(tmp_path: Path) -> None:
    partial = tmp_path / "summary.md.partial"
    partial.write_text("# No\n", encoding="utf-8")
    with pytest.raises(PdfExportError, match="partial"):
        export_markdown_file_to_pdf(partial)

    empty = tmp_path / "summary.md"
    empty.write_text("   \n", encoding="utf-8")
    with pytest.raises(PdfExportError, match="empty"):
        export_markdown_file_to_pdf(empty)


@pytest.mark.asyncio
async def test_directory_manager_uses_final_summary_md(tmp_path: Path) -> None:
    md_file = tmp_path / "summary.md"
    md_file.write_text(SAMPLE_MD, encoding="utf-8")
    manager = DirectoryManager()
    pdf_path = await manager.create_pdf_version(str(md_file), document_id="dir-sample")
    assert pdf_path is not None
    assert Path(pdf_path).is_file()
    assert Path(pdf_path).read_bytes().startswith(b"%PDF")

    partial = tmp_path / "summary.md.partial"
    partial.write_text(SAMPLE_MD, encoding="utf-8")
    with pytest.raises(PdfExportError):
        await manager.create_pdf_version(str(partial))


def test_html_document_embeds_print_css() -> None:
    inner = render_markdown_to_html(SAMPLE_MD).html
    document = build_html_document(inner, title="Prueba")
    assert "<h1>" in document
    assert "markdown-body" in document
    assert "@page" in document
    assert "Brevio Sans" in document or "Noto Sans" in document
    assert "pre-wrap" in document
