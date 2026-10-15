import abc
import logging
import os
import re
from typing import Dict, Optional

from openai import AsyncOpenAI

from core.brevio_api.models.errors.provider_errors import ProviderErrorKind

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "xai": "https://api.x.ai/v1",
    "anthropic": "https://api.anthropic.com",
    "ollama": "http://host.docker.internal:11434/v1",
    # RunAI serves an OpenAI-compatible API on port 11435.
    # host.docker.internal resolves to the host from inside Docker containers.
    "runai": "http://host.docker.internal:11435/v1",
}

_GOOGLE_NATIVE_MODELS_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
)


class InvalidProviderCredential(Exception):
    """Raised when a credential is rejected with a user-facing reason."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def get_provider_base_url(provider: str) -> str:
    name = provider.strip().lower()
    env_url = os.getenv(f"{name.upper()}_API_URL")
    if env_url and env_url.strip():
        return env_url.strip()
    return DEFAULT_PROVIDER_BASE_URLS.get(name, "")


def normalize_api_key(api_key: str) -> str:
    """Strip whitespace, wrapping quotes and zero-width chars from pasted keys."""
    cleaned = (api_key or "").strip().strip("\"'")
    cleaned = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", cleaned)
    return cleaned.strip()


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


class GoogleAdapter(ProviderAdapter):
    """Validate Gemini API keys via the native Generative Language API.

    Google often returns HTTP 400 (INVALID_ARGUMENT / API_KEY_INVALID) instead of
    401 for bad keys. The OpenAI-compatible ``models.list`` path alone is easy to
    mis-classify; the native ``/v1beta/models`` endpoint is authoritative.

    AI Studio project IDs look like ``gen-lang-client-...`` and are not API keys.
    Keys are typically ``AIza...`` (legacy) or ``AQ....`` (AI Studio auth keys).
    """

    async def validate_credential(self, api_key: str, base_url: str) -> bool:
        import httpx

        key = normalize_api_key(api_key)
        if not key:
            raise InvalidProviderCredential("La clave API es obligatoria.")

        if key.lower().startswith("gen-lang-client-"):
            raise InvalidProviderCredential(
                "Eso parece el Project ID de Google AI Studio "
                "(gen-lang-client-...), no la API key. En AI Studio abre "
                "Get API key y copia la clave completa (suele empezar por "
                "AIza... o AQ....)."
            )

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Prefer header auth (required for newer AQ. keys); fall back to
                # query-param auth used by classic AIza keys.
                response = await client.get(
                    _GOOGLE_NATIVE_MODELS_URL,
                    params={"pageSize": 1},
                    headers={"x-goog-api-key": key},
                )
                if response.status_code in {400, 401} and not key.startswith("AQ."):
                    response = await client.get(
                        _GOOGLE_NATIVE_MODELS_URL,
                        params={"key": key, "pageSize": 1},
                    )
        except Exception:
            logger.warning(
                "event=google_credential_validate_network_error",
                exc_info=True,
            )
            raise InvalidProviderCredential(
                "No se pudo contactar con Google para validar la clave. Inténtalo de nuevo."
            ) from None

        if response.status_code in {200, 429}:
            return True
        if response.status_code == 403:
            reason = self._google_error_reason(response)
            if reason in {
                "API_KEY_SERVICE_BLOCKED",
                "SERVICE_DISABLED",
                "ACCESS_TOKEN_SCOPE_INSUFFICIENT",
            }:
                raise InvalidProviderCredential(
                    "Google rechazó la clave: activa la Generative Language API "
                    "(Gemini) para este proyecto o revisa las restricciones de la API key."
                )
            raise InvalidProviderCredential(
                "Google rechazó la clave (403). Si la key tiene restricciones de "
                "IP o HTTP referrer, el servidor de Brevio no podrá usarla; "
                "usa una key sin esas restricciones o permite la IP del servidor."
            )
        if response.status_code in {400, 401}:
            reason = self._google_error_reason(response)
            logger.info(
                "event=google_credential_rejected status=%s reason=%s prefix=%s",
                response.status_code,
                reason or "unknown",
                key[:8],
            )
            if reason == "ACCESS_TOKEN_TYPE_UNSUPPORTED":
                raise InvalidProviderCredential(
                    "Google no aceptó este tipo de clave en la Generative Language API. "
                    "Genera una API key en Google AI Studio (Get API key) y pégala completa."
                )
            raise InvalidProviderCredential(
                "Google rechazó la clave para Gemini. Debe ser la API key de "
                "AI Studio / Gemini (AIza... o AQ....), no el Project ID "
                "(gen-lang-client-...) ni una key de Maps u otro producto. "
                "Si la key es correcta, revisa restricciones de IP/HTTP referrer."
            )

        logger.warning(
            "event=google_credential_unexpected_status status=%s",
            response.status_code,
        )
        raise InvalidProviderCredential(
            f"Google respondió {response.status_code} al validar la clave. Inténtalo más tarde."
        )

    @staticmethod
    def _google_error_reason(response) -> Optional[str]:
        try:
            payload = response.json()
            error = payload.get("error") or {}
            for detail in error.get("details") or []:
                reason = detail.get("reason")
                if reason:
                    return str(reason)
            status = error.get("status")
            return str(status) if status else None
        except Exception:
            return None

    def map_error(self, error: Exception) -> ProviderErrorKind:
        import httpx

        status = getattr(error, "status_code", None)
        if status is None and isinstance(error, httpx.HTTPStatusError):
            status = error.response.status_code
        if status in {400, 401, 403}:
            return ProviderErrorKind.UNAUTHORIZED
        if status == 429:
            return ProviderErrorKind.RATE_LIMIT_EXCEEDED
        return ProviderErrorKind.PROVIDER_ERROR


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
        return ProviderErrorKind.PROVIDER_ERROR


class XAIAdapter(OpenAIAdapter):
    pass


# RunAI exposes the same OpenAI-compatible API as Ollama.
# No real API key is required; a dummy token is used to satisfy the SDK.
class RunAIAdapter(OllamaAdapter):
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
            "runai": RunAIAdapter(),
        }

    def get_adapter(self, provider: str) -> ProviderAdapter:
        adapter = self._adapters.get(provider.lower())
        if not adapter:
            raise ValueError(f"Provider {provider} not supported")
        return adapter
