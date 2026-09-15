from __future__ import annotations

import argparse
import json
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

import httpx
import tiktoken
from dotenv import load_dotenv

from .runtime import _ollama_native_url, capture_ollama_runtime

_ENCODER = tiktoken.get_encoding("cl100k_base")
_MARKDOWN = re.compile(r"[*_`>#|]+")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÜÑ0-9])")
_NUMBER = re.compile(
    r"(?<![\w.])(?:\d{1,4}(?:[.,]\d{3})*(?:[.,]\d+)?%?|"
    r"\d+(?:st|nd|rd|th))(?!\w)",
    re.IGNORECASE,
)
_DATE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:19|20)\d{2}|"
    r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|"
    r"octubre|noviembre|diciembre|january|february|march|april|may|june|"
    r"july|august|september|october|november|december)\s+\d{1,4})\b",
    re.IGNORECASE,
)

_SEGMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "fact": {"type": "string"},
                    "source_evidence": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": [
                            "fact",
                            "number",
                            "date",
                            "entity",
                            "relation",
                            "conclusion",
                            "definition",
                        ],
                    },
                    "section": {"type": "string"},
                    "importance": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 3,
                    },
                    "coverage": {
                        "type": "string",
                        "enum": ["full", "partial", "missing"],
                    },
                    "summary_evidence": {"type": "string"},
                },
                "required": [
                    "fact",
                    "source_evidence",
                    "kind",
                    "section",
                    "importance",
                    "coverage",
                    "summary_evidence",
                ],
            },
        },
        "supported_claim_ids": {
            "type": "array",
            "items": {"type": "string"},
        },
        "partially_supported_claim_ids": {
            "type": "array",
            "items": {"type": "string"},
        },
        "contradictions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string"},
                    "source_evidence": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["claim_id", "source_evidence", "reason"],
            },
        },
        "linguistic_quality": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
        },
        "coherence": {"type": "number", "minimum": 0, "maximum": 100},
        "structure": {"type": "number", "minimum": 0, "maximum": 100},
        "language_adherence": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
        },
        "summary_level_adherence": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
        },
        "category_adherence": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
        },
        "style_adherence": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
        },
        "format_adherence": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
        },
        "rubric_evidence": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "facts",
        "supported_claim_ids",
        "partially_supported_claim_ids",
        "contradictions",
        "linguistic_quality",
        "coherence",
        "structure",
        "language_adherence",
        "summary_level_adherence",
        "category_adherence",
        "style_adherence",
        "format_adherence",
        "rubric_evidence",
    ],
}


def _clean_claim(text: str) -> str:
    text = _MARKDOWN.sub(" ", text)
    text = re.sub(r"^\s*(?:[-+•]|\d+[.)])\s*", "", text)
    return re.sub(r"\s+", " ", text).strip(" -:;\t")


def extract_claims(summary: str, *, limit: int = 160) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_line in summary.splitlines():
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


def _split_tokens(text: str, max_tokens: int) -> list[str]:
    tokens = _ENCODER.encode(text)
    if not tokens:
        return []
    return [
        _ENCODER.decode(tokens[index : index + max_tokens])
        for index in range(0, len(tokens), max_tokens)
    ]


def _artifact_path(raw: str, repository_root: Path) -> Path:
    path = Path(raw)
    if path.is_file():
        return path
    if path.is_absolute() and path.parts[:2] == ("/", "workspace"):
        candidate = repository_root.joinpath(*path.parts[2:])
        if candidate.is_file():
            return candidate
    candidate = repository_root / path
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(raw)


