from typing import Optional

from core.shared.utils.environment import (
    current_environment,
    dev_allow_platform_override,
)


class PlatformAccessPolicy:
    """
    Determines if fallback to the platform's `.env` credential is allowed.
    """

    def __init__(self, override_allow_platform: Optional[bool] = None):
        self._override = override_allow_platform

    @property
    def environment(self) -> str:
        return current_environment()

    @property
    def dev_allow_override(self) -> bool:
        return dev_allow_platform_override()

    def is_authorized(
        self, environment: Optional[str] = None, provider: Optional[str] = None
    ) -> bool:
        return self.can_use_platform_credential(environment, provider)

    def can_use_platform_credential(
        self, environment: Optional[str] = None, provider: Optional[str] = None
    ) -> bool:
        if self._override is not None:
            return self._override

        current_env = (environment or self.environment).lower()
        allow_override = self.dev_allow_override

        # This override only covers a missing platform key in development.
        # Pay-per-use still uses the env API key when it exists; credits are
        # enforced separately in CredentialResolver.ensure_model_access().
        if current_env == "production":
            return False

        # In development, check if the developer allows fallback
        return current_env == "development" and allow_override
