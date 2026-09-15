from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock

import pytest

from core.brevio_api.events.broker import (
    InMemoryEventBroker,
    RedisEventBroker,
    is_redis_url,
    reset_event_broker,
    stream_key,
)
from core.brevio_api.events.models import SummaryEventType, SummaryJobEvent
from core.brevio_api.events.publisher import publish_summary_job_event
from core.brevio_api.events.sse import format_sse_comment, format_sse_event
from core.shared.enums.job_status import JobStatus


def _event(job_id: str = "job-1", name: str = "Doc.pdf") -> SummaryJobEvent:
    return SummaryJobEvent.completed(
        job_id=job_id, document_id="doc-1", document_name=name
    )


def test_is_redis_url() -> None:
    assert is_redis_url("redis://localhost:6379/0") is True
    assert is_redis_url("rediss://secure:6379/0") is True
    assert is_redis_url("memory://") is False
    assert is_redis_url(None) is False


def test_sse_format_includes_id_event_and_json_data() -> None:
    event = _event()
    event.event_id = "42"
    frame = format_sse_event(event)
    assert frame.startswith("id: 42\n")
    assert "event: summary.completed\n" in frame
    assert frame.endswith("\n\n")
    data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload["type"] == "summary.completed"
    assert payload["job_id"] == "job-1"
    assert payload["status"] == JobStatus.COMPLETED.value
    assert format_sse_comment("keepalive") == ": keepalive\n\n"


def test_publish_completed_and_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    broker = InMemoryEventBroker()
    reset_event_broker(broker)
    completed = publish_summary_job_event(
        user_id="user-a",
        job_id="job-1",
        document_id="doc-1",
        status=JobStatus.COMPLETED.value,
        document_name="Doc.pdf",
    )
    failed = publish_summary_job_event(
        user_id="user-a",
        job_id="job-2",
        document_id="doc-2",
        status=JobStatus.FAILED.value,
        document_name="Other.pdf",
        error_code="MAP",
        error_message="MAP failed",
    )
    assert completed is not None
    assert completed.type is SummaryEventType.COMPLETED
    assert failed is not None
    assert failed.type is SummaryEventType.FAILED
    assert failed.error is not None
    assert failed.error.code == "MAP"
    assert (
        publish_summary_job_event(
            user_id="user-a",
            job_id="job-3",
            document_id="doc-3",
            status=JobStatus.PROCESSING.value,
        )
        is None
    )


def test_publisher_swallows_broker_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    broken = MagicMock()
    broken.publish.side_effect = RuntimeError("redis down")
    reset_event_broker(broken)
    assert (
        publish_summary_job_event(
            user_id="user-a",
            job_id="job-1",
            document_id="doc-1",
            status=JobStatus.COMPLETED.value,
        )
        is None
    )


@pytest.mark.asyncio
async def test_in_memory_user_isolation_and_replay() -> None:
    broker = InMemoryEventBroker()
    reset_event_broker(broker)
    first = broker.publish("user-a", _event("job-a"))
    broker.publish("user-b", _event("job-b"))
    second = broker.publish("user-a", _event("job-a2"))

    received: list[str] = []

    async def consume() -> None:
        async for event in broker.subscribe("user-a", last_event_id=first.event_id):
            received.append(event.job_id)
            if len(received) >= 1:
                break

    await asyncio.wait_for(consume(), timeout=1)
    assert received == ["job-a2"]
    assert second.job_id == "job-a2"


@pytest.mark.asyncio
async def test_in_memory_live_delivery_and_disconnect() -> None:
    broker = InMemoryEventBroker()
    agen = broker.subscribe("user-a")
    waiter = asyncio.create_task(anext(agen))
    for _ in range(50):
        if broker.subscriber_count("user-a") == 1:
            break
        await asyncio.sleep(0.01)
    assert broker.subscriber_count("user-a") == 1
    broker.publish("user-a", _event("live-job"))
    event = await asyncio.wait_for(waiter, timeout=1)
    assert event.job_id == "live-job"
    await agen.aclose()
    assert broker.subscriber_count("user-a") == 0


def test_redis_broker_publish_uses_user_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = MagicMock()
    fake.xadd.return_value = "1710000-0"
    broker = RedisEventBroker("redis://localhost:6379/0")
    monkeypatch.setattr(broker, "_sync_client", lambda: fake)
    event = broker.publish("user-z", _event("job-z"))
    fake.xadd.assert_called_once()
    args, kwargs = fake.xadd.call_args
    assert args[0] == stream_key("user-z")
    assert kwargs["maxlen"] == 200
    payload = json.loads(args[1]["payload"])
    assert payload["job_id"] == "job-z"
    assert event.event_id == "1710000-0"
    fake.expire.assert_called_once()
    fake.close.assert_called_once()


def test_redis_parse_malformed_returns_none() -> None:
    assert RedisEventBroker._parse("1-0", {"payload": "{"}) is None
    parsed = RedisEventBroker._parse(
        "9-0",
        {
            "payload": json.dumps(
                SummaryJobEvent.failed(
                    job_id="j",
                    document_id="d",
                    error_code="X",
                    error_message="nope",
                ).model_dump(mode="json")
            )
        },
    )
    assert parsed is not None
    assert parsed.event_id == "9-0"
    assert parsed.type is SummaryEventType.FAILED
