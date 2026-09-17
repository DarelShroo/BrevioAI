import httpx
import pytest
from openai import APIError, AuthenticationError, RateLimitError

from core.brevio.services.provider_registry import (
    GoogleAdapter,
    InvalidProviderCredential,
    OpenAIAdapter,
    ProviderRegistry,
    normalize_api_key,
)
from core.brevio_api.models.errors.provider_errors import ProviderErrorKind


def test_registry_get_adapter():
    registry = ProviderRegistry()
    adapter = registry.get_adapter("openai")
    assert isinstance(adapter, OpenAIAdapter)

    with pytest.raises(ValueError):
        registry.get_adapter("unsupported")


def test_openai_adapter_map_error():
    adapter = OpenAIAdapter()
    req = httpx.Request("GET", "https://api.openai.com")
    resp = httpx.Response(401, request=req)

    auth_err = AuthenticationError("unauthorized", response=resp, body=None)
    assert adapter.map_error(auth_err) == ProviderErrorKind.UNAUTHORIZED

    rate_err = RateLimitError("insufficient_quota", response=resp, body=None)
    assert adapter.map_error(rate_err) == ProviderErrorKind.INSUFFICIENT_FUNDS

    rate_err2 = RateLimitError("rate limit exceeded", response=resp, body=None)
    assert adapter.map_error(rate_err2) == ProviderErrorKind.RATE_LIMIT_EXCEEDED

    api_err = APIError("server error", request=req, body=None)
    assert adapter.map_error(api_err) == ProviderErrorKind.PROVIDER_ERROR


@pytest.mark.asyncio
async def test_openai_adapter_validate_credential_success(mocker):
    mock_client = mocker.patch("core.brevio.services.provider_registry.AsyncOpenAI")
    mock_instance = mock_client.return_value
    mock_instance.models.list = mocker.AsyncMock()
    mock_instance.close = mocker.AsyncMock()

    adapter = OpenAIAdapter()
    result = await adapter.validate_credential("sk-123", "https://api.openai.com")
    assert result is True


@pytest.mark.asyncio
async def test_openai_adapter_validate_credential_failure(mocker):
    from openai import AuthenticationError

    mock_client = mocker.patch("core.brevio.services.provider_registry.AsyncOpenAI")
    mock_instance = mock_client.return_value

    req = httpx.Request("GET", "https://api.openai.com")
    resp = httpx.Response(401, request=req)
    mock_instance.models.list.side_effect = AuthenticationError(
        "unauthorized", response=resp, body=None
    )
    mock_instance.close = mocker.AsyncMock()

    adapter = OpenAIAdapter()
    result = await adapter.validate_credential("sk-invalid", "https://api.openai.com")
    assert result is False
    mock_instance.close.assert_awaited()


@pytest.mark.asyncio
async def test_openai_adapter_validate_credential_rate_limit_is_valid(mocker):
    mock_client = mocker.patch("core.brevio.services.provider_registry.AsyncOpenAI")
    mock_instance = mock_client.return_value
    req = httpx.Request("GET", "https://api.openai.com")
    resp = httpx.Response(429, request=req)
    mock_instance.models.list.side_effect = RateLimitError(
        "rate limit exceeded", response=resp, body=None
    )
    mock_instance.close = mocker.AsyncMock()

    adapter = OpenAIAdapter()
    result = await adapter.validate_credential("sk-123", "https://api.openai.com")
    assert result is True


def test_provider_base_url_uses_env_and_defaults(monkeypatch):
    from core.brevio.services.provider_registry import get_provider_base_url

    monkeypatch.delenv("OPENAI_API_URL", raising=False)
    assert get_provider_base_url("openai").startswith("https://api.openai.com")
    monkeypatch.setenv("OPENAI_API_URL", "https://example.test/v1")
    assert get_provider_base_url("openai") == "https://example.test/v1"
    monkeypatch.delenv("XAI_API_URL", raising=False)
    assert get_provider_base_url("xai").startswith("https://api.x.ai")
    monkeypatch.delenv("ANTHROPIC_API_URL", raising=False)
    assert get_provider_base_url("anthropic").startswith("https://api.anthropic.com")


def test_registry_supports_xai_and_anthropic():
    registry = ProviderRegistry()
    assert registry.get_adapter("xai") is not None
    assert registry.get_adapter("anthropic") is not None


