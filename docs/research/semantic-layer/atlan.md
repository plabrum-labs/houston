# Atlan

**What it is:** An active metadata / data-catalog platform that connects to external systems (warehouses, BI tools, pipelines) rather than owning the data itself, and does its governance work primarily through lineage.
**Axis:** governance, lineage, catalog.
**Depth:** thin — scoped intentionally short per research brief; tag-propagation mechanism verified against docs, deeper product surface not explored.

## Products & surfaces

| Product | What it is |
|---|---|
| **Atlan catalog** | Unified metadata layer over connected systems (Snowflake, Databricks, BI tools, pipelines) via a broad connector library. |
| **Metadata Propagator** | The app/mechanism that pushes governance metadata (owners, certificates, tags) downstream along lineage automatically. |
| **Lineage graph** | Cross-system, automatically inferred lineage assembled from query history and connector metadata mining. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Tag propagation along lineage** | Classifications, sensitivity labels, and glossary terms automatically flow to every downstream asset a tagged asset feeds | yes |
| **Cross-system lineage inference** | Lineage assembled by mining query history and connector metadata rather than requiring instrumentation in each system | yes |

`Steal?` is a first-pass signal only, not a decision.

## Worth stealing

### Tag propagation along lineage

Atlan's **Metadata Propagator** automatically carries tags, classifications, glossary terms, and sensitivity labels from an upstream asset to every downstream asset connected to it by lineage, without a human re-applying the tag at each hop. Practically: mark a source column `pii` once, and every derived table/dashboard/report built from it downstream inherits the label automatically as the lineage graph grows — governance metadata doesn't need to be reasserted at each transformation step. This is the same instinct as Palantir's marking propagation (`palantir.md`) — protection travels through transforms — implemented as a catalog feature over externally-owned systems rather than as a mandatory access control baked into a single owned platform.

### Cross-system lineage inference — because Atlan doesn't own the systems

Atlan does not run the warehouse or the BI tool; it connects to them. Its lineage is therefore necessarily **inferred**, not derived from an execution engine it controls (contrast Unity Catalog's execution-plan interception in `databricks-unity-catalog.md`, which only works because Databricks owns the compute). Atlan's approach: mine query history (e.g., Snowflake's `ACCOUNT_USAGE`/`INFORMATION_SCHEMA`) and connector-provided metadata across every connected system, then assemble a unified graph spanning systems that were never designed to share a lineage model. **Doing hard cross-system inference is a direct consequence of not owning the systems** — a catalog vendor that can't intercept execution has to reconstruct lineage after the fact from whatever exhaust each system leaves behind.

## Worth avoiding

- Inferred, cross-system lineage is a weaker guarantee than execution-plan-derived lineage from a platform that owns the compute — it's reconstructed from logs and query text, which is inherently more fragile to obfuscated transforms, non-instrumented systems, or connectors that don't expose sufficient history.

### Adjacent pattern worth noting: don't let inference clobber a human assertion

Two open-source catalogs in this space encode a related but distinct discipline — not just *how* lineage is inferred, but **marking whether a given edge was asserted by a human or derived by a machine, so re-derivation can't silently overwrite a human correction**:

- **OpenMetadata**'s lineage-edge `source` field is a closed enum whose value names how that specific edge was created: `Manual` (the default) plus **ten** machine-inference methods — `ViewLineage`, `QueryLineage`, `PipelineLineage`, `DashboardLineage`, `DbtLineage`, `SparkLineage`, `OpenLineage`, `ExternalTableLineage`, `CrossDatabaseLineage`, and related pipeline/query-derived sources. A human-drawn edge is `Manual`; everything else names its inference method.
- **DataHub**'s `FineGrainedLineage` carries a `confidenceScore` field (0.0–1.0, default 1.0) on every field-level lineage edge — a continuous signal rather than a binary source label, letting a consumer decide how much to trust a given inferred edge.

Both are solving the same problem Atlan's propagation and Palantir's marking-propagation also touch: **automatically re-deriving lineage on every ingestion run risks silently overwriting a lineage edge a human corrected by hand.** Tagging provenance (`Manual` vs. named inference method, or a confidence score) is the minimum discipline needed to make automatic re-derivation safe to run repeatedly without clobbering deliberate human work — and to avoid presenting an inferred, possibly-wrong edge with the same visual authority as a verified one.

## Facts & figures

- Not independently verified beyond docs.atlan.com search summaries; no first-party quantitative figures (customer counts, connector counts) were pulled for this file.

## Sources

- [Atlan lineage concepts](https://docs.atlan.com/product/capabilities/lineage/concepts/what-is-lineage) · [Generate lineage between assets](https://docs.atlan.com/product/capabilities/lineage/how-tos/generate-lineage-between-assets)
- [Data Lineage — Trace Every AI Answer to the Truth](https://atlan.com/data-lineage/)
- [Snowflake Data Lineage Best Practices](https://atlan.com/know/snowflake-data-lineage-best-practices/) · [Databricks Data Lineage Best Practices](https://atlan.com/know/databricks-data-lineage-best-practices/)
- [OpenMetadata entityLineage schema](https://docs.open-metadata.org/v1.6.x/main-concepts/metadata-standard/schemas/type/entitylineage) · [entityLineage.json (GitHub)](https://github.com/open-metadata/OpenMetadata/blob/main/openmetadata-spec/src/main/resources/json/schema/type/entityLineage.json)
- [DataHub fine-grained lineage emitter example](https://github.com/datahub-project/datahub/blob/master/metadata-ingestion/examples/library/lineage_emitter_dataset_finegrained.py) · [DataHub Dataset entity docs](https://docs.datahub.com/docs/0.15.0/generated/metamodel/entities/dataset)
- **Not directly verified:** exact product name/architecture of "Metadata Propagator" and its propagation rules were captured via WebSearch summarization of docs.atlan.com content rather than a single primary page fetched directly — worth a direct doc fetch before relying on specifics.
