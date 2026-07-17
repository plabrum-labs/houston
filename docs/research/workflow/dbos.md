# DBOS

**What it is:** A **library, not a service** — durable workflow execution embedded in your own application process, checkpointing state directly into the Postgres you already run.
**Axis:** workflow.
**Depth:** deep.

## Products & surfaces

| Product | What it is |
|---|---|
| **DBOS Transact** | The open-source library (Python, TypeScript, Go, Java) — register functions as workflows/steps, run in-process. |
| **`dbos-transact-golang`** | The Go SDK — `dbos.RunAsStep()` wraps a function as a durable step. |
| **DBOS Cloud / Conductor** | Optional hosted layer for observability, deployment, autoscaling on top of the same library. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Library, not server | No separate orchestration cluster; workflows run inside your app process | yes |
| Step + checkpoint in one Postgres transaction | Exactly-once step execution by piggybacking the checkpoint write on the step's own DB transaction | yes — the key mechanism |
| `dbos.RunAsStep()` | Wraps an ordinary Go function as a durable, retryable step | yes |
| `SELECT FOR UPDATE SKIP LOCKED` queueing | Contention-free work dequeue at high throughput | yes |
| SQL-queryable workflow state | Run history lives in ordinary Postgres tables — query it directly | yes |
| Step-checkpoint model (vs. full history replay) | Memoizes named steps; forgiving of code changes that don't touch step boundaries | yes |

## Worth stealing

### The core claim: exactly-once steps by piggybacking the checkpoint on the step's own transaction

This is DBOS's most load-bearing, most carefully-worded claim, and it holds up under scrutiny of their own docs: *"execute the entire step in a single database transaction, and to 'piggyback' the step checkpoint as part of the transaction. That way, if the workflow fails while the step is executing, the entire transaction is rolled back and nothing happens."* For a DBOS "transaction" step specifically (a step that itself does DB writes), the function's own writes and its completion-checkpoint write commit or roll back **together, atomically, in the same Postgres transaction**. There is no window where the step's side effect committed but the checkpoint didn't (or vice versa) — the two are the same commit.

