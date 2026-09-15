from __future__ import annotations

from pathlib import Path

from benchmarks.summary_pipeline.aggregation import aggregate_iteration
from benchmarks.summary_pipeline.client import SubmittedJob
from benchmarks.summary_pipeline.decision import (
    compare_iterations,
    iteration_valid_for_comparison,
)
from benchmarks.summary_pipeline.models import (
    BenchmarkConfig,
    BenchmarkPaths,
    TelemetrySnapshot,
)
from benchmarks.summary_pipeline.rescore import rescore_iteration_payload
from benchmarks.summary_pipeline.runner import persist_results, run_experiments
from benchmarks.summary_pipeline.telemetry import snapshot_from_mapping

FAITHFUL = (
    "La economía estudia cómo los agentes eligen bajo escasez. "
    "El primer principio es la optimización y el segundo el equilibrio. "
    "Facebook no cobra dinero a sus usuarios; el negocio se sostiene con publicidad. "
    "El tipo de cambio del ejemplo usa 166.33 y el coste de oportunidad mide la alternativa sacrificada. "
    "Estos pilares —optimización, equilibrio y escasez— organizan el análisis de decisiones. "
    "El resumen cubre los conceptos centrales del capítulo sin copiar el documento entero. "
)
SOURCE = (
    "La economía estudia cómo los agentes eligen bajo escasez de recursos. "
    "El primer principio de la economía es la optimización. "
    "El segundo principio es el equilibrio. "
    "Facebook no cobra dinero a sus usuarios. "
    "El tipo de cambio del ejemplo usa 166.33. "
) * 30

PROVENANCE = {
    "git_sha": "abc123",
    "dataset_sha": "dataset1",
    "matrix_hash": "matrix1",
    "benchmark_version": "2.0.0",
    "scorer_version": "2.0.0",
    "judge_version": "2.0.0-optional",
}


def _telemetry() -> dict:
    return TelemetrySnapshot(
        folder_id="job-1",
        telemetry_status="present",
        model="qwen3:14b",
        total_tokens_summary_input=100,
        total_tokens_summary_output=50,
        total_tokens_postprocess_input=0,
        total_tokens_postprocess_output=0,
        retry_requests=0,
        api_request_count=2,
        total_time=10.0,
        estimated_provider_cost=None,
    ).to_dict()


def _record(
    doc: str,
    score: float,
    *,
    status: str = "VALID",
    level: str = "moderate",
) -> dict:
    return {
        "document": f"{doc}.txt",
        "document_id": doc,
        "status": status,
        "error": "",
        "fingerprint": f"fp-{doc}-{level}",
        "cell_key": [
            doc,
            "qwen3:14b",
            "spanish",
            level,
            "education",
            "guide",
            "markdown",
        ],
        "config": {
            "summary_level": level,
            "category": "education",
            "style": "guide",
            "output_format": "markdown",
            "language": "spanish",
            "model": "qwen3:14b",
        },
        "quality": {
            "quality_score": score,
            "fidelity": score,
            "coverage": score,
            "completeness": score,
            "hallucination": 100,
            "contradiction": 100,
            "utility": score,
        },
        "telemetry": _telemetry(),
    }


def _iteration(records: list[dict], **extra) -> dict:
    payload = {
        "iteration_id": extra.get("iteration_id", "candidate"),
        "provenance": dict(PROVENANCE),
        "experiments": records,
        "aggregates": aggregate_iteration(records),
    }
    payload.update(
        {key: value for key, value in extra.items() if key != "iteration_id"}
    )
    payload["iteration_id"] = extra.get("iteration_id", payload["iteration_id"])
    return payload


