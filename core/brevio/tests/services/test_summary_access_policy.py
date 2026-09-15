from __future__ import annotations

import os
from unittest.mock import patch

from core.brevio.services.summary_providers.access_policy import SummaryAccessPolicy
from core.brevio_api.models.errors.provider_errors import (
    ProviderError,
    ProviderErrorKind,
)
from core.shared.enums.model import ModelType
from core.shared.utils.model_catalog import ModelAccess, list_model_catalog


def test_development_keeps_local_summary_models(monkeypatch) -> None:
    monkeypatch.delenv("ENABLED_SUMMARY_PROVIDERS", raising=False)
    monkeypatch.delenv("SUMMARY_LOCAL_USER_ACCESS", raising=False)
    policy = SummaryAccessPolicy(environment="development")
    assert policy.user_can_select_model(ModelType.QWEN3_8B) is True
    assert policy.user_can_select_model(ModelType.GPT_4O_MINI) is True
    ids = policy.selectable_model_ids()
    assert ModelType.QWEN3_8B.value in ids
    assert ModelType.GPT_4O_MINI.value in ids


def test_production_hides_local_summary_models(monkeypatch) -> None:
    monkeypatch.delenv("SUMMARY_LOCAL_USER_ACCESS", raising=False)
    monkeypatch.delenv("ENABLED_SUMMARY_PROVIDERS", raising=False)
    policy = SummaryAccessPolicy(environment="production")
    assert policy.user_can_select_model(ModelType.QWEN3_8B) is False
    assert policy.user_can_select_model(ModelType.GPT_4O_MINI) is True
    ids = policy.selectable_model_ids()
    assert ModelType.QWEN3_8B.value not in ids
    assert ModelType.GPT_4O_MINI.value in ids
    assert ModelType.GPT_5_6.value in ids
    assert ModelType.GROK_4_6.value in ids
    assert ModelType.CLAUDE_SONNET_5.value in ids
    assert any(entry.access is ModelAccess.LOCAL for entry in list_model_catalog())


@patch.dict(
    os.environ, {"SUMMARY_LOCAL_USER_ACCESS": "true", "ENVIRONMENT": "production"}
)
def test_explicit_env_override_enables_local_summary_models_in_production() -> None:
    policy = SummaryAccessPolicy()
    assert policy.user_can_select_model(ModelType.QWEN3_8B) is True


@patch.dict(os.environ, {"ENABLED_SUMMARY_PROVIDERS": "openai"})
def test_allowlist_hides_other_summary_providers() -> None:
    policy = SummaryAccessPolicy(environment="development")
    assert policy.user_can_select_provider("openai") is True
    assert policy.user_can_select_provider("deepseek") is False
    assert policy.user_can_select_model(ModelType.DEEPSEEK_FLASH) is False


def test_production_rejects_local_model_selection(monkeypatch) -> None:
    monkeypatch.delenv("SUMMARY_LOCAL_USER_ACCESS", raising=False)
    monkeypatch.delenv("ENABLED_SUMMARY_PROVIDERS", raising=False)
    policy = SummaryAccessPolicy(environment="production")
    try:
        policy.ensure_user_may_select(ModelType.QWEN3_8B)
        raise AssertionError("expected ProviderError")
    except ProviderError as exc:
        assert exc.kind == ProviderErrorKind.MODEL_NOT_ALLOWED
