from enum import StrEnum, auto


class Role(StrEnum):
    """This app's human roles — the concrete enum behind houston's generic `Role`.

    No SYSTEM member: houston handles system-initiated state-machine edges via
    `system_only`, so an app's Role carries only its real human roles.
    """

    STAFF = auto()
    CLIENT = auto()
