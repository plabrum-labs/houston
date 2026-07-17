# Hex

**What it is:** A reactive, DAG-based notebook (SQL + Python + no-code cells) that publishes to a drag-drop app, with an agent layered on both authoring and semantic modeling. The direct reference point for Houston's notebook-to-app plan.
**Axis:** app-builder, analysis, agent, semantic layer.
**Depth:** deep.

## Products & surfaces

| Surface | What it is |
|---|---|
| **Notebook view** | The logic surface — SQL, Python, R, and no-code cells wired into a reactive dependency graph. |
| **App Builder / App view** | Drag-drop presentation layer over the *same* cells as the notebook — a subgraph execution, not a separate artifact. |
| **Threads** | Conversational analytics surface for non-technical users, grounded in connections/semantic models, producing Explore-cell visualizations; toggles into a full notebook. |
| **Modeling Workbench** | Semantic model authoring — dimensions, measures, joins — with a Modeling Agent, diff view, and version history. |
| **Notebook Agent** | In-notebook AI that drafts/edits cells and app layout, with staged, reviewable changes. |
| **Context Studio** | Admin surface for thread/agent metadata — credit consumption, topics, spend — explorable in UI or pulled via CLI/API. |
| **Public API** | REST orchestration hook (`app.hex.tech/api/v1`) — run published projects, poll status, manage access/connections. Not a query API. |
| **Hex MCP server** (beta) | Exposes Hex to external agent clients (Claude Desktop/Code, Cursor, Codex, ChatGPT, Glean) — search projects, create/continue Threads, create/modify notebooks. |
| **Git export** | Bidirectional sync of a project (code + cell configuration) to a GitHub repo, with optional required-PR gating. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Reactive DAG via static analysis | Dependencies inferred from variable references across Python *and* SQL — no manual `ref()` wiring | yes |
| Parallel SQL execution | Independent SQL cells run concurrently (up to 8/connection, 4 for SSH/Redshift), gated on upstream completion and no conflicting writeback | yes |
| App-as-subgraph | Published app execution prunes cells not in the app, not code/writeback, with no downstream dependents, and not non-SELECT SQL | yes |
| Dataframe SQL + LazyDF | SQL cells query in-memory DuckDB over dataframes/CSVs; non-Python cells return a lazy handle instead of materializing pandas | yes |
| Three-layer caching (query / app default-state / published-refresh) | Distinct mechanisms for query reuse, instant-load stale display, and force-fresh-for-everyone | yes |
| Saved Views | Named, listable, schedulable combination of input/filter values | yes |
| Versioning as Git commits + YAML | Every save is a commit; cell *configuration* (not just code) is serialized, so chart/pivot/input changes are reviewable diffs | yes |
| "Can View App" role | Sees/comments on the published app only, no notebook or App Builder access | yes |
| Notebook Agent staged changes | All agent edits go through a cell-by-cell "Pending changes" accept/reject modal | yes |
| Agent Tasks | Schedules a recurring **prompt**, not a notebook, delivered to Slack/email | maybe |
| `design.md` brand file | Workspace-level style rules (colors, typography, spacing) the agent applies to every generative app | maybe |
| No push webhooks on the API | Orchestration is poll-only | no (limitation, not a feature) |

## Worth stealing

### Execution model: DAG inferred by static analysis, not declared

Hex's compute engine performs **static analysis of variable references** across Python and SQL cells to build the dependency graph automatically — no manual wiring, no dbt-style `ref()`. Running any cell computes its upstream and downstream closure. Hex explicitly frames this as fixing three failure modes of traditional notebooks, citing Joel Grus's "I Don't Like Notebooks" (JupyterCon): **interpretability** (out-of-order execution makes state impossible to reason about), **reproducibility** (a change now triggers "a predictable, consistent set of re-computes"), and **performance** (no wasteful full re-runs, especially in published apps). The design touchstones named in the Hex 2.0 post are **Excel recalculation** and orchestration DAGs (**Airflow, Dagster, dbt**) — the claim is that reactive-notebook and DAG-orchestration models both avoid the state problem that plagues kernel-backed notebooks, and Hex is deliberately building the notebook-authoring side of that same shape.

