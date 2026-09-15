from __future__ import annotations

from pathlib import Path

from benchmarks.summary_pipeline.claims import extract_claims
from benchmarks.summary_pipeline.evaluator import score_job
from benchmarks.summary_pipeline.fingerprint import experiment_fingerprint
from benchmarks.summary_pipeline.gold import gold_for_document
from benchmarks.summary_pipeline.judge import create_judge
from benchmarks.summary_pipeline.models import (
    BenchmarkConfig,
    JobStatus,
    TelemetrySnapshot,
)
from benchmarks.summary_pipeline.telemetry import snapshot_from_mapping

FIXTURES = Path(__file__).resolve().parent / "fixtures"

ECON_PARAGRAPH = (
    "La economía estudia cómo los agentes eligen bajo escasez de recursos. "
    "El primer principio de la economía es la optimización: elegir la mejor opción disponible. "
    "El segundo principio es el equilibrio, donde nadie se beneficia desviándose unilateralmente. "
    "Facebook no cobra dinero a sus usuarios y obtiene ingresos de la publicidad. "
    "El tipo de cambio del ejemplo convierte pesetas con el divisor 166.33. "
    "El coste de oportunidad es el valor de la mejor alternativa sacrificada. "
)
ECON_SOURCE = ECON_PARAGRAPH * 40

FAITHFUL_SUMMARY = (
    "La economía estudia cómo los agentes eligen bajo escasez. "
    "El primer principio es la optimización y el segundo el equilibrio. "
    "Facebook no cobra dinero a sus usuarios; el negocio se sostiene con publicidad. "
    "El tipo de cambio del ejemplo usa 166.33 y el coste de oportunidad mide la alternativa sacrificada. "
    "Estos pilares —optimización, equilibrio y escasez— organizan el análisis de decisiones. "
    "El resumen cubre los conceptos centrales del capítulo sin copiar el documento entero. "
)

CONFIG = BenchmarkConfig("moderate", "education", "guide", language="spanish")
MATCHING_RUNTIME = {
    "requested_context": 16384,
    "effective_loaded_context_length": 16384,
}
DOC = "synthetic-econ.txt"


def present_telemetry() -> TelemetrySnapshot:
    return TelemetrySnapshot(
        folder_id="job-1",
        telemetry_status="present",
        model="qwen3:14b",
        truncation_detected=False,
        total_tokens_summary_input=1200,
        total_tokens_summary_output=400,
        total_tokens_postprocess_input=0,
        total_tokens_postprocess_output=0,
        api_request_count=4,
        retry_requests=0,
        failed_requests=0,
        total_time=42.0,
        estimated_provider_cost=None,
        pricing_version=None,
        token_accounting="provider_reported_tokens",
    )


def score(
    summary: str,
    *,
    config: BenchmarkConfig = CONFIG,
    telemetry: TelemetrySnapshot | None = None,
    runtime: dict | None = None,
    error: str = "",
    document_name: str = DOC,
    source: str = ECON_SOURCE,
):
    return score_job(
        source_text=source,
        summary=summary,
        config=config,
        document_name=document_name,
        telemetry=present_telemetry() if telemetry is None else telemetry,
        error=error,
        runtime=MATCHING_RUNTIME if runtime is None else runtime,
    )


def test_sabotage_01_empty_summary_fails() -> None:
    status, reasons, _, _, quality = score("")
    assert status is JobStatus.INSUFFICIENT_OUTPUT
    assert quality.quality_score is None
    assert any("insufficient" in item for item in reasons)


def test_sabotage_02_chatbot_fails() -> None:
    summary = (
        "¿Qué necesitas? Estoy aquí para ayudarte. "
        "Puedo explicarte el temario o darte un resumen. "
        "Dime qué opción te interesa y especifica una. "
        "Gracias por compartir esta información conmigo para continuar. "
        "Opciones para ayudarte: resumen, ejemplos, autor o código. "
    )
    status, reasons, _, lint, quality = score(summary)
    assert status is JobStatus.CHATBOT_OUTPUT
    assert lint.chatbot_score >= 50
    assert status.value != "VALID"
    assert quality.quality_score is None or quality.quality_score <= 20


