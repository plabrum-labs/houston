# Convex

**What it is:** A reactive application database where all client access goes through typed server functions (queries/mutations/actions) rather than a client-exposed database + row policies.
**Axis:** semantic layer, deploy/migration, agent, enterprise governance (permissions as code, not policy).
**Depth:** medium — Convex docs, `stack.convex.dev` engineering blog, and `convex-helpers` GitHub source; no independent load-testing of the retry/OCC claims.

## Products & surfaces

| Product | What it is |
|---|---|
| **Queries / Mutations / Actions** | The three function types — Convex's type system for side effects (below). |
| **Scheduler** | `ctx.scheduler.runAfter`/`runAt`, jobs stored as rows in `_scheduled_functions`. |
| **Components** | Installable, isolated sub-apps with their own DB/functions/scheduler/storage. |
| **Migrations component** | Batched, checkpointed, resumable data migrations as a first-class package. |
| **File Storage** | `ctx.storage`, URL-based file serving. |
| **Preview Deployments** | Ephemeral per-branch deployments created by the same CLI command as production deploys. |
| **convex-helpers** | Community/first-party helper package including an RLS wrapper and DB triggers. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Query/mutation/action split | A type system for side effects: purity, determinism, and retry semantics vary by function kind | yes |
| Mutations are exactly-once + auto-retried | Purity buys free retries — safe to retry a transaction that never touched the outside world | yes |
| Actions are at-most-once, never retried | Anything that calls `fetch` (Stripe, email) doesn't get silently re-run | yes |
| Transactional scheduling | A scheduled function is part of the mutation's transaction — both commit or neither does | yes |
| No query planner | TypeScript types force correct index usage; unindexed access is a compile-time constraint | yes |
| Staged indexes | Async index backfill that doesn't block deploy | yes |
| Push-time schema validation | New schema pushes are validated against every existing document before being accepted | yes |
| Migrations component | Batched, checkpointed, resumable, idempotent data migrations, queryable in realtime | yes |
| Components | Installable sub-apps with platform-enforced isolation (can't read your tables unless you pass them in) | yes |
| Preview deployments | Same `convex deploy` command deploys prod or preview, branch-name-derived, seeded by a typed function | yes |
| `storage.getUrl()` | Mints a URL anyone holding it can use; only revocation is deleting the file | no (cautionary) |
| RLS-as-tax argument | Convex's stated case against exposing the DB to the client at all | see below |

## Worth stealing

### The query/mutation/action split as a type system for side effects

- **Query**: read-only, no `fetch`, deterministic, cacheable and subscribable (this is what makes reactivity possible — a deterministic read can be safely re-run and diffed).
- **Mutation**: read/write, transactional, deterministic, **exactly-once** — network retries are safe and automatic because the function has no side effects Convex doesn't control.
- **Action**: the only function kind that can call `fetch`/talk to the outside world; can only touch the database via `runQuery`/`runMutation`; non-deterministic; **at-most-once, never auto-retried**.

Convex's stated justification: **"purity buys free retries."** Their own example — a mutation that calls Stripe is dangerous because Convex "can simply re-run the transaction" on conflict, and a naive mutation would "charge money to Stripe" twice; routing the Stripe call through an action (at-most-once) and confining the transactional/retryable part to a mutation is what makes the retry safe. The type system is doing correctness work most stacks push onto developer discipline (idempotency keys, careful retry logic) — here it's structurally impossible to accidentally double-charge from a mutation, because mutations can't reach `fetch` at all.

### Transactional scheduling

`ctx.scheduler.runAfter()` called inside a mutation is **part of that mutation's transaction**: *"If the mutation succeeds, the scheduled function is guaranteed to be scheduled... if the mutation fails, no function will be scheduled,"* even if the failure happens after the scheduling call. Scheduled jobs are ordinary rows in the `_scheduled_functions` system table — introspectable, cancellable, queryable like any other data, not a black-box queue. Scheduling from an *action* has no such guarantee, since actions aren't transactional — this is a direct, load-bearing consequence of the query/mutation/action split above, not a separate feature bolted on.

### No query planner — the type system walks you to the right index

Convex doesn't have a cost-based query planner. Cited justification: "many outages at companies with millions of customers were the result of a query doing a scan instead of an index." Instead, `withIndex()` calls are typed against the schema's declared index field order — the TypeScript compiler requires you to constrain index fields in the declared order (e.g., an index on `["author", "title"]` requires `.eq("author", ...)` before you can constrain `title`). You cannot combine two `.withIndex()` calls or two `.order()` calls on one query. An unindexed table scan is still possible (default behavior on an unconstrained query) but is opt-in and visible in the code, not a planner's silent fallback decision.

**Staged indexes** decouple index creation from deploy blocking: `staged: true` on a new index lets it backfill asynchronously while further pushes continue, with progress visible on the dashboard; the index can't be used in queries until backfill finishes and the `staged` flag is removed.

**Push-time schema validation**: the first push after adding/changing a schema validates every existing document against the new shape and **rejects the push** if any document fails — schema drift is caught at deploy time, not discovered later as a runtime type error.

### Migrations component — checkpointed, resumable, idempotent

`@convex-dev/migrations` processes data in configurable batches to stay within function execution limits, **"automatically saves progress after each batch and resumes from the last checkpoint"** on timeout, and tracks migration state explicitly so it "can avoid running twice, pick up where it left off... in the case of a bug or failure along the way." Per-record success/failure is logged, so partial failures don't require reprocessing everything — you can retry just the failed subset. Progress (records processed, remaining, estimated completion) is exposed live via ordinary Convex queries, not a separate migration-status system.

### Components — platform-enforced isolation, not convention

A Component is described as *"a self-contained Convex app that runs inside your Convex app with its own database, functions, scheduler, and storage."* The calling boundary is one-directional and **enforced by the platform**: a component cannot read the host app's tables or call the host app's functions unless the host explicitly passes data in. Convex's own framing: this lets you "confidently install third-party components without worrying about them reading your user data" — the isolation guarantee doesn't depend on the component author writing well-behaved code.

### Preview deployments — same command, branch-derived, typed seeding

`npx convex deploy` detects CI context and **derives the preview deployment name from the git branch automatically** when a *preview* deploy key is set — the exact same CLI invocation deploys to production or to a preview environment, switching purely on which deploy key is configured, not on a different command or flag set. `--preview-create` recreates a fresh preview each time rather than reusing one; `--preview-name` names it explicitly. `--preview-run=<functionName>` seeds the new preview by **running a typed Convex function you already wrote** — not a `seed.sql` file that can drift from the schema, since the seeding code is checked by the same compiler as the rest of the app. Auto-expiry: 5 days on the free plan, 14 days on paid plans.

### The RLS-as-tax argument

Convex's engineering blog ("Row-Level Security is a Ticking Timebomb") argues RLS is a workaround for a prior architectural choice: *"The root problem is that we're exposing the database to the client, then patching that exposure with row-level rules."* Because every Convex data access goes through a server function, "authorization logic and application logic can live in the same place, in the same language" — no separate policy DSL evaluated inside the database. Whether this generalizes depends on whether the app in question needs client-direct queries at all — it's a real trade-off, not a strict improvement, since it forecloses ad-hoc client-side querying entirely.

## Worth avoiding

### The RLS-optional pitch has its own escape hatches

Convex's own `convex-helpers` package ships an RLS-style wrapper (`queryWithRLS`/`mutationWithRLS`) for teams that want row-level rules anyway — and the package's own documentation concedes real gaps: **"if you forget to use the wrapper, the triggers won't run (use eslint rules)"** — i.e., the enforcement mechanism is an opt-in function wrapper backed by a *lint rule* reminding you to opt in, not something the platform makes structurally unavoidable the way Components' isolation is. The recommended mitigation is literally an ESLint `no-restricted-imports` rule blocking the raw `mutation`/`internalMutation` imports so only the wrapped versions are reachable — a convention with a linter guardrail, the same category of protection Convex's core sales pitch (server-function-only access) is supposed to make unnecessary. The wrapper is also **bypassed entirely by dashboard-initiated edits and `npx convex import`**, which write directly without going through any application-level wrapper.

### `storage.getUrl()` is capability-by-URL with no revocation short of deletion

Convex's own docs: **"anyone with the URL can access the file"** — there's no per-request authorization check once a URL has been minted, and the SDK gives no way to expire or invalidate a specific URL. The only revocation path is deleting the underlying file object, after which existing URLs 404. If access needs to change over time short of full deletion (e.g., "this user no longer has access"), Convex's own guidance is to route file serving through an **HTTP action that checks permissions before returning bytes** instead of using `getUrl()` — i.e., the fast path is capability-URL-shaped and insecure-by-default for anything requiring revocable access, and the safe path requires opting out of the storage feature's main convenience.

## Facts & figures

- Preview deployment auto-expiry: 5 days (free plan) / 14 days (Professional, Business, Enterprise) — vendor-reported.
- Migrations component batches configurable; exact default batch size not confirmed in public docs excerpted here.

## Sources

- [Actions](https://docs.convex.dev/functions/actions) · [Mutations](https://docs.convex.dev/functions/mutation-functions) · [Automatically Retry Actions](https://stack.convex.dev/retry-actions)
- [Scheduled Functions](https://docs.convex.dev/scheduling/scheduled-functions) · [Scheduling](https://docs.convex.dev/scheduling)
- [Indexes](https://docs.convex.dev/database/reading-data/indexes/) · [Introduction to Indexes and Query Performance](https://docs.convex.dev/database/reading-data/indexes/indexes-and-query-perf) · [Queries that scale](https://stack.convex.dev/queries-that-scale)
- [Migrations component](https://www.convex.dev/components/migrations) · [get-convex/migrations on GitHub](https://github.com/get-convex/migrations) · [Stateful Online Migrations using Mutations](https://stack.convex.dev/migrating-data-with-mutations)
- [Components docs](https://docs.convex.dev/components) · [Authoring Components](https://docs.convex.dev/components/authoring)
- [Working with Multiple Deployments (Preview Deployments)](https://docs.convex.dev/production/hosting/preview-deployments) · [npx convex deploy CLI reference](https://docs.convex.dev/cli/reference/deploy)
- [File Storage](https://docs.convex.dev/file-storage) · [Serving Files](https://docs.convex.dev/file-storage/serve-files)
- [Row-Level Security is a Ticking Timebomb](https://stack.convex.dev/why-convex-doesnt-need-row-level-security)
- [convex-helpers README (RLS/triggers, eslint guardrail)](https://github.com/get-convex/convex-helpers/blob/main/packages/convex-helpers/README.md) · [Database Triggers](https://stack.convex.dev/triggers) · [ESLint rules](https://docs.convex.dev/eslint)
- **Not directly verified:** the precise phrase "a tax paid by client-oriented databases like Firebase or Supabase" was not found verbatim in the fetched Ticking Timebomb article — the underlying argument (exposing the DB then patching with row rules) is directly quoted/sourced above, but treat the exact wording in this file's framing as paraphrase, not a verified direct quote.
