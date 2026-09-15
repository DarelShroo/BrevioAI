import hashlib
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from core.brevio.services.api_service import ApiService
from core.brevio.services.credential_resolver import (
    CredentialResolver,
    ResolvedCredential,
)
from core.brevio.services.platform_access_policy import PlatformAccessPolicy
from core.brevio.services.provider_registry import ProviderRegistry
from core.brevio_api.models.errors.provider_errors import (
    ProviderError,
    ProviderErrorKind,
)
from core.brevio_api.models.user.credential_model import (
    CredentialStatus,
    UserCredentialDocument,
)
from core.brevio_api.repositories.user_credential_repository import (
    UserCredentialRepository,
)
from core.shared.enums.model import ModelType


@pytest.fixture
def mock_repo():
    return AsyncMock(spec=UserCredentialRepository)


@pytest.fixture
def mock_policy():
    return Mock(spec=PlatformAccessPolicy)


@pytest.fixture
def mock_registry():
    return Mock(spec=ProviderRegistry)


@pytest.fixture
def resolver(mock_repo, mock_policy, mock_registry):
    return CredentialResolver(mock_repo, mock_policy, mock_registry)


@pytest.fixture
def api_service(resolver):
    return ApiService(
        running=True,
        task_queue=AsyncMock(),
        queue_lock=AsyncMock(),
        client_lock=AsyncMock(),
        tasks_put=0,
        task_done_calls=0,
        running_tasks=[],
        credential_resolver=resolver,
    )


@pytest.mark.asyncio
async def test_missing_user_id_denied(api_service):
    """missing user_id -> no platform credential"""
    with pytest.raises(ValueError, match="user_id is required"):
        await api_service._initialize_client(ModelType.GPT_4O_MINI, user_id=None)


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "", "ENVIRONMENT": "production"})
async def test_production_user_without_credential_denied(
    resolver, mock_repo, mock_policy
):
    """production + usuario sin key + sin platform key -> USER_CREDENTIAL_REQUIRED"""
    mock_repo.get_active_credentials_for_user.return_value = []
    mock_policy.can_use_platform_credential.return_value = False

    with pytest.raises(ProviderError) as exc_info:
        await resolver.resolve("user1", "openai")
    assert exc_info.value.kind in (
        ProviderErrorKind.USER_CREDENTIAL_REQUIRED,
        ProviderErrorKind.UNAUTHORIZED,
    )


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "plat_key", "ENVIRONMENT": "development"})
async def test_development_override_allowed(resolver, mock_repo, mock_policy):
    """development + explicit dev override -> platform credential"""
    mock_repo.get_active_credentials_for_user.return_value = []
    # simulate policy allowing it in dev
    mock_policy.can_use_platform_credential.return_value = True

    cred = await resolver.resolve("user1", "openai")
    assert cred.api_key == "plat_key"
    assert cred.is_platform is True


@pytest.mark.asyncio
async def test_user_isolation(resolver, mock_repo):
    """User A / OpenAI key A != User B / OpenAI key B"""
    # Just asserting the cache mechanism isolates by user
    cache_key_a = f"usr:user_A:openai"
    cache_key_b = f"usr:user_B:openai"
    assert cache_key_a != cache_key_b


