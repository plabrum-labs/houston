from enum import StrEnum, auto


class ActionResultType(StrEnum):
    """Types of actions the frontend should take after action execution."""

    REDIRECT = auto()
    DOWNLOAD_FILE = auto()
    COPY_TO_CLIPBOARD = auto()


class ActionIcon(StrEnum):
    DEFAULT = auto()
    REFRESH = auto()
    DOWNLOAD = auto()
    SEND = auto()
    EDIT = auto()
    TRASH = auto()
    ADD = auto()
    CHECK = auto()
    X = auto()
    LINK = auto()
    CALENDAR = auto()
    PLAY = auto()
    CLIPBOARD = auto()
    REWIND = auto()
