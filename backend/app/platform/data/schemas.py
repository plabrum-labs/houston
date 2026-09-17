from datetime import datetime

from msgspec import Struct

from app.platform.base.filters import FilterDefinition
from app.platform.base.schemas import BaseSchema
from app.platform.data.enums import AggregationType, FieldType, Granularity, TimeRange


class TimeSeriesDataRequest(BaseSchema):
    field: str
    time_range: TimeRange | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    granularity: Granularity = Granularity.AUTO
    aggregation: AggregationType | None = None
    filters: list[FilterDefinition] = []
    fill_missing: bool = True


class NumericalDataPoint(BaseSchema):
    timestamp: datetime
    value: float | None
    count: int


class CategoricalDataPoint(BaseSchema):
    timestamp: datetime
    breakdowns: dict[str, int]
    total_count: int


class NumericalTimeSeriesData(Struct, tag="numerical"):
    points: list[NumericalDataPoint]


class CategoricalTimeSeriesData(Struct, tag="categorical"):
    points: list[CategoricalDataPoint]


TimeSeriesData = NumericalTimeSeriesData | CategoricalTimeSeriesData


class TimeSeriesDataResponse(BaseSchema):
    data: TimeSeriesData
    field_name: str
    field_type: FieldType
    aggregation_type: AggregationType
    granularity_used: Granularity
    start_date: datetime
    end_date: datetime
    total_records: int


class FieldSchema(BaseSchema):
    name: str
    label: str
    field_type: FieldType
    aggregatable: bool
    filterable: bool


class DataSchemaResponse(BaseSchema):
    fields: list[FieldSchema]
    timestamp_field: str
