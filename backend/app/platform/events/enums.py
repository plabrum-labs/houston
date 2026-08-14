from enum import StrEnum, auto


class EventType(StrEnum):
    """Types of activity events that can be tracked."""

    CREATED = auto()
    UPDATED = auto()
    DELETED = auto()
    STATE_CHANGED = auto()
    CUSTOM = auto()
