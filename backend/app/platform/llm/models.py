"""LLM thread + message persistence models.

LLM threads are distinct from the WebSocket-backed `Thread` model in
the platform's `threads/` module. They store the full LLM message history (including tool-use
and tool-result blocks) so a conversation can be resumed.

Threads are polymorphically linkable to a domain object via
`(threadable_type, threadable_id)` — e.g. an order or a support ticket.
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.base.models import BaseDBModel
from app.platform.llm.enums import MessageRole
from app.platform.utils.textenum import TextEnum


class LLMThread(BaseDBModel):
    __tablename__ = "llm_threads"

    user_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True, index=True)

    threadable_type: Mapped[str | None] = mapped_column(sa.Text, nullable=True, index=True)
    threadable_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True, index=True)

    model: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    messages: Mapped[list[LLMMessage]] = relationship(
        "LLMMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="LLMMessage.id",
    )


class LLMMessage(BaseDBModel):
    __tablename__ = "llm_messages"

    thread_id: Mapped[int] = mapped_column(
        sa.ForeignKey("llm_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(TextEnum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)

    thread: Mapped[LLMThread] = relationship("LLMThread", back_populates="messages", lazy="raise")
    tool_calls: Mapped[list[LLMToolCall]] = relationship(
        "LLMToolCall",
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="LLMToolCall.id",
        lazy="noload",
    )


class LLMToolCall(BaseDBModel):
    __tablename__ = "llm_tool_calls"

    message_id: Mapped[int] = mapped_column(
        sa.ForeignKey("llm_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_use_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
    is_error: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))

    message: Mapped[LLMMessage] = relationship("LLMMessage", back_populates="tool_calls", lazy="raise")
