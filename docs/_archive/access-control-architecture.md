# Access control architecture

Status: **early design** — captures where a working conversation landed, not a spec to build against yet. Extends the RLS/data-model decisions in `many-backends-architecture.md` and the tool-surface/agent decisions in `app-model-and-agents.md`; this doc is the dedicated home for access-control questions so they don't keep getting bolted onto those two ad hoc.

## Problem statement

A vertical app on Houston has more than one axis of "who can see this row," and they need to compose without each new axis adding bespoke SQL predicate logic to every table:

1. **Tenant isolation** — a customer org can only see its own org's rows within an app's schema. Already settled (`many-backends-architecture.md`): `organization_id` column + RLS policy against a per-transaction session variable.
2. **Operator-private data** — the vertical-app builder (the "tenant" selling the SaaS app, e.g. `arive` as a company) may have proprietary tables (pricing models, internal formulas, cost data) that must be invisible to *every* customer org, not just other orgs' rows.
3. **Dynamic, per-object sharing** (Google-Docs-style) — a specific record shared with a specific user or group, decided at runtime by an end user, independent of org membership.

The design goal is to keep (1) — the overwhelming majority case — exactly as fast and simple as it already is, and treat (2) and (3) as narrow, opt-in extensions rather than generalizing everything into one heavier mechanism that taxes every table.

## Base case: org-scoped tenant isolation (settled, unchanged)

This is the default and the only mechanism most tables ever need. No change from `many-backends-architecture.md`:

```sql
USING (organization_id = current_setting('app.organization_id')::uuid)
```

- Single indexed equality check against a per-transaction session variable — O(1) per row, no joins, no function calls.
- Every table gets this and nothing else unless it explicitly needs one of the extensions below.
- **Priority ordering, explicit**: the base case must never be made slower or more complex in service of the extensions below. Those are additive to specific tables that opt in, not defaults every table inherits.

## Operator-private tables (settled)

Tables the vertical-app operator (e.g. `arive` the company) owns but no customer org should ever see — proprietary formulas, internal cost data, etc. Same mechanism as tenant isolation, different session variable, no new machinery:

```sql
USING (current_setting('app.actor_type') = 'operator')
```

- Deny-by-default to any customer-scoped session, regardless of the app's own Go code — a careless handler that joins in proprietary data still gets zero rows back, because Postgres enforces it, not application code discipline.
- **Every table needs an explicit RLS posture** — "operator-only" must be a real, deliberately-written policy, not just the absence of an `organization_id` column. A table with no policy at all risks being readable by whichever role happens to have a grant on it.
- Rejected alternative: generating two separate `ent` clients (customer-scoped vs. operator-scoped) to prevent this at the Go type level instead of the DB level. Rejected because it duplicates enforcement in two places (RLS *and* the type system) instead of trusting the one boundary (Postgres) that already can't be bypassed by buggy app code.

## Dynamic per-object sharing (designed, not yet built)

Deliberately **not implemented for v1** — sharing is not expected to be a common pattern across vertical apps, so this section documents the design for whenever a specific app's table actually needs it, rather than building speculative infra every app schema carries whether it's used or not.

### Why not more RLS predicates

Naively extending RLS with one more bespoke predicate per new access pattern (org isolation, operator-only, now per-object sharing, and whatever comes after) accumulates unmanageable per-table SQL logic. The better fit, closer to how Google Docs and Foundry's ACL layer actually work, is **relationship-based access control** (Zanzibar-style): permissions as data — tuples of `(object, relation, subject)` — resolved by a query, not encoded as growing SQL predicates.

### Why not a standalone authz service

A separate authz service (OpenFGA, Ory Keto) checked from application code would reopen the exact problem operator-only tables just closed: the DB stops being a backstop if a handler forgets to call the check. To keep the "leak-proof even against buggy code" property, the relationship data must be resolved **inside** the RLS policy itself, not from Go code.

### Why not a naive resolver function in the policy

