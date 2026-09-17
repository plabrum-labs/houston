"""LLM tools for managing the user's dashboard widgets."""

from typing import Any

import msgspec
from msgspec import Struct
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.platform.dashboard.enums import WidgetColor, WidgetType
from app.platform.dashboard.models import Dashboard, Widget
from app.platform.dashboard.schemas import WidgetQuery
from app.platform.data.enums import AggregationType, Granularity, TimeRange
from app.platform.llm.registry import SloopTool, ToolContext, ToolResult, register_tool
from app.platform.llm.schemas import InputSchema, PropertySchema
from app.platform.utils.sqids import Sqid  # Sqid is used in input structs for decoding widget_id

# The platform names no app resources; the concrete resource set is app-defined
# and supplied at runtime, so the framework default is an empty neutral list.
_RESOURCE_TYPES: list[str] = []
_WIDGET_TYPES = [e.value for e in WidgetType]
_AGGREGATION_TYPES = [e.value for e in AggregationType]
_GRANULARITIES = [e.value for e in Granularity]
_TIME_RANGES = [e.value for e in TimeRange]
_WIDGET_COLORS = [e.value for e in WidgetColor]

_FIELD_REQUIRED_TYPES = {WidgetType.AREA_CHART, WidgetType.BAR_CHART, WidgetType.STAT_NUMBER}


def _validate_widget_field(widget_type: WidgetType, field: str | None) -> str | None:
    """Return an error string if field is missing for chart/stat widgets, else None."""
    if widget_type in _FIELD_REQUIRED_TYPES and not field:
        return f"Widget type '{widget_type}' requires a non-empty 'field'."
    return None


async def _get_or_create_dashboard(ctx: ToolContext) -> Dashboard:
    result = await ctx.db.execute(select(Dashboard))
    dashboard = result.scalar_one_or_none()
    if dashboard is None:
        dashboard = Dashboard(user_id=int(ctx.user.id))
        ctx.db.add(dashboard)
        await ctx.db.flush()
    return dashboard


async def _load_widget(ctx: ToolContext, widget_id: Sqid) -> Widget | None:
    result = await ctx.db.execute(select(Widget).where(Widget.id == int(widget_id)))
    return result.scalar_one_or_none()


class ListWidgetsInput(Struct):
    pass


@register_tool
class ListWidgetsTool(SloopTool):
    name = "list_widgets"
    description = "List all widgets currently on the user's dashboard."
    input_schema = InputSchema(properties={})
    input_struct = ListWidgetsInput

    async def execute(self, ctx: ToolContext, args: ListWidgetsInput) -> ToolResult | str:
        result = await ctx.db.execute(select(Dashboard).options(selectinload(Dashboard.widgets)))
        dashboard = result.scalar_one_or_none()
        if dashboard is None or not dashboard.widgets:
            return ToolResult(message="The dashboard has no widgets.")

        data: list[dict[str, Any]] = [
            {
                "id": str(w.id),
                "type": w.type,
                "title": w.title,
                "description": w.description,
                "query": w.query,
                "position_x": w.position_x,
                "position_y": w.position_y,
                "size_w": w.size_w,
                "size_h": w.size_h,
            }
            for w in dashboard.widgets
        ]
        return ToolResult(data=data)


class AddWidgetInput(Struct):
    type: str
    title: str
    resource: str
    description: str | None = None
    field: str | None = None
    aggregation: str | None = None
    time_range: str | None = None
    granularity: str | None = None
    columns: list[str] = []
    limit: int | None = None
    color: str | None = None
    href: str | None = None
    position_x: int = 0
    position_y: int = 0
    size_w: int = 2
    size_h: int = 2


