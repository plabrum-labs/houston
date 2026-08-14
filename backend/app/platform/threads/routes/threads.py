"""Thread REST routes — message create/list and batch unread counts."""

import logging
from collections.abc import Sequence
from typing import Annotated, Any

from litestar import Router, get, post
from litestar.channels import ChannelsPlugin
from litestar.params import Dependency, Parameter
from litestar.types import Guard
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.platform.state_machine.roles import Actor
from app.platform.threads.enums import ThreadSocketMessageType
from app.platform.threads.models import Message, Thread
from app.platform.threads.schemas import (
    BatchUnreadRequest,
    BatchUnreadResponse,
    MessageCreateSchema,
    MessageListResponse,
    MessageSchema,
    ServerMessage,
    ThreadUnreadInfo,
)
from app.platform.threads.services import (
    get_batch_unread_counts,
    get_or_create_thread,
    mark_thread_as_read,
    notify_thread,
)
from app.platform.utils.sqids import Sqid, sqid_encode

logger = logging.getLogger(__name__)


@post("/{threadable_type:str}/{threadable_id:int}/messages")
async def create_message(
    threadable_type: str,
    threadable_id: int,
    data: MessageCreateSchema,
    transaction: AsyncSession,
    channels: ChannelsPlugin,
    user: Actor[Any] = Dependency(skip_validation=True),
) -> MessageSchema:
    user_id = user.id

    thread = await get_or_create_thread(
        transaction=transaction,
        threadable_type=threadable_type,
        threadable_id=threadable_id,
    )

    message = Message(thread_id=thread.id, user_id=user_id, content=data.content)
    transaction.add(message)
    await transaction.flush()

    # Sender's own messages shouldn't count as unread for them.
    await mark_thread_as_read(transaction, thread.id, user_id)

    await notify_thread(
        channels,
        thread.id,
        ServerMessage(
            message_type=ThreadSocketMessageType.MESSAGE_CREATED,
            message_id=sqid_encode(message.id),
            thread_id=sqid_encode(thread.id),
            user_id=sqid_encode(user_id),
            viewers=[],
        ),
    )

    logger.info(
        "Created message %s in thread %s (%s:%s)",
        message.id,
        thread.id,
        threadable_type,
        threadable_id,
    )

    return MessageSchema(
        id=Sqid(message.id),
        thread_id=Sqid(thread.id),
        user_id=Sqid(user_id),
        content=message.content,
        created_at=message.created_at,
        updated_at=message.updated_at,
        user=None,
    )


@get("/{threadable_type:str}/{threadable_id:int}/messages")
async def list_messages(
    threadable_type: str,
    threadable_id: int,
    transaction: AsyncSession,
    offset: Annotated[int, Parameter(ge=0)] = 0,
    limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
) -> MessageListResponse:
    stmt = (
        select(Message)
        .join(
            Thread,
            and_(
                Message.thread_id == Thread.id,
                Thread.threadable_type == threadable_type,
                Thread.threadable_id == threadable_id,
            ),
        )
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(limit)
        .options(joinedload(Message.thread))
    )

    result = await transaction.execute(stmt)
    rows = result.scalars().all()

    messages = [
        MessageSchema(
            id=Sqid(m.id),
            thread_id=Sqid(m.thread_id),
            user_id=Sqid(m.user_id) if m.user_id is not None else None,
            content=m.content,
            created_at=m.created_at,
            updated_at=m.updated_at,
            user=None,
        )
        for m in rows
    ]

    return MessageListResponse(messages=messages, offset=offset, limit=limit)


@post("/{threadable_type:str}/{threadable_id:int}/mark-read", status_code=204)
async def mark_read(
    threadable_type: str,
    threadable_id: int,
    transaction: AsyncSession,
    user: Actor[Any] = Dependency(skip_validation=True),
) -> None:
    thread = await get_or_create_thread(
        transaction=transaction,
        threadable_type=threadable_type,
        threadable_id=threadable_id,
    )
    await mark_thread_as_read(transaction, thread.id, user.id)


@post("/{threadable_type:str}/batch-unread")
async def get_batch_thread_unread(
    threadable_type: str,
    data: BatchUnreadRequest,
    transaction: AsyncSession,
    user: Actor[Any] = Dependency(skip_validation=True),
) -> BatchUnreadResponse:
    if not data.object_ids:
        return BatchUnreadResponse(threads=[], total_unread=0)

    results = await get_batch_unread_counts(
        transaction,
        threadable_type,
        [int(oid) for oid in data.object_ids],
        user.id,
    )

    thread_infos: list[ThreadUnreadInfo] = []
    total_unread = 0
    for thread_id, unread_count in results:
        thread_infos.append(ThreadUnreadInfo(thread_id=Sqid(thread_id), unread_count=unread_count))
        total_unread += unread_count

    return BatchUnreadResponse(threads=thread_infos, total_unread=total_unread)


def build_thread_router(*, path: str = "/threads", guards: Sequence[Guard] = ()) -> Router:
    """Build the threads REST router for an app.

    The platform doesn't own the app's auth guards, so the module-level router from
    the source app (which hardcoded `guards=[requires_session]`) becomes a factory
    with `guards` injected — same guard-injection pattern as `build_action_router` / the CRUD
    controller factories / `build_document_router` / `build_media_router`.
    """
    return Router(
        path=path,
        guards=list(guards),
        route_handlers=[
            create_message,
            list_messages,
            mark_read,
            get_batch_thread_unread,
        ],
        tags=["threads"],
    )
