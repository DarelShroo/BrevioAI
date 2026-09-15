from __future__ import annotations

import re
from typing import Any

from .models import BenchmarkConfig, HeuristicLint, TelemetrySnapshot

_CHATBOT_PATTERNS = (
    r"¿qué necesitas\?",
    r"qué necesitas\?",
    r"estoy aquí para ayudarte",
    r"estoy aqui para ayudarte",
    r"cómo puedo ayudarte",
    r"como puedo ayudarte",
    r"en qué puedo ayudarte",
    r"opciones para ayudarte",
    r"gracias por compartir esta información",
    r"how can i help you",
    r"what do you need\?",
    r"let me know what you'd like",
    r"especifica una",
)
_FIRST_PERSON = re.compile(
    r"\b(aprend[ií]|necesito|me ayudaría|yo creo|en mi opinión|"
    r"i learned|i think|we will learn)\b",
    re.IGNORECASE,
)
_SPANISH_MARKERS = (
    " el ", " la ", " los ", " las ", " que ", " para ", " con ", " una ",
)
_ENGLISH_MARKERS = (
    " the ", " and ", " of ", " to ", " in ", " is ", " for ", " with ",
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def detect_language(text: str) -> str:
    blob = (text or "").strip()
    if not blob:
        return "und"
    try:
        from langdetect import DetectorFactory, detect

        DetectorFactory.seed = 0
        code = detect(blob)
    except Exception:
        padded = f" {_norm(blob)} "
        es = sum(padded.count(m) for m in _SPANISH_MARKERS)
        en = sum(padded.count(m) for m in _ENGLISH_MARKERS)
        if es == 0 and en == 0:
            return "und"
        return "spanish" if es >= en else "english"
    mapping = {
        "es": "spanish",
        "en": "english",
        "fr": "french",
        "de": "german",
        "it": "italian",
        "pt": "portuguese",
        "zh-cn": "chinese",
        "ja": "japanese",
        "ko": "korean",
        "ru": "russian",
        "ar": "arabic",
        "hi": "hindi",
    }
    return mapping.get(code, code)


def requested_language_name(requested: str) -> str:
    value = (requested or "spanish").strip().lower()
    if value in {"es", "spanish", "español", "espanol"}:
        return "spanish"
    if value in {"en", "english"}:
        return "english"
    return value


def chatbot_signals(summary: str) -> list[str]:
    text = _norm(summary)
    hits: list[str] = []
    for pattern in _CHATBOT_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(pattern)
    questions_to_user = len(
        re.findall(r"\b(dime|especifica|elije|elige|tell me|let me know)\b", text)
    )
    if questions_to_user >= 2:
        hits.append("user_prompt_questions")
    if "😊" in (summary or "") or "🙂" in (summary or ""):
        hits.append("assistant_emoji")
    return hits


def copy_ratio(source: str, summary: str) -> float | None:
    source_words = (source or "").split()
    summary_words = (summary or "").split()
    if not source_words or not summary_words:
        return None
    if len(summary_words) < 40:
        return 0.0
    src_ngrams = _ngrams(source_words, 8)
    sum_ngrams = _ngrams(summary_words, 8)
    if not sum_ngrams:
        return round(len(summary_words) / max(1, len(source_words)), 4)
    overlap = len(src_ngrams & sum_ngrams) / max(1, len(sum_ngrams))
    length_ratio = len(summary_words) / max(1, len(source_words))
    # A dump is long AND verbatim. Short quotations are not automatic wins
    # or automatic failures; they scale with how much of the source was copied.
    dump = overlap * length_ratio / 0.15
    return round(min(1.0, dump), 4)


def _ngrams(words: list[str], size: int) -> set[tuple[str, ...]]:
    lowered = [word.casefold() for word in words]
    if len(lowered) < size:
        return set()
    return {tuple(lowered[i : i + size]) for i in range(0, len(lowered) - size + 1)}


def evaluate_lint(
    *,
    source_text: str,
    summary: str,
    config: BenchmarkConfig,
    telemetry: TelemetrySnapshot | None = None,
) -> HeuristicLint:
    summary = summary or ""
    source_text = source_text or ""
    notes: list[str] = []
    chatbot = chatbot_signals(summary)
    detected = detect_language(summary) if summary.strip() else "und"
    requested = requested_language_name(config.language)
    language_score: float | None
    if not summary.strip():
        language_score = None
        notes.append("empty-summary")
    elif detected == "und":
        language_score = 50.0
        notes.append("language-undetermined")
    elif detected == requested:
        language_score = 100.0
    else:
        language_score = 0.0
        notes.append(f"language mismatch: detected={detected} requested={requested}")
    truncation: list[str] = []
    if telemetry and telemetry.truncation_detected:
        truncation.append("provider_truncation_flag")
    history = (telemetry.history_tokens_per_call if telemetry else None) or []
    for call in history:
        if str(call.get("finish_reason") or "") in {"length", "max_tokens"}:
            if call.get("is_final_reduce") or str(call.get("type_call")) == "reduce":
                truncation.append(
                    f"finish_reason={call.get('finish_reason')} "
                    f"reduce_level={call.get('reduce_level')}"
                )
    stripped = summary.rstrip()
    if stripped.endswith(("...", "[", "—")) or "[texto truncado]" in summary.lower():
        truncation.append("artifact_ellipsis")
    ratio = copy_ratio(source_text, summary)
    headings = sum(1 for ln in summary.splitlines() if ln.lstrip().startswith("#"))
    lint = HeuristicLint(
        language_label=detected,
        language_score=language_score,
        chatbot_score=min(100.0, 25.0 * len(chatbot)),
        copy_ratio=ratio,
        truncation_signals=sorted(set(truncation)),
        first_person=bool(_FIRST_PERSON.search(summary)),
        markdown_headings=headings,
        summary_words=len(summary.split()),
        source_words=len(source_text.split()),
        notes=notes + [f"chatbot:{item}" for item in chatbot],
    )
    return lint
