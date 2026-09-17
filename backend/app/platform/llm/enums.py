from enum import StrEnum, auto


class MessageRole(StrEnum):
    USER = auto()
    ASSISTANT = auto()
    ASSISTANT_TOOL = auto()
    TOOL_RESULT = auto()
