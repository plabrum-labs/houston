from enum import Enum, StrEnum, auto


class FieldType(StrEnum):
    INT = auto()
    FLOAT = auto()
    CENTS = auto()
    STRING = auto()
    ENUM = auto()
    DATETIME = auto()
    BOOL = auto()


class AggregationType(Enum):
    sum = "sum"
    avg = "avg"
    max = "max"
    min = "min"
    count = "count"


class Granularity(StrEnum):
    HOUR = auto()
    DAY = auto()
    WEEK = auto()
    MONTH = auto()
    QUARTER = auto()
    YEAR = auto()
    AUTO = auto()


class TimeRange(StrEnum):
    LAST_7_DAYS = auto()
    LAST_30_DAYS = auto()
    LAST_90_DAYS = auto()
    LAST_6_MONTHS = auto()
    LAST_YEAR = auto()
    YEAR_TO_DATE = auto()
    MONTH_TO_DATE = auto()
    ALL_TIME = auto()
