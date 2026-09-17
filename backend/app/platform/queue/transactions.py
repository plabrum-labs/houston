import asyncio
import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, cast

from litestar import Request
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import config
from app.platform.queue.enums import TaskRoleType
from app.platform.queue.exceptions import CommittableTaskError
from app.platform.queue.registry import get_registry
from app.platform.queue.types import PlatformContext


@asynccontextmanager
async def task_transaction(
    db_sessionmaker: async_sessionmaker[AsyncSession],
    role_type: TaskRoleType = TaskRoleType.SYSTEM,
    *,
    user_id: int | None = None,
) -> AsyncGenerator[AsyncSession]:
    """Async context manager that begins a transaction with RLS context.

    role_type=USER sets app.user_id (requires user_id kwarg).
    role_type=SYSTEM sets app.is_system_mode=true (bypasses RLS).

    Commits on success or on CommittableTaskError (then re-raises).
    Rolls back on all other exceptions.
    """
    async with db_sessionmaker() as session:
        await session.begin()
        try:
            if role_type == TaskRoleType.USER:
                if user_id is None:
                    raise ValueError("user_id is required for TaskRoleType.USER")
                # Bypass RLS briefly so we can resolve the user's org for scoping.
                await session.execute(text("SET LOCAL app.is_system_mode = true"))
                org_id_row = (
                    await session.execute(
                        text("SELECT organization_id FROM users WHERE id = :uid"),
                        {"uid": user_id},
                    )
                ).scalar_one_or_none()
                if org_id_row is None:
                    raise ValueError(f"User {user_id} not found")
                await session.execute(text("SET LOCAL app.is_system_mode = false"))
                # SET LOCAL's grammar only accepts a literal, not a bind param (Postgres
                # rejects `SET LOCAL x = $1` at parse time) — must interpolate, so cast to
                # int first (user_id/org_id_row may be a Sqid, an int subclass whose
                # __str__ renders the encoded string, not the digits).
                await session.execute(text(f"SET LOCAL app.user_id = {int(user_id)}"))
                await session.execute(text(f"SET LOCAL app.organization_id = {int(org_id_row)}"))
            else:
                await session.execute(text("SET LOCAL app.is_system_mode = true"))

            yield session
            await session.commit()
        except CommittableTaskError:
            await session.commit()
            raise
        except Exception:
            await session.rollback()
            raise


def with_transaction(
    fn: Callable[..., Any] | None = None,
    *,
    role_type: TaskRoleType = TaskRoleType.SYSTEM,
) -> Callable[..., Any]:
    """Decorator that injects `transaction: AsyncSession` as a keyword argument.

    Args:
        role_type: RLS context for the transaction (default: SYSTEM).
            SYSTEM bypasses RLS. USER requires `user_id` in task kwargs.

    If `transaction` is already present in kwargs (e.g. passed by dispatch_task in
    sync mode), the function is called directly — the caller owns the session lifecycle.

    Usage:
        @with_transaction                              # SYSTEM (default)
        @with_transaction(role_type=TaskRoleType.USER)  # USER — reads user_id from kwargs
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(ctx: Any, **kwargs: Any) -> Any:
            if "transaction" in kwargs:
                return await func(ctx, **kwargs)
            user_id = kwargs.get("user_id") if role_type == TaskRoleType.USER else None
            async with task_transaction(ctx["db_sessionmaker"], role_type, user_id=user_id) as session:
                return await func(ctx, transaction=session, **kwargs)

        return wrapper

    # Support both @with_transaction and @with_transaction(role_type=...)
    if fn is not None:
        return decorator(fn)
    return decorator


async def dispatch_task(
    transaction: AsyncSession,
    request: Request,
    task_name: str,
    *,
    queue: str = "default",
    **kwargs: Any,
) -> None:
    """Dispatch a task either inline (QUEUE_SYNC=true) or via the SAQ queue.

    In sync mode the task runs immediately, reusing the caller's session so no
    extra DB connection or commit is needed. If the task raises, the exception
    propagates and the outer transaction rolls back.

    In async mode the task is enqueued after the session commits.

    Sync mode's inline `ctx` only carries `config` — none of the client keys a
    real worker's startup hook would populate. A task declaring a typed client
    kwarg (`@task`'s DI pulls it from `ctx`) must have that client passed
    explicitly here via `**kwargs` instead — the caller already has it from its
    own route DI, and an explicit kwarg always wins over `@task`'s ctx lookup.
    """
    if config.QUEUE_SYNC:
        fn = get_registry().get_task_by_name(task_name)
        if fn is None:
            raise ValueError(f"No task registered for {task_name!r}")
        ctx = cast(PlatformContext, {"config": config})
        await fn(ctx, transaction=transaction, **kwargs)
    else:

        async def _enqueue() -> None:
            try:
                await request.app.state.task_queues.get(queue).enqueue(task_name, **kwargs)
            except Exception:
                logging.getLogger(__name__).exception("Failed to enqueue task %s", task_name)

        def _listener(_session: Any) -> None:
            asyncio.ensure_future(_enqueue())

        event.listen(transaction.sync_session, "after_commit", _listener, once=True)