@register_tool
class AddWidgetTool(SloopTool):
    name = "add_widget"
    description = (
        "Add a new widget to the user's dashboard. "
        f"widget_type options: {_WIDGET_TYPES}. "
        f"resource options: {_RESOURCE_TYPES}. "
        f"aggregation options: {_AGGREGATION_TYPES}. "
        f"time_range options: {_TIME_RANGES}. "
        f"granularity options: {_GRANULARITIES}. "
        f"color options: {_WIDGET_COLORS}. "
        "kanban widgets group rows by state on a state-machine resource "
        "and let the user drag cards between columns to trigger state transitions; "
        "they're wide — prefer size_w=4 size_h=4."
    )
    input_schema = InputSchema(
        properties={
            "type": PropertySchema(type="string", description=f"Widget type. One of: {_WIDGET_TYPES}."),
            "title": PropertySchema(type="string", description="Display title for the widget."),
            "resource": PropertySchema(type="string", description=f"Data resource. One of: {_RESOURCE_TYPES}."),
            "description": PropertySchema(type="string", description="Optional subtitle."),
            "field": PropertySchema(
                type="string", description="Field to aggregate (e.g. 'created_at', 'market_value_cents')."
            ),
            "aggregation": PropertySchema(
                type="string", description=f"Aggregation function. One of: {_AGGREGATION_TYPES}."
            ),
            "time_range": PropertySchema(type="string", description=f"Time range. One of: {_TIME_RANGES}."),
            "granularity": PropertySchema(type="string", description=f"Chart granularity. One of: {_GRANULARITIES}."),
            "columns": PropertySchema(
                type="array",
                description="Columns to show (for resource_table widgets).",
                items=PropertySchema(type="string"),
            ),
            "limit": PropertySchema(type="integer", description="Row limit (for list/table widgets)."),
            "color": PropertySchema(
                type="string", description=f"Accent color (for stat_number widgets). One of: {_WIDGET_COLORS}."
            ),
            "href": PropertySchema(type="string", description="Link URL for the widget title."),
            "position_x": PropertySchema(type="integer", description="Column position (0-indexed, default 0)."),
            "position_y": PropertySchema(type="integer", description="Row position (0-indexed, default 0)."),
            "size_w": PropertySchema(type="integer", description="Width in grid columns (default 2)."),
            "size_h": PropertySchema(type="integer", description="Height in grid rows (default 2)."),
        },
        required=["type", "title", "resource"],
    )
    input_struct = AddWidgetInput

    async def execute(self, ctx: ToolContext, args: AddWidgetInput) -> ToolResult | str:
        dashboard = await _get_or_create_dashboard(ctx)

        widget_type = WidgetType(args.type)
        field = args.field or None
        if err := _validate_widget_field(widget_type, field):
            return err

        query = WidgetQuery(
            resource=args.resource,
            field=field,
            aggregation=AggregationType(args.aggregation) if args.aggregation else None,
            time_range=TimeRange(args.time_range) if args.time_range else None,
            granularity=Granularity(args.granularity) if args.granularity else None,
            columns=args.columns,
            limit=args.limit,
            color=WidgetColor(args.color) if args.color else None,
            href=args.href,
        )

        widget = Widget(
            dashboard_id=int(dashboard.id),
            user_id=int(ctx.user.id),
            type=widget_type,
            title=args.title,
            description=args.description,
            query=msgspec.to_builtins(query),
            position_x=args.position_x,
            position_y=args.position_y,
            size_w=args.size_w,
            size_h=args.size_h,
        )
        ctx.db.add(widget)
        await ctx.db.flush()

        ctx.invalidate_keys.append("/dashboard")
        return ToolResult(
            data={"id": str(widget.id)},
            message=f"Widget '{args.title}' added to dashboard.",
        )


class RemoveWidgetInput(Struct):
    widget_id: Sqid


