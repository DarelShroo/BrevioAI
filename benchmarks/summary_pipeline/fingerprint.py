from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from .models import BENCHMARK_VERSION, JUDGE_VERSION, SCORER_VERSION, BenchmarkConfig


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_sha(repository_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def git_dirty(repository_root: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return True
    return bool(result.stdout.strip())


def benchmark_code_sha(package_root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(package_root.glob("*.py"))
    for path in files:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\n")
    return digest.hexdigest()


def canonical_json(payload: Mapping[str, Any] | Sequence[Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def matrix_hash(cells: Sequence[Mapping[str, str]]) -> str:
    ordered = sorted(canonical_json(dict(cell)) for cell in cells)
    return _sha256_text("\n".join(ordered))


PROMPT_HASH_RELATIVE_PATHS = (
    "core/brevio/services/summary_service.py",
    "core/brevio/services/advanced_content_generator.py",
    "core/brevio/models/prompt_config_model.py",
    "core/brevio/protocols/language_prompt_protocol.py",
)


def gold_facts_sha(gold_dir: Path | None = None) -> str:
    directory = gold_dir or Path(__file__).resolve().parent / "dataset" / "gold"
    digest = hashlib.sha256()
    for path in sorted(directory.glob("*.json")):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\n")
    return digest.hexdigest()


def prompt_templates_sha(repository_root: Path) -> str:
    digest = hashlib.sha256()
    for relative in PROMPT_HASH_RELATIVE_PATHS:
        path = repository_root / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        if path.is_file():
            digest.update(path.read_bytes())
        digest.update(b"\n")
    return digest.hexdigest()


def dataset_sha(manifest: Mapping[str, Any]) -> str:
    books = []
    for book in manifest.get("books") or []:
        books.append(
            {
                "document_id": book.get("document_id") or book.get("corpus_id") or "",
                "name": book.get("name") or "",
                "sha256": book.get("sha256") or "",
                "language_detected": book.get("language_detected") or "",
            }
        )
    books.sort(key=lambda item: str(item["document_id"]))
    return _sha256_text(canonical_json({"books": books}))


def experiment_fingerprint(
    *,
    git_commit: str | None,
    code_sha: str,
    dataset: str,
    matrix: str,
    document_id: str,
    source_sha: str,
    config: BenchmarkConfig | Mapping[str, str],
    requested_context: int | None,
    judge_model: str,
    scorer_version: str = SCORER_VERSION,
    judge_version: str = JUDGE_VERSION,
    benchmark_version: str = BENCHMARK_VERSION,
    prompt_hash: str = "",
    gold_sha: str = "",
) -> str:
    cfg = config.to_dict() if isinstance(config, BenchmarkConfig) else dict(config)
    payload = {
        "benchmark_version": benchmark_version,
        "scorer_version": scorer_version,
        "judge_version": judge_version,
        "git_sha": git_commit or "",
        "benchmark_code_sha": code_sha,
        "dataset_sha": dataset,
        "matrix_hash": matrix,
        "document_id": document_id,
        "source_sha": source_sha,
        "config": cfg,
        "requested_context": requested_context,
        "judge_model": judge_model or "disabled",
        "prompt_hash": prompt_hash or "",
        "gold_sha": gold_sha or "",
    }
    return _sha256_text(canonical_json(payload))