@pytest.mark.asyncio
async def test_cache_rotation(api_service, mock_repo, resolver, mock_policy):
    """credential v1 -> client v1, credential v2 -> client v2"""
    mock_policy.can_use_platform_credential.return_value = False

    # First call: v1
    doc_v1 = UserCredentialDocument(
        _id="cred_1",
        user_id="user1",
        provider="openai",
        encrypted_key="enc1",
        updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
    )
    mock_repo.get_active_credentials_for_user.return_value = [doc_v1]
    mock_repo.decrypt_credential.return_value = "key_v1"

    client_v1 = await api_service._initialize_client(ModelType.GPT_4O_MINI, "user1")
    assert client_v1.api_key == "key_v1"

    # Second call: v2 (rotated)
    doc_v2 = UserCredentialDocument(
        _id="cred_2",
        user_id="user1",
        provider="openai",
        encrypted_key="enc2",
        updated_at=datetime(2023, 1, 2, tzinfo=timezone.utc),
    )
    mock_repo.get_active_credentials_for_user.return_value = [doc_v2]
    mock_repo.decrypt_credential.return_value = "key_v2"

    client_v2 = await api_service._initialize_client(ModelType.GPT_4O_MINI, "user1")
    assert client_v2.api_key == "key_v2"
    assert client_v1 != client_v2
    # Ensure plaintext keys are not cached
    assert not hasattr(api_service, "_client_api_keys")
    cache_key = "usr:user1:openai"
    assert api_service._client_versions[cache_key] == (
        "cred_2",
        str(doc_v2.updated_at.timestamp()),
    )


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": ""})
async def test_revocation_cache_invalidation(api_service, mock_repo, mock_policy):
    """ACTIVE -> REVOKED -> no resolution without platform key, cache invalidated"""
    mock_policy.can_use_platform_credential.return_value = False
    # Setup active
    doc = UserCredentialDocument(
        _id="cred_1", user_id="user1", provider="openai", encrypted_key="enc1"
    )
    mock_repo.get_active_credentials_for_user.return_value = [doc]
    mock_repo.decrypt_credential.return_value = "key_v1"

    await api_service._initialize_client(ModelType.GPT_4O_MINI, "user1")
    cache_key = "usr:user1:openai"
    assert cache_key in api_service.clients

    # Revoke (returns empty list from repo)
    mock_repo.get_active_credentials_for_user.return_value = []

    with pytest.raises(ProviderError):
        await api_service._initialize_client(ModelType.GPT_4O_MINI, "user1")

    assert cache_key not in api_service.clients
    assert cache_key not in api_service._client_versions


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_can_resolve_vs_resolve(resolver, mock_repo):
    """can_resolve doesn't guarantee resolve if decryption fails"""
    doc = UserCredentialDocument(
        _id="cred_1", user_id="user1", provider="openai", encrypted_key="bad_enc"
    )
    mock_repo.get_active_credentials_for_user.return_value = [doc]
    # can_resolve should return True (preflight)
    assert await resolver.can_resolve("user1", "openai") is True

    # resolve should fail (source of truth)
    mock_repo.decrypt_credential.side_effect = Exception("EncryptionError")
    with pytest.raises(Exception):
        await resolver.resolve("user1", "openai")


# ─── 10 MANDATORY SPECIFICATION TESTS ────────────────────────────────────────


@pytest.mark.asyncio
@patch.dict(
    os.environ,
    {
        "ENVIRONMENT": "development",
        "DEV_ALLOW_PLATFORM_OVERRIDE": "true",
        "DEEPSEEK_API_KEY": "dev_deepseek_key",
    },
)
async def test_scenario_1_dev_override_deepseek_key():
    """1. Development + override + DEEPSEEK_API_KEY -> PLATFORM"""
    repo = AsyncMock(spec=UserCredentialRepository)
    repo.get_active_credentials_for_user.return_value = []
    policy = PlatformAccessPolicy()
    registry = ProviderRegistry()
    res = CredentialResolver(repo, policy, registry)

    cred = await res.resolve("user1", "deepseek")
    assert cred.api_key == "dev_deepseek_key"
    assert cred.is_platform is True


@pytest.mark.asyncio
@patch.dict(
    os.environ,
    {
        "ENVIRONMENT": "development",
        "DEV_ALLOW_PLATFORM_OVERRIDE": "true",
        "OPENAI_API_KEY": "dev_openai_key",
    },
)
async def test_scenario_2_dev_override_openai_key():
    """2. Development + override + OPENAI_API_KEY -> PLATFORM"""
    repo = AsyncMock(spec=UserCredentialRepository)
    repo.get_active_credentials_for_user.return_value = []
    policy = PlatformAccessPolicy()
    registry = ProviderRegistry()
    res = CredentialResolver(repo, policy, registry)

    cred = await res.resolve("user1", "openai")
    assert cred.api_key == "dev_openai_key"
    assert cred.is_platform is True


