"""Process-safe event broker: Redis Streams in production, in-memory for tests."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from collections import defaultdict
from typing import AsyncIterator, Protocol
from urllib.parse import urlparse

from core.brevio_api.events.models import SummaryJobEvent

logger = logging.getLogger(__name__)

_HISTORY_LIMIT = 200
_STREAM_TTL_SECONDS = 86_400
_DEFAULT_BLOCK_MS = 15_000


class EventBroker(Protocol):
    def publish(self, user_id: str, event: SummaryJobEvent) -> SummaryJobEvent:
        ...

    def subscribe(
        self, user_id: str, last_event_id: str | None = None
    ) -> AsyncIterator[SummaryJobEvent]:
        ...

    def subscriber_count(self, user_id: str) -> int:
        ...


def is_redis_url(url: str | None) -> bool:
    if not url:
        return False
    scheme = urlparse(url).scheme.lower()
    return scheme in {"redis", "rediss"}


def events_redis_url() -> str | None:
    from core.shared.utils.redis_url import resolve_redis_url

    explicit = os.getenv("EVENTS_REDIS_URL")
    if is_redis_url(explicit):
        return resolve_redis_url(explicit)
    broker = os.getenv("CELERY_BROKER_URL")
    if is_redis_url(broker):
        return resolve_redis_url(broker)
    return None


def stream_key(user_id: str) -> str:
    return f"brevio:events:{user_id}"


class InMemoryEventBroker:
    """Same-process broker used by tests and when Redis is not configured."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seq = 0
        self._history: dict[str, list[SummaryJobEvent]] = defaultdict(list)
        self._subscribers: dict[
            str, list[tuple[asyncio.Queue[SummaryJobEvent], asyncio.AbstractEventLoop]]
        ] = defaultdict(list)

    def publish(self, user_id: str, event: SummaryJobEvent) -> SummaryJobEvent:
        with self._lock:
            self._seq += 1
            if not event.event_id:
                event.event_id = str(self._seq)
            history = self._history[user_id]
            history.append(event)
            del history[:-_HISTORY_LIMIT]
            subscribers = list(self._subscribers.get(user_id, []))
        for queue, loop in subscribers:
            self._put(queue, loop, event)
        return event

    def _put(
        self,
        queue: asyncio.Queue[SummaryJobEvent],
        loop: asyncio.AbstractEventLoop,
        event: SummaryJobEvent,
    ) -> None:
        def enqueue() -> None:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Dropping summary event for a slow SSE subscriber")

        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            enqueue()
            return
        try:
            loop.call_soon_threadsafe(enqueue)
        except RuntimeError:
            logger.debug("SSE subscriber loop is closed; skipped notify")

    async def subscribe(
        self, user_id: str, last_event_id: str | None = None
    ) -> AsyncIterator[SummaryJobEvent]:
        queue: asyncio.Queue[SummaryJobEvent] = asyncio.Queue(maxsize=256)
        loop = asyncio.get_running_loop()
        with self._lock:
            self._subscribers[user_id].append((queue, loop))
            replay = self._replay(user_id, last_event_id)
        try:
            for event in replay:
                yield event
            while True:
                yield await queue.get()
        finally:
            with self._lock:
                current = self._subscribers.get(user_id, [])
                self._subscribers[user_id] = [
                    item for item in current if item[0] is not queue
                ]

    def _replay(self, user_id: str, last_event_id: str | None) -> list[SummaryJobEvent]:
        if not last_event_id:
            return []
        history = self._history.get(user_id, [])
        if last_event_id in {"0", "-"}:
            return list(history)
        emitted: list[SummaryJobEvent] = []
        seen = False
        for event in history:
            if seen:
                emitted.append(event)
            elif event.event_id == last_event_id:
                seen = True
        return emitted

    def subscriber_count(self, user_id: str) -> int:
        with self._lock:
            return len(self._subscribers.get(user_id, []))


class RedisEventBroker:
    """Cross-process broker: workers XADD, API XREAD BLOCK per user stream."""

    def __init__(self, url: str) -> None:
        self._url = url

    def _sync_client(self):
        import redis

        return redis.Redis.from_url(self._url, decode_responses=True)

    def publish(self, user_id: str, event: SummaryJobEvent) -> SummaryJobEvent:
        client = self._sync_client()
        try:
            payload = json.dumps(event.model_dump(mode="json"), default=str)
            event_id = client.xadd(
                stream_key(user_id),
                {"payload": payload},
                maxlen=_HISTORY_LIMIT,
                approximate=True,
            )
            client.expire(stream_key(user_id), _STREAM_TTL_SECONDS)
            event.event_id = str(event_id)
            return event
        finally:
            client.close()

    async def subscribe(
        self, user_id: str, last_event_id: str | None = None
    ) -> AsyncIterator[SummaryJobEvent]:
        import redis.asyncio as redis_async

        client = redis_async.from_url(self._url, decode_responses=True)
        last_id = last_event_id or "$"
        key = stream_key(user_id)
        try:
            while True:
                try:
                    rows = await client.xread(
                        {key: last_id}, block=_DEFAULT_BLOCK_MS, count=20
                    )
                except Exception as exc:
                    logger.warning("Redis XREAD failed for user %s: %s", user_id, exc)
                    await asyncio.sleep(1)
                    last_id = last_event_id or "$"
                    continue
                if not rows:
                    continue
                for _name, messages in rows:
                    for message_id, fields in messages:
                        last_id = str(message_id)
                        parsed = self._parse(str(message_id), fields)
                        if parsed is not None:
                            yield parsed
        finally:
            await client.aclose()

    def subscriber_count(self, user_id: str) -> int:
        return 0

    @staticmethod
    def _parse(message_id: str, fields: dict) -> SummaryJobEvent | None:
        raw = fields.get("payload")
        if not raw:
            return None
        try:
            payload = json.loads(raw)
            payload["event_id"] = message_id
            return SummaryJobEvent.model_validate(payload)
        except Exception:
            logger.warning("Ignoring malformed summary event %s", message_id)
            return None


_broker: EventBroker | None = None
_broker_lock = threading.Lock()


def create_event_broker() -> EventBroker:
    url = events_redis_url()
    if url:
        logger.info("Using Redis event broker at %s", url.split("@")[-1])
        return RedisEventBroker(url)
    logger.info("Using in-memory event broker")
    return InMemoryEventBroker()


def get_event_broker() -> EventBroker:
    global _broker
    if _broker is None:
        with _broker_lock:
            if _broker is None:
                _broker = create_event_broker()
    return _broker


def reset_event_broker(broker: EventBroker | None = None) -> EventBroker:
    global _broker
    with _broker_lock:
        _broker = broker if broker is not None else InMemoryEventBroker()
        return _broker
