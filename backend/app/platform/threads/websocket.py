"""Thread WebSocket — handles connection lifecycle and client→server messages."""

import logging
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager

import msgspec
from litestar import WebSocket
from litestar.channels import ChannelsPlugin
from litestar.exceptions import WebSocketDisconnect
from litestar.handlers import websocket_listener
from litestar.types import Guard
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.threads.enums import ThreadSocketMessageType
from app.platform.threads.schemas import ClientMessage, ServerMessage
from app.platform.threads.services import (
    ThreadViewerStore,
    get_or_create_thread,
    mark_thread_as_read,
    notify_thread,
)
from app.platform.threads.utils import get_thread_channel
from app.platform.utils.sqids import sqid_encode

logger = logging.getLogger(__name__)


@asynccontextmanager
async def thread_connection_lifespan(
    socket: WebSocket,
    channels: ChannelsPlugin,
    threadable_type: str,
    threadable_id: int,
    transaction: AsyncSession,
    viewer_store: ThreadViewerStore,
) -> AsyncGenerator[None]:
    thread = await get_or_create_thread(
        transaction=transaction,
        threadable_type=threadable_type,
        threadable_id=threadable_id,
    )

    user_id: int = socket.user
    viewer_ids = await viewer_store.add_viewer(thread.id, user_id)

    await notify_thread(
        channels,
        thread.id,
        ServerMessage(
            message_type=ThreadSocketMessageType.USER_JOINED,
            user_id=sqid_encode(user_id),
            viewers=[sqid_encode(viewer) for viewer in viewer_ids],
        ),
    )

    logger.info("WebSocket connected: user %s -> thread %s", user_id, thread.id)

    async with (
        channels.start_subscription([get_thread_channel(thread.id)]) as subscriber,
        subscriber.run_in_background(socket.send_text),
    ):
        try:
            socket.state["thread_id"] = thread.id
            socket.state["user_id"] = user_id
            yield
        except WebSocketDisconnect:
            pass
        finally:
            viewer_ids = await viewer_store.remove_viewer(thread.id, user_id)
            await notify_thread(
                channels,
                thread.id,
                ServerMessage(
                    message_type=ThreadSocketMessageType.USER_LEFT,
                    user_id=sqid_encode(user_id),
                    viewers=[sqid_encode(viewer) for viewer in viewer_ids],
                ),
            )
            logger.info("WebSocket disconnected: user %s from thread %s", user_id, thread.id)


async def thread_handler(
    data: dict,
    channels: ChannelsPlugin,
    socket: WebSocket,
    transaction: AsyncSession,
    viewer_store: ThreadViewerStore,
) -> None:
    thread_id: int = socket.state["thread_id"]
    user_id: int = socket.state["user_id"]
    message: ClientMessage = msgspec.convert(data, ClientMessage)

    match message.message_type:
        case ThreadSocketMessageType.USER_FOCUS | ThreadSocketMessageType.USER_BLUR:
            viewer_ids = await viewer_store.add_viewer(thread_id, user_id)
            await notify_thread(
                channels,
                thread_id,
                ServerMessage(
                    message_type=message.message_type,
                    user_id=sqid_encode(user_id),
                    viewers=[sqid_encode(viewer) for viewer in viewer_ids],
                ),
            )
        case ThreadSocketMessageType.MARK_READ:
            await mark_thread_as_read(transaction, thread_id, user_id)
            await transaction.commit()


def build_thread_handler(
    *,
    path: str = "/ws/threads/{threadable_type:str}/{threadable_id:int}",
    guards: Sequence[Guard] = (),
) -> websocket_listener:
    """Build the thread WebSocket listener for an app.

    The platform doesn't own the app's auth guards, so the module-level
    `@websocket_listener(..., guards=[requires_session])` from the source app
    becomes a factory with `guards` injected — same pattern as the route factories.
    """
    return websocket_listener(
        path,
        connection_lifespan=thread_connection_lifespan,
        guards=list(guards),
    )(thread_handler)
