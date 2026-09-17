"""Action route factory.

The platform doesn't own the app's `ActionGroupType` enum, its auth guards, or its
discovery wiring — so the module-level router from the source app becomes a factory.
The app passes its `group_enum` (to coerce the `{action_group}` path string back
to a key) and its `guards`, and runs discovery / imports its actions before
calling. This keeps the factory pure and decoupled.
"""

from collections.abc import Sequence

from litestar import Router, get, post
from litestar.handlers.base import BaseRouteHandler
from litestar.params import Dependency
from litestar.types import Guard

from app.platform.actions.deps import ActionDeps
from app.platform.actions.registry import ActionRegistry
from app.platform.actions.schemas import (
    ActionExecutionResponse,
    ActionListResponse,
    _action_metadata,
    build_action_metadata,
    build_action_union,
)
from app.platform.utils.sqids import Sqid


def build_action_router(
    *,
    registry: ActionRegistry,
    group_enum: type,
    path: str = "/actions",
    guards: Sequence[Guard] = (),
) -> Router:
    """Build the actions router for an app.

    Args:
        registry: The (singleton) ActionRegistry, populated by the app's actions.
        group_enum: The app's ActionGroupType StrEnum — coerces the path string.
        path: Mount path (default "/actions").
        guards: Litestar guards applied to every action route (e.g. requires_session).
    """
    # Build the discriminated union + form metadata from the registered actions.
    action_union = build_action_union(registry)
    _action_metadata.update(build_action_metadata(registry))

    @get("/{action_group:str}")
    async def list_actions(
        action_group: str,
        action_registry: ActionRegistry,
        action_deps: ActionDeps = Dependency(skip_validation=True),
    ) -> ActionListResponse:
        """List available top-level actions for a group (no object context)."""
        group = group_enum(action_group)
        action_group_instance = action_registry.get_class(group)
        available_actions = action_group_instance.get_available_actions(action_deps)
        return ActionListResponse(actions=available_actions)

    @get("/{action_group:str}/{object_id:str}")
    async def list_object_actions(
        action_group: str,
        object_id: Sqid,
        action_registry: ActionRegistry,
        action_deps: ActionDeps = Dependency(skip_validation=True),
    ) -> ActionListResponse:
        """List available actions for a specific object within a group."""
        group = group_enum(action_group)
        action_group_instance = action_registry.get_class(group)
        object = await action_group_instance.get_object(object_id, action_deps.transaction)
        available_actions = action_group_instance.get_available_actions(action_deps, object)
        return ActionListResponse(actions=available_actions)

    async def execute_action(
        action_group: str,
        data,  # annotation set to `action_union` below
        action_registry: ActionRegistry,
        action_deps: ActionDeps = Dependency(skip_validation=True),
    ) -> ActionExecutionResponse:
        group = group_enum(action_group)
        action_group_instance = action_registry.get_class(group)
        return await action_group_instance.trigger(
            data=data,
            deps=action_deps,
            object_id=None,
        )

    async def execute_object_action(
        action_group: str,
        object_id: Sqid,
        data,  # annotation set to `action_union` below
        action_registry: ActionRegistry,
        action_deps: ActionDeps = Dependency(skip_validation=True),
    ) -> ActionExecutionResponse:
        group = group_enum(action_group)
        action_group_instance = action_registry.get_class(group)
        return await action_group_instance.trigger(
            data=data,
            deps=action_deps,
            object_id=object_id,
        )

    # The platform doesn't know the action union until the registry is populated, so the
    # `data` body type is injected onto the handler annotations after the fact.
    execute_action.__annotations__["data"] = action_union
    execute_object_action.__annotations__["data"] = action_union

    handlers: list[BaseRouteHandler] = [
        list_actions,
        list_object_actions,
        post("/{action_group:str}")(execute_action),
        post("/{action_group:str}/{object_id:str}")(execute_object_action),
    ]

    return Router(
        path=path,
        route_handlers=handlers,
        tags=["actions"],
        guards=list(guards),
    )
