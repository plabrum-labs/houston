"""Typed dependencies for actions.

`ActionDeps` is the principal seam. The platform owns only the framework fields
(`user`/`organization`/`transaction`/`request`); apps subclass it to add their own
services (billing, email, sm_service, config, task_queues) and may re-annotate
`organization` to their concrete model. The app owns `provide_action_deps`
(returning its subclass) — the platform ships only `provide_action_registry`.

`organization` is typed `OrganizationBase` (the platform-owned tenant-root base,
an `id`-bearing `BaseDBModel`) so platform-owned actions can read `deps.organization.id`
when creating an org-scoped row that has no parent to inherit from. The app's
concrete `Organization(OrganizationBase)` satisfies it; reads stay RLS-scoped (D18).
"""

from dataclasses import dataclass
from typing import Any

from litestar import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.actions.registry import ActionRegistry
from app.platform.state_machine.roles import Actor
from app.platform.users.models import OrganizationBase
from app.platform.utils.deps import dep


@dataclass
class ActionDeps:
    """Base typed dependencies available to all actions."""

    user: Actor[Any]
    organization: OrganizationBase
    transaction: AsyncSession
    request: Request


@dep("action_registry", sync_to_thread=False)
def provide_action_registry() -> ActionRegistry:
    return ActionRegistry()
