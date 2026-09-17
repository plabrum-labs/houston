"""Base user + organization tenancy layer.

The platform owns the tenancy convention: tables named `users` / `organizations`, and
the RLS session vars `app.user_id` / `app.organization_id` / `app.is_system_mode`.
Apps define the CONCRETE tables by subclassing these mixins and binding their own
`Role` enum (role values are app-specific), then add whatever extra columns and
relationships they need:

    class Role(StrEnum):
        STAFF = auto(); CLIENT = auto()

    class Organization(OrganizationBase):
        __tablename__ = "organizations"

    class User(UserMixin(role_enum=Role, default_role=Role.CLIENT)):
        __tablename__ = "users"
        name: Mapped[str] = mapped_column(sa.Text)

A concrete `User` exposes `.id` (int) and `.role` (R), so it structurally
satisfies `app.platform.state_machine.roles.Actor[R]` with no adapter.
"""

from __future__ import annotations

from enum import Enum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.platform.base.models import BaseDBModel
from app.platform.utils.textenum import TextEnum


class OrganizationBase(BaseDBModel):
    """Abstract base for the tenant root. Apps set `__tablename__ = "organizations"`."""

    __abstract__ = True


class _UserMixinBase[R: Enum](BaseDBModel):
    """Statically-visible surface of the `UserMixin(...)` factory's return type.

    `UserMixin(...)` is *declared* to return `type[_UserMixinBase[R]]`, so this is
    the only class a type checker ever sees for a concrete `User` — the factory's
    local `_Mixin` is invisible to it. Every tenancy column the factory adds at
    runtime therefore has to be re-declared here, or `User.organization_id` /
    `User.role` do not exist statically and `User` silently fails to satisfy
    `app.platform.state_machine.roles.Actor[R]`.

    The declarations are annotation-only and this class is `__abstract__`, so the
    real columns still come from `_Mixin`'s `@declared_attr`s.
    """

    __abstract__ = True
    role: Mapped[R]
    organization_id: Mapped[int]


def UserMixin[R: Enum](  # noqa: N802
    *, role_enum: type[R], default_role: R
) -> type[_UserMixinBase[R]]:
    """Factory returning an abstract mixin with the tenancy columns (`organization_id`, `role`)."""

    class _Mixin(_UserMixinBase[R]):
        __abstract__ = True

        @declared_attr
        def organization_id(cls) -> Mapped[int]:  # noqa: N805
            return mapped_column(
                sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
                nullable=False,
                index=True,
            )

        @declared_attr
        def role(cls) -> Mapped[R]:  # noqa: N805
            return mapped_column(
                TextEnum(role_enum),
                nullable=False,
                server_default=default_role.name,
            )

        def __init_subclass__(cls, **kwargs: object) -> None:
            # Pin the concrete role type on the subclass BEFORE super() triggers
            # SQLAlchemy mapping — otherwise the mapper sees the unresolved
            # `Mapped[R]` TypeVar inherited from _UserMixinBase and fails.
            if not cls.__dict__.get("__abstract__", False):
                cls.__annotations__["role"] = Mapped[role_enum]
            super().__init_subclass__(**kwargs)

    return _Mixin
