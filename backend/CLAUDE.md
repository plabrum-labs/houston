# Backend — Claude Code Guidelines

Litestar + SQLAlchemy (async) + advanced_alchemy + msgspec. See root [CLAUDE.md](../CLAUDE.md) for shared rules.

## Hard Rules

- **Inject `transaction`, never `db_session`.** `transaction` wraps with RLS, soft-delete listener, and raiseload safety. `db_session` bypasses all three.
- **Inject `user: User` directly, don't pull it off `request`.** Litestar's auth flow resolves `User` as a normal dep wherever auth is required — including inside `@dep` providers. Reach for `request.user` or `request.scope.get("user")` only when the code legitimately runs on unauthenticated paths (rare; see `provide_transaction`).
- **Raiseload blocks lazy loads.** Relationships accessed in CRUD mappers need `lazy="noload"` + explicit `joinedload()` in the CRUD config. `lazy="joined"` on the model is overridden by session-level raiseload → silent 500s.
- **No field name shadowing in msgspec Structs.** Never name a field the same as its type import (`date: date`, `type: str`). Python 3.14 CI resolves annotations differently from 3.13 local — silent 500s on action endpoints.
- **Top-level endpoints only.** Never nested list routes. Use parent ID in `filterable_columns`; RLS handles access control.
- **State transitions through `StateMachineService` only.** Never assign `obj.state = ...` directly.
- **msgspec** (`BaseSchema(Struct)`), not Pydantic.
- **`advanced_alchemy.extensions.litestar`**, not `litestar.plugins.sqlalchemy`.

## Layering: routes / actions / models

Each domain under `app/domain/<entity>/` follows the same shape. There is **no per-domain CRUD layer** — reads come from a declarative config, writes come from actions.

**`routes.py` — reads only.**
A `CRUDConfig` + `make_crud_controller("", config)` handles GET/list/filter/sort. List and detail shapes are produced by `_to_list_item(obj, user)` and `_to_detail(obj, user)` transformer functions. No POST/PUT/DELETE here. See `app/domain/clients/routes.py` for the canonical minimal example.

**`actions.py` — all mutations.**
Create / update / delete / domain verbs (send, mark_paid, void, …) are `BaseTopLevelAction` or `BaseObjectAction` subclasses, registered via an `action_group_factory(...)` decorator. `execute()` receives `(data, transaction, deps)` and mutates models directly on the session. No separate service layer for simple CRUD-shaped actions — talk to the ORM. See `app/domain/invoices/actions.py`.

**`schemas.py` — wire types.**
msgspec `Struct` subclasses. `XxxListItem` / `XxxDetail` for output, `CreateXxxData` / `UpdateXxxData` for action input. Update schemas are declarative (all fields required, nullable fields typed `T | None`).

**`models.py` — SQLAlchemy ORM** (`BaseDBModel`).

**`enums.py` — `TextEnum` only.** Stored as TEXT, no ALTER TYPE migrations when values change.

**`state_machine.py`** — declarative states + transitions, only for domains with workflow.

### When to add a service

Default: actions call models / queries directly. **Add a `service.py` + `queries.py` only when:**
- Validation spans multiple records (e.g. uniqueness checks against derived fields)
- Logic is reused across more than one action or controller
- An action needs to call out to platform infra (LLM, email, billing) with non-trivial orchestration

Single-use validation belongs inline in the action. `app/domain/users/` is the reference for when a service is justified — don't introduce one preemptively.

### Helpers inside `actions.py`

Small pure helpers used by multiple actions in the same file (e.g. `_recalculate_totals` in invoices) live at module scope with a leading underscore. Once a helper is used outside the file or grows past ~30 lines, promote it to `service.py` / `queries.py`.

## Error Handling

**Raise typed exceptions, don't return error responses.** All HTTP errors flow through `ApplicationError` in `app/utils/exceptions.py`.

- Subclass `ApplicationError` and set `status_code` + `detail`. Define subclasses next to the code that raises them (e.g. `InboxLocalPartTakenError` lives in `app/domain/users/service.py`).
- One exception class per distinct user-facing failure mode. Don't reuse a generic `ValidationError` for unrelated conditions — the class name *is* the API contract.
- Raise from the lowest layer that knows it's an error (the query / service / action). Don't catch-and-rewrap unless you're genuinely adding context.
- The handler registered in `factory.py` converts `ApplicationError` → JSON via `exception_to_http_response`. Never construct `Response(status_code=4xx, ...)` yourself in a handler.

**Don't:**
- Raise `HTTPException` / `litestar.exceptions.*` directly from domain code — use a typed `ApplicationError` subclass so the failure mode is named.
- Log-and-swallow. If a condition is an error, raise. If it isn't, don't log it at `error`/`warning`.
- Use exceptions for control flow inside a single function. Save them for crossing layer boundaries.

**Logging vs raising:**
- Raise for anything the caller (or a user) needs to know about.
- Log at `info` for notable successful events; `warning` only for recoverable conditions you're choosing to continue past; `exception` inside an `except` block when you're handling rather than re-raising.
- f-strings in logging calls (`logger.info(f"...{var}")`), not `%`-style lazy args.

## Schemas

- **Enums:** use `TextEnum` for enum fields, not `sa.Enum()`. Stored as TEXT — no ALTER TYPE migrations when values change.
- **Update schemas are declarative.** All fields required, no `UNSET`/`UnsetType`. Fields that can be null are typed `T | None`.

## Python style

- `T | None` over `Optional[T]`
- `datetime.now(tz=timezone.utc)` not `datetime.utcnow()` (deprecated)
- 4-space indents, snake_case for modules/functions/variables, PascalCase for classes
- `from __future__ import annotations` at the top of every module
- f-strings in logging calls, not `%`-style lazy args
