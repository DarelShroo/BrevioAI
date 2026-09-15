from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).resolve().parent / "dataset" / "catalog.json"


def load_dataset_catalog(path: Path | None = None) -> dict[str, Any]:
    catalog_path = path or _CATALOG_PATH
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("dataset catalog must be an object")
    return payload


def catalog_documents(path: Path | None = None) -> list[dict[str, Any]]:
    return list(load_dataset_catalog(path).get("documents") or [])
