"""Append-only event log + async-consumer failure tracking."""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.base.models import BaseDBModel
from app.platform.events.enums import EventType
from app.platform.utils.textenum import TextEnum


class Event(BaseDBModel):
    """Append-only event log for object lifecycle tracking.

    Records structured events (create, update, delete, state change) with
    associated data. Events are processed by registered consumers for
    downstream actions (thread messages, websocket broadcasts, webhooks).
    """

    __tablename__ = "events"

    actor_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True, index=True)
    organization_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True, index=True)

    object_type: Mapped[str] = mapped_column(String(50), nullable=False)
    object_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    event_type: Mapped[EventType] = mapped_column(TextEnum(EventType), nullable=False)

    event_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_events_object", "object_type", "object_id", "created_at"),
        Index("ix_events_org_created", "organization_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Event({self.event_type.value}: {self.object_type}#{self.object_id} by actor {self.actor_id})>"


class EventConsumerFailure(BaseDBModel):
    """Failure record for async event consumers.

    Persisted before the SAQ task re-raises so the failure survives the
    transaction rollback (CommittableTaskError-style recovery). Lets retries
    and monitoring see what went wrong.
    """

    __tablename__ = "event_consumer_failures"

    event_id: Mapped[int] = mapped_column(sa.Integer, nullable=False, index=True)
    consumer_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)
    error: Mapped[str] = mapped_column(sa.Text, nullable=False)
