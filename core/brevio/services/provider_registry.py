import abc
import os
from typing import Dict

from openai import AsyncOpenAI

from core.brevio_api.models.errors.provider_errors import (
    ProviderError,
    ProviderErrorKind,
)

DEFAULT_PROVIDER_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "xai": "https://api.x.ai/v1",
    "anthropic": "https://api.anthropic.com",
    "ollama": "http://host.docker.internal:11434/v1",
}


def get_provider_base_url(provider: str) -> str:
    name = provider.strip().lower()
    env_url = os.getenv(f"{name.upper()}_API_URL")
    if env_url and env_url.strip():
        return env_url.strip()
    return DEFAULT_PROVIDER_BASE_URLS.get(name, "")


class ProviderAdapter(abc.ABC):
    @abc.abstractmethod
    async def validate_credential(self, api_key: str, base_url: str) -> bool:
        """Validates if the provided credential is valid for this provider."""
        pass

    @abc.abstractmethod
    def map_error(self, error: Exception) -> ProviderErrorKind:
        """Maps an underlying provider exception to our taxonomy."""
        pass


class OpenAIAdapter(ProviderAdapter):
    async def validate_credential(self, api_key: str, base_url: str) -> bool:
        client = AsyncOpenAI(
            api_key=api_key, base_url=base_url, max_retries=0, timeout=15.0
        )
        try:
            await client.models.list()
            return True
        except Exception as e:
            kind = self.map_error(e)
            # The key was accepted; quota or rate limits are not a reason to reject save.
            if kind in (
                ProviderErrorKind.RATE_LIMIT_EXCEEDED,
                ProviderErrorKind.INSUFFICIENT_FUNDS,
            ):
                return True
            return False
        finally:
            await client.close()

    def map_error(self, error: Exception) -> ProviderErrorKind:
        from openai import APIError, AuthenticationError, RateLimitError

        if isinstance(error, AuthenticationError):
            return ProviderErrorKind.UNAUTHORIZED
        elif isinstance(error, RateLimitError):
            err_msg = str(error).lower()
            if "insufficient_quota" in err_msg or "balance" in err_msg:
                return ProviderErrorKind.INSUFFICIENT_FUNDS
            return ProviderErrorKind.RATE_LIMIT_EXCEEDED
        elif isinstance(error, APIError):
            return ProviderErrorKind.PROVIDER_ERROR
        return ProviderErrorKind.UNKNOWN


class DeepSeekAdapter(OpenAIAdapter):
    # DeepSeek uses OpenAI SDK, so the behavior is identical
    pass


class GoogleAdapter(OpenAIAdapter):
    # Gemini exposes an OpenAI-compatible API.
    pass


class OllamaAdapter(ProviderAdapter):
    async def validate_credential(self, api_key: str, base_url: str) -> bool:
        client = AsyncOpenAI(
            api_key=api_key or "ollama",
            base_url=base_url,
            max_retries=0,
            timeout=15.0,
        )
        try:
            await client.models.list()
            return True
        except Exception:
            return False
        finally:
            await client.close()

    def map_error(self, error: Exception) -> ProviderErrorKind:
        import asyncio

        import httpx

        if isinstance(error, httpx.ReadTimeout) or isinstance(
            error, asyncio.TimeoutError
        ):
            return ProviderErrorKind.PROVIDER_ERROR
        # Treat other connection issues as unknown or provider error
        return ProviderErrorKind.PROVIDER_ERROR


class XAIAdapter(OpenAIAdapter):
    pass


class AnthropicAdapter(ProviderAdapter):
    async def validate_credential(self, api_key: str, base_url: str) -> bool:
        import httpx

        root = (base_url or "https://api.anthropic.com").rstrip("/")
        if root.endswith("/v1"):
            root = root[:-3]
        url = f"{root}/v1/models"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    url,
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                )
            if response.status_code == 401:
                return False
            if response.status_code in {429, 402}:
                return True
            return response.is_success
        except Exception:
            return False

    def map_error(self, error: Exception) -> ProviderErrorKind:
        import httpx

        status = getattr(error, "status_code", None)
        if status is None and isinstance(error, httpx.HTTPStatusError):
            status = error.response.status_code
        if status in {401, 403}:
            return ProviderErrorKind.UNAUTHORIZED
        if status == 429:
            return ProviderErrorKind.RATE_LIMIT_EXCEEDED
        if status == 402:
            return ProviderErrorKind.INSUFFICIENT_FUNDS
        return ProviderErrorKind.PROVIDER_ERROR


class ProviderRegistry:
    def __init__(self):
        self._adapters: Dict[str, ProviderAdapter] = {
            "openai": OpenAIAdapter(),
            "deepseek": DeepSeekAdapter(),
            "google": GoogleAdapter(),
            "xai": XAIAdapter(),
            "anthropic": AnthropicAdapter(),
            "ollama": OllamaAdapter(),
        }

    def get_adapter(self, provider: str) -> ProviderAdapter:
        adapter = self._adapters.get(provider.lower())
        if not adapter:
            raise ValueError(f"Provider {provider} not supported")
        return adapter