def test_sabotage_03_literal_copy_does_not_win() -> None:
    copy_status, _, _, copy_lint, copy_quality = score(ECON_SOURCE)
    good_status, _, _, good_lint, good_quality = score(FAITHFUL_SUMMARY)
    assert copy_status is JobStatus.VALID
    assert good_status is JobStatus.VALID
    assert copy_lint.copy_ratio is not None and copy_lint.copy_ratio >= 0.8
    assert (copy_quality.quality_score or 0) <= 40
    assert (good_quality.quality_score or 0) > (copy_quality.quality_score or 0)


def test_sabotage_04_domain_hallucination_lowers_fidelity() -> None:
    invented = (
        "Keynes demostró que el multiplicador fiscal es 9.7 en todos los países. "
        "España creció un 400% en 2024 gracias a que Facebook cobra 50 euros al mes. "
        "El banco central fijó el tipo de interés en 87.5% de forma permanente. "
        "Estos hechos no aparecen en el capítulo pero conviene memorizarlos. "
        "La política monetaria se reduce a imprimir billetes sin límite. "
    )
    good_status, _, _, _, good = score(FAITHFUL_SUMMARY)
    bad_status, _, _, _, bad = score(invented)
    assert good_status is JobStatus.VALID
    assert bad_status is JobStatus.VALID
    assert good.fidelity is not None and bad.fidelity is not None
    assert bad.fidelity < good.fidelity
    assert good.hallucination is not None and bad.hallucination is not None
    assert bad.hallucination < good.hallucination


def test_sabotage_05_language_mismatch_fails() -> None:
    english = (
        "The economy studies how agents choose under scarcity of resources. "
        "The first principle is optimization and the second is equilibrium. "
        "Facebook does not charge money to its users and funds itself with ads. "
        "This English summary is intentionally written in the wrong language. "
        "Opportunity cost measures the value of the sacrificed alternative. "
    )
    status, reasons, _, lint, quality = score(english)
    assert status is JobStatus.LANGUAGE_MISMATCH
    assert lint.language_label == "english"
    assert quality.language == 0
    assert any("language mismatch" in item for item in reasons)


def test_sabotage_06_extremely_short_summary_penalizes_coverage() -> None:
    short = (
        "Este texto es breve y genérico. Habla de ideas, de páginas y de un autor. "
        "Menciona empresas, publicidad y cifras sueltas sin desarrollar ningún pilar. "
        "No aparecen definiciones, ni el equilibrio, ni la escasez, ni el tipo de cambio. "
        "Sirve como ejemplo de un resumen demasiado corto para cubrir el documento. "
        "El lector no podría revisar el capítulo a partir de estas líneas aisladas. "
    )
    _, _, _, _, short_quality = score(short)
    _, _, _, _, good = score(FAITHFUL_SUMMARY)
    assert short_quality.coverage is not None and good.coverage is not None
    assert short_quality.coverage < good.coverage
    assert short_quality.completeness is not None and good.completeness is not None
    assert short_quality.completeness < good.completeness


def test_sabotage_07_extremely_long_copy_is_not_automatically_better() -> None:
    long_copy = ECON_SOURCE + " " + ECON_SOURCE
    _, _, _, _, long_quality = score(long_copy)
    _, _, _, _, good = score(FAITHFUL_SUMMARY)
    assert (long_quality.quality_score or 0) <= 40
    assert (good.quality_score or 0) > (long_quality.quality_score or 0)


