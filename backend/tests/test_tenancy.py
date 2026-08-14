"""Proves the harness: savepoint isolation, polyfactory seeding, RLS scoping.

Exercises `app.platform.testing` (savepoint_session + set_rls) and `BaseFactory` through
real pytest fixtures against Postgres, using the `App` domain entity.
"""

from sqlalchemy import select

from app.domain.apps.enums import AppState
from app.domain.apps.models import App
from app.domain.users.roles import Role
from app.factories import AppFactory, OrganizationFactory, UserFactory
from app.platform.testing import set_rls


async def test_factory_seeds_in_system_mode(db_session):
    org = await OrganizationFactory.create_async(db_session, name="Acme")
    assert isinstance(org.id, int)
    user = await UserFactory.create_async(db_session, organization_id=org.id, role=Role.STAFF)
    assert user.role is Role.STAFF
    assert user.organization_id == org.id


async def test_app_starts_in_initial_state(db_session, organization):
    app = await AppFactory.create_async(
        db_session, organization_id=organization.id, name="Widgets", repo_url="https://example.com/widgets.git"
    )
    assert app.state is AppState.registered


async def test_rls_isolates_to_own_org(db_session):
    acme = await OrganizationFactory.create_async(db_session, name="Acme")
    bravo = await OrganizationFactory.create_async(db_session, name="Bravo")
    staff = await UserFactory.create_async(db_session, organization_id=acme.id, role=Role.STAFF)
    await AppFactory.create_async(
        db_session, organization_id=acme.id, name="mine", repo_url="https://example.com/mine.git"
    )
    await AppFactory.create_async(
        db_session, organization_id=bravo.id, name="theirs", repo_url="https://example.com/theirs.git"
    )

    # Flip from system mode to the acme user's RLS scope.
    await set_rls(db_session, user_id=int(staff.id), organization_id=int(acme.id))

    names = {a.name for a in (await db_session.scalars(select(App))).all()}
    assert "mine" in names
    assert "theirs" not in names  # the other org's row is invisible under RLS