def test_stratified_aggregation_does_not_let_one_document_dominate() -> None:
    records = [
        _record("alpha", 100, level="very_concise"),
        _record("alpha", 100, level="moderate"),
        _record("alpha", 100, level="very_detailed"),
        _record("beta", 10, level="moderate"),
    ]
    aggregates = aggregate_iteration(records)
    job_mean = aggregates["quality"]["quality_score"]["mean"]
    equal = aggregates["quality"]["document_equal_weight_quality_score"]["mean"]
    assert job_mean == 77.5
    assert equal == 55.0
    assert set(aggregates["per_document"]) == {"alpha", "beta"}
    assert set(aggregates["per_level"]) >= {"moderate", "very_concise", "very_detailed"}


def test_keep_requires_several_documents() -> None:
    before = _iteration(
        [_record("a", 70), _record("b", 70), _record("c", 70)], iteration_id="base"
    )
    after = _iteration(
        [_record("a", 80), _record("b", 80), _record("c", 80)], iteration_id="cand"
    )
    keep = compare_iterations(before, after)
    assert keep["decision"] == "KEEP"
    small_before = _iteration([_record("a", 70)], iteration_id="base")
    small_after = _iteration([_record("a", 80)], iteration_id="cand")
    inconclusive = compare_iterations(small_before, small_after)
    assert inconclusive["decision"] == "INCONCLUSIVE"


def test_coverage_drop_reverts_even_if_quality_rises() -> None:
    before_rows = [_record("a", 80), _record("b", 80), _record("c", 80)]
    after_rows = [_record("a", 83), _record("b", 83), _record("c", 83)]
    for row in after_rows:
        row["quality"]["coverage"] = 60
        row["quality"]["fidelity"] = 80
    before = _iteration(before_rows)
    after = _iteration(after_rows)
    result = compare_iterations(before, after)
    assert result["decision"] == "REVERT"
    assert "coverage" in result["reason"]


def test_chatbot_increase_reverts() -> None:
    before = _iteration([_record("a", 80)])
    after_rows = [_record("a", 80)]
    after_rows[0]["status"] = "CHATBOT_OUTPUT"
    after = _iteration(after_rows)
    after["aggregates"] = aggregate_iteration(after_rows)
    result = compare_iterations(before, after)
    assert result["decision"] == "REVERT"
    assert "chatbot" in result["reason"] or "invalid" in result["reason"]


def test_latest_is_fail_closed(tmp_path: Path) -> None:
    paths = BenchmarkPaths(tmp_path)
    paths.ensure()
    sentinel = {"iteration_id": "keep-me", "valid_for_comparison": True}
    latest = paths.results / "latest.json"
    latest.write_text('{"iteration_id": "keep-me"}\n', encoding="utf-8")
    invalid = {
        "iteration_id": "iteration_005_per_book_density",
        "experiments": [
            {
                "status": "FAILED",
                "error": "timeout",
                "fingerprint": "",
                "cell_key": [],
                "quality": {"overall": 81.37},
                "telemetry": {
                    "telemetry_status": "missing",
                    "estimated_provider_cost": 0,
                },
            }
        ],
        "aggregates": aggregate_iteration(
            [
                {
                    "status": "FAILED",
                    "error": "timeout",
                    "quality": {"overall": 81.37},
                    "telemetry": {"telemetry_status": "missing"},
                }
            ]
        ),
        "provenance": {},
    }
    payload = persist_results(invalid, paths)
    assert payload["latest_promoted"] is False
    assert payload["validity"]["valid_for_comparison"] is False
    assert latest.read_text(encoding="utf-8").find("keep-me") >= 0
    assert not payload["validity"]["valid_for_comparison"]
    del sentinel


def test_latest_promotes_only_comparable_runs(tmp_path: Path) -> None:
    paths = BenchmarkPaths(tmp_path)
    payload = persist_results(
        _iteration([_record("a", 80)], iteration_id="good"), paths
    )
    assert payload["latest_promoted"] is True
    assert payload["validity"]["valid_for_comparison"] is True
    stored = (paths.results / "latest.json").read_text(encoding="utf-8")
    assert '"valid_for_comparison": true' in stored


