# Quiver equivalent: agent-authored analysis DSL

Status: **early direction, actively evolving** — captures a decision made in conversation, ahead of design detail. Expect this doc to change shape once the semantic object layer DSL (below) gets designed.

## What Quiver does in Foundry

Point-and-click, no-code interface for object and time-series analysis over the Ontology — chainable "cards" (filter, join, derive, chart), no manual joins since links are native to the Ontology, results embeddable as dashboards. Contour covers the same territory for large-scale tabular aggregation specifically. See `docs/platforms/README.md` for the full mapping.

## Houston's direction: no GUI, an agent-written DSL instead

Decision: Houston does not build a point-and-click analysis GUI. Instead, the bundled agent (`app-model-and-agents.md`) writes and executes a DSL against an app's data — the analysis surface is conversational/agent-driven, not direct-manipulation.

This is consistent with the app-building model already settled elsewhere in these docs: prefer "an agent writes ergonomic code/queries for you" over "a separate no-code product with its own learning curve and its own drift risk from the code-first path." Same reasoning that killed the idea of a standalone app-building DSL applies here.

Mechanically, this composes with what's already designed rather than replacing it:

- The agent queries the core DB through the existing RLS-scoped path (`app-model-and-agents.md`, async agent tasks section) — no new data-access mechanism.
- Results land in the same per-task DuckDB workspace already designed for the bundled agent's background analysis tasks.
- Contour's "large-scale tabular aggregation" niche and Quiver's "object/time-series, ontology-aware" niche both collapse into this one mechanism in Houston — there's no separate tool to choose between, see `docs/platforms/README.md`'s "notable collapses" section.

## Open thread: the semantic object layer DSL (datafusion adapter)

Flagged as a future design, not yet specified: this analysis DSL is expected to eventually mesh with a **semantic object layer DSL** built on a DataFusion adapter. Not yet designed — captured here as a forward reference so it isn't lost, to be expanded when that thread gets picked up.

## Open questions

- What does the DSL itself look like — closer to SQL, closer to a query-builder API the agent calls as tools, or something else? Not yet decided.
- Does a human ever interact with this DSL directly (e.g., reviewing/editing what the agent wrote before it runs), or is it strictly agent-authored and agent-executed end to end?
- How this DSL relates to the semantic object layer DSL once that's designed — same language, or the object-layer DSL compiles into this one?
