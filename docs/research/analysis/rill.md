# Rill

**What it is:** File-based BI — source/model/dashboard pipelines and YAML metrics views over DuckDB/ClickHouse, positioned explicitly for both human and agent consumption.
**Axis:** semantic layer, app-builder, agent.
**Depth:** thin.

## Products & surfaces

| Surface | What it is |
|---|---|
| **Rill** | Open-source (+ hosted) BI: `source → model → dashboard` pipeline defined entirely in files, backed by DuckDB or ClickHouse. |
| **Metrics views** | YAML definitions of dimensions/measures/timeseries — the semantic layer artifact. |
| **Metrics SQL** | A SQL-based query interface over the semantic layer, positioned for both human and agent querying. |
| **MCP server** | Lets agents (Claude, ChatGPT) query metrics and author dashboards/models directly. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| `source → model → dashboard` as folders/files | The entire pipeline — ingestion, transform SQL, dashboard config — lives in version-controlled files | yes |
| Metrics views in YAML | `type: metrics_view` with `timeseries`, `dimensions`, `measures` (measures as SQL expressions, e.g. `sum(price * quantity)`) | yes |
| `dimensions: "*"` wildcard | Expose all columns of a model as dimensions without enumerating them | maybe |
| Explicit "BI for humans and agents" positioning | Same metrics layer serves interactive dashboards and MCP-based agent queries | yes |

## Worth stealing

**The whole stack is files, including the semantic layer.** Sources, models (transform SQL), and dashboards are each their own file type in a folder structure — there's no "some of it is in files, some of it is in a database-backed config table" split. A metrics view is a YAML file with a `type: metrics_view`, a `timeseries` field, `dimensions` (column mappings, with a `"*"` wildcard to take all columns without enumeration), and `measures` (plain SQL expressions, e.g. `count(*)`, `sum(price * quantity)`) — the semantic layer artifact is diffable and reviewable exactly like the transform SQL upstream of it. Dashboards (`type: explore`) then reference a `metrics_view` and select which dimensions/measures to surface, rather than redefining logic.

**Explicit "agents are a first-class consumer" framing.** Rill's own tagline is "the fastest BI tool for humans and agents," and the mechanism backing that claim is concrete: an MCP server exposes the same metrics views to Claude/ChatGPT for natural-language querying, and because the whole model is files-on-disk, an agent (via Cursor or similar) can author or edit dashboards/models the same way a human developer would — through the file, not through a separate agent-specific API surface.

## Worth avoiding

Not enough independent evidence gathered on production-scale limits (query performance at high cardinality, ClickHouse vs. DuckDB tradeoffs in practice) to make an avoid-list claim here.

## Facts & figures

- Backing engines: DuckDB (local/embedded) and ClickHouse (scale/real-time).
- Open source: `rilldata/rill` on GitHub.

## Sources

- [Rill GitHub](https://github.com/rilldata/rill) · [Rill + ClickHouse](https://clickhouse.com/blog/rill) · [Introducing Metrics SQL](https://www.rilldata.com/blog/introducing-metrics-sql-a-sql-based-semantic-layer-for-humans-and-agents) · [Building your data pipeline in Rill](https://docs.rilldata.com/developers/build)
