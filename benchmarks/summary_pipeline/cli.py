from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

from .client import BrevioApiClient, resolve_benchmark_credentials
from .models import DEFAULT_BENCHMARK_MODELS, BenchmarkConfig, BenchmarkPaths
from .runner import (
    DEFAULT_DOCS_DIR,
    configs_for_document,
    discover_documents,
    resolve_configs,
    run_experiments,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate summaries through the live Brevio API, attach pipeline "
            "telemetry from logs.json, and score each summary against the source."
        )
    )
    parser.add_argument(
        "documents",
        nargs="*",
        type=Path,
        help="Explicit files. If omitted, every PDF/DOCX/TXT in --docs-dir is used.",
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path(os.getenv("BREVIO_BENCHMARK_DOCS_DIR", str(DEFAULT_DOCS_DIR))),
        help="Directory of books to benchmark (default: /home/psych/Descargas/libros)",
    )
    parser.add_argument("--summary-level", default="very_detailed")
    parser.add_argument("--category", default="simple_summary")
    parser.add_argument("--style", default="default")
    parser.add_argument("--format", dest="output_format", default="markdown")
    parser.add_argument("--language", default="spanish")
    parser.add_argument(
        "--model",
        dest="models",
        action="append",
        help=(
            "Model to run. Repeat or omit: matrix defaults to qwen3:14b."
        ),
    )
    parser.add_argument(
        "--models",
        dest="models_csv",
        default=None,
        help="Comma-separated models (overrides repeated --model)",
    )
    parser.add_argument(
        "--suite",
        choices=("single", "matrix"),
        default="single",
        help="single = CLI flags; matrix = mandatory category/style/level grid",
    )
    parser.add_argument("--iteration", default="iteration")
    parser.add_argument(
        "--api-url", default=os.getenv("BREVIO_API_URL", "http://localhost:8000")
    )
    parser.add_argument("--identity", default=os.getenv("BREVIO_BENCHMARK_IDENTITY"))
    parser.add_argument("--password", default=os.getenv("BREVIO_BENCHMARK_PASSWORD"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(os.getenv("BREVIO_BENCHMARK_OUTPUT", "benchmark")),
    )
    parser.add_argument(
        "--logs-json",
        type=Path,
        default=Path(
            os.getenv(
                "BREVIO_LOGS_JSON",
                "core/brevio_api/logs/logs.json",
            )
        ),
    )
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--job-timeout", type=float, default=7200.0)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume VALID jobs whose experiment fingerprint still matches.",
    )
    parser.add_argument(
        "--judge-model",
        default="",
        help="Optional semantic judge. Leave empty (default) to disable. Do not use the generator model.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Previous iteration JSON for KEEP/REVERT/INCONCLUSIVE comparison.",
    )
    parser.add_argument(
        "--rescore",
        type=Path,
        default=None,
        help="Re-score an existing iteration JSON. Never writes results/latest.json.",
    )
    return parser


def _load_baseline(path: Path | None, repository_root: Path) -> dict | None:
    if path is None:
        return None
    resolved = path if path.is_absolute() else repository_root / path
    return json.loads(resolved.read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    repository_root = Path(__file__).resolve().parents[2]
    load_dotenv(repository_root / ".env")
    args = build_parser().parse_args(argv)
    if args.rescore:
        from .rescore import rescore_iteration_file

        source = args.rescore
        if not source.is_absolute():
            source = repository_root / source
        destination = source.with_name(f"{source.stem}_rescored.json")
        payload = rescore_iteration_file(source, destination)
        print(payload.get("report") or "", flush=True)
        print(
            json.dumps(payload.get("validity") or {}, ensure_ascii=False, indent=2),
            flush=True,
        )
        return 0
    identity, password = resolve_benchmark_credentials(args.identity, args.password)
    output = args.output
    if not output.is_absolute():
        output = repository_root / output
    logs_json = args.logs_json
    if not logs_json.is_absolute():
        logs_json = repository_root / logs_json
    paths = BenchmarkPaths(output)
    paths.ensure()
    if args.models_csv:
        models = [item.strip() for item in args.models_csv.split(",") if item.strip()]
    elif args.models:
        models = list(args.models)
    elif args.suite == "matrix":
        models = list(DEFAULT_BENCHMARK_MODELS)
    else:
        models = ["qwen3:14b"]
    base = BenchmarkConfig(
        summary_level=args.summary_level,
        category=args.category,
        style=args.style,
        output_format=args.output_format,
        language=args.language,
        model=models[0],
    )
    configs = resolve_configs(args.suite, base, models=models)
    documents = [path.resolve() for path in args.documents]
    if not documents:
        docs_dir = args.docs_dir
        if not docs_dir.is_absolute():
            docs_dir = repository_root / docs_dir
        documents = discover_documents(docs_dir)
    plan = {
        path.name: [cfg.to_dict() for cfg in configs_for_document(path, args.suite, base, models)]
        for path in documents
    }
    print(
        json.dumps(
            {
                "event": "suite_start",
                "iteration": args.iteration,
                "suite": args.suite,
                "n_configs": len(configs),
                "n_jobs": sum(len(items) for items in plan.values()),
                "n_models": len(models),
                "models": models,
                "documents": [path.name for path in documents],
                "configurations": [cfg.to_dict() for cfg in configs],
                "jobs_by_document": plan,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    with BrevioApiClient(
        args.api_url, identity=identity, password=password
    ) as client:
        client.authenticate()
        print(
            json.dumps(
                {
                    "event": "authenticated",
                    "identity": client.identity,
                    "endpoint": "/auth/login",
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        payload = run_experiments(
            documents=documents,
            configs=configs,
            client=client,
            paths=paths,
            logs_json=logs_json,
            iteration_id=args.iteration,
            job_timeout=args.job_timeout,
            poll_seconds=args.poll_seconds,
            suite=args.suite,
            base=base,
            models=models,
            resume=args.resume,
            judge_model=args.judge_model,
            cli_command=sys.argv if argv is None else ["benchmark.py", *list(argv)],
            baseline=_load_baseline(args.baseline, repository_root),
        )
    validity = payload.get("validity") or {}
    counts = (payload.get("aggregates") or {}).get("counts") or {}
    print(json.dumps({"aggregates": payload.get("aggregates")}, ensure_ascii=False, indent=2))
    failed = int(counts.get("failed_jobs") or 0)
    if failed and int(counts.get("valid_jobs") or 0) == 0:
        print(f"{failed} experiment(s) failed and none are VALID.", file=sys.stderr)
        return 2
    if not payload.get("experiments"):
        print("No summary generated.", file=sys.stderr)
        return 2
    if not validity.get("valid_for_comparison"):
        print(
            "Iteration is not valid_for_comparison: "
            + "; ".join(validity.get("reasons") or []),
            file=sys.stderr,
        )
        return 0
    return 0
