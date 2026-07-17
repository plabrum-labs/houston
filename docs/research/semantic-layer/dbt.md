# dbt

**What it is:** The transformation/testing/governance layer for the modern data stack — SQL models compiled and run against a warehouse, with a DAG, a testing framework, versioned model contracts, and (via MetricFlow) a metrics layer.
**Axis:** semantic layer, data modeling, testing/governance, CI, lineage substrate.
**Depth:** deep — tests, contracts, model versions, CI defer/state selection, exposures, DAG artifact shape, dbt_expectations, and MetricFlow entities all verified against current docs; constraint enforcement matrix independently cross-checked.

## Products & surfaces

| Product | What it is |
|---|---|
| **dbt Core** | Open-source CLI: models, tests, docs, DAG, `manifest.json`/`run_results.json` artifacts. |
| **dbt Cloud / dbt Platform** | Managed orchestration, CI jobs, dbt Explorer (lineage UI), Semantic Layer hosting. |
| **MetricFlow** | The metrics-computation engine (Apache 2.0 since Coalesce 2025) powering the dbt Semantic Layer: semantic models, entities, metrics. |
| **dbt Semantic Layer** | Query interface (GraphQL/JDBC/Arrow Flight) over MetricFlow-defined metrics — the consumption surface for BI tools and agents. |
| **Packages (e.g., `dbt_expectations`, `dbt_constraints`)** | Community macro libraries extending tests and constraint enforcement. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Tests as `select`, zero rows = pass** | A data test is a query returning failing rows; empty result set is the only pass condition | yes |
| **Contracts (pre-build) vs tests (post-build)** | Contracts shape how a model *can* be built; tests check what got built | yes |
| **Constraint enforcement varies sharply by platform** | Only Postgres enforces the full ANSI set; other platforms enforce `not_null` and little else | yes — as a caveat |
| **Model versions** (`latest_version`, `versions:`, `deprecation_date`) | Multiple concurrent model shapes, explicit deprecation, enumerated breaking changes | yes |
| **The `alias` strangler-fig trick** | v1 keeps the original table name; v2 gets the new shape; migrate consumers at their own pace | yes |
| **CI `state:modified+` + `--defer`** | Build only the blast radius of a PR against a production manifest baseline | yes |
| **Exposures** | Extend the DAG to dashboards/notebooks/ML models as terminal consumer nodes | yes, with caveat |
| **`parent_map`/`child_map` in `manifest.json`** | The entire DAG tooling ecosystem rides on two adjacency maps plus stable node IDs | yes |
| **`dbt_expectations` moving-stdev anomaly test** | Log-normal anomaly detection over a moving average, in pure SQL | yes |
| **MetricFlow entities** (`primary`/`foreign`/`unique`) | Models join because they share a typed entity, not because someone wrote `ON` | yes |

`Steal?` is a first-pass signal only, not a decision.

## Worth stealing

### The load-bearing primitive: a test is a query for its own counterexamples

Every dbt data test compiles to a `select` statement; if it returns any rows, those rows are the failures, and **zero rows is the only passing state**. This one design decision is generative — nearly everything else in dbt's testing surface falls out of it:

- **Thresholds** (`error_if`, `warn_if`) are just a count comparison against the failing-row query's row count, not a different mechanism.
- **`store_failures`** works because the failing rows are already a well-formed result set — dbt just persists that query's output to a table named after the test, then counts against it.
- **`limit`** and **`where`** on a test are trivial to add because the test is already a `select` — scoping it is just more SQL, not a different code path.

Because a test is *just SQL*, arbitrarily sophisticated logic (anomaly detection, cross-table consistency, statistical bounds) is expressible without a separate testing DSL — see `dbt_expectations` below.

### Contracts vs. tests — before-build vs. after-build

The distinction, stated precisely in dbt's own docs: **tests run after the model is built and validate content; contracts are applied before a model is built and shape the way it is created.** A contract declares column names, types, and (where enforceable) constraints; if the model's compiled logic doesn't match that shape, **the model does not build at all** — not "builds and then fails a test," but never materializes. This moves a category of governance failure from "caught downstream by a scheduled test run" to "impossible to build in the first place."

### Constraint enforcement — verify per platform, don't assume

**This is a real, current gap and worth stating precisely rather than glossing over.** Per dbt's constraints reference:

