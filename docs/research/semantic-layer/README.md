# Semantic layer

**What this category is:** platforms that put a governed, declared model between raw storage and every consumer — BI tool, embedded app, or agent — so queries are expressed against named business concepts (metrics, dimensions, objects) instead of raw tables and joins.
**Why it's in this research:** semantic objects are Houston's core bet (the Foundry side of the Palantir × Vercel × Fly.io mix). This is the landscape of who else has built a declared-model layer, what mechanisms they use for correctness and access control, and how far each one's ambition goes.
**Files:** 8.

## The players

| Company | What it is | Depth |
|---|---|---|
| [palantir](palantir.md) | Ontology: governed, typed, bidirectional knowledge graph with a kinetic (Action type) layer on top — the reference implementation | deep |
| [dbt](dbt.md) | Transformation/testing/governance layer; MetricFlow (now Apache 2.0) is its read-only metrics engine, joining models by declared entity | deep |
| [databricks-unity-catalog](databricks-unity-catalog.md) | Lakehouse governance substrate — row/column policies as UDFs, tag-driven ABAC, automatic execution-plan lineage, Metric Views | medium-deep |
| [cube](cube.md) | Open-core semantic layer compiling a governed metrics model to SQL/REST/GraphQL/MCP; three-axis access-policy algebra | medium |
| [looker](looker.md) | LookML — the originator of "declared model, not raw schema"; symmetric aggregates as a runtime correctness rewrite | medium |
| [malloy](malloy.md) | Unified model+query language; the only design that fixes join fan-out structurally rather than at runtime | medium |
| [atlan](atlan.md) | Active metadata catalog — doesn't own the data, does governance through inferred cross-system lineage and tag propagation | thin |
| [collibra](collibra.md) | Governance-process platform — business glossary linked directly to physical assets, backed by a BPMN workflow engine | thin |

Palantir is the reference implementation and the only platform in this set with a kinetic (write/action) layer. dbt, Cube, Looker, Malloy, and Unity Catalog are all read-only analytics layers of varying sophistication. Atlan and Collibra sit one layer up — governance/cataloging over systems they don't own, rather than a query-compiling semantic layer themselves.

## Convergence

**Only Palantir has a kinetic side.** Cube, LookML, Malloy, MetricFlow, and Unity Catalog's Metric Views are all read-only: they compile structured requests to SQL and return governed results. None has anything resembling Palantir's Action types (transactional, validated, auditable writes to the model). This is the sharpest category-level gap and the clearest whitespace Palantir occupies alone.