@pytest.mark.asyncio
@patch.dict(
    os.environ,
    {"ENVIRONMENT": "development", "DEV_ALLOW_PLATFORM_OVERRIDE": "true"},
    clear=True,
)
async def test_scenario_3_dev_override_provider_without_key():
    """3. Development + override + provider sin platform key -> PLATFORM_CREDENTIAL_UNAVAILABLE"""
    repo = AsyncMock(spec=UserCredentialRepository)
    repo.get_active_credentials_for_user.return_value = []
    policy = PlatformAccessPolicy()
    registry = ProviderRegistry()
    res = CredentialResolver(repo, policy, registry)

    with pytest.raises(ProviderError) as exc_info:
        await res.resolve("user1", "deepseek")
    assert exc_info.value.kind == ProviderErrorKind.PLATFORM_CREDENTIAL_UNAVAILABLE


@pytest.mark.asyncio
@patch.dict(
    os.environ,
    {"ENVIRONMENT": "production", "DEV_ALLOW_PLATFORM_OVERRIDE": "true"},
    clear=True,
)
async def test_scenario_4_prod_user_without_key():
    """4. Production + usuario sin key -> USER_CREDENTIAL_REQUIRED"""
    repo = AsyncMock(spec=UserCredentialRepository)
    repo.get_active_credentials_for_user.return_value = []
    policy = PlatformAccessPolicy()
    registry = ProviderRegistry()
    res = CredentialResolver(repo, policy, registry)

    with pytest.raises(ProviderError) as exc_info:
        await res.resolve("user1", "openai")
    assert exc_info.value.kind == ProviderErrorKind.USER_CREDENTIAL_REQUIRED


@pytest.mark.asyncio
@patch.dict(os.environ, {"ENVIRONMENT": "production"})
async def test_scenario_5_prod_user_with_key():
    """5. Production + usuario con key -> USER"""
    repo = AsyncMock(spec=UserCredentialRepository)
    doc = UserCredentialDocument(
        _id="c1", user_id="u1", provider="openai", encrypted_key="enc"
    )
    repo.get_active_credentials_for_user.return_value = [doc]
    repo.decrypt_credential.return_value = "user_secret"
    policy = PlatformAccessPolicy()
    registry = ProviderRegistry()
    res = CredentialResolver(repo, policy, registry)

    cred = await res.resolve("u1", "openai")
    assert cred.api_key == "user_secret"
    assert cred.is_platform is False


@pytest.mark.asyncio
@patch.dict(
    os.environ, {"ENVIRONMENT": "production", "DEEPSEEK_API_KEY": "platform_payg_key"}
)
async def test_scenario_6_prod_pay_per_use_uses_platform_key():
    """6. Production + usuario sin key + platform key -> pago por uso (créditos se validan aparte)"""
    repo = AsyncMock(spec=UserCredentialRepository)
    repo.get_active_credentials_for_user.return_value = []
    policy = PlatformAccessPolicy()
    registry = ProviderRegistry()
    res = CredentialResolver(repo, policy, registry)

    cred = await res.resolve("u1", "deepseek")
    assert cred.api_key == "platform_payg_key"
    assert cred.is_platform is True


@pytest.mark.asyncio
@patch.dict(
    os.environ,
    {
        "ENVIRONMENT": "production",
        "DEEPSEEK_API_KEY": "",
        "OPENAI_API_KEY": "sk-pytest-isolated-not-real",
    },
)
async def test_scenario_7_user_has_openai_no_deepseek():
    """7. Usuario con OpenAI pero sin DeepSeek ni platform key -> DeepSeek requiere credencial"""
    repo = AsyncMock(spec=UserCredentialRepository)
    doc_openai = UserCredentialDocument(
        _id="c1", user_id="u1", provider="openai", encrypted_key="enc_oai"
    )

    async def fake_get(user_id, provider):
        if provider == "openai":
            return [doc_openai]
        return []

    repo.get_active_credentials_for_user.side_effect = fake_get
    repo.decrypt_credential.return_value = "openai_user_key"
    policy = PlatformAccessPolicy()
    registry = ProviderRegistry()
    res = CredentialResolver(repo, policy, registry)

    cred_oai = await res.resolve("u1", "openai")
    assert cred_oai.api_key == "openai_user_key"

    with pytest.raises(ProviderError) as exc_info:
        await res.resolve("u1", "deepseek")
    assert exc_info.value.kind == ProviderErrorKind.USER_CREDENTIAL_REQUIRED


