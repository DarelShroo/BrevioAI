from unittest.mock import MagicMock

import pytest

from benchmarks.summary_pipeline.client import (
    DEFAULT_BENCHMARK_IDENTITY,
    BrevioApiClient,
)
from benchmarks.summary_pipeline.corpus import (
    audit_corpus_coverage,
    build_corpus_manifest,
    classify_size,
    estimated_chunks,
)
from benchmarks.summary_pipeline.dataset import catalog_documents
from benchmarks.summary_pipeline.evaluator import compare_iterations, evaluate_summary
from benchmarks.summary_pipeline.models import (
    COMPARISON_MATRIX,
    DOCUMENT_MATRIX,
    BenchmarkConfig,
    TelemetrySnapshot,
)
from benchmarks.summary_pipeline.runner import (
    configs_for_document,
    discover_documents,
    matrix_templates_for_document,
    resolve_configs,
)


def test_benchmark_defaults_to_existing_darelsm2_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BREVIO_BENCHMARK_IDENTITY", raising=False)
    monkeypatch.delenv("BREVIO_BENCHMARK_PASSWORD", raising=False)
    client = BrevioApiClient("http://localhost:8000")
    try:
        assert client.identity == DEFAULT_BENCHMARK_IDENTITY
        assert client.identity == "Darelsm2"
    finally:
        client.close()


def test_request_retries_transport_disconnect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    monkeypatch.delenv("BREVIO_BENCHMARK_IDENTITY", raising=False)
    monkeypatch.delenv("BREVIO_BENCHMARK_PASSWORD", raising=False)
    client = BrevioApiClient("http://localhost:8000")
    client.token = "tok"
    calls = {"n": 0}

    def fake_request(*_: object, **__: object):
        calls["n"] += 1
        if calls["n"] < 3:
            raise httpx.RemoteProtocolError(
                "Server disconnected without sending a response."
            )
        response = MagicMock()
        response.status_code = 200
        return response

    sleeps: list[float] = []
    monkeypatch.setattr("benchmarks.summary_pipeline.client.time.sleep", sleeps.append)
    try:
        client._http.request = fake_request  # type: ignore[method-assign]
        assert client._request("GET", "/users/entries").status_code == 200
        assert calls["n"] == 3
        assert sleeps
    finally:
        client.close()


def test_authenticate_posts_login_and_never_registers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BREVIO_BENCHMARK_IDENTITY", raising=False)
    monkeypatch.delenv("BREVIO_BENCHMARK_PASSWORD", raising=False)
    posted: list[tuple[str, dict[str, str]]] = []

    def fake_post(url: str, json: dict[str, str] | None = None, **_: object):
        posted.append((url, json or {}))
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"data": {"access_token": "tok"}}
        return response

    client = BrevioApiClient("http://localhost:8000")
    try:
        client._http.post = fake_post  # type: ignore[method-assign]
        assert client.authenticate() == "tok"
        assert posted == [
            ("/auth/login", {"identity": "Darelsm2", "password": "A123@test"})
        ]
        assert all("/auth/register" not in url for url, _ in posted)
    finally:
        client.close()


def test_authenticate_accepts_http_only_access_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BREVIO_BENCHMARK_IDENTITY", raising=False)
    monkeypatch.delenv("BREVIO_BENCHMARK_PASSWORD", raising=False)

    def fake_post(url: str, json: dict[str, str] | None = None, **_: object):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "status": "success",
            "data": {"authenticated": True},
        }
        response.cookies.get.side_effect = (
            lambda key, default=None: "cookie-tok"
            if key == "brevio_access"
            else default
        )
        return response

    client = BrevioApiClient("http://localhost:8000")
    try:
        client._http.post = fake_post  # type: ignore[method-assign]
        assert client.authenticate() == "cookie-tok"
        assert client.token == "cookie-tok"
    finally:
        client.close()


