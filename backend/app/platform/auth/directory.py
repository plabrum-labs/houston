"""Generic `UserDirectory` implementations over any `AuthUserMixin` subclass (D19).

Two directories exist on purpose:

- `ModelUserDirectory` is DI-backed (`transaction: AsyncSession`) and is only
  ever used inside a request that already has one — i.e. by
  `app.platform.auth.deps.provide_auth_service` for the `/auth/magic-link/*` routes.
- `SessionScopedUserDirectory` owns a short-lived session per lookup because
  `SessionAuth`'s `retrieve_user_handler` runs inside the authentication
  middleware, *before* Litestar resolves any request-scoped dependency (there
  is no `transaction` dep yet at that point in the ASGI pipeline).

Both are parameterized by the app's concrete `User` model (any
`AuthUserMixin` subclass) instead of being hand-written per app — the lookup
logic itself is generic. `get_or_create_by_email` only ever *gets*: apps are
assumed pre-provisioned (no org context to attach a brand-new account to at
magic-link request time). An app whose lookup semantics genuinely differ
(e.g. create-on-first-request) subclasses `ModelUserDirectory` and overrides
that one method.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.auth.models import AuthUserMixin
from app.platform.state_machine.roles import Actor

__all__ = ["ModelUserDirectory", "SessionScopedUserDirectory"]


class ModelUserDirectory[U: AuthUserMixin]:
    """`UserDirectory` backed by the request's own scoped `transaction`."""

    def __init__(self, transaction: AsyncSession, model: type[U]) -> None:
        self.db = transaction
        self.model = model

    async def get_or_create_by_email(self, email: str) -> tuple[U, bool]:
        """Only ever *gets* — raises if no matching row. See module docstring.

        Returns the concrete `U`, not `Actor[Any]`: every real `model` also
        composes `app.platform.users.models.UserMixin`, so `U` structurally
        satisfies `Actor` at the call site and needs no cast here.
        """
        user = await self._get_by_email(email)
        if user is None:
            raise ValueError(f"No account exists for {email}")
        return user, False

    async def get_by_id(self, user_id: int) -> U | None:
        return await self.db.get(self.model, user_id)

    async def mark_email_verified(self, user: Actor[Any]) -> None:
        assert isinstance(user, self.model)
        if user.email_verified_at is None:
            user.email_verified_at = datetime.now(UTC)
            await self.db.flush()

    async def _get_by_email(self, email: str) -> U | None:
        result = await self.db.execute(select(self.model).where(self.model.email == email))
        return result.scalar_one_or_none()


class SessionScopedUserDirectory[U: AuthUserMixin]:
    """`UserDirectory` used only by `SessionAuth`'s `retrieve_user_handler`.

    `open_session` is called once per lookup and must yield an `AsyncSession`
    as an async context manager (an `async_sessionmaker` instance satisfies
    this directly — calling it returns a session that is itself an async
    context manager). Only `get_by_id` is exercised in practice; the other two
    protocol methods are not reachable from the middleware and raise.
    """

    def __init__(
        self,
        open_session: Callable[[], AbstractAsyncContextManager[AsyncSession]],
        model: type[U],
    ) -> None:
        self._open_session = open_session
        self.model = model

    async def get_by_id(self, user_id: int) -> U | None:
        async with self._open_session() as session:
            async with session.begin():
                await session.execute(text("SELECT set_config('app.is_system_mode', 'true', true)"))
                user = await session.scalar(select(self.model).where(self.model.id == user_id))
                if user is not None:
                    session.expunge(user)
            return user

    async def get_or_create_by_email(self, email: str) -> tuple[Actor[Any], bool]:
        raise NotImplementedError("SessionScopedUserDirectory only supports get_by_id")

    async def mark_email_verified(self, user: Actor[Any]) -> None:
        raise NotImplementedError("SessionScopedUserDirectory only supports get_by_id")
