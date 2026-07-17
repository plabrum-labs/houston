# Data migration

**What this category is:** how data gets moved, validated, mapped, and mastered — ingestion (ELT/CDC), onboarding surfaces (embeddable importers), reverse ETL, data-quality/observability tooling, and the entity-resolution/MDM layer that sits on top of merged data.
**Why it's in this research:** every axis of "data gets into and stays clean inside Houston" — ingestion correctness, schema-drift handling, validation timing, and identity/golden-record construction all inform how Houston's own data layer should behave.
**Files:** 15.

## The players

| Company | What it is | Depth |
|---|---|---|
| [airbyte](airbyte.md) | OSS-first ELT connector platform, ~600 connectors | medium |
| [fivetran](fivetran.md) | Managed-first ELT connector platform, Airbyte's philosophical opposite on schema drift | medium |
| [estuary](estuary.md) | Streaming-first CDC via a durable, replayable log | thin/medium |
| [meltano](meltano.md) | OSS ELT on the Singer tap/target protocol; sortedness as an explicit stream contract | medium |
| [confluent-schema-registry](confluent-schema-registry.md) | Kafka Schema Registry + Data Contracts — the only preventive (write-time) validator in the set | medium |
| [datafold](datafold.md) | Checksum-bisection data-diffing for migration verification; OSS project archived, algorithm still public | medium |
| [great-expectations](great-expectations.md) | OSS data-validation framework; commercial tier sells the UI/alerting layer | thin |
| [soda](soda.md) | Data-quality checker, now a "Data Contracts engine" (v4, Jan 2026) | medium |
| [monte-carlo](monte-carlo.md) | Data observability via metadata-only (query-log/`information_schema`) monitoring | thin |
| [anomalo](anomalo.md) | Monte Carlo-adjacent observability platform — docs gated, mechanism unverifiable | unresearchable |
| [flatfile](flatfile.md) | Embeddable importer, developer-facing; Automap threshold-gated auto-mapping | thin |
| [oneschema](oneschema.md) | Embeddable importer, drop-in-speed-oriented competitor to Flatfile | thin |
| [osmos](osmos.md) | "Agentic data engineering" — LLM writes PySpark, doesn't touch rows; acquired by Microsoft Jan 2026 | thin (gated docs) |
| [hightouch](hightouch.md) | Reverse ETL, warehouse → operational tools | thin |
| [census](census.md) | Reverse ETL, acquired by Fivetran, now "Fivetran Activations" | thin |

Order reflects category role, not alphabetical: ingestion (Airbyte/Fivetran/Estuary/Meltano/Confluent) is the largest and most load-bearing cluster; validation/observability (Datafold, GE, Soda, Monte Carlo, Anomalo) is the detective-tooling tier; onboarding importers (Flatfile, OneSchema, Osmos) are a distinct customer-facing surface; reverse ETL (Hightouch, Census) is the outbound half of the same problem. Airbyte and Fivetran are the reference implementations for the category's central fork (see Convergence); everything else is either a variant, a narrower tool, or thinly documented.

Entity resolution / MDM (Senzing, Splink, Zingg, Informatica, Reltio, Tamr) is a separate, closely related category — see `../entity-resolution/README.md`. Several data-migration files here (Informatica, Reltio via their `semantic-layer` cross-references) touch golden-record construction, but the dedicated matching/mastering engines live in that folder.

## Convergence

**Detective vs. preventive is the single sharpest fork in the category, and it's structural, not a vendor choice.** Every warehouse-centric quality tool researched here — Great Expectations, Soda, Monte Carlo, Anomalo, and by extension dbt tests / ODCS-style contracts — can only scan data *after* it has already landed, because a warehouse does not run arbitrary code at write time; something has to come along later and check. Confluent Schema Registry's Data Contracts are the sole counterexample in this set: because the client library sits directly in the Kafka serialization path, a `domainRule` (CEL expression) can reject, transform, or route a bad write *before it's committed anywhere* — this is a property of streaming's architecture, not a feature one vendor added. See `confluent-schema-registry.md` for the full argument. Houston-relevant framing: "detect the problem after the fact" and "reject at the boundary" are different tiers of guarantee, and only a write-path-resident validator can do the latter.

