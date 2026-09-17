from enum import StrEnum, auto


class MessageDirection(StrEnum):
    IN = auto()
    OUT = auto()


class MessageState(StrEnum):
    RECEIVED = auto()
    QUEUED = auto()
    SENT = auto()
    FAILED = auto()


class CommsTaskName(StrEnum):
    """Task names owned by the comms module (D6 — the platform's framework `TaskName` is
    framework-only; service task names live with their service; the registry and
    `dispatch_task` accept any str name).

    Only the outbound tasks the platform implements live here. The INBOUND pipeline
    (`process_inbound_email`, app-specific inbound handlers) is per-app — it routes on
    `User.inbox_local_part` and enqueues domain tasks — so the app owns those
    names on its own enum.
    """

    SEND_EMAIL = auto()
