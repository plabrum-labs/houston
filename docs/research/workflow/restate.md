# Restate

**What it is:** A durable execution engine built as a single self-contained system — a distributed log plus consensus engine, shipped as one Rust binary — rather than durable execution bolted on top of an existing queue or database.
**Axis:** workflow.
**Depth:** deep.

## Products & surfaces

| Product | What it is |
|---|---|
| **Restate Server** | Self-hosted, single-binary durable execution engine (command log + event processor). |
| **Restate Cloud** | Managed hosting of the same engine. |
| **SDKs** (TypeScript, Java/Kotlin, Python, Rust, Go) | Register handlers; `Context`/`ObjectContext`/`WorkflowContext` gives durable steps, state, and messaging. |
| **Virtual Objects** | Keyed, stateful entities with serialized per-key handler execution. |
| **Workflows** | A specialization of Virtual Objects for one-shot, run-to-completion processes with a durable promise-style result. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Virtual Objects | Per-key state with a per-key intrinsic lock — only one handler runs per key at a time, others enqueue | yes |
| Log-first execution | Every event is durably logged before being acted on; recovery replays the journal | yes |
| Journaled step results | Completed step results are recorded once and returned instantly on replay, not re-executed | yes |
| Single-binary architecture | No external DB or log dependency — the durability log is Restate itself | maybe |
| Queue vs. durable-execution framing | A clean, reusable heuristic for when each is the right tool | yes |

## Worth stealing

### Virtual Objects — per-key state that replaces a lock service

A Virtual Object is addressed by a key (session ID, user ID, account ID, etc.) and carries its own state. The concurrency model is the interesting part: *"Virtual Objects have an intrinsic lock per key, meaning Restate will make sure at most one request can run at the same time for a given key, and any additional request will be enqueued in a per-key queue."* Restate's own framing of the payoff: *"the single-writer-per-key and linearizable consistency model means developers don't need to worry about locks, race conditions, dirty reads, change visibility, zombie processes, etc."*

The mechanism worth extracting independent of Restate itself: **serialized-per-key execution is a general substitute for a distributed lock service.** Anywhere an application would reach for Redis-based locking, `SELECT ... FOR UPDATE` contention, or a dedicated lock manager to guard "only one in-flight operation per entity," a queue-per-key model gives the same guarantee for free as a side effect of how work is dispatched, with no separate lock-acquisition/lock-release code path to get wrong (no lock that can be held past a crash, no lease-expiry tuning).

### Log-first execution and journaled step results

Restate's architecture note on its own internals: *"events get always added to the log first, and once they are received by the processor they are acted upon."* On failure, *"the processor dispatches a new invocation, attaching the full journal events from this invocation so far,"* so the retried invocation sees everything that already happened and doesn't redo it — a completed step's result, once journaled, *"will always be recovered"* (returned instantly from the journal on replay rather than re-executed). This is durable execution's core recovery mechanism stated plainly: journal before completing, return recorded results for anything already journaled, resume only from the point that wasn't yet recorded.

### The category framing: what separates a queue from durable execution

The clean, reusable version of this distinction (Inngest's wording, cited by multiple vendors in this space including Restate's own comparisons): **a queue's contract ends at delivery; durable execution's contract is completion.**

> "Queuing platforms — BullMQ, Celery, Sidekiq — guarantee delivery. They ensure a worker receives your job and runs it. [...] What happens inside the job, whether it completes, and what to do if it fails midway are outside the queue's contract."

> "Durable execution platforms [...] guarantee completion under any scenario. They persist execution state as work progresses, so that if a process crashes mid-execution, it resumes exactly where it stopped."

The heuristic for which one a given piece of work needs: is the work **"atomic, self-contained, and can restart cleanly from scratch"** — describable as a single verb (send, process, sync, generate) — or is it **"process-shaped: multi-step, long-running, stateful"**, where a mid-execution crash needs to resume rather than restart? A useful tell cited alongside this: if describing the workflow needs "and then," "if that," or "when that," it's process-shaped, not job-shaped.

Restate's operational version of "the contract is completion": it journals each step before returning its result, so a crash replays the journal, returns recorded results for completed steps instantly, and resumes execution exactly at the point that failed — no re-running of already-committed steps, no gap where "delivered but incomplete" work silently drops.

## Worth avoiding

Restate's pitch to *not* adopt the workflow/activity split that Temporal-style engines impose — *"compose durable services into any shape instead of folding every problem into the workflow/activity pattern"* — is a genuine architectural difference, but it's also a smaller, younger ecosystem than Temporal's; weigh operational maturity and community size against the architectural elegance before treating "no external DB or log dependency" as a strict win. A single-binary durability log is also, definitionally, a new kind of infrastructure to operate and back up correctly — it's not free of the "state store" operational burden, just concentrated differently than Temporal's Cassandra+Elasticsearch combination.

## Facts & figures

- Ships as a single Rust binary containing its own distributed log and consensus algorithm — no external database/log dependency required (vendor-reported architecture).
- SDKs: TypeScript, Java/Kotlin, Python, Rust, Go (per Restate docs).

## Sources

- [Building a modern Durable Execution Engine from First Principles](https://www.restate.dev/blog/building-a-modern-durable-execution-engine-from-first-principles) · [The Anatomy of a Durable Execution Stack from First Principles](https://restate.dev/blog/the-anatomy-of-a-durable-execution-stack-from-first-principles/) · [Restate 1.2 announcement](https://www.restate.dev/blog/announcing-restate-1.2)
- [Restate vs Temporal](https://www.restate.dev/vs/temporal) · [Why we built Restate](https://www.restate.dev/blog/why-we-built-restate) · [What is Durable Execution?](https://www.restate.dev/what-is-durable-execution)
- [Key Concepts](https://docs.restate.dev/foundations/key-concepts) · [Databases and Restate](https://docs.restate.dev/guides/databases) · [WorkflowContext (TS SDK)](https://restatedev.github.io/sdk-typescript/interfaces/_restatedev_restate-sdk.WorkflowContext)
- [When a queue isn't enough (Inngest)](https://www.inngest.com/blog/when-a-queue-isnt-enough) — source of the "contract ends at delivery / contract is completion" framing, cited here for the general category distinction rather than as a Restate-authored claim.
