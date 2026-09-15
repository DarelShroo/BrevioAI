from core.shared.enums.model import ModelType
from core.shared.utils.model_catalog import (
    ModelAccess,
    build_models_payload,
    catalog_entry_for_model,
    is_known_provider,
    is_local_provider,
    list_model_catalog,
    list_public_model_ids,
    model_requires_api_key,
    provider_requires_api_key,
)


def test_catalog_splits_local_and_paid_models() -> None:
    catalog = list_model_catalog()
    ids = [entry.id for entry in catalog]

    assert ModelType.DEEPSEEK_V4_PRO.value in ids
    assert ModelType.GPT_5_6.value in ids
    assert ModelType.GROK_4_6.value in ids
    assert ModelType.CLAUDE_SONNET_5.value in ids
    assert ids == list_public_model_ids()
    assert ids == sorted(
        ids,
        key=lambda model_id: (
            0
            if next(e for e in catalog if e.id == model_id).access is ModelAccess.LOCAL
            else 1,
            0 if next(e for e in catalog if e.id == model_id).recommended else 1,
            0 if next(e for e in catalog if e.id == model_id).status == "stable" else 1,
            model_id,
        ),
    )

    local = [entry for entry in catalog if entry.access is ModelAccess.LOCAL]
    paid = [entry for entry in catalog if entry.access is ModelAccess.PAY_PER_USE]

    assert local
    assert paid
    assert all(entry.provider == "ollama" for entry in local)
    assert all(not entry.requires_api_key for entry in local)
    assert all(entry.requires_api_key for entry in paid)
    assert {entry.id for entry in local} >= {
        ModelType.QWEN3_8B.value,
        ModelType.QWEN3_14B.value,
        ModelType.GPT_OSS_20B.value,
    }
    assert {entry.id for entry in paid} >= {
        ModelType.GPT_4O_MINI.value,
        ModelType.GPT_4.value,
        ModelType.GEMINI_3_1_FLASH_LITE.value,
        ModelType.DEEPSEEK_FLASH.value,
    }


def test_local_models_do_not_require_api_key() -> None:
    local = catalog_entry_for_model(ModelType.QWEN3_8B)
    paid = catalog_entry_for_model(ModelType.GPT_4O_MINI)

    assert is_local_provider("OLLAMA") is True
    assert is_local_provider("openai") is False
    assert provider_requires_api_key("ollama") is False
    assert provider_requires_api_key("openai") is True
    assert model_requires_api_key(ModelType.QWEN3_8B) is False
    assert model_requires_api_key(ModelType.GPT_4O_MINI) is True
    assert local.access is ModelAccess.LOCAL
    assert paid.access is ModelAccess.PAY_PER_USE
    assert is_known_provider("google") is True
    assert is_known_provider("anthropic") is True
    assert is_known_provider("xai") is True


def test_catalog_payload_exposes_per_model_parameters() -> None:
    payload = build_models_payload()
    by_id = {item["id"]: item for item in payload["catalog"]}
    gpt56 = by_id[ModelType.GPT_5_6.value]
    assert gpt56["output_token_param"] == "max_completion_tokens"
    assert "temperature" not in gpt56["parameters"]
    assert "max_output_tokens" not in gpt56["parameters"]
    assert "reasoning_effort" in gpt56["parameters"]
    assert gpt56["reasoning_values"] == [
        "none",
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
    ]
    assert "context_window" not in gpt56
    assert "native_max_output_tokens" not in gpt56
    assert "summary_max_output_tokens" not in gpt56
    grok = by_id[ModelType.GROK_4_6.value]
    assert grok["provider"] == "xai"
    assert grok["reasoning_values"] == ["low", "medium", "high", "xhigh"]
    assert "temperature" not in grok["parameters"]
    assert "max_output_tokens" not in grok["parameters"]
    sonnet = by_id[ModelType.CLAUDE_SONNET_5.value]
    assert sonnet["provider"] == "anthropic"
    assert "effort" in sonnet["parameters"]
    assert "temperature" not in sonnet["parameters"]
    gpt4 = by_id[ModelType.GPT_4.value]
    assert gpt4["status"] == "deprecated"
    assert gpt4["recommended"] is False
    assert gpt4["retirement"] == "2026-10-23"
    mini = by_id[ModelType.GPT_4O_MINI.value]
    assert "temperature" not in mini["parameters"]
    assert "max_output_tokens" not in mini["parameters"]
    provider_ids = {item["id"] for item in payload["providers"]}
    assert {
        "openai",
        "google",
        "xai",
        "deepseek",
        "anthropic",
        "ollama",
    } <= provider_ids


def test_models_payload_keeps_legacy_ids_and_adds_catalog() -> None:
    payload = build_models_payload(["qwen3:8b", "gpt-4o-mini", "claude-3"])

    assert payload["models"] == ["qwen3:8b", "gpt-4o-mini", "claude-3"]
    by_id = {item["id"]: item for item in payload["catalog"]}
    assert by_id["qwen3:8b"]["access"] == "local"
    assert by_id["qwen3:8b"]["requires_api_key"] is False
    assert by_id["gpt-4o-mini"]["access"] == "pay_per_use"
    assert by_id["gpt-4o-mini"]["requires_api_key"] is True
    assert by_id["claude-3"]["provider"] == "unknown"
    assert by_id["claude-3"]["requires_api_key"] is True
    provider_ids = {item["id"] for item in payload["providers"]}
    assert "ollama" in provider_ids
    assert "openai" in provider_ids
