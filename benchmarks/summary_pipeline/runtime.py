from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from .models import DEFAULT_REQUESTED_CONTEXT
from core.shared.utils.environment import llm_temperature


def _ollama_native_url(path: str) -> str:
    configured = os.getenv(
        "OLLAMA_API_URL", "http://host.docker.internal:11434/v1"
    )
    parsed = urlsplit(configured)
    base_path = parsed.path.rstrip("/")
    if base_path.endswith("/v1"):
        base_path = base_path[:-3]
    return urlunsplit(
        (parsed.scheme, parsed.netloc, f"{base_path}{path}", "", "")
    )


def requested_context_for_model(model: str) -> int:
    try:
        from core.shared.enums.model import ModelType
        from core.shared.utils.model_capabilities import get_model_capabilities

        caps = get_model_capabilities(ModelType(model))
        return int(caps.context_window)
    except Exception:
        if "qwen3:14b" in model:
            return DEFAULT_REQUESTED_CONTEXT
        return DEFAULT_REQUESTED_CONTEXT


def capture_ollama_runtime(model: str) -> dict[str, Any]:
    requested = requested_context_for_model(model)
    snapshot: dict[str, Any] = {
        "requested_model": model,
        "temperature": llm_temperature(),
        "seed": None,
        "endpoint": _ollama_native_url(""),
        "available": False,
        "error": "",
        "requested_context": requested,
        "effective_loaded_context_length": None,
        "native_context_length": None,
        "context_mismatch": False,
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            show_response = client.post(
                _ollama_native_url("/api/show"),
                json={"model": model},
            )
            show_response.raise_for_status()
            show = show_response.json()
            ps_response = client.get(_ollama_native_url("/api/ps"))
            ps_response.raise_for_status()
            running = ps_response.json().get("models") or []
        active = next(
            (
                item
                for item in running
                if str(item.get("model") or item.get("name") or "") == model
            ),
            None,
        )
        model_info = show.get("model_info") or {}
        effective = (active or {}).get("context_length")
        native = model_info.get("qwen3.context_length") or model_info.get(
            "llama.context_length"
        )
        mismatch = (
            effective is not None
            and int(effective) != int(requested)
        )
        snapshot.update(
            {
                "available": True,
                "model_digest": str((active or {}).get("digest") or ""),
                "details": show.get("details") or {},
                "parameter_count": model_info.get("general.parameter_count"),
                "native_context_length": native,
                "effective_loaded_context_length": effective,
                "active_model": str(
                    (active or {}).get("model")
                    or (active or {}).get("name")
                    or ""
                ),
                "context_mismatch": mismatch,
            }
        )
    except Exception as exc:
        snapshot["error"] = f"{type(exc).__name__}: {exc}"
    return snapshot


def audit_effective_model(
    records: list[dict[str, Any]],
    *,
    required_model: str,
) -> dict[str, Any]:
    requested = sorted(
        {
            str((row.get("config") or {}).get("model") or "")
            for row in records
        }
    )
    observed = sorted(
        {
            str((row.get("telemetry") or {}).get("model") or "")
            for row in records
            if not row.get("error")
            and (row.get("telemetry") or {}).get("telemetry_status") == "present"
        }
    )
    mismatches = [
        {
            "document": row.get("document"),
            "requested": (row.get("config") or {}).get("model"),
            "observed": (row.get("telemetry") or {}).get("model"),
        }
        for row in records
        if not row.get("error")
        and (row.get("telemetry") or {}).get("telemetry_status") == "present"
        and str((row.get("config") or {}).get("model") or "")
        != str((row.get("telemetry") or {}).get("model") or "")
    ]
    return {
        "required_model": required_model,
        "requested_models": requested,
        "observed_models": observed,
        "mismatches": mismatches,
        "all_match": (
            requested == [required_model]
            and (not observed or observed == [required_model])
            and not mismatches
        ),
    }
