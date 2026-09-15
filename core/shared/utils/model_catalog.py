from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Optional

from core.shared.enums.model import ModelType
from core.shared.utils.model_capabilities import (
    MODEL_CAPABILITIES,
    generation_parameter_ids,
    get_model_capabilities,
    summary_max_output_tokens,
)


class ModelAccess(str, Enum):
    LOCAL = "local"
    PAY_PER_USE = "pay_per_use"


LOCAL_PROVIDERS = frozenset({"ollama"})
DEPRECATED_MODELS = frozenset()


@dataclass(frozen=True)
class ModelCatalogEntry:
    id: str
    model: ModelType
    provider: str
    access: ModelAccess
    requires_api_key: bool
    display_name: str
    context_window: int
    native_max_output_tokens: int
    summary_max_output_tokens: int
    output_token_param: str
    parameters: tuple[str, ...]
    reasoning: Optional[str]
    reasoning_values: tuple[str, ...]
    status: str
    retirement: Optional[str]
    recommended: bool


@dataclass(frozen=True)
class ProviderCatalogEntry:
    id: str
    access: ModelAccess
    requires_api_key: bool


def is_local_provider(provider: str) -> bool:
    return provider.strip().lower() in LOCAL_PROVIDERS


def provider_requires_api_key(provider: str) -> bool:
    return not is_local_provider(provider)


def model_requires_api_key(model: ModelType) -> bool:
    return provider_requires_api_key(get_model_capabilities(model).provider)


def access_for_provider(provider: str) -> ModelAccess:
    if is_local_provider(provider):
        return ModelAccess.LOCAL
    return ModelAccess.PAY_PER_USE


def catalog_entry_for_model(model: ModelType) -> ModelCatalogEntry:
    capabilities = get_model_capabilities(model)
    access = access_for_provider(capabilities.provider)
    return ModelCatalogEntry(
        id=model.value,
        model=model,
        provider=capabilities.provider,
        access=access,
        requires_api_key=access is ModelAccess.PAY_PER_USE,
        display_name=model.value,
        context_window=capabilities.context_window,
        native_max_output_tokens=capabilities.native_max_output_tokens,
        summary_max_output_tokens=summary_max_output_tokens(capabilities),
        output_token_param=capabilities.output_token_param,
        parameters=tuple(generation_parameter_ids(capabilities)),
        reasoning=capabilities.reasoning,
        reasoning_values=capabilities.reasoning_values,
        status=capabilities.status,
        retirement=capabilities.retirement,
        recommended=capabilities.recommended,
    )


def list_model_catalog() -> List[ModelCatalogEntry]:
    entries = [
        catalog_entry_for_model(model)
        for model in MODEL_CAPABILITIES
        if model not in DEPRECATED_MODELS
    ]
    entries.sort(
        key=lambda entry: (
            0 if entry.access is ModelAccess.LOCAL else 1,
            0 if entry.recommended else 1,
            0 if entry.status == "stable" else 1,
            entry.id,
        )
    )
    return entries


def list_public_model_ids() -> List[str]:
    return [entry.id for entry in list_model_catalog()]


def list_provider_catalog() -> List[ProviderCatalogEntry]:
    seen: Dict[str, ProviderCatalogEntry] = {}
    for entry in list_model_catalog():
        if entry.provider not in seen:
            seen[entry.provider] = ProviderCatalogEntry(
                id=entry.provider,
                access=entry.access,
                requires_api_key=entry.requires_api_key,
            )
    providers = list(seen.values())
    providers.sort(
        key=lambda item: (0 if item.access is ModelAccess.LOCAL else 1, item.id)
    )
    return providers


def is_known_provider(provider: str) -> bool:
    name = provider.strip().lower()
    if not name:
        return False
    if name in LOCAL_PROVIDERS:
        return True
    return any(item.id.lower() == name for item in list_provider_catalog())


def _provider_payload(entry: ProviderCatalogEntry) -> dict:
    return {
        "id": entry.id,
        "access": entry.access.value,
        "requires_api_key": entry.requires_api_key,
    }


def _model_payload(entry: ModelCatalogEntry) -> dict:
    return {
        "id": entry.id,
        "provider": entry.provider,
        "access": entry.access.value,
        "requires_api_key": entry.requires_api_key,
        "display_name": entry.display_name,
        "output_token_param": entry.output_token_param,
        "parameters": list(entry.parameters),
        "reasoning": entry.reasoning,
        "reasoning_values": list(entry.reasoning_values),
        "status": entry.status,
        "retirement": entry.retirement,
        "recommended": entry.recommended,
    }


def build_models_payload(model_ids: Optional[Iterable[str]] = None) -> dict:
    catalog = list_model_catalog()
    by_id = {entry.id: entry for entry in catalog}
    ids = list(model_ids) if model_ids is not None else [entry.id for entry in catalog]
    items: List[dict] = []
    providers: Dict[str, ProviderCatalogEntry] = {}

    for model_id in ids:
        entry = by_id.get(model_id)
        if entry is None:
            payload = {
                "id": model_id,
                "provider": "unknown",
                "access": ModelAccess.PAY_PER_USE.value,
                "requires_api_key": True,
                "display_name": model_id,
            }
            provider = ProviderCatalogEntry(
                id="unknown",
                access=ModelAccess.PAY_PER_USE,
                requires_api_key=True,
            )
        else:
            payload = _model_payload(entry)
            provider = ProviderCatalogEntry(
                id=entry.provider,
                access=entry.access,
                requires_api_key=entry.requires_api_key,
            )
        items.append(payload)
        if provider.id not in providers:
            providers[provider.id] = provider

    ordered_providers = sorted(
        providers.values(),
        key=lambda item: (0 if item.access is ModelAccess.LOCAL else 1, item.id),
    )
    return {
        "models": ids,
        "catalog": items,
        "providers": [_provider_payload(item) for item in ordered_providers],
    }
