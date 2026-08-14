from enum import StrEnum, auto


class DocumentStates(StrEnum):
    """Document processing states."""

    PENDING = auto()
    PROCESSING = auto()
    READY = auto()
    FAILED = auto()
