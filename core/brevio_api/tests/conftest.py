import pytest

@pytest.fixture(autouse=True)
def _isolate_rate_limits(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    path = str(getattr(request, "fspath", ""))
    if "anti_abuse" in path or "security" in path or "attack" in path:
        return
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("ANTI_ABUSE_ENABLED", "false")

