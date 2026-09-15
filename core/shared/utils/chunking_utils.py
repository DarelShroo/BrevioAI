import logging
import re
from typing import Any, List, Sequence

from core.shared.enums.model import ModelType
from core.shared.utils.model_tokens_utils import get_encoder
from core.shared.utils.summary_quality import filter_reliable_outline

logger = logging.getLogger(__name__)

_MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_NUMBERED_SECTION = re.compile(
    r"^((?:\d+\.)+\d*|\d+)\s+([A-ZÁÉÍÓÚÑÜ][^\n]{2,120})$",
    re.MULTILINE,
)
_TOC_INDEX_MARKERS = (
    "tabla de contenido",
    "tabla de contenidos",
    "table of contents",
    "tabla de ejemplos",
    "table of examples",
    "índice de contenido",
    "indice de contenido",
    "índice general",
    "indice general",
    "índice detallado",
    "indice detallado",
)
_TOC_LEADER = re.compile(r"\.{4,}")
_TOC_PAGE_LINE = re.compile(r".{8,}(?:\.{3,}|\s{2,})\d+\s*$")
_TOC_TRAILING_PAGE = re.compile(r"\s{2,}\d{1,4}\s*$")
_TOC_NUMBERED_ENTRY = re.compile(
    r"(?im)^\s*(?:\d+\.\d+|[ivx]+\.\d+|cap[ií]tulo\s+\d+|chapter\s+\d+|parte\s+[ivxlcdm\d]+)\b"
)
_TOC_RECURRING = re.compile(
    r"(?im)^\s*(?:resumen|t[ée]rminos clave|preguntas|problemas|"
    r"ap[ée]ndice|notas|glosario|cr[ée]ditos|índice anal[ií]tico|"
    r"indice analitico|que hablen los datos|econom[ií]a basada en la evidencia|"
    r"decisi[oó]n y consecuencia)\b"
)
_TOC_UNIT_LINE = re.compile(
    r"(?im)^\s*(?:unidad|unit|cap[ií]tulo|chapter|ejemplo|example|parte)\s+[ivx\d]+"
)
_ROMAN_PAGE = re.compile(r"(?i)^\s*[ivxlcdm]{1,8}\s*$")
_BODY_FRONT_MATTER = re.compile(
    r"(?im)^\s*(los autores|pr[oó]logo|prologue|preface|prefaci[oa])\s*$"
)