| Constraint | Postgres | Redshift | Snowflake | BigQuery | Databricks |
|---|---|---|---|---|---|
| `not_null` | enforced | enforced | enforced | enforced | enforced |
| `primary_key` | enforced | definable only | definable only | definable only | definable only |
| `unique` | enforced | definable only | definable only | not supported | not supported |
| `foreign_key` | enforced | definable only | definable only | definable only | not supported |
| `check` | enforced | not supported | not supported | not supported | enforced |

**Postgres is the only platform enforcing the full ANSI set.** Everywhere else, `primary_key`/`unique`/`foreign_key` are *definable* (they appear in DDL, and on Snowflake with `RELY` can even help the query optimizer) but **not enforced** — nothing stops a row that violates them from being inserted. `check` is unsupported on Redshift, Snowflake, and BigQuery entirely; Databricks is the outlier that enforces `check` but not `primary_key`/`foreign_key`/`unique`. A contract's declared constraints are therefore only as strong as the underlying platform's willingness to enforce them — a contract on BigQuery is documentation-plus-`not_null`, not a referential-integrity guarantee.

### Model versions — deprecation as a first-class, machine-checkable state

A versioned model declares a `versions:` list (each a `v:` plus optional `config` overrides and a `columns: {include: all, exclude: [...]}` shape), a `latest_version` pointer, and per-version `deprecation_date`. Consumers either float (`ref('dim_customers')`, resolves to `latest_version`) or pin (`ref('dim_customers', v=1)`).

- **Unpinned refs are not silent.** Resolving an unpinned ref emits a message naming the version it resolved to and, if a newer prerelease version exists, tells the caller how to try it or pin to the current one — e.g. *"Resolving to latest version: my_model.v2 ... Pin to v2: `ref('my_dbt_project', 'my_model', v='2')`."*
- **`deprecation_date`** is enforced, not decorative: deleting a versioned model before its deprecation date raises an error in development and fails CI jobs.
- **Breaking changes are enumerated**, not left to judgment: removing or renaming a column, changing a column's `data_type`, changing nullability, or removing a constraint that was part of the contract. Because the list is closed and specific, contract-diffing between manifests is mechanical — a CI check can flag a breaking change without a human reading the diff.

### The `alias` trick — a strangler-fig migration expressed declaratively

```yaml
versions:
  - v: 1
    config:
      alias: dim_customers   # v1 keeps the original table name
  - v: 2
    # materializes as dim_customers_v2 by default
```

v1 continues to populate the table name every existing dashboard/query already points at, while v2 builds the new shape under a new name. Nothing downstream breaks on cutover day; consumers migrate to `ref('dim_customers', v=2)` on their own schedule, and the whole migration is expressed as YAML config rather than a coordinated rename-and-pray.

### CI jobs: build only the blast radius

The standard dbt Cloud CI job pattern is `dbt build --select state:modified+ --defer`:

- **`state:modified+`** selects nodes that changed relative to a baseline **production manifest**, plus (`+`) everything downstream of them — the actual blast radius of the PR, not the whole DAG.
- **`--defer`** tells dbt to resolve `ref()`s for everything *not* selected against the already-built production tables, instead of rebuilding upstream context from scratch.

Together: a PR that touches one staging model builds that model, everything downstream of it, and nothing else — while still resolving correctly against a full, real production dependency graph it never rebuilds.

### Exposures — extending the DAG to real consumers, with a real caveat

**Exposures** are metadata nodes (dashboards, notebooks, ML models, applications) that extend the lineage graph beyond dbt's own models, so `state:modified+`-style downstream selection and lineage visualization reach actual consumers, not just the last dbt-built table. **But exposures must be manually declared in YAML** (dbt Cloud's "automatic exposures" via BI-tool integrations like Looker/Tableau are the exception, not the default) — a dashboard nobody remembered to register is invisible to the lineage graph. **Declared lineage rots exactly like any other manually maintained metadata**: it's accurate at the moment someone writes it and increasingly wrong as consumers change without anyone updating the YAML.

### The DAG substrate is deceptively simple

The entirety of dbt's DAG-dependent tooling — node selection syntax, `state:modified`, dbt Explorer's lineage graph, third-party orchestrators (Dagster, Airflow) — rides on two adjacency lists in `manifest.json`: **`parent_map`** and **`child_map`**, keyed by stable node IDs of the form `<type>.<package>.<name>` (e.g. `model.my_project.customer_orders`). Nothing more exotic than two maps and a stable ID scheme underlies the entire ecosystem's ability to reason about "what depends on what."

