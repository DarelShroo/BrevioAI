"""Public read-only endpoints for showcase example summaries under data/example."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, PlainTextResponse

from core.brevio.constants.constants import Constants

SAFE_ID = re.compile(r"^[a-fA-F0-9]{24}$")

router = APIRouter(prefix="/examples", tags=["examples"])


def example_root() -> Path:
    return (Path(Constants.DESTINATION_FOLDER) / "example").resolve()


def _ensure_under_example(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(example_root())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Example not found"
        ) from exc
    return resolved


def _load_manifest() -> dict[str, Any]:
    manifest_path = example_root() / "manifest.json"
    if not manifest_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Example showcase is not available",
        )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Example showcase manifest is invalid",
        )
    return payload


def _find_entry(slug_or_id: str) -> dict[str, Any]:
    key = (slug_or_id or "").strip()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Example not found")

    manifest = _load_manifest()
    for entry in manifest["entries"]:
        if not isinstance(entry, dict):
            continue
        if entry.get("slug") == key or entry.get("id") == key:
            return entry

    # Allow bare trailing hex (d89204) → summary_d89204
    if re.fullmatch(r"[a-fA-F0-9]{6}", key):
        return _find_entry(f"summary_{key}")

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Example not found")


def _entry_dir(entry: dict[str, Any]) -> Path:
    entry_id = str(entry.get("id") or "")
    if not SAFE_ID.match(entry_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Example not found")
    return _ensure_under_example(example_root() / entry_id / "0")


@router.get("")
async def list_examples() -> dict[str, Any]:
    manifest = _load_manifest()
    entries = []
    for raw in manifest["entries"]:
        if not isinstance(raw, dict):
            continue
        entries.append(
            {
                "id": raw.get("id"),
                "slug": raw.get("slug"),
                "title": raw.get("title"),
                "category": raw.get("category"),
                "category_key": raw.get("category_key"),
                "style": raw.get("style"),
                "style_key": raw.get("style_key"),
                "type": raw.get("type"),
                "model": raw.get("model"),
                "results": raw.get("results", 1),
                "created_label": raw.get("created_label"),
                "document_name": raw.get("document_name"),
                "summary_level": raw.get("summary_level"),
                "summary_level_label": raw.get("summary_level_label"),
                "format": raw.get("format"),
                "format_label": raw.get("format_label"),
                "language": raw.get("language"),
                "language_label": raw.get("language_label"),
                "default": bool(raw.get("default")),
            }
        )
    return {
        "default_slug": manifest.get("default_slug"),
        "entries": entries,
    }


@router.get("/{slug_or_id}")
async def get_example(slug_or_id: str) -> dict[str, Any]:
    entry = _find_entry(slug_or_id)
    return {
        "id": entry.get("id"),
        "slug": entry.get("slug"),
        "title": entry.get("title"),
        "category": entry.get("category"),
        "category_key": entry.get("category_key"),
        "style": entry.get("style"),
        "style_key": entry.get("style_key"),
        "type": entry.get("type"),
        "model": entry.get("model"),
        "results": entry.get("results", 1),
        "created_label": entry.get("created_label"),
        "document_name": entry.get("document_name"),
        "summary_level": entry.get("summary_level"),
        "summary_level_label": entry.get("summary_level_label"),
        "format": entry.get("format"),
        "format_label": entry.get("format_label"),
        "language": entry.get("language"),
        "language_label": entry.get("language_label"),
        "default": bool(entry.get("default")),
        "highlights": entry.get("highlights") or [],
        "summary_url": f"/examples/{entry.get('slug')}/summary",
        "pdf_url": f"/examples/{entry.get('slug')}/pdf",
    }


@router.get("/{slug_or_id}/summary")
async def get_example_summary(slug_or_id: str) -> PlainTextResponse:
    entry = _find_entry(slug_or_id)
    summary_name = str(entry.get("summary_file") or "summary.md")
    if "/" in summary_name or "\\" in summary_name or summary_name.startswith("."):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Example not found")
    path = _ensure_under_example(_entry_dir(entry) / summary_name)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found")
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")


@router.get("/{slug_or_id}/pdf")
async def get_example_pdf(slug_or_id: str) -> FileResponse:
    entry = _find_entry(slug_or_id)
    pdf_name = str(entry.get("pdf_file") or entry.get("document_name") or "")
    if not pdf_name or "/" in pdf_name or "\\" in pdf_name or pdf_name.startswith("."):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found")
    if not pdf_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found")
    path = _ensure_under_example(_entry_dir(entry) / pdf_name)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=pdf_name,
        content_disposition_type="inline",
    )
