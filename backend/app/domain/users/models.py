"""Concrete tenancy models — the required subclasses of houston's abstract mixins.

Every houston app MUST define a concrete `User` and `Organization`: houston ships
`UserMixin` / `OrganizationBase` abstract (it owns the base tenancy + RLS convention,
names a generic `Actor`), and the app supplies the real tables + its `Role`. This is
the spine, not demo code — the domain models under `app/domain/` hang off it.
"""

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.users.roles import Role
from app.platform.users.models import UserMixin


class User(UserMixin(role_enum=Role, default_role=Role.CLIENT)):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(sa.Text)
