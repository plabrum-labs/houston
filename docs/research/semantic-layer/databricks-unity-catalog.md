# Databricks Unity Catalog

**What it is:** Databricks' governance layer over the lakehouse — catalog/schema/table hierarchy, row/column access policies, automatic lineage, and (via Metric Views) a semantic layer feeding both BI dashboards and Genie's natural-language agent.
**Axis:** semantic layer, access policy, lineage, agent-facing metadata.
**Depth:** medium-deep — row filters/column masks, ABAC GA, lineage capture/loss conditions, Metric Views agent metadata, and the local-to-global promotion path all verified against current docs.

## Products & surfaces

| Product | What it is |
|---|---|
| **Unity Catalog** | The governance substrate: catalogs, schemas, tables, tags, permissions, lineage — the layer everything else in this file sits on. |
| **Row filters / column masks** | Per-table access policies implemented as SQL UDFs. |
| **ABAC (attribute-based access control)** | Tag-and-policy access control at catalog/schema scope, GA in 2026. |
| **Metric Views** | Unity-Catalog-native semantic layer objects: dimensions, measures, joins, agent metadata. |
| **AI/BI Dashboards** | BI surface with "local metric views" authorable in-dashboard, promotable to global Metric Views. |
| **Genie / Genie Spaces / Genie Agents** | Natural-language query agent, curated per "space," grounded on Metric Views and other governed sources. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Row filters / column masks as UDFs** | Access policy logic is literally a registered SQL function, evaluated per row/column at query time | yes |
| **ABAC — tag once, policy once** | Policies match tags at catalog/schema scope and apply to every current *and future* matching table | yes |
| **Automatic execution-plan lineage** | Column-level lineage captured with zero instrumentation, from Spark execution plans | yes |
| **Lineage loss conditions** | Path-based table references and UDF transforms break column-level lineage capture | yes — as a caveat |
| **Agent metadata on Metric Views** | Display names, synonyms (up to 10/field), format specs shipped as schema fields for LLM consumption | yes |
| **Local → global Metric View promotion** | Ad-hoc dashboard modeling promotable to a governed catalog object in one action | yes |
| **Genie Spaces on Metric Views** | NL queries resolve against governed metric definitions instead of inferring from raw tables | yes |

`Steal?` is a first-pass signal only, not a decision.

## Worth stealing

### Row filters and column masks are UDFs, not config

A row filter is a **SQL user-defined function**, registered in Unity Catalog, that evaluates each row at query time and returns a boolean; it can take zero or more input parameters, each bound to a column of the table. A column mask is likewise a **SQL UDF** that takes the column value (and optionally other columns, for multi-attribute masking logic) as input and returns either the real value or a masked substitute — return type must match or be castable to the column's declared type. Each table gets at most one row filter and each column at most one mask, applied by the table owner directly in SQL.

Making the policy *a function* rather than a declarative rule means arbitrary logic is available for free — a mask can be a regex, a hash, a lookup against another table, a conditional based on the querying user's group. The tradeoff is the same one dbt tests take with plain `select`: power via "it's just code," at the cost of policies being harder to statically analyze than a declarative filter list would be. Databricks explicitly documents the boundary this creates: **row-level security and column masks cannot be applied to a view**, and neither works through the Iceberg REST catalog, Unity REST APIs, or Delta Lake APIs — the policy only fires through Unity Catalog's own query path.

### ABAC (GA 2026): tag once, write the policy once, let it apply by matching

Table-level row filters/masks don't scale past a certain institutional size — Databricks' own framing is that per-object policies become unmanageable as an organization grows (the constraint isn't just "avoid repetition," it's auditability). **ABAC's fix**: tag columns with **governed tags** (key-value pairs defined at the account level, e.g. `pii`, `phi`) and write filter/mask **policies whose conditions match the tags** — attached at **catalog or schema scope**, not per-table. A policy written once against the tag `pii` applies automatically to **every current table with a column tagged `pii`, and every future one**, with no per-table policy authored at all.

