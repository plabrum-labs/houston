# Analysis

**What this category is:** notebook, BI, and semantic-layer tools for exploring and presenting data — reactive notebooks (Hex, marimo, Deepnote, Count), code-first/static BI (Observable, Evidence, Rill), and live-warehouse BI (Omni, Lightdash, Sigma, Metabase).
**Why it's in this research:** analysis, app-builder (notebook-to-app), semantic layer, agent (agentic notebooks and BI copilots).
**Files:** 11.

## The players

| Company | What it is | Depth |
|---|---|---|
| [hex](hex.md) | Reactive DAG notebook (SQL+Python+no-code) that publishes to a drag-drop app over the same cells; agent layered on both authoring and semantic modeling. The direct reference point for a notebook-to-app plan | deep |
| [marimo](marimo.md) | Open-source reactive Python notebook whose file format is a plain, valid `.py` module, not JSON | thin |
| [deepnote](deepnote.md) | Jupyter-compatible cloud notebook with a fully autonomous "Auto AI" agent mode and an open block-schema package | thin |
| [count](count.md) | Killed its SQL notebook UI, rebuilt around an infinite canvas — the category's explicit counter-bet against structure | thin |
| [observable](observable.md) | Static site generator for data apps; data loaders run once at build time, viewers issue zero live queries | thin |
| [evidence](evidence.md) | "BI as code" — named SQL in markdown fences, compiled to a static site at build time | thin |
| [rill](rill.md) | File-based BI — source/model/dashboard pipeline and YAML metrics views over DuckDB/ClickHouse, explicitly positioned for humans and agents | thin |
| [omni](omni.md) | BI with a three-layer data model (schema/shared/workbook) and a field-promotion workflow between them | thin |
| [lightdash](lightdash.md) | Open-source BI built directly on a dbt project; dashboards-as-code, agent writes go through PR review | thin |
| [sigma](sigma.md) | Spreadsheet-grid UI compiled to live SQL; writeback tables (Input Tables, Sigma Tables) make it a lightweight operational app builder | thin |
| [metabase](metabase.md) | Open-source BI — point-and-click query builder, multiple embedding tiers | thin |

**Hex is the reference implementation by a distance** — the only deep file, and the only one with independently verified execution-model, caching, and agent-context mechanics rather than a single-pass docs summary. Every other file in this category is thin (single-source, one research pass); read them as directional data points that corroborate or complicate the Hex-centric picture, not as equally-weighted peers.

## Convergence

**The reactive DAG is winning, but two credible dissenters exist for structurally different reasons.** Hex infers its dependency graph via static analysis of variable references across Python *and* SQL — no manual `ref()` wiring — explicitly citing Excel recalculation and orchestration DAGs (Airflow, Dagster, dbt) as its design touchstones (`hex.md`). marimo independently converges on the same reactive-by-default model, but ships it as **cells-that-are-functions-in-a-real-`.py`-file** rather than a proprietary graph engine — "notebook is a Python module," diffable, importable, pytest-collectible (`marimo.md`). Rill converges on files-as-the-substrate too, but for the *semantic layer specifically* — sources, models, and dashboards (including the metrics-view YAML) are each their own file type in a folder structure, no database-backed config split (`rill.md`). **Count is the one deliberate dissent** — it killed its SQL notebook UI for an infinite canvas, and this research explicitly names the cost: an infinite canvas has no natural linear order to diff against and no stable cell-addressing scheme for an agent to target, which is exactly the opposite of where Hex, marimo, and Rill are all moving (`count.md`). Three-versus-one, converging independently from different starting points (notebook UX, file format, semantic-layer storage), is a strong signal that structure — DAG, typed cells, file-based format — is what makes both version control and agent editing tractable, with Count as the explicit counter-data-point that a stakeholder-colocation motivation can exist without buying into that structure.

**Build-time static compilation is a second, independent convergence — Observable Framework and Evidence arrive at the identical tradeoff from different starting syntaxes.** Observable: data loaders run once at build, the published site ships pre-computed static snapshots, viewers issue zero live queries and need no warehouse credentials. Evidence: named SQL in markdown fences, compiled once at build into static HTML+JS with no runtime warehouse dependency. Both explicitly trade freshness (a rebuild is required to update data) for instant, credential-free distribution — the sharpest possible contrast to Hex/Sigma's "every page view is a live query" model (`observable.md`, `evidence.md`).

**The "promotion path" from ungoverned to governed is a named convergence between Omni and dbt-native BI tools, independently solving the same tension.** Omni's workbook model sits above its schema/shared layers specifically so an analyst can build a field ad hoc and then explicitly **promote** it upward into the governed model — "a path, not just a gate" (`omni.md`). Lightdash solves an adjacent version of the same problem by routing *agent* writes to the dbt project through the identical pull-request review as human writes — "don't build a separate trust tier for agent output, route it through the review mechanism you already have" (`lightdash.md`). Both are responses to the same underlying failure mode named in `omni.md`: most BI tools either block ad hoc fields entirely (analysts route around the tool) or let them live forever ungoverned (nothing is ever trustworthy) — Omni and Lightdash independently reject both horns.

