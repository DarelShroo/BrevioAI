"""Contract for whether a generated summary may be delivered as COMPLETED.

Chunk-ID presence, a non-empty file, and finish_reason=stop are not enough.
This module inspects the real artifact text and the pipeline's size signals.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterable, Optional, Sequence

from core.brevio.enums.summary_level import SummaryLevel

EncodeFn = Callable[[str], int]


class ArtifactVerdict(str, Enum):
    VALID = "VALID"
    DEGRADED = "DEGRADED"
    SALVAGED = "SALVAGED"
    INVALID = "INVALID"


# Hierarchical floor: final words / MAP words. Below this is catastrophic collapse.
_MAP_KEEP_FLOOR = {
    SummaryLevel.VERY_CONCISE: 0.10,
    SummaryLevel.CONCISE: 0.16,
    SummaryLevel.MODERATE: 0.22,
    SummaryLevel.DETAILED: 0.28,
    SummaryLevel.VERY_DETAILED: 0.35,
}

# Floor vs source words. Long books cannot keep 28% of tokens in one 8k call;
# this is a *safety* floor against menus and stubs, not the retention target.
_SOURCE_KEEP_FLOOR = {
    SummaryLevel.VERY_CONCISE: 0.012,
    SummaryLevel.CONCISE: 0.02,
    SummaryLevel.MODERATE: 0.035,
    SummaryLevel.DETAILED: 0.05,
    SummaryLevel.VERY_DETAILED: 0.07,
}

# Fail if artifact tokens < this fraction of declared output_min_tokens.
_OUTPUT_MIN_FRACTION = 0.40

_ABSOLUTE_MIN_WORDS = {
    SummaryLevel.VERY_CONCISE: 80,
    SummaryLevel.CONCISE: 120,
    SummaryLevel.MODERATE: 180,
    SummaryLevel.DETAILED: 260,
    SummaryLevel.VERY_DETAILED: 340,
}

_HELP_PHRASES = (
    "¿qué necesitas?",
    "que necesitas?",
    "qué necesitas?",
    "what do you need?",
    "how can i help",
    "cómo puedo ayudarte",
    "como puedo ayudarte",
    "en qué puedo ayudarte",
    "en que puedo ayudarte",
    "estoy aquí para ayudarte",
    "estoy aqui para ayudarte",
    "i'm here to help",
    "i am here to help",
    "opciones para ayudarte",
    "please tell me which",
    "especifica una",
    "dime qué necesitas",
    "dime que necesitas",
    "¿en qué puedo ayudarte?",
    "gracias por compartir",
    "basado en los fragmentos proporcionados",
    "aquí tienes una síntesis estructurada de lo que podría estar buscando",
    "estoy aquí para ayudarte",
)

_MENU_HEADINGS = (
    "opciones para ayudarte",
    "options to help you",
    "how can i assist",
    "menú de opciones",
    "option menu",
)

_CODE_EXT = re.compile(
    r"\.(py|js|ts|jsx|tsx|java|go|rs|c|h|cpp|hpp|rb|php|sh|md|txt|json|yml|yaml|toml)\s*$",
    re.IGNORECASE,
)
_CITATION_YEAR = re.compile(r"\((?:19|20)\d{2}\)")
_PAGE_CITE = re.compile(r"\bp\.\s*\d+", re.IGNORECASE)
_INITIAL_NAME = re.compile(r"^[A-ZÁÉÍÓÚÑ]\.\s+[A-ZÁÉÍÓÚÑ]")
_CAPTION = re.compile(
    r"(?i)^(ilustraci[oó]n|figure|figura|table|tabla|photo|image|imagen)\b"
)
_RUNNING_HEADER = re.compile(
    r"(?i)^(aula mentor|isbn\b|www\.|http|\d+\s+mario bunge)\b"
)


def count_words(text: str) -> int:
    return len((text or "").split())


def _safe_int(value, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def approximate_tokens(text: str, encode: Optional[EncodeFn] = None) -> int:
    if encode is not None:
        try:
            return max(0, int(encode(text or "")))
        except Exception:
            pass
    return max(0, len(text or "") // 4)


def assistant_chat_score(text: str) -> float:
    """Structural score in [0, 1]. High means help-desk / menu, not a summary."""
    if not text or not text.strip():
        return 0.0
    sample = text.lower()
    score = 0.0
    phrase_hits = sum(1 for marker in _HELP_PHRASES if marker in sample)
    if phrase_hits:
        score += min(0.55, 0.22 * phrase_hits)
    if any(heading in sample for heading in _MENU_HEADINGS):
        score += 0.25
    questions = sample.count("?")
    words = max(1, count_words(text))
    if questions >= 3 and words < 800:
        score += 0.15
    if questions >= 2 and re.search(
        r"(?i)(opción|option|elige|choose|especifica|tell me which)", sample
    ):
        score += 0.2
    numbered_options = len(re.findall(r"(?m)^\s*(?:\d+[\.\)]\s+|\*\*\d+\.)", text))
    if numbered_options >= 3 and words < 600:
        score += 0.2
    if re.search(
        r"(?i)\b(estoy aqu[ií] para|i can help you|what do you need)\b", sample
    ):
        score += 0.15
    if re.search(r"(?i)^(hi|hola|hello|hey)\b", sample.strip()[:40]):
        score += 0.1
    return min(1.0, score)


def looks_like_assistant_chat(text: str) -> bool:
    return assistant_chat_score(text) >= 0.35


def looks_truncated(text: str) -> bool:
    stripped = (text or "").rstrip()
    if not stripped:
        return True
    if stripped.endswith(("[texto truncado]", "[truncated]", "...[cut]")):
        return True
    last = next(
        (line.strip() for line in reversed(stripped.splitlines()) if line.strip()), ""
    )
    if last.endswith("-") and len(last.split()) >= 4:
        return True
    if last.endswith(",") and len(last.split()) >= 8:
        return True
    return False


def is_reliable_outline_entry(label: str) -> bool:
    """Reject code filenames, captions, footnotes, and running headers."""
    if not label or not str(label).strip():
        return False
    title = str(label).lstrip("#").strip()
    title_core = re.sub(r"^\d+(?:\.\d+)*\s*", "", title).strip()
    if len(title_core) < 8:
        return False
    if _CODE_EXT.search(title_core):
        return False
    if _CAPTION.match(title_core):
        return False
    if _RUNNING_HEADER.match(title_core):
        return False
    if _CITATION_YEAR.search(title_core) or _PAGE_CITE.search(title_core):
        return False
    if _INITIAL_NAME.match(title_core):
        return False
    if title_core.count(",") >= 2 and len(title_core) > 90:
        return False
    return True


def filter_reliable_outline(entries: Sequence[str], *, min_keep: int = 2) -> list[str]:
    kept: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        if not is_reliable_outline_entry(entry):
            continue
        key = re.sub(r"\s+", " ", entry).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        kept.append(entry)
    if len(kept) < min_keep:
        return []
    return kept


@dataclass(frozen=True)
class QualitySignals:
    source_tokens: int = 0
    source_words: int = 0
    map_tokens: int = 0
    map_words: int = 0
    final_tokens: int = 0
    final_words: int = 0
    output_min_tokens: int = 0
    output_target_tokens: int = 0
    output_hard_limit: int = 0
    summary_level: SummaryLevel = SummaryLevel.MODERATE
    route: str = "hierarchical"
    pages_dropped: int = 0
    pages_total: int = 0
    toc_drop_ratio: float = 0.0


@dataclass
class QualityReport:
    verdict: ArtifactVerdict
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    chatbot_score: float = 0.0
    map_ratio: float = 0.0
    source_ratio: float = 0.0
    min_token_ratio: float = 0.0
    salvage_source: str = ""
    signals: QualitySignals = field(default_factory=QualitySignals)

    @property
    def deliverable(self) -> bool:
        return self.verdict in {
            ArtifactVerdict.VALID,
            ArtifactVerdict.DEGRADED,
            ArtifactVerdict.SALVAGED,
        }


def _level(value: SummaryLevel | str | None) -> SummaryLevel:
    if isinstance(value, SummaryLevel):
        return value
    if value is None or value == "":
        return SummaryLevel.MODERATE
    try:
        return SummaryLevel(str(value))
    except Exception:
        try:
            return SummaryLevel[str(value).upper()]
        except Exception:
            return SummaryLevel.MODERATE


def evaluate_artifact(
    text: str,
    signals: QualitySignals,
    *,
    encode: Optional[EncodeFn] = None,
    salvage_source: str = "",
) -> QualityReport:
    """Judge the text that would be committed to summary.md."""
    level = _level(signals.summary_level)
    reasons: list[str] = []
    warnings: list[str] = []
    body = text or ""
    words = count_words(body)
    tokens = signals.final_tokens or approximate_tokens(body, encode)
    chatbot = assistant_chat_score(body)
    truncated = looks_truncated(body)

    map_words = max(0, _safe_int(signals.map_words))
    source_words = max(0, _safe_int(signals.source_words))
    map_ratio = (words / map_words) if map_words else 1.0
    source_ratio = (words / source_words) if source_words else 1.0
    min_tokens = max(0, _safe_int(signals.output_min_tokens))
    min_token_ratio = (tokens / min_tokens) if min_tokens else 1.0

    if not body.strip():
        reasons.append("empty_artifact")
    if chatbot >= 0.35:
        reasons.append("assistant_chat")
    if truncated and words < max(_ABSOLUTE_MIN_WORDS[level] * 3, 400):
        reasons.append("truncated_tail")

    substantial_source = source_words >= 800 or map_words >= 400
    if substantial_source:
        abs_min = _ABSOLUTE_MIN_WORDS[level]
        if words < abs_min:
            reasons.append(f"below_absolute_min_words:{words}<{abs_min}")

        if map_words >= 400 and signals.route != "direct":
            floor = _MAP_KEEP_FLOOR[level]
            if map_ratio < floor:
                reasons.append(f"map_collapse:{map_ratio:.3f}<{floor}")
        if source_words >= 1500:
            floor = _SOURCE_KEEP_FLOOR[level]
            if source_ratio < floor:
                reasons.append(f"source_collapse:{source_ratio:.3f}<{floor}")
        if min_tokens >= 400:
            cap = _safe_int(signals.output_hard_limit) or min_tokens
            enforce_min = min(min_tokens, cap)
            if tokens < int(enforce_min * _OUTPUT_MIN_FRACTION):
                reasons.append(
                    f"below_output_min:{tokens}<{int(enforce_min * _OUTPUT_MIN_FRACTION)}"
                )

    if signals.pages_total and signals.pages_dropped:
        dropped_ratio = signals.pages_dropped / max(1, signals.pages_total)
        if dropped_ratio >= 0.25:
            warnings.append(f"pages_dropped_ratio:{dropped_ratio:.2f}")
        elif dropped_ratio > 0:
            warnings.append(f"pages_dropped:{signals.pages_dropped}")
    if signals.toc_drop_ratio >= 0.35:
        warnings.append(f"toc_drop_ratio:{signals.toc_drop_ratio:.2f}")

    if reasons:
        verdict = ArtifactVerdict.INVALID
    elif warnings:
        verdict = ArtifactVerdict.DEGRADED
    else:
        verdict = ArtifactVerdict.VALID

    if salvage_source:
        verdict = (
            ArtifactVerdict.SALVAGED if verdict != ArtifactVerdict.INVALID else verdict
        )

    return QualityReport(
        verdict=verdict,
        reasons=reasons,
        warnings=warnings,
        chatbot_score=chatbot,
        map_ratio=map_ratio,
        source_ratio=source_ratio,
        min_token_ratio=min_token_ratio,
        salvage_source=salvage_source,
        signals=signals,
    )


def choose_deliverable_text(
    candidates: Iterable[tuple[str, str]],
    base_signals: QualitySignals,
    *,
    encode: Optional[EncodeFn] = None,
) -> tuple[str, QualityReport]:
    """Pick the first candidate that is deliverable.

    ``candidates`` are (label, text) in preference order, typically
    ``proposed`` then ``pre_final`` then ``map_extracts``.
    """
    ordered = list(candidates)
    reports: list[tuple[str, str, QualityReport]] = []
    for label, text in ordered:
        signals = QualitySignals(
            source_tokens=base_signals.source_tokens,
            source_words=base_signals.source_words,
            map_tokens=base_signals.map_tokens,
            map_words=base_signals.map_words,
            final_tokens=approximate_tokens(text, encode),
            final_words=count_words(text),
            output_min_tokens=_safe_int(base_signals.output_min_tokens),
            output_target_tokens=base_signals.output_target_tokens,
            output_hard_limit=_safe_int(base_signals.output_hard_limit),
            summary_level=base_signals.summary_level,
            route=base_signals.route,
            pages_dropped=base_signals.pages_dropped,
            pages_total=base_signals.pages_total,
            toc_drop_ratio=base_signals.toc_drop_ratio,
        )
        salvage = "" if label == "proposed" else label
        report = evaluate_artifact(text, signals, encode=encode, salvage_source=salvage)
        reports.append((label, text, report))
        if report.deliverable and "assistant_chat" not in report.reasons:
            if salvage:
                report.verdict = ArtifactVerdict.SALVAGED
                report.salvage_source = label
            return text, report

    # Nothing deliverable: return the proposed text with its INVALID report.
    if reports:
        label, text, report = reports[0]
        report.verdict = ArtifactVerdict.INVALID
        return text, report
    empty = evaluate_artifact("", base_signals, encode=encode)
    empty.reasons.append("no_candidates")
    return "", empty
