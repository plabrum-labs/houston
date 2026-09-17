"""Database fixtures — the app-owned wrappers over `app.platform.testing`.

Schema is built ONCE per session: `reset_schema` drops/recreates `public`, Alembic
migrates to head, then a non-superuser `houston_app` LOGIN role is created (so RLS
actually isolates orgs — superusers bypass it). Each test then runs inside a savepoint
via `savepoint_session` and rolls back on teardown.

`NullPool` keeps no cross-event-loop connections, so the session-scoped engine is safe
across pytest-asyncio's per-test loops.
"""

import asyncio
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.config import TestConfig
from app.domain.users.roles import Role
from app.factories import OrganizationFactory, UserFactory
from app.platform.base.soft_delete import install_soft_delete_filter
from app.platform.testing import reset_schema, savepoint_session, set_rls

# tests/fixtures/database.py -> backend/
_BACKEND_DIR = Path(__file__).resolve().parents[2]

__all__ = [
    "app_database_url",
    "db_session",
    "organization",
    "setup_database",
    "test_config",
    "test_engine",
    "transaction",
    "user",
]


def _as_app_role(url: str) -> str:
    return url.replace("postgres:postgres@", "houston_app:houston_app@")


@pytest.fixture(scope="session")
def test_config() -> TestConfig:
    cfg = TestConfig()
    install_soft_delete_filter()  # process-wide session listener — install once
    return cfg


@pytest.fixture(scope="session")
def app_database_url(test_config: TestConfig) -> str:
    return _as_app_role(test_config.ASYNC_DATABASE_URL)


async def _create_extensions(admin_url: str) -> None:
    engine = create_async_engine(admin_url, poolclass=NullPool)
    async with engine.begin() as conn:
        # SearchMixin's GIN trigram index needs pg_trgm; reset_schema dropped it.
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    await engine.dispose()


async def _grant_app_role(admin_url: str) -> None:
    engine = create_async_engine(admin_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "DO $$ BEGIN IF EXISTS (SELECT FROM pg_roles WHERE rolname='houston_app') "
                "THEN EXECUTE 'DROP OWNED BY houston_app'; END IF; END $$;"
            )
        )
        await conn.execute(text("DROP ROLE IF EXISTS houston_app"))
        await conn.execute(text("CREATE ROLE houston_app LOGIN PASSWORD 'houston_app'"))
        await conn.execute(text("GRANT USAGE ON SCHEMA public TO houston_app"))
        await conn.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO houston_app"))
        await conn.execute(text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO houston_app"))
    await engine.dispose()


@pytest.fixture(scope="session")
def setup_database(test_config: TestConfig, app_database_url: str) -> str:
    reset_schema(test_config.ADMIN_DB_URL)
    asyncio.run(_create_extensions(test_config.ADMIN_DB_URL))  # pg_trgm before migrations
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=_BACKEND_DIR,
        capture_output=True,
        text=True,
        # alembic/env.py builds its engine from `app.config.config`. The subprocess
        # inherits ENV=testing (set in conftest), so that resolves to TestConfig and
        # already targets the test-db; ADMIN_DATABASE_URL is passed as a belt-and-braces
        # override for any non-testing resolution.
        env={**os.environ, "ADMIN_DATABASE_URL": test_config.ADMIN_DB_URL},
    )
    if result.returncode != 0:
        raise RuntimeError(f"Alembic migration failed:\n{result.stderr}")
    asyncio.run(_grant_app_role(test_config.ADMIN_DB_URL))
    return app_database_url


@pytest.fixture(scope="session")
def test_engine(setup_database: str):
    return create_async_engine(setup_database, poolclass=NullPool)


@pytest.fixture
async def db_session(test_engine):
    """A savepoint-isolated, system-mode session for fixture seeding (rolls back)."""
    async with savepoint_session(test_engine) as session:
        yield session


@pytest.fixture
async def organization(db_session):
    return await OrganizationFactory.create_async(db_session, name="Acme")


@pytest.fixture
async def user(db_session, organization):
    return await UserFactory.create_async(db_session, name="Stan", organization_id=organization.id, role=Role.STAFF)


@pytest.fixture
async def transaction(db_session, user):
    """The same session, flipped from system mode to the user's RLS scope."""
    await set_rls(db_session, user_id=int(user.id), organization_id=int(user.organization_id))
    return db_session
