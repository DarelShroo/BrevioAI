import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from core.brevio.services.credential_resolver import (
    CredentialResolver,
    ResolvedCredential,
)
from core.brevio.services.platform_access_policy import PlatformAccessPolicy
from core.brevio.services.provider_registry import OllamaAdapter, ProviderRegistry
from core.brevio_api.models.errors.provider_errors import ProviderErrorKind
from core.shared.enums.model import ModelType


@pytest.mark.asyncio
async def test_ollama_adapter_validate_credential_success():
    adapter = OllamaAdapter()
    with patch("core.brevio.services.provider_registry.AsyncOpenAI") as mock_openai:
        # Configure mock
        mock_client_instance = MagicMock()
        mock_models = MagicMock()
        mock_models.list = AsyncMock(return_value={"data": [{"id": "qwen3:14b-q6"}]})
        mock_client_instance.models = mock_models
        mock_client_instance.close = AsyncMock()

        mock_openai.return_value = mock_client_instance

        result = await adapter.validate_credential(
            api_key="ollama", base_url="http://localhost:11434/v1"
        )
        assert result is True
        mock_models.list.assert_called_once()
        mock_client_instance.close.assert_called_once()


@pytest.mark.asyncio
async def test_ollama_adapter_validate_credential_failure():
    adapter = OllamaAdapter()
    with patch("core.brevio.services.provider_registry.AsyncOpenAI") as mock_openai:
        mock_client_instance = MagicMock()
        mock_models = MagicMock()
        mock_models.list = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client_instance.models = mock_models
        mock_client_instance.close = AsyncMock()

        mock_openai.return_value = mock_client_instance

        result = await adapter.validate_credential(
            api_key="ollama", base_url="http://localhost:11434/v1"
        )
        assert result is False


def test_ollama_adapter_map_error():
    adapter = OllamaAdapter()

    timeout_err = httpx.ReadTimeout("Timeout")
    assert adapter.map_error(timeout_err) == ProviderErrorKind.PROVIDER_ERROR

    async_timeout_err = asyncio.TimeoutError("Timeout")
    assert adapter.map_error(async_timeout_err) == ProviderErrorKind.PROVIDER_ERROR

    generic_err = Exception("Something else")
    assert adapter.map_error(generic_err) == ProviderErrorKind.PROVIDER_ERROR


@pytest.mark.asyncio
async def test_credential_resolver_ollama_platform():
    mock_repo = MagicMock()
    # Ensure it returns empty so we fallback to platform
    mock_repo.get_active_credentials_for_user = AsyncMock(return_value=[])

    mock_policy = MagicMock()
    mock_policy.can_use_platform_credential.return_value = False

    provider_registry = ProviderRegistry()

    resolver = CredentialResolver(mock_repo, mock_policy, provider_registry)

    with patch(
        "os.getenv",
        side_effect=lambda key, default="": "http://localhost:11434/v1"
        if key == "OLLAMA_API_URL"
        else default,
    ):
        resolved = await resolver.resolve(user_id="user_123", provider="ollama")

        assert resolved.is_platform is True
        assert resolved.api_key == "ollama-local-key"
        assert resolved.base_url == "http://localhost:11434/v1"
        assert resolved.credential_id == "local"


