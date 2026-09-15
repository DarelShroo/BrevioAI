from __future__ import annotations

import json
import mimetypes
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .models import BenchmarkConfig

DEFAULT_BENCHMARK_IDENTITY = "Darelsm2"
DEFAULT_BENCHMARK_PASSWORD = "A123@test"
ACCESS_COOKIE_NAME = "brevio_access"


class BenchmarkApiError(RuntimeError):
    pass


def resolve_benchmark_credentials(
    identity: str | None = None,
    password: str | None = None,
) -> tuple[str, str]:
    resolved_identity = (
        identity
        or os.getenv("BREVIO_BENCHMARK_IDENTITY")
        or DEFAULT_BENCHMARK_IDENTITY
    ).strip()
    resolved_password = (
        password
        or os.getenv("BREVIO_BENCHMARK_PASSWORD")
        or DEFAULT_BENCHMARK_PASSWORD
    )
    if not resolved_identity or not resolved_password:
        raise BenchmarkApiError(
            "Benchmark credentials are required. Set "
            "BREVIO_BENCHMARK_IDENTITY and BREVIO_BENCHMARK_PASSWORD"
        )
    return resolved_identity, resolved_password


@dataclass
class SubmittedJob:
    task_id: str
    folder_entry_id: str
    submitted_at_monotonic: float


