"""Thread request/response and websocket schemas."""

from datetime import datetime
from typing import Any

from msgspec import Struct

from app.platform.base.schemas import BaseSchema
from app.platform.threads.enums import ThreadSocketMessageType
from app.platform.utils.sqids import Sqid


class MessageSenderSchema(BaseSchema):
    id: Sqid
    email: str
    name: str


class MessageSchema(BaseSchema):
    id: Sqid
    thread_id: Sqid
    user_id: Sqid | None
    content: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    user: MessageSenderSchema | None = None


class MessageCreateSchema(BaseSchema):
    content: dict[str, Any]


class MessageUpdateSchema(BaseSchema):
    content: dict[str, Any]


class MessageListResponse(BaseSchema):
    messages: list[MessageSchema]
    offset: int
    limit: int


class BatchUnreadRequest(BaseSchema):
    object_ids: list[Sqid]


class ThreadUnreadInfo(BaseSchema):
    thread_id: Sqid
    unread_count: int


class BatchUnreadResponse(BaseSchema):
    threads: list[ThreadUnreadInfo]
    total_unread: int


class UserPresence(BaseSchema):
    user_id: Sqid
    name: str
    is_typing: bool


# ─── WebSocket message structs ────────────────────────────────────────────────


class ClientMessage(Struct, frozen=True):
    """Single unified client message — `message_type` determines payload."""

    message_type: ThreadSocketMessageType


class ServerMessage(Struct, frozen=True):
    """Single unified server message broadcast to subscribers.

    `viewers` is always present; remaining fields depend on `message_type`.
    """

    message_type: ThreadSocketMessageType
    viewers: list[str]
    user_id: str | None = None
    message_id: str | None = None
    thread_id: str | None = None
