"""Alembic environment — houston metadata + RLS policy autogeneration.

Migrations span both owners: every platform subsystem's tables (events, queue,
state-transition logs, users, sequences, …) AND this app's concrete tables
(`app.domain.*`), plus the RLS policies emitted via alembic-utils from
the platform's `RLS_POLICY_REGISTRY`. All model modules are auto-discovered so they
populate `BaseDBModel.metadata` before autogenerate reads it.
"""

from logging.config import fileConfig
from pathlib import Path

from alembic.autogenerate import comparators
from alembic.operations.ops import CreateTableOp, MigrateOperation, MigrationScript, UpgradeOps
from alembic.runtime.migration import MigrationContext
from alembic_utils.pg_policy import PGPolicy as PGPolicyType
from alembic_utils.replaceable_entity import register_entities
from alembic_utils.reversible_op import CreateOp
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Connection
from sqlalchemy.types import TypeDecorator

import app
from alembic import context
from app.config import config as app_config
from app.platform.base.models import BaseDBModel
from app.platform.base.rls_comparator import compare_rls
from app.platform.base.rls_mixins import RLS_POLICY_REGISTRY
from app.platform.base.rls_operations import EnableRLSOp
from app.platform.utils.discovery import discover_and_import

# Discover every model module so all tables register on BaseDBModel.metadata before
# autogenerate reads it — platform subsystems + this app's own models + app/domain/*.
discover_and_import(["models.py", "models/**/*.py"], search_root=Path(app.__file__).parent)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = BaseDBModel.metadata
database_url = app_config.ADMIN_DB_URL


def _policy_table(policy: PGPolicyType) -> str:
    """Bare name of the table a policy applies to (`public.orders` -> `orders`)."""
    return policy.on_entity.split(".")[-1]


def _tables_in_database() -> set[str]:
    """Tables that already exist in the target database (empty if it is unreachable)."""
    try:
        engine = create_engine(database_url)
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        engine.dispose()
    except Exception:
        return set()
    return existing_tables


# alembic-utils detects policy changes by *executing* the policy's CREATE against the
# live database (inside a rolled-back transaction), so registering a policy whose table
# does not exist yet aborts autogenerate. Hence the filter — policies for tables that
# *this* revision creates are appended by the `process_revision_directives` hook below.
_EXISTING_TABLES = _tables_in_database()
register_entities(
    [p for p in RLS_POLICY_REGISTRY if _policy_table(p) in _EXISTING_TABLES],
    entity_types=[PGPolicyType],
)
comparators.dispatch_for("table")(compare_rls)


def _rls_ops_for_new_tables(upgrade_ops: UpgradeOps) -> list[MigrateOperation]:
    """RLS ops for the tables this revision creates, in create_table order."""
    rls_tables: set[str] = target_metadata.info.get("rls", set())
    new_ops: list[MigrateOperation] = []
    for op in upgrade_ops.ops:
        if not isinstance(op, CreateTableOp) or op.table_name not in rls_tables:
            continue
        new_ops.append(EnableRLSOp(op.schema or "public", op.table_name, force=True))
        new_ops.extend(CreateOp(p) for p in RLS_POLICY_REGISTRY if _policy_table(p) == op.table_name)
    return new_ops


def process_revision_directives(
    context_: MigrationContext,
    revision: str | tuple[str, ...] | None,
    directives: list[MigrationScript],
) -> None:
    """Append the new tables' RLS ops to the revision alembic is about to write."""
    for script in directives:
        upgrade_ops = script.upgrade_ops
        if upgrade_ops is None:
            continue
        new_ops = _rls_ops_for_new_tables(upgrade_ops)
        if not new_ops:
            continue
        upgrade_ops.ops.extend(new_ops)
        downgrade_ops = script.downgrade_ops
        if downgrade_ops is not None:
            for new_op in new_ops:
                downgrade_ops.ops.insert(0, new_op.reverse())


def include_object(object, name, type_, reflected, compare_to):
    """Exclude SAQ's own tables from autogenerate."""
    if type_ == "table" and name.startswith("saq_"):
        return False
    return True


def render_item(type_: str, obj: object, autogen_context: object) -> str | bool:
    """Render houston's custom column types in migration files."""
    if type_ == "type":
        class_name = obj.__class__.__name__
        if class_name == "Vector":
            autogen_context.imports.add("from pgvector.sqlalchemy import Vector")  # type: ignore[union-attr]
            dim = getattr(obj, "dim", None)
            return f"Vector({dim})" if dim is not None else "Vector()"
        if isinstance(obj, TypeDecorator):
            if class_name == "SqidType":
                autogen_context.imports.add("from app.platform.utils.sqids import SqidType")  # type: ignore[union-attr]
                return "SqidType()"
            if class_name == "TextEnum":
                autogen_context.imports.add("from app.platform.utils.textenum import TextEnum")  # type: ignore[union-attr]
                enum_cls = obj.enum_class  # type: ignore[attr-defined]
                autogen_context.imports.add(  # type: ignore[union-attr]
                    f"from {enum_cls.__module__} import {enum_cls.__qualname__}"
                )
                return f"TextEnum({enum_cls.__qualname__})"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        render_item=render_item,  # type: ignore[arg-type]
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        render_item=render_item,  # type: ignore[arg-type]
        process_revision_directives=process_revision_directives,  # type: ignore[arg-type]
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(database_url)
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
