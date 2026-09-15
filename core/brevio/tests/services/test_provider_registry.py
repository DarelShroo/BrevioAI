import httpx
import pytest
from openai import APIError, AuthenticationError, RateLimitError

from core.brevio.services.provider_registry import OpenAIAdapter, ProviderRegistry
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