**Declared relationships let the engine guarantee correctness nobody asked for.** Looker's symmetric aggregates and Malloy's structural join-graph preservation solve the identical bug (`SUM`/`COUNT` inflated by join fan-out) two different ways — Looker via a runtime rewrite triggered by declared primary-key + join-cardinality metadata (fragile if the modeler declares the relationship wrong), Malloy by making the ambiguous aggregate inexpressible in the language itself (structurally can't be gotten wrong the same way). MetricFlow converges on the same instinct from a third angle: models join because they share a typed **entity** (`primary`/`foreign`/`unique`), not because someone wrote an `ON` clause — the join path is derived, not authored, specifically to avoid fan-out/chasm joins by construction.

**The read-only consumption pattern is identical everywhere it's been built for agents.** Cube's MCP flow, Databricks' Genie-on-Metric-Views, and dbt's Semantic Layer all land on: introspect the governed model (not the warehouse schema) → issue a structured request, never raw SQL → compile with access policy baked in at compile time → cache-then-execute → return governed results. Cube states the security argument most directly: the agent literally cannot express an unsafe query because the layer never compiles one.

**Tag-driven policy is the answer to per-object rules not scaling.** Unity Catalog's ABAC (tag a column once, write a policy against the tag, it applies to every current and future matching table) and Atlan's tag propagation along lineage (tag a source column once, every downstream derived asset inherits it automatically) are independent solutions to the same underlying problem: manually re-asserting a policy or a label at every object doesn't survive institutional scale. Palantir's marking propagation is the same instinct again, expressed as mandatory access control on an owned platform rather than a catalog feature over external systems.

**The glossary problem is solved by making the glossary structural.** Collibra's pitch — link a business term directly to the physical columns that implement it, so drift either updates the link or visibly breaks it — is the same "the model IS the schema" idea Databricks expresses via Metric View synonyms (department-specific vocabulary mapped once, structurally, onto the queryable object) and MetricFlow's declared entities. A prose glossary rots because nothing forces it to stay attached to what it describes; a glossary wired into the queryable model can't drift silently.

**A second, smaller convergence: promote-on-demand from ungoverned to governed.** Unity Catalog's local→global Metric View promotion (model ad hoc inside a dashboard, promote to a catalog object in one action) is flagged in `databricks-unity-catalog.md` as converging with Omni's equivalent pattern — start fast and ungoverned, promote to shared/governed only once a definition proves useful org-wide.

## Worth stealing

- **Action types** (`palantir.md`) — a transactional, validated, auditable set of edits as a first-class model citizen. Nothing else in this category has it.
- **Scenarios** (`palantir.md`) — agent-proposed changes staged as a sandboxed subset, applied all-or-nothing, reviewable as a diff before commit.
- **Markings and mandatory-vs-discretionary control** (`palantir.md`) — conjunctive access control even an Owner can't remove, propagating through lineage.
- **Cube's three-state access-policy algebra** (`cube.md`) — rows, members, and a masked middle state, composed with a precise (and non-obvious) union/intersection rule.
- **"Never expose cubes, expose views"** (`cube.md`) — the internal model graph and the governed public surface are explicitly different objects.
- **dbt contracts vs. tests** (`dbt.md`) — a contract shapes the model before it's built; a test checks it after. Moves a class of governance failure from "caught downstream" to "impossible to build."
- **dbt model versioning + the `alias` strangler-fig trick** (`dbt.md`) — machine-checkable deprecation dates and enumerated breaking changes, migration expressed as YAML config rather than coordinated rename-and-pray.
- **Unity Catalog ABAC** (`databricks-unity-catalog.md`) — tag once, write the policy once, auditable by construction instead of scattered across hundreds of per-table policies.
- **Row filters/column masks as SQL UDFs** (`databricks-unity-catalog.md`) — arbitrary policy logic for free, at the cost of static analyzability.
- **Metric View agent metadata** (`databricks-unity-catalog.md`) — display names, up to 10 synonyms, and format specs shipped as structured schema fields, actively consumed by both dashboards and Genie, not documentation comments.
- **Term-to-asset linking + BPMN workflow** (`collibra.md`) — governance state (draft/approved/certified) as a queryable, enforced fact.

## Worth avoiding

- **Looker's symmetric aggregates depend on the modeler declaring join cardinality correctly** — mislabel a `many_to_many` join as `one_to_one` and the safety net silently doesn't fire (`looker.md`).
- **Constraint enforcement on dbt contracts is easy to over-trust** — only Postgres enforces the full ANSI constraint set; on BigQuery a `primary_key` constraint is documentation plus `not_null`, not a referential-integrity guarantee (`dbt.md`).
- **dbt exposures and Unity Catalog lineage both degrade silently** — exposures require manual YAML registration (an unregistered dashboard is invisible to the DAG); Unity Catalog lineage loses column-level fidelity under path-based table references or UDF-obscured transforms, with no warning either way (`dbt.md`, `databricks-unity-catalog.md`).
- **Row/column policies in Unity Catalog don't cover views** and don't apply through the Iceberg REST catalog, Unity REST APIs, or Delta Lake APIs — any access path outside Unity Catalog's own query engine bypasses the policy entirely (`databricks-unity-catalog.md`).
- **Atlan's lineage is inferred, not derived** — reconstructed from query history and connector exhaust because Atlan doesn't own the compute, which is inherently more fragile than Unity Catalog's execution-plan interception (`atlan.md`).
- **Cube's Jinja-templated data modeling has no type system** — a malformed loop fails at render time, not author time, the tradeoff of not having a real compiler (`cube.md`).

## Gaps

- **No one but Palantir has a write/action model.** The rest of the category has converged hard on read-only, which means any Houston bet on kinetic (Action-type-shaped) semantics has essentially no competitive precedent to copy mechanics from outside Palantir itself.
- **Lineage-edge provenance (human-asserted vs. machine-inferred) is not solved inside this category's core products.** `atlan.md` flags that OpenMetadata and DataHub (adjacent open-source catalogs, not covered as their own files here) tag lineage edges with a `Manual`/inference-method enum or a confidence score specifically so automatic re-derivation can't silently clobber a human correction — none of Palantir, Cube, Looker, Malloy, dbt, or Unity Catalog document an equivalent discipline for their own lineage/relationship metadata.
- **The interchange format (OSI) is early and versioning is still unstable** — dbt Core 1.12 accepts OSI documents versioned `0.1.0`/`0.1.1` against an "OSI v1.0" spec brand; treat cross-vendor semantic-layer portability claims as aspirational for now (`dbt.md`).

## Notes

- Several files in this category carry an explicit "not directly verified" tail — Palantir's five-layer AIP runtime description, Cube's exact MCP tool schema, Malloy's generated-SQL internals for nested queries, and Atlan's product-name/architecture specifics were all captured via secondary summarization rather than a directly fetched primary source. Treat those specifics as directionally correct, not quoted.
- Atlan and Collibra are intentionally thin files (short by research-scope design), not under-researched relative to their actual depth in the category — they're one layer removed from query-compiling semantic layers.
- dbt's MetricFlow licensing history (AGPL → BSL → Apache 2.0, 2025) and its role as OSI infrastructure is recent and could shift the interchange-format story quickly; re-check before depending on cross-vendor portability claims.