### `dbt_expectations` — statistical testing in pure SQL, zero infrastructure

`dbt_expectations.expect_column_values_to_be_within_n_moving_stdevs` implements anomaly detection for time-series metrics entirely as a compiled SQL test: it assumes period-over-period logged differences follow a log-normal distribution, and flags a value when it deviates more than a configured `sigma_threshold` from a moving average computed over `trend_periods`. Configuration is declarative (`date_column_name`, `period`, `lookback_periods`, `trend_periods`, `test_periods`, `sigma_threshold`, `take_logs`) — no external anomaly-detection service, no Python runtime, no model training. It's a test macro that compiles to a window-function query, running on whatever warehouse already executes the rest of the project.

### MetricFlow: joins by shared entity, not by written `ON` clause

Semantic models declare **entities** typed `primary`, `foreign`, or `unique`. A `primary` entity uniquely identifies every row of its table; a `foreign` entity is a reference to another model's primary entity; a `unique` entity uniquely identifies a row but permits nulls. **Two semantic models join because they declare the same entity, not because a modeler wrote a join condition** — MetricFlow builds a join graph with semantic models as nodes and shared entities as edges, then picks join type and path automatically (predominantly left joins from fact to dimension), specifically to avoid fan-out/chasm joins by construction.

The claim worth being precise about: **this is a semantic assertion you can make before a foreign-key constraint exists in the warehouse** — declaring `type: foreign` on a column is a statement of intent about the data's meaning, independent of whether the underlying platform enforces (or even supports) an FK constraint (see the constraint-enforcement table above — most platforms don't). But **MetricFlow's entity graph is a metric-computation graph, not a knowledge graph**: edges exist solely to enable correct joins, keyed on physical columns; there's no inheritance, no "is-a" relationship, no inference over the graph, nothing resembling ontological reasoning. It's denormalization-oriented — built to answer "what's the correct join path for this metric query," not "what does this entity mean in relation to other entities."

### Went Apache 2.0; industry-wide interchange format emerging

MetricFlow moved from AGPL (through v0.140.0) to BSL (v0.150.0–v0.208.2) to **Apache 2.0 (v0.209.0+), announced at Coalesce 2025** — explicitly to let any vendor build on it without licensing friction, positioned as infrastructure for the **Open Semantic Interchange (OSI)** initiative (Snowflake-led, partners including Salesforce, BlackRock, dbt Labs, Atlan, Cube, Hex, Omni, Sigma, ThoughtSpot, and others). **OSI's core spec (v1.0) was published January 27, 2026** as an Apache 2.0-licensed, YAML-based vendor-neutral spec for datasets, metrics, dimensions, relationships, and contexts. **Verified: dbt Core v1.12+ reads OSI documents** — place OSI-format JSON files in an `OSI/` directory (or a configured `osi-paths` location); dbt parses them into the manifest alongside native dbt semantic models, and the two can coexist in the same project. One nuance worth flagging: **the OSI document version dbt Core 1.12 actually accepts is `0.1.0` or `0.1.1`** (any other version string raises a parse error) — a numbering mismatch against the "OSI v1.0 spec" branding that's worth re-checking as both projects continue to version independently.

## Worth avoiding

- **Constraint enforcement is easy to over-trust.** A contract with a declared `primary_key` reads as a guarantee; on every warehouse except Postgres it is not one. Teams building governance on top of dbt contracts need to know which platform they're on before treating a constraint as load-bearing.
- **Exposures are manually maintained and therefore incomplete by default.** Any lineage system whose downstream edge relies on a human remembering to register a consumer will under-represent real consumers over time — dbt doesn't solve this; automatic exposures narrow it only for specific integrated BI tools.
- **The OSI/dbt versioning mismatch** (spec v1.0 vs. accepted document versions 0.1.0/0.1.1) is a sign the interchange format is still stabilizing — treat "OSI support" claims as early and re-verify version compatibility before depending on it.

## Facts & figures