**The schema-drift fork: Fivetran mutates schema, preserves data; Airbyte preserves schema, drops values.** When a column's type changes at the source, Fivetran promotes the destination column to the most specific type that losslessly holds old and new data (one-directional — a column that reaches STRING never reverts), guaranteeing no data is ever dropped at the cost of schema drifting toward the lowest common denominator over time. Airbyte does the opposite: it keeps the declared schema fixed and writes NULL for a non-conforming value, logging a `DESTINATION_TYPECAST_ERROR` in `_airbyte_meta.changes` — auditable, but a real per-cell data loss. Neither is strictly better; they're answering "which do you protect, the schema or the row" in opposite directions. See `fivetran.md` and `airbyte.md`.

**The OSS-tier pattern: the check/validation *engine* is open, the commercial layer sells UI/alerting/results-history.** Great Expectations Core and Soda Core are both fully open-source detection engines; what GX Cloud and Soda's commercial tier actually charge for is where results live, who gets paged, and the dashboard — not "can it detect the problem." Explicitly named as a category-wide pattern in `great-expectations.md`.

**Snapshot-diffing is structurally forced on reverse ETL, not a design choice.** Both Hightouch and Census run "incremental sync" as "re-run the query, diff against last run's result set" because warehouses can't emit CDC for an arbitrary SQL query's output — a CDC stream exists (if at all) at the table level, upstream of whatever transform produced the synced model. This is why deletion is genuinely hard for both vendors: knowing a record "left the source" requires having kept the full prior result set to diff against. See the shared finding in `census.md`.

**Same word, opposite default semantics — a cross-vendor terminology collision worth flagging on its own.** Hightouch's "Mirror" mode makes deletion a separate, opt-in setting; Census's identically-named "Mirror" mode deletes destination records by default as an intrinsic part of the mode. A team assuming parity across the two platforms will get materially different (and in one direction, silently destructive) results.

**A decade of hardened Postgres CDC failure modes is now shared industry knowledge, not any one vendor's IP.** Airbyte, Fivetran, Estuary, and Meltano/Singer have all had to design around the same three hazards: replication-slot disk exhaustion, silent full-resync on `confirmed_flush_lsn` lag, and `xmin` wraparound. Documented once in `airbyte.md`, referenced by `meltano.md`.

**Checkpointing safety is a property of the stream's ordering guarantee, not of "did we save state periodically."** Meltano's Singer SDK makes this explicit and machine-checked via `is_sorted` — a declared, enforced boolean that determines whether a mid-run checkpoint is trustworthy at all. This is a smaller-scale instance of the same discipline Airflow brings to scheduling (see `../workflow/README.md`): treat a correctness assumption as a declared, checked contract rather than an implicit belief.

## Worth stealing

