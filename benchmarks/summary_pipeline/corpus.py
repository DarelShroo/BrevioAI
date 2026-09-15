from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .gold import document_id_for_name
from .source import profile_source

SUPPORTED_DOCUMENT_SUFFIXES = frozenset({".pdf", ".docx", ".txt"})


def discover_corpus_files(docs_dir: Path) -> list[Path]:
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"Documents directory not found: {docs_dir}")
    return sorted(path.resolve() for path in docs_dir.iterdir() if path.is_file())


def classify_size(approx_tokens: int) -> str:
    if approx_tokens < 10_000:
        return "SMALL"
    if approx_tokens < 50_000:
        return "MEDIUM"
    if approx_tokens < 150_000:
        return "LARGE"
    return "VERY_LARGE"


def estimated_chunks(
    tokens: int,
    *,
    chunk_tokens: int = 3_000,
    overlap_tokens: int = 200,
) -> int:
    if tokens <= chunk_tokens:
        return 1
    stride = max(1, chunk_tokens - overlap_tokens)
    return 1 + math.ceil((tokens - chunk_tokens) / stride)


def _pdf_pages(path: Path) -> int | None:
    if path.suffix.lower() != ".pdf":
        return None
    from pypdf import PdfReader

    return len(PdfReader(str(path)).pages)


from .lint import detect_language as _detect_language


def _corpus_id(path: Path, source_hash: str = "") -> str:
    identity = f"{path.name}\0{path.stat().st_size}\0{source_hash}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return f"book-{digest}"


def build_corpus_manifest(
    docs_dir: Path,
    *,
    model: str = "qwen3:14b",
    chunk_tokens: int = 3_000,
    overlap_tokens: int = 200,
) -> dict[str, Any]:
    books: list[dict[str, Any]] = []
    for path in discover_corpus_files(docs_dir):
        supported = path.suffix.lower() in SUPPORTED_DOCUMENT_SUFFIXES
        row: dict[str, Any] = {
            "corpus_id": "",
            "name": path.name,
            "path": str(path),
            "extension": path.suffix.lower(),
            "format": path.suffix.lower().lstrip("."),
            "bytes": path.stat().st_size,
            "discovered": True,
            "supported": supported,
            "processable": False,
            "error": "",
        }
        if supported:
            try:
                profile = profile_source(path)
                text = str(profile.pop("text"))
                approx_tokens = int(profile.get("approx_tokens") or 0)
                sections = list(profile.get("outline") or [])
                row.update(profile)
                row.update(
                    {
                        "document_id": document_id_for_name(path.name),
                        "pages": profile.get("pages") or _pdf_pages(path),
                        "sections_detected": len(sections),
                        "language_detected": _detect_language(text),
                        "size_class": classify_size(approx_tokens),
                        "estimated_pipeline_chunks": estimated_chunks(
                            approx_tokens,
                            chunk_tokens=chunk_tokens,
                            overlap_tokens=overlap_tokens,
                        ),
                        "complexity": (
                            "high"
                            if approx_tokens >= 50_000 or len(sections) >= 60
                            else "medium"
                            if approx_tokens >= 10_000 or len(sections) >= 20
                            else "low"
                        ),
                        "processable": bool(text.strip()),
                    }
                )
            except Exception as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
        row["corpus_id"] = _corpus_id(path, str(row.get("sha256") or ""))
        books.append(row)

    valid = [
        row for row in books if row.get("supported") and row.get("processable")
    ]
    return {
        "schema_version": 2,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus_root": str(docs_dir.resolve()),
        "supported_extensions": sorted(SUPPORTED_DOCUMENT_SUFFIXES),
        "model_required": model,
        "chunk_profile": {
            "max_tokens_per_chunk": chunk_tokens,
            "overlap_tokens": overlap_tokens,
        },
        "totals": {
            "files_discovered": len(books),
            "books_valid": len(valid),
            "books_unsupported": sum(
                1 for row in books if not row.get("supported")
            ),
            "books_unprocessable": sum(
                1
                for row in books
                if row.get("supported") and not row.get("processable")
            ),
        },
        "books": books,
    }


def write_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(dict(manifest), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def audit_corpus_coverage(
    manifest: Mapping[str, Any],
    records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = list(records)
    valid_books = [
        item
        for item in manifest.get("books", [])
        if item.get("supported") and item.get("processable")
    ]
    audit_rows: list[dict[str, Any]] = []
    for book in valid_books:
        name = str(book.get("name") or "")
        book_records = [
            row for row in rows if str(row.get("document") or "") == name
        ]
        processed = any(
            row.get("task_id") or row.get("folder_entry_id") for row in book_records
        )
        successful = [
            row
            for row in book_records
            if int(row.get("summary_characters") or 0) > 0
            and row.get("summary_path")
        ]
        summarized = bool(successful)
        def _legacy_ok(row: Mapping[str, Any]) -> bool:
            return (
                not row.get("status")
                and not str(row.get("error") or "").strip()
                and bool(row.get("quality"))
                and int(row.get("summary_characters") or 0) > 0
                and bool(row.get("summary_path"))
            )

        valid_ok = any(
            str(row.get("status") or "") == "VALID" or _legacy_ok(row)
            for row in book_records
        )
        evaluated = any(
            bool(row.get("status") or row.get("quality")) for row in book_records
        )
        errors = sorted(
            {
                str(row.get("error") or row.get("status"))
                for row in book_records
                if str(row.get("error") or "").strip()
                or str(row.get("status") or "") not in {"", "VALID"}
            }
        )
        status = (
            "VALID"
            if processed and summarized and valid_ok
            else "SCORED_INVALID"
            if processed and evaluated
            else "NOT_EVALUATED"
            if summarized
            else "NO_SUMMARY"
            if processed
            else "NOT_PROCESSED"
        )
        audit_rows.append(
            {
                "corpus_id": book.get("corpus_id"),
                "book": name,
                "discovered": True,
                "processed": processed,
                "summary_generated": summarized,
                "evaluated": evaluated,
                "status": status,
                "error": "; ".join(errors),
            }
        )

    counts = {
        "books_discovered": len(valid_books),
        "books_processed": sum(bool(row["processed"]) for row in audit_rows),
        "books_summarized": sum(
            bool(row["summary_generated"]) for row in audit_rows
        ),
        "books_evaluated": sum(bool(row["evaluated"]) for row in audit_rows),
    }
    complete = len(set(counts.values())) == 1 and all(
        row["status"] in {"VALID", "SCORED_INVALID"} for row in audit_rows
    )
    return {
        **counts,
        "books_pending": sum(row["status"] != "VALID" for row in audit_rows),
        "books_omitted": sum(not row["processed"] for row in audit_rows),
        "complete": complete,
        "invariant": (
            "books_discovered == books_processed == "
            "books_summarized == books_evaluated"
        ),
        "books": audit_rows,
    }
