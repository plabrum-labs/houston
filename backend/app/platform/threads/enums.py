"""Thread enums."""

from enum import StrEnum, auto


class MessageActions(StrEnum):
    """Available actions for messages."""

    UPDATE = auto()
    DELETE = auto()


class MessageUpdateType(StrEnum):
    """Type of message update."""

    CREATED = auto()
    UPDATED = auto()
    DELETED = auto()


class ThreadSocketMessageType(StrEnum):
    """Types of messages exchanged over the thread WebSocket."""

    MARK_READ = auto()
    USER_JOINED = auto()
    USER_LEFT = auto()
    USER_FOCUS = auto()
    USER_BLUR = auto()
    MESSAGE_CREATED = auto()
    MESSAGE_UPDATED = auto()
    MESSAGE_DELETED = auto()
