# Agent Loops

Houston runs long-lived agents as a first-class primitive. An agent loop is a durable piece of
work that a human starts, an agent advances over hours or days, and a human approves before
anything irreversible happens. The loop parks between steps, wakes on signals from the outside
world, takes feedback from people and from machines alike, and keeps a live workspace the whole
time so that resuming costs nothing.

A new agent is a configuration plus a small adapter — a prompt, a tool surface, a validator, a
place to put the result. The loop itself, the workspace, the gate, the journal and the signal
plumbing are the platform's.

## The shape

```
trigger ──▶ work item ──▶ [ turn ──▶ validate ──▶ feedback ]* ──▶ gate ──▶ commit
                 ▲                                   │
                 └──────────── signals ──────────────┘
              (human replies · external validators · watched systems)
```

A work item is created by a trigger, carries a live workspace, and advances one turn at a time.
Each turn produces work and a structured result. Validation follows. Failure becomes feedback and
another turn. When the work is ready it goes to a human, who approves it or feeds back more.
Approval releases the commit — the one irreversible act the loop exists to perform.

## The four primitives

**Work item.** The durable unit. It holds state, a target configuration, a bound conversation, a
subscription to external signals, a journal, accumulated artifacts, and a workspace. It outlives
any single turn and most of its life is spent parked.

**Workspace.** A live execution environment belonging to one work item for that item's whole
lifetime. Its tree stays checked out, its dependencies stay installed, its caches stay warm, and
its agent session stays resident — a turn picks up exactly where the last one left off. The
mental model is a worktree on your own machine that someone else is also working in: still there,
still set up, still current.

**Turn.** One advance of the work item. A turn is either *agentic* — a session with a bounded
tool surface producing a structured result — or *deterministic*, a plain operation the platform
performs. Deterministic turns escalate into agentic ones when they fail, so routine work stays
cheap and only genuine judgment reaches a model.

**Gate.** The point where a human decides. A gate is a conversation, not a switch: the agent
proposes, the human approves or responds, the agent revises, and only approval releases the
commit. Every loop that touches the outside world irreversibly has one.

## Triggers and signals

A work item is born from a **trigger**:

- an **event** — something appeared in a watched system
- a **schedule** — it is Sunday
- a **request** — a person asked, in a chat thread, for something to happen

Once live, a work item **subscribes** to the signals that concern it, and each one wakes it: a
reply on its thread, a comment on its output, an external check reporting, an upstream dependency
moving, its own completion being confirmed elsewhere. Signals that arrive together coalesce into a
single wake, and a work item runs at most one turn at a time — the platform decides what happens
next with everything it knows in hand.

The trigger also binds the work item to a **conversation**: where it reports, where it asks, and
where a human's reply reaches it. A loop always has somewhere to talk.

## The revision loop

There is one revision mechanism and it takes feedback from three places:

| source | arrives | example |
|---|---|---|
| **self-check** | synchronously, inside a turn | the check tier fails; the turn is blocked and retried |
| **external validator** | asynchronously, as a signal | CI reports red; the store rejects two items |
| **human** | asynchronously, as a signal | a comment on the pull request; "swap Thursday's meal" |

All three produce the same thing: a statement of what is wrong, and another turn. Attempts are
bounded, and exhaustion escalates to a human rather than looping. This is why "fix the failing
build," "apply this review comment," and "now break that out by month" are the same transition in
the platform and differ only in who is talking.

## Validators

**In-loop validators** run synchronously inside a turn, in the workspace, and their output feeds
straight back into the live session. They are how a turn refuses to finish while its own work is
broken.

**Post-hoc validators** run elsewhere and report back later as a signal, waking a parked work
item. They are how the outside world's opinion enters the loop.

A validator is either a command executed in the workspace or a function over the structured
result, depending on where the loop runs.

## Placement

Each kind declares where its turns execute.

**In-cluster** turns run next to the database with an HTTP tool surface and no workspace. They are
for loops whose work is reading and writing systems of record.

**Sandboxed** turns run on a host that provides isolation: a real filesystem, a shell, and the
freedom to execute code that Houston did not write. Any loop whose agent writes and runs code is
sandboxed, and so is any loop that executes a target's own commands.

Placement is a property of a kind, not a fork in the architecture. Both kinds of turn are driven
by the same loop, produce the same structured results, and pass through the same gates.

