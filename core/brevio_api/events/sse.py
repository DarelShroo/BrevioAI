"""SSE frame helpers (text/event-stream)."""

from __future__ import annotations

import json

from core.brevio_api.events.models import SummaryJobEvent

SSE_CONTENT_TYPE = "text/event-stream"
SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def format_sse_event(event: SummaryJobEvent) -> str:
    payload = event.model_dump(mode="json")
    return (
        f"id: {event.event_id}\n"
        f"event: {event.type.value}\n"
        f"data: {json.dumps(payload, default=str)}\n"
        "\n"
    )


def format_sse_comment(comment: str = "keepalive") -> str:
    return f": {comment}\n\n"
