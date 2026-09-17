# Houston — Claude Code Guidelines

Houston is a platform built on the inlined snacks stack: a Litestar + async
SQLAlchemy backend with per-tenant RLS. Area-specific rules live alongside the
code and auto-load when you work there:

- Backend (`backend/`) — see [backend/CLAUDE.md](backend/CLAUDE.md)
- Infra & CI/CD (`infra/`) — see [infra/CLAUDE.md](infra/CLAUDE.md)
- Design record (`docs/`) — see [docs/CLAUDE.md](docs/CLAUDE.md)

The rules below apply everywhere.

## Code philosophy

- **No defensive coding.** Belt-and-suspenders, defense-in-depth at the function level, "just in case" guards — these are anti-patterns, not virtues. Trust your callers and your types. Validate at real boundaries (HTTP input, external APIs, deserialization) and nowhere else.
- **`try` / `except` only when you have a real action to take in the failure case** (retry, fall back to a known value, translate to a typed error, clean up a resource). Wrapping code in `try` to log-and-continue or to "be safe" is worse than letting it crash — it hides bugs and produces silently wrong state.
- **Avoid nullable code.** A pure, non-null-returning function is always preferable to one that returns `T | None`. Null checks scattered through call sites are hard to read and breed off-by-one bugs. If a value is required, type it as required; if it's genuinely optional, narrow it once at the edge.
- **No stringly-typed code.** No `getattr` / `setattr` / `hasattr` with string keys to dodge the type system. No magic strings standing in for enums. If you reach for these, the model is wrong — fix the model.
- **No lazy imports.** Imports go at the top of the file. If you're using a lazy import to break a cycle, the cycle is the bug — fix the module boundary.
- **No `# type: ignore`.** If the type checker is wrong, fix the types. If it's right, fix the code. Suppressions rot and accumulate.

## Control flow & types

The `python-styleguide` skill carries the full guide (typing, dataclasses vs pydantic, pure functions, no nested functions). The load-bearing rules for readable code:

- **`match` / `case` for multi-branch dispatch** on an enum's variants or a value's shape — not an `if` / `elif` chain. Every branch returns explicitly, and exhaustiveness should be visible at a glance.
- **Enums for closed sets** — statuses, modes, kinds, categories. Never bare string literals compared against constants. If a value is being checked against a fixed set of strings, it's an enum.
- **No `while` loops.** Express iteration with `for`, comprehensions, or generators. A `while` is usually a sign the termination condition should be an explicit iterable or a bounded range.
- **Keep control flow flat and forward.** Prefer early returns to nested branches; keep the happy path at the lowest indentation.

## Comments

**Keep a comment when:**
- The code does something surprising or counter-intuitive
- There's a constraint not visible in the code (a workaround for an external bug, a compliance requirement, a performance trap) — state the constraint concretely
- A TODO has a genuine open question or domain decision still pending

**Delete a comment when:**
- It restates what the function or class name already says
- It labels a block of code that does exactly what it says (`# Search`, `# Paginate`)
- It's a decorative section header (`# ─── Section ───`)
- It explains *what* the code does rather than *why*

**Never track decisions in comments.** No decision ledger, no citations to one — `# Follows from D29`, `# per the auth RFC`, `# decided in the Q3 sync`. Code describes what is, not the paper trail that produced it. If a past decision left a real constraint, state the constraint itself; the citation is noise.

**Docstrings:**
- Public API methods: include only if they explain params or non-obvious behavior, not if they repeat the name
- Internal helpers and guards: usually no docstring needed; the name should be enough
- Exception classes: skip the docstring unless the semantics are subtle

## Language

Write plainly and concretely, in comments, docstrings, and docs alike. Describe what the code or system actually does — the real mechanism and the real behavior.

Avoid the abstract-architecture register: "decisions," "seams," "gates," and the like, reached for when a concrete description would do. That vocabulary sounds like structure without carrying any, and it reads as filler. If you can't name the concrete thing, you don't understand it yet — so name the thing.
