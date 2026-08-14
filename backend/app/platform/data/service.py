"""Time-series aggregation for CRUD `/data` endpoints.

Ported from the source app's `platform/data/service`. One forced change: the
`organization_id` parameter and its two `org_id_col == organization_id` WHERE
conditions are dropped — row scoping is RLS's job, identical to how `crud.py`
and `search_routes.py` were decoupled. The remaining `getattr(model, ...)` calls
resolve client/config-supplied *column-name strings* (the field and timestamp
columns) and are intrinsic to the data DSL — same as `base/filters`.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from litestar.exceptions import ValidationException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.base.filters import apply_filter
from app.platform.base.models import BaseDBModel
from app.platform.data.enums import AggregationType, FieldType, Granularity, TimeRange
from app.platform.data.schemas import (
    CategoricalDataPoint,
    CategoricalTimeSeriesData,
    NumericalDataPoint,
    NumericalTimeSeriesData,
    TimeSeriesDataRequest,
    TimeSeriesDataResponse,
)


@dataclass
class FieldConfig:
    name: str
    label: str
    field_type: FieldType
    aggregatable: bool = True
    filterable: bool = True


def _is_numerical(field_type: FieldType) -> bool:
    return field_type in (FieldType.INT, FieldType.FLOAT, FieldType.CENTS)


def _is_categorical(field_type: FieldType) -> bool:
    return field_type in (FieldType.STRING, FieldType.ENUM, FieldType.BOOL)


def _get_default_aggregation(field_type: FieldType) -> AggregationType:
    if _is_numerical(field_type):
        return AggregationType.sum
    return AggregationType.count


def _resolve_time_range(
    time_range: TimeRange | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> tuple[datetime, datetime]:
    now = datetime.now(tz=UTC)

    if start_date and end_date:
        return start_date, end_date

    if start_date and not end_date:
        return start_date, now

    end = end_date or now

    if time_range:
        start = _calculate_start(time_range, end)
    else:
        start = end - timedelta(days=30)

    return start, end


def _calculate_start(time_range: TimeRange, end: datetime) -> datetime:
    match time_range:
        case TimeRange.LAST_7_DAYS:
            return end - timedelta(days=7)
        case TimeRange.LAST_30_DAYS:
            return end - timedelta(days=30)
        case TimeRange.LAST_90_DAYS:
            return end - timedelta(days=90)
        case TimeRange.LAST_6_MONTHS:
            return end - timedelta(days=180)
        case TimeRange.LAST_YEAR:
            return end - timedelta(days=365)
        case TimeRange.YEAR_TO_DATE:
            return end.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        case TimeRange.MONTH_TO_DATE:
            return end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        case TimeRange.ALL_TIME:
            return end - timedelta(days=3650)


def _determine_granularity(granularity: Granularity, start: datetime, end: datetime) -> Granularity:
    if granularity != Granularity.AUTO:
        return granularity

    delta = end - start
    if delta <= timedelta(days=1):
        return Granularity.HOUR
    elif delta <= timedelta(days=7):
        return Granularity.DAY
    elif delta <= timedelta(days=90):
        return Granularity.WEEK
    elif delta <= timedelta(days=365):
        return Granularity.MONTH
    elif delta <= timedelta(days=730):
        return Granularity.QUARTER
    else:
        return Granularity.YEAR


def _trunc_format(granularity: Granularity) -> str:
    match granularity:
        case Granularity.HOUR:
            return "hour"
        case Granularity.DAY:
            return "day"
        case Granularity.WEEK:
            return "week"
        case Granularity.MONTH:
            return "month"
        case Granularity.QUARTER:
            return "quarter"
        case Granularity.YEAR:
            return "year"
        case Granularity.AUTO:
            raise ValueError("Granularity must be resolved before use")


def _series_interval(granularity: Granularity) -> str:
    match granularity:
        case Granularity.HOUR:
            return "1 hour"
        case Granularity.DAY:
            return "1 day"
        case Granularity.WEEK:
            return "1 week"
        case Granularity.MONTH:
            return "1 month"
        case Granularity.QUARTER:
            return "3 months"
        case Granularity.YEAR:
            return "1 year"
        case Granularity.AUTO:
            raise ValueError("Granularity must be resolved before use")


async def query_time_series_data(
    session: AsyncSession,
    model: type[BaseDBModel],
    fields: list[FieldConfig],
    request: TimeSeriesDataRequest,
    timestamp_field: str = "created_at",
) -> TimeSeriesDataResponse:
    field_cfg = next((f for f in fields if f.name == request.field), None)
    if field_cfg is None or not field_cfg.aggregatable:
        raise ValidationException(f"Field '{request.field}' is not available for aggregation")

    start, end = _resolve_time_range(request.time_range, request.start_date, request.end_date)
    granularity = _determine_granularity(request.granularity, start, end)
    aggregation = request.aggregation or _get_default_aggregation(field_cfg.field_type)

    trunc = _trunc_format(granularity)
    interval = _series_interval(granularity)

    timestamp_col = getattr(model, timestamp_field)
    field_col = getattr(model, field_cfg.name)

    filterable_cols = {f.name for f in fields if f.filterable}

    # Count total records in range (RLS scopes the rows).
    count_q = (
        select(func.count())
        .select_from(model)
        .where(
            timestamp_col >= start,
            timestamp_col <= end,
        )
    )
    for f in request.filters:
        count_q = apply_filter(count_q, model, f, filterable_cols)
    total = (await session.execute(count_q)).scalar_one()

    # generate_series subquery for gap-filling
    time_series = select(
        func.generate_series(
            func.date_trunc(trunc, start),
            func.date_trunc(trunc, end),
            text(f"interval '{interval}'"),
        ).label("time_bucket")
    ).subquery()

    time_bucket_expr = func.date_trunc(trunc, timestamp_col)

    base_conditions = [
        timestamp_col >= start,
        timestamp_col <= end,
    ]

    if _is_categorical(field_cfg.field_type):
        agg_q = (
            select(
                time_bucket_expr.label("time_bucket"),
                field_col.label("category_value"),
                func.count().label("count"),
            )
            .select_from(model)
            .where(*base_conditions)
            .group_by(time_bucket_expr, field_col)
        )
        for f in request.filters:
            agg_q = apply_filter(agg_q, model, f, filterable_cols)

        agg_sub = agg_q.subquery()
        final_q = (
            select(
                time_series.c.time_bucket,
                agg_sub.c.category_value,
                func.coalesce(agg_sub.c.count, 0).label("count"),
            )
            .select_from(time_series)
            .outerjoin(agg_sub, time_series.c.time_bucket == agg_sub.c.time_bucket)
            .order_by(time_series.c.time_bucket)
        )

        rows = (await session.execute(final_q)).all()

        bucket_map: dict[datetime, dict[str, int]] = {}
        for row in rows:
            bucket = row.time_bucket
            if bucket not in bucket_map:
                bucket_map[bucket] = {}
            if row.category_value is not None:
                bucket_map[bucket][str(row.category_value)] = row._mapping["count"]

        points = [
            CategoricalDataPoint(
                timestamp=bucket,
                breakdowns=breakdowns,
                total_count=sum(breakdowns.values()),
            )
            for bucket, breakdowns in sorted(bucket_map.items())
        ]

        return TimeSeriesDataResponse(
            data=CategoricalTimeSeriesData(points=points),
            field_name=field_cfg.name,
            field_type=field_cfg.field_type,
            aggregation_type=AggregationType.count,
            granularity_used=granularity,
            start_date=start,
            end_date=end,
            total_records=total,
        )

    else:
        match aggregation:
            case AggregationType.sum:
                agg_func = func.sum(field_col)
            case AggregationType.avg:
                agg_func = func.avg(field_col)
            case AggregationType.max:
                agg_func = func.max(field_col)
            case AggregationType.min:
                agg_func = func.min(field_col)
            case AggregationType.count:
                agg_func = func.count(field_col)
            case _:
                agg_func = func.sum(field_col)

        agg_q = (
            select(
                time_bucket_expr.label("time_bucket"),
                agg_func.label("agg_value"),
                func.count().label("record_count"),
            )
            .select_from(model)
            .where(*base_conditions)
            .group_by(time_bucket_expr)
        )
        for f in request.filters:
            agg_q = apply_filter(agg_q, model, f, filterable_cols)

        agg_sub = agg_q.subquery()
        final_q = (
            select(
                time_series.c.time_bucket,
                func.coalesce(agg_sub.c.agg_value, 0).label("agg_value"),
                func.coalesce(agg_sub.c.record_count, 0).label("record_count"),
            )
            .select_from(time_series)
            .outerjoin(agg_sub, time_series.c.time_bucket == agg_sub.c.time_bucket)
            .order_by(time_series.c.time_bucket)
        )

        rows = (await session.execute(final_q)).all()

        points = [
            NumericalDataPoint(
                timestamp=row.time_bucket,
                value=float(row.agg_value) if row.agg_value is not None else None,
                count=row.record_count,
            )
            for row in rows
        ]

        return TimeSeriesDataResponse(
            data=NumericalTimeSeriesData(points=points),
            field_name=field_cfg.name,
            field_type=field_cfg.field_type,
            aggregation_type=aggregation,
            granularity_used=granularity,
            start_date=start,
            end_date=end,
            total_records=total,
        )
