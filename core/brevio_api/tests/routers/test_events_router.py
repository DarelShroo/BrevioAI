from __future__ import annotations

import asyncio
import json
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from core.brevio_api.__main__ import app
from core.brevio_api.events.broker import InMemoryEventBroker, reset_event_broker
from core.brevio_api.events.models import SummaryJobEvent
from core.brevio_api.events.publisher import publish_summary_job_event
from core.brevio_api.events.sse import SSE_CONTENT_TYPE
from core.brevio_api.routers.events_router import iter_user_events
from core.brevio_api.services.token_service import TokenService
from core.shared.enums.job_status import JobStatus


class _FakeRequest:
    def __init__(self) -> None:
        self.disconnected = False

    async def is_disconnected(self) -> bool:
        return self.disconnected


@pytest.fixture
def broker() -> Iterator[InMemoryEventBroker]:
    instance = InMemoryEventBroker()
    reset_event_broker(instance)
    yield instance
    reset_event_broker()


@pytest.fixture
def user_a() -> str:
    return "aaaaaaaaaaaaaaaaaaaaaaaa"


@pytest.fixture
def user_b() -> str:
    return "bbbbbbbbbbbbbbbbbbbbbbbb"


def _token(user_id: str) -> str:
    return TokenService().create_access_token({"id": user_id})


@pytest.fixture(autouse=True)
def _clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


async def _collect_until(
    user_id: str,
    last_event_id: str | None,
    predicate,
    *,
    broker: InMemoryEventBroker,
    limit: int = 8,
) -> str:
    request = _FakeRequest()
    body = ""
    agen = iter_user_events(
        request,  # type: ignore[arg-type]
        user_id,
        last_event_id,
        broker=broker,
        heartbeat=0.05,
    )
    try:
        async for chunk in agen:
            body += chunk
            if predicate(body) or body.count("\n\n") >= limit:
                request.disconnected = True
                break
    finally:
        await agen.aclose()
    return body


def test_sse_requires_authentication(broker: InMemoryEventBroker) -> None:
    client = TestClient(app)
    response = client.get("/events/stream")
    assert response.status_code == 401


def test_sse_rejects_invalid_token(broker: InMemoryEventBroker) -> None:
    client = TestClient(app)
    response = client.get(
        "/events/stream", headers={"Authorization": "Bearer not-a-token"}
    )
    assert response.status_code == 401


def test_sse_does_not_trust_query_user_id(
    broker: InMemoryEventBroker, user_a: str
) -> None:
    client = TestClient(app)
    response = client.get("/events/stream", params={"user_id": "attacker"})
    assert response.status_code == 401
    token = _token(user_a)
    payload_user = TokenService().validate_access_token(token)["id"]
    assert payload_user == user_a
    assert payload_user != "attacker"