def _is_toc_continuation(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 110:
        return False
    if stripped.endswith(("?", ":", ",", ";", "—", "-")):
        return True
    if stripped[0].islower() or stripped.startswith("¿"):
        return True
    return False


def _looks_like_body_prose(line: str) -> bool:
    stripped = line.strip()
    if _BODY_FRONT_MATTER.match(stripped):
        return True
    if (
        "." in stripped
        and len(stripped) >= 70
        and not _TOC_TRAILING_PAGE.search(stripped)
        and not any(marker in stripped.lower() for marker in _TOC_INDEX_MARKERS)
    ):
        return True
    return False


def _is_toc_line(line: str, *, in_index: bool = False) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    lower = stripped.lower()
    if any(marker in lower for marker in _TOC_INDEX_MARKERS):
        return True
    if _TOC_LEADER.search(stripped) or _TOC_PAGE_LINE.search(stripped):
        return True
    if _TOC_TRAILING_PAGE.search(stripped) and len(stripped) < 160:
        return True
    if _TOC_UNIT_LINE.match(stripped):
        return True
    if in_index and (
        _TOC_NUMBERED_ENTRY.match(stripped) or _TOC_RECURRING.match(stripped)
    ):
        return True
    if stripped.count("_") >= 15:
        return True
    if re.search(r"\.{3,}\s*\d+\s*$", stripped):
        return True
    if _ROMAN_PAGE.match(stripped):
        return True
    if re.match(r"(?i)^\s*dedicatoria\s*$", stripped):
        return True
    return False


def is_table_of_contents_chunk(text: str) -> bool:
    """True when a chunk is mostly an index / TOC, not developed body prose."""
    if not text or not text.strip():
        return False
    lower = text.lower()
    leader_runs = _TOC_LEADER.findall(text)
    leader_run_count = len(leader_runs)
    leader_chars = sum(len(run) for run in leader_runs)
    if leader_run_count >= 12 or leader_chars >= 200:
        return True
    if any(marker in lower for marker in _TOC_INDEX_MARKERS) and (
        leader_run_count >= 4
        or leader_chars >= 80
        or "índice general" in lower
        or "indice general" in lower
        or "índice detallado" in lower
    ):
        return True
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 8:
        return False
    page_lines = sum(
        1
        for line in lines
        if _TOC_PAGE_LINE.search(line) or _TOC_TRAILING_PAGE.search(line)
    )
    unit_lines = sum(1 for line in lines if _TOC_UNIT_LINE.search(line))
    if page_lines >= 8 and page_lines / len(lines) >= 0.28:
        return True
    return unit_lines >= 8 and (leader_run_count >= 6 or leader_chars >= 100)


def extract_toc_entry_labels(text: str, max_entries: int = 24) -> List[str]:
    """Pull short TOC unit/example labels for a compact MAP stub."""
    if not text:
        return []
    labels: List[str] = []
    seen: set[str] = set()
    for match in _TOC_UNIT_LINE.finditer(text):
        line_end = text.find("\n", match.start())
        if line_end < 0:
            line_end = len(text)
        raw = text[match.start() : line_end]
        cleaned = re.sub(r"\.{2,}.*$", "", raw)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .-_")
        if len(cleaned) < 4:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        labels.append(cleaned[:120])
        if len(labels) >= max_entries:
            break
    return labels


def split_text_into_chunks(
    text: str,
    chunk_size: int,
    overlap: float,
    model: ModelType,
) -> List[str]:
    encoder = get_encoder(model)
    tokens = encoder.encode(text)

    chunks: List[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(encoder.decode(chunk_tokens))

        overlap_tokens = int(chunk_size * overlap)
        start = end - overlap_tokens if end - overlap_tokens > start else end

    return chunks


def strip_leading_toc(text: str) -> str:
    """Drop leading TOC/index lines from a hybrid chunk; keep developed body prose."""
    if not text or not text.strip():
        return text

    def toc_like(line: str) -> bool:
        return _is_toc_line(line)

    lines = text.splitlines(keepends=True)
    index = 0
    while index < len(lines) and toc_like(lines[index]):
        index += 1
    cleaned = "".join(lines[index:]).strip()
    return cleaned if cleaned else ""


def strip_interior_book_index(text: str) -> str:
    """Remove a long interior index (Índice general) that sits after front matter."""
    if not text or not text.strip():
        return text
    lines = text.splitlines(keepends=True)
    best: tuple[int, int] | None = None
    index = 0
    while index < len(lines):
        raw_line = lines[index]
        lower = raw_line.lower()
        starts_index = any(marker in lower for marker in _TOC_INDEX_MARKERS)
        if not raw_line.strip() or not (_is_toc_line(raw_line) or starts_index):
            index += 1
            continue
        end = index
        toc_count = 0
        in_index = starts_index
        while end < len(lines):
            current = lines[end]
            if _looks_like_body_prose(current) and not _is_toc_line(
                current, in_index=True
            ):
                break
            if current.strip() and any(
                marker in current.lower() for marker in _TOC_INDEX_MARKERS
            ):
                in_index = True
            if _is_toc_line(current, in_index=in_index) or not current.strip():
                if current.strip():
                    toc_count += 1
                end += 1
                continue
            fragment = current.strip()
            if (
                in_index
                and fragment
                and len(fragment) <= 110
                and not fragment.endswith((".", "!", "?"))
            ):
                toc_count += 1
                end += 1
                continue
            if _is_toc_continuation(current):
                toc_count += 1
                end += 1
                continue
            break
        if toc_count >= 8:
            if best is None or (end - index) > (best[1] - best[0]):
                best = (index, end)
        index = max(end, index + 1)
    if best is None:
        return text
    start, stop = best
    kept = "".join(lines[:start] + lines[stop:])
    if not kept.strip():
        return text
    removed = "".join(lines[start:stop]).lower()
    explicit_index = any(marker in removed for marker in _TOC_INDEX_MARKERS)
    if explicit_index:
        if len(kept.strip()) < 200:
            return text
        return kept.strip()
    removed_ratio = 1.0 - (len(kept) / max(1, len(text)))
    if removed_ratio > 0.92 and len(kept.strip()) < 400:
        return text
    return kept.strip()


_LAST_TOC_STRIP_STATS: dict[str, Any] = {
    "chars_before": 0,
    "chars_after": 0,
    "drop_ratio": 0.0,
    "applied": False,
    "reason": "none",
}


def last_toc_strip_stats() -> dict[str, Any]:
    return dict(_LAST_TOC_STRIP_STATS)


def _record_toc_stats(before: str, after: str, *, applied: bool, reason: str) -> str:
    before_n = len(before or "")
    after_n = len(after or "")
    drop = 1.0 - (after_n / max(1, before_n))
    _LAST_TOC_STRIP_STATS.update(
        {
            "chars_before": before_n,
            "chars_after": after_n,
            "drop_ratio": round(drop, 4),
            "applied": applied,
            "reason": reason,
        }
    )
    return after


def strip_document_front_matter_toc(text: str) -> str:
    """Remove front-matter TOC before the first developed body section.

    Generic TOC markers only. Language-specific body anchors are not used as
    a global rule. Drops above 35% without an explicit index marker are
    rejected so body prose is not deleted silently.
    """
    if not text or not text.strip():
        return _record_toc_stats(text or "", text or "", applied=False, reason="empty")

    original = text
    # Body anchors must not match TOC rows that end with leader dots + page number.
    body_anchors = (
        re.compile(
            r"(?im)^(?:\s*)(?:UNIDAD|UNIT|CAP[IÍ]TULO|CHAPTER)\s+1\b[^\n.]{0,80}$"
        ),
    )
    cleaned = None
    reason = "none"
    for anchor in body_anchors:
        match = anchor.search(text)
        if not match:
            continue
        heading_line = match.group().strip().splitlines()[-1]
        if (
            _TOC_LEADER.search(heading_line)
            or re.search(r"\.{3,}\s*\d+\s*$", heading_line)
            or _TOC_PAGE_LINE.search(heading_line)
        ):
            continue
        prefix = text[: match.start()]
        prefix_has_index = any(
            marker in prefix.lower() for marker in _TOC_INDEX_MARKERS
        )
        if not prefix_has_index:
            continue
        start = match.start()
        candidate = text[start:].strip()
        min_keep = min(400, max(120, int(len(original) * 0.10)))
        if len(candidate) >= min_keep:
            cleaned = candidate
            reason = "body_anchor_after_index"
            break

    if cleaned is None:
        stripped = strip_leading_toc(text)
        candidate = stripped if stripped else text
        interior = strip_interior_book_index(candidate)
        cleaned = interior if interior else text
        reason = "leading_or_interior_index"

    drop = 1.0 - (len(cleaned) / max(1, len(original)))
    explicit_index = any(marker in original.lower() for marker in _TOC_INDEX_MARKERS)
    if drop >= 0.70 and len((cleaned or "").strip()) < 400 and not explicit_index:
        return _record_toc_stats(
            original, original, applied=False, reason="drop_would_empty"
        )
    if drop >= 0.35 and not explicit_index:
        return _record_toc_stats(
            original, original, applied=False, reason="drop_ratio_without_index_marker"
        )
    if drop >= 0.35 and explicit_index:
        logger.warning(
            "TOC strip dropped %.1f%% of characters with an explicit index marker (reason=%s)",
            drop * 100,
            reason,
        )
    applied = cleaned.strip() != original.strip()
    return _record_toc_stats(original, cleaned, applied=applied, reason=reason)


def extract_document_outline(text: str, max_headings: int = 48) -> List[str]:
    """Deterministic outline extraction — no LLM call.

    Prefers Markdown headings; falls back to numbered section titles.
    """
    if not text or not text.strip():
        return []

    headings: List[str] = []
    seen: set[str] = set()

    for match in _MD_HEADING.finditer(text):
        label = f"{match.group(1)} {match.group(2).strip()}"
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        headings.append(label)
        if len(headings) >= max_headings:
            break

    if headings:
        return filter_reliable_outline(headings)

    for match in _NUMBERED_SECTION.finditer(text):
        label = f"{match.group(1)} {match.group(2).strip()}"
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        headings.append(label)
        if len(headings) >= max_headings:
            break

    return filter_reliable_outline(headings)


def outline_for_chunk(chunk: str, outline: Sequence[str]) -> List[str]:
    """Return outline entries whose title text appears in this chunk."""
    if not chunk or not outline:
        return []
    lowered = chunk.lower()
    matched: List[str] = []
    for entry in outline:
        title = entry.lstrip("#").strip()
        # Strip leading numbering for fuzzy presence check
        title_core = re.sub(r"^\d+(?:\.\d+)*\s*", "", title).strip()
        needle = title_core.lower() if title_core else title.lower()
        if needle and needle in lowered:
            matched.append(entry)
    return matched


_TOC_MAP_STUB_PREFIXES = (
    "índice únicamente",
    "indice unicamente",
    "index only",
    "apenas índice",
    "apenas indice",
    "solo indice",
    "solo índice",
    "nur inhaltsverzeichnis",
    "sommaire uniquement",
    "только оглавление",
    "목차만",
    "目次のみ",
    "仅目录",
    "فهرس فقط",
    "केवल अनुक्रमणिका",
)


def is_toc_map_stub(text: str) -> bool:
    """True when MAP output is the compact TOC stub, not developed content."""
    head = (text or "").lstrip().lower()[:96]
    return any(head.startswith(prefix) for prefix in _TOC_MAP_STUB_PREFIXES)


def format_coverage_checklist(outline: Sequence[str], language_prompts: Any) -> str:
    """Build an outline coverage checklist via the language prompt module.

    ``language_prompts`` is required — never falls back to another language.
    """
    if language_prompts is None:
        raise ValueError(
            "language_prompts is required; do not fall back to a default language"
        )
    return language_prompts.get_coverage_checklist(outline)
