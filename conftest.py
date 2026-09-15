"""Keep the default pytest run hermetic: no .env, Mongo, Redis, LLM, or HuggingFace."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import MagicMock

import dotenv
import httpx
import pytest

dotenv.load_dotenv = lambda *args, **kwargs: False  # type: ignore[assignment]

_ISOLATED_ENV = {
    "ENVIRONMENT": "test",
    "MONGODB_URI": "mongodb://127.0.0.1:27017/brevio_pytest_isolated",
    "OPENAI_API_KEY": "sk-pytest-isolated-not-real",
    "DEEPSEEK_API_KEY": "sk-pytest-isolated-not-real",
    "GOOGLE_API_KEY": "sk-pytest-isolated-not-real",
    "OLLAMA_API_KEY": "sk-pytest-isolated-not-real",
    "API_KEY": "pytest-isolated-api-key",
    "SECRET_TOKEN_KEY": "pytest-isolated-secret",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
    "REFRESH_TOKEN_EXPIRE_DAYS": "7",
    "COOKIE_SECURE": "false",
    "CORS_ORIGINS": "http://localhost:3000",
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_DATASETS_OFFLINE": "1",
    "TOKENIZERS_PARALLELISM": "false",
    "PROVIDER_QUOTA_ENABLED": "false",
    "MAX_TOKEN_PER_MINUTE": "200000",
    "BREVIO_KEEP_PARTIALS": "false",
    "BREVIO_ALLOW_MAP_ORIGINAL_TEXT_FALLBACK": "false",
    "CELERY_BROKER_URL": "memory://",
    "CELERY_RESULT_BACKEND": "cache+memory://",
}

for _key, _value in _ISOLATED_ENV.items():
    os.environ[_key] = _value

_ALLOWED_HTTP_HOSTS = frozenset({"testserver", "test"})

collect_ignore = ["benchmark.py"]
collect_ignore_glob = [
    "benchmarks/**",
    "frontend/**",
    "data/**",
    "benchmark/**",
    "**/.tmp/**",
    "**/.pytest_cache/**",
    "**/.pytest_basetemp/**",
]

_ARTIFACT_DIRNAME = ".tmp"


def _suite_root_for(path: Path, config: pytest.Config) -> Path:
    resolved = path.resolve()
    for relative in config.getini("testpaths") or []:
        root = (config.rootpath / relative).resolve()
        try:
            resolved.relative_to(root)
            return root
        except ValueError:
            continue
    for parent in (resolved, *resolved.parents):
        if parent.name == "tests":
            return parent
    return (config.rootpath / "core" / "brevio" / "tests").resolve()


def _safe_test_dirname(node: pytest.Item) -> str:
    raw = getattr(node, "name", None) or "test"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._") or "test"
    return safe[:80]


def _ensure_suite_tmp(suite: Path) -> Path:
    tmp = suite / _ARTIFACT_DIRNAME
    tmp.mkdir(parents=True, exist_ok=True)
    return tmp


def _assert_http_allowed(request: httpx.Request) -> None:
    host = (request.url.host or "").lower()
    if host in _ALLOWED_HTTP_HOSTS:
        return
    raise RuntimeError(
        f"Tests must not make outbound HTTP calls: blocked {request.url}"
    )


_ORIGINAL_ASYNC_SEND = httpx.AsyncClient.send
_ORIGINAL_SYNC_SEND = httpx.Client.send


async def _guarded_async_send(
    self: httpx.AsyncClient, request: httpx.Request, *args: Any, **kwargs: Any
) -> httpx.Response:
    _assert_http_allowed(request)
    return await _ORIGINAL_ASYNC_SEND(self, request, *args, **kwargs)


def _guarded_sync_send(
    self: httpx.Client, request: httpx.Request, *args: Any, **kwargs: Any
) -> httpx.Response:
    _assert_http_allowed(request)
    return _ORIGINAL_SYNC_SEND(self, request, *args, **kwargs)


httpx.AsyncClient.send = _guarded_async_send  # type: ignore[method-assign]
httpx.Client.send = _guarded_sync_send  # type: ignore[method-assign]


def _isolated_async_db_init(self: Any, uri: str | None = None) -> None:
    self.client = MagicMock()
    self.db = MagicMock()


def _isolated_database(self: Any, database_name: str = "brevio") -> MagicMock:
    if self.db is None:
        self.db = MagicMock()
    return self.db


async def _isolated_verify_connection(self: Any) -> None:
    return None


async def _isolated_close(self: Any) -> None:
    self.client = None
    self.db = None


def pytest_configure(config: pytest.Config) -> None:
    tests_root = Path(config.rootpath) / "core" / "brevio" / "tests"
    cache_dir = tests_root / ".pytest_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    config.option.cache_dir = str(cache_dir)
    if not getattr(config.option, "basetemp", None):
        factory_tmp = tests_root / ".pytest_basetemp"
        factory_tmp.mkdir(parents=True, exist_ok=True)
        config.option.basetemp = str(factory_tmp)

    from core.brevio_api.core.database import AsyncDB

    AsyncDB.__init__ = _isolated_async_db_init  # type: ignore[method-assign]
    AsyncDB.database = _isolated_database  # type: ignore[method-assign]
    AsyncDB.verify_connection = _isolated_verify_connection  # type: ignore[method-assign]
    AsyncDB.close = _isolated_close  # type: ignore[method-assign]

    try:
        from transformers.models.auto.tokenization_auto import AutoTokenizer

        def _offline_from_pretrained(cls: Any, *args: Any, **kwargs: Any) -> Any:
            raise OSError("Tests are offline: tokenizer downloads are disabled")

        AutoTokenizer.from_pretrained = classmethod(_offline_from_pretrained)  # type: ignore[method-assign]
    except Exception:
        pass


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    from core.shared.utils.environment import env_flag

    run_redis = env_flag("BREVIO_RUN_REDIS_TESTS")
    if run_redis:
        return
    skip_redis = pytest.mark.skip(
        reason="Redis tests are opt-in; set BREVIO_RUN_REDIS_TESTS=1"
    )
    for item in items:
        if item.get_closest_marker("redis"):
            item.add_marker(skip_redis)


@pytest.fixture
def tmp_path(request: pytest.FixtureRequest) -> Path:
    test_path = Path(str(getattr(request, "path", request.fspath)))
    suite = _suite_root_for(test_path, request.config)
    base = _ensure_suite_tmp(suite)
    name = _safe_test_dirname(request.node)
    candidate = base / name
    index = 0
    while candidate.exists():
        index += 1
        candidate = base / f"{name}_{index}"
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


@pytest.fixture(autouse=True)
def _isolate_runtime_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[None]:
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    logs_path = tmp_path / "logs.json"
    monkeypatch.setenv("PROVIDER_QUOTA_ENABLED", "false")
    monkeypatch.setenv("BREVIO_KEEP_PARTIALS", "false")
    monkeypatch.setenv("BREVIO_ALLOW_MAP_ORIGINAL_TEXT_FALLBACK", "false")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    monkeypatch.setenv("MAX_TOKEN_WAIT", "1")
    monkeypatch.setenv("EVENTS_SSE_HEARTBEAT_SECONDS", "1")
    monkeypatch.delenv("PROVIDER_QUOTA_CONFIG_PATH", raising=False)
    monkeypatch.delenv("JOB_MAX_PROVIDER_REQUESTS", raising=False)
    monkeypatch.delenv("EVENTS_REDIS_URL", raising=False)
    monkeypatch.setattr(
        "core.brevio.services.summary_service.AUDIT_DIR",
        str(audit_dir),
    )
    monkeypatch.setattr(
        "core.brevio.services.summary_service.dump_audit",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "core.shared.utils.json_data_utils.DEFAULT_LOGS_PATH",
        str(logs_path),
    )
    from core.brevio_api.events.broker import reset_event_broker

    reset_event_broker()
    yield
    reset_event_broker()