def test_matrix_is_factorial_and_shared_across_books() -> None:
    configs = resolve_configs("matrix", BenchmarkConfig())
    assert {c.model for c in configs} == {"qwen3:14b"}
    triples = {(c.category, c.style, c.summary_level) for c in configs}
    assert triples == {
        ("education", "guide", "very_concise"),
        ("education", "guide", "moderate"),
        ("education", "guide", "very_detailed"),
    }
    assert len(configs) == 3
    assert DOCUMENT_MATRIX == ()
    assert COMPARISON_MATRIX == tuple(configs) or len(COMPARISON_MATRIX) == 3

    from pathlib import Path

    economics = Path("/tmp/798_INDICE-PROLOGO-CAPITULO_1.pdf")
    marketing = Path("/tmp/978-84-11921-29-9 Fundamentos de marketing.pdf")
    base = BenchmarkConfig()
    spanish = {
        (cfg.category, cfg.style, cfg.summary_level, cfg.language)
        for cfg in configs_for_document(
            economics, "matrix", base, ["qwen3:14b"], native_language="spanish"
        )
    }
    also_spanish = {
        (cfg.category, cfg.style, cfg.summary_level, cfg.language)
        for cfg in configs_for_document(
            marketing, "matrix", base, ["qwen3:14b"], native_language="spanish"
        )
    }
    english = {
        (cfg.category, cfg.style, cfg.summary_level, cfg.language)
        for cfg in configs_for_document(
            economics, "matrix", base, ["qwen3:14b"], native_language="english"
        )
    }
    assert spanish == also_spanish
    assert all(item[3] == "spanish" for item in spanish)
    assert all(item[3] == "english" for item in english)
    assert (
        matrix_templates_for_document(Path("/tmp/alpha-book.pdf")) == COMPARISON_MATRIX
    )


def test_discover_documents_reads_every_book_in_libros_dir() -> None:
    from pathlib import Path

    folder = Path("/tmp/brevio-libros-test")
    folder.mkdir(exist_ok=True)
    (folder / "alpha.pdf").write_bytes(b"%PDF-1.4")
    (folder / "beta.docx").write_bytes(b"PK")
    (folder / "notes.txt").write_text("hola", encoding="utf-8")
    (folder / "ignore.png").write_bytes(b"x")
    found = {path.name for path in discover_documents(folder)}
    assert found == {"alpha.pdf", "beta.docx", "notes.txt"}


def test_evaluator_uses_gold_and_claims_not_js_keyword_list() -> None:
    source = (
        "Javascript es un lenguaje de programación interpretado. "
        'Se integra con <script src="micodigo.js"></script>. '
        "El conversor usa ImportePtas / 166.33 y prompt()."
    )
    good = (
        "JavaScript es un lenguaje interpretado que se ejecuta en el navegador. "
        "El código se inserta entre las etiquetas SCRIPT de una página HTML. "
        "El conversor usa ImportePtas y el divisor 166.33. "
        "Aula Mentor presenta ejemplos con micodigo.js y la función prompt(). "
        "El temario cubre HTML, el navegador y el uso básico de Javascript. "
    )
    bad = (
        "Keynes demostró que el multiplicador es 9.7 y que Node.js con React "
        "es el único runtime válido. El conversor divide entre 999.99. "
        "Aprendí que hay que usar VS Code para este temario de Aula Mentor. "
        "No hay referencias a SCRIPT ni a ImportePtas en esta versión. "
        "El curso se presenta como un tutorial de frameworks modernos. "
    )
    config = BenchmarkConfig("very_detailed", "education", "guide")
    telemetry = TelemetrySnapshot(
        folder_id="g",
        telemetry_status="present",
        total_tokens_summary_input=10,
        total_tokens_summary_output=10,
        total_tokens_postprocess_input=0,
        total_tokens_postprocess_output=0,
        retry_requests=0,
    )
    runtime = {"requested_context": 16384, "effective_loaded_context_length": 16384}
    good_scores = evaluate_summary(
        source_text=source,
        summary=good,
        config=config,
        document_name="iniciacion_javascript.pdf",
        telemetry=telemetry,
        runtime=runtime,
    )
    bad_scores = evaluate_summary(
        source_text=source,
        summary=bad,
        config=config,
        document_name="iniciacion_javascript.pdf",
        telemetry=telemetry,
        runtime=runtime,
    )
    assert not hasattr(good_scores, "overall")
    assert (
        good_scores.hallucination is not None and bad_scores.hallucination is not None
    )
    assert good_scores.fidelity is not None and bad_scores.fidelity is not None
    assert good_scores.hallucination > bad_scores.hallucination
    assert good_scores.fidelity > bad_scores.fidelity
    assert good_scores.coverage is not None and bad_scores.coverage is not None
    assert good_scores.coverage > bad_scores.coverage


