"""Seed the dev database with one org, one user, and a few apps.

Idempotent: does nothing if `dev@houston.dev` already exists. Runs in a system-mode
session (`app.is_system_mode = true`, bypassing RLS) so it seeds cleanly even under a
non-superuser role. Log in as the seeded user via `just dev-backend` +
`POST /auth/magic-link/request {"email": "dev@houston.dev"}` — the magic link lands in
the backend logs (LocalEmailClient).

Run: `just seed-dev`.
"""

import asyncio

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import config
from app.domain.apps.models import App
from app.domain.organizations.models import Organization
from app.domain.users.models import User
from app.domain.users.roles import Role

DEV_EMAIL = "dev@houston.dev"

_APPS: list[tuple[str, str]] = [
    ("Aurora", "https://github.com/houston-labs/aurora"),
    ("Beacon", "https://github.com/houston-labs/beacon"),
    ("Comet", "https://github.com/houston-labs/comet"),
]


async def seed() -> None:
    engine = create_async_engine(config.ASYNC_DATABASE_URL)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessionmaker() as session, session.begin():
            await session.execute(text("SELECT set_config('app.is_system_mode', 'true', true)"))

            existing = await session.scalar(select(User).where(User.email == DEV_EMAIL))
            if existing is not None:
                print(f"seed: {DEV_EMAIL} already exists (user id={existing.id}) — nothing to do")
                return

            org = Organization(name="Houston Dev Org")
            session.add(org)
            await session.flush()

            user = User(name="Dev User", email=DEV_EMAIL, role=Role.STAFF, organization_id=org.id)
            session.add(user)

            for name, repo_url in _APPS:
                session.add(App(organization_id=org.id, name=name, repo_url=repo_url))

            await session.flush()
            print(f"seed: created org id={org.id}, user {DEV_EMAIL} id={user.id}, {len(_APPS)} apps")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
