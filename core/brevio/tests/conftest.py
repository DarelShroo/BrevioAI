import pytest


@pytest.fixture(autouse=True)
def _isolate_partial_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BREVIO_KEEP_PARTIALS", "false")
    monkeypatch.setenv("PROVIDER_QUOTA_ENABLED", "false")
    monkeypatch.setenv("BREVIO_ALLOW_MAP_ORIGINAL_TEXT_FALLBACK", "false")
    monkeypatch.delenv("PROVIDER_QUOTA_CONFIG_PATH", raising=False)
    monkeypatch.delenv("JOB_MAX_PROVIDER_REQUESTS", raising=False)
