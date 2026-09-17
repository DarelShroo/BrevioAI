"""Abuse cooldown / violation tracking (FASE 7). Operational Redis only."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from core.brevio_api.services.anti_abuse.config import (
    abuse_cooldown_seconds,
    abuse_violation_threshold,
    abuse_violation_ttl_seconds,
    anti_abuse_enabled,
    anti_abuse_redis_url,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CooldownStatus:
    active: bool
    retry_after: int
    violations: int


class AbuseGuard:
    def __init__(self, redis_client: Any | None = None) -> None:
        self._client = redis_client
        self._owns = redis_client is None

    def _get(self) -> Any:
        if self._client is not None:
            return self._client
        import redis

        self._client = redis.Redis.from_url(
            anti_abuse_redis_url(), decode_responses=True
        )
        return self._client

    def close(self) -> None:
        if self._owns and self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    @staticmethod
    def violations_key(subject: str) -> str:
        return f"antiabuse:violations:{subject}"

    @staticmethod
    def cooldown_key(subject: str) -> str:
        return f"antiabuse:cooldown:{subject}"

    def ping(self) -> bool:
        try:
            return bool(self._get().ping())
        except Exception:
            return False

    def check_cooldown(self, subject: str) -> CooldownStatus:
        if not anti_abuse_enabled():
            return CooldownStatus(False, 0, 0)
        try:
            client = self._get()
            ttl = int(client.ttl(self.cooldown_key(subject)) or -2)
            violations = int(client.get(self.violations_key(subject)) or 0)
            if ttl > 0:
                return CooldownStatus(True, ttl, violations)
            return CooldownStatus(False, 0, violations)
        except Exception:
            # Fail closed for cooldown check on expensive paths is handled by caller.
            return CooldownStatus(False, 0, 0)

    def record_violation(self, subject: str) -> CooldownStatus:
        """Increment violation counter; enter cooldown when threshold reached."""
        if not anti_abuse_enabled():
            return CooldownStatus(False, 0, 0)
        try:
            client = self._get()
            vkey = self.violations_key(subject)
            n = int(client.incr(vkey))
            if n == 1:
                client.expire(vkey, abuse_violation_ttl_seconds())
            threshold = abuse_violation_threshold()
            if n >= threshold:
                cool = abuse_cooldown_seconds()
                client.set(self.cooldown_key(subject), "1", ex=cool)
                logger.warning(
                    "event=anti_abuse_cooldown subject=%s violations=%s cooldown_s=%s",
                    subject,
                    n,
                    cool,
                )
                return CooldownStatus(True, cool, n)
            return CooldownStatus(False, 0, n)
        except Exception as exc:
            logger.error(
                "event=anti_abuse_record_failed subject=%s error=%s",
                subject,
                type(exc).__name__,
            )
            return CooldownStatus(False, 0, 0)