A plpgsql function called from `USING` is a black box to the query planner — it can't be combined with an index scan, so Postgres tends to fall back to scanning every row and calling the function per row. Worse when OR'd with the org-scoped condition (`organization_id = X OR has_access(...)`), since Postgres generally can't cleanly index across two unrelated disjuncts unless both sides are independently indexable.

### Why not naive full flattening either

An earlier version of this design proposed flattening resolved access into `(object_id, subject_id)` pairs — one row per user who can see each object. Rejected: a single broad grant (share with a 1,000-person group) would write 1,000 rows for one sharing action, and the table's size would scale with **reach** of grants (org size, group size) rather than the **number of grants**, which is the wrong growth curve.

### Landed design

- **Source of truth**, platform-schema-owned (subjects — users, groups, orgs — are shared identity, same reasoning as why `users`/`organizations` are platform-owned):

  ```sql
  platform.relationship_tuples (object_type, object_id, relation, subject_type, subject_id)
  ```

  `object_type` namespaced per app (`'arive.record'`) so object IDs don't collide across apps sharing one tuples table.

- **Grants-only flattening**, not pairs — subject stays a `user` or a `group` reference, never expanded to individual members:

  ```sql
  platform.effective_access (object_type, object_id, subject_type, subject_id)
  ```

  A group grant is one row regardless of group size. A maintenance trigger on `relationship_tuples` keeps this materialized for *computed* relations only (e.g. "editor implies viewer" becomes an explicit `viewer` row) — it does not expand group membership, so this table's size scales with the number of sharing actions taken, not their reach.

- **RLS policy on an opted-in table**, additive to the org-scoped default:

  ```sql
  USING (
    organization_id = current_setting('app.organization_id')::uuid
    OR EXISTS (
      SELECT 1 FROM platform.effective_access ea
      WHERE ea.object_type = 'arive.record' AND ea.object_id = id::text
        AND (
          (ea.subject_type = 'user' AND ea.subject_id = current_setting('app.actor_id')::uuid)
          OR (ea.subject_type = 'group' AND ea.subject_id = ANY(current_actor_groups()))
        )
    )
  )
  ```

  `current_actor_groups()` resolves the *actor's own* small group membership set (someone belongs to a handful of groups, not thousands) — expansion happens on the small side of the join, never the large side.

- **Performance property**: both disjuncts are independently indexable (`organization_id` equality; `effective_access` on `(object_type, object_id)`), so Postgres can plan this as a `BitmapOr` of two index scans rather than a per-row function evaluation or full scan. Opting a table into sharing does not degrade that table's org-scoped queries.
- **Consistency**: the maintenance trigger runs synchronously, in the same transaction as the tuple write — avoids the eventual-consistency window (a revoked share briefly still visible, or a new share not yet visible) that an async fan-out job would introduce. Revisit only if group-membership churn at scale makes synchronous maintenance a bottleneck — not a concern at the currently-scoped single level of group expansion.
- **Scope cut for whenever this is built**: one level of group expansion only (subject is a user, or "any member of group G"). No recursive/nested-group userset rewriting — that's where Zanzibar's own engineering cost concentrates (a dedicated, heavily cached graph-index service), not worth taking on without a concrete need for nested groups.
- **Grants, matching the existing platform-schema access pattern**: `_runtime` roles get read-only access to `relationship_tuples`/`effective_access`, same as they already do for `users`/`organizations`. Writing a tuple (a "share" action) goes through a houston API/service call, not a direct cross-schema write — same rule already governing writes to platform data.

## Open questions

- No concrete app has needed dynamic sharing yet — the design above stays undocumented-and-unbuilt until one does. Revisit scope (recursive groups, async flattening) only against a real requirement, not speculatively.
- Revocation path: removing someone from a group currently relies on `current_actor_groups()` being resolved live per request (not materialized), so revocation is immediate without touching `effective_access` rows — confirm this holds once the mechanism is actually implemented against a real table.
- Whether `relationship_tuples`/`effective_access` should be exposed through the agent tool-surface model from `app-model-and-agents.md` at all (e.g., can the bundled agent see/modify shares?) — not yet considered.