@register_tool
class RemoveWidgetTool(SloopTool):
    name = "remove_widget"
    description = "Remove a widget from the dashboard by its ID."
    input_schema = InputSchema(
        properties={
            "widget_id": PropertySchema(type="string", description="The widget's SQID (from list_widgets)."),
        },
        required=["widget_id"],
    )
    input_struct = RemoveWidgetInput

    async def execute(self, ctx: ToolContext, args: RemoveWidgetInput) -> ToolResult | str:
        widget = await _load_widget(ctx, args.widget_id)
        if widget is None:
            return "Widget not found."

        widget.soft_delete()
        ctx.invalidate_keys.append("/dashboard")
        return ToolResult(message=f"Widget '{widget.title}' removed.")


class UpdateWidgetInput(Struct):
    widget_id: Sqid
    type: str
    title: str
    resource: str
    description: str | None = None
    field: str | None = None
    aggregation: str | None = None
    time_range: str | None = None
    granularity: str | None = None
    columns: list[str] = []
    limit: int | None = None
    color: str | None = None
    href: str | None = None
    position_x: int = 0
    position_y: int = 0
    size_w: int = 2
    size_h: int = 2


@register_tool
class UpdateWidgetTool(SloopTool):
    name = "update_widget"
    description = "Update an existing dashboard widget's configuration, title, or position."
    input_schema = InputSchema(
        properties={
            "widget_id": PropertySchema(type="string", description="The widget's SQID (from list_widgets)."),
            "type": PropertySchema(type="string", description=f"Widget type. One of: {_WIDGET_TYPES}."),
            "title": PropertySchema(type="string", description="Display title for the widget."),
            "resource": PropertySchema(type="string", description=f"Data resource. One of: {_RESOURCE_TYPES}."),
            "description": PropertySchema(type="string", description="Optional subtitle."),
            "field": PropertySchema(type="string", description="Field to aggregate."),
            "aggregation": PropertySchema(
                type="string", description=f"Aggregation function. One of: {_AGGREGATION_TYPES}."
            ),
            "time_range": PropertySchema(type="string", description=f"Time range. One of: {_TIME_RANGES}."),
            "granularity": PropertySchema(type="string", description=f"Chart granularity. One of: {_GRANULARITIES}."),
            "columns": PropertySchema(
                type="array",
                description="Columns to show.",
                items=PropertySchema(type="string"),
            ),
            "limit": PropertySchema(type="integer", description="Row limit."),
            "color": PropertySchema(type="string", description=f"Accent color. One of: {_WIDGET_COLORS}."),
            "href": PropertySchema(type="string", description="Link URL."),
            "position_x": PropertySchema(type="integer", description="Column position."),
            "position_y": PropertySchema(type="integer", description="Row position."),
            "size_w": PropertySchema(type="integer", description="Width in grid columns."),
            "size_h": PropertySchema(type="integer", description="Height in grid rows."),
        },
        required=["widget_id", "type", "title", "resource"],
    )
    input_struct = UpdateWidgetInput

    async def execute(self, ctx: ToolContext, args: UpdateWidgetInput) -> ToolResult | str:
        widget = await _load_widget(ctx, args.widget_id)
        if widget is None:
            return "Widget not found."

        widget_type = WidgetType(args.type)
        field = args.field or None
        if err := _validate_widget_field(widget_type, field):
            return err

        query = WidgetQuery(
            resource=args.resource,
            field=field,
            aggregation=AggregationType(args.aggregation) if args.aggregation else None,
            time_range=TimeRange(args.time_range) if args.time_range else None,
            granularity=Granularity(args.granularity) if args.granularity else None,
            columns=args.columns,
            limit=args.limit,
            color=WidgetColor(args.color) if args.color else None,
            href=args.href,
        )

        widget.type = widget_type
        widget.title = args.title
        widget.description = args.description
        widget.query = msgspec.to_builtins(query)
        widget.position_x = args.position_x
        widget.position_y = args.position_y
        widget.size_w = args.size_w
        widget.size_h = args.size_h

        ctx.invalidate_keys.append("/dashboard")
        return ToolResult(message=f"Widget '{args.title}' updated.")