## Workspaces are resident

A sandboxed work item's workspace is created when the item starts and lives until it closes. It is
not rebuilt between turns and it is not rebuilt on wake. Houston keeps a residency table — which
host holds which workspace — and routes every turn for a work item to its host.

Because the workspace is live, it stays **current** rather than going stale: it tracks its upstream
continuously as the world moves, so an agent returning after three days finds a tree that is up to
date rather than three days of drift to discover. Each turn opens with a delta — what changed,
what failed, who said what — the same orientation a person wants when they come back to a branch.

A workspace is inspectable. If it is a worktree on a machine, a human can go and look at it.

Losing a host is a disaster, not a routine event, and the recovery is a rebuild: the work item's
durable record — its target, its branch or dataset, its journal — is sufficient to reconstruct a
workspace from nothing. The fast path is that this never happens.

## Tools and capabilities

Two distinct surfaces, and only one of them is exposed to a model.

**Agent tools** are what the model can invoke: a shell, file access, a query interface, a
domain client. A kind declares its tool surface and each turn is granted a subset.

**Platform capabilities** are the machinery around the session, which the platform runs and the
model never calls: provisioning a workspace, running validators, uploading artifacts, publishing a
result. Keeping these out of the tool surface is what stops a model choosing what gets published
or where.

Both live in the host image. Activation is layered, and the lower layers are the ones that bind:

1. **present** in the image
2. **granted** for the turn — shapes what the model can reach for, and produces the denial record
3. **credentialed** per turn — short-lived, narrowly scoped, issued when the turn is dispatched
4. **egress-restricted** by the sandbox to the hosts the kind names

The rule this rests on: **images carry capabilities, never credentials.** A tool present without a
credential is inert, which is what makes one host safe to hand any work.

## Artifacts and the journal

A turn's output is a structured result plus **artifacts** — files the work produced. Artifacts are
uploaded from the workspace and referenced by the work item, so a chart, a report, a database or a
log survives the workspace that made it.

The **journal** is the work item's readable record: what was attempted, what failed and why, what
was decided, what a human said. It is written from each turn's structured result. It is what a
person reads to understand what has been happening, what seeds a rebuilt workspace, and what makes
the loop legible without attaching to a host.

## What a kind is

A kind is mostly rows, plus a small amount of code.

**Configuration** — prompt template, tool grants, structured output schema, ceilings and limits,
retry policy, which states gate, the trigger, the placement and image, the workspace provisioner,
the validators, the sink.

**Code** — the adapters that touch the outside world: a client for the system this loop acts on, a
provisioner for its workspace, a schema for its result, and its commit. Adding a kind is a
configuration row, one adapter module, and a result schema.

**Target configuration** is separate and versioned: the loop's target — a repository, a warehouse,
an account — carries its own settings, proposed by whoever owns the target and approved by an
operator before anything runs against it. Privileged settings are never proposable.

## The conformance set

Three loops define the surface. A change to the platform is right when all three still fit.

| | code agent | meal planner | data analyst |
|---|---|---|---|
| **trigger** | a request in a chat thread | a schedule | a question |
| **placement** | sandboxed | in-cluster | sandboxed |
| **workspace** | a checked-out tree on a branch | none | a scratch tree with fetched datasets |
| **tools** | shell, files, source control | calendar, inventory, ordering | shell, files, query engine |
| **in-loop validation** | the target's own checks and tests | budget and availability | the script runs and returns rows |
| **post-hoc validation** | continuous integration | the store confirms the order | — |
| **artifacts** | logs, diffs | the proposed basket | a database, charts, a notebook |
| **gate** | a human reviews the change | a human approves the basket | a human accepts the analysis |
| **commit** | the change lands | the order is placed | the analysis is published |
| **feedback** | review comments, red builds | "swap Thursday" | "break that out by month" |

The **code agent** is the flagship and the hardest case: a long-lived work item, many turns over
many days, all three feedback sources, a warm tree that tracks a moving upstream, and a commit
nobody wants done twice. The **meal planner** is the degenerate case — no workspace, one turn, one
gate — and it exists to keep the platform honest about how little a simple loop should have to
carry. The **data analyst** sits between them, and it is the one that insists artifacts and warm
environments are primitives rather than conveniences.
