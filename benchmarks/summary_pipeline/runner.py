from __future__ import annotations

import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .aggregation import aggregate_iteration
from .client import BrevioApiClient
from .baseline import baseline_from_iteration
from .corpus import (
    SUPPORTED_DOCUMENT_SUFFIXES,
    audit_corpus_coverage,
    build_corpus_manifest,
    write_manifest,
)
from .decision import compare_iterations, iteration_valid_for_comparison
from .evaluator import compare_level_progression
from .fingerprint import (
    benchmark_code_sha,
    dataset_sha,
    experiment_fingerprint,
    git_dirty,
    git_sha,
    gold_facts_sha,
    matrix_hash,
    prompt_templates_sha,
)
from .gold import document_id_for_name
from .job_validation import classify_job
from .judge import judge_metadata
from .lint import evaluate_lint
from .models import (
    BENCHMARK_VERSION,
    COMPARISON_MATRIX,
    DEFAULT_BENCHMARK_MODELS,
    JUDGE_VERSION,
    SCORER_VERSION,
    BenchmarkConfig,
    BenchmarkPaths,
    ExperimentRecord,
    JobStatus,
    record_from_mapping,
)
from .quality import evaluate_quality
from .report import render_report
from .runtime import audit_effective_model, capture_ollama_runtime, requested_context_for_model
from .source import profile_source
from .telemetry import snapshot_for_folder
from core.shared.utils.environment import llm_temperature

DOCUMENT_SUFFIXES = set(SUPPORTED_DOCUMENT_SUFFIXES)
DEFAULT_DOCS_DIR = Path("/home/psych/Descargas/libros")
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]


def discover_documents(docs_dir: Path) -> list[Path]:
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"Documents directory not found: {docs_dir}")
    files = [
        path
        for path in sorted(docs_dir.iterdir())
        if path.is_file() and path.suffix.lower() in DOCUMENT_SUFFIXES
    ]
    if not files:
        raise FileNotFoundError(f"No PDF/DOCX/TXT documents found in {docs_dir}")
    return files


def _summary_filename(
    iteration_id: str,
    document: Path,
    config: BenchmarkConfig,
    folder_entry_id: str,
) -> str:
    return (
        f"{iteration_id}_{document.stem}_{config.slug()}_{folder_entry_id[:8]}.md"
    )


def _archive_audit_artifacts(
    *,
    folder_entry_id: str,
    logs_json: Path,
    paths: BenchmarkPaths,
) -> list[str]:
    if not folder_entry_id:
        return []
    configured = os.getenv("BREVIO_AUDIT_DIR")
    candidates = [Path(configured)] if configured else []
    try:
        candidates.append(logs_json.resolve().parents[3] / "data" / "audit")
    except IndexError:
        pass
    candidates.append(Path("data/audit").resolve())
    source_dir = next((path for path in candidates if path.is_dir()), None)
    if source_dir is None:
        return []
    destination = paths.audit / folder_entry_id
    destination.mkdir(parents=True, exist_ok=True)
    archived: list[str] = []
    for source in sorted(source_dir.glob(f"{folder_entry_id}_*.txt")):
        target = destination / source.name
        shutil.copy2(source, target)
        archived.append(str(target))
    return archived


def _native_language(source: dict[str, Any], fallback: str) -> str:
    detected = str(source.get("language_detected") or "").strip().lower()
    if detected in {"spanish", "english"}:
        return detected
    text = str(source.get("text") or "")
    if text:
        from .lint import detect_language

        label = detect_language(text)
        if label in {"spanish", "english"}:
            return label
    return fallback


def configs_for_document(
    document: Path,
    suite: str,
    base: BenchmarkConfig,
    models: Sequence[str] | None = None,
    *,
    native_language: str | None = None,
) -> list[BenchmarkConfig]:
    resolved_models = [item.strip() for item in (models or ()) if item.strip()]
    if not resolved_models:
        resolved_models = [base.model] if suite != "matrix" else list(
            DEFAULT_BENCHMARK_MODELS
        )
    templates = COMPARISON_MATRIX if suite == "matrix" else (base,)
    configs: list[BenchmarkConfig] = []
    for model in resolved_models:
        for item in templates:
            language = item.language
            if language in {"auto", ""} or suite == "matrix":
                language = native_language or item.language or base.language
            if suite != "matrix":
                language = base.language if base.language not in {"auto", ""} else language
            configs.append(
                BenchmarkConfig(
                    summary_level=item.summary_level if suite == "matrix" else base.summary_level,
                    category=item.category if suite == "matrix" else base.category,
                    style=item.style if suite == "matrix" else base.style,
                    output_format=base.output_format,
                    language=language,
                    model=model,
                )
            )
    return configs


