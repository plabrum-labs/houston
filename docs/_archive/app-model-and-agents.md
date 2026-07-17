# App-building model & agent platform

Status: **early design** — captures where a working conversation landed, not a spec to build against yet. Companion to `many-backends-architecture.md` (runtime/compute) and `frontend-hosting-architecture.md` (hosting); this doc covers how builders construct apps and how apps get agent behavior.

## Problem statement

Houston needs to let people build fully custom vertical SaaS apps at varying "altitude" — from a non-technical founder describing intent, to a developer writing full custom Go — without the platform splintering into disconnected product surfaces (a low-code layer that can't do what code can, and vice versa). Separately, every app should be able to offer competent agent behavior without each builder hand-rolling agent orchestration from scratch. Getting the composability of these right is the core design problem, not a side concern.

## Personas

- **Platform operator** (Houston team) — builds and runs the infra/runtime itself.
- **App builder** — eventually third-party, not just internal. Ranges from non-technical (never reads a diff) to full Go developers. The same person may move along this range within one app.
- **End customer / org admin** — uses a deployed vertical app, within their org's RLS-scoped data.

## App-building model (settled)

Considered a three-layer architecture (code-first / declarative DSL / agentic), each compiling down or delegating to the one below. Rejected in favor of a simpler, lower-risk model:

- **One substrate, not three layers.** The "DSL" is not a separate format (no YAML/JSON that compiles to Go). It's idiomatic Go + `ent` schema + `huma` handlers, made ergonomic enough via `snacks-go` SDK conventions (form/workflow helpers, auth/billing helpers, agent-tool registration) that writing declarative-feeling app code and writing fully custom code are the same activity at different points on a spectrum — not two systems that need to stay in sync.
- **Rejected alternative**: a genuine independent DSL (own parser/compiler targeting ent+huma). Would buy a format other tooling (a future visual builder) could read/write independent of an agent — but at the cost of a two-representation drift risk. Parked; revisit only if a concrete need for non-Claude-Code tooling shows up.
- **Skills teach Claude the conventions, not a parser.** `bootstrap-app` (and future skills — `add-form`, `add-workflow`, `add-agent-tool`) encode how a Houston app is idiomatically structured, so Claude writes consistent, platform-compatible code regardless of whether the human is non-technical (never reads the code) or a developer (reviews and extends it directly).
- **No escape hatch to design.** Because there's one substrate, "I hit something the low-code layer can't express" isn't a designed transition — it's just the next line of code, written in the same session, same repo. This eliminates the classic low-code failure mode (a real wall between "easy mode" and "real code").
- **Open question, not yet designed**: whether the SDK's conventions are actually ergonomic enough that Claude reliably writes idiomatic code instead of reinventing patterns per app. This is real design work (good defaults, strong typing, codegen for boilerplate) and is where the composability risk now actually lives.

## Builder experience (settled)

- **Claude Code + Houston skills, run locally, is the primary builder interface** — not a hosted web IDE or dashboard. This is a deliberate departure from the Foundry/Vercel/Modal model, none of which have "local AI pair-programmer as the primary builder surface."
- **Iteration is local and cheap for the builder, not Houston.** A founder describes their app, Claude scaffolds/iterates via skills entirely on their machine at their own Claude usage cost. A `deploy` skill provisions schema/subdomain/billing and ships to the runner fleet only once the builder is ready. Houston's compute is only touched by the final deployed artifact (a small, idle-until-woken Go binary) — not by the trial-and-error of getting there. This is a favorable cost structure versus hosted-builder platforms, where every iteration cycle is the platform's compute bill.
- **Open question**: local iteration is easy for pure UI/form/workflow logic, but touching auth, RLS, multi-tenant orgs, or billing needs *some* backing service to behave like prod. Not yet decided whether local dev talks to a shared low-cost dev Houston instance, a local Docker Postgres+RLS harness, or something else.

## Agent platform (working design)

Every Houston app is agent-native by construction, because the same typed API surface serves three consumers instead of needing three separate integrations:

- **Tools are auto-derived, not hand-authored.** Since every app's API is already typed OpenAPI (`huma`) over the ontology (`ent` + RLS), an agent's tool surface *is* that API surface. Adding an endpoint adds a tool for free — no separate "define agent tools" step that can drift from the real endpoints.
- **Scoping is free.** An agent acts as the calling user, through the same RLS/org-scoping every human request goes through. It can only see/do what that user's org already permits — no separate agent-permissions model to get wrong.
- **Bundled as a platform feature, not builder-owned infra.** Vertical-app builders "turn on" an agent the way they'd bundle a Stripe Radar or Ramp-style in-product review agent — pointed at their own app's ontology, branded as part of their product — without writing orchestration code themselves. This is a monetizable, differentiated capability: "your vertical SaaS app ships with a competent agent."
- **Runtime is model/framework-agnostic underneath.** Since the mechanism is "an agent loop calling a stable typed tool surface," the model or agent framework driving that loop (Claude, GPT, whatever's cutting-edge next) is a swappable implementation detail — the architecture doesn't bet on one vendor's agent framework.
- **Same surface, external callers too.** The identical tool surface can be exposed as an MCP server, so a customer's own agent (their Claude Desktop, their ChatGPT, whatever they bring) can drive their app instance directly. "Apps as agent-callable tools" and "agents embedded inside apps" are the same mechanism viewed from two directions.
- **Open question, not yet decided**: should the bundled agent be on by default or opt-in per app? An agent taking actions on a paying customer's data is a bigger trust/support commitment than a form submission.

## Async agent tasks & analytics workspace (working design)

Extends the bundled agent from synchronous tool calls to background analysis tasks, reusing infra already committed to elsewhere rather than inventing new infra:

- **Async triggering** reuses the `asynq` (Redis-backed) job queue already chosen for the platform (see `many-backends-architecture.md`). The agent is another producer onto that queue, not a new subsystem.
- **Dedicated workspace per task** reuses the runner model's "fetch, exec, tear down when idle" pattern, applied at task granularity instead of app granularity — one task gets one throwaway workspace.
- **Data flow, settled**: the agent queries the core Postgres DB through the same RLS-scoped path any request uses — no raw DB connection, no special export path. Results are loaded into a local **DuckDB** instance in the task's workspace as needed.
- **Why this shape**: RLS is enforced exactly once, at the same boundary as every other request — DuckDB just caches an already-authorized result set, rather than becoming a new place org-scoping can be gotten wrong. Data only moves when a task actually needs it, so there's no standing replication/CDC pipeline running whether or not anyone's using it — consistent with the platform's "don't pay for idle" posture (Aurora floor, ECS runner scale-to-zero-ish design).
- **DuckDB's value is the iterate step, not the fetch step.** Once loaded, the agent can join/aggregate/window-function across pulled tables locally, repeatedly, without round-tripping to Postgres per analytical step.
- **Rejected alternative**: a continuously-synced Parquet/DuckDB store per org (CDC pipeline keeping data warm). Would give faster task starts but reintroduces an always-on cost center the rest of the architecture deliberately avoids. Not ruled out permanently — revisit if on-demand query load against Postgres becomes a real bottleneck.
- **Full shape**: agent task → `asynq` job → ephemeral workspace (runner-pattern reuse) → RLS-scoped queries against core Postgres, pulled in as needed → DuckDB for local iteration → result/report handed back → workspace discarded.

## Open questions

- SDK ergonomics: what conventions actually make code feel declarative enough for Claude to write reliably idiomatic apps? Not yet designed.
- Local dev backing service for auth/RLS/billing-touching iteration — shared dev instance vs. local harness vs. something else.
- Bundled agent: on by default or opt-in per app.
- Async agent task trigger surface: chat-initiated only, or also scheduled/cron-triggered?
- Workspace lifecycle specifics for agent tasks (idle timeout, max task duration, concurrent task limits per org).
