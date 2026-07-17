# Temporal

**What it is:** Durable execution engine — a cluster (Temporal Server) that persists an append-only event history for every workflow, replays it to reconstruct state after crashes, and drives execution through workers that host your code.
**Axis:** workflow, agent.
**Depth:** deep.

## Products & surfaces

| Product | What it is |
|---|---|
| **Temporal Server / Cluster** | The durable execution engine — persistence, task queues, matching, history service. |
| **Temporal Cloud** | Managed hosting of the above. |
| **SDKs** (Go, Java, Python, TypeScript, .NET, PHP) | Workflow/activity code you write; the deterministic-execution contract lives here. |
| **Workflow Streams** (2026, Public Preview) | Real-time output channel out of a running workflow, built on Signals/Updates. |
| **Worker Versioning / Build IDs** | Server-side routing of tasks to compatible worker code versions. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Signals | Async external event delivered into a running workflow, no reply | yes |
| Queries | Synchronous read of workflow state; adds no history; works on completed workflows | yes |
| Updates | Synchronous tracked write; caller awaits result or error | yes |
| `GetVersion`/patching | Records a marker in event history so a changed code path stays deterministic on replay | yes, with caution |
| Build-ID worker versioning | Server routes tasks to a compatible worker build; Pinned vs Auto-Upgrade | maybe |
| Continue-as-new | Truncates history, restarts the workflow fresh with carried-over state | yes |
| Child workflows | Sub-workflows with their own history/identity | yes |
| Saga / compensation library helpers | Register a compensation alongside each forward step | yes |
| Workflow Streams | Token-level streaming out of a durable workflow via Signals/Updates | maybe |

## Worth stealing

### Signals, Queries, Updates — three distinct message shapes, not one

Temporal's docs draw the boundary precisely:

- **Signal** — async write. *"Cause changes in the running Workflow, but you cannot await any response or error."* Fire-and-forget, prioritizes throughput and low client latency.
- **Query** — sync read. *"Can read the current state of the Workflow but cannot block in doing so."* The two properties that matter: Queries **"never add entries to the Workflow Event History"** (they're free — no durability write), and they **"can operate on completed Workflows"** (you can query a workflow's final state after it finished, indefinitely).
- **Update** — sync write. *"The sender of the Update can wait for a response on completion or an error on failure."* Requires the worker to acknowledge, and — unlike a Signal — an accepted Update **does** create event-history entries, because it's a tracked, replayable state change.

The three-way split maps cleanly onto a real design problem: "did my external write actually happen and what did it return" (Update) vs. "notify but don't block" (Signal) vs. "what's the state right now, cheaply, even after it's done" (Query). Most homegrown workflow engines collapse this into a single generic "send event" primitive and then bolt polling onto it to recover the other two behaviors.

### Versioning — the tax nobody tells you about upfront

The core constraint: *"The Temporal Platform requires that Workflow code is deterministic. If you make a change to your Workflow code that would cause non-deterministic behavior on Replay, you'll need to use one of Temporal's Versioning methods."* A crashed worker recovers by **replaying** the event history against the current workflow code — if the code takes a different path than it did the first time, replay diverges from the recorded history and the workflow errors out mid-execution, in production, for an already-running instance you can't easily fix.

**`workflow.GetVersion()` patching**: *"When `workflow.GetVersion()` is run for the new Workflow Execution, it records a marker in the Event History so that all future calls to GetVersion for this change [return the same version]."* Concretely: on first execution (no marker yet), it writes a marker and returns the new version; on replay, it finds the marker and returns whatever version was recorded, so old-history and new-code diverge only at points you've explicitly branched on. Get the marker ordering wrong — insert a new patch **before** its corresponding marker in history — and replay throws a non-deterministic exception because replay and original event histories no longer line up.

**Build-ID worker versioning** is the newer, server-side alternative: a Build ID (recommended as a code-hash + timestamp) identifies a worker deployment version; multiple versions poll the same task queue simultaneously and *"the Temporal Server routes Tasks to the right version."* Per-workflow-type **Pinned** (guaranteed to complete on one deployment version, never migrates) vs. **Auto-Upgrade** (moves to new code as it rolls out) policies replace needing `GetVersion()` branches for many routine deployments.

**The determinism constraint is viral on user code.** It's not just "don't call `random()`" — *"adding, removing, or reordering await calls on Command-producing APIs such as Activities and timers"* breaks replay, because each await is a yield point that the replay engine matches against the recorded Command sequence. This means an apparently-harmless refactor (reordering two independent `await activity()` calls, adding a new early-exit branch) can break every in-flight instance of that workflow. Versioning exists specifically because this cost is otherwise invisible until an instance actually replays through the changed code path — the tax is a structural consequence of full-history replay as the recovery mechanism, not an implementation bug.

### Sagas — compensation is the design surface, not an afterthought

Temporal's own guidance and worked examples treat compensation-first as good practice: *"Define Compensation Actions: Plan rollback mechanisms for each step"* and warn against *"Undefined Compensation Actions"* as a common pitfall — every forward step needs a defined undo before you rely on the sequence completing. SDK helpers let you register a compensation right where you invoke the forward step (`saga.addCompensation(activities::cancelHotel, ...); activities.bookHotel(...)`), and unwind them in reverse order automatically if a later step fails. The pattern generalizes: any multi-step workflow that spans external side effects (payment capture, third-party bookings, resource provisioning) needs its "undo" defined as a first-class, equally-tested code path, not an exception handler bolted on later.

### Continue-as-new — bounding memory for workflows that never really end