@pytest.mark.asyncio
async def test_sse_delivers_completed_event_to_owner(
    broker: InMemoryEventBroker, user_a: str
) -> None:
    publish_summary_job_event(
        user_id=user_a,
        job_id="job-1",
        document_id="doc-1",
        status=JobStatus.COMPLETED.value,
        document_name="Doc.pdf",
    )
    body = await _collect_until(
        user_a, "0", lambda text: "summary.completed" in text, broker=broker
    )
    assert "event: summary.completed" in body
    data_line = next(line for line in body.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload["job_id"] == "job-1"
    assert payload["document_id"] == "doc-1"
    assert payload["status"] == JobStatus.COMPLETED.value
    assert payload["document_name"] == "Doc.pdf"


@pytest.mark.asyncio
async def test_sse_isolates_users(
    broker: InMemoryEventBroker, user_a: str, user_b: str
) -> None:
    publish_summary_job_event(
        user_id=user_a,
        job_id="secret-job",
        document_id="doc-a",
        status=JobStatus.COMPLETED.value,
        document_name="Secret.pdf",
    )
    body = await _collect_until(
        user_b, "0", lambda text: "summary.completed" in text, broker=broker
    )
    assert "secret-job" not in body
    assert "Secret.pdf" not in body
    assert "keepalive" in body or "connected" in body


@pytest.mark.asyncio
async def test_sse_failed_event_payload(
    broker: InMemoryEventBroker, user_a: str
) -> None:
    publish_summary_job_event(
        user_id=user_a,
        job_id="job-fail",
        document_id="doc-fail",
        status=JobStatus.FAILED.value,
        document_name="Bad.pdf",
        error_code="MAP_FAILED",
        error_message="MAP failed",
    )
    body = await _collect_until(
        user_a, "0", lambda text: "summary.failed" in text, broker=broker
    )
    data_line = next(line for line in body.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload["type"] == "summary.failed"
    assert payload["error"]["code"] == "MAP_FAILED"
    assert payload["error"]["message"] == "MAP failed"


@pytest.mark.asyncio
async def test_sse_replays_missed_events_after_last_event_id(
    broker: InMemoryEventBroker, user_a: str
) -> None:
    first = broker.publish(
        user_a,
        SummaryJobEvent.completed(job_id="job-old", document_id="d1"),
    )
    broker.publish(
        user_a,
        SummaryJobEvent.completed(job_id="job-new", document_id="d2"),
    )
    body = await _collect_until(
        user_a, first.event_id, lambda text: "job-new" in text, broker=broker
    )
    assert "job-new" in body
    assert "job-old" not in body


@pytest.mark.asyncio
async def test_sse_heartbeat_comment(broker: InMemoryEventBroker, user_a: str) -> None:
    body = await _collect_until(
        user_a, None, lambda text: "keepalive" in text, broker=broker, limit=4
    )
    assert ":" in body
    assert "connected" in body or "keepalive" in body


@pytest.mark.asyncio
async def test_sse_multiple_jobs_replay(
    broker: InMemoryEventBroker, user_a: str
) -> None:
    publish_summary_job_event(
        user_id=user_a,
        job_id="job-1",
        document_id="d1",
        status=JobStatus.COMPLETED.value,
    )
    publish_summary_job_event(
        user_id=user_a,
        job_id="job-2",
        document_id="d2",
        status=JobStatus.FAILED.value,
        error_code="X",
        error_message="no",
    )
    body = await _collect_until(
        user_a,
        "0",
        lambda text: "job-1" in text and "job-2" in text,
        broker=broker,
    )
    assert "summary.completed" in body
    assert "summary.failed" in body


@pytest.mark.asyncio
async def test_sse_disconnect_releases_subscribers(
    broker: InMemoryEventBroker, user_a: str
) -> None:
    request = _FakeRequest()
    agen = iter_user_events(
        request, user_a, broker=broker, heartbeat=0.05
    )  # type: ignore[arg-type]
    await agen.__anext__()
    for _ in range(50):
        if broker.subscriber_count(user_a) == 1:
            break
        await asyncio.sleep(0.01)
    assert broker.subscriber_count(user_a) == 1
    await agen.aclose()
    assert broker.subscriber_count(user_a) == 0


@pytest.mark.asyncio
async def test_sse_live_event_after_subscribe(
    broker: InMemoryEventBroker, user_a: str
) -> None:
    request = _FakeRequest()
    agen = iter_user_events(
        request, user_a, broker=broker, heartbeat=1
    )  # type: ignore[arg-type]
    first = await agen.__anext__()
    assert "connected" in first
    for _ in range(50):
        if broker.subscriber_count(user_a) == 1:
            break
        await asyncio.sleep(0.01)
    publish_summary_job_event(
        user_id=user_a,
        job_id="live-job",
        document_id="live-doc",
        status=JobStatus.COMPLETED.value,
        document_name="Live.pdf",
    )
    body = first
    for _ in range(6):
        body += await agen.__anext__()
        if "live-job" in body:
            break
    await agen.aclose()
    assert "live-job" in body
    assert "summary.completed" in body


def test_sse_headers_constant() -> None:
    assert SSE_CONTENT_TYPE == "text/event-stream"


def test_route_registered() -> None:
    from core.brevio_api.routers.events_router import events_router

    paths = [
        (route.path, getattr(route, "methods", None)) for route in events_router.routes
    ]
    assert ("/events/stream", {"GET"}) in paths
