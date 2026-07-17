# Soda

**What it is:** Data-quality checking tool. **As of Soda Core v4 (public release January 28, 2026), it has fully replaced its old SodaCL checks language with contract-first YAML and rebrands itself a "Data Contracts engine."** Anyone benchmarking "Soda = SodaCL" is benchmarking a dead product.
**Axis:** data migration (validation), semantic layer (contracts).
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Soda Core v4** | Parses, publishes, and verifies **data contracts** (YAML), replacing the old SodaCL checks language — this is a breaking change from v3, with a documented migration/conversion tool. |
| Soda Core v3 (legacy) | The SodaCL-based predecessor; still documented but superseded. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Orthogonal `threshold:` block** | A single threshold shape (`must_be_greater_than`, `must_be_between: {greater_than, less_than}`, etc.) reused identically across every check type | yes |
| **`metric: percent` / `level: warn`** | Thresholds can target a percentage rather than a raw count, and severity is a first-class field on the threshold itself | yes |
| **`qualifier`** | An explicit, user-supplied string that gives a check a stable identity independent of its position or config | yes |
| **`failed_rows`** | Check type/output that surfaces the actual offending rows, not just a pass/fail count | maybe |

## Worth stealing

**The `threshold:` block is orthogonal to check type, and that's the whole design win.** Rather than each check type inventing its own bespoke set of comparison arguments, Soda v4 contracts reuse one threshold shape everywhere: `must_be_greater_than`, `must_be_less_than`, or the ranged `must_be_between` (itself composed of `greater_than`/`less_than` or the inclusive variants), plus `metric: percent` to express the bound as a percentage instead of an absolute count, plus `level: warn` to mark severity **inside the same block**. Compare this to dbt tests, where every test macro defines its own bespoke argument shape and severity is bolted on separately per test — Soda's version means learning the threshold syntax once teaches you every check type.

**`qualifier` solves stable check identity more cleanly than auto-generated names.** In a contract YAML, every check needs a unique identity; Soda generates one by default from the check's location plus type/name, but a check author can set an explicit `qualifier` string to get a **stable identity independent of where the check sits in the file or how its config changes** — meaning you can define multiple checks of the same type on the same column and know exactly which one broke, rather than parsing an auto-generated name to figure it out. dbt's equivalent (auto-generated test unique-IDs from macro args) is more brittle: change an argument, the generated ID changes, and history/tracking tools lose continuity.

## Worth avoiding

**Benchmarking or documenting against SodaCL is now benchmarking a superseded product.** The v3→v4 transition is a breaking change in the literal sense — v4 does not run SodaCL checks without conversion. Any existing internal notes, comparisons, or integration code referencing SodaCL syntax needs to be treated as describing the *previous* Soda, not the current one.

## Facts & figures

- **Soda Core v4 public release: January 28, 2026.**
- v4 supports Postgres, Snowflake, BigQuery, Databricks, Redshift, SQL Server, Fabric, Synapse, Athena, DuckDB.
- New check types introduced with contracts: Missing, Invalid, Duplicate, Aggregate, Failed Rows, Metric.

## Sources

- [Soda Core release notes](https://docs.soda.io/release-notes/soda-core)
- [Introducing Soda 4.0](https://soda.io/blog/introducing-soda-4.0)
- [Contract Language reference (v4)](https://docs.soda.io/soda-v4/reference/contract-language-reference)
- [soda-core GitHub](https://github.com/sodadata/soda-core)