Continue-as-new *"allows you to checkpoint your Workflow's state and start a fresh Workflow ... your Workflow can run forever."* The new execution keeps the same Workflow ID but a fresh Run ID and empty event history; you pass forward whatever state needs to survive. Two independent reasons to use it: **performance** (long histories bog down replay and can hit event-count limits) and **versioning** (an old, still-running history stops accumulating code-version drift once truncated). SDKs expose a "continue-as-new suggested" signal so the workflow itself can decide when to checkpoint rather than the operator guessing a threshold. This is the standard shape for "entity workflows" — a durable object (a user session, an account, a long-lived deal) modeled as one continuously-running workflow instance rather than a new workflow per event.

### Workflow Streams (2026) — durability without losing interactivity

Announced at Replay 2026, now Public Preview: a real-time output channel from inside a durable workflow *"without requiring Redis, a separate SSE server, or any custom state management."* Built entirely on Signals and Updates — token batches and app-level updates stream out over the same primitives, inheriting the same durability guarantees as the rest of the workflow. Vendor-stated framing: it targets the three reasons teams previously avoided Temporal for AI workloads — infra overhead, queue-service dependency, and LLM-streaming incompatibility. Practical guidance from the docs: ~200ms batching is a reasonable default for a chat UI (a 30-second LLM response generates roughly 150 publish signals at that cadence). SDK support as of the announcement: Python and Go/.NET, with Java/TypeScript in pre-release.

### Retool chose Temporal over building a job queue

Retool initially built its own queue on PG Boss + AWS Lambda for its Workflows product, hit scaling and maintenance limits, and adopted Temporal instead. When launching a second product (Agents), the team — having already run Temporal in production — went straight to Temporal Cloud rather than repeat the build: *"building a durable, production-grade orchestration layer in-house would be a massive lift."* Read as a case study in the queue-vs-durable-execution tradeoff: the cost of hand-rolled orchestration doesn't show up until you need retries, replay, or a second product built on the same primitive.

## Worth avoiding

**Determinism is not opt-in and not locally scoped.** A change to a workflow *definition* — not even business-logic-visible, e.g. reordering two independent activity calls — can break every in-flight instance of that workflow the moment a worker crashes and needs to replay. The mitigation (`GetVersion`/Build-ID versioning) is real but is itself an ongoing maintenance surface: every "safe" change still requires a developer to correctly reason about whether it's replay-safe, and getting the marker/version bookkeeping wrong produces the exact failure it exists to prevent — silently, in production, only on replay.

## Facts & figures

- **$300M Series D at a $5B valuation, led by Andreessen Horowitz, February 2026** — doubles the October valuation; Lightspeed and Sapphire joined, with Sequoia, Index, Tiger, GIC, Madrona, Amplify participating. $650M raised to date (vendor/press-reported).
- OpenAI uses Temporal for Codex (production coding agent); OpenAI Agents SDK integrated Temporal in February 2026. Replit migrated Replit Agent onto Temporal starting Nov 2024, describing the migration as taking "a couple of weeks" for most of the system (vendor case study).
- Customers cited in the funding coverage: ADP, Yum! Brands, Block (press-reported).
- Workflow Streams: Public Preview as of Replay 2026; contrib library, Python/Go/.NET supported, Java/TypeScript pre-release (vendor-reported).

## Sources

- [Workflow message passing](https://docs.temporal.io/encyclopedia/workflow-message-passing) · [Sending Signals, Queries & Updates](https://docs.temporal.io/sending-messages) · [Handling Signals, Queries & Updates](https://docs.temporal.io/handling-messages)
- [Patching](https://docs.temporal.io/patching) · [Go SDK versioning](https://docs.temporal.io/develop/go/workflows/versioning) · [Safely deploying changes to Workflow code](https://docs.temporal.io/develop/safe-deployments)
- [Worker Versioning](https://docs.temporal.io/production-deployment/worker-deployments/worker-versioning)
- [Saga compensating transactions blog](https://temporal.io/blog/compensating-actions-part-of-a-complete-breakfast-with-sagas) · [Mastering saga patterns](https://temporal.io/blog/mastering-saga-patterns-for-distributed-transactions-in-microservices) · [temporal-compensating-transactions repo](https://github.com/temporalio/temporal-compensating-transactions)
- [Continue-As-New](https://docs.temporal.io/workflow-execution/continue-as-new) · [Managing very long-running Workflows](https://temporal.io/blog/very-long-running-workflows)
- [Workflow Streams docs](https://docs.temporal.io/workflow-streams) · [Workflow Streams announcement](https://temporal.io/blog/workflow-streams-live-interactivity-agents-other-applications) · [Replay 2026 announcements](https://temporal.io/blog/replay-2026-product-announcements)
- [Temporal raises $300M Series D](https://www.geekwire.com/2026/temporal-raises-300m-hits-5b-valuation-as-seattle-infrastructure-startup-rides-ai-wave/) · [Temporal's own announcement](https://temporal.io/blog/temporal-raises-usd300m-series-d-at-a-usd5b-valuation)
- [Retool: robust Workflow & Agents products on Temporal](https://temporal.io/resources/case-studies/how-retool-built-robust-workflow-agents-products) · [Replit case study](https://temporal.io/resources/case-studies/replit-uses-temporal-to-power-replit-agent-reliably-at-scale)
- **Not directly verified:** exact wording "Define the compensating transaction for every saga step before implementing the forward transaction" was not found verbatim in reachable Temporal sources; closest verified guidance is "Define Compensation Actions: Plan rollback mechanisms for each step" / "Undefined Compensation Actions: Ensure every step can be reversed" (mastering-saga-patterns blog).
