"""Event consumer registry — sync (in-process) and async (SAQ-dispatched)."""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.base.models import BaseDBModel
from app.platform.base.registry import BaseRegistry
from app.platform.events.enums import EventType
from app.platform.events.models import Event

logger = logging.getLogger(__name__)

EventConsumer = Callable[..., Awaitable[None]]
EventFilter = Callable[[Event], bool]


def consumer_key(func: Callable[..., Any]) -> str:
    """Stable identifier used to look up a consumer from a SAQ task."""
    return f"{func.__module__}:{func.__qualname__}"


@dataclass
class ConsumerRegistration:
    consumer: EventConsumer
    model_filters: list[type[BaseDBModel]] | None = None
    filter: EventFilter | None = None
    is_async: bool = False

    def matches(self, event: Event) -> bool:
        if self.model_filters is not None:
            if not any(event.object_type == m.__tablename__ for m in self.model_filters):
                return False
        if self.filter is not None:
            try:
                if not self.filter(event):
                    return False
            except Exception:
                logger.exception("Filter for consumer '%s' raised; treating as no match", self.consumer.__name__)
                return False
        return True


class EventConsumerRegistry(BaseRegistry[EventType, list[ConsumerRegistration]]):
    """Singleton registry of event consumers grouped by event type."""

    def register_consumer(
        self,
        event_type: EventType,
        consumer: EventConsumer,
        model_filters: list[type[BaseDBModel]] | None = None,
        filter: EventFilter | None = None,
        is_async: bool = False,
    ) -> None:
        if event_type not in self._registry:
            self._registry[event_type] = []
        self._registry[event_type].append(
            ConsumerRegistration(
                consumer=consumer,
                model_filters=model_filters,
                filter=filter,
                is_async=is_async,
            )
        )

    def get_registrations(self, event: Event) -> list[ConsumerRegistration]:
        return [r for r in self._registry.get(event.event_type, []) if r.matches(event)]

    def lookup_by_key(self, key: str) -> ConsumerRegistration | None:
        for regs in self._registry.values():
            for r in regs:
                if consumer_key(r.consumer) == key:
                    return r
        return None


_registry = EventConsumerRegistry()


def _normalize_models(
    model: type[BaseDBModel] | list[type[BaseDBModel]] | None,
) -> list[type[BaseDBModel]] | None:
    if model is None:
        return None
    return [model] if not isinstance(model, list) else model


def event_consumer(
    *event_types: EventType,
    model: type[BaseDBModel] | list[type[BaseDBModel]] | None = None,
    filter: EventFilter | None = None,
) -> Callable[[EventConsumer], EventConsumer]:
    """Register a synchronous, in-process event consumer.

    Runs in the same transaction as the emitter — use only for fast,
    latency-sensitive work (e.g. websocket broadcasts).
    """

    def decorator(func: EventConsumer) -> EventConsumer:
        model_filters = _normalize_models(model)
        for et in event_types:
            _registry.register_consumer(et, func, model_filters, filter, is_async=False)
        return func

    return decorator


def async_event_consumer(
    *event_types: EventType,
    model: type[BaseDBModel] | list[type[BaseDBModel]] | None = None,
    filter: EventFilter | None = None,
) -> Callable[[EventConsumer], EventConsumer]:
    """Register an async event consumer that runs in a SAQ task.

    On emit, the framework enqueues a `RUN_EVENT_CONSUMER` task that loads the
    Event by id and invokes the consumer in a fresh transaction. Use for slow
    work (external webhooks, analytics, notifications).
    """

    def decorator(func: EventConsumer) -> EventConsumer:
        model_filters = _normalize_models(model)
        for et in event_types:
            _registry.register_consumer(et, func, model_filters, filter, is_async=True)
        return func

    return decorator


async def _invoke_consumer(
    consumer: EventConsumer,
    session: AsyncSession,
    event: Event,
    obj: BaseDBModel,
    dependencies: dict[str, Any],
) -> None:
    sig = inspect.signature(consumer)
    params = sig.parameters
    candidate = {"session": session, "event": event, "obj": obj, **dependencies}
    missing = [name for name, p in params.items() if p.default is inspect.Parameter.empty and name not in candidate]
    if missing:
        logger.warning(
            "Skipping consumer '%s' for event %s — missing dependencies: %s",
            consumer.__name__,
            event.id,
            missing,
        )
        return
    kwargs = {n: v for n, v in candidate.items() if n in params}
    await consumer(**kwargs)


async def trigger_consumers(
    session: AsyncSession,
    event: Event,
    obj: BaseDBModel,
    dispatch_async: Callable[[str, int], Awaitable[None]] | None = None,
    **dependencies: Any,
) -> None:
    """Run sync consumers in-process; hand async consumers to `dispatch_async`."""
    registrations = _registry.get_registrations(event)
    if not registrations:
        logger.debug("No consumers for %s on %s", event.event_type.value, event.object_type)
        return

    for reg in registrations:
        try:
            if reg.is_async:
                if dispatch_async is None:
                    logger.warning(
                        "Async consumer '%s' skipped — no dispatcher provided for event %s",
                        reg.consumer.__name__,
                        event.id,
                    )
                    continue
                await dispatch_async(consumer_key(reg.consumer), event.id)
            else:
                await _invoke_consumer(reg.consumer, session, event, obj, dependencies)
        except Exception:
            logger.exception("Consumer '%s' failed for event %s", reg.consumer.__name__, event.id)


def get_registered_consumers() -> dict[EventType, list[str]]:
    """Inspection helper — returns {event_type: [consumer_name, ...]}."""
    return {et: [r.consumer.__name__ for r in regs] for et, regs in _registry.get_all_types().items()}


def get_registry_singleton() -> EventConsumerRegistry:
    return _registry
