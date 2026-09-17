from __future__ import annotations

from enum import StrEnum, auto

import msgspec
from litestar.exceptions import NotFoundException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.actions.base import BaseObjectAction, BaseTopLevelAction, EmptyActionData, action_group_factory
from app.platform.actions.deps import ActionDeps
from app.platform.actions.enums import ActionIcon
from app.platform.actions.schemas import ActionExecutionResponse
from app.platform.dashboard.models import Dashboard, Widget
from app.platform.dashboard.schemas import CreateWidgetData, UpdateWidgetData


class DashboardActionGroupType(StrEnum):
    # The platform ships these widget actions, so this module brings its own action
    # group key (D15 — the platform is generic over the app's action-group StrEnum;
    # the app routes this group alongside its own).
    WIDGET_ACTIONS = auto()


class WidgetActionKey(StrEnum):
    CREATE = auto()
    UPDATE = auto()
    DELETE = auto()


widget_actions = action_group_factory(
    group_type=DashboardActionGroupType.WIDGET_ACTIONS,
    default_invalidation="/dashboard",
    model_type=Widget,
)


async def _load_owned_dashboard(transaction: AsyncSession, dashboard_id: int) -> Dashboard:
    result = await transaction.execute(select(Dashboard).where(Dashboard.id == int(dashboard_id)))
    dashboard = result.scalar_one_or_none()
    if dashboard is None:
        raise NotFoundException(detail="Dashboard not found")
    return dashboard


@widget_actions
class CreateWidget(BaseTopLevelAction[CreateWidgetData]):
    action_key = WidgetActionKey.CREATE
    label = "Add Widget"
    icon = ActionIcon.ADD
    priority = 10

    @classmethod
    async def execute(
        cls, data: CreateWidgetData, transaction: AsyncSession, deps: ActionDeps
    ) -> ActionExecutionResponse:
        await _load_owned_dashboard(transaction, int(data.dashboard_id))

        widget = Widget(
            dashboard_id=int(data.dashboard_id),
            user_id=int(deps.user.id),
            type=data.type,
            title=data.title,
            description=data.description,
            query=msgspec.to_builtins(data.query),
            position_x=data.position_x,
            position_y=data.position_y,
            size_w=data.size_w,
            size_h=data.size_h,
        )
        transaction.add(widget)
        await transaction.flush()
        return ActionExecutionResponse(message="Widget created", created_id=widget.id)


@widget_actions
class UpdateWidget(BaseObjectAction[Widget, UpdateWidgetData]):
    action_key = WidgetActionKey.UPDATE
    label = "Edit Widget"
    icon = ActionIcon.EDIT
    priority = 20

    @classmethod
    async def execute(
        cls, obj: Widget, data: UpdateWidgetData, transaction: AsyncSession, deps: ActionDeps
    ) -> ActionExecutionResponse:
        obj.type = data.type
        obj.title = data.title
        obj.description = data.description
        obj.query = msgspec.to_builtins(data.query)
        obj.position_x = data.position_x
        obj.position_y = data.position_y
        obj.size_w = data.size_w
        obj.size_h = data.size_h
        return ActionExecutionResponse(message="Widget updated")


@widget_actions
class DeleteWidget(BaseObjectAction[Widget, EmptyActionData]):
    action_key = WidgetActionKey.DELETE
    label = "Delete Widget"
    icon = ActionIcon.TRASH
    priority = 90
    confirmation_message = "Delete this widget?"

    @classmethod
    async def execute(
        cls, obj: Widget, data: EmptyActionData, transaction: AsyncSession, deps: ActionDeps
    ) -> ActionExecutionResponse:
        obj.soft_delete()
        return ActionExecutionResponse(message="Widget deleted")
