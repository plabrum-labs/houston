"""app.platform.testing — the reusable half of the test harness.

Ships the database-lifecycle primitives (savepoint isolation, RLS scoping, schema
reset) so domains don't re-derive them. The app-specific wiring — the engine from
`app.config`, `create_app` overrides, the polyfactory `BaseFactory` and per-model
factories — lives in `app/factories/` and `tests/` and is owned there.

SQLAlchemy-only by design (no pytest or polyfactory import) so it stays dependency-light
and usable from both the test harness and any runtime tooling.
"""

from __future__ import annotations

from app.platform.testing.db import reset_schema, savepoint_session, set_rls

__all__ = ["reset_schema", "savepoint_session", "set_rls"]