@pytest.mark.asyncio
async def test_anthropic_validate_credential_is_mocked(mocker):
    from core.brevio.services.provider_registry import AnthropicAdapter

    class FakeResponse:
        status_code = 200
        is_success = True

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, headers=None):
            assert "x-api-key" in headers
            return FakeResponse()

    mocker.patch("httpx.AsyncClient", return_value=FakeClient())
    adapter = AnthropicAdapter()
    assert (
        await adapter.validate_credential("sk-ant", "https://api.anthropic.com") is True
    )


def test_normalize_api_key_strips_quotes_and_zero_width():
    assert normalize_api_key('  "AIzaSyTest"  ') == "AIzaSyTest"
    assert normalize_api_key("AIza\u200bSyTest") == "AIzaSyTest"


def test_registry_supports_google():
    registry = ProviderRegistry()
    assert isinstance(registry.get_adapter("google"), GoogleAdapter)


@pytest.mark.asyncio
async def test_google_adapter_validate_uses_native_models_endpoint(mocker):
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"models": [{"name": "models/gemini-2.0-flash"}]}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None, headers=None):
            captured["url"] = url
            captured["params"] = params
            captured["headers"] = headers
            return FakeResponse()

    mocker.patch("httpx.AsyncClient", return_value=FakeClient())
    adapter = GoogleAdapter()
    assert (
        await adapter.validate_credential(
            "  AIzaSyValidKey  ",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        is True
    )
    assert captured["url"].endswith("/v1beta/models")
    assert captured["headers"]["x-goog-api-key"] == "AIzaSyValidKey"
    assert captured["params"]["pageSize"] == 1


@pytest.mark.asyncio
async def test_google_adapter_rejects_project_id_as_key():
    adapter = GoogleAdapter()
    with pytest.raises(InvalidProviderCredential) as exc:
        await adapter.validate_credential(
            "gen-lang-client-0029271443",
            "https://unused",
        )
    assert "Project ID" in exc.value.message


@pytest.mark.asyncio
async def test_google_adapter_rejects_api_key_invalid_with_message(mocker):
    class FakeResponse:
        status_code = 400

        def json(self):
            return {
                "error": {
                    "status": "INVALID_ARGUMENT",
                    "details": [{"reason": "API_KEY_INVALID"}],
                }
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None, headers=None):
            return FakeResponse()

    mocker.patch("httpx.AsyncClient", return_value=FakeClient())
    adapter = GoogleAdapter()
    with pytest.raises(InvalidProviderCredential) as exc:
        await adapter.validate_credential("bad-key", "https://unused")
    assert "Gemini" in exc.value.message


@pytest.mark.asyncio
async def test_google_adapter_accepts_rate_limit_as_valid(mocker):
    class FakeResponse:
        status_code = 429

        def json(self):
            return {"error": {"status": "RESOURCE_EXHAUSTED"}}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None, headers=None):
            return FakeResponse()

    mocker.patch("httpx.AsyncClient", return_value=FakeClient())
    adapter = GoogleAdapter()
    assert await adapter.validate_credential("AIzaSyLimited", "https://unused") is True


@pytest.mark.asyncio
async def test_google_adapter_service_disabled_message(mocker):
    class FakeResponse:
        status_code = 403

        def json(self):
            return {
                "error": {
                    "status": "PERMISSION_DENIED",
                    "details": [{"reason": "SERVICE_DISABLED"}],
                }
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None, headers=None):
            return FakeResponse()

    mocker.patch("httpx.AsyncClient", return_value=FakeClient())
    adapter = GoogleAdapter()
    with pytest.raises(InvalidProviderCredential) as exc:
        await adapter.validate_credential("AIzaSyBlocked", "https://unused")
    assert "Generative Language API" in exc.value.message


@pytest.mark.asyncio
async def test_google_adapter_falls_back_to_query_key_for_aiza(mocker):
    calls = []

    class FakeResponse:
        def __init__(self, status_code):
            self.status_code = status_code

        def json(self):
            return {
                "error": {
                    "status": "INVALID_ARGUMENT",
                    "details": [{"reason": "API_KEY_INVALID"}],
                }
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None, headers=None):
            calls.append({"params": params, "headers": headers})
            if headers and headers.get("x-goog-api-key"):
                return FakeResponse(400)
            return FakeResponse(200)

    mocker.patch("httpx.AsyncClient", return_value=FakeClient())
    adapter = GoogleAdapter()
    assert await adapter.validate_credential("AIzaSyFallback", "https://unused") is True
    assert len(calls) == 2
    assert calls[1]["params"]["key"] == "AIzaSyFallback"