def test_historical_iteration_005_cannot_be_latest() -> None:
    here = Path(__file__).resolve()
    root = next(parent for parent in here.parents if (parent / "pytest.ini").is_file())
    historical = (
        root / "benchmark" / "iterations" / "iteration_005_per_book_density.json"
    )
    latest = root / "benchmark" / "results" / "latest.json"
    for path in (historical, latest):
        if not path.is_file():
            continue
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
        ok, reasons = iteration_valid_for_comparison(payload)
        assert ok is False
        assert reasons
    if historical.is_file():
        import json

        raw = json.loads(historical.read_text(encoding="utf-8"))
        rescored = rescore_iteration_payload(raw)
        assert rescored["validity"]["valid_for_comparison"] is False
        assert rescored["aggregates"]["cost"]["provider_cost"]["mean"] is None


def test_zero_telemetry_cost_is_unknown() -> None:
    snapshot = snapshot_from_mapping(
        {
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
    records = [
        {
            "status": "INVALID_TELEMETRY",
            "quality": {"quality_score": 90},
            "telemetry": snapshot.to_dict(),
        }
    ]
    aggregates = aggregate_iteration(records)
    assert aggregates["cost"]["provider_cost"]["mean"] is None
    assert aggregates["counts"]["valid_jobs"] == 0


class _FakeClient:
    def __init__(self) -> None:
        self.submits = 0

    def submit_document(self, document, config):
        self.submits += 1
        return SubmittedJob("task", "folder1", 0.0)

    def wait_for_result(self, job, timeout_seconds=0, poll_seconds=0):
        return None

    def download_summary(self, folder_id):
        return FAITHFUL


def test_resume_rejects_changed_git_sha(monkeypatch, tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    book = docs / "synthetic-econ.txt"
    book.write_text(SOURCE, encoding="utf-8")
    output = tmp_path / "bench"
    paths = BenchmarkPaths(output)
    logs = tmp_path / "logs.json"
    logs.write_text("[]", encoding="utf-8")
    client = _FakeClient()
    telemetry = TelemetrySnapshot(
        folder_id="folder1",
        telemetry_status="present",
        model="qwen3:14b",
        total_tokens_summary_input=10,
        total_tokens_summary_output=10,
        total_tokens_postprocess_input=0,
        total_tokens_postprocess_output=0,
        retry_requests=0,
        truncation_detected=False,
    )
    monkeypatch.setattr(
        "benchmarks.summary_pipeline.runner.snapshot_for_folder",
        lambda *_args, **_kwargs: telemetry,
    )
    monkeypatch.setattr(
        "benchmarks.summary_pipeline.runner.requested_context_for_model",
        lambda _model: 16384,
    )
    runtime = {
        "qwen3:14b": {
            "requested_context": 16384,
            "effective_loaded_context_length": 16384,
            "model_digest": "digest",
        }
    }
    shas = {"value": "sha-a"}
    monkeypatch.setattr(
        "benchmarks.summary_pipeline.runner.git_sha",
        lambda _root: shas["value"],
    )
    first = run_experiments(
        documents=[book],
        configs=[BenchmarkConfig()],
        client=client,
        paths=paths,
        logs_json=logs,
        iteration_id="resume-test",
        job_timeout=5,
        poll_seconds=0.01,
        suite="single",
        resume=False,
        runtime_override=runtime,
    )
    assert client.submits == 1
    assert first["experiments"][0]["status"] == "VALID"
    run_experiments(
        documents=[book],
        configs=[BenchmarkConfig()],
        client=client,
        paths=paths,
        logs_json=logs,
        iteration_id="resume-test",
        job_timeout=5,
        poll_seconds=0.01,
        suite="single",
        resume=True,
        runtime_override=runtime,
    )
    assert client.submits == 1
    shas["value"] = "sha-b"
    run_experiments(
        documents=[book],
        configs=[BenchmarkConfig()],
        client=client,
        paths=paths,
        logs_json=logs,
        iteration_id="resume-test",
        job_timeout=5,
        poll_seconds=0.01,
        suite="single",
        resume=True,
        runtime_override=runtime,
    )
    assert client.submits > 1
