"""Event emission service — records an Event row and triggers consumers."""

from __future__ import annotations

import logging
from dataclasses import asdict, is_dataclass
from typing import Any

from litestar import Request
from litestar.channels import ChannelsPlugin
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.platform.base.models import BaseDBModel
from app.platform.events.enums import EventType
from app.platform.events.models import Event
from app.platform.events.registry import trigger_consumers
from app.platform.events.schemas import (
    CreatedEventData,
    CustomEventData,
    DeletedEventData,
    StateChangedEventData,
    UpdatedEventData,
)
from app.platform.queue.enums import TaskName
from app.platform.queue.transactions import dispatch_task

logger = logging.getLogger(__name__)

EventDataTypes = (
    CreatedEventData
    | UpdatedEventData
    | DeletedEventData
    | StateChangedEventData
    | CustomEventData
    | dict[str, Any]
    | None
)


async def emit_event(
    session: AsyncSession,
    event_type: EventType,
    obj: BaseDBModel,
    user_id: int | None,
    org_id: int | None,
    event_data: EventDataTypes = None,
    *,
    request: Request | None = None,
    channels: ChannelsPlugin | None = None,
) -> Event:
    """Persist an Event row and trigger registered consumers.

    `channels` is only injected into consumers whose signature requests it,
    so consumers without a websocket dependency work fine without it.
    Async consumers are enqueued as SAQ tasks (requires `request` for the
    queue handle, unless QUEUE_SYNC is enabled).
    """
    data_dict: dict[str, Any] | None
    if event_data is None:
        data_dict = None
    elif isinstance(event_data, dict):
        data_dict = event_data
    elif is_dataclass(event_data):
        data_dict = asdict(event_data)
    else:
        raise TypeError(f"Unsupported event_data type: {type(event_data).__name__}")

    event = Event(
        actor_id=user_id,
        organization_id=org_id,
        object_type=obj.__tablename__,
        object_id=obj.id,
        event_type=event_type,
        event_data=data_dict,
    )
    session.add(event)
    await session.flush()

    logger.info(
        "Event emitted: %s on %s#%s by actor %s",
        event_type.value,
        event.object_type,
        event.object_id,
        user_id,
    )

    dependencies: dict[str, Any] = {}
    if channels is not None:
        dependencies["channels"] = channels
    if request is not None:
        dependencies["request"] = request

    dispatcher = _make_async_dispatcher(session, request)
    await trigger_consumers(session, event, obj, dispatch_async=dispatcher, **dependencies)
    return event


def _make_async_dispatcher(session: AsyncSession, request: Request | None):
    """Return a coroutine that enqueues the RUN_EVENT_CONSUMER task."""

    async def dispatch(consumer_key: str, event_id: int) -> None:
        if request is None and not config.QUEUE_SYNC:
            logger.warning(
                "Async consumer '%s' for event %s skipped — no request available to enqueue task",
                consumer_key,
                event_id,
            )
            return
        await dispatch_task(
            transaction=session,
            request=request,  # type: ignore[arg-type]
            task_name=TaskName.RUN_EVENT_CONSUMER,
            consumer_key=consumer_key,
            event_id=event_id,
        )

    return dispatch
