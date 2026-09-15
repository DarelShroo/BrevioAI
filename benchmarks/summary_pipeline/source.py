from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


def extract_document_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text, _ = _read_pdf_with_page_count(path)
        return text
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".docx":
        from docx import Document

        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    raise ValueError(f"Unsupported document type: {path.suffix}")


def _read_pdf(path: Path) -> str:
    text, _ = _read_pdf_with_page_count(path)
    return text


def _read_pdf_with_page_count(path: Path) -> tuple[str, int]:
    import pypdf

    reader = pypdf.PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        cleaned = re.sub(r"\n+", "\n", text.strip())
        if cleaned:
            pages.append(cleaned)
    if not pages:
        raise ValueError(f"Empty PDF: {path}")
    return "\n".join(pages), len(reader.pages)


def profile_source(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".pdf":
        raw, page_count = _read_pdf_with_page_count(path)
    else:
        raw = extract_document_text(path)
        page_count = max(1, raw.count("\f") + 1)
    try:
        from core.shared.utils.chunking_utils import (
            extract_document_outline,
            strip_document_front_matter_toc,
        )

        body = strip_document_front_matter_toc(raw) or raw
        outline = extract_document_outline(body)
    except Exception:
        body = raw
        outline = []
    words = body.split()
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return {
        "path": str(path),
        "name": path.name,
        "bytes": path.stat().st_size,
        "pages_or_sections": page_count,
        "pages": page_count if path.suffix.lower() == ".pdf" else None,
        "raw_characters": len(raw),
        "body_characters": len(body),
        "body_words": len(words),
        "approx_tokens": max(1, int(len(body) / 4)),
        "outline": outline,
        "sha256": digest[:16],
        "sha256_full": digest,
        "text": body,
    }
