from typing import Any

from alembic_utils.pg_policy import PGPolicy

from app.platform.base.models import BaseDBModel

# Global registry for RLS policies — consumed by alembic env.py
RLS_POLICY_REGISTRY: list[PGPolicy] = []

# Active scope is communicated to Postgres via session variables set by
# `provide_transaction` (requests) and `task_transaction` (jobs):
#   app.user_id          — current user
#   app.organization_id  — current user's org (used for direct column matching)
#   app.is_system_mode   — bypass for migrations and system jobs


ORG_ROOT_POLICY = """
    AS PERMISSIVE
    FOR ALL
    USING (
        NULLIF(current_setting('app.is_system_mode', true), '')::boolean IS TRUE
        OR (NULLIF(current_setting('app.organization_id', true), '') IS NOT NULL
            AND id = NULLIF(current_setting('app.organization_id', true), '')::int)
    )
"""


def org_child_policy(table: str) -> str:
    return f"""
    AS PERMISSIVE
    FOR ALL
    USING (
        NULLIF(current_setting('app.is_system_mode', true), '')::boolean IS TRUE
        OR (NULLIF(current_setting('app.organization_id', true), '') IS NOT NULL
            AND {table}.organization_id = NULLIF(current_setting('app.organization_id', true), '')::int)
    )
"""


USER_SCOPED_POLICY = """
    AS PERMISSIVE
    FOR ALL
    USING (
        NULLIF(current_setting('app.is_system_mode', true), '')::boolean IS TRUE
        OR (NULLIF(current_setting('app.user_id', true), '') IS NOT NULL
            AND user_id = NULLIF(current_setting('app.user_id', true), '')::int)
    )
"""


# ── Mixins ───────────────────────────────────────────────────────────────────


class OrgRootMixin:
    """Applied only to the top-level org-scope model (e.g. Org).

    Uses the table's own id as the scope identifier.
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        if not hasattr(cls, "__tablename__"):
            return

        tablename: str = cls.__tablename__  # type: ignore[misc]

        # Register table for RLS enablement (used by comparator)
        BaseDBModel.metadata.info.setdefault("rls", set()).add(tablename)

        RLS_POLICY_REGISTRY.append(
            PGPolicy(
                schema="public",
                signature="org_scope_policy",
                on_entity=f"public.{tablename}",
                definition=ORG_ROOT_POLICY,
            )
        )


class UserScopedMixin:
    """Applied to tables where rows belong to a single user (e.g. LLM threads).

    Does NOT add columns — the model must define its own user_id FK.
    Registers a user-scoped RLS policy: only the owning user (or system mode)
    can access rows.
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        if not hasattr(cls, "__tablename__"):
            return

        tablename: str = cls.__tablename__  # type: ignore[misc]

        BaseDBModel.metadata.info.setdefault("rls", set()).add(tablename)

        RLS_POLICY_REGISTRY.append(
            PGPolicy(
                schema="public",
                signature="user_scope_policy",
                on_entity=f"public.{tablename}",
                definition=USER_SCOPED_POLICY,
            )
        )


class OrgScopedMixin:
    """Marker mixin: registers an org-scoped RLS policy on the table.

    The model must declare its own `organization_id` column (FK to organizations.id).
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        if not hasattr(cls, "__tablename__"):
            return

        tablename: str = cls.__tablename__  # type: ignore[misc]

        BaseDBModel.metadata.info.setdefault("rls", set()).add(tablename)

        RLS_POLICY_REGISTRY.append(
            PGPolicy(
                schema="public",
                signature="org_scope_policy",
                on_entity=f"public.{tablename}",
                definition=org_child_policy(tablename),
            )
        )
