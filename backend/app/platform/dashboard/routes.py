from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import msgspec
from litestar import Router, get
from litestar.params import Dependency
from litestar.types import Guard
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.platform.dashboard.enums import WidgetType
from app.platform.dashboard.models import Dashboard, Widget
from app.platform.dashboard.schemas import DashboardRead, WidgetQuery, WidgetRead
from app.platform.state_machine.roles import Actor

_ALL_WIDGET_TYPES = list(WidgetType)


def _widget_to_read(widget: Widget) -> WidgetRead:
    return WidgetRead(
        id=widget.id,
        dashboard_id=widget.dashboard_id,
        type=widget.type,
        title=widget.title,
        description=widget.description,
        query=msgspec.convert(widget.query, WidgetQuery),
        position_x=widget.position_x,
        position_y=widget.position_y,
        size_w=widget.size_w,
        size_h=widget.size_h,
        created_at=widget.created_at,
        updated_at=widget.updated_at,
    )


def _to_read(dashboard: Dashboard, widgets: list[Widget]) -> DashboardRead:
    return DashboardRead(
        id=dashboard.id,
        widgets=[_widget_to_read(w) for w in widgets],
        widget_types=_ALL_WIDGET_TYPES,
        updated_at=dashboard.updated_at,
    )


@get("/", tags=["dashboard"], operation_id="get_dashboard")
async def get_dashboard_handler(
    transaction: AsyncSession,
    user: Actor[Any] = Dependency(skip_validation=True),
) -> DashboardRead:
    result = await transaction.execute(select(Dashboard).options(selectinload(Dashboard.widgets)))
    dashboard = result.scalar_one_or_none()
    if dashboard is None:
        dashboard = Dashboard(user_id=user.id)
        transaction.add(dashboard)
        await transaction.flush()
        widgets: list[Widget] = []
    else:
        widgets = list(dashboard.widgets)
    return _to_read(dashboard, widgets)


def build_dashboard_router(*, path: str = "/dashboard", guards: Sequence[Guard] = ()) -> Router:
    """Build the dashboard router for an app.

    The platform doesn't own the app's auth guards, so the module-level router from
    the source app (which hardcoded `guards=[requires_session]`) becomes a factory
    with `guards` injected — same guard-injection pattern as `build_action_router` / the CRUD
    controller factories / `build_document_router` / `build_thread_router`.
    """
    return Router(
        path=path,
        guards=list(guards),
        route_handlers=[get_dashboard_handler],
    )
