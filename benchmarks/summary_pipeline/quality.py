from __future__ import annotations

from typing import Any

from .claims import claim_supported_by_source, extract_claims, extract_numbers
from .gold import gold_for_document, match_key_claims, match_numbers, match_topics
from .lint import HeuristicLint, evaluate_lint
from .models import BenchmarkConfig, QualityVector, TelemetrySnapshot


def _clip(value: float) -> float:
    return max(0.0, min(100.0, value))


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def evaluate_quality(
    *,
    source_text: str,
    summary: str,
    config: BenchmarkConfig,
    document_name: str,
    telemetry: TelemetrySnapshot | None = None,
    lint: HeuristicLint | None = None,
    status: str = "VALID",
) -> QualityVector:
    lint = lint or evaluate_lint(
        source_text=source_text,
        summary=summary,
        config=config,
        telemetry=telemetry,
    )
    if status in {"FAILED", "TIMEOUT", "INSUFFICIENT_OUTPUT"} or not (summary or "").strip():
        return QualityVector(
            gold_coverage="unavailable" if gold_for_document(document_name) is None else "available",
            notes=[f"quality withheld: status={status}"],
            evidence={"status": status, "lint": lint.to_dict()},
        )

    gold = gold_for_document(document_name)
    notes: list[str] = list(lint.notes)
    evidence: dict[str, Any] = {"lint": lint.to_dict()}
    summary_claims = extract_claims(summary)
    source_support = [
        {
            "id": claim["id"],
            "claim": claim["claim"],
            "support": claim_supported_by_source(claim["claim"], source_text),
        }
        for claim in summary_claims
    ]
    evidence["summary_claims"] = source_support
    supported = [row for row in source_support if row["support"] == "supported"]
    partial = [row for row in source_support if row["support"] == "partial"]
    unsupported = [row for row in source_support if row["support"] == "unsupported"]
    total_w = sum(int(claim["importance"]) for claim in summary_claims) or 1
    support_w = 0.0
    unsup_w = 0.0
    importance = {claim["id"]: int(claim["importance"]) for claim in summary_claims}
    for row in source_support:
        weight = importance.get(row["id"], 1)
        if row["support"] == "supported":
            support_w += weight
        elif row["support"] == "partial":
            support_w += 0.5 * weight
        else:
            unsup_w += weight
    fidelity = _clip(100.0 * support_w / total_w) if summary_claims else None
    hallucination = _clip(100.0 * (1.0 - unsup_w / total_w)) if summary_claims else None

    gold_coverage = "unavailable"
    coverage = None
    completeness = None
    contradiction = 100.0
    if gold:
        gold_coverage = "available"
        topics = list(gold.get("important_topics") or [])
        present, missing = match_topics(topics, summary)
        evidence["topics_present"] = present
        evidence["topics_missing"] = missing
        coverage = (
            _clip(100.0 * len(present) / max(1, len(present) + len(missing)))
            if topics
            else None
        )
        claim_rows = match_key_claims(list(gold.get("key_claims") or []), summary, source_text)
        evidence["gold_claims"] = claim_rows
        if claim_rows:
            weights = [max(1, int(row["importance"])) for row in claim_rows]
            scores = []
            for row, weight in zip(claim_rows, weights):
                if row["status"] == "supported":
                    scores.append(weight)
                elif row["status"] == "partial":
                    scores.append(0.5 * weight)
                else:
                    scores.append(0.0)
            completeness = _clip(100.0 * sum(scores) / max(1, sum(weights)))
        number_rows = match_numbers(list(gold.get("critical_numbers") or []), summary, source_text)
        evidence["gold_numbers"] = number_rows
        contradicted = sum(1 for row in number_rows if row.get("contradicted"))
        if number_rows:
            contradiction = _clip(100.0 * (1.0 - contradicted / len(number_rows)))
        entities = list(gold.get("critical_entities") or [])
        if entities:
            entity_hits = [
                entity
                for entity in entities
                if entity.casefold() in (summary or "").casefold()
            ]
            evidence["entities_present"] = entity_hits
            entity_score = 100.0 * len(entity_hits) / len(entities)
            if coverage is None:
                coverage = _clip(entity_score)
            else:
                coverage = _clip(0.7 * coverage + 0.3 * entity_score)
    else:
        notes.append("gold_coverage=unavailable")
        numbers_in_summary = extract_numbers(summary)
        invented = [num for num in numbers_in_summary if num not in (source_text or "")]
        evidence["invented_numbers"] = invented[:20]
        if invented:
            hallucination = _clip((hallucination or 100.0) - 8.0 * min(8, len(invented)))
            notes.append(f"unsupported numbers: {invented[:8]}")

    copy_ratio = lint.copy_ratio or 0.0
    utility = 100.0
    if lint.chatbot_score:
        utility -= min(80.0, lint.chatbot_score)
    utility -= min(70.0, 100.0 * copy_ratio)
    if coverage is not None:
        utility = 0.6 * utility + 0.4 * coverage
    if lint.summary_words < 80:
        utility -= 15
    utility = _clip(utility)

    coherence = _clip(
        90.0
        - (15.0 if lint.first_person else 0.0)
        - (10.0 if lint.truncation_signals else 0.0)
        - (20.0 if lint.chatbot_score else 0.0)
    )
    instruction = []
    if lint.language_score is not None:
        instruction.append(lint.language_score)
    if copy_ratio >= 0.5:
        instruction.append(20.0)
        notes.append("copy-like dump")
    instruction_adherence = _mean(instruction)

    quality_score = None
    if gold_coverage == "available" and None not in (fidelity, coverage, hallucination):
        quality_score = round(
            0.25 * (fidelity or 0)
            + 0.20 * (coverage or 0)
            + 0.15 * (completeness if completeness is not None else coverage or 0)
            + 0.20 * (hallucination or 0)
            + 0.10 * contradiction
            + 0.10 * utility,
            2,
        )
        if copy_ratio >= 0.80:
            quality_score = min(quality_score, 40.0)
            notes.append("copy_dump_cap=40")
        elif copy_ratio >= 0.50:
            quality_score = min(quality_score, 50.0)
            notes.append("copy_dump_cap=50")
        if lint.chatbot_score >= 50:
            quality_score = min(quality_score, 20.0)
            notes.append("chatbot_output_cap=20")

    return QualityVector(
        fidelity=None if fidelity is None else round(fidelity, 2),
        coverage=None if coverage is None else round(coverage, 2),
        completeness=None if completeness is None else round(completeness, 2),
        hallucination=None if hallucination is None else round(hallucination, 2),
        contradiction=round(contradiction, 2),
        coherence=round(coherence, 2),
        utility=round(utility, 2),
        language=lint.language_score,
        instruction_adherence=instruction_adherence,
        quality_score=quality_score,
        gold_coverage=gold_coverage,
        notes=notes,
        evidence=evidence,
    )
