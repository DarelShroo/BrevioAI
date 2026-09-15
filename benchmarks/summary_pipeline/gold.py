from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from .claims import content_tokens, extract_numbers, token_overlap

_GOLD_DIR = Path(__file__).resolve().parent / "dataset" / "gold"

DOCUMENT_ALIASES: tuple[tuple[str, str], ...] = (
    ("798_indice", "acemoglu-econ-ch1"),
    ("fundamentos de marketing", "fundamentos-marketing"),
    ("inciciacion_javascript", "iniciacion-javascript"),
    ("iniciacion_javascript", "iniciacion-javascript"),
    ("bunge_ciencia", "bunge-ciencia"),
    ("sistema_carga", "sistema-carga-u1"),
    ("using-asyncio", "asyncio-hattingh"),
    ("asyncio", "asyncio-hattingh"),
)


def document_id_for_name(name: str) -> str:
    stem = Path(name).stem.lower()
    for needle, doc_id in DOCUMENT_ALIASES:
        if needle in stem:
            return doc_id
    return re_slug(stem)


def re_slug(value: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "unknown-document"


@lru_cache(maxsize=32)
def load_gold(document_id: str) -> dict[str, Any] | None:
    path = _GOLD_DIR / f"{document_id}.json"
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return payload


def gold_for_document(name: str) -> dict[str, Any] | None:
    return load_gold(document_id_for_name(name))


def match_topics(topics: list[str], summary: str) -> tuple[list[str], list[str]]:
    haystack = (summary or "").casefold()
    present: list[str] = []
    missing: list[str] = []
    for topic in topics:
        tokens = content_tokens(topic)
        if not tokens:
            continue
        if topic.casefold() in haystack or all(tok in haystack for tok in tokens):
            present.append(topic)
        else:
            missing.append(topic)
    return present, missing


def match_key_claims(
    claims: list[Mapping[str, Any]],
    summary: str,
    source: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for claim in claims:
        text = str(claim.get("text") or claim.get("claim") or "")
        if not text:
            continue
        coverage = token_overlap(text, summary)
        if text.casefold() in (summary or "").casefold() or coverage >= 0.55:
            status = "supported"
        elif coverage >= 0.30:
            status = "partial"
        else:
            status = "missing"
        rows.append(
            {
                "id": claim.get("id"),
                "text": text,
                "importance": int(claim.get("importance") or 2),
                "status": status,
                "overlap": round(coverage, 3),
                "in_source": text.casefold() in (source or "").casefold()
                or token_overlap(text, source) >= 0.4,
            }
        )
    return rows


def match_numbers(
    gold_numbers: list[Mapping[str, Any] | str],
    summary: str,
    source: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    summary_nums = extract_numbers(summary)
    for item in gold_numbers:
        if isinstance(item, str):
            number, meaning = item, ""
        else:
            number = str(item.get("text") or item.get("number") or "")
            meaning = str(item.get("meaning") or "")
        if not number:
            continue
        in_summary = number in (summary or "") or number in summary_nums
        in_source = number in (source or "")
        contradicted = False
        if in_source and not in_summary and summary_nums:
            if meaning and meaning.casefold() in (summary or "").casefold():
                contradicted = True
        rows.append(
            {
                "number": number,
                "meaning": meaning,
                "in_summary": in_summary,
                "in_source": in_source,
                "contradicted": contradicted,
            }
        )
    return rows
