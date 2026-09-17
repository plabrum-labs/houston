from enum import StrEnum, auto


# Violations — these lines must be flagged
class BadEnum(StrEnum):
    # ruleid: strenum-use-auto
    PENDING = "pending"
    # ruleid: strenum-use-auto
    ACTIVE = "active"


# OK — these must not be flagged
class GoodEnum(StrEnum):
    PENDING = auto()
    ACTIVE = auto()


# Non-StrEnum classes with string values must not be flagged
class NotAnEnum:
    PENDING = "pending"


# Lowercase/mixed-case member names must be flagged
class BadCaseEnum(StrEnum):
    # ruleid: strenum-member-caps
    pending = auto()
    # ruleid: strenum-member-caps
    camelCase = auto()
    # ruleid: strenum-member-caps
    MixedCase = auto()


# UPPER_SNAKE_CASE must not be flagged
class GoodCaseEnum(StrEnum):
    PENDING = auto()
    IN_PROGRESS = auto()


# Non-StrEnum classes with lowercase names must not be flagged
class NotAnEnumEither:
    pending = "pending"


# Lowercase name with hardcoded string triggers both rules
class DoubleBadEnum(StrEnum):
    # ruleid: strenum-use-auto, strenum-member-caps
    pending = "pending"


# Dunder attributes must not be flagged by either rule
class EnumWithDocstring(StrEnum):
    # ok: strenum-use-auto, strenum-member-caps
    __doc__ = "An enum"
    PENDING = auto()
