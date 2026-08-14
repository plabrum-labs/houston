from enum import StrEnum, auto


class MediaStates(StrEnum):
    """Media processing states."""

    PENDING = auto()
    PROCESSING = auto()
    READY = auto()
    FAILED = auto()


class MediaTaskName(StrEnum):
    """Task names owned by the media module.

    The source app declared `GENERATE_THUMBNAIL` on the central `TaskName` enum, but
    the platform's framework `TaskName` is framework-only (D6) — domain/service task
    names live with their service. The registry and `enqueue` accept any str
    name, so this enum interoperates with the framework one.
    """

    GENERATE_THUMBNAIL = auto()
