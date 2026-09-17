"""App action group — the houston actions (write) pillar from an app's view.

The app owns its `ActionGroupType` StrEnum (houston is generic over it, like `Role`):
a top-level create + an object action that drives the state machine, each gated by
`is_available` reading `deps.user.role`.
"""

from enum import StrEnum, auto

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.apps.enums import AppState
from app.domain.apps.models import App
from app.domain.apps.state_machine import app_machine
from app.domain.users.roles import Role
from app.platform.actions.base import (
    BaseObjectAction,
    BaseTopLevelAction,
    EmptyActionData,
    action_group_factory,
)
from app.platform.actions.deps import ActionDeps
from app.platform.actions.schemas import ActionExecutionResponse
from app.platform.base.schemas import BaseSchema
from app.platform.state_machine.machine import StateMachineService


class AppActionGroupType(StrEnum):
    """App-owned action group enum — houston is generic over this (like Role)."""

    APP_ACTIONS = auto()


class AppActionKey(StrEnum):
    CREATE_APP = auto()
    PROVISION_APP = auto()


app_actions = action_group_factory(
    group_type=AppActionGroupType.APP_ACTIONS,
    model_type=App,
    default_invalidation="/apps",
)


class CreateAppData(BaseSchema):
    name: str
    repo_url: str


@app_actions
class CreateApp(BaseTopLevelAction[CreateAppData]):
    action_key = AppActionKey.CREATE_APP
    label = "Create App"

    @classmethod
    def is_available(cls, deps: ActionDeps) -> bool:
        return deps.user.role is Role.STAFF

    @classmethod
    async def execute(
        cls,
        data: CreateAppData,
        transaction: AsyncSession,
        deps: ActionDeps,
    ) -> ActionExecutionResponse:
        app = App(organization_id=deps.organization.id, name=data.name, repo_url=data.repo_url)
        transaction.add(app)
        await transaction.flush()
        return ActionExecutionResponse(message="App created", created_id=app.id)


@app_actions
class ProvisionApp(BaseObjectAction[App, EmptyActionData]):
    action_key = AppActionKey.PROVISION_APP
    label = "Provision App"
    target_state = AppState.provisioning

    @classmethod
    def is_available(cls, obj: App, deps: ActionDeps) -> bool:
        return deps.user.role is Role.STAFF

    @classmethod
    async def execute(
        cls,
        obj: App,
        data: EmptyActionData,
        transaction: AsyncSession,
        deps: ActionDeps,
    ) -> ActionExecutionResponse:
        svc = StateMachineService(transaction)
        await svc.transition(app_machine, obj, AppState.provisioning, actor=deps.user)
        return ActionExecutionResponse(message="App provisioning")
