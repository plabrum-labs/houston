# Cube

**What it is:** Open-source (Apache 2.0 core) semantic layer that sits between a warehouse and every downstream consumer — BI tools, embedded analytics, and AI agents — compiling a governed metrics model to SQL, with an optional caching/orchestration platform (Cube Cloud) on top.
**Axis:** semantic layer, data modeling, access policy, agent consumption pattern.
**Depth:** medium — access-policy mechanics and the MCP consumption pattern verified against current docs; some Cube Cloud specifics (pricing, deployment topology) not explored.

## Products & surfaces

| Product | What it is |
|---|---|
| **Cube Core** | Apache 2.0 semantic layer: cubes, views, joins, pre-aggregations, access policies. Self-hostable. |
| **Cube Cloud** | Managed platform: orchestration, caching infra, Rollup Designer, Chart Prototyping (Vizard), AI API, MCP server, deployment/tenant management. |
| **APIs** | SQL (Postgres-wire compatible), REST, GraphQL, and MCP — same governed model, four transports. |
| **MCP server** | Exposes the semantic model to MCP-compatible AI clients (Claude, ChatGPT, in-house agents) over HTTPS/OAuth. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Access policies** (`row_level`, `member_level`, `member_masking`) | Three-axis access control: rows, members, and a masked middle state | yes |
| **Composition algebra** | Members unite across policies; rows intersect per queried member; full access beats masking | yes |
| **Views as the only exposed surface** | Cubes are internal graph nodes; views are the governed, joined, curated public API | yes |
| **Pre-aggregations / rollups** | Materialized, matched-at-query-time summary tables; can force rollup-only mode | yes |
| **MCP server** | Model introspection + structured query tools over MCP, no client-authored SQL | yes |
| **Auto chart type** | Recharts integration picks a chart from query shape when no hint is given | maybe |
| **Jinja-based data modeling** | Templated YAML/Jinja for dynamic cube generation when no real compiler exists | maybe |

`Steal?` is a first-pass signal only, not a decision.

## Worth stealing

### Access policies: three states, not two

Cube's `access_policy` block composes three orthogonal controls per policy group, matched by security-context attributes (e.g., `userAttributes.userId`):

- **`row_level.filters`** — row axis. A list of `{member, operator, values}` filters; values can reference security-context attributes (`{ userAttributes.country }`).
- **`member_level.includes` / `excludes`** — member/field axis. `includes: "*"` or an explicit list; a policy with no `member_level` at all spans every member.
- **`member_masking`** — the third state. Requires `member_level` in the same policy. Members named in `member_level.includes` get full values; members named only in `member_masking.includes` return a masked value (defined per-dimension via a `mask.sql` transform) instead of being denied outright.

### The composition algebra, precisely

When a user matches multiple policy groups:

- **Members unite**: "A member is accessible if any matching policy grants it."
- **Rows intersect per queried member, but union across policies that grant that member**: for each member in the query, its visible-row set is the union of row filters from every policy that grants that member; the row actually returned must satisfy the visible-row set of **every** queried member simultaneously (an intersection across members, not policies).
- **Full access beats masking**: if any matching policy grants a member unconditional full access (`member_level`, no `row_level` filter), the real value wins. If the only grant is conditional (full access gated by a row filter), masking becomes conditional too — the generated SQL is effectively `CASE WHEN <row filter> THEN <value> ELSE <mask> END`.

Cube's own worked example: a user in both a `support` group (members `[status, count]`, rows filtered to `region='US'`) and a `finance` group (members `[count, revenue]`, rows filtered to `region='EU'`) querying `status, count` sees **US rows only** — because `status` is granted solely by the `support` policy, so rows outside its filter can never satisfy that member, even though `count` alone (queried without `status`) would return both regions' rows unioned.

This is a materially more precise algebra than most row-level-security systems, which typically only support row filters ANDed together with no member axis and no masked middle state.

### "Never expose cubes, expose views"

Cubes are the internal data-graph nodes (joins, raw measures/dimensions). **Views sit on top and are the only thing meant to be queried by consumers** — they compose members from multiple cubes into a flat, pre-joined, governance-scoped facade. Views are positioned explicitly as the "public API" of the semantic layer: the surface for "BI users, data apps, and AI agents" alike, not a separate consumer track per audience. View-level member rules **override** (not combine with) cube-level rules, while row filters combine — a specific asymmetry worth copying if a semantic layer needs a curated top layer over a wider raw graph.

### The consumption pattern the whole category converged on

Cube's MCP flow is the clean version of a pattern every semantic-layer product in this research set eventually lands on:

1. **Introspect** — the client (increasingly over MCP) discovers available measures/dimensions/descriptions from the governed model, not the warehouse schema.
2. **Structured request, not SQL** — the client names measures, dimensions, filters, time ranges. It does not author a query string.
3. **Compile with access rules applied** — the semantic layer turns the structured request into SQL with the user's row/member/masking policy baked in at compile time.
4. **Cache-then-execute** — the compiled query is matched against pre-aggregations first; only a miss reaches the warehouse.
5. **Governed results back**, with chart type auto-selected from the shape of the returned data if the client didn't specify one.

