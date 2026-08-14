from enum import StrEnum, auto


class TaskName(StrEnum):
    """Framework task names owned by app.platform.

    Apps define their own task-name enum for domain tasks (send email, imports,
    etc.); the registry and `dispatch_task` accept any str-valued name, so an
    app enum interoperates with these.
    """

    HEALTH_CHECK = auto()
    RUN_EVENT_CONSUMER = auto()


class TaskRoleType(StrEnum):
    USER = auto()
    SYSTEM = auto()


class TaskStatus(StrEnum):
    PENDING = auto()
    ACTIVE = auto()
    COMPLETE = auto()
    FAILED = auto()
    ABORTED = auto()
