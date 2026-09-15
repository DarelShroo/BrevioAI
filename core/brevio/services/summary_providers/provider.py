from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class CompletionRequest:
    model: str
    messages: list[dict[str, Any]]
    max_tokens: int
    temperature: float
    extra: dict[str, Any] = field(default_factory=dict)
    timeout: float = 120.0


@runtime_checkable
class SummaryProvider(Protocol):
    provider_id: str
    requires_api_key: bool
    is_local: bool

    async def complete(self, client: Any, request: CompletionRequest) -> Any:
        ...
