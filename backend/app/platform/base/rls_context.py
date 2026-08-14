"""Read the RLS session variables set by `task_transaction` / `rls_transaction`.

The transaction wrappers `SET LOCAL app.organization_id` and `app.user_id` so
RLS policies evaluate against the current actor. Non-action helpers (extractor
operations, queries that need to set FK columns) read these back here instead
of plumbing the IDs through every signature.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class MissingRLSContextError(Exception):
    """Session has no organization_id / user_id set — caller is outside an RLS context."""


async def current_organization_id(transaction: AsyncSession) -> int:
    result = await transaction.execute(text("SELECT NULLIF(current_setting('app.organization_id', true), '')::int"))
    org_id = result.scalar_one_or_none()
    if org_id is None:
        raise MissingRLSContextError("app.organization_id is not set on this session")
    return int(org_id)


async def current_user_id(transaction: AsyncSession) -> int:
    result = await transaction.execute(text("SELECT NULLIF(current_setting('app.user_id', true), '')::int"))
    user_id = result.scalar_one_or_none()
    if user_id is None:
        raise MissingRLSContextError("app.user_id is not set on this session")
    return int(user_id)
