# Platforms

The platforms Houston will have — one entry per platform, each with a **stage** showing how far along it is. This folder holds both the catalog (this file) and the design docs behind the platforms that have one. What each capability *does* and why it's designed the way it is lives in the design docs here; the order platforms get built lives in `../planning/`; why any of them matter lives in `../vision/`.

## Stages

Same four labels used across `../planning/`:

| Stage | Meaning |
|---|---|
| **planned** | Named, slot understood, no design doc yet. |
| **v0** | Design landed on paper — a doc in this folder, with open questions listed. |
| **v1** | First working implementation; a real app depends on it live. |
| **v2** | Generalized and hardened across multiple apps. |

Nothing is past `v0` yet — the whole platform is pre-implementation. Stages advance per the milestone ladder in `../planning/`.

## Catalog

Codenames are working names from the Bowie namespace (`platform_names.md`), not product branding. "Source" is where the capability comes from: a Palantir Foundry/AIP product, the `snacks` predecessor stack, or net-new to Houston.

### Designed (v0)

| Platform | Codename | What it is | Source | Design doc |
|---|---|---|---|---|
| Runtime & infra | Diamond Dogs | Runner fleet + shared Aurora/Redis + frontend hosting; cheap-idle, warm-wake | Houston | [many-backends-architecture.md](many-backends-architecture.md), [frontend-hosting-architecture.md](frontend-hosting-architecture.md) |
| App builder | Fashion | One-substrate app model (ent+huma), built locally with Claude Code + skills | Foundry (Workshop/Slate) | [app-model-and-agents.md](app-model-and-agents.md) |
| Agent | Duke | Auto-derived tools over each app's typed API; async agent tasks + DuckDB | Foundry (AIP) | [app-model-and-agents.md](app-model-and-agents.md) |
| Access control | Major | Auth/identity, tenant isolation via RLS, operator-private + per-object sharing | snacks | [access-control-architecture.md](access-control-architecture.md) |
| Analysis | *(Quiver-repl.)* | Agent-authored analysis DSL instead of a point-and-click GUI | Foundry (Quiver/Contour) | [quiver-agent-dsl.md](quiver-agent-dsl.md) |
| Ontology | Blackstar | Typed `ent` data model every other platform reads/writes through | Foundry | *(within the above docs; no dedicated doc yet)* |

### Ported from snacks (planned — implementation ports in M1)

Accepted, with working implementations in the Python `snacks` stack, awaiting the Go port. No Houston design doc needed for most — the design is "port it."

| Platform | Codename | What it is |
|---|---|---|
| Billing | Golden Years | Subscription/payment via Stripe |
| Comms | Sound and Vision | Email transport (state-machine-backed) |
| Events | Five Years | Event bus / audit log — backbone other platforms subscribe to |
| Embeddings | Starman | Vector search / semantic matching |

Plus the spine capabilities tracked in `FEATURES.md`: multi-tenancy/RLS, RBAC, state machines, CRUD/schema pillar, actions pillar, background jobs, media & documents, full-text search, threads, scaffolding CLI, infra modules, frontend components, LLM orchestration.

### Planned / gaps (no design yet)

Named and slotted, not yet designed. Sequenced by real app demand in `../planning/` M6+, not speculatively.

| Platform | Codename | What it would be | Source |
|---|---|---|---|
| Object Explorer | Lazarus | Browse/search an app's entities | Foundry |
| Notebook | Moonage | Notebooks publishable as standalone apps | Hex |
| Automate | Ashes to Ashes | Condition-triggered actions on data | Foundry |
| Data Connection / Writeback | Station to Station | Ingest external data / sync back out | Foundry |
| Notifications | Speed of Life | Cross-channel hub (email + in-app + push) | Houston (promoted) |
| Ledger | Cash Girl | Double-entry accounting primitive | Houston (net-new) |
| Approvals | — | Human-in-the-loop sequenced sign-off chains | Foundry |
| Marketplace | Fame | Package/distribute reusable app templates | Foundry |
| Map | Ziggy | Geospatial analysis | Foundry |
| Model Studio | Sane | No-code ML training/deployment | Foundry |
| Notepad | Heroes | Collaborative reports embedding live data | Foundry |
| Feature flags | — | Per-tenant/per-app rollout flags | Houston (net-new) |
| Observability / APM | — | Logging, tracing, error monitoring across apps | Houston (net-new) |

## Also in this folder

- **[FEATURES.md](FEATURES.md)** — the exhaustive feature list with per-item Accepted/Pending/Rejected status. The catalog above is the platform-level view; FEATURES is the line-item view.
- **[platform_names.md](platform_names.md)** — the Bowie codename reference sheet and what's still available.

---

## Foundry mapping (living index)

Tracks, product by product, what Houston's equivalent of each non-defense Palantir Foundry/AIP product is. Gov/Gotham/mission-adjacent products are out of scope. Update this table whenever a platform thread gets designed. `Settled` / `Emerging` / `Redefined` / `Gap` describe the *design state* of the mapping; the catalog above tracks the build *stage*.

