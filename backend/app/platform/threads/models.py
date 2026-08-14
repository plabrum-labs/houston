"""Thread models — polymorphic threads with messages and read tracking."""

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.base.models import BaseDBModel


class Thread(BaseDBModel):
    """Polymorphic thread — any domain object can have one.

    `(threadable_type, threadable_id)` identifies the parent object. The pair is
    unique so each object has at most one thread.
    """

    __tablename__ = "threads"

    threadable_type: Mapped[str] = mapped_column(sa.Text, nullable=False, index=True)
    threadable_id: Mapped[int] = mapped_column(sa.Integer, nullable=False, index=True)

    messages: Mapped[list["Message"]] = relationship(
        "app.platform.threads.models.Message",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="app.platform.threads.models.Message.created_at",
    )
    read_statuses: Mapped[list["ThreadReadStatus"]] = relationship(
        "ThreadReadStatus",
        back_populates="thread",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "threadable_type",
            "threadable_id",
            name="uq_thread_per_object",
        ),
    )


class Message(BaseDBModel):
    """A single message inside a thread.

    `user_id` is nullable so system-generated messages (e.g. event-driven
    activity feed entries) can be authored without a user.
    Content is TipTap JSON so the frontend can render rich text.
    """

    __tablename__ = "messages"

    thread_id: Mapped[int] = mapped_column(
        sa.ForeignKey("threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
        index=True,
    )

    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    thread: Mapped["Thread"] = relationship("Thread", back_populates="messages")

    __table_args__ = (sa.Index("ix_messages_thread_created", "thread_id", "created_at"),)


class ThreadReadStatus(BaseDBModel):
    """Append-only log of thread read events used to derive unread counts."""

    __tablename__ = "thread_read_statuses"

    thread_id: Mapped[int] = mapped_column(
        sa.ForeignKey("threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        index=True,
    )

    read_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )

    thread: Mapped["Thread"] = relationship("Thread", back_populates="read_statuses")

    __table_args__ = (
        sa.Index(
            "ix_thread_read_status_lookup",
            "thread_id",
            "user_id",
            "read_at",
        ),
    )
