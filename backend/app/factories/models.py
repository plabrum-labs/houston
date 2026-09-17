"""Per-model factories.

`Organization`/`User` are spine (every houston app has them). Factories pin only what a
test cares about (FK wiring, role, initial state) and let faker fill the rest.
"""

from app.domain.apps.enums import AppState
from app.domain.apps.models import App
from app.domain.organizations.models import Organization
from app.domain.users.models import User
from app.domain.users.roles import Role
from app.factories.base import BaseFactory


class OrganizationFactory(BaseFactory[Organization]):
    __model__ = Organization


class UserFactory(BaseFactory[User]):
    __model__ = User

    role = Role.CLIENT


class AppFactory(BaseFactory[App]):
    __model__ = App

    state = AppState.registered
