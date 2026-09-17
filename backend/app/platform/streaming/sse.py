from collections.abc import AsyncGenerator

import msgspec
from litestar.response import Stream

from app.platform.llm.schemas import SseEvent


def format_frame(ev: SseEvent) -> bytes:
    encoded = msgspec.json.encode(ev).decode()
    return f"event: {ev.event}\r\ndata: {encoded}\r\n\r\n".encode()


def stream_response(gen: AsyncGenerator[bytes]) -> Stream:
    return Stream(
        content=gen,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
