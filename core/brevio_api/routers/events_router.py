import asyncio
import logging
import os

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse
from starlette.requests import Request as StarletteRequest

from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.events.broker import EventBroker, get_event_broker
from core.brevio_api.events.sse import (
    SSE_CONTENT_TYPE,
    SSE_HEADERS,
    format_sse_comment,
    format_sse_event,
)

logger = logging.getLogger(__name__)


def heartbeat_seconds() -> float:
    raw = os.getenv("EVENTS_SSE_HEARTBEAT_SECONDS", "15")
    try:
        value = float(raw)
    except ValueError:
        return 15.0
    return max(1.0, value)


async def iter_user_events(
    request: StarletteRequest,
    user_id: str,
    last_event_id: str | None = None,
    broker: EventBroker | None = None,
    heartbeat: float | None = None,
):
    """Yield SSE frames for one authenticated user until the client disconnects."""
    event_broker = broker or get_event_broker()
    interval = heartbeat if heartbeat is not None else heartbeat_seconds()
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)

    async def pump() -> None:
        try:
            async for event in event_broker.subscribe(user_id, last_event_id):
                await queue.put(event)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("SSE pump failed for user %s", user_id)

    task = asyncio.create_task(pump())
    try:
        yield format_sse_comment("connected")
        while True:
            if await request.is_disconnected():
                logger.debug("SSE client disconnected user=%s", user_id)
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=interval)
                yield format_sse_event(event)
            except asyncio.TimeoutError:
                yield format_sse_comment("keepalive")
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.debug("SSE pump shutdown for user %s", user_id, exc_info=True)


class EventsRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/events", tags=["events"])
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.get(
            "/stream",
            summary="Subscribe to summary job events for the authenticated user",
            response_class=StreamingResponse,
        )
        async def stream_events(
            request: Request,
            current_user: str = Depends(get_current_user),
            last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
        ) -> StreamingResponse:
            user_id = str(current_user)
            return StreamingResponse(
                iter_user_events(request, user_id, last_event_id),
                media_type=SSE_CONTENT_TYPE,
                headers=SSE_HEADERS,
            )


events_router = EventsRouter().router