def _json_from_content(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError("Judge returned a non-object JSON value")
    return payload


def _judge_segment(
    *,
    model: str,
    source_segment: str,
    summary: str,
    claims: list[dict[str, Any]],
    config: dict[str, str],
    source_index: int,
    source_total: int,
    timeout: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    rubric = f"""
You are a strict document-summary evaluator. Compare the ORIGINAL SOURCE SEGMENT
against the COMPLETE GENERATED SUMMARY. Use no external knowledge.

Configuration:
- summary_level: {config.get("summary_level")}
- category: {config.get("category")}
- style: {config.get("style")}
- requested language: {config.get("language")}
- requested format: {config.get("output_format")}

Rules:
1. Extract at most 12 distinct source facts that are important for the requested
   summary_level. For very_concise retain only pillars and indispensable
   conclusions; for moderate include major arguments, definitions, relations,
   and representative evidence; for very_detailed include all materially
   relevant details in this segment.
2. Quote short exact source evidence for every fact.
3. Mark each fact full, partial, or missing in the summary and quote summary
   evidence when present.
4. A summary claim is supported only when this source segment directly entails
   it. Do not accept plausibility, common knowledge, or a nearby but different
   number/name/relation.
5. Mark a contradiction only with explicit opposite or incompatible source
   evidence. Unsupported is not automatically contradiction.
6. Score language, linguistic quality, coherence, structure, summary-level,
   category, style, and format conservatively. Scores above 95 require no
   material defect. The same document is being assessed over several source
   segments, so those rubric scores must judge the complete summary itself.
7. Return only JSON matching the supplied schema.

This is source segment {source_index + 1} of {source_total}.
""".strip()
    user_content = (
        "ORIGINAL SOURCE SEGMENT:\n"
        f"{source_segment}\n\n"
        "COMPLETE GENERATED SUMMARY:\n"
        f"{summary}\n\n"
        "ATOMIC SUMMARY CLAIMS:\n"
        f"{json.dumps(claims, ensure_ascii=False)}"
    )
    payload = {
        "model": model,
        "stream": False,
        "think": False,
        "format": _SEGMENT_SCHEMA,
        "messages": [
            {"role": "system", "content": rubric},
            {"role": "user", "content": user_content},
        ],
        "options": {
            "temperature": 0,
            "seed": 17,
            "num_ctx": 16_384,
            "num_predict": 2_048,
        },
    }
    started = time.monotonic()
    with httpx.Client(timeout=timeout) as client:
        response = client.post(_ollama_native_url("/api/chat"), json=payload)
        response.raise_for_status()
        raw = response.json()
    elapsed = time.monotonic() - started
    result = _json_from_content(str((raw.get("message") or {}).get("content") or ""))
    telemetry = {
        "duration_seconds": round(elapsed, 3),
        "prompt_tokens": int(raw.get("prompt_eval_count") or 0),
        "output_tokens": int(raw.get("eval_count") or 0),
        "done_reason": str(raw.get("done_reason") or ""),
        "source_segment": source_index,
    }
    return result, telemetry


def _weighted_score(
    facts: Iterable[dict[str, Any]],
    *,
    kinds: set[str] | None = None,
) -> float | None:
    selected = [
        fact
        for fact in facts
        if kinds is None or str(fact.get("kind") or "") in kinds
    ]
    denominator = sum(max(1, int(fact.get("importance") or 1)) for fact in selected)
    if denominator <= 0:
        return None
    values = {"full": 1.0, "partial": 0.5, "missing": 0.0}
    numerator = sum(
        max(1, int(fact.get("importance") or 1))
        * values.get(str(fact.get("coverage") or ""), 0.0)
        for fact in selected
    )
    return round(100.0 * numerator / denominator, 2)


def _mean(values: Iterable[float]) -> float:
    items = list(values)
    return round(sum(items) / len(items), 2) if items else 0.0


def _claim_support_scores(
    claims: list[dict[str, Any]],
    supported: set[str],
    partial: set[str],
    contradicted: set[str],
) -> tuple[float, float, float, list[str]]:
    total = sum(int(claim["importance"]) for claim in claims) or 1
    support_weight = 0.0
    unsupported: list[str] = []
    contradiction_weight = 0
    for claim in claims:
        claim_id = str(claim["id"])
        weight = int(claim["importance"])
        if claim_id in contradicted:
            contradiction_weight += weight
        if claim_id in supported:
            support_weight += weight
        elif claim_id in partial:
            support_weight += 0.5 * weight
        else:
            unsupported.append(claim_id)
    fidelity = 100.0 * support_weight / total
    hallucination_free = 100.0 * (
        1.0
        - sum(
            int(claim["importance"])
            for claim in claims
            if claim["id"] in unsupported
        )
        / total
    )
    contradiction_free = 100.0 * (1.0 - contradiction_weight / total)
    return (
        round(fidelity, 2),
        round(max(0.0, hallucination_free), 2),
        round(max(0.0, contradiction_free), 2),
        unsupported,
    )


def _hard_failures(scores: dict[str, float], truncation: bool) -> list[str]:
    failures: list[str] = []
    if truncation:
        failures.append("provider_truncation")
    thresholds = {
        "fidelity": 90,
        "coverage": 85,
        "completeness": 85,
        "hallucinations": 95,
        "contradictions": 95,
        "language": 95,
        "configuration": 90,
    }
    for field, threshold in thresholds.items():
        if float(scores.get(field, 0)) < threshold:
            failures.append(f"{field}_below_{threshold}")
    return failures


def evaluate_record(
    record: dict[str, Any],
    *,
    repository_root: Path,
    model: str,
    timeout: float = 900.0,
) -> dict[str, Any]:
    if record.get("error"):
        raise ValueError(f"Cannot evaluate failed experiment: {record['error']}")
    source_path = _artifact_path(
        str((record.get("source") or {}).get("extracted_path") or ""),
        repository_root,
    )
    summary_path = _artifact_path(
        str(record.get("summary_path") or ""),
        repository_root,
    )
    source = source_path.read_text(encoding="utf-8")
    summary = summary_path.read_text(encoding="utf-8")
    claims = extract_claims(summary)
    if not claims:
        raise ValueError("Generated summary contains no evaluable claims")

    summary_tokens = len(_ENCODER.encode(summary))
    claims_tokens = len(_ENCODER.encode(json.dumps(claims, ensure_ascii=False)))
    source_chunk_tokens = max(
        1_500,
        min(4_500, 16_384 - 2_048 - 1_800 - summary_tokens - claims_tokens),
    )
    segments = _split_tokens(source, source_chunk_tokens)
    results: list[dict[str, Any]] = []
    telemetry: list[dict[str, Any]] = []
    for index, segment in enumerate(segments):
        result, call_telemetry = _judge_segment(
            model=model,
            source_segment=segment,
            summary=summary,
            claims=claims,
            config=dict(record.get("config") or {}),
            source_index=index,
            source_total=len(segments),
            timeout=timeout,
        )
        results.append(result)
        telemetry.append(call_telemetry)

    supported: set[str] = set()
    partial: set[str] = set()
    contradictions: dict[str, list[dict[str, str]]] = defaultdict(list)
    facts: list[dict[str, Any]] = []
    for index, result in enumerate(results):
        supported.update(str(item) for item in result.get("supported_claim_ids") or [])
        partial.update(
            str(item)
            for item in result.get("partially_supported_claim_ids") or []
        )
        for item in result.get("contradictions") or []:
            claim_id = str(item.get("claim_id") or "")
            if claim_id:
                contradictions[claim_id].append(dict(item))
        for fact in result.get("facts") or []:
            stored = dict(fact)
            stored["source_segment"] = index
            facts.append(stored)
    partial -= supported

    fidelity, hallucinations, contradiction_free, unsupported = (
        _claim_support_scores(
            claims,
            supported,
            partial,
            set(contradictions),
        )
    )
    coverage = _weighted_score(facts) or 0.0
    critical_scores = {
        "numbers": _weighted_score(facts, kinds={"number"}),
        "dates": _weighted_score(facts, kinds={"date"}),
        "entities": _weighted_score(facts, kinds={"entity"}),
        "relations": _weighted_score(facts, kinds={"relation"}),
        "conclusions": _weighted_score(facts, kinds={"conclusion"}),
        "definitions": _weighted_score(facts, kinds={"definition"}),
    }
    available_critical = [
        float(value) for value in critical_scores.values() if value is not None
    ]
    critical_data = _mean(available_critical) if available_critical else coverage
    completeness = round(0.72 * coverage + 0.28 * critical_data, 2)

    sections: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in facts:
        section = str(fact.get("section") or "").strip() or "unlabelled"
        sections[section].append(fact)
    represented_sections = sum(
        1
        for items in sections.values()
        if any(item.get("coverage") in {"full", "partial"} for item in items)
    )
    structural_coverage = round(
        100.0 * represented_sections / max(1, len(sections)),
        2,
    )

    linguistic = _mean(
        float(result.get("linguistic_quality") or 0) for result in results
    )
    coherence = _mean(float(result.get("coherence") or 0) for result in results)
    structure = _mean(float(result.get("structure") or 0) for result in results)
    language = _mean(
        float(result.get("language_adherence") or 0) for result in results
    )
    summary_level = _mean(
        float(result.get("summary_level_adherence") or 0)
        for result in results
    )
    category = _mean(
        float(result.get("category_adherence") or 0) for result in results
    )
    style = _mean(
        float(result.get("style_adherence") or 0) for result in results
    )
    output_format = _mean(
        float(result.get("format_adherence") or 0) for result in results
    )
    configuration = round(
        0.30 * language
        + 0.25 * summary_level
        + 0.15 * category
        + 0.15 * style
        + 0.15 * output_format,
        2,
    )

    scores = {
        "fidelity": fidelity,
        "coverage": coverage,
        "completeness": completeness,
        "hallucinations": hallucinations,
        "contradictions": contradiction_free,
        "critical_data": critical_data,
        "linguistic": linguistic,
        "coherence": coherence,
        "structure": structure,
        "configuration": configuration,
        "summary_level": summary_level,
        "category": category,
        "style": style,
        "language": language,
        "format": output_format,
        "structural_coverage": structural_coverage,
    }
    raw_overall = (
        0.20 * fidelity
        + 0.15 * coverage
        + 0.10 * completeness
        + 0.15 * hallucinations
        + 0.10 * contradiction_free
        + 0.08 * critical_data
        + 0.07 * linguistic
        + 0.05 * coherence
        + 0.05 * structure
        + 0.05 * configuration
    )
    truncation = bool((record.get("telemetry") or {}).get("truncation_detected"))
    failures = _hard_failures(scores, truncation)
    overall = raw_overall
    if "provider_truncation" in failures:
        overall = min(overall, 59.0)
    elif any(
        item.startswith(("hallucinations_", "contradictions_", "language_"))
        for item in failures
    ):
        overall = min(overall, 79.0)
    elif failures:
        overall = min(overall, 89.0)
    scores["overall"] = round(overall, 2)

    source_tokens = len(_ENCODER.encode(source))
    covered_weight = sum(
        max(1, int(fact.get("importance") or 1))
        * {"full": 1.0, "partial": 0.5}.get(
            str(fact.get("coverage") or ""), 0.0
        )
        for fact in facts
    )
    evidence = {
        "claims": claims,
        "supported_claim_ids": sorted(supported),
        "partially_supported_claim_ids": sorted(partial),
        "unsupported_claim_ids": unsupported,
        "contradictions": dict(contradictions),
        "source_facts": facts,
        "critical_scores": critical_scores,
        "rubric_evidence": [
            item
            for result in results
            for item in (result.get("rubric_evidence") or [])
        ],
    }
    return {
        **scores,
        "hard_failures": failures,
        "excellent": scores["overall"] >= 95 and not failures,
        "evidence": evidence,
        "efficiency": {
            "source_tokens": source_tokens,
            "summary_tokens": summary_tokens,
            "compression_ratio": round(summary_tokens / max(1, source_tokens), 4),
            "information_density_weight_per_1k_summary_tokens": round(
                1_000.0 * covered_weight / max(1, summary_tokens),
                3,
            ),
            "judge_calls": len(telemetry),
            "judge_input_tokens": sum(item["prompt_tokens"] for item in telemetry),
            "judge_output_tokens": sum(item["output_tokens"] for item in telemetry),
            "judge_seconds": round(
                sum(item["duration_seconds"] for item in telemetry),
                3,
            ),
        },
        "judge_telemetry": telemetry,
    }


def evaluate_iteration(
    iteration_path: Path,
    *,
    output_path: Path | None = None,
    model: str = "qwen3:14b",
    only_documents: Sequence[str] = (),
) -> dict[str, Any]:
    repository_root = Path(__file__).resolve().parents[2]
    payload = json.loads(iteration_path.read_text(encoding="utf-8"))
    selected = set(only_documents)
    evaluated = 0
    failures = 0
    for record in payload.get("experiments") or []:
        if selected and str(record.get("document") or "") not in selected:
            continue
        try:
            semantic = evaluate_record(
                record,
                repository_root=repository_root,
                model=model,
            )
            record["quality_deterministic"] = record.get("quality") or {}
            record["quality"] = semantic
            evaluated += 1
        except Exception as exc:
            record["semantic_evaluation_error"] = (
                f"{type(exc).__name__}: {exc}"
            )
            failures += 1
    quality_rows = [
        row.get("quality") or {}
        for row in payload.get("experiments") or []
        if row.get("quality") and not row.get("semantic_evaluation_error")
    ]
    fields = (
        "overall",
        "fidelity",
        "coverage",
        "completeness",
        "hallucinations",
        "contradictions",
        "critical_data",
        "linguistic",
        "coherence",
        "structure",
        "configuration",
        "summary_level",
        "category",
        "style",
        "language",
        "format",
        "structural_coverage",
    )
    payload["semantic_evaluation"] = {
        "model": model,
        "runtime": capture_ollama_runtime(model),
        "evaluated": evaluated,
        "failed": failures,
        "aggregates": {
            field: _mean(float(row.get(field) or 0) for row in quality_rows)
            for field in fields
        },
        "hard_failures": sum(
            bool(row.get("hard_failures")) for row in quality_rows
        ),
    }
    destination = output_path or iteration_path.with_name(
        f"{iteration_path.stem}_evaluated.json"
    )
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate real Brevio summaries against original documents."
    )
    parser.add_argument("iteration", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model", default="qwen3:14b")
    parser.add_argument("--document", action="append", default=[])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    repository_root = Path(__file__).resolve().parents[2]
    load_dotenv(repository_root / ".env")
    args = _parser().parse_args(argv)
    payload = evaluate_iteration(
        args.iteration,
        output_path=args.output,
        model=args.model,
        only_documents=args.document,
    )
    report = payload["semantic_evaluation"]
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 2 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
