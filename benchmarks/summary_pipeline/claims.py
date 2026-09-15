from __future__ import annotations

import re
from typing import Any

_MARKDOWN = re.compile(r"[*_`>#|]+")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÜÑ0-9])")
_NUMBER = re.compile(
    r"(?<![\w.])(?:\d{1,4}(?:[.,]\d{3})*(?:[.,]\d+)?%?|"
    r"\d+(?:st|nd|rd|th))(?!\w)",
    re.IGNORECASE,
)
_DATE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(?:19|20)\d{2})\b"
)
_CONTENT = re.compile(
    r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_\-]{2,}"
)
_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was",
    "el", "la", "los", "las", "una", "unos", "del", "que", "por", "con",
    "para", "como", "este", "esta", "esto",
}


def _clean_claim(text: str) -> str:
    text = _MARKDOWN.sub(" ", text)
    text = re.sub(r"^\s*(?:[-+•]|\d+[.)])\s*", "", text)
    return re.sub(r"\s+", " ", text).strip(" -:;\t")


def extract_claims(summary: str, *, limit: int = 160) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_line in (summary or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line in {"---", "***"}:
            continue
        for part in _SENTENCE_BOUNDARY.split(line):
            claim = _clean_claim(part)
            words = claim.split()
            if len(words) < 4 or claim.endswith(":"):
                continue
            normalized = claim.casefold()
            if normalized in seen:
                continue
            seen.add(normalized)
            importance = 2
            if _NUMBER.search(claim) or _DATE.search(claim):
                importance = 3
            elif len(words) < 8:
                importance = 1
            claims.append(
                {
                    "id": f"c{len(claims) + 1:03d}",
                    "claim": claim,
                    "importance": importance,
                }
            )
            if len(claims) >= limit:
                return claims
    return claims


def content_tokens(text: str) -> set[str]:
    return {
        match.group(0).casefold()
        for match in _CONTENT.finditer(text or "")
        if match.group(0).casefold() not in _STOP
    }


def extract_numbers(text: str) -> set[str]:
    return {match.group(0) for match in _NUMBER.finditer(text or "")}


def token_overlap(left: str, right: str) -> float:
    a = content_tokens(left)
    b = content_tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a)


def claim_supported_by_source(claim: str, source: str) -> str:
    if not claim.strip() or not source.strip():
        return "unsupported"
    folded_source = source.casefold()
    folded_claim = claim.casefold()
    numbers = extract_numbers(claim)
    if numbers and any(num not in source and num not in folded_source for num in numbers):
        if any(num in source or num in folded_source for num in numbers):
            return "partial"
        return "unsupported"
    overlap = token_overlap(claim, source)
    if folded_claim in folded_source or overlap >= 0.55:
        return "supported"
    if overlap >= 0.30:
        return "partial"
    return "unsupported"


def contradiction_against_gold_number(
    summary: str,
    gold_number: str,
    source: str,
) -> bool:
    if gold_number not in source and gold_number not in source.casefold():
        return False
    numbers = extract_numbers(summary)
    if gold_number in numbers or gold_number in summary:
        return False
    if not numbers:
        return False
    # A nearby rewritten number while the gold value is absent from the summary
    # is treated as a contradiction only when the gold number is important
    # enough to appear in source and a different number was substituted.
    return gold_number not in summary and bool(numbers)
