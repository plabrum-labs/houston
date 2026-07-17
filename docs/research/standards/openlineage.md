# OpenLineage (+ Marquez)

**What it is:** OpenLineage is an open standard (LF AI & Data project) for emitting lineage events — jobs, runs, datasets, and facets describing them — from any pipeline tool. Marquez is the reference implementation: a metadata service that collects OpenLineage events and stores versioned lineage.
**Axis:** governance, lineage, semantic layer (as substrate for trust in derived data).
**Depth:** medium — column-lineage type taxonomy and the `masking` facet field verified directly against the OpenLineage spec; Marquez's versioning model verified at a conceptual level, some internal table names not independently confirmed.

## Products & surfaces

| Product | What it is |
|---|---|
| **OpenLineage spec** | The event/facet schema: `Job`, `Run`, `Dataset`, and pluggable facets attached to each. |
| **Integrations** | Emitters for Spark, Airflow, dbt, Flink, and others — instrumented to emit OpenLineage events as pipelines execute. |
| **Marquez** | Reference metadata backend: ingests OpenLineage events, stores versioned jobs/datasets/runs, serves a lineage API and UI. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **DIRECT vs. INDIRECT column lineage** | Distinguishes columns a value is *derived from* versus columns that merely *influenced* it (e.g., a `WHERE` clause column) | yes |
| **DIRECT subtypes**: `IDENTITY`, `TRANSFORMATION`, `AGGREGATION` | Names *how* a value was derived from its direct input | yes |
| **INDIRECT subtypes**: `JOIN`, `GROUP_BY`, `FILTER`, `SORT`, `WINDOW`, `CONDITIONAL` | Names *how* a column influenced the output without contributing its value | yes |
| **`masking` boolean** | Marks that a transformation obfuscated the value en route (e.g., a hash) | yes |
| **Marquez three-way versioning** (code, data, run) | Job code version, dataset version, and run are independently versioned entities | yes |
| **`runs_input_mapping`-style pinning** | Each run records exactly which data version of each input it read | yes |

`Steal?` is a first-pass signal only, not a decision.

## Worth stealing

### DIRECT vs. INDIRECT column lineage — the distinction almost every system drops

Most lineage tools (including several elsewhere in this research set) collapse "this output column depends on that input column" into a single edge type. OpenLineage's `ColumnLineageDatasetFacet` splits it in two, and the split is the actual insight:

- **DIRECT** — "derived from inputField value." The output's *value* comes from this input. Subtyped further:
  - `IDENTITY` — passed through unchanged.
  - `TRANSFORMATION` — computed from the input via some function (subtype example: `hash`).
  - `AGGREGATION` — computed from many input rows' values (subtype example: `count`).
- **INDIRECT** — "impacted by the value, but not derived from it." The output's *presence or shape* depends on this input, but the input's value never flows into the output value. Subtyped:
  - `JOIN` — the input participated in a join condition.
  - `GROUP_BY` — the input drove which rows got aggregated together.
  - `FILTER` — the input appeared in a `WHERE` clause.
  - `SORT` — the input drove `ORDER BY`.
  - `WINDOW` — the input partitioned/ordered a window function.
  - `CONDITIONAL` — the input appeared inside `IF`/`CASE WHEN`/`COALESCE`.

