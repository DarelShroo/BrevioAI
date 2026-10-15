import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.services.credential_resolver import (
    CredentialResolver,
    ResolvedCredential,
)
from core.brevio_api.models.errors.provider_errors import (
    ProviderError,
    ProviderErrorKind,
)
from core.shared.enums.model import ModelType


@pytest.fixture
def mock_repository():
    repo = MagicMock()
    repo.get_active_credentials_for_user = AsyncMock(return_value=[])
    repo.decrypt_credential = MagicMock(return_value="user_decrypted_key")
    return repo


@pytest.fixture
def mock_policy():
    policy = MagicMock()
    policy.can_use_platform_credential.return_value = False
    return policy


@pytest.fixture
def mock_registry():
    registry = MagicMock()
    registry.get_adapter.return_value = MagicMock()
    return registry


@pytest.fixture
def resolver(mock_repository, mock_policy, mock_registry):
    return CredentialResolver(mock_repository, mock_policy, mock_registry)


@pytest.mark.asyncio
async def test_resolve_with_user_default_key(resolver, mock_repository):
    doc1 = MagicMock(is_default=False, updated_at=1)
    doc2 = MagicMock(is_default=True, updated_at=2)
    mock_repository.get_active_credentials_for_user.return_value = [doc1, doc2]
    mock_repository.decrypt_credential.return_value = "user_default"

    res = await resolver.resolve("u1", "openai")

    assert res.api_key == "user_default"
    assert res.is_platform is False
    mock_repository.decrypt_credential.assert_called_once_with(doc2)


@pytest.mark.asyncio
async def test_resolve_with_user_latest_fallback(resolver, mock_repository):
    doc1 = MagicMock(is_default=False, updated_at=10)
    doc2 = MagicMock(is_default=False, updated_at=20)
    mock_repository.get_active_credentials_for_user.return_value = [doc1, doc2]
    mock_repository.decrypt_credential.return_value = "user_latest"

    res = await resolver.resolve("u1", "openai")

    assert res.api_key == "user_latest"
    assert res.is_platform is False
    mock_repository.decrypt_credential.assert_called_once_with(doc2)


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "plat_key", "OPENAI_API_URL": "plat_url"})
async def test_resolve_with_platform_fallback(resolver, mock_policy, mock_repository):
    mock_repository.get_active_credentials_for_user.return_value = []
    mock_policy.can_use_platform_credential.return_value = True

    res = await resolver.resolve("u1", "openai")

    assert res.api_key == "plat_key"
    assert res.base_url == "plat_url"
    assert res.is_platform is True


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "", "ENVIRONMENT": "production"})
async def test_resolve_fails_no_credentials(resolver, mock_policy, mock_repository):
    mock_repository.get_active_credentials_for_user.return_value = []
    mock_policy.can_use_platform_credential.return_value = False

    with pytest.raises(ProviderError) as exc:
        await resolver.resolve("u1", "openai")

    assert exc.value.kind == ProviderErrorKind.USER_CREDENTIAL_REQUIRED


@pytest.mark.asyncio
@patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True)
async def test_resolve_local_ollama_without_api_key_in_production(
    resolver, mock_policy, mock_repository
):
    mock_repository.get_active_credentials_for_user.return_value = []
    mock_policy.can_use_platform_credential.return_value = False

    res = await resolver.resolve("u1", "ollama")

    assert res.is_platform is True
    assert res.api_key == "ollama-local-key"
    assert res.credential_id == "local"
    assert await resolver.can_resolve("u1", "ollama") is True


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_ensure_model_access_skips_key_for_local_models(
    mock_get, resolver, mock_policy, mock_repository
):
    # Local models do not require a key. They are skipped before checking keys.
    mock_repository.get_active_credentials_for_user.return_value = []
    mock_policy.can_use_platform_credential.return_value = False

    await resolver.ensure_model_access("u1", ModelType.QWEN3_8B, user_credits=0)
    mock_repository.get_active_credentials_for_user.assert_not_called()