Databricks explicitly recommends ABAC over per-table row filters/column masks for this reason. The concrete argument for why this matters: **200 objects × N roles of individually authored per-object policy is not something anyone can audit** — there's no single place to look to answer "what can role X see," because the answer is scattered across hundreds of table definitions. Tag-and-match collapses that to "what tags exist, and what does each policy do with each tag" — an auditable, enumerable surface. At GA, policy limits were raised 10x across scope (10,000+ policies per metastore, 100+ per catalog/schema), and ABAC also supports dynamic **GRANT policies** (beta, currently scoped to `EXECUTE` on models) — attribute-conditioned privilege grants, not just row/column filtering.

### Lineage: automatic, column-level, execution-plan-derived — and lossy in specific, named ways

Unity Catalog captures lineage **automatically**, with no code instrumentation, by intercepting Spark execution plans at runtime and extracting column-level dependency metadata, aggregated across every workspace attached to the metastore, and tagged with the triggering compute entity (job, notebook, query). This is a materially stronger default than most lineage systems in this research set, which require either manual declaration (dbt exposures) or external inference.

But it is **lost under two specific, documented conditions**, worth stating precisely rather than as a vague caveat:

- **Path-based table references.** `SELECT * FROM delta.`s3://bucket/path`` produces a lineage record carrying only the storage path, not the table name — column lineage requires both source and target to be referenced **by table name** (`catalog.schema.table`), not by path.
- **UDF-obscured transforms.** Custom UDFs (Python, Scala, or complex stored-procedure logic) "obscure the mapping between source and target columns" — lineage capture degrades to table-level, losing the column-to-column edges that make lineage useful for "what does changing this column break."

Both gaps have the same shape: **lineage capture depends on being able to statically read the transform from the execution plan.** Anything that hides the transform behind an opaque function call or an untyped path reference breaks the automatic capture, regardless of how sophisticated the plan-interception machinery is.

### Metric Views ship agent metadata as a first-class schema field

A Metric View's YAML definition can carry, per dimension/measure: a **display name** (human-readable label, ≤255 chars), up to **10 synonyms** (≤255 chars each), and a **format spec** (how to render the value — currency, date, number, etc.). These aren't documentation comments — they're structured fields the platform actively consumes: **AI/BI dashboards auto-populate display names and formats into visualizations**, and **Genie Agents automatically import synonyms** to resolve user vocabulary to the correct field.

The synonym field is the notable piece: it's an explicit, first-class acknowledgment that **the same concept is called different things by different departments** — Databricks' framing names this directly as the reason synonyms exist, citing the pattern of `cust`/`client`/`acct_holder`/`member` all meaning the same entity across different teams. Rather than solving this with an LLM inferring equivalence at query time (unreliable, unauditable), the vocabulary mapping is captured once, structurally, in the model — the same instinct as a glossary (see `collibra.md`), but attached directly to the queryable object instead of living in a separate governance tool.

### Local-to-global Metric View promotion — one action, not a rebuild

AI/BI dashboards support **local metric views**: dimensions, measures, and joins defined directly inside a dashboard via a visual interface, with joins resolved at runtime so a user can slice across any connected dataset and build multi-fact, multi-grain analysis without pre-declaring every join path. Up to 200 custom calculations per dataset are supported inline. **When a local metric view is ready for broader use, it can be exported to Unity Catalog as a global metric view in one action** — instantly making it accessible to every downstream tool that reads Unity Catalog metric views, not just the dashboard it was built in.

This is worth flagging as an **independent convergence with Omni's semantic-layer promotion path** (see whichever Omni research file exists, if any, in this folder): both products let a non-technical user model ad hoc inside a BI surface, then promote that model to governed, shared status without a separate re-authoring step. The pattern — "start ungoverned and fast, promote to governed and shared on demand" — appears to be an emerging convention for reconciling agility (analysts want to add a calc field *now*) with governance (that calc field should become the canonical definition if it turns out to be useful org-wide).

