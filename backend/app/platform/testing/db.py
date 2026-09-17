"""Universal test-database lifecycle: schema reset, savepoint isolation, RLS scoping.

The convention-owning half of a platform consumer's test harness. SQLAlchemy-only
(no pytest / polyfactory import) so it ships in the runtime wheel and updates via a
version bump — the app's `tests/fixtures/database.py` is a thin wrapper that turns
these into pytest fixtures.

`savepoint_session` is the "roll back after each test" primitive: a connection whose
outer transaction is never committed, with a `create_savepoint`-mode session bound to
it. On exit the transaction rolls back, leaving the schema clean — faster than
truncating and immune to migration-state pollution.

RLS var names (`app.user_id` / `app.organization_id` / `app.is_system_mode`) match the
runtime `app.platform.utils.deps` provider — the platform owns this convention on both paths.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool


def reset_schema(admin_url: str, schema: str = "public") -> None:
    """Drop and recreate `schema` on a sync admin connection.

    `admin_url` is a *sync* (psycopg) URL for a role that owns the schema. Run once
    per session before migrations; the GRANTs keep both the migration role and the
    app role able to use the fresh schema.
    """
    admin_engine = create_engine(admin_url, poolclass=NullPool)
    try:
        with admin_engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
            conn.execute(text(f"CREATE SCHEMA {schema}"))
            conn.execute(text(f"GRANT ALL ON SCHEMA {schema} TO postgres"))
            conn.execute(text(f"GRANT ALL ON SCHEMA {schema} TO public"))
    finally:
        admin_engine.dispose()


async def set_rls(
    session: AsyncSession,
    *,
    user_id: int | None = None,
    organization_id: int | None = None,
    system_mode: bool = False,
) -> None:
    """`SET LOCAL` the RLS session vars on an open transaction.

    System mode bypasses RLS (for fixture seeding); otherwise the user/org vars scope
    every policy. Mirrors `app.platform.utils.deps.provide_transaction`. Ints are
    interpolated (not bound) because Postgres rejects bind params in `SET LOCAL`.
    """
    if system_mode:
        await session.execute(text("SET LOCAL app.is_system_mode = true"))
        return
    await session.execute(text("SET LOCAL app.is_system_mode = false"))
    if user_id is not None:
        await session.execute(text(f"SET LOCAL app.user_id = {int(user_id)}"))
    if organization_id is not None:
        await session.execute(text(f"SET LOCAL app.organization_id = {int(organization_id)}"))


@asynccontextmanager
async def savepoint_session(
    engine: AsyncEngine,
    *,
    system_mode: bool = True,
) -> AsyncIterator[AsyncSession]:
    """A savepoint-isolated session whose outer transaction never commits.

    The connection opens a transaction, the session joins it in `create_savepoint`
    mode, and on exit the whole transaction rolls back — so a test's writes vanish
    without truncation. Defaults to `system_mode=True` so factories seed across
    tenants freely; flip per-user with `set_rls` once fixtures exist.
    """
    connection = await engine.connect()
    transaction = await connection.begin()

    if system_mode:
        await connection.execute(text("SET LOCAL app.is_system_mode = true"))

    session = async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    )()

    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