| Palantir product | What it does in Foundry | Houston equivalent | Design state | Notes / doc |
|---|---|---|---|---|
| **Ontology** | Semantic object/link/action layer every other tool consumes | `ent` schema + `huma` typed API | Settled | `many-backends-architecture.md`, `app-model-and-agents.md` |
| **Object Explorer** | Search/discovery over the Ontology | — | Gap | Likely folds into the frontend base layer (default entity browse/search view) rather than a separate product; not yet designed |
| **Workshop** | No-code drag-and-drop operational app builder | Schema-driven default UI + override layer | Emerging | Discussed but not yet written up as its own doc — needs one |
| **Slate** | Drag-and-drop app builder + full HTML/CSS/JS escape hatch | Full custom page layer (same substrate, same repo) | Emerging | Same doc gap as Workshop above |
| **Quiver** | Point-and-click object/time-series analysis, chainable cards, dashboards | Agent-authored analysis DSL (no GUI) | **Redefined** | `quiver-agent-dsl.md` — ties forward to the semantic object layer DSL (datafusion adapter, not yet documented) |
| **Contour** | No-code tabular analysis/aggregation at scale | Same mechanism as Quiver's replacement — agent + DSL + DuckDB workspace | Redefined (collapsed into Quiver's replacement) | See `quiver-agent-dsl.md` — both reduce to "agent queries + analyzes data" |
| **Map** | Geospatial analysis | — | Gap | Possibly a function-library extension of the agent DSL rather than a separate surface; not yet considered |
| **Model Studio** | No-code ML model training/deployment | — | Gap | No Houston ML training story yet |
| **Notepad** | Collaborative rich-text doc embedding live widgets | — | Gap | Loosely adjacent to an async agent task's "report" output (`app-model-and-agents.md`), but that's agent-authored, not collaborative live-editing |
| **AIP Logic** | Explicitly-authored agent/business-logic control flow over the Ontology | — | Gap | "Gap 2" vs. Foundry — Houston's bundled agent is auto-derived/generalist, not explicitly authored; some compliance-sensitive apps will want this shape |
| **AIP Chatbot Studio / Agent Studio** | Explicitly-configured conversational agent builder | Bundled, auto-derived agent | Settled (different shape, deliberately) | `app-model-and-agents.md` — zero-config: every app gets one from its API surface, no separate builder product |
| **AIP Evals** | Eval framework for agent/LLM output quality | — | Gap | No eval/testing framework for agent behavior yet; likely needed once the bundled agent ships |
| **Apollo** | Continuous deployment / ops control plane | ECS runner fleet + skill-driven local deploy | Settled (different shape, deliberately) | `many-backends-architecture.md` — Apollo deploys into single-tenant customer envs; Houston is many-tenant, cost-optimized for idle apps |
| **Automate** | Condition-triggered actions on Ontology objects | — | Gap | Distinct from just having `asynq` (on-demand/scheduled) — no "when object meets condition X, trigger Y" primitive yet; would subscribe to the Events bus once built |
| **Data Connection / Pipeline Builder / Code Workbook / Code Repositories** | Data ingestion + transformation pipelines from external sources | — | Gap | No equivalent — apps currently define their data model directly via `ent`; matters the moment an app must sync from a customer's existing system |
| **Writeback** | Sync transformed Foundry data back out to external systems | Houston's outbound/webhook mechanism | Gap | Decided direction: model outbound integrations as "writeback" rather than a generic webhooks bolt-on, paired with the Data Connection gap. Not yet designed |
| **Marketplace** | Package & distribute reusable "products" into other Foundry instances | Skills (`bootstrap-app` etc.) + future app templates | Partial | Skills cover "scaffold from a known-good pattern"; no equivalent yet for packaging/distributing a complete pre-built vertical-app module |
| **Approvals** (Actions-adjacent) | Human-in-the-loop sequenced sign-off chains on Actions | — | Gap | Narrowly scoped to human sequencing — deliberately split from event-driven logic (Automate/AIP Logic's job). Not yet designed |

### Notable collapses vs. Foundry

Where Houston deliberately ends up with *fewer* distinct products than Foundry, because the underlying mechanism is shared:

- **Contour + Quiver → one mechanism.** Both reduce, in Houston, to "an agent writes a query/analysis DSL and runs it against data pulled into a DuckDB workspace" — no separate no-code GUI, no "which tool do I open" decision.
- **AIP Chatbot Studio + (eventually) AIP Logic → one bundled agent**, if/when explicit-control-flow authoring gets added — one agent surface with a spectrum of builder control, not two products.

### Open threads

- `quiver-agent-dsl.md` forward-references a "semantic object layer DSL (datafusion adapter)" not yet documented — flagged, not designed.
- Workshop/Slate equivalent (the frontend plugin architecture) has been discussed at length but has no doc yet — should get one before it's lost to conversation history.
- Gaps with no Houston equivalent at all yet: Object Explorer, Map, Model Studio, Notepad, AIP Logic, AIP Evals, Automate, Approvals, the whole data-ingestion/pipeline layer (including Writeback), and Marketplace-style packaging. Not all need solving soon — listed so they're evaluated deliberately rather than discovered late.

### Non-Foundry platforms

The mapping above is scoped to the Foundry/AIP comparison. Capabilities outside it are tracked in `FEATURES.md`:

- **Ported from `snacks`**: auth/identity (incl. SSO/SAML), billing, comms (email transport), embeddings, form DSL, multi-tenancy/RLS, RBAC, state machine framework, CRUD/schema pillar, actions pillar, background jobs, events/audit log, media & documents, full-text search, threads, app scaffolding CLI, infra-as-code modules, frontend component platform, LLM orchestration.
- **Net-new to Houston**: **Ledger** (double-entry accounting — balances, journal entries, reconciliation, alongside Billing; confirmed absent from `snacks`, needs its own design doc). Also **Feature flags** and **Observability/APM** — both absent from `snacks`, standard platform-ops with no Foundry mapping.
- **Promoted to core platforms** (a `snacks` supporting mechanism elevated to first-class): **Notifications** — cross-channel hub unifying Comms + Threads + push behind one per-user preference/digest center; `snacks` has the channels but no unifying layer. **Events** — `snacks` already emits events off CRUD/state-machine transitions for audit; promoted because it's also the pub/sub backbone Automate, Approvals, and Notifications subscribe to once built.
