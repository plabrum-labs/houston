from enum import StrEnum, auto


class AppState(StrEnum):
    registered = auto()
    provisioning = auto()
    live = auto()
    suspended = auto()
