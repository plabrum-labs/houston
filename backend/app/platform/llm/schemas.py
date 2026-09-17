"""msgspec schemas for LLM threads, messages, and tool definitions."""

from datetime import datetime

from msgspec import Struct

from app.platform.base.schemas import BaseSchema
from app.platform.utils.sqids import Sqid


class ToolCallRecord(BaseSchema):
    id: str
    name: str
    input: dict
    is_error: bool = False


class MessageSchema(BaseSchema):
    id: Sqid
    thread_id: Sqid
    role: str
    content: str
    created_at: datetime
    tool_calls: list[ToolCallRecord] = []


class CreateThreadBody(BaseSchema):
    content: str
    timezone: str | None = None
    context: dict | None = None
    threadable_type: str | None = None
    threadable_id: Sqid | None = None


class ThreadCreatedSchema(BaseSchema):
    id: Sqid
    messages: list[MessageSchema]
    created_at: datetime


class SendMessageBody(BaseSchema):
    content: str
    timezone: str | None = None
    context: dict | None = None


class SendMessageResponse(BaseSchema):
    message: MessageSchema


class MessagePageSchema(BaseSchema):
    messages: list[MessageSchema]
    has_more: bool
    next_cursor: Sqid | None


class ThreadSummarySchema(BaseSchema):
    id: Sqid
    title: str | None
    last_message_at: datetime | None


class ThreadListPage(BaseSchema):
    threads: list[ThreadSummarySchema]


# --- Tool definition schemas (sent to Anthropic) ---


class PropertySchema(Struct, omit_defaults=True):
    type: str
    description: str | None = None
    enum: list[str] | None = None
    items: "PropertySchema | None" = None


class InputSchema(Struct):
    type: str = "object"
    properties: dict[str, PropertySchema] = {}
    required: list[str] = []


class ToolDefinition(Struct):
    name: str
    description: str
    input_schema: InputSchema


# --- SSE event schemas ---


class TokenEvent(Struct):
    event: str = "token"
    delta: str = ""


class ToolCallEvent(Struct):
    id: str
    name: str
    input: dict
    event: str = "tool_call"


class ToolResultEvent(Struct):
    tool_use_id: str
    is_error: bool
    event: str = "tool_result"


class SseMessageSchema(Struct):
    id: str
    thread_id: str
    role: str
    content: str
    created_at: str  # ISO-8601 string


class MessageCompleteEvent(Struct):
    thread_id: str
    message: SseMessageSchema
    invalidate_queries: list[str]
    event: str = "message_complete"


class ErrorEvent(Struct):
    message: str
    code: str = "error"
    event: str = "error"


SseEvent = TokenEvent | ToolCallEvent | ToolResultEvent | MessageCompleteEvent | ErrorEvent