**Row/column-level and derived-value/trigger-graph boundaries recur here too, cross-referencing the other categories.** Hex's three-layer caching model (query cache / app default-state / published-refresh-for-everyone) is a finer-grained version of the general "don't collapse distinct cache semantics into one toggle" lesson. Multi-tenant embedded-analytics vendors (Cube, Luzmo, Explo, Qrvey, Toucan, cited in `metabase.md`) converge on **architectural, token-enforced tenant isolation from day one** as opposed to Sigma's own admission that it grew up single-tenant/team-segmented first and had to retrofit "Sigma Tenants" as a separately-launched, distinct capability (`sigma.md`, `metabase.md`) — directly parallel to the citizen-developer and app-builder categories' recurring "retrofitting isolation is possible but is a distinct, later feature, not free from the base architecture" lesson.

## Worth stealing

- **Hex's DAG-as-subgraph app model**: the published app is the *same cells* as the notebook, executed as a pruned subgraph — never a separate export/build — see `hex.md`.
- **Hex's three distinct caching layers** (query cache, app cached-default-state, published-refresh-for-everyone) — most BI tools collapse this into one "cache" toggle — `hex.md`.
- **Hex's staged agent edits**: every agent change goes through a cell-by-cell "Pending changes" accept/reject modal, never applied directly — `hex.md`.
- **marimo's lazy/stale runtime mode**: a cell edit marks descendants *stale* without auto-executing them, and stale ancestors are still force-run before a dependent executes — reactivity's correctness guarantee without paying for every downstream recompute on every edit — `marimo.md`.
- **Deepnote Auto AI's read-execute-adapt loop**: the agent executes each block it writes and uses the actual output as context for the next block, closing the "generate code, hope it's right" gap most AI-coding features leave open — `deepnote.md`.
- **Lightdash's Preview Projects**: a full, isolated environment spun up per dbt PR against dev data, so a reviewer sees the dashboard actually render, not just a YAML diff — `lightdash.md`.
- **Sigma's Input Tables / Sigma Tables**: writeback as native `INSERT`/`UPDATE` against warehouse tables any workbook/app/script/agent can read or write — the warehouse table itself, not a proprietary API, is the integration point — `sigma.md`.
- **Omni's field-promotion workflow** (workbook → shared model → schema) as the resolution to governed-vs-ad-hoc tension — `omni.md`.
- **Rill and Hex both treating the semantic layer as "one more source into the reactive graph," not a walled garden** — Rill's metrics views are files an agent edits like any other file; Hex's Semantic/Metrics cell returns a dataframe that flows into any downstream cell exactly like a SQL result — `rill.md`, `hex.md`.

## Worth avoiding

- **Count's infinite canvas as a target for agent-driven editing or git-diff review** — no natural linear order, no stable cell-addressing scheme, spatial layout carries meaning a text diff can't represent. A coherent bet for stakeholder colocation, a poor one for anything AI-authored (`count.md`).
- **Hex's own documented reactivity failure mode**: `globals()` defeats static-analysis dependency detection — anything that obscures a variable reference from the analyzer breaks reactivity silently (`hex.md`).
- **Hex's API is poll-only, no push/webhook** for run completion, rate-limited to 20 req/min — sized for "kick off a scheduled run and check later," not interactive or high-frequency orchestration (`hex.md`).
- **Sigma's retrofit tenant isolation** — grew up single-tenant/team-segmented, added "Sigma Tenants" as a later, separately-launched, architecture-level capability rather than a day-one guarantee (`sigma.md`).
- **Full-app iframe embedding as a default** (Metabase, and implicitly Sigma pre-Tenants) — reads as a foreign, boundary-visible block with no way to inherit the host's design system; every vendor with a component-level SDK treats iframe embedding as a fallback, not a target (`metabase.md`).

## Gaps

- **No independent evidence in this survey on Deepnote Auto AI's containment** during unattended runs (sandboxing, spend caps, writeback confirmation) — flagged as an open question, not a confirmed gap, since autonomous execution against live compute/data is exactly the surface needing the most guardrails.
- **Nobody in this category has published production-scale limits** for the file-based/agent-native BI tools (Rill's query performance at high cardinality, ClickHouse vs. DuckDB tradeoffs in practice) — thin research depth across the board here.
- **Omni's promotion workflow friction is unverified** — how much manual review promotion requires, whether it triggers re-testing, wasn't confirmed beyond vendor/partner marketing pages.

## Notes

- Depth is heavily skewed toward Hex; every other file in this category is a thin, single-pass research artifact — treat comparative claims between Hex and the others as asymmetric in confidence, not just in content.
- Hex's Team-tier pricing is contradictory across sources ($75/editor/month per the vendor site vs. $149–199/creator/month per third-party trackers) — unresolved in this pass.
- Hex's LazyDF 5–10x runtime-improvement figure and its Hashboard-acquisition mention are vendor-reported/third-party-only, not independently verified.
- Omni's "one of the few BI platforms with bidirectional dbt sync" claim is vendor/partner-sourced, not independently benchmarked against competitors.
- Sigma's "grew up single-tenant-first" framing is this research folder's paraphrase of Sigma's own launch-post framing plus third-party review commentary, not a direct Sigma quote.
