"""Generic WebSocket lifecycle helper — accept, run, log, close."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from litestar import WebSocket
from litestar.exceptions import NotAuthorizedException

from app.platform.state_machine.roles import Actor

logger = logging.getLogger(__name__)


async def run_websocket(
    socket: WebSocket,
    *,
    label: str,
    handler: Callable[[WebSocket, Actor[Any]], Awaitable[None]],
) -> None:
    """Run a WebSocket handler with auth, accept, lifecycle logging, and guaranteed close.

    The `handler` is invoked with the accepted socket and authenticated user. Any
    exception it raises is logged but not re-raised — the socket is closed in the
    `finally` block either way.
    """
    user = socket.user
    if user is None:
        raise NotAuthorizedException("Authentication required")

    await socket.accept()
    logger.info(f"{label} connected: user={user.id}")
    try:
        await handler(socket, user)
    except Exception:
        logger.exception(f"{label} failed: user={user.id}")
    finally:
        logger.info(f"{label} disconnected: user={user.id}")
        try:
            await socket.close()
        except Exception:
            pass