### Genie Spaces resolve against governed metrics, not raw-table inference

A Genie Space is a curated environment encoding "organization's logic, vocabulary, and rules so that natural language questions resolve into correct queries." When a Metric View is the data source, Genie's LLM layer retrieves the **defined metric and its metadata** rather than inferring a calculation directly from raw tables — Databricks' framing is that this materially improves accuracy versus letting the model guess at joins and aggregation logic from schema alone. This is the same "agent reads from a governed model, doesn't improvise SQL against a raw schema" pattern documented in `cube.md`'s MCP section — Databricks' version is Genie-specific rather than an open protocol.

## Worth avoiding

- **Row filters/masks cannot cover views**, and don't work through Iceberg REST, Unity REST APIs, or Delta Lake APIs — any access path outside Unity Catalog's own SQL query engine bypasses the policy. A team relying on a non-Unity-Catalog access route (a REST API integration, an Iceberg-native reader) needs to know the row/column policy simply won't apply there.
- **Lineage silently degrades**, not loudly. Neither path-based references nor UDF-obscured transforms raise a warning — lineage just stops being column-level (or stops entirely) with no signal to the user that the record they're looking at is incomplete. Anyone building trust ("can I safely change this column") on Unity Catalog lineage needs to know both failure modes exist and are undetectable from the lineage graph itself.

## Facts & figures

- ABAC GA: policy limits raised to 10,000+ per metastore, 100+ per catalog and per schema (vendor-reported).
- Metric View agent metadata: up to 10 synonyms per field/measure, 255-character limit per display name and per synonym.
- Local metric views in AI/BI dashboards support up to 200 custom calculations per dataset.
- Agent-metadata YAML requires Databricks Runtime 17.3 and YAML 1.1.
- ABAC GRANT policies (attribute-conditioned privilege grants) are in beta, currently scoped to `EXECUTE` on models only.

## Sources

- [Row filters and column masks](https://docs.databricks.com/aws/en/data-governance/unity-catalog/filters-and-masks/) · [Manually apply row filters and column masks](https://docs.databricks.com/aws/en/data-governance/unity-catalog/filters-and-masks/manually-apply)
- [Attribute-based access control in Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac/) · [Core concepts for ABAC](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac/core-concepts) · [Create and manage row filter/column mask policies](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac/policies) · [ABAC GA announcement](https://www.databricks.com/blog/abac-row-filtering-and-column-masking-policies-governed-tags-and-data-classification-are-now)
- [Lineage in Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-lineage) · [Lineage system tables reference](https://docs.databricks.com/aws/en/admin/system-tables/lineage)
- [Agent metadata in metric views](https://docs.databricks.com/aws/en/business-semantics/agent-metadata) · [Unity Catalog metric views](https://docs.databricks.com/aws/en/business-semantics/metric-views/) · [Use semantic metadata in metric views](https://docs.databricks.com/aws/en/metric-views/semantic-metadata)
- [Data modeling in AI/BI dashboards](https://docs.databricks.com/aws/en/dashboards/manage/data-modeling/) · [Local metric views](https://docs.databricks.com/aws/en/dashboards/manage/data-modeling/local-metric-views)
- [From Data to Dialogue: Genie Spaces best practices](https://www.databricks.com/blog/data-dialogue-best-practices-guide-building-high-performing-genie-spaces) · [Genie Agents](https://docs.databricks.com/aws/en/genie/) · [Curate an effective Genie Agent](https://docs.databricks.com/aws/en/genie/best-practices)
- **Not directly verified:** the specific `cust`/`client`/`acct_holder`/`member` vocabulary-drift example was captured via WebSearch summarization of Databricks-adjacent commentary, not confirmed verbatim in a single primary doc page; exact wording of Databricks' "audit 200 objects × N roles" framing for recommending ABAC over per-table policies was reconstructed from search summaries rather than a direct quote.
