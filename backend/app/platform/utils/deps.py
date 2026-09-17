"""Dependency registry for Litestar DI.

Decorate provider functions with @dep("key") to register them.
In factory.py, call discover_and_import(["deps.py"]) then get_dependencies().

Example:
    @dep("my_service")
    def provide_my_service(transaction: AsyncSession) -> MyService:
        return MyService(transaction)
"""

import inspect
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

from litestar import Request
from litestar.di import Provide
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_registry: dict[str, Provide] = {}


def dep(name: str, *, sync_to_thread: bool = False) -> Callable:
    """Register a provider function as a named Litestar dependency."""

    def decorator(fn: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn)
        _registry[name] = Provide(fn) if is_async else Provide(fn, sync_to_thread=sync_to_thread)
        return fn

    return decorator


def get_dependencies() -> dict[str, Any]:
    return dict(_registry)


@dep("transaction")
async def provide_transaction(db_session: AsyncSession, request: Request) -> AsyncGenerator[AsyncSession]:
    """Provide a database transaction with `app.user_id` and `app.organization_id` set so RLS policies evaluate."""
    async with db_session.begin():
        if request.scope.get("user") is not None:
            user_id = int(request.user.id)
            organization_id = int(request.user.organization_id)
            await db_session.execute(text(f"SET LOCAL app.user_id = {user_id}"))
            await db_session.execute(text(f"SET LOCAL app.organization_id = {organization_id}"))
        yield db_session


@asynccontextmanager
async def rls_transaction(
    db_session: AsyncSession, *, user_id: int, organization_id: int
) -> AsyncGenerator[AsyncSession]:
    """Short-lived RLS-scoped transaction for long-running handlers (e.g. WebSockets).

    The request-scoped `transaction` dep wraps the entire request in a single
    `db_session.begin()` context. WS handlers run for minutes and would either
    hold one transaction open the whole time or break that context manager by
    committing inside. Use this helper to wrap each unit of work in its own
    short-lived transaction with RLS variables set.
    """
    async with db_session.begin():
        await db_session.execute(text(f"SET LOCAL app.user_id = {int(user_id)}"))
        await db_session.execute(text(f"SET LOCAL app.organization_id = {int(organization_id)}"))
        yield db_session
