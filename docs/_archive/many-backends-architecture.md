# Many small backends: problem statement & working architecture

Status: **research in progress** — this captures where the thinking has landed, not a final decision. Treat every section under "Runner model" and "Scaling to many runners" as a hypothesis to stress-test against alternatives, not a spec to build against yet.

## Problem statement

Many independent vertical SaaS apps (working names: `arive`, `marlin`, `pear`, `cuida`, ...; potentially reaching into the hundreds or low thousands over time) are idle the large majority of the time. We want to run all of them on our own AWS infrastructure without either:

- paying full always-on compute cost per app, or
- accepting multi-second wake latency when an idle app receives a request.

Constraints already settled through prior discussion:

- **Stay on AWS.**
- **No AWS Lambda for serving traffic**, in any language. Confirmed bad experience running Litestar on Lambda directly; separately, even considering Rust (which has genuinely fast Lambda cold starts, tens of ms via `provided.al2023`/`cargo lambda`), Lambda was ruled out again on its own merits: no native WebSocket support (API Gateway's `$connect`/`$disconnect` model is an awkward bolt-on), and cold start is a real cost even when it's small. This is a blanket platform preference, not a Python-specific one. Lambda may still be fine for narrow non-serving automation (e.g. an S3-event webhook forwarder), which is a different use case.
- **ECS-native**, not a from-scratch orchestrator, at least as the starting point.
- Paying-customer-facing latency must never depend on a cold boot. (Ruled out per-customer ECS task scale-to-zero explicitly for this reason — Fargate task boot, dominated by image pull + container init + health check grace period, is tens of seconds, which is unacceptable UX for a paying customer's request.)

## Go stack (settled)

`go-huma-ent/STACK.md` (in `polyglot-backends`) is the settled target stack for houston and every vertical app: **huma** (typed handlers + free OpenAPI, on stdlib `net/http`) + **ent** (typed, generated Postgres client, schema defined once in Go) + **pgx** (driver) + **atlas** (schema-as-code migrations generated from the ent schema) + **river** (Postgres-backed job queue) + **otel** (tracing/metrics) + **testcontainers-go** (integration tests against a real Postgres).

One concrete implication, resolved:

- **Atlas replaces Alembic for migrations** — the "dedicated Alembic wrapper" planned below (schema-scoped `env.py`, per-app `version_table_schema`) needs an Atlas-native equivalent instead: schema-scoped migration directories/versioning per app, and the same `_migrator`-vs-`_runtime` role separation expressed through however Atlas's migration runner authenticates. Not yet designed.

**River is dropped, reversing `STACK.md`'s job-queue choice — decided.** Path to this decision, kept because the reasoning matters for later calls:

- Initial concern: River's polling/`LISTEN`-`NOTIFY` mechanism means its workers must periodically touch Postgres to notice new jobs, even when idle — in direct conflict with Aurora Serverless v2's auto-pause (`seconds_until_auto_pause` in `app_stack`'s Terraform), since a queue worker pinging the database every few seconds keeps the idle timer from ever reaching zero.
- Refinement: this conflict only actually matters in **development**, where Aurora is meant to scale to 0. **Production runs Aurora at a fixed 0.5 ACU floor and never pauses at all** (deliberately, to avoid the ~15s cold-resume latency on a paying customer's request — see Database layer), so River polling costs nothing extra there. Running River in prod but something else in dev was considered and rejected: it means exercising two different queue implementations across environments, which risks retry/scheduling bugs hiding in dev until they hit production.
- **Deciding factor, settled**: sessions need a shared store regardless of the queue question. Snacks' existing session mechanism (`snacks/auth/session.py`) is a **server-side session** (Litestar `SessionAuth` + `ServerSideSessionConfig`), not a stateless JWT — the session dict is a tiny `{"user_id": int}` pointer, with the full user re-fetched from Postgres per request via `retrieve_user_handler`. Storing it server-side (vs. a self-contained token) means revocation is instant by construction — delete the session key and access is gone on the user's next request. That's an intentional design choice already made, not incidental, and it means whichever store holds it must be shared across however many Go tasks/runners are live and fast enough to hit on every authenticated request — Postgres would face the same "keeps Aurora awake" problem as River; Redis is the standard fit. **So Redis is a fixed requirement independent of the queue decision** — the houston/Go port keeps the same session shape, Redis-backed. Once Redis is unavoidable anyway, there's no infra-minimization reason left to prefer River over a Redis-backed queue.
- **Queue library: `asynq`** (Redis-backed, closest Go analog to `litestar-saq` — retries, scheduled/cron jobs), running against the same always-on ElastiCache instance as sessions. River was ruled out as a like-for-like swap here regardless, since it's architecturally Postgres-only (no Redis driver — its `SELECT ... FOR UPDATE SKIP LOCKED` + `LISTEN`/`NOTIFY` mechanism doesn't translate to Redis's data model).
- **Redis sizing**: smallest ElastiCache tier, `cache.t4g.micro` — **~$11.68/month on-demand** (verified against current AWS pricing; the earlier "~$5/month" estimate was wrong), single node, no Multi-AZ replica configured yet.

## Database layer (settled)

This part of the design isn't in question — it holds regardless of which compute model wins below.

- **One shared Postgres instance** (Aurora), not one database per app.
- **Platform schema** — shared across every app, holds `users` / `organizations`. Owned and migrated only by `houston` (this repo). Every other app's runtime DB role gets **read-only** access to it; writes to platform data go through a houston API/service call, not a direct cross-schema write, so there's a single place enforcing invariants on that data.
- **One schema per vertical app** (`arive`, `marlin`, `pear`, `cuida`, ...). Each app's own Alembic migration chain touches only its own schema — never platform's, never another app's.
- **Within a vertical app's schema**, multi-org tenancy uses the existing RLS mechanism already built into `snacks`: an `organization_id` column plus Postgres session variables (`app.organization_id`) set per-transaction, enforced by RLS policies. This is a different axis from schema-per-app — schema separates *products*, RLS separates *customer orgs within one product*.
- Vertical apps **import platform model classes from `snacks`** (e.g. `User`, `Organization`) rather than redefining them locally, so there's one source of truth for their shape even though houston alone owns their migrations.
- **Two DB roles per app**: a `_migrator` role (DDL on that app's schema only, used solely by the deploy-time Alembic wrapper) and a `_runtime` role (DML only on its own schema, `SELECT`-only on platform, used by the running app process). The running process never holds DDL rights.
- Each app's `alembic_version` table must live inside its own schema (`version_table_schema=<app_schema>`), not a shared default, or two apps' migration heads collide.
- A dedicated migration wrapper is planned so no app repo has to hand-roll schema-scoping correctly on its own — originally scoped as an Alembic wrapper; needs re-scoping for Atlas now that the Go stack is settled (see "Go stack" section above).
- **Aurora Serverless v2 scaling policy differs by environment, on purpose.** Development: `min_capacity = 0`, `seconds_until_auto_pause = 300` (existing `app_stack` Terraform defaults) — true scale-to-zero, since dev cost matters more than dev latency. Production: fixed floor of **0.5 ACU, never pauses** — specifically because resuming Aurora from a full pause takes **~15 seconds** for the first connection (AWS-documented), which is unacceptable latency for a paying customer's request, same category of problem as the ECS-task-cold-start latency already ruled out elsewhere in this doc. Pricing for reference: Aurora Serverless v2 Postgres is **$0.12/ACU-hour**; storage (~$0.10/GB-month) and IO (~$0.20/million requests) bill regardless of pause state. A continuously-idle dev cluster kept awake at a light floor (e.g. by a naive always-polling worker) would cost roughly **$44/month** in compute alone versus near-zero when actually allowed to pause — this was the concrete number that drove the queue-store decision above.

## Compute layer — path taken to get here

Recorded so alternatives already ruled out (and *why*) aren't silently re-litigated later:

1. **Mounting all apps into one Litestar process** (ASGI `is_mount=True`, confirmed technically supported by Litestar) — rejected. `snacks.config._config` and `BaseRegistry`/tool-registry are process-global singletons; two apps in one process collide on config and registration namespaces. Fixing this needs contextvar-scoping every global in `snacks` — real platform surgery with real correctness risk (silent cross-app state leakage), for savings that don't justify it. Also: one process = one dependency environment, permanently, which fights the "independent repos" premise; zero process-level fault isolation (one blocking call anywhere stalls every mounted app's shared event loop); deploy coupling is *worse in kind* than the alternatives below (one merged artifact to rebuild/retest per change, not a scoped image swap).
2. **Multi-container ECS task per app** (each vertical app its own container within one task, Caddy sidecar routing by Host/path over `localhost`) — viable for Python, but has real costs: task definitions are atomic, so any one app's redeploy bumps a new task-def revision and restarts the whole task (siblings included); shared memory ceiling means one app's leak can OOM-kill everyone in the task; scaling is per-task, so all apps in it scale as a bundle.
3. **Pivot to Rust** for this specific problem (`~/repos/polyglot-backends` — nine backend stacks benchmarked side by side, five of them Rust: Axum+SeaORM+utoipa, Axum+prost/protobuf, poem+poem-openapi, Rocket, loco.rs). Rationale: the wake-latency problem that killed scale-to-zero for Python is really a *CPython-interpreter-plus-import-chain* problem, not fundamentally an ECS problem. A statically-linked Rust binary has no interpreter to boot and a tiny image footprint, which reopens fast-wake designs that don't work for Python.
4. **Bare EC2 + systemd, no Docker at all** — floated, since a `musl`-static Rust binary needs no container to bundle a runtime (unlike Python, which needs Docker specifically to bundle the interpreter+venv). Real upside: fully independent per-app deploys (`systemctl restart <app>`, no shared task definition). Set aside for now as "too far" — loses ECS's native per-service horizontal autoscaling, and the group wanted a middle ground rather than abandoning ECS orchestration entirely.
5. **Pivot from Rust to Go, for both the vertical apps and houston itself** — superseding item 3 above. Driving reason: third-party SDK coverage. Stripe, Pulumi, AWS, and most infra/observability vendors ship official, first-class Go SDKs; Rust support for the same services is community-maintained or partial. Since the vertical apps were already confirmed unable to stay Python, and a non-Python app can't `import` `snacks`' Python model classes regardless of which language wins, there's no remaining benefit to keeping houston/`snacks` in Python while apps move elsewhere — splitting the platform across two languages would mean paying the full rewrite cost for cross-language contracts while still maintaining two toolchains. **Decision: one language (Go) for houston and every vertical app. `snacks` gets a full port to Go, not a partial one** — its auth, billing, RLS-as-code, form DSL, LLM/agentic-tool layer, embeddings, and comms modules all need Go equivalents; several (RLS-policy-as-code via `alembic_utils`, the form DSL) don't have an off-the-shelf Go equivalent and will need to be hand-built.

## Language validation: Go vs. Rust, measured

Before committing to Go, ran a real benchmark rather than relying on the general "Go carries more runtime weight than Rust" intuition — built the existing `go-huma-ent` and `rust-axum-seaorm` services from `polyglot-backends` (stripped release binaries) against the live Postgres in that repo's `docker-compose`.

| Metric | Go (huma+ent) | Rust (axum+SeaORM) |
|---|---|---|
| Stripped binary size | 18.3 MB | 17.9 MB |
| Cold start → first healthy response (1st run) | 280 ms | 318 ms |
| Cold start (subsequent runs, warm OS cache) | 7–8 ms | 28–31 ms |
| Idle RSS after serving one request | 15.1 MB | 6.2 MB |

Caveats on reading these numbers:
- **Binary size is a wash for these two *full-featured* stacks** (both pull in an ORM, an async runtime, OpenAPI/Swagger tooling) — the "Rust is way smaller" intuition holds for a minimal binary without that machinery, not necessarily for a real ORM+OpenAPI service in either language.
- **The startup-time comparison isn't perfectly apples-to-apples**: Rust's `main()` blocks on `Database::connect().await` (SeaORM eagerly validates the DB connection) before serving anything; Go's `database/sql` (`sql.Open`) is lazy and this Go `/health` handler never touches the DB at all. Rust's number partly reflects that idiom difference, not a fundamental Rust cold-start cost.
- **Idle RSS is the number that actually matters for the runner model**, since it bounds how many backends fit in one runner's fixed memory budget — Go uses **~2.4x more memory per idle instance than Rust** (15.1 MB vs. 6.2 MB). On a 2 GB runner task that's roughly ~130 idle Go backends vs. ~330 idle Rust ones (rough math, before OS/runner overhead). Real cost, not disqualifying — plan runner fleet capacity against Go's ~15 MB idle floor.

Both are roughly an order of magnitude better than Python on every one of these axes. Optimization directions flagged as worth trying before finalizing runner capacity numbers, not yet attempted:
- Symmetrize the DB-connect eagerness between the two (or defer pool init to first query generally) so cold-start comparisons reflect binary/runtime cost, not ORM idiom.
- `GOGC`/`GOMEMLIMIT` tuning — Go's default GC targets throughput, not idle footprint, which is the wrong target for hundreds of mostly-idle processes.
- Trim what's actually linked into the Go binary — `ent`'s generated client and `huma`'s OpenAPI machinery are likely a meaningful chunk of both the binary size and idle RSS above; a handler-only build without that codegen overhead may shrink both.

## Runner model (current working design — not yet finalized)

The landed middle ground: an always-on ECS task running a small **runner** container whose job is to host up to N Go backend processes and start/stop them on demand *within* that already-warm task. (Written as "Rust" in earlier discussion below this pivot — the mechanics are identical for Go; only the per-instance idle-memory budget changes, per the validation above.)

- The runner owns the task's one exposed port and is the only thing the ALB health-checks — individual backends can be up or down without affecting task-level health.
- **Backend binaries are fetched dynamically at runtime from S3**, not baked into the runner's image. This decouples each app's deploy from the runner's own image lifecycle entirely — a given app's CI just needs to push a new binary to S3; it doesn't touch the runner. This is a much more tractable version of "dynamic loading" than the equivalent Python idea (which was rejected earlier for this project) specifically because a static Go binary is a fully self-contained OS process with nothing to hot-reload or version-conflict — "fetch a file, `chmod +x`, exec" is the entire mechanism.
- On a request for a backend that isn't currently running: fetch/exec it, hold the request while it comes up (expected: single-digit-to-tens of milliseconds, since this is a process fork of an already-local binary, not a container or task boot), then proxy.
- On a request for a backend that's already running: proxy straight through.
- A reaper stops backends idle past a threshold (SIGTERM, then SIGKILL), freeing the task's shared CPU/memory budget for whatever's actually active.
- **Two things this design makes non-free, flagged for deliberate handling rather than accidental loss:**
  - **Logs.** ECS's per-container log streams don't exist below the container level — the runner must tag/prefix each child process's stdout/stderr itself (or redirect to per-app pipes/files it forwards with structured tags) or all apps' logs blur into one stream.
  - **Metrics.** Same issue — ECS/CloudWatch container metrics only see the one runner container's aggregate usage. Per-app resource visibility requires the runner to expose its own metrics endpoint.

## Scaling to many runners (M runners, ~1000 apps)

One runner/task can't hold everything at scale, so this becomes app-to-runner placement across a fleet:

- **Consistent hashing**, not static `hash % M` (which reshuffles nearly everything when the runner fleet size changes) and not free-for-all (which causes redundant cold starts of the same app across multiple runners with no cache coherence). Each app hashes to a small set of candidate runners (~2-3, for redundancy); route to the primary unless it's unhealthy/overloaded.
- **Routing tier candidate: Envoy's `ring_hash` load-balancing policy**, keyed on a header identifying the target app — this is a solved problem in existing L7 proxy tooling and worth using rather than hand-rolling a custom consistent-hash router.
- **Fleet membership** via ECS Service Discovery (Cloud Map), feeding the hash ring as runners scale up/down or get replaced.
- **Self-healing property, no extra design needed**: a dead runner's apps simply resolve to their next candidate on the ring and cold-start there on next request.
- **Eviction/idle-reaping stays purely local** to each runner — no new global coordination needed at the fleet layer just because there are now M runners instead of one.

## Open questions — explicitly not yet decided

Flagging these so the next research pass has a concrete list rather than starting from scratch:

- **Binary provenance/integrity**: exact versioning, checksum/signature verification before exec'ing a fetched binary, and rollback strategy if a bad binary gets pushed.
- **Hand-rolled router vs. Envoy/service-mesh** for the ring-hash tier — not decided; Envoy is the "don't reinvent this" candidate but hasn't been evaluated against the team's ops comfort with running/operating Envoy.
- **CI/deploy flow** for pushing a new Rust binary to S3 per app repo, and how the runner detects/picks up a new version for an app that's currently idle vs. currently running.
- **Sizing/tuning**: idle-timeout thresholds, how many concurrent backends a given runner size can hold, and what metric drives runner-fleet autoscaling.
- **Paying vs. free tier**, revisited on top of this model. Earlier discussion explored dedicated ECS tasks per paying customer (rejected — pays full 24/7 cost per customer) and shared pools sized by tier (parked when the conversation refocused on the general many-apps problem). Worth revisiting whether a paying customer could get a *pinned, guaranteed-warm* placement via the same hashing mechanism instead of relying on shared LRU behavior.
- **The full `snacks`-to-Go port** — no equivalent yet identified for RLS-policy-as-code (previously `alembic_utils`; Atlas's extensibility for versioned Postgres RLS policies needs checking, see below) or the form DSL specifically; everything else (auth, billing/Stripe, embeddings, comms) has plausible Go library support but hasn't been scoped module-by-module.
- **Alternatives not yet fully explored**, worth a research pass before committing to the runner model above:
  - Firecracker/microVM-per-app (Fly Machines-style) — originally set aside because Python's interpreter startup made it unattractive; worth reconsidering now that Rust's boot time is in the same ballpark as a Firecracker microVM boot, which might change the calculus versus building a custom in-process supervisor.
  - WASM/WASI-based sandboxing as a lighter-weight isolation unit than an OS process (came up previously in an unrelated platform-callback-isolation context; may or may not transfer here).
  - Existing multi-tenant isolate-based platforms (Cloudflare Workers/Containers, Deno Deploy) as prior art for the runner's core problem, even though the AWS-only constraint rules them out directly as a target.
  - Nomad or Kubernetes as an alternative to hand-rolling placement/routing on top of raw ECS — not discussed at all yet.