class BrevioApiClient:
    def __init__(
        self,
        base_url: str,
        *,
        identity: str | None = None,
        password: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.identity, self.password = resolve_benchmark_credentials(
            identity, password
        )
        self.token: str | None = None
        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout_seconds, connect=20.0),
            follow_redirects=True,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "BrevioApiClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def authenticate(self) -> str:
        last_error: Exception | None = None
        for attempt in range(5):
            try:
                response = self._http.post(
                    "/auth/login",
                    json={"identity": self.identity, "password": self.password},
                )
                payload = self._json_or_error(response, "login")
                token = self._token_from_auth_response(response, payload)
                if not token:
                    raise BenchmarkApiError("Login response did not contain a token")
                self.token = token
                return token
            except (httpx.TransportError, BenchmarkApiError) as exc:
                last_error = exc
                if attempt >= 4:
                    break
                time.sleep(min(16.0, 2.0 ** attempt))
        raise BenchmarkApiError("login failed after retries") from last_error

    def _refresh_session(self) -> str | None:
        response = self._http.post("/auth/refresh")
        if response.status_code >= 400:
            return None
        try:
            payload = response.json()
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        token = self._token_from_auth_response(response, payload)
        if token:
            self.token = token
        return token

    def _token_from_auth_response(
        self,
        response: httpx.Response,
        payload: dict[str, Any],
    ) -> str | None:
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict):
            raw = data.get("access_token")
            if raw:
                return str(raw)
        cookie = response.cookies.get(ACCESS_COOKIE_NAME) or self._http.cookies.get(
            ACCESS_COOKIE_NAME
        )
        if cookie:
            return str(cookie)
        return None

    def submit_document(
        self,
        document: Path,
        config: BenchmarkConfig,
    ) -> SubmittedJob:
        if self.token is None:
            self.authenticate()
        mime_type = mimetypes.guess_type(document.name)[0] or "application/octet-stream"
        last_error: Exception | None = None
        for attempt in range(5):
            try:
                with document.open("rb") as handle:
                    response = self._request(
                        "POST",
                        "/brevio/summary-documents",
                        files={"files": (document.name, handle, mime_type)},
                        data=config.to_form(),
                        timeout=None,
                    )
                payload = self._json_or_error(response, "summary submission")
                task_id = str(payload.get("task_id") or "")
                folder_entry_id = str(payload.get("folder_entry_id") or "")
                if not task_id:
                    raise BenchmarkApiError("Submission response did not contain task_id")
                if not folder_entry_id:
                    raise BenchmarkApiError(
                        "Submission response did not contain folder_entry_id; "
                        "the API cannot be polled deterministically"
                    )
                return SubmittedJob(
                    task_id=task_id,
                    folder_entry_id=folder_entry_id,
                    submitted_at_monotonic=time.monotonic(),
                )
            except (httpx.TransportError, BenchmarkApiError) as exc:
                last_error = exc
                if attempt >= 4 or not _is_retryable_client_error(exc):
                    raise
                self.token = None
                time.sleep(min(16.0, 2.0 ** attempt))
        raise BenchmarkApiError("summary submission failed after retries") from last_error

    def wait_for_result(
        self,
        job: SubmittedJob,
        *,
        result_index: int = 0,
        timeout_seconds: float = 7200.0,
        poll_seconds: float = 2.0,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        last_state: dict[str, Any] = {
            "status": "QUEUED",
            "phase": "QUEUED",
            "results": [],
        }
        while time.monotonic() < deadline:
            response = self._request(
                "POST",
                "/users/entries",
                json={"entries_refs": [job.folder_entry_id]},
            )
            payload = self._json_or_error(response, "job status polling")
            entries = payload.get("entries") or []
            if entries:
                results = entries[0].get("results") or []
                last_state = {
                    "status": "QUEUED",
                    "phase": "QUEUED",
                    "entry": entries[0],
                    "results": results,
                }
                matching = next(
                    (
                        item
                        for item in results
                        if int(item.get("index", -1)) == result_index
                    ),
                    results[result_index] if len(results) > result_index else None,
                )
                if matching:
                    last_state = dict(matching)
                    last_state["entry"] = entries[0]
                    status = str(matching.get("status") or "").upper()
                    if status == "COMPLETED":
                        return last_state
                    if status == "FAILED":
                        message = (
                            matching.get("error_message")
                            or matching.get("error_type")
                            or "Summary job failed"
                        )
                        raise BenchmarkApiError(
                            f"Summary job {job.folder_entry_id} failed: {message}"
                        )
            time.sleep(max(0.1, poll_seconds))
        raise TimeoutError(
            f"Summary job {job.folder_entry_id} did not finish within "
            f"{timeout_seconds:.0f}s; last state={last_state}"
        )

    def download_summary(
        self,
        folder_entry_id: str,
        *,
        result_index: int = 0,
    ) -> str:
        response = self._request(
            "GET",
            f"/brevio/download/{folder_entry_id}",
            params={"format": "md", "result_index": result_index},
            timeout=None,
        )
        if response.status_code >= 400:
            self._raise_http_error(response, "summary download")
        text = response.text
        if not text.strip():
            raise BenchmarkApiError("Downloaded summary is empty")
        return text

    def estimate_document(
        self,
        document: Path,
        config: BenchmarkConfig,
    ) -> dict[str, Any]:
        mime_type = mimetypes.guess_type(document.name)[0] or "application/octet-stream"
        with document.open("rb") as handle:
            response = self._request(
                "POST",
                "/brevio/estimate-documents",
                files={"files": (document.name, handle, mime_type)},
                data=config.to_form(),
                timeout=None,
            )
        return self._json_or_error(response, "document estimation")

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        retries = 1 if kwargs.get("files") is not None else 5
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                if self.token is None:
                    self.authenticate()
                headers = dict(kwargs.get("headers") or {})
                headers["Authorization"] = f"Bearer {self.token}"
                request_kwargs = dict(kwargs)
                request_kwargs["headers"] = headers
                response = self._http.request(method, url, **request_kwargs)
                if response.status_code == 401 and self.identity and self.password:
                    if not self._refresh_session():
                        self.authenticate()
                    headers["Authorization"] = f"Bearer {self.token}"
                    request_kwargs["headers"] = headers
                    response = self._http.request(method, url, **request_kwargs)
                if response.status_code in {502, 503, 504} and attempt + 1 < retries:
                    time.sleep(min(16.0, 2.0 ** attempt))
                    continue
                return response
            except httpx.TransportError as exc:
                last_error = exc
                if attempt + 1 >= retries:
                    raise
                time.sleep(min(16.0, 2.0 ** attempt))
        raise BenchmarkApiError(f"{method} {url} failed after retries") from last_error

    def _json_or_error(
        self,
        response: httpx.Response,
        operation: str,
    ) -> dict[str, Any]:
        if response.status_code >= 400:
            self._raise_http_error(response, operation)
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise BenchmarkApiError(
                f"{operation} returned non-JSON status={response.status_code}"
            ) from exc
        if not isinstance(payload, dict):
            raise BenchmarkApiError(f"{operation} returned a non-object JSON body")
        return payload

    @staticmethod
    def _raise_http_error(response: httpx.Response, operation: str) -> None:
        detail: Any
        try:
            payload = response.json()
            detail = payload.get("message") or payload.get("detail") or payload
        except Exception:
            detail = response.text[:1000]
        raise BenchmarkApiError(
            f"{operation} failed with HTTP {response.status_code}: {detail}"
        )


def _is_retryable_client_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return isinstance(exc, httpx.TransportError) or any(
        token in text
        for token in (
            "disconnected",
            "503",
            "502",
            "504",
            "unavailable",
            "high demand",
            "connection reset",
        )
    )
