# Fivetran

**What it is:** Managed ELT connector platform — the commercial-first counterpart to Airbyte's OSS-first model. Same category, opposite philosophy on schema drift.
**Axis:** data migration (ingestion).
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Fivetran connectors** | Managed source→destination sync, hosted, not self-run. |
| **HVR** | CDC-specific product line (acquired), for database replication. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Automatic type promotion on schema drift** | When a column's source type changes, Fivetran mutates the destination column to the most specific type that losslessly accepts both old and new data | yes |
| Type hierarchy with one-way promotion | Once a column is promoted to a "higher" type (e.g. STRING), it will not revert even if later data would fit a narrower type | maybe |

## Worth stealing / the fork with Airbyte

**Fivetran preserves data, mutates schema. Airbyte (`airbyte.md`) preserves schema, drops values.** This is the key comparison point in the category. When a Fivetran-tracked column's data type changes at the source, Fivetran:

1. Creates a new column with a temporary name.
2. Copies all existing values into it, cast to **"the most specific data type that losslessly accepts both the old and new data."**
3. Drops the old column.
4. Renames the new column to the original name.

Concretely: an INTEGER column that starts receiving decimals gets promoted to DOUBLE (both fit losslessly). A DOUBLE column that starts receiving booleans gets promoted all the way to **STRING** — because STRING is the only type in the hierarchy that can losslessly represent both a float and the literal strings `"true"`/`"false"`. **Type promotion is one-directional**: once a column is STRING, it stays STRING even if subsequent data would fit back into a narrower type — Fivetran's own docs are explicit that "we will not revert to a lower [type]."

The design tradeoff versus Airbyte is the thing worth internalizing, not either mechanism in isolation: Fivetran guarantees **no data is ever dropped or nulled** at the cost of a schema that can drift toward the lowest common denominator (STRING) over time and require an active migration to tighten back up. Airbyte guarantees the **schema stays exactly as declared** at the cost of silently-NULLed values on individual rows (auditable via `_airbyte_meta`, but still data loss on that cell). Neither is strictly better — they're answering "which do you protect, the schema or the row" differently, and that's a decision Houston will face for any equivalent sync surface.

## Worth avoiding

The one-way ratchet toward STRING is a real cost: a single anomalous row (one boolean value in a numeric column) can permanently downgrade a column's type for all future data, with no automatic path back to a tighter type — that has to be a manual intervention.

## Facts & figures

None beyond the mechanism itself; no adoption/scale figures independently verified in this pass.

## Sources

- [Reliable Data Replication in the Face of Schema Drift — Fivetran blog](https://www.fivetran.com/blog/reliable-data-replication-in-the-face-of-schema-drift)
- [Why Did My Schema Data Type Change From INTEGER to NVARCHAR?](https://fivetran.com/docs/destinations/troubleshooting/change-integer-nvarchar)
- [Can I Change Column Data Type in the Destination?](https://fivetran.com/docs/destinations/troubleshooting/change-column-data-type)
