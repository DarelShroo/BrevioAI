import pytest

from core.shared.utils.environment import (
    access_token_expire_minutes,
    current_environment,
    env_flag,
    env_override_bool,
    is_production_environment,
    jwt_algorithm,
    jwt_secret_key,
    keep_partials_enabled,
    llm_temperature,
    local_user_access,
    parse_enabled_ids,
    tokens_per_minute,
)


def test_current_environment_normalizes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", " Production ")
    assert current_environment() == "production"
    assert is_production_environment() is True


def test_local_user_access_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUMMARY_LOCAL_USER_ACCESS", raising=False)
    assert (
        local_user_access("SUMMARY_LOCAL_USER_ACCESS", environment="development")
        is True
    )
    assert (
        local_user_access("SUMMARY_LOCAL_USER_ACCESS", environment="production")
        is False
    )


def test_env_override_bool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLAG", raising=False)
    assert env_override_bool("FLAG") is None
    monkeypatch.setenv("FLAG", "true")
    assert env_override_bool("FLAG") is True
    monkeypatch.setenv("FLAG", "1")
    assert env_override_bool("FLAG") is True
    monkeypatch.setenv("FLAG", "yes")
    assert env_override_bool("FLAG") is True
    monkeypatch.setenv("FLAG", "false")
    assert env_override_bool("FLAG") is False
    monkeypatch.setenv("FLAG", "0")
    assert env_override_bool("FLAG") is False
    monkeypatch.setenv("FLAG", "no")
    assert env_override_bool("FLAG") is False


def test_env_flag_accepts_common_truthy_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BREVIO_KEEP_PARTIALS", raising=False)
    assert env_flag("BREVIO_KEEP_PARTIALS") is False
    monkeypatch.setenv("BREVIO_KEEP_PARTIALS", "1")
    assert keep_partials_enabled() is True
    monkeypatch.setenv("BREVIO_KEEP_PARTIALS", "yes")
    assert keep_partials_enabled() is True


def test_parse_enabled_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENABLED_SUMMARY_PROVIDERS", raising=False)
    assert parse_enabled_ids("ENABLED_SUMMARY_PROVIDERS") is None
    monkeypatch.setenv("ENABLED_SUMMARY_PROVIDERS", "openai, DeepSeek, google")
    assert parse_enabled_ids("ENABLED_SUMMARY_PROVIDERS") == frozenset(
        {"openai", "deepseek", "google"}
    )


def test_tokens_per_minute_canonical_name_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_TOKEN_PER_MINUTE", "111")
    monkeypatch.setenv("TOKENS_PER_MINUTE", "222")
    assert tokens_per_minute() == 111


def test_tokens_per_minute_legacy_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAX_TOKEN_PER_MINUTE", raising=False)
    monkeypatch.setenv("TOKENS_PER_MINUTE", "333")
    assert tokens_per_minute() == 333


def test_jwt_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECRET_TOKEN_KEY", raising=False)
    monkeypatch.delenv("TOKEN_ALGORITHM", raising=False)
    monkeypatch.setenv("SECRET_KEY", "legacy-secret")
    monkeypatch.setenv("ALGORITHM", "HS384")
    assert jwt_secret_key() == "legacy-secret"
    assert jwt_algorithm() == "HS384"
    monkeypatch.setenv("SECRET_TOKEN_KEY", "canonical-secret")
    monkeypatch.setenv("TOKEN_ALGORITHM", "HS256")
    assert jwt_secret_key() == "canonical-secret"
    assert jwt_algorithm() == "HS256"


def test_access_token_ttl_reads_env_at_call_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "42")
    assert access_token_expire_minutes() == 42


def test_temperature_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEMPERATURE", raising=False)
    assert llm_temperature() == 0.2
    monkeypatch.setenv("TEMPERATURE", "0.7")
    assert llm_temperature() == 0.7
