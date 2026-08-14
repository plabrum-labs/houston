"""App-owned dependencies.

The app subclasses houston's base `ActionDeps` (re-annotating `organization` to its
concrete model) and owns `provide_action_deps` — houston ships only
`provide_action_registry`. The app decides here which services
its actions receive. Add `billing` / `email` / `config` / `task_queues` fields here as
you adopt those services.
"""

from dataclasses import dataclass

from litestar import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.organizations.models import Organization
from app.domain.users.models import User
from app.platform.actions.deps import ActionDeps
from app.platform.utils.deps import dep


@dataclass
class AppActionDeps(ActionDeps):
    organization: Organization


@dep("user", sync_to_thread=False)
def provide_user(request: Request) -> User:
    return request.user


@dep("organization")
async def provide_organization(transaction: AsyncSession, user: User) -> Organization:
    org = await transaction.get(Organization, user.organization_id)
    assert org is not None  # visible under the caller's own org scope
    return org


@dep("action_deps", sync_to_thread=False)
def provide_action_deps(
    transaction: AsyncSession,
    request: Request,
    user: User,
    organization: Organization,
) -> AppActionDeps:
    return AppActionDeps(
        user=user,
        organization=organization,
        transaction=transaction,
        request=request,
    )