def test_compare_iterations_reverts_quality_drop() -> None:
    provenance = {
        "scorer_version": "2.0.0",
        "judge_version": "2.0.0-optional",
        "dataset_sha": "ds",
        "matrix_hash": "mx",
    }
    cell = ["doc", "qwen3:14b", "spanish", "moderate", "education", "guide", "markdown"]
    before = {
        "provenance": provenance,
        "experiments": [
            {
                "cell_key": cell,
                "status": "VALID",
                "document_id": "doc",
                "quality": {
                    "quality_score": 90,
                    "fidelity": 95,
                    "coverage": 90,
                    "completeness": 88,
                    "hallucination": 98,
                    "contradiction": 100,
                },
            }
        ],
        "aggregates": {
            "counts": {"valid_jobs": 1, "invalid_jobs": 0, "failed_jobs": 0},
            "quality": {
                "quality_score": {"mean": 90},
                "fidelity": {"mean": 95},
                "coverage": {"mean": 90},
                "completeness": {"mean": 88},
                "hallucination": {"mean": 98},
                "contradiction": {"mean": 100},
            },
            "per_document": {"doc": {}},
        },
    }
    after = {
        "provenance": provenance,
        "experiments": [
            {
                "cell_key": cell,
                "status": "VALID",
                "document_id": "doc",
                "quality": {
                    "quality_score": 70,
                    "fidelity": 80,
                    "coverage": 60,
                    "completeness": 60,
                    "hallucination": 90,
                    "contradiction": 100,
                },
            }
        ],
        "aggregates": {
            "counts": {"valid_jobs": 1, "invalid_jobs": 0, "failed_jobs": 0},
            "quality": {
                "quality_score": {"mean": 70},
                "fidelity": {"mean": 80},
                "coverage": {"mean": 60},
                "completeness": {"mean": 60},
                "hallucination": {"mean": 90},
                "contradiction": {"mean": 100},
            },
            "per_document": {"doc": {}},
        },
    }
    result = compare_iterations(before, after)
    assert result["decision"] == "REVERT"


def test_corpus_manifest_and_coverage_invariant(tmp_path) -> None:
    (tmp_path / "alpha.txt").write_text(
        "La economía estudia decisiones y recursos limitados. " * 20,
        encoding="utf-8",
    )
    manifest = build_corpus_manifest(tmp_path)
    assert manifest["totals"]["files_discovered"] == 1
    assert manifest["totals"]["books_valid"] == 1
    assert manifest["books"][0]["processable"] is True
    assert manifest["books"][0]["corpus_id"].startswith("book-")

    incomplete = audit_corpus_coverage(manifest, [])
    assert incomplete["complete"] is False
    assert incomplete["books_pending"] == 1

    record = {
        "document": "alpha.txt",
        "task_id": "task",
        "folder_entry_id": "folder",
        "summary_characters": 120,
        "summary_path": "/tmp/summary.md",
        "quality": {"fidelity": 95},
        "status": "VALID",
        "error": "",
    }
    complete = audit_corpus_coverage(manifest, [record])
    assert complete["complete"] is True
    assert complete["books_discovered"] == complete["books_processed"]
    assert complete["books_processed"] == complete["books_summarized"]
    assert complete["books_summarized"] == complete["books_evaluated"]
    assert complete["books"][0]["status"] == "VALID"


def test_corpus_size_and_chunk_classification() -> None:
    assert classify_size(9_999) == "SMALL"
    assert classify_size(10_000) == "MEDIUM"
    assert classify_size(50_000) == "LARGE"
    assert classify_size(150_000) == "VERY_LARGE"
    assert estimated_chunks(3_000) == 1
    assert estimated_chunks(3_001) == 2
    assert estimated_chunks(8_601) == 4


def test_dataset_catalog_lists_distinct_domains() -> None:
    docs = catalog_documents()
    ids = {item["id"] for item in docs}
    domains = {item["domain"] for item in docs}
    assert "asyncio-hattingh" in ids
    assert "synthetic-econ" in ids
    assert {"economics", "technical", "academic", "tutorial", "marketing"} <= domains