def matrix_templates_for_document(document: Path) -> tuple[BenchmarkConfig, ...]:
    del document
    return COMPARISON_MATRIX


def resolve_configs(
    suite: str,
    base: BenchmarkConfig,
    models: Sequence[str] | None = None,
) -> list[BenchmarkConfig]:
    resolved_models = [item.strip() for item in (models or ()) if item.strip()]
    if not resolved_models:
        resolved_models = [base.model] if suite != "matrix" else list(
            DEFAULT_BENCHMARK_MODELS
        )
    templates = list(COMPARISON_MATRIX) if suite == "matrix" else [base]
    configs: list[BenchmarkConfig] = []
    for model in resolved_models:
        for item in templates:
            configs.append(
                BenchmarkConfig(
                    summary_level=item.summary_level,
                    category=item.category,
                    style=item.style,
                    output_format=base.output_format,
                    language=item.language,
                    model=model,
                )
            )
    return configs


def persist_results(
    payload: dict[str, Any],
    paths: BenchmarkPaths,
    *,
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    paths.ensure()
    if baseline is not None:
        comparison = compare_iterations(baseline, payload)
        comparison["baseline_id"] = baseline.get("iteration_id")
        payload["comparison"] = comparison
        payload["baseline"] = baseline_from_iteration(baseline)
    comparable, reasons = iteration_valid_for_comparison(payload)
    payload["validity"] = {
        "valid_for_comparison": comparable,
        "reasons": reasons,
    }
    payload["report"] = render_report(payload)
    iteration_id = str(payload.get("iteration_id") or "iteration")
    out = paths.iterations / f"{iteration_id}.json"
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    out.write_text(serialized, encoding="utf-8")
    last_run = paths.results / "last_run.json"
    last_run.write_text(serialized, encoding="utf-8")
    latest = paths.results / "latest.json"
    if comparable:
        latest.write_text(serialized, encoding="utf-8")
        payload["latest_promoted"] = True
    else:
        payload["latest_promoted"] = False
        print(
            json.dumps(
                {
                    "event": "latest_not_promoted",
                    "reasons": reasons,
                    "path": str(out),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    print(
        json.dumps({"event": "iteration_saved", "path": str(out)}, ensure_ascii=False),
        flush=True,
    )
    print(payload["report"], flush=True)
    return payload


def run_experiments(
    *,
    documents: Sequence[Path],
    configs: Sequence[BenchmarkConfig],
    client: BrevioApiClient,
    paths: BenchmarkPaths,
    logs_json: Path,
    iteration_id: str,
    job_timeout: float,
    poll_seconds: float,
    suite: str = "single",
    base: BenchmarkConfig | None = None,
    models: Sequence[str] | None = None,
    resume: bool = False,
    judge_model: str = "",
    cli_command: Sequence[str] | None = None,
    runtime_override: dict[str, Any] | None = None,
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    paths.ensure()
    experiments: list[ExperimentRecord] = []
    checkpoint_path = paths.iterations / f"{iteration_id}.checkpoint.json"
    if resume and checkpoint_path.is_file():
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        experiments = [
            record_from_mapping(item)
            for item in checkpoint.get("experiments", [])
            if isinstance(item, dict)
        ]
    source_cache: dict[str, dict[str, Any]] = {}
    corpus_root = Path(
        os.path.commonpath(
            [str(Path(document).resolve().parent) for document in documents]
        )
    )
    manifest = build_corpus_manifest(corpus_root)
    manifest_path = paths.root / "corpus_manifest.json"
    write_manifest(manifest_path, manifest)
    configured_models = sorted({config.model for config in configs}) or ["qwen3:14b"]
    runtime_before = runtime_override or {
        model: capture_ollama_runtime(model) for model in configured_models
    }
    git_commit = git_sha(REPOSITORY_ROOT)
    code_sha = benchmark_code_sha(PACKAGE_ROOT)
    data_sha = dataset_sha(manifest)
    prompt_sha = prompt_templates_sha(REPOSITORY_ROOT)
    gold_sha = gold_facts_sha()
    planned_cells: list[dict[str, str]] = []
    for document in documents:
        document = document.resolve()
        if document.as_posix() not in source_cache:
            profile = profile_source(document)
            source_path = paths.sources / f"{document.stem}.txt"
            source_path.write_text(profile["text"], encoding="utf-8")
            stored = dict(profile)
            stored["extracted_path"] = str(source_path)
            stored["document_id"] = document_id_for_name(document.name)
            stored["language_detected"] = _native_language(stored, "spanish")
            source_cache[document.as_posix()] = stored
        native = source_cache[document.as_posix()].get("language_detected")
        for config in configs_for_document(
            document,
            suite,
            base or BenchmarkConfig(),
            models=models,
            native_language=str(native) if suite == "matrix" else None,
        ) if suite == "matrix" else list(configs):
            doc_id = source_cache[document.as_posix()]["document_id"]
            planned_cells.append(
                {
                    **config.to_dict(),
                    "document_id": doc_id,
                    "document": document.name,
                }
            )
    mtx_hash = matrix_hash(planned_cells)
    judge_id = judge_model or "disabled"

    for document in documents:
        document = document.resolve()
        if not document.is_file():
            raise FileNotFoundError(f"Document not found: {document}")
        source = source_cache[document.as_posix()]
        source_public = {key: value for key, value in source.items() if key != "text"}
        document_id = str(source.get("document_id") or document_id_for_name(document.name))
        native = str(source.get("language_detected") or "spanish")
        if suite == "matrix":
            document_configs = configs_for_document(
                document,
                suite,
                base or BenchmarkConfig(),
                models=models,
                native_language=native,
            )
        else:
            document_configs = list(configs)
        for config in document_configs:
            requested_ctx = requested_context_for_model(config.model)
            runtime_now = runtime_before.get(config.model) or {}
            fingerprint = experiment_fingerprint(
                git_commit=git_commit,
                code_sha=code_sha,
                dataset=data_sha,
                matrix=mtx_hash,
                document_id=document_id,
                source_sha=str(source.get("sha256_full") or source.get("sha256") or ""),
                config=config,
                requested_context=requested_ctx,
                judge_model=judge_id,
                prompt_hash=prompt_sha,
                gold_sha=gold_sha,
            )
            existing = next(
                (
                    item
                    for item in experiments
                    if item.fingerprint == fingerprint
                    and item.status in {JobStatus.VALID.value, JobStatus.TRUNCATED.value}
                    and item.summary_path
                    and item.summary_characters > 0
                ),
                None,
            )
            if resume and existing is not None:
                print(
                    json.dumps(
                        {
                            "event": "job_resumed",
                            "iteration": iteration_id,
                            "document": document.name,
                            "fingerprint": fingerprint,
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                continue
            started = time.monotonic()
            error = ""
            folder_entry_id = ""
            task_id = ""
            summary = ""
            summary_path = paths.summaries / _summary_filename(
                iteration_id, document, config, "pending"
            )
            try:
                job = client.submit_document(document, config)
                folder_entry_id = job.folder_entry_id
                task_id = job.task_id
                summary_path = paths.summaries / _summary_filename(
                    iteration_id, document, config, folder_entry_id
                )
                print(
                    json.dumps(
                        {
                            "event": "job_submitted",
                            "iteration": iteration_id,
                            "document": document.name,
                            "task_id": task_id,
                            "folder_entry_id": folder_entry_id,
                            "configuration": config.to_dict(),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                client.wait_for_result(
                    job,
                    timeout_seconds=job_timeout,
                    poll_seconds=poll_seconds,
                )
                summary = client.download_summary(job.folder_entry_id)
                summary_path.write_text(summary, encoding="utf-8")
            except TimeoutError as exc:
                error = str(exc)
            except Exception as exc:
                error = str(exc)
            wall = time.monotonic() - started
            telemetry = snapshot_for_folder(logs_json, folder_entry_id)
            telemetry_payload = telemetry.to_dict()
            telemetry_payload["audit_artifacts"] = _archive_audit_artifacts(
                folder_entry_id=folder_entry_id,
                logs_json=logs_json,
                paths=paths,
            )
            lint = evaluate_lint(
                source_text=source.get("text") or "",
                summary=summary,
                config=config,
                telemetry=telemetry,
            )
            status, reasons, warnings, lint = classify_job(
                summary=summary,
                error=error,
                config=config,
                telemetry=telemetry,
                runtime=runtime_now,
                lint=lint,
                source_text=source.get("text") or "",
            )
            quality = evaluate_quality(
                source_text=source.get("text") or "",
                summary=summary,
                config=config,
                document_name=document.name,
                telemetry=telemetry,
                lint=lint,
                status=status.value,
            )
            judge_info = judge_metadata(judge_model, config.model)
            if judge_info["equals_generator"]:
                warnings.append("JUDGE_EQUALS_GENERATOR")
            record = ExperimentRecord(
                iteration_id=iteration_id,
                document=document.name,
                document_path=str(document),
                document_id=document_id,
                config=config.to_dict(),
                folder_entry_id=folder_entry_id,
                task_id=task_id,
                summary_path=str(summary_path) if summary else "",
                summary_characters=len(summary),
                summary_words=len(summary.split()),
                wall_seconds=round(wall, 3),
                source=source_public,
                telemetry=telemetry_payload,
                quality=quality.to_dict(),
                heuristic_lint=lint.to_dict(),
                error=error,
                status=status.value,
                invalid_reasons=reasons,
                warnings=warnings,
                fingerprint=fingerprint,
                cell_key=list(config.cell_key(document_id)),
                judge=judge_info,
            )
            experiments.append(record)
            checkpoint_payload = {
                "iteration_id": iteration_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "experiments": [item.to_dict() for item in experiments],
            }
            checkpoint_temporary = checkpoint_path.with_suffix(".json.tmp")
            checkpoint_temporary.write_text(
                json.dumps(checkpoint_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            checkpoint_temporary.replace(checkpoint_path)

    experiment_payload = [item.to_dict() for item in experiments]
    corpus_audit = audit_corpus_coverage(manifest, experiment_payload)
    required_model = (
        configured_models[0] if len(configured_models) == 1 else "qwen3:14b"
    )
    aggregates = aggregate_iteration(experiment_payload)
    provenance = {
        "git_sha": git_commit,
        "git_dirty": git_dirty(REPOSITORY_ROOT),
        "dataset_sha": data_sha,
        "dataset_manifest_sha": data_sha,
        "benchmark_version": BENCHMARK_VERSION,
        "prompt_hash": prompt_sha,
        "gold_sha": gold_sha,
        "model": configured_models,
        "model_digest": {
            model: (runtime_before.get(model) or {}).get("model_digest")
            for model in configured_models
        },
        "requested_context": {
            model: (runtime_before.get(model) or {}).get("requested_context")
            for model in configured_models
        },
        "effective_context": {
            model: (runtime_before.get(model) or {}).get(
                "effective_loaded_context_length"
            )
            for model in configured_models
        },
        "temperature": llm_temperature(),
        "seed": None,
        "cli_command": list(cli_command or sys.argv),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "matrix_hash": mtx_hash,
        "scorer_version": SCORER_VERSION,
        "judge_version": JUDGE_VERSION,
        "benchmark_code_sha": code_sha,
        "judge_model": judge_id,
    }
    payload = {
        "iteration_id": iteration_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "n_experiments": len(experiments),
        "corpus_manifest": str(manifest_path),
        "corpus_audit": corpus_audit,
        "model_audit": audit_effective_model(
            experiment_payload,
            required_model=required_model,
        ),
        "runtime": {
            "before": runtime_before,
            "after": runtime_override
            or {
                model: capture_ollama_runtime(model) for model in configured_models
            },
        },
        "provenance": provenance,
        "experiments": experiment_payload,
        "level_progression": compare_level_progression(experiment_payload),
        "aggregates": aggregates,
    }
    return persist_results(payload, paths, baseline=baseline)
