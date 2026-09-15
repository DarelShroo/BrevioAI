from __future__ import annotations

import os
from typing import Optional

TRUE_VALUES = frozenset({"1", "true", "yes"})
FALSE_VALUES = frozenset({"0", "false", "no"})

_DEFAULT_TOKENS_PER_MINUTE = 200_000
_DEFAULT_TEMPERATURE = 0.2
_DEFAULT_MAX_TOKEN_WAIT = 300
_DEFAULT_MAX_TOKENS = 4096


def current_environment() -> str:
    return os.getenv("ENVIRONMENT", "development").strip().lower() or "development"


def is_production_environment(environment: Optional[str] = None) -> bool:
    return (environment or current_environment()) == "production"


def env_first(*names: str, default: str = "") -> str:
    """Return the first non-empty environment value among ``names``."""
    for name in names:
        raw = os.getenv(name)
        if raw is not None and raw.strip() != "":
            return raw
    return default


def parse_bool_value(raw: str) -> bool:
    return raw.strip().lower() in TRUE_VALUES


def env_flag(name: str, default: bool = False) -> bool:
    """Truthy flag: ``1`` / ``true`` / ``yes``. Unset or blank uses ``default``."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return parse_bool_value(raw)


def env_override_bool(name: str) -> Optional[bool]:
    """Tri-state flag. ``None`` if unset/blank; otherwise true/false.

    Accepts the same tokens as ``env_flag`` so ``SUMMARY_LOCAL_USER_ACCESS=1``
    is not silently treated as false.
    """
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return None
    normalized = raw.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return False


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return default


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw.strip())
    except (TypeError, ValueError):
        return default


def env_optional_int(name: str) -> Optional[int]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return None
    return int(raw.strip())


def local_user_access(override_var: str, *, environment: Optional[str] = None) -> bool:
    override = env_override_bool(override_var)
    if override is not None:
        return override
    return not is_production_environment(environment)


def parse_enabled_ids(env_var: str) -> Optional[frozenset[str]]:
    raw = os.getenv(env_var)
    if raw is None or not raw.strip():
        return None
    return frozenset(
        part.strip().lower().replace("-", "_")
        for part in raw.split(",")
        if part.strip()
    )


def tokens_per_minute(default: int = _DEFAULT_TOKENS_PER_MINUTE) -> int:
    """Local token-bucket capacity.

    Canonical name: ``MAX_TOKEN_PER_MINUTE``.
    Legacy alias: ``TOKENS_PER_MINUTE`` (used only if the canonical name is unset).
    """
    raw = os.getenv("MAX_TOKEN_PER_MINUTE")
    if raw is None or raw.strip() == "":
        raw = os.getenv("TOKENS_PER_MINUTE")
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return default


def llm_temperature(default: float = _DEFAULT_TEMPERATURE) -> float:
    """Legacy env fallback. Summary sampling uses official per-model defaults."""
    return env_float("TEMPERATURE", default)


def max_token_wait_seconds(default: int = _DEFAULT_MAX_TOKEN_WAIT) -> int:
    return env_int("MAX_TOKEN_WAIT", default)


def max_tokens_fallback(default: int = _DEFAULT_MAX_TOKENS) -> int:
    """Fallback output-token cap used only when model capabilities are missing."""
    return env_int("MAX_TOKENS", default)


def keep_partials_enabled() -> bool:
    return env_flag("BREVIO_KEEP_PARTIALS", False)


def format_phase_enabled() -> bool:
    return env_flag("BREVIO_ENABLE_FORMAT_PHASE", False)


def min_tokens_for_postprocess_override() -> Optional[int]:
    return env_optional_int("BREVIO_MIN_TOKENS_FOR_POSTPROCESS")


def provider_quota_is_enabled() -> bool:
    return env_flag("PROVIDER_QUOTA_ENABLED", False)


def map_original_text_fallback_override() -> Optional[bool]:
    return env_override_bool("BREVIO_ALLOW_MAP_ORIGINAL_TEXT_FALLBACK")


def dev_allow_platform_override() -> bool:
    return env_flag("DEV_ALLOW_PLATFORM_OVERRIDE", True)


def access_token_expire_minutes(default: int = 15) -> int:
    return max(1, env_int("ACCESS_TOKEN_EXPIRE_MINUTES", default))


def refresh_token_expire_days(default: int = 7) -> int:
    return max(1, env_int("REFRESH_TOKEN_EXPIRE_DAYS", default))


def jwt_secret_key(default: str = "default_secret_key") -> str:
    """Canonical ``SECRET_TOKEN_KEY``; legacy alias ``SECRET_KEY``."""
    return env_first("SECRET_TOKEN_KEY", "SECRET_KEY", default=default)


def jwt_algorithm(default: str = "HS256") -> str:
    """Canonical ``TOKEN_ALGORITHM``; legacy alias ``ALGORITHM``."""
    return env_first("TOKEN_ALGORITHM", "ALGORITHM", default=default)
