"""Credential resolution for BYOK / platform / local providers.

Public API (stable):
    from core.brevio.services.credential_resolver import CredentialResolver, ResolvedCredential

``ResolvedCredential`` lives in ``resolved_credential.py`` so DTO-only consumers
never pull this module's heavier dependencies (and cannot accidentally create a
self-import cycle by re-importing this module from within itself).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from core.brevio.services.platform_access_policy import PlatformAccessPolicy
from core.brevio.services.provider_registry import (
    ProviderRegistry,
    get_provider_base_url,
)
from core.brevio.services.resolved_credential import ResolvedCredential
from core.brevio.services.summary_providers.access_policy import SummaryAccessPolicy
from core.brevio_api.models.errors.provider_errors import (
    ProviderError,
    ProviderErrorKind,
)
from core.brevio_api.repositories.user_credential_repository import (
    UserCredentialRepository,
)
from core.shared.enums.model import ModelType
from core.shared.utils.environment import current_environment
from core.shared.utils.model_capabilities import get_model_capabilities
from core.shared.utils.model_catalog import is_local_provider, model_requires_api_key

logger = logging.getLogger(__name__)

__all__ = ["CredentialResolver", "ResolvedCredential"]


class CredentialResolver:
    def __init__(
        self,
        repository: UserCredentialRepository,
        platform_policy: PlatformAccessPolicy,
        provider_registry: ProviderRegistry,
    ):
        self.repository = repository
        self.platform_policy = platform_policy
        self.provider_registry = provider_registry

    async def resolve(self, user_id: str, provider: str) -> ResolvedCredential:
        """
        Resolves the appropriate credential for a user and provider.
        Priority:
        1. User's default credential (BYOK)
        2. User's most recently updated active credential (fallback)
        3. Local Ollama dummy credential
        4. Platform pay-per-use credential when a platform API key exists

        Credits for pay-per-use are enforced in ensure_model_access().

        Raises ProviderError if no credential can be resolved.

        Local providers (Ollama) never require a user API key. A dummy
        OpenAI-compatible token is used so the SDK can talk to the local
        server. User-facing access to local models is gated separately by
        SummaryAccessPolicy (hidden in production unless
        SUMMARY_LOCAL_USER_ACCESS=true).
        """
        provider_clean = provider.lower()
        # Ensure provider is supported by checking registry
        self.provider_registry.get_adapter(provider_clean)

        user_doc = await self._get_user_doc(user_id, provider_clean)

        if user_doc:
            user_key = self.repository.decrypt_credential(user_doc)
            base_url = self._get_platform_base_url(provider_clean)
            return ResolvedCredential(
                api_key=user_key,
                base_url=base_url,
                is_platform=False,
                credential_id=user_doc.id,
                updated_at=user_doc.updated_at,
            )

        if is_local_provider(provider_clean):
            return self._local_platform_credential(provider_clean)

        platform_key = self._get_platform_key(provider_clean)
        if platform_key:
            base_url = self._get_platform_base_url(provider_clean)
            return ResolvedCredential(
                api_key=platform_key,
                base_url=base_url,
                is_platform=True,
                credential_id="platform",
                updated_at=datetime.min.replace(tzinfo=timezone.utc),
            )

        current_env = current_environment()
        if self.platform_policy.can_use_platform_credential(
            current_env, provider_clean
        ):
            logger.error(
                f"event=credential_resolution_failed provider={provider_clean} user_id={user_id} "
                f"environment={current_env} reason=platform_credential_missing credential_source=platform"
            )
            raise ProviderError(
                kind=ProviderErrorKind.PLATFORM_CREDENTIAL_UNAVAILABLE,
                message="Los servicios de Brevio no se pueden usar por su plan. Si quiere usarlo deberá configurar una API Key en su perfil.",
            )

        logger.error(
            f"event=credential_resolution_failed provider={provider_clean} user_id={user_id} "
            f"environment={current_env} reason=user_credential_required credential_source=user"
        )
        raise ProviderError(
            kind=ProviderErrorKind.USER_CREDENTIAL_REQUIRED,
            message="Los servicios de Brevio no se pueden usar por su plan. Si quiere usarlo deberá configurar una API Key en su perfil.",
        )

    async def can_resolve(self, user_id: str, provider: str) -> bool:
        """
        Fast check to see if a credential could be resolved.
        Used by API endpoints (FastAPI) to fail-fast before queuing Celery tasks.
        NOTE: This is a preflight check. It checks for existence of credentials but
        does not attempt real decryption. `resolve()` is the ultimate source of truth.
        """
        try:
            provider_clean = provider.lower()
            # Must be a valid provider
            self.provider_registry.get_adapter(provider_clean)

            if is_local_provider(provider_clean):
                return True

            credentials = await self.repository.get_active_credentials_for_user(
                user_id, provider_clean
            )
            if credentials:
                return True

            if self.has_platform_credential(provider_clean):
                return True

            return False
        except Exception:
            return False

    def has_platform_credential(self, provider: str) -> bool:
        """
        Check if the platform has a credential configured for this provider,
        and if the current environment permits using it.
        """
        provider_clean = provider.lower()
        if is_local_provider(provider_clean):
            return True
            
        current_env = current_environment()
        if not self.platform_policy.can_use_platform_credential(current_env, provider_clean):
            return False
            
        return bool(self._get_platform_key(provider_clean))

    async def ensure_model_access(
        self,
        user_id: str,
        model: ModelType,
        user_credits: float = 0,
    ) -> None:
        """Fail fast before queuing a job.

        Local models: allowed only when SummaryAccessPolicy permits them.
        BYOK: user profile key is enough (credits reserved as 0 at admission).
        Pay-per-use: platform key required; commercial credit gate is FASE 3
        reservation at job admission (CreditAccount), not legacy user_credit.
        """
        SummaryAccessPolicy().ensure_user_may_select(model)
        provider = get_model_capabilities(model).provider.lower()
        if not model_requires_api_key(model):
            if provider in ("ollama", "runai"):
                try:
                    import httpx
                    url = self._get_platform_base_url(provider)
                    base_url = url.replace("/v1", "")
                    async with httpx.AsyncClient() as client:
                        await client.get(base_url, timeout=2.0)
                except Exception as e:
                    logger.error(f"Local provider {provider} is unreachable during preflight: {e}")
                    raise ProviderError(
                        kind=ProviderErrorKind.PROVIDER_ERROR,
                        message="El modelo local seleccionado no está encendido o es inaccesible en este momento."
                    )
            return
        
        credentials = await self.repository.get_active_credentials_for_user(
            user_id, provider
        )
        if credentials:
            return

        current_env = current_environment()
        if not self.platform_policy.can_use_platform_credential(current_env, provider):
            logger.error(
                "event=credential_resolution_failed provider=%s user_id=%s "
                "reason=user_credential_required credential_source=user model=%s",
                provider,
                user_id,
                model.value,
            )
            raise ProviderError(
                kind=ProviderErrorKind.USER_CREDENTIAL_REQUIRED,
                message="Los servicios de Brevio no se pueden usar por su plan. Si quiere usarlo deberá configurar una API Key en su perfil.",
            )

        platform_key = self._get_platform_key(provider)
        if not platform_key:
            logger.error(
                "event=credential_resolution_failed provider=%s user_id=%s "
                "reason=platform_credential_missing credential_source=platform model=%s",
                provider,
                user_id,
                model.value,
            )
            raise ProviderError(
                kind=ProviderErrorKind.PLATFORM_CREDENTIAL_UNAVAILABLE,
                message="Los servicios de Brevio no se pueden usar por su plan. Si quiere usarlo deberá configurar una API Key en su perfil.",
            )

        # Platform key present: model access OK. Credit reservation (FASE 3)
        # is enforced at job admission, not via legacy user_credits > 0.
        _ = user_credits
        return

    async def ensure_user_credential(self, user_id: str, provider: str) -> None:
        """Fail fast when a user BYOK credential is required (no platform fallback)."""
        provider_clean = provider.lower()
        self.provider_registry.get_adapter(provider_clean)
        credentials = await self.repository.get_active_credentials_for_user(
            user_id, provider_clean
        )
        if credentials:
            return
        logger.error(
            "event=credential_resolution_failed provider=%s user_id=%s "
            "reason=user_credential_required credential_source=user",
            provider_clean,
            user_id,
        )
        raise ProviderError(
            kind=ProviderErrorKind.USER_CREDENTIAL_REQUIRED,
            message="Los servicios de Brevio no se pueden usar por su plan. Si quiere usarlo deberá configurar una API Key en su perfil.",
        )

    async def resolve_user_credential(
        self, user_id: str, provider: str
    ) -> ResolvedCredential:
        """Resolve only the user's BYOK credential. Never returns a platform key."""
        provider_clean = provider.lower()
        self.provider_registry.get_adapter(provider_clean)
        user_doc = await self._get_user_doc(user_id, provider_clean)
        if not user_doc:
            logger.error(
                "event=credential_resolution_failed provider=%s user_id=%s "
                "reason=user_credential_required credential_source=user",
                provider_clean,
                user_id,
            )
            raise ProviderError(
                kind=ProviderErrorKind.USER_CREDENTIAL_REQUIRED,
                message="Los servicios de Brevio no se pueden usar por su plan. Si quiere usarlo deberá configurar una API Key en su perfil.",
            )
        user_key = self.repository.decrypt_credential(user_doc)
        return ResolvedCredential(
            api_key=user_key,
            base_url=self._get_platform_base_url(provider_clean),
            is_platform=False,
            credential_id=user_doc.id,
            updated_at=user_doc.updated_at,
        )

    def _local_platform_credential(self, provider: str) -> ResolvedCredential:
        return ResolvedCredential(
            api_key=self._get_platform_key(provider) or "ollama",
            base_url=self._get_platform_base_url(provider),
            is_platform=True,
            credential_id="local",
            updated_at=datetime.min.replace(tzinfo=timezone.utc),
        )

    async def _get_user_doc(self, user_id: str, provider: str):
        credentials = await self.repository.get_active_credentials_for_user(
            user_id, provider
        )
        if not credentials:
            return None

        default_cred = next((c for c in credentials if c.is_default), None)
        if default_cred:
            return default_cred

        # Fallback to most recently updated
        latest_cred = max(credentials, key=lambda c: c.updated_at)
        return latest_cred

    def _get_platform_key(self, provider: str) -> Optional[str]:
        if provider.upper() == "OLLAMA":
            return "ollama-local-key"
        name = provider.strip().lower()
        env_names = [f"{name.upper()}_API_KEY"]
        if name == "google":
            env_names.append("GEMINI_API_KEY")
        for env_name in env_names:
            raw = os.getenv(env_name)
            if raw and raw.strip():
                return raw.strip()
        return None

    def _get_platform_base_url(self, provider: str) -> str:
        return get_provider_base_url(provider)