@pytest.mark.asyncio
async def test_summary_service_integration_ollama():
    """
    Test that checking connectivity and resolving clients works as expected
    when QWEN3_14B is selected.
    """
    from core.brevio.services.api_service import ApiService
    from core.shared.utils.model_capabilities import get_model_capabilities

    mock_repo = MagicMock()
    mock_repo.get_active_credentials_for_user = AsyncMock(return_value=[])
    mock_policy = MagicMock()
    mock_policy.can_use_platform_credential.return_value = False
    provider_registry = ProviderRegistry()

    resolver = CredentialResolver(mock_repo, mock_policy, provider_registry)

    queue_lock = asyncio.Lock()
    client_lock = asyncio.Lock()
    task_queue = asyncio.Queue()

    api_service = ApiService(
        running=True,
        task_queue=task_queue,
        queue_lock=queue_lock,
        client_lock=client_lock,
        tasks_put=0,
        task_done_calls=0,
        running_tasks=[],
        credential_resolver=resolver,
    )

    with patch(
        "os.getenv",
        side_effect=lambda key, default="": "http://localhost:11434/v1"
        if key == "OLLAMA_API_URL"
        else default,
    ):
        with patch("core.brevio.services.api_service.AsyncOpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            client = await api_service._initialize_client(
                ModelType.QWEN3_14B, "user_123"
            )

            mock_openai.assert_called_once_with(
                api_key="ollama-local-key",
                base_url="http://localhost:11434/v1",
                max_retries=0,
            )

            caps = get_model_capabilities(ModelType.QWEN3_14B)
            assert caps.provider == "ollama"
            assert caps.context_window == 16384
            assert caps.native_max_output_tokens == 8192


def test_qwen3_14b_q6_capabilities_and_quota_identity():
    from pathlib import Path

    from core.brevio.services.provider_quota.policy import (
        QuotaPolicyRegistry,
        load_quota_policies,
    )
    from core.shared.utils.model_capabilities import get_model_capabilities
    from core.shared.utils.pricing_registry import get_pricing_snapshot

    assert ModelType.QWEN3_14B.value == "qwen3:14b-q6"
    caps = get_model_capabilities(ModelType.QWEN3_14B)
    assert caps.provider == "ollama"
    assert caps.context_window == 16384
    assert caps.native_max_output_tokens == 8192
    assert caps.max_tokens_per_chunk == 3000
    assert caps.reduce_batch_tokens == 8000
    assert caps.supports_chunking is True

    pricing = get_pricing_snapshot(ModelType.QWEN3_14B)
    assert pricing.provider == "ollama"
    assert pricing.model == "qwen3:14b-q6"
    assert pricing.input_price_per_million == 0.0
    assert pricing.output_price_per_million == 0.0

    registry = QuotaPolicyRegistry(
        load_quota_policies(
            str(Path("core/brevio/config/provider_quotas.example.yaml"))
        )
    )
    policy = registry.resolve("ollama", "qwen3:14b-q6", require=True)
    assert policy.model == "qwen3:14b-q6"
    assert policy.max_in_flight == 1
    assert policy.lease_ttl_ms == 600000


def test_qwen3_32b_capabilities_and_quota_identity():
    from core.shared.utils.model_capabilities import get_model_capabilities
    from core.shared.utils.pricing_registry import get_pricing_snapshot

    caps = get_model_capabilities(ModelType.QWEN3_32B)
    assert ModelType.QWEN3_32B.value == "qwen3:32b"
    assert caps.provider == "ollama"
    assert caps.context_window == 32768
    assert caps.native_max_output_tokens == 16384
    assert caps.max_tokens_per_chunk == 4000
    assert caps.reduce_batch_tokens == 10000
    assert caps.supports_chunking is True

    pricing = get_pricing_snapshot(ModelType.QWEN3_32B)
    assert pricing.provider == "ollama"
    assert pricing.input_price_per_million == 0.0
    assert pricing.output_price_per_million == 0.0


def test_qwen3_32b_quota_policy_from_example_yaml():
    from pathlib import Path

    from core.brevio.services.provider_quota.policy import (
        QuotaPolicyRegistry,
        load_quota_policies,
    )

    path = Path("core/brevio/config/provider_quotas.example.yaml")
    registry = QuotaPolicyRegistry(load_quota_policies(str(path)))
    policy = registry.resolve("ollama", "qwen3:32b", require=True)
    assert policy.model == "qwen3:32b"
    assert policy.max_in_flight == 1
    assert policy.lease_ttl_ms == 600000


