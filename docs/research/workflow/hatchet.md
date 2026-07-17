# Hatchet

**What it is:** Task/workflow orchestration engine (queue + DAG + durable execution) built directly on Postgres for both the runtime and the observability store — a direct architectural bet against "Postgres can't scale as a queue."
**Axis:** workflow.
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Hatchet engine** | Task queue, DAG orchestrator, and durable execution engine — usable as any one or all three. |
| **Durable tasks** | Runtime-determined workflows: branching, looping, and child-spawning decided by code at execution time, not a static graph. |
| **Hatchet Cloud / self-hosted** | Managed or self-hosted, Postgres-backed. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Postgres for runtime + observability | One datastore for both durability and the dashboard/history queries | yes |
| Durable execution | Checkpointed steps (`SleepFor`, `WaitForEvent`, `WaitFor`, `Memo`, `RunChild`) | yes |
| DAGs as durable workflows | Static DAG definitions get the same durability/checkpoint guarantees | yes |
| `RunChild` | Spawn a child task/workflow at runtime, wait for its result | yes |
| Replay from failed step | Redrive a run from the point of failure, reusing (or editing) original inputs | yes |

## Worth stealing

### Postgres as the single durability + observability layer

Hatchet's founding bet, stated plainly: *"Postgres solves for 99.9% of queueing use-cases"* better than the common alternatives (Celery on Redis/RabbitMQ, BullMQ on Redis) — citing `SKIP LOCKED` and modern replication as having closed the gap that used to force teams to a dedicated broker. The architectural consequence: **Postgres is the durability layer for both runtime state and observability** — the same tables that make execution durable are queryable for the dashboard, run history, and search, with no separate observability pipeline (compare DBOS's identical "SQL-queryable run history" argument in `dbos.md`, and Temporal's opposite choice of Cassandra + Elasticsearch as two separate systems).

### Durable tasks — runtime-determined structure, checkpointed per call

A "durable task" in Hatchet isn't a static graph — *"the number of children, which branches to take, and whether to loop or stop are all determined by your code at runtime."* Each call to `SleepFor`, `WaitForEvent`, `WaitFor`, `Memo`, or `RunChild` creates a checkpoint in the durable event log, so recovery resumes after the last completed checkpoint rather than replaying the whole function. This is the same step-checkpoint model DBOS uses (vs. Temporal's full-history replay) — Hatchet's docs frame it as letting ordinary imperative code (loops, conditionals, dynamic child counts) drive the workflow shape, since only the checkpointed calls need to be replay-stable, not the surrounding control flow.

### `RunChild` — the primary composition primitive

Spawning children is described as *"the primary way durable tasks build workflows at runtime"*: a durable task can spawn any runnable — a plain task, another durable task, or an entire DAG workflow — wait for its result, and branch on it. The explicit guidance: any code that does I/O or calls another system (a DB fetch, an external API) should be wrapped as a child task/workflow via `RunChild` rather than called inline, keeping the durable task's own body free of non-replay-safe side effects.

### DAGs get durability too

Static DAG-defined workflows aren't a separate, less-durable mode — Hatchet's docs frame DAGs explicitly as *"Durable Workflows"*: the same checkpoint/recovery guarantees apply whether the shape is declared upfront (DAG) or decided at runtime (durable task). This avoids a common split in other engines where "the simple static-graph mode" and "the fully durable mode" are different products with different guarantees.

### Replay/redrive from the failure point

Failed runs can be replayed from the failed step, **reusing the original inputs** by default (a "Replay Event" action), with the option to hand-edit the JSON input before replay to fix bad data that caused the original failure, or to override values via a `context.playground`-style mechanism for parent/child step input adjustments. This is the practical debugging loop durable execution is supposed to enable: fix the data or the code, re-run from the failure point, not from the start.

## Worth avoiding

The "Postgres solves 99.9% of queueing" framing is a founder-stated design thesis (from a 2024 Hacker News launch thread), not an independently benchmarked claim — treat the specific figure as rhetorical, the architectural direction (Postgres as unified durability+observability store, aided by `SKIP LOCKED`) as the real, verifiable claim, and cross-check against DBOS's own published `SKIP LOCKED` scaling numbers (`dbos.md`) if a hard throughput ceiling matters.

## Facts & figures

- Founding claim (2024 HN launch): Postgres, with `SKIP LOCKED` and modern replication, can scale to 10k+ TPS and horizontally across regions for queueing use cases (vendor-founder-reported, not independently benchmarked here).

## Sources

- [Durable Tasks](https://docs.hatchet.run/home/durable-execution) · [Introduction to Durable Execution](https://docs.hatchet.run/v1/durable-execution) · [Durable Best Practices](https://docs.hatchet.run/home/durable-best-practices)
- [DAGs as Durable Workflows](https://docs.hatchet.run/v1/directed-acyclic-graphs) · [Child Spawning](https://docs.hatchet.run/v1/child-spawning)
- [Bulk Cancellations and Replays](https://docs.hatchet.run/home/bulk-retries-and-cancellations)
- [Hatchet GitHub](https://github.com/hatchet-dev/hatchet) · [Show HN: Hatchet launch thread](https://news.ycombinator.com/item?id=39643136) (source of the "99.9%" quote)
- **Not directly verified:** the "99.9%" figure and 10k+ TPS claim are founder statements from a launch thread, not a published benchmark.