@pytest.mark.asyncio
@patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False)
async def test_ensure_model_access_rejects_local_models_in_production(
    resolver, monkeypatch
):
    monkeypatch.delenv("SUMMARY_LOCAL_USER_ACCESS", raising=False)
    with pytest.raises(ProviderError) as exc:
        await resolver.ensure_model_access("u1", ModelType.QWEN3_8B, user_credits=0)
    assert exc.value.kind == ProviderErrorKind.MODEL_NOT_ALLOWED


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": ""})
async def test_ensure_model_access_paid_without_platform_key_requires_user_key(
    resolver, mock_policy, mock_repository
):
    mock_repository.get_active_credentials_for_user.return_value = []
    mock_policy.can_use_platform_credential.return_value = False

    with pytest.raises(ProviderError) as exc:
        await resolver.ensure_model_access("u1", ModelType.GPT_4O_MINI, user_credits=0)
    assert exc.value.kind == ProviderErrorKind.USER_CREDENTIAL_REQUIRED


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "plat_key"})
async def test_can_resolve(resolver, mock_policy, mock_repository):
    mock_repository.get_active_credentials_for_user.return_value = []
    # If policy forbids platform key, it can't resolve
    mock_policy.can_use_platform_credential.return_value = False
    assert await resolver.can_resolve("u1", "openai") is False

    # If policy allows platform key, it resolves
    mock_policy.can_use_platform_credential.return_value = True
    assert await resolver.can_resolve("u1", "openai") is True

    # If user has a key, it resolves regardless of policy
    mock_policy.can_use_platform_credential.return_value = False
    mock_repository.get_active_credentials_for_user.return_value = [MagicMock()]
    assert await resolver.can_resolve("u1", "openai") is True


@pytest.mark.asyncio
async def test_ensure_model_access_byok_skips_credits(
    resolver, mock_policy, mock_repository
):
    mock_repository.get_active_credentials_for_user.return_value = [MagicMock()]
    mock_policy.can_use_platform_credential.return_value = False
    await resolver.ensure_model_access("u1", ModelType.GPT_4O_MINI, user_credits=0)


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "plat_key", "ENVIRONMENT": "production"})
async def test_ensure_model_access_pay_per_use_allows_platform_key_without_legacy_credits(
    resolver, mock_policy, mock_repository
):
    """Credits are gated at CreditService.reserve_for_job, not here."""
    mock_repository.get_active_credentials_for_user.return_value = []
    mock_policy.can_use_platform_credential.return_value = True

    await resolver.ensure_model_access("u1", ModelType.GPT_4O_MINI, user_credits=0)


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "plat_key", "ENVIRONMENT": "development"})
async def test_ensure_model_access_pay_per_use_allows_platform_key_in_dev(
    resolver, mock_policy, mock_repository
):
    mock_repository.get_active_credentials_for_user.return_value = []
    mock_policy.can_use_platform_credential.return_value = True

    await resolver.ensure_model_access("u1", ModelType.GPT_4O_MINI, user_credits=0)


@pytest.mark.asyncio
async def test_resolve_user_credential_requires_byok(resolver, mock_repository):
    mock_repository.get_active_credentials_for_user.return_value = []
    with pytest.raises(ProviderError) as exc:
        await resolver.resolve_user_credential("u1", "openai")
    assert exc.value.kind == ProviderErrorKind.USER_CREDENTIAL_REQUIRED


@pytest.mark.asyncio
async def test_resolve_user_credential_returns_user_key(resolver, mock_repository):
    doc = MagicMock(is_default=True, updated_at=1, id="cred-1")
    mock_repository.get_active_credentials_for_user.return_value = [doc]
    mock_repository.decrypt_credential.return_value = "sk-user-only"
    cred = await resolver.resolve_user_credential("u1", "openai")
    assert cred.api_key == "sk-user-only"
    assert cred.is_platform is False
    assert cred.credential_id == "cred-1"


@pytest.mark.asyncio
async def test_ensure_user_credential_ok_when_present(resolver, mock_repository):
    mock_repository.get_active_credentials_for_user.return_value = [MagicMock()]
    await resolver.ensure_user_credential("u1", "openai")


@pytest.mark.asyncio
async def test_ensure_user_credential_missing(resolver, mock_repository):
    mock_repository.get_active_credentials_for_user.return_value = []
    with pytest.raises(ProviderError) as exc:
        await resolver.ensure_user_credential("u1", "openai")
    assert exc.value.kind == ProviderErrorKind.USER_CREDENTIAL_REQUIRED


@pytest.mark.asyncio
@patch.dict(os.environ, {"GEMINI_API_KEY": "gemini-platform", "GOOGLE_API_KEY": ""})
async def test_google_platform_key_accepts_gemini_alias(
    resolver, mock_policy, mock_repository
):
    mock_repository.get_active_credentials_for_user.return_value = []
    mock_policy.can_use_platform_credential.return_value = True
    res = await resolver.resolve("u1", "google")
    assert res.api_key == "gemini-platform"
    assert res.is_platform is True