- Constraint enforcement: Postgres enforces `not_null`, `primary_key`, `unique`, `foreign_key`, `check`; Redshift/Snowflake/BigQuery enforce only `not_null` (others definable-only); BigQuery additionally doesn't support `unique`; Databricks enforces `not_null` and `check` but not `primary_key`/`unique`/`foreign_key`.
- MetricFlow license history: AGPL (≤v0.140.0) → BSL (v0.150.0–v0.208.2) → Apache 2.0 (v0.209.0+, announced at Coalesce 2025).
- OSI v1.0 core spec published 2026-01-27; partner list per Snowflake's announcement includes Alation, Atlan, BlackRock, Blue Yonder, Cube, dbt Labs, Elementum AI, Hex, Honeydew, Mistral AI, Omni, RelationalAI, Salesforce, Select Star, Sigma, Snowflake, ThoughtSpot.
- dbt Core v1.12+ accepts OSI documents versioned `0.1.0`/`0.1.1` specifically; other version strings raise a parse error.

## Sources

- [Add data tests to your DAG](https://docs.getdbt.com/docs/build/data-tests) · [About data tests property](https://docs.getdbt.com/reference/resource-properties/data-tests) · [store_failures](https://docs.getdbt.com/reference/resource-configs/store_failures) · [severity/error_if/warn_if](https://docs.getdbt.com/reference/resource-configs/severity) · [fail_calc](https://docs.getdbt.com/reference/resource-configs/fail_calc)
- [Model contracts](https://docs.getdbt.com/docs/mesh/govern/model-contracts) · [contract config](https://docs.getdbt.com/reference/resource-configs/contract)
- [constraints reference](https://docs.getdbt.com/reference/resource-properties/constraints) (platform enforcement matrix)
- [Model versions](https://docs.getdbt.com/docs/mesh/govern/model-versions) · [versions reference](https://docs.getdbt.com/reference/resource-properties/versions) · [deprecation_date](https://docs.getdbt.com/reference/resource-properties/deprecation_date) · [Coordinating model versions](https://docs.getdbt.com/best-practices/how-we-mesh/mesh-6-coordinate-versions)
- [Continuous integration jobs](https://docs.getdbt.com/docs/deploy/ci-jobs) · [Defer](https://docs.getdbt.com/reference/node-selection/defer) · [About local state](https://docs.getdbt.com/reference/node-selection/state-selection) · [Using defer](https://docs.getdbt.com/docs/platform/about-defer)
- [Visualize and orchestrate downstream exposures](https://docs.getdbt.com/docs/platform-integrations/downstream-exposures) · [Visualize downstream exposures](https://docs.getdbt.com/docs/explore/view-downstream-exposures)
- [Manifest JSON file](https://docs.getdbt.com/reference/artifacts/manifest-json)
- [dbt-expectations (GitHub)](https://github.com/calogica/dbt-expectations) · [expect_column_values_to_be_within_n_moving_stdevs (Elementary docs)](https://www.elementary-data.com/dbt-tests/expect-column-values-to-be-within-n-moving-stdevs)
- [About MetricFlow](https://docs.getdbt.com/docs/build/about-metricflow) · [Entities](https://docs.getdbt.com/docs/build/entities) · [Semantic models](https://docs.getdbt.com/docs/build/semantic-models) · [Joins](https://docs.getdbt.com/docs/build/join-logic)
- [Announcing open source MetricFlow](https://www.getdbt.com/blog/open-source-metricflow-governed-metrics) · [dbt-labs/metricflow LICENSE](https://github.com/dbt-labs/metricflow/blob/main/LICENSE)
- [Snowflake: OSI initiative announcement](https://www.snowflake.com/en/news/press-releases/snowflake-salesforce-dbt-labs-and-more-revolutionize-data-readiness-for-ai-with-open-semantic-interchange-initiative/) · [OSI spec finalized](https://www.snowflake.com/en/blog/open-semantic-interchanges-specs-finalized/) · [open-semantic-interchange/OSI (GitHub)](https://github.com/open-semantic-interchange/OSI)
- [OSI semantic layer documents (dbt docs)](https://docs.getdbt.com/docs/build/osi-semantic-models) · [Upgrading to v1.12](https://docs.getdbt.com/docs/dbt-versions/core-upgrade/upgrading-to-v1.12)
- **Not directly verified:** exact wording of the unpinned-ref warning message was reconstructed from a WebFetch summary rather than a raw doc quote captured verbatim; whether OSI's "v1.0" spec numbering and dbt's accepted "0.1.0/0.1.1" document versions will reconcile in a future dbt release was not confirmed.
