import re
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse

DISPLAY_NAME_MAX_LENGTH = 255
GENERIC_DOCUMENT_NAME = re.compile(r"^(document|documento|video)\s*\d*$", re.IGNORECASE)
BATCH_SUFFIX = re.compile(r"\s\(\+\d+\)$")


def is_generic_source_name(value: str | None) -> bool:
    text = (value or "").strip()
    if not text:
        return True
    return bool(GENERIC_DOCUMENT_NAME.match(text))


def clip_display_name(value: str, max_length: int = DISPLAY_NAME_MAX_LENGTH) -> str:
    cleaned = " ".join((value or "").split())
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[:max_length].rstrip()


def source_basename(path_or_url: str | None) -> str:
    raw = (path_or_url or "").strip()
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        name = unquote(Path(parsed.path).name)
        return name.split("?")[0].strip()
    return Path(raw).name.strip()


def names_for_source(
    path_or_url: str | None,
    index: int = 0,
    *,
    kind: str = "document",
) -> tuple[str, str]:
    """Return (display_name, original_name) from a file path or URL.

    Used for individual *results* (files), not for FolderEntry / LibraryFolder titles.
    """
    original = source_basename(path_or_url)
    if original and not is_generic_source_name(original):
        display = clip_display_name(original)
        return display, clip_display_name(original)
    fallback = f"{kind.capitalize()} {index}"
    display = clip_display_name(original or fallback)
    return display, clip_display_name(original) if original else display


def originals_for_batch(
    paths_or_urls: list[str | None] | tuple[str | None, ...],
    *,
    kind: str = "document",
) -> str:
    """Audit trail of source basenames for a job; never used as the entry title."""
    items = list(paths_or_urls or [])
    if not items:
        return ""
    originals = [
        source_basename(item) or f"{kind.capitalize()} {index}"
        for index, item in enumerate(items)
    ]
    return clip_display_name("; ".join(originals))


def names_for_batch(
    paths_or_urls: list[str | None] | tuple[str | None, ...],
    *,
    kind: str = "document",
    entry_name: str | None = None,
) -> tuple[str, str]:
    """Return (entry_display_name, original_name) for a summary job.

    The entry title is independent of contained files:
    - If the caller provides ``entry_name``, that is the display name.
    - Otherwise display name is empty (caller assigns a stable ID-based name).
    ``original_name`` remains an audit string of source basenames.
    """
    original = originals_for_batch(paths_or_urls, kind=kind)
    cleaned = " ".join((entry_name or "").split())
    if cleaned and not is_generic_source_name(cleaned):
        return clip_display_name(cleaned), original
    return "", original


def stable_entry_name(entry_id: str | None) -> str:
    """Stable fallback title when no user-provided entry name exists."""
    raw = str(entry_id or "").strip()
    suffix = raw[-6:] if raw else "entry"
    return clip_display_name(f"Summary {suffix}")


def _result_source_labels(results: Iterable[object] | None) -> set[str]:
    labels: set[str] = set()
    for result in results or []:
        if isinstance(result, dict):
            for attr in ("name", "original_name"):
                raw = result.get(attr)
                if isinstance(raw, str) and raw.strip():
                    labels.add(raw.strip())
            continue
        for attr in ("name", "original_name"):
            value = getattr(result, attr, None)
            if isinstance(value, str) and value.strip():
                labels.add(value.strip())
    return labels


def is_file_derived_entry_name(
    name: str | None,
    results: Iterable[object] | None = None,
    *,
    original_name: str | None = None,
) -> bool:
    """True when ``name`` looks auto-derived from contained file names."""
    text = (name or "").strip()
    if not text or is_generic_source_name(text):
        return True

    labels = _result_source_labels(results)
    if text in labels:
        return True

    without_batch = BATCH_SUFFIX.sub("", text).strip()
    if without_batch and without_batch in labels:
        return True

    if original_name:
        originals = [part.strip() for part in original_name.split(";") if part.strip()]
        if text in originals:
            return True
        if without_batch and without_batch in originals:
            return True
        if len(originals) > 1 and text == originals[0]:
            return True

    return False


def resolve_entry_display_name(
    *,
    entry_id: str | None,
    name: str | None,
    original_name: str | None = None,
    results: Iterable[object] | None = None,
) -> str:
    """Single source of truth for FolderEntry display titles."""
    text = (name or "").strip()
    if text and not is_file_derived_entry_name(
        text, results, original_name=original_name
    ):
        return clip_display_name(text)
    return stable_entry_name(entry_id)


def require_editable_name(
    value: str | None, *, code_empty: str, code_too_long: str
) -> str:
    cleaned = " ".join((value or "").split())
    if not cleaned:
        raise NameValidationError(code_empty)
    if len(cleaned) > DISPLAY_NAME_MAX_LENGTH:
        raise NameValidationError(code_too_long)
    return cleaned


class NameValidationError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
