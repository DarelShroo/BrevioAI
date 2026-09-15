from __future__ import annotations

from typing import Iterable, List, Optional

from core.brevio_api.models.errors.provider_errors import (
    ProviderError,
    ProviderErrorKind,
)
from core.shared.enums.model import ModelType
from core.shared.utils.environment import (
    current_environment,
    is_production_environment,
    local_user_access,
    parse_enabled_ids,
)
from core.shared.utils.model_capabilities import get_model_capabilities
from core.shared.utils.model_catalog import (
    ModelCatalogEntry,
    is_local_provider,
    list_model_catalog,
)


class SummaryAccessPolicy:
    """Separates technical capability from end-user availability for summary models.

    Local providers (Ollama) stay implemented. Production hides them from users
    unless SUMMARY_LOCAL_USER_ACCESS=true. Development keeps them selectable.
    """

    def __init__(self, environment: Optional[str] = None) -> None:
        self._environment_override = environment

    @property
    def environment(self) -> str:
        if self._environment_override is not None:
            return self._environment_override.strip().lower() or current_environment()
        return current_environment()

    def is_production(self) -> bool:
        return is_production_environment(self.environment)

    def enabled_providers(self) -> Optional[frozenset[str]]:
        return parse_enabled_ids("ENABLED_SUMMARY_PROVIDERS")

    def user_can_select_provider(self, provider: str) -> bool:
        name = provider.strip().lower()
        if not name:
            return False
        enabled = self.enabled_providers()
        if enabled is not None and name not in enabled:
            return False
        if is_local_provider(name):
            return local_user_access(
                "SUMMARY_LOCAL_USER_ACCESS", environment=self.environment
            )
        return True

    def user_can_select_model(self, model: ModelType) -> bool:
        provider = get_model_capabilities(model).provider.lower()
        return self.user_can_select_provider(provider)

    def user_can_select_entry(self, entry: ModelCatalogEntry) -> bool:
        return self.user_can_select_provider(entry.provider)

    def ensure_user_may_select(self, model: ModelType) -> None:
        if not self.user_can_select_model(model):
            raise ProviderError(
                kind=ProviderErrorKind.MODEL_NOT_ALLOWED,
                message="Este modelo no está disponible en el entorno actual.",
            )

    def selectable_catalog(
        self, entries: Optional[Iterable[ModelCatalogEntry]] = None
    ) -> List[ModelCatalogEntry]:
        catalog = list(entries) if entries is not None else list_model_catalog()
        return [entry for entry in catalog if self.user_can_select_entry(entry)]

    def selectable_model_ids(self) -> List[str]:
        return [entry.id for entry in self.selectable_catalog()]