def test_sabotage_08_contradiction_is_detected() -> None:
    contradicted = (
        "La economía estudia cómo los agentes eligen bajo escasez. "
        "El primer principio es la optimización y el segundo el equilibrio. "
        "Facebook no cobra dinero a sus usuarios. "
        "El tipo de cambio del ejemplo es 200.00 y no se menciona otro divisor. "
        "El coste de oportunidad sigue siendo la alternativa sacrificada. "
        "Optimización y equilibrio organizan el análisis de las decisiones. "
    )
    status, _, _, _, quality = score(contradicted)
    assert status is JobStatus.VALID
    assert quality.contradiction is not None
    assert quality.contradiction < 100
    numbers = (quality.evidence or {}).get("gold_numbers") or []
    assert any(row.get("contradicted") for row in numbers)


def test_sabotage_09_same_summary_different_levels_do_not_change_semantics() -> None:
    concise = BenchmarkConfig("very_concise", "education", "guide")
    detailed = BenchmarkConfig("very_detailed", "education", "guide")
    _, _, _, _, left = score(FAITHFUL_SUMMARY, config=concise)
    _, _, _, _, right = score(FAITHFUL_SUMMARY, config=detailed)
    assert left.fidelity == right.fidelity
    assert left.coverage == right.coverage
    assert left.completeness == right.completeness
    assert left.hallucination == right.hallucination
    assert left.contradiction == right.contradiction
    assert left.quality_score == right.quality_score


def test_sabotage_10_missing_telemetry_is_unknown_not_zero() -> None:
    missing = TelemetrySnapshot(folder_id="job-1", telemetry_status="missing")
    status, reasons, _, _, _ = score(FAITHFUL_SUMMARY, telemetry=missing)
    assert status is JobStatus.INVALID_TELEMETRY
    assert missing.estimated_provider_cost is None
    assert missing.total_tokens is None
    snapshot = snapshot_from_mapping(
        {
            "folder_id": "x",
            "model": "",
            "total_tokens_summary_input": 0,
            "total_tokens_summary_output": 0,
            "api_request_count": 0,
            "number_of_chunks": 0,
            "num_tokens_file": 0,
            "estimated_provider_cost": 0,
        }
    )
    assert snapshot.telemetry_status == "missing"
    assert snapshot.estimated_provider_cost is None
    assert snapshot.total_tokens is None
    assert any("telemetry" in item for item in reasons)


def test_sabotage_11_runtime_context_mismatch_invalidates_job() -> None:
    runtime = {
        "requested_context": 16384,
        "effective_loaded_context_length": 4096,
    }
    status, reasons, _, _, _ = score(FAITHFUL_SUMMARY, runtime=runtime)
    assert status is JobStatus.INVALID_RUNTIME
    assert any("requested_context=16384" in item for item in reasons)


def test_sabotage_12_different_matrix_is_not_comparable() -> None:
    from benchmarks.summary_pipeline.decision import compare_iterations

    provenance = {
        "scorer_version": "2.0.0",
        "judge_version": "2.0.0-optional",
        "dataset_sha": "ds",
        "matrix_hash": "mx",
    }
    before = {
        "provenance": provenance,
        "experiments": [
            {
                "cell_key": [
                    "doc",
                    "qwen3:14b",
                    "spanish",
                    "moderate",
                    "education",
                    "guide",
                    "markdown",
                ],
                "status": "VALID",
                "quality": {"quality_score": 80, "fidelity": 90, "coverage": 90},
            }
        ],
    }
    after = {
        "provenance": provenance,
        "experiments": [
            {
                "cell_key": [
                    "doc",
                    "qwen3:14b",
                    "spanish",
                    "very_detailed",
                    "education",
                    "guide",
                    "markdown",
                ],
                "status": "VALID",
                "quality": {"quality_score": 88, "fidelity": 92, "coverage": 91},
            }
        ],
    }
    result = compare_iterations(before, after)
    assert result["valid_for_comparison"] is False
    assert result["decision"] == "INVALID"


def test_sabotage_13_fingerprint_changes_with_git_sha() -> None:
    kwargs = dict(
        code_sha="code",
        dataset="data",
        matrix="mx",
        document_id="synthetic-econ",
        source_sha="src",
        config=CONFIG,
        requested_context=16384,
        judge_model="disabled",
        prompt_hash="p",
        gold_sha="g",
    )
    left = experiment_fingerprint(git_commit="aaa", **kwargs)
    right = experiment_fingerprint(git_commit="bbb", **kwargs)
    assert left != right