The canonical example that makes this concrete: **a column used only in a `WHERE` clause influences the output rows without ever appearing in any output column.** A lineage system that only tracks DIRECT edges would show that column as unrelated to the result — wrong for impact analysis (change that column's meaning and every filtered query changes) and wrong for compliance (a `WHERE region = 'EU'` filter on a sensitive column is exactly the kind of dependency an auditor needs visible, even though no `region` value is *returned*). Modeling both edge types, each independently subtyped, is a level of precision essentially unique to OpenLineage in this research set.

### The `masking` boolean — a compliance-shaped field

Each transformation description carries `type`, `subtype`, `description`, and a boolean `masking` field indicating whether that specific transformation **obfuscated** the input value (a hash of PII being the canonical example — an `IDENTITY|MASKED` subtype combination reflects "same shape as input, but no original data recoverable"). This is exactly the fact a compliance reviewer needs and that most lineage graphs don't carry: not just "this column feeds that column," but **"and along the way, the value was irreversibly transformed"** — the difference between "this report contains customer emails" and "this report contains a one-way hash of customer emails" is the entire difference between a finding and a non-issue, and OpenLineage encodes that distinction directly on the lineage edge rather than requiring a human to go read the transformation code.

### Marquez's three-way versioning — why "why did this number change" is answerable

Marquez treats **code version**, **data version**, and **execution (run)** as three independently versioned entities rather than collapsing them into "a pipeline ran":

- A **run** has a unique ID, its code version, its run args, its state transitions, and its input/output datasets.
- Each **dataset version** is an immutable pointer, mapped to the specific run that produced that state of the dataset.
- The mapping between a run and *which version of each input dataset it actually read* is recorded explicitly — a run doesn't just point at "the orders table," it points at the orders table **as it existed at that specific version**.

Because code version and input-data version are tracked as separate, independently addressable axes, **"why did this number change?" decomposes into two independently answerable questions**: did the job's code change between the two runs being compared, or did an upstream input's data change? A system that only tracks "a run happened at time T" can't separate those two causes without external log spelunking; Marquez's model makes the diff a direct query — diff the job version between two runs, and independently diff the input dataset version each run consumed.

## Worth avoiding

- The value of both features (DIRECT/INDIRECT typing, `masking`) depends entirely on integrations actually emitting them faithfully — OpenLineage is a spec, not an enforcement mechanism. A Spark or dbt integration that doesn't populate `subtype`/`masking` correctly produces a lineage graph that looks complete but silently omits the distinctions the spec makes possible.
- Marquez's per-run, per-dataset versioning is thorough but has a documented storage cost: a stable schema re-versioned on every run of a frequently-scheduled job can generate very large volumes of near-duplicate version rows (a real GitHub issue cites a 20-column schema updated every 10 minutes for 30 days producing 864,000 field-mapping rows) — the fidelity that makes "why did this change" answerable also means the system accumulates history aggressively and needs a retention/compaction story.

## Facts & figures

- OpenLineage is an LF AI & Data Foundation project (Linux Foundation umbrella).
- Column lineage facet defines exactly 3 DIRECT subtypes (`IDENTITY`, `TRANSFORMATION`, `AGGREGATION`) and exactly 6 INDIRECT subtypes (`JOIN`, `GROUP_BY`, `FILTER`, `SORT`, `WINDOW`, `CONDITIONAL`).
- Marquez GitHub issue #2676 documents a real storage-growth case: ~864,000 duplicate field-mapping rows from a 20-column schema versioned every 10 minutes over 30 days.

## Sources

- [Column Level Lineage Dataset Facet spec](https://openlineage.io/docs/spec/facets/dataset-facets/column_lineage_facet/) · [ColumnLineageDatasetFacet.json (GitHub)](https://github.com/OpenLineage/OpenLineage/blob/main/spec/facets/ColumnLineageDatasetFacet.json)
- [OpenLineage.md spec (GitHub)](https://github.com/OpenLineage/OpenLineage/blob/main/spec/OpenLineage.md)
- [Getting Started — OpenLineage](https://openlineage.io/getting-started/)
- [Marquez Project — About](https://marquezproject.ai/about/) · [Marquez Quickstart](https://marquezproject.ai/docs/quickstart/) · [Trying Out the New Column Lineage Feature](https://marquezproject.ai/blog/column-lineage-demo/) · [Exploring Lineage History via the Marquez API](https://openlineage.io/blog/explore-lineage-api/)
- [MarquezProject/marquez (GitHub)](https://github.com/MarquezProject/marquez) · [Issue #2676 — version dataset schemas separately (storage growth example)](https://github.com/MarquezProject/marquez/issues/2676)
- **Not directly verified:** the exact table name `runs_input_mapping` was not confirmed against current Marquez source — related tables found during research (`job_versions_io_mapping`, `dataset_versions_field_mapping`) confirm the underlying versioning model but under different table names; treat "run pins which data version it read" as a verified *behavior*, the specific table name as unverified. Whether Marquez's UI/API surfaces a direct "diff two runs by code-version vs. data-version independently" query, versus this being an implication of the stored model, was not directly confirmed against the API docs.