Cube's stated framing for why this matters for agents specifically: *"An agent acting for a single-tenant user cannot construct a query that returns another tenant's rows, because the layer never compiles one."* The security boundary is the compiler, not a prompt instruction or a post-hoc filter — the agent literally cannot express the unsafe query because it never writes SQL.

### Positioning line

Cube's marketing framing, useful as a target sentence for what a semantic layer is *for*: **"a governed semantic layer is what lets an AI analyst answer safely inside your product and keeps every tenant isolated by default."** Per-tenant security is applied at compile time so an embedded AI analyst "stays inside the customer's data" and every answer "ties back to the same numbers" as the BI dashboard and the embedded chart, because all three read the same certified metric.

### Pre-aggregations as the performance answer to "no client writes SQL"

Once queries are structured requests rather than arbitrary SQL, the layer can **match** a query's shape against a catalog of pre-aggregation (rollup) tables — materialized, grouped-and-summarized subsets of a cube — before ever reaching the source warehouse. `CUBEJS_ROLLUP_ONLY` mode can force every query through a rollup, guaranteeing the raw warehouse is never hit by ad hoc traffic (agent or human). This only works because the request space is structured and enumerable — free-form SQL can't be reliably matched against a rollup catalog.

### Jinja templating — the tell for "no compiler"

Cube's data models can be authored in YAML with embedded Jinja for dynamic generation (looping over a list of tables/columns to generate repetitive cube definitions, conditional member inclusion, etc.). This is worth noting as a category pattern, not just a Cube quirk: **templating is what a semantic layer reaches for once it needs to generate many similar model definitions and doesn't have a proper compiler/codegen path.** It's flexible but pushes correctness checking to runtime YAML rendering rather than a typed build step.

## Worth avoiding

- **MCP server docs are thin on the raw structured-query mechanics.** Public docs describe `listDeployments`, `chat`, and `loadQueryResults` tools and frame the primary interaction as natural-language chat rather than documenting a explicit "list measures / list dimensions / run query" tool contract. The introspect → structured-request → compile pattern is well established in Cube's own conceptual writing but not fully spelled out at the tool-schema level in the fetched docs — treat the MCP tool list above as partial.
- **Jinja templating has no type system.** It solves "define 200 similar cubes without repeating yourself" but a malformed loop or missing variable fails at render time, not at author time — the tradeoff for not having a real compiler.

## Facts & figures

- Cube Core is Apache 2.0 licensed.
- Access policies require `member_masking` to be paired with `member_level` in the same policy block (cannot mask without a defined member-level grant).
- Rollup-only mode is an environment variable (`CUBEJS_ROLLUP_ONLY`), not a per-query flag — it's a deployment-wide guarantee.
- Vendor-reported: "100+ SaaS companies" ship AI-powered customer-facing analytics on Cube, citing Brex ("Brex Spaces") and Webflow as named examples — unverified beyond Cube's own marketing page.

## Sources

- [Access policies](https://docs.cube.dev/docs/data-modeling/data-access-policies) (redirects from `cube.dev/docs/product/auth/data-access-policies`)
- [Row-level security](https://cube.dev/docs/product/auth/row-level-security) · [Member-level security](https://cube.dev/docs/product/auth/member-level-security)
- [Views reference](https://docs.cube.dev/reference/data-modeling/view) · [Introducing Views for metrics management](https://cube.dev/blog/introducing-views)
- [Pre-aggregations reference](https://cube.dev/docs/product/data-modeling/reference/pre-aggregations) · [Using pre-aggregations](https://cube.dev/docs/product/caching/using-pre-aggregations) · [Matching queries with pre-aggregations](https://cube.dev/docs/product/caching/matching-pre-aggregations)
- [MCP server docs](https://docs.cube.dev/docs/integrations/mcp-server) · [Unlocking Universal Data Access for AI with Anthropic's MCP](https://cube.dev/blog/unlocking-universal-data-access-for-ai-with-anthropics-model-context)
- [Semantic Layer for AI Agents (2026)](https://cube.dev/articles/semantic-layer-for-ai-agents-2026)
- [Embedded Analytics — AI-native, multi-tenant, governed](https://cube.dev/embedded-analytics)
- [What Is a Semantic Layer?](https://cube.dev/articles/what-is-a-semantic-layer)
- [Chart Prototyping / Vizard](https://cube.dev/docs/product/workspace/vizard) · [Introducing the AI API and Chart Prototyping](https://cube.dev/blog/introducing-the-ai-api-and-chart-prototyping-in-cube-cloud)
- **Not directly verified:** the literal phrase "the final data products for data consumers — BI users, data apps, and AI agents" was not found verbatim in currently reachable docs (closest is "facade of your whole data model with which data consumers can interact" plus separate marketing copy naming BI, embedded apps, and AI agents as the three consumer classes) — treat as paraphrase of consistent messaging, not a single sourced quote. MCP tool-level schema (exact tool names/args for model introspection) not found in a single authoritative reference.
