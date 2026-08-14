from __future__ import annotations

from enum import Enum
from typing import Protocol

from sqlalchemy.orm import Mapped

from app.platform.utils.sqids import Sqid


class Actor[R: Enum](Protocol):
    """Structural type for the authenticated principal.

    Any *mapped* model exposing an `id`, a role enum column and an
    `organization_id` column satisfies the contract — the app's `User` model
    (on `UserMixin`, which carries `role` + `organization_id`) satisfies it
    as-is, no adapter needed. The role enum itself is supplied by the app
    (generic `R`); the platform never names a specific role. Reading a member off an
    `Actor` still yields the plain value (`Sqid` / `R` / `int`) — SQLAlchemy's
    `Mapped` descriptor unwraps on instance access.

    The members are declared as `Mapped[...]` rather than plain `int` / `R`
    because a type checker does *not* apply the descriptor protocol when
    matching a class against a protocol: a model declaring
    `id: Mapped[Sqid]` never matches a protocol declaring `id: int`, however
    the attribute behaves at runtime. Declaring the mapped types is what makes
    "`User` satisfies `Actor` with no adapter" true statically as well as at
    runtime (D30). `Mapped` is invariant here because the members are mutable,
    hence `Mapped[Sqid]` (what every `BaseDBModel` declares) rather than
    `Mapped[int]`.

    `organization_id` is part of the principal because the platform is org-scoped
    multi-tenant throughout (`OrgScopedMixin`, RLS `app.organization_id`):
    platform-owned code needs the caller's org to create org-scoped rows and to
    set up the RLS/tenant context on non-action paths (e.g. websocket handlers).
    Read *filtering* stays RLS's job (D18) — this is only write/context access.
    """

    id: Mapped[Sqid]
    role: Mapped[R]
    organization_id: Mapped[int]