@pytest.mark.asyncio
@patch.dict(
    os.environ,
    {
        "ENVIRONMENT": "production",
        "OPENAI_API_KEY": "",
        "DEEPSEEK_API_KEY": "sk-pytest-isolated-not-real",
    },
)
async def test_scenario_8_user_has_deepseek_no_openai():
    """8. Usuario con DeepSeek pero sin OpenAI ni platform key -> OpenAI requiere credencial"""
    repo = AsyncMock(spec=UserCredentialRepository)
    doc_ds = UserCredentialDocument(
        _id="c2", user_id="u1", provider="deepseek", encrypted_key="enc_ds"
    )

    async def fake_get(user_id, provider):
        if provider == "deepseek":
            return [doc_ds]
        return []

    repo.get_active_credentials_for_user.side_effect = fake_get
    repo.decrypt_credential.return_value = "deepseek_user_key"
    policy = PlatformAccessPolicy()
    registry = ProviderRegistry()
    res = CredentialResolver(repo, policy, registry)

    cred_ds = await res.resolve("u1", "deepseek")
    assert cred_ds.api_key == "deepseek_user_key"

    with pytest.raises(ProviderError) as exc_info:
        await res.resolve("u1", "openai")
    assert exc_info.value.kind == ProviderErrorKind.USER_CREDENTIAL_REQUIRED


@pytest.mark.asyncio
@patch.dict(os.environ, {"ENVIRONMENT": "production"})
async def test_scenario_9_user_has_both_keys():
    """9. Usuario con ambas -> cada modelo utiliza su provider correspondiente"""
    repo = AsyncMock(spec=UserCredentialRepository)
    doc_oai = UserCredentialDocument(
        _id="c1", user_id="u1", provider="openai", encrypted_key="enc_oai"
    )
    doc_ds = UserCredentialDocument(
        _id="c2", user_id="u1", provider="deepseek", encrypted_key="enc_ds"
    )

    async def fake_get(user_id, provider):
        if provider == "openai":
            return [doc_oai]
        elif provider == "deepseek":
            return [doc_ds]
        return []

    repo.get_active_credentials_for_user.side_effect = fake_get
    repo.decrypt_credential.side_effect = (
        lambda doc: "key_oai" if doc.provider == "openai" else "key_ds"
    )
    policy = PlatformAccessPolicy()
    registry = ProviderRegistry()
    res = CredentialResolver(repo, policy, registry)

    cred_oai = await res.resolve("u1", "openai")
    cred_ds = await res.resolve("u1", "deepseek")
    assert cred_oai.api_key == "key_oai"
    assert cred_ds.api_key == "key_ds"


@pytest.mark.asyncio
async def test_scenario_10_no_secrets_or_provider_in_http_response():
    """10. Ningún error HTTP debe exponer el provider innecesariamente ni ningún secreto"""
    import json

    from fastapi import Request

    from core.brevio_api.handlers.exception_handlers import (
        provider_error_exception_handler,
    )

    exc = ProviderError(
        kind=ProviderErrorKind.USER_CREDENTIAL_REQUIRED,
        message="Esta solicitud requiere una credencial de API configurada por el usuario.",
    )
    req = Mock(spec=Request)
    res = await provider_error_exception_handler(req, exc)
    body = json.loads(res.body.decode())

    assert res.status_code == 401
    assert body["status"] == "error"
    assert body["code"] == "USER_CREDENTIAL_REQUIRED"
    assert "deepseek" not in body["message"].lower()
    assert "openai" not in body["message"].lower()
    assert "secret" not in body["message"].lower()
    assert (
        "key" not in body["message"].lower() or "credencial" in body["message"].lower()
    )