def test_deepseek_r1_local_iq3_xs_capabilities_and_quota():
    from pathlib import Path

    from core.brevio.services.provider_quota.policy import (
        QuotaPolicyRegistry,
        load_quota_policies,
    )
    from core.shared.utils.model_capabilities import get_model_capabilities
    from core.shared.utils.pricing_registry import get_pricing_snapshot

    assert ModelType.DEEPSEEK_R1_LOCAL_IQ3_XS.value == "deepseek-r1-local:iq3-xs"
    caps = get_model_capabilities(ModelType.DEEPSEEK_R1_LOCAL_IQ3_XS)
    assert caps.provider == "ollama"
    assert caps.context_window == 32768
    assert caps.native_max_output_tokens == 8192
    assert caps.max_tokens_per_chunk == 2500
    assert caps.reduce_batch_tokens == 6000
    assert caps.chunk_overlap == 300

    pricing = get_pricing_snapshot(ModelType.DEEPSEEK_R1_LOCAL_IQ3_XS)
    assert pricing.provider == "ollama"
    assert pricing.input_price_per_million == 0.0

    registry = QuotaPolicyRegistry(
        load_quota_policies(
            str(Path("core/brevio/config/provider_quotas.example.yaml"))
        )
    )
    policy = registry.resolve("ollama", "deepseek-r1-local:iq3-xs", require=True)
    assert policy.model == "deepseek-r1-local:iq3-xs"
    assert policy.max_in_flight == 1
    assert policy.lease_ttl_ms == 600000


def test_gpt_oss_20b_capabilities_and_quota():
    from pathlib import Path

    from core.brevio.services.provider_quota.policy import (
        QuotaPolicyRegistry,
        load_quota_policies,
    )
    from core.shared.utils.model_capabilities import get_model_capabilities
    from core.shared.utils.pricing_registry import get_pricing_snapshot

    assert ModelType.GPT_OSS_20B.value == "gpt-oss:20b"
    caps = get_model_capabilities(ModelType.GPT_OSS_20B)
    assert caps.provider == "ollama"
    assert caps.context_window == 32768
    assert caps.native_max_output_tokens == 8192
    assert caps.max_tokens_per_chunk == 3000
    assert caps.reduce_batch_tokens == 8000
    assert caps.chunk_overlap == 256

    pricing = get_pricing_snapshot(ModelType.GPT_OSS_20B)
    assert pricing.provider == "ollama"
    assert pricing.input_price_per_million == 0.0

    registry = QuotaPolicyRegistry(
        load_quota_policies(
            str(Path("core/brevio/config/provider_quotas.example.yaml"))
        )
    )
    policy = registry.resolve("ollama", "gpt-oss:20b", require=True)
    assert policy.model == "gpt-oss:20b"
    assert policy.max_in_flight == 1
    assert policy.lease_ttl_ms == 600000


def test_gemma4_31b_iq3_capabilities_and_quota():
    from pathlib import Path

    from core.brevio.services.provider_quota.policy import (
        QuotaPolicyRegistry,
        load_quota_policies,
    )
    from core.shared.utils.model_capabilities import get_model_capabilities
    from core.shared.utils.pricing_registry import get_pricing_snapshot

    assert ModelType.GEMMA4_31B_IQ3.value == "batiai/gemma4-31b:iq3"
    caps = get_model_capabilities(ModelType.GEMMA4_31B_IQ3)
    assert caps.provider == "ollama"
    assert caps.context_window == 32768
    assert caps.native_max_output_tokens == 8192
    assert caps.max_tokens_per_chunk == 2500
    assert caps.reduce_batch_tokens == 6000
    assert caps.chunk_overlap == 256

    pricing = get_pricing_snapshot(ModelType.GEMMA4_31B_IQ3)
    assert pricing.provider == "ollama"
    assert pricing.model == "batiai/gemma4-31b:iq3"
    assert pricing.input_price_per_million == 0.0

    registry = QuotaPolicyRegistry(
        load_quota_policies(
            str(Path("core/brevio/config/provider_quotas.example.yaml"))
        )
    )
    policy = registry.resolve("ollama", "batiai/gemma4-31b:iq3", require=True)
    assert policy.model == "batiai/gemma4-31b:iq3"
    assert policy.max_in_flight == 1
    assert policy.lease_ttl_ms == 600000
