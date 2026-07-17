# Malloy

**What it is:** An open-source modeling and query language (originally from Google, now community/Malloy Data maintained) that unifies the semantic model and the query language into one syntax, compiling to SQL for BigQuery, Postgres, Snowflake, MySQL, Trino/Presto, and natively DuckDB.
**Axis:** semantic layer, query language design, join-correctness.
**Depth:** medium — join/graph semantics and nesting mechanics verified against current docs; ecosystem tooling (Composer, Explorer UI, MCP server) noted but not deeply explored.

## Products & surfaces

| Product | What it is |
|---|---|
| **Malloy language** | The core: a combined semantic-model + query language, compiled to SQL. |
| **`malloy` npm / PyPI packages** | Compiler libraries embedding Malloy in JS/TS and Python toolchains. |
| **Explorer UI** | Point-and-click exploration surface over a published Malloy model. |
| **`malloyyo` (MCP server)** | Serves a Malloy semantic model over MCP so any MCP-compatible AI client queries through the governed model. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Unified model + query language** | One syntax defines the semantic model and expresses queries against it — no separate DSL/query-string split | yes |
| **Data graph preserved through joins** | Joins don't flatten to one table space; the graph persists so aggregates can be computed at the correct locality | yes |
| **Structural fan/chasm-trap prevention** | Aggregate calculations navigate the graph to deduce correct computation locality — solved in the language, not by a runtime rewrite or a modeling convention | yes |
| **Nested queries → aggregating subqueries** | `nest:` compiles to a subquery producing one subtable per parent row, arbitrarily deep | yes |
| **Composability** | Queries and joined sources can be reused as sources for further queries, function-composition style | yes |
| **Multi-dialect compilation** | Same model compiles to BigQuery, Postgres, DuckDB (and others) SQL | maybe |

`Steal?` is a first-pass signal only, not a decision.

## Worth stealing

### The only design in the category that solves fan-out structurally

Malloy's own framing: *"When two sources are joined, Malloy retains the graph nature and hierarchy of the data relationships... unlike SQL, which flattens everything into a single table [space]."* Because the graph survives the join, *"aggregate calculations navigate this graph to deduce the locality of computation, so they are always computed correctly regardless of join pattern, avoiding the fan and chasm traps."*

This is the direct structural counterpart to Looker's symmetric aggregates (see `looker.md`) — same underlying bug class (join fanout inflating `SUM`/`COUNT`), opposite fix location:

- **Looker**: raw SQL semantics are unchanged; a runtime rewrite (`SUM(DISTINCT hash(pk) + val) - SUM(DISTINCT hash(pk))`) is triggered by metadata the modeler declared (primary key + join cardinality). Get the declaration wrong and the safety net doesn't fire.
- **Malloy**: the query language itself never lets you express an ambiguous aggregate. The graph relationship is a property of the *join itself* as written in the model, not a side declaration a modeler could omit or mismatch. There's no "forgot to mark `relationship: one_to_many`" failure mode, because the language's own semantics track locality directly.

This is the sharper argument of the two for language-level design over convention-plus-runtime-repair: it removes an entire class of "declared the wrong thing" errors rather than catching them with a safety net.

### Nested queries compile to safe aggregating subqueries

`nest:` inside a query produces, per the docs, *"an aggregating subquery, which produces a subtable per row in the view in which it is embedded"* — and nesting can go arbitrarily deep (a nested view containing another nested view). Concretely:

```malloy
run: airports -> {
  group_by: state
  aggregate: airport_count
  nest: by_facility is {
    group_by: fac_type
    aggregate: airport_count
  }
}
```

produces one row per `state`, each carrying a `by_facility` array scoped only to that state's airports — a genuinely nested result set, not a flattened join that has to be regrouped client-side. The underlying compiled SQL uses `CROSS JOIN`-style group-set generation, `CASE WHEN`-scoped conditional aggregation per nesting level, and `LIST()`-style aggregation to assemble the arrays — machinery a hand-written query would rarely get right, generated automatically from the `nest:` syntax.

### Composable like functions

Queries and joined sources can themselves be used as sources for further joins/queries — the docs demonstrate reusable, nested data structures built by composing prior query results, the same way a function's output becomes another function's input. This is the same instinct behind dbt's `ref()` graph and Cube's views-over-cubes layering, but expressed at the query-language level rather than only at the model-definition level: in Malloy you compose *queries*, not just named model artifacts.

### Multi-dialect compilation

One model compiles to BigQuery, Postgres, DuckDB (and Snowflake, MySQL, Trino/Presto per connector support) SQL. Combined with native DuckDB support, this makes a Malloy model portable across a local dev database and a production warehouse without a rewrite — a materially different bet than tools whose SQL dialect handling is warehouse-specific by convention.

## Worth avoiding

- Malloy is a genuinely new language, not a YAML/config layer over SQL like Cube or LookML — that's precisely the source of its structural correctness guarantee, but it also means the adoption cost is "learn a new query language," not "learn a new config schema." No amount of doc quality erases that it's a different mental model from SQL, which is the thing every analyst and BI tool already knows.
- The compiled SQL for nested queries (group-set generation, conditional `CASE WHEN` aggregation, `LIST()` collection) is nontrivial machinery — worth being aware that "safe by construction" queries can still produce SQL that's hard for a human to debug by reading the generated output, even if the *result* is guaranteed correct.

## Facts & figures

- Connects to BigQuery, Snowflake, PostgreSQL, MySQL, Trino, or Presto; natively supports DuckDB.
- Originated at Google; now maintained under the Malloy Data / open-source community umbrella (exact current governance not independently verified beyond the GitHub org).
- `malloyyo` is a community MCP server project exposing a Malloy semantic model to MCP clients — vendor/community-reported, not part of Malloy core.

## Sources

- [What Is Malloy](https://docs.malloydata.dev/documentation/) · [Key Features](https://docs.malloydata.dev/documentation/about/features.html)
- [Nested Views](https://docs.malloydata.dev/documentation/language/nesting) · [Aggregates](https://docs.malloydata.dev/documentation/language/aggregates.html)
- [Joins](https://docs.malloydata.dev/documentation/language/join.html) — source of the "SQL flattens everything into a single table [space]" / "avoiding the fan and chasm traps" language
- [Querying a Semantic Model](https://docs.malloydata.dev/documentation/user_guides/querying_a_model) · [Explorer UI](https://docs.malloydata.dev/documentation/user_guides/publishing/explorer)
- [malloydata/malloy (GitHub)](https://github.com/malloydata/malloy) · [malloy npm package](https://www.npmjs.com/package/@malloydata/malloy) · [malloy PyPI package](https://pypi.org/project/malloy/)
- [malloydata/malloyyo — MCP server](https://github.com/malloydata/malloyyo)
- [Why Malloy? (Credible Data, third-party)](https://docs.credibledata.com/concepts/why-malloy)
- **Not directly verified:** the exact generated SQL for nested aggregating subqueries (group-set/`CASE WHEN`/`LIST()` description) was synthesized from a WebFetch summarization of the docs page rather than confirmed against a raw SQL output example; current corporate/governance status of the Malloy project was not independently confirmed beyond GitHub.