def test_sabotage_14_scorer_version_mismatch_is_not_comparable() -> None:
    from benchmarks.summary_pipeline.decision import compare_iterations

    cells = [
        {
            "cell_key": [
                "doc",
                "qwen3:14b",
                "spanish",
                "moderate",
                "education",
                "guide",
                "markdown",
            ],
            "status": "VALID",
            "quality": {"quality_score": 80, "fidelity": 90, "coverage": 90},
        }
    ]
    before = {"provenance": {"scorer_version": "2.0.0"}, "experiments": cells}
    after = {"provenance": {"scorer_version": "2.1.0"}, "experiments": cells}
    result = compare_iterations(before, after)
    assert result["decision"] == "INVALID"
    assert "scorer_version" in result["reason"]


def test_asyncio_chatbot_fixture_never_passes() -> None:
    summary = (FIXTURES / "asyncio_chatbot.md").read_text(encoding="utf-8")
    status, reasons, _, lint, quality = score(
        summary,
        document_name="using-asyncio-python.pdf",
        source="asyncio event loop coroutines async/await tasks Caleb Hattingh",
    )
    assert status is JobStatus.CHATBOT_OUTPUT
    assert "¿Qué necesitas?" in summary
    assert lint.chatbot_score >= 50
    assert not hasattr(quality, "overall")
    assert quality.quality_score is None or quality.quality_score <= 20
    assert status.value != "VALID"
    assert any("chatbot" in item for item in reasons)


def test_gold_coverage_unavailable_is_not_100() -> None:
    assert gold_for_document("totally-unknown-book.pdf") is None
    _, _, _, _, quality = score(
        FAITHFUL_SUMMARY, document_name="totally-unknown-book.pdf"
    )
    assert quality.gold_coverage == "unavailable"
    assert quality.quality_score is None


def test_truncation_finish_reason_is_detected() -> None:
    telemetry = present_telemetry()
    telemetry.history_tokens_per_call = [
        {
            "type_call": "reduce",
            "is_final_reduce": True,
            "finish_reason": "length",
            "reduce_level": 2,
        }
    ]
    status, reasons, _, _, _ = score(FAITHFUL_SUMMARY, telemetry=telemetry)
    assert status is JobStatus.TRUNCATED
    assert any("finish_reason=length" in item for item in reasons)


def test_failed_job_has_no_usable_quality() -> None:
    status, _, _, _, quality = score(
        FAITHFUL_SUMMARY, error="timeout waiting for celery"
    )
    assert status is JobStatus.TIMEOUT
    assert quality.quality_score is None
    assert quality.fidelity is None
    status, _, _, _, quality = score(
        FAITHFUL_SUMMARY, error="timeout waiting for celery"
    )
    assert status is JobStatus.TIMEOUT
    assert quality.quality_score is None
    assert quality.fidelity is None


def test_heuristic_is_not_primary_quality() -> None:
    _, _, _, _, quality = score(FAITHFUL_SUMMARY)
    assert not hasattr(quality, "overall")
    assert quality.quality_score is not None
    assert quality.fidelity is not None


def test_judge_defaults_to_disabled_and_is_not_the_generator() -> None:
    judge = create_judge("")
    assert judge.enabled is False
    assert judge.model == "disabled"
    payload = judge.evaluate({"summary": FAITHFUL_SUMMARY})
    assert payload["enabled"] is False
    assert payload["cost"] is None


def test_claim_extraction_keeps_numbered_facts() -> None:
    claims = extract_claims(
        "# Título\n"
        "- **Optimización:** Los agentes eligen la mejor opción disponible.\n"
        "- En 2025 el precio aumentó un 12%.\n"
    )
    assert len(claims) == 2
    assert claims[0]["id"] == "c001"
    assert claims[1]["importance"] == 3