- **Preserve schema, drop the value, keep the receipt** — Airbyte's `_airbyte_meta.changes` audit trail on a typecast failure (`airbyte.md`).
- **Breaking-change detection as a separate, overriding axis** — cursor/PK removal pauses a connection regardless of the configured drift-propagation policy (`airbyte.md`).
- **Checksum-bisection diffing** — verify two tables match by comparing in-database checksums recursively, transferring only hashes, never rows; O(k log n) in the number of actual differences, not table size (`datafold.md`).
- **`onSuccess`/`onFailure` as a configurable action, including DLQ** — a rejected write becomes a captured, inspectable artifact instead of a dropped write or a failed producer call (`confluent-schema-registry.md`).
- **The `threshold:` block is orthogonal to check type** — one reusable comparison shape (`must_be_between`, `metric: percent`, `level: warn`) across every check type, vs. dbt's bespoke-per-test-macro argument shapes (`soda.md`).
- **`qualifier` for stable check identity** — an explicit string independent of file position or config, so history/tracking survives edits (`soda.md`).
- **Metadata-only monitoring** — Monte Carlo reads query logs and `information_schema`, not row data, making "monitor everything automatically" cost-tractable (`monte-carlo.md`).
- **Data Docs as static, ownable HTML** — validation results as a durable artifact you can check into history, not a live query against a vendor backend (`great-expectations.md`).
- **`is_sorted` as a declared, runtime-enforced contract** — the SDK raises `InvalidStreamSortException` if the tap author's claim is false, rather than trusting documentation (`meltano.md`).
- **Threshold-as-gate, not threshold-as-score** — Flatfile's Automap either clears the accuracy bar for every field or refuses to run, forcing an explicit human-fallback decision rather than letting a half-mapped file slip through (`flatfile.md`).
- **Program synthesis as the trust mechanism** — Osmos has the LLM write PySpark that then moves the data, rather than letting the model touch rows directly; the artifact is reviewable, versionable, deterministic on re-run (`osmos.md`).
- **Delete as a decoupled, explicit setting** — Hightouch's separation of sync mode from delete behavior is the safer default shape, contrasted directly against Census's bundled default (`hightouch.md`).

## Worth avoiding

- **Fivetran's one-way ratchet toward STRING** — a single anomalous row can permanently downgrade a column's type for all future data, with no automatic path back (`fivetran.md`).
- **Census's Mirror-deletes-by-default vs. Hightouch's Mirror-deletes-opt-in** — the exact same term, opposite defaults, a real migration/multi-tool hazard (`census.md`, `hightouch.md`).
- **Vendor claims that can't be checked against a mechanism at all** — Anomalo's technical docs are gated behind a redirect; its capability claims overlap Monte Carlo's but nothing about *how* it works is verifiable (`anomalo.md`). Osmos is one step better (blog/press-sourced) but still has no primary technical documentation reachable — every "how it works" claim there is vendor narrative (`osmos.md`).
- **Benchmarking against a dead product** — Soda Core v4 (Jan 2026) fully replaced the SodaCL checks language with contract-first YAML; any comparison written against SodaCL syntax describes the previous product (`soda.md`).
- **Stateless mapping with no cross-run memory** — Flatfile's Automap remaps every file from scratch; a customer's correction today gives zero benefit on their next upload (contrast the vendor claim that Nuvo, an adjacent player, does learn across imports — unverified) (`flatfile.md`).

## Gaps

- **No researched vendor combines write-time rejection (Confluent's mechanism) with warehouse-shaped ergonomics.** The preventive tier is streaming-only; anyone wanting boundary-time rejection on data that ultimately lands in a warehouse has no off-the-shelf tool bridging the two.
- **Reverse ETL's deletion problem has no clean solution in this set** — both major players are stuck diffing full result sets because warehouses don't expose query-level CDC; nobody has a documented mechanism that avoids this.
- **Cross-run mapping memory is absent or unverified across the entire importer tier** — Flatfile documents its absence, OneSchema doesn't document the mechanism at all, and Nuvo's "improves with every import" claim is vendor-only.

## Notes

- Anomalo: technical docs unreachable (307-redirect to gated marketing page) — treat all capability claims as marketing until primary docs surface.
- Osmos: acquired by Microsoft (announced Jan 5, 2026); primary docs sites are gated or TLS-broken as of this research pass — every mechanism claim here is press/blog-sourced, not vendor-documentation-sourced.
- Datafold's OSS `data-diff` repo was archived 2024-05-17 — a maintenance/support sunset tied to Datafold's cloud strategy, not evidence the algorithm doesn't work; it remains public and reimplementable.
- Several "facts & figures" across this category (Datafold's 1B-rows-in-5-minutes, Estuary's sub-100ms latency, OneSchema's 4GB/20M-row throughput, Osmos's 50% dev-effort reduction) are vendor-reported and explicitly flagged as such in the underlying files — not independently reproduced.
