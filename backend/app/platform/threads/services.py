"""Thread services — get-or-create, unread counts, presence store, broadcast."""

import logging
from datetime import UTC, datetime
from typing import cast

from litestar.channels import ChannelsPlugin
from litestar.stores.base import Store
from litestar.stores.memory import MemoryStore
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.threads.models import Message, Thread, ThreadReadStatus
from app.platform.threads.schemas import ServerMessage
from app.platform.threads.utils import encode_server_message_str, get_thread_channel

logger = logging.getLogger(__name__)


# ─── Viewer presence (in-memory; swap for Redis without API change) ──────────


class ThreadViewerStore:
    """Tracks which users are currently connected to each thread.

    Wraps a Litestar `Store` so the backend can be swapped (memory → Redis)
    without changing call sites. Serialization will become relevant the moment
    a non-memory backend is used.
    """

    def __init__(self, store: Store):
        self.store: MemoryStore = cast(MemoryStore, store)

    def get_key(self, thread_id: int) -> str:
        return f"thread_id_{thread_id}"

    async def get_viewers(self, thread_id: int) -> set[int]:
        data = await self.store.get(self.get_key(thread_id))
        return cast(set[int], data) if data else set()

    async def add_viewer(self, thread_id: int, user_id: int) -> set[int]:
        viewers = await self.get_viewers(thread_id)
        viewers.add(user_id)
        await self.store.set(self.get_key(thread_id), cast(bytes, viewers))
        return viewers

    async def remove_viewer(self, thread_id: int, user_id: int) -> set[int]:
        viewers = await self.get_viewers(thread_id)
        viewers.discard(user_id)
        await self.store.set(self.get_key(thread_id), cast(bytes, viewers))
        return viewers


async def get_or_create_thread(
    transaction: AsyncSession,
    threadable_type: str,
    threadable_id: int,
) -> Thread:
    stmt = select(Thread).where(
        Thread.threadable_type == threadable_type,
        Thread.threadable_id == threadable_id,
    )
    result = await transaction.execute(stmt)
    thread = result.scalar_one_or_none()
    if thread:
        return thread

    thread = Thread(
        threadable_type=threadable_type,
        threadable_id=threadable_id,
    )
    transaction.add(thread)
    await transaction.flush()

    logger.info(
        "Created new thread for %s:%s (thread_id=%s)",
        threadable_type,
        threadable_id,
        thread.id,
    )
    return thread


async def get_unread_count(
    session: AsyncSession,
    thread_id: int,
    user_id: int,
) -> int:
    last_read_stmt = select(func.max(ThreadReadStatus.read_at)).where(
        ThreadReadStatus.thread_id == thread_id,
        ThreadReadStatus.user_id == user_id,
    )
    result = await session.execute(last_read_stmt)
    last_read_at = result.scalar_one_or_none()

    query = select(func.count()).select_from(Message).where(Message.thread_id == thread_id)
    if last_read_at:
        query = query.where(Message.created_at > last_read_at)

    result = await session.execute(query)
    return result.scalar_one()


async def get_batch_unread_counts(
    session: AsyncSession,
    threadable_type: str,
    threadable_ids: list[int],
    user_id: int,
) -> list[tuple[int, int]]:
    """Return `(thread_id, unread_count)` for the requested objects in one query."""
    max_read_subq = (
        select(
            ThreadReadStatus.thread_id,
            func.max(ThreadReadStatus.read_at).label("last_read_at"),
        )
        .where(ThreadReadStatus.user_id == user_id)
        .group_by(ThreadReadStatus.thread_id)
        .subquery()
    )

    stmt = (
        select(
            Thread.id.label("thread_id"),
            max_read_subq.c.last_read_at,
            func.count(Message.id).label("unread_count"),
        )
        .select_from(Thread)
        .outerjoin(max_read_subq, max_read_subq.c.thread_id == Thread.id)
        .outerjoin(
            Message,
            (Message.thread_id == Thread.id)
            & ((max_read_subq.c.last_read_at.is_(None)) | (Message.created_at > max_read_subq.c.last_read_at)),
        )
        .where(
            Thread.threadable_type == threadable_type,
            Thread.threadable_id.in_(threadable_ids),
        )
        .group_by(Thread.id, max_read_subq.c.last_read_at)
    )

    result = await session.execute(stmt)
    return [(row.thread_id, row.unread_count) for row in result.all()]


async def mark_thread_as_read(
    session: AsyncSession,
    thread_id: int,
    user_id: int,
) -> None:
    """Append a read event for a thread/user pair."""
    read_status = ThreadReadStatus(
        thread_id=thread_id,
        user_id=user_id,
        read_at=datetime.now(tz=UTC),
    )
    session.add(read_status)
    await session.flush()
    logger.info("Marked thread %s as read for user %s", thread_id, user_id)


async def notify_thread(
    channels: ChannelsPlugin,
    thread_id: int,
    message: ServerMessage,
) -> None:
    try:
        channels.publish(
            encode_server_message_str(message),
            [get_thread_channel(thread_id)],
        )
        logger.debug("Notified thread %s: %s", thread_id, message)
    except Exception as e:
        logger.warning("Failed to notify thread %s: %s", thread_id, e)