This is a real structural claim, not marketing: **an engine whose durability store is a separate system from the one the step writes to (Temporal + Cassandra/Postgres history vs. your application's Postgres) cannot make this guarantee** — there is necessarily a window between "step's database write committed" and "engine recorded that the step completed," and a crash in that window forces at-least-once semantics (the step may re-run). DBOS's design collapses that window to zero *for steps that do database work in the same Postgres instance DBOS itself uses.* The guarantee is narrower than "exactly-once for all steps" — a step that calls an external HTTP API still can't get true exactly-once (the caller can't make an external service's side effect atomic with a local commit) — but for the very common case of "workflow step writes to your app's own database," it's a genuine structural advantage of the library-in-your-Postgres model over a separately-hosted orchestrator.

### `RunAsStep` and the Go SDK shape

The Go SDK (`dbos-transact-golang`) mirrors the pattern from other SDKs: any function doing I/O or complex/non-deterministic work should run as `dbos.RunAsStep(ctx, fn)`, where `fn` has signature `func(ctx context.Context) (R, error)` with `R` JSON-serializable. Retries are configured via step options (`WithStepMaxRetries`, etc). Arguments are passed by wrapping the step function in a closure. The workflow function itself is just an ordinary registered Go function — there's no separate "workflow worker process" to stand up, matching the "library not a service" framing.

### `SELECT ... FOR UPDATE SKIP LOCKED` for contention-free queueing

DBOS's own engineering writeup on scaling their Postgres-backed queue is candid about the failure mode it fixes: without `SKIP LOCKED`, concurrent workers contending for the same dequeue rows either serialize (throughput collapses past ~100 workflows/sec) or hit serialization failures past ~1000/sec. `SKIP LOCKED` lets each worker skip rows already locked by another worker and grab the next available one, restoring real parallelism. After further optimization (a partial index maintained only while a workflow is in `ENQUEUED` status, sorted by priority/timestamp), DBOS reports scaling queues to **over 30,000 workflows/second, or 80B/month** (vendor-reported). The mechanism — not the specific number — is the reusable idea: Postgres itself, with the right index and locking clause, is a legitimate high-throughput work queue; you don't need a separate broker to get contention-free dequeue.

### Workflow state in relational tables — SQL as the observability layer

Because workflow/step state lives in ordinary Postgres tables, DBOS's pitch is that you get run history "for free" as SQL: *"Postgres's relational model allows you to express complex filtering and analytical operations declaratively in SQL, leveraging decades of query optimization research"* — their example is a direct query for all workflows that errored in a time window, usable for a dashboard without any bespoke observability API. Their comparison page states this plainly: *"Search, pause, cancel, or resume workflows using SQL."* This is the flip side of choosing Postgres as the durability store instead of a purpose-built event-history service — you trade a specialized replay engine for "it's just rows," and every downstream tool that already speaks SQL (dashboards, ad hoc debugging, alerting) works without new integration.

### Their critique of Temporal — and the step-checkpoint vs. full-replay distinction underneath it

DBOS's direct comparison: adopting Temporal means you *"rearchitect your program to move your workflows and steps to a cluster of Temporal workers,"* then operate the orchestration server plus its own datastores (commonly Cassandra + Elasticsearch) as new, separately-scaled infrastructure that sits **on the critical path** for every workflow execution. Their comparison page quantifies this for a sample app: integrating Temporal requires splitting into two services (worker + API server), adding a runtime dependency on a third service, and 100+ lines of code changed — versus 7 lines of code and no architectural change for DBOS on the same app (vendor-reported benchmark; the app is small, treat the specific LOC delta as illustrative not universal).

The deeper distinction worth carrying forward, independent of vendor framing: **DBOS memoizes named steps** (each step's result is checkpointed once, keyed to that step) while **Temporal replays the entire workflow's control flow** against recorded event history on every recovery. The practical consequence is how forgiving each model is of code changes: under step-checkpointing, a code change that doesn't alter which steps run or their order is safe — the checkpoint for a completed step is just "step N returned X," independent of surrounding control flow. Under full-history replay, the *sequence of awaited operations* itself must match, so even a reorder of two independent, already-completed steps can break replay of an in-flight instance. This is the real tradeoff, not merely "DBOS is Postgres and Temporal is a cluster": one model requires whole-program determinism across every recovery, the other requires only that individual steps be idempotent/pure at their own boundary.

## Worth avoiding

DBOS's "exactly-once" language is easy to over-read as "exactly-once for everything a step does." It specifically covers steps whose side effects are Postgres writes made through DBOS's own transaction API, in the same Postgres instance as the workflow checkpoints. A step that calls an external API, writes to a different database, or has any side effect DBOS doesn't mediate falls back to at-least-once with idempotency left to the caller, same as any other durable execution engine. The marketing surface ("exactly-once execution") doesn't always carry this qualifier — verify which specific step type is being discussed before repeating the claim.

## Facts & figures

- Queue throughput: **"over 30,000 workflows/second, or 80B/month"** after `SKIP LOCKED` + partial-index optimization (vendor-reported, DBOS engineering blog).
- Sample-app migration comparison: Temporal ~100+ LOC changed / new service split / new runtime dependency vs. DBOS ~7 LOC changed / no architecture change (vendor-reported, DBOS comparison page — treat as illustrative of a small sample app, not a general ratio).
- SDKs: Python, TypeScript, Go (`dbos-transact-golang`), Java.

## Sources

- [Why Postgres is a Good Choice for Durable Workflow Execution](https://www.dbos.dev/blog/why-postgres-durable-execution)
- [Making Postgres Queues Scale](https://www.dbos.dev/blog/making-postgres-queues-scale)
- [DBOS vs. Temporal](https://www.dbos.dev/compare/dbos-vs-temporal)
- [Why DBOS?](https://docs.dbos.dev/why-dbos)
- [Steps — DBOS Go Docs](https://docs.dbos.dev/golang/tutorials/step-tutorial) · [Workflows — DBOS Go Docs](https://docs.dbos.dev/golang/tutorials/workflow-tutorial) · [dbos-transact-golang GitHub](https://github.com/dbos-inc/dbos-transact-golang) · [Go package reference](https://pkg.go.dev/github.com/dbos-inc/dbos-transact-golang/dbos)
- [Running Durable Workflows in Postgres using DBOS (Supabase)](https://supabase.com/blog/durable-workflows-in-postgres-dbos)
- [Making Apps Durable with 10x Less Code](https://www.dbos.dev/blog/durable-execution-coding-comparison)
- **Not directly verified:** the 30K workflows/sec and 80B/month figures and the 7-LOC-vs-100-LOC comparison are vendor-reported and not independently reproduced here.