The one documented failure mode: **`globals()` defeats reference detection**. Hex's own docs warn that creating or referencing variables via `globals()` "is not advised" because it breaks reactivity — cells stop re-running when their inputs change, or error unpredictably. This is the explicit tax of static-analysis-based reactivity: anything that obscures a variable reference from the analyzer breaks the model. ([Execution model docs](https://learn.hex.tech/docs/explore-data/projects/project-execution/execution-model), [Hex 2.0 post](https://hex.tech/blog/hex-two-point-oh/))

### Parallel execution with connection-aware concurrency caps

SQL cells run concurrently once (1) all upstream dependencies have completed and (2) no upstream writeback or non-SELECT statement on the same connection is still in flight. Concurrency is capped **per connection type**: **up to 8** for most connections, **up to 4** for SSH tunnels and Redshift specifically (source: Hex docs, exact figures not independently cross-verified beyond the docs page). Each warehouse SQL cell opens its own database session — which is *why* parallelism is possible, but also means two statements needing shared session state must live in one cell. Users can disable reordering entirely via an "allow execution reordering" environment setting. ([Execution model docs](https://learn.hex.tech/docs/explore-data/projects/project-execution/execution-model))

### Published apps are a pruned subgraph, not a separate build

An app is **the same cells as the notebook**, executed as a subgraph. Cells are *never* skipped if they're explicitly in the app, are code or writeback cells, have downstream dependents, or are non-SELECT SQL (DDL, writes). Everything else — most commonly a SQL cell that was scratch work and isn't referenced downstream — is skipped on app runs, including scheduled runs. This means the notebook/app relationship isn't "export a copy," it's "the app is a live view that computes a subset of the same graph on every run." ([Execution model docs](https://learn.hex.tech/docs/explore-data/projects/project-execution/execution-model))

### Dataframe SQL and LazyDF — DuckDB as the connective tissue between cells

SQL cells can target either a warehouse connection or **in-memory DuckDB running over dataframes and CSVs** — you write `FROM my_dataframe` the way you'd write a table name. This makes SQL → Python → SQL chains over the same in-memory data reactive and typed like everything else. The performance trick underneath: **LazyDF**. A non-Python cell (SQL, Chart, Pivot, etc.) doesn't materialize a pandas dataframe by default — it returns a lightweight lazy handle, and any downstream cell can run DuckDB SQL directly against the LazyDF's underlying Feather-backed data. Hex reports this avoids "streaming tons of data down into the Python kernel" for every intermediate step and cites **5–10x project runtime improvements** (vendor-reported). ([Lazy dataframes post](https://hex.tech/blog/lazy-dataframes/), [SQL cells intro](https://learn.hex.tech/docs/explore-data/cells/sql-cells/sql-cells-introduction))

### Cell taxonomy spans code and no-code, all in the same graph

SQL (warehouse or dataframe), Python, R, Markdown/Text, **Input parameters** (text, number, date, date-range, boolean, dropdown/multi-select), Chart, Map, Table display, **Single value** (KPI), Pivot, Filter, Explore, Writeback, and Semantic/Metrics cells all participate in the same reactive graph — a no-code Pivot cell and a hand-written Python cell are dependency-graph peers. Chart and Pivot cells were made to **run in parallel** rather than serially as of mid-2026. ([No-code cells post](https://hex.tech/blog/introducing-no-code-cells/), [2026-07-08 changelog](https://learn.hex.tech/changelog/2026-07-08))

### App Builder: one set of cells, two presentations

Every project has a Notebook view (logic) and an App view (presentation) over the *same* cells — rows, proportional sizing, resize handles, tabs, full-width blocks, an auto-generated table of contents from markdown headers, per-project metadata (name/description/author/last-modified/categories/status), light/dark/user-preference theming (custom CSS and up to 5 custom themes on Enterprise, 1 on Team), and per-cell display mode (source only / output only / both). **The same cell can appear on multiple tabs.** Critically, **execution still follows notebook order, not app layout** — the app-view arrangement is purely presentational and doesn't reorder the DAG. The Notebook Agent can draft and edit the app layout directly ("create a Hex app via the agent with one prompt," shipped ~April 2026). ([App builder docs](https://learn.hex.tech/docs/share-insights/apps/app-builder), [Custom styling](https://learn.hex.tech/docs/administration/workspace_settings/workspace-custom-styling))

### Parameterization: inputs are just variables, addressable by URL and Jinja

Input cells are plain Python variables downstream, or interpolated into SQL via Jinja (`{{ input_1 }}`). Each input has a **Label** (display) separate from its **Name** (variable identifier). Input values on a published app are settable via **URL query params** — turning any app into a parameterized report link without custom routing code. **Saved Views** bundle a named combination of input/filter values, are listable to other users, and are independently **schedulable** — a scheduled run can be pointed at up to three Saved Views instead of running with defaults. ([Saved views docs](https://learn.hex.tech/docs/share-insights/apps/saved-views), [Saved views launch post](https://hex.tech/blog/introducing-saved-views/))

### Three distinct caching layers — don't conflate them

1. **SQL query cache** — identical query text run within the last 60 minutes reuses results, in both notebook and app.
2. **App "cache default state"** — opening a published app renders the *previous run's* output immediately with zero compute; if stale past a configured timeout, Hex kicks off a background refresh that **ignores the SQL cache** to force freshness, then updates the published output for everyone.
3. **Published-results refresh** — an explicit refresh (manual or scheduled) updates the app's displayed results **for every viewer**, not just the person who triggered it. Scheduled runs by editors **bypass the SQL cache by default**, writing fresh results back into it so subsequent cache hits are current.

This is a genuinely three-way distinction most BI tools collapse into one "cache" toggle. ([SQL query caching docs](https://learn.hex.tech/docs/explore-data/cells/sql-cells/query-caching), [App run settings](https://learn.hex.tech/docs/share-insights/apps/app-run-settings))

### Scheduling and notification primitives

Cron scheduling on Team/Enterprise, simple intervals (hourly/daily/weekly/monthly) on Professional, **max hourly** frequency. **Subscriptions** deliver the app link via email or Slack (Slack requires Team+) on run completion or on error. **Conditional notifications** fire only if a condition evaluates true post-run — alerting without a separate alerting product. Schedules run with default input values unless pointed at a Saved View. Two built-ins let code distinguish contexts: **`hex_scheduled`** (boolean, true during scheduled runs) and **`hex_run_context`**, so writebacks or side effects can be guarded to fire only on scheduled runs. ([Scheduled runs docs](https://learn.hex.tech/docs/share-insights/scheduled-runs), [App notifications docs](https://learn.hex.tech/docs/share-insights/app-notifications))

### Agent Tasks — the scheduled unit is a prompt, not a notebook

Shipped June 2026: schedule a **recurring agent prompt** delivered to Slack or email — "weekly standup summary," "metric checks." The recommended workflow is to draft and validate the prompt inside Threads first, then attach a schedule. This is a different abstraction from scheduled notebook/app runs: the artifact being scheduled is conversational instruction, not a pinned computation graph. ([2026-06-16 changelog](https://learn.hex.tech/changelog/2026-06-16))

### Versioning: every save is a Git commit, including cell configuration

Every saved version is a commit on a GitHub branch; the published version tracks `main`. The critical detail: **the project is serialized as YAML describing cell configuration, not just code** — so changing a chart's aggregation, a pivot's grouping, or an input's default value produces a reviewable diff, not just a black-box config blob. Optional **"require PR"** gates publishing on an approved and merged pull request. Sync is bidirectional — edits made outside Hex (in the repo) pull back in. ([Git export docs](https://learn.hex.tech/docs/explore-data/projects/git-export), [GitHub sync post](https://hex.tech/blog/github-sync/))

### Permissions: a role that can see outputs but never logic

**"Can View App"** grants viewing and commenting on the published app **only** — no access to the notebook or App Builder, no duplicate/modify/share. Sharing is layered: a workspace-level "Share to web" toggle gates whether *any* project can go public at all; per-project sharing can then be scoped to the workspace or "anyone with the link"; a **Public group** exists specifically for web-app viewers who aren't workspace members (i.e., people with a link but no seat). ([Project sharing docs](https://learn.hex.tech/docs/collaborate/sharing-and-permissions/project-sharing))

### Notebook Agent: broad context, but changes are always staged

Context assembled for the agent = current notebook (always) + data connections + semantic models + workspace rules + Hex's own product docs + other named projects (their structure, code, **and outputs** — not just schema). The agent can create Python, SQL, Markdown, **Pivot, Input, Single-value, Chart** cells and edit app layout. Every agent change is staged behind a **"Pending changes" modal** that walks through cell-by-cell accept/reject; selecting a pending cell jumps you to it in context. Requires Editor+ role and Can Edit+ on the project; **not available on published apps** (agent editing is a notebook-only capability). Two distinct repair modes: **"Fix with agent"** (multi-cell debugging) vs. **"Quick fix"** (syntax-level). Per-thread model and reasoning-effort picker, a workspace default model, and an "Auto" mode. ([Notebook agent docs](https://learn.hex.tech/docs/explore-data/notebook-view/notebook-agent))

### Threads: a second, non-technical entry point that upgrades into the real thing

Threads is a conversational surface grounded in connections, semantic models, and endorsed tables, producing **Explore-cell** visualizations that are "fully interactive... and you can click into them at any time to edit and work with them more deeply." Critically there's a **toggle from a Thread into a full notebook** — the conversational surface isn't a dead end, it's an on-ramp. The workspace homepage is now a prompt bar into Threads. It's also Hex's first mobile-tuned surface. (Public beta on Team/Enterprise as of Fall 2025.) ([Fall 2025 launch post](https://hex.tech/blog/fall-2025-launch/), [Threads docs](https://learn.hex.tech/docs/explore-data/threads))

### 2026 changelog as a competitive clock

Selected shipped items, roughly chronological: agent web search via **Parallel** (search the open web and synthesize alongside data, or paste a URL for extraction) — on by default for Professional/Team/Enterprise; mid-conversation **model switching** in Threads plus a workspace default model; prompt queuing; image/file upload to the agent; **one-prompt app creation** ("create a Hex app via the agent with one prompt"); dual-axis and reference-line charts; **`design.md`** workspace brand file (colors, typography, spacing, style rules) that the agent applies to every generative app, with the agent able to draft the file from existing brand guidelines; Hex made callable from **Claude (Desktop/Code), Cursor, Codex, ChatGPT, Glean** via an MCP server (beta), and from **Google Sheets** separately; a **Figma connector** letting the Figma agent pull Hex data into design files; **Context Studio** exposing thread/agent metadata (credit, topic, spend) via CLI/API, not just UI; **per-user/group monthly credit allocations and spend limits** for admins. Generative app code is now exportable/importable as YAML. This cadence — an agent feature roughly every 2–4 weeks through H1 2026 — is itself the notable fact: Hex is iterating the agent surface faster than the underlying notebook primitives. ([Changelog index](https://learn.hex.tech/changelog))

### Semantic layer as a source, not a walled garden

**Semantic Model Sync** persistently syncs datasets, measures, dimensions, and joins from third-party semantic layers — **dbt Semantic Layer (MetricFlow)**, **Cube**, and (private beta) **Snowflake Semantic Views** — into Hex's no-code Explore experience. Hex is a founding-ish participant in the **Open Semantic Interchange** initiative (Snowflake-led, with dbt Labs, Salesforce, ThoughtSpot, Sigma, Omni, and others) aiming at a vendor-neutral semantic-definition standard. The architectural choice that matters: the **Metrics/Semantic cell returns a dataframe**, which flows into any downstream cell — chart, pivot, filter, Dataframe SQL — exactly like any other cell output. The semantic layer is one more data source into the same reactive graph, not a separate walled-off query mode. Semantically-enriched Explore cells are chainable into SQL/Python cells the same way. The **Modeling Agent** synthesizes semantic models directly from existing Hex project code (`@mention` a project, agent inspects code and joins multiple semantic models), with a **diff view** for proposed changes and a **version history** that records drafts, published versions, and agent-generated checkpoints — including a checkpoint taken automatically before the agent makes a change. ([Semantic Model Sync intro](https://learn.hex.tech/docs/connect-to-data/semantic-models/semantic-model-sync/intro), [Snowflake Semantic Views post](https://hex.tech/blog/introducing-snowflake-semantic-sync-aisql/), [Semantic authoring post](https://hex.tech/blog/introducing-semantic-authoring/))

## Worth avoiding / limits

### The API is an orchestration hook, not a query interface — and it's poll-only

`RunProject` and friends live at `app.hex.tech/api/v1`, rate-limited to **20 requests/minute and 60/hour**. That ceiling is telling: this API is sized for "kick off a scheduled/programmatic run and check on it later," not for interactive or high-frequency use. There is **no push/webhook mechanism** for run completion — callers must poll `GetRunStatus` or `GetProjectRuns`. Anyone building automation on top of Hex needs to budget for polling latency and rate-limit headroom. ([API reference](https://learn.hex.tech/docs/api/api-reference))

### Collaboration is deliberately not CRDT/OT — and says so

Hex's engineering blog ("A Pragmatic Approach to Live Collaboration") is explicit that they rejected full CRDT/OT in favor of **cell-level locking + presence**: a user editing a cell acquires a lock and is the only one who can edit it until release or takeover. This is a real, named trade-off — Hex says the cell-based, notebook-style UI makes fine-grained conflict resolution unnecessary, at the cost of not supporting things like simultaneous multi-user text editing within one cell. Reported as shipped in under 6 weeks. This is worth reading as a case for "locking is fine when the unit of collaboration is a cell, not a character" — the opposite bet from Figma/Notion-style CRDT editors. ([Pragmatic collaboration post](https://hex.tech/blog/a-pragmatic-approach-to-live-collaboration/))

## Facts & figures

- Pricing (vendor site, 2026): Community free; **Professional $36/editor/month**; **Team $75/editor/month** (third-party trackers cite higher list pricing, $149–199/creator/month, for Team-tier annual contracts — treat as unverified/contradictory); **Enterprise** custom.
- SQL query cache window: **60 minutes**.
- Parallel SQL concurrency: **8 per connection**, **4 for SSH/Redshift**.
- Scheduling frequency floor: **hourly** (max).
- API rate limits: **20 req/min, 60 req/hour** on `RunProject`.
- Custom app themes: **1 (Team) / 5 (Enterprise)**.
- Saved Views per scheduled run: **max 3**.
- Semantic project ingestion-by-zip API: **3 requests/minute** (separate, tighter limit than RunProject).
- LazyDF-driven runtime improvement: **5–10x** (vendor-reported, not independently verified).
- Investors reported: 137 Ventures, Dash VC, Liquid 2 Ventures, Lorimer Ventures (via PitchBook); a Hashboard acquisition is referenced by third-party trackers but not directly verified against a Hex primary source in this pass.

## Sources

- [Execution model](https://learn.hex.tech/docs/explore-data/projects/project-execution/execution-model) · [Hex 2.0: Reactivity, Graphs, and a little bit of Magic](https://hex.tech/blog/hex-two-point-oh/) · [Beyond linear notebooks](https://hex.tech/blog/beyond-linear-notebooks/)
- [SQL cells introduction](https://learn.hex.tech/docs/explore-data/cells/sql-cells/sql-cells-introduction) · [SQL query caching](https://learn.hex.tech/docs/explore-data/cells/sql-cells/query-caching) · [Lazy dataframes](https://hex.tech/blog/lazy-dataframes/) · [No-code cells](https://hex.tech/blog/introducing-no-code-cells/) · [Pivot cells](https://learn.hex.tech/docs/explore-data/cells/transform-cells/pivot-cells)
- [App builder](https://learn.hex.tech/docs/share-insights/apps/app-builder) · [App configuration options](https://learn.hex.tech/docs/build-apps/app-configuration-options) · [Custom styling](https://learn.hex.tech/docs/administration/workspace_settings/workspace-custom-styling) · [App run settings](https://learn.hex.tech/docs/share-insights/apps/app-run-settings)
- [Saved views](https://learn.hex.tech/docs/share-insights/apps/saved-views) · [Introducing Saved Views](https://hex.tech/blog/introducing-saved-views/) · [Scheduled runs](https://learn.hex.tech/docs/share-insights/scheduled-runs) · [App notifications](https://learn.hex.tech/docs/share-insights/app-notifications) · [Agent Tasks changelog](https://learn.hex.tech/changelog/2026-06-16)
- [Git export](https://learn.hex.tech/docs/explore-data/projects/git-export) · [Using Hex + Snowflake with Git / GitHub sync](https://hex.tech/blog/github-sync/)
- [Project sharing](https://learn.hex.tech/docs/collaborate/sharing-and-permissions/project-sharing)
- [Notebook agent](https://learn.hex.tech/docs/explore-data/notebook-view/notebook-agent) · [Introducing Notebook Agent](https://hex.tech/blog/introducing-notebook-agent/)
- [Threads docs](https://learn.hex.tech/docs/explore-data/threads) · [Fall 2025 Launch](https://hex.tech/blog/fall-2025-launch/) · [Introducing Threads](https://hex.tech/blog/introducing-threads/)
- [Semantic Model Sync intro](https://learn.hex.tech/docs/connect-to-data/semantic-models/semantic-model-sync/intro) · [Introducing Snowflake Semantic Sync + AISQL](https://hex.tech/blog/introducing-snowflake-semantic-sync-aisql/) · [Introducing Semantic Authoring](https://hex.tech/blog/introducing-semantic-authoring/) · [Modeling Workbench](https://learn.hex.tech/docs/connect-to-data/semantic-models/semantic-authoring/semantic-authoring-overview)
- [Public API overview](https://learn.hex.tech/docs/api-integrations/api/overview) · [API reference](https://learn.hex.tech/docs/api/api-reference) · [Hex MCP server](https://learn.hex.tech/docs/api-integrations/mcp-server) · [Announcing orchestration integrations + public API](https://hex.tech/blog/announcing-orchestration-public-api/)
- [A Pragmatic Approach to Live Collaboration](https://hex.tech/blog/a-pragmatic-approach-to-live-collaboration/) · [Real-time collaboration docs](https://learn.hex.tech/docs/collaborate/real-time-collaboration)
- [Changelog index](https://learn.hex.tech/changelog) · [2026-06-11 (web search, model picker)](https://learn.hex.tech/changelog/2026-06-11) · [2026-07-08 (generative app controls)](https://learn.hex.tech/changelog/2026-07-08) · [2026-04-14 (agent on Hex apps)](https://learn.hex.tech/changelog/2026-04-14) · [2026-05-14 (repos as agent context)](https://learn.hex.tech/changelog/2026-05-14)
- [Hex pricing](https://hex.tech/pricing/)
- **Not directly verified:** exact Team-tier list pricing (vendor site vs. third-party trackers disagree, $75 vs. $149–199); Hashboard acquisition (third-party only); full RunProject rate-limit rationale; whether SSH/Redshift concurrency cap of 4 applies identically across all warehouse variants under SSH tunneling.
