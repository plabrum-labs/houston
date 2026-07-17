# Airbyte

**What it is:** Open-source (plus managed cloud) ELT connector platform — ~600 pre-built connectors, self-hostable, with a connector-builder SDK for anything not in the catalog.
**Axis:** data migration (ingestion), workflow.
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Airbyte OSS** | Self-hosted connector runtime. |
| **Airbyte Cloud** | Managed version of the same. |
| **Connector Builder / CDK** | No-code and code-based tooling for building connectors not in the 600+ catalog. |
| **Destinations V2 / Typing & Deduping** | The current-generation load path — normalizes raw synced data into typed tables in the destination. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Schema drift: preserve schema, drop bad values, log it** | A value that doesn't fit the stream's declared type becomes NULL, with an entry in `_airbyte_meta.changes` recording a `DESTINATION_TYPECAST_ERROR` | yes |
| **Breaking-change detection as a separate, overriding axis** | Cursor or primary-key removal pauses the connection immediately, regardless of whatever schema-propagation policy is configured | yes |
| **Column removal is non-destructive by default** | A field dropped at the source stays in the destination and simply stops updating, rather than being deleted along with its history | yes |
| ~600 connectors | Breadth of the OSS catalog | n/a |

## Worth stealing

### "Preserve schema, drop the value, keep the receipt"

When Destinations V2 encounters a value that doesn't match the stream's declared schema, it does **not** fail the sync and does **not** silently coerce the type. It writes **NULL** for that cell and appends a `DESTINATION_TYPECAST_ERROR` entry to the `_airbyte_meta.changes` array on that row. This is a deliberate split introduced with Destinations V2: **"data-moving problems" are separated from "data-content problems."** A sync that can't move data at all still fails outright; a sync that moved the data but hit a per-row content mismatch succeeds, with the damage localized and queryable via `_airbyte_meta`. Contrast Fivetran's approach below — this is the schema-fixed, data-flexible half of a genuine fork in philosophy.

### Breaking-change detection always wins, independent of the propagation policy

Airbyte lets you configure how routine schema changes propagate (field-only vs. field-and-stream, auto vs. manual-approval). **Cursor or primary-key removal is treated as a different, higher-priority axis entirely: it pauses the connection immediately for manual review**, regardless of what the propagation policy says should happen to ordinary field changes. The mechanism worth stealing is the *layering* — routine drift is a policy choice; loss of the two things (cursor, PK) the sync's correctness depends on is not something any propagation policy is allowed to auto-approve past.

### Column removal defaults to non-destructive

If a column disappears at the source, Airbyte's default behavior retains the field in the destination and simply **stops updating it** — historical values remain intact. It is only actually removed if the connection is later cleared/refreshed. This protects against the common failure mode of "someone renamed a source column and now three months of history for the old name just vanished."

### The decade of hardened CDC failure modes worth naming

Airbyte (like Fivetran/Estuary) has had to build around well-known Postgres logical-replication failure modes that any CDC implementation eventually hits:
- **Replication-slot disk exhaustion** — an unadvanced slot holds WAL segments (and blocks VACUUM on rows the slot might still need) indefinitely; in extreme cases this can force the database to shut down to prevent transaction-ID wraparound.
- **`confirmed_flush_lsn` silent full-resync fallback** — if the consumer's saved offset falls behind what Postgres has already purged (WAL beyond `restart_lsn`), the only recovery is a full resync; this can happen silently if slot advancement lags.
- **`xmin` wraparound** — the 32-bit transaction ID counter wraps at ~4.29B; once wrapped, `xmin`-based cursors can no longer be trusted monotonically, which can force resyncing data already synced.

These aren't Airbyte-specific bugs — they're the standard hazards any Postgres-CDC-based product (Airbyte, Fivetran, Estuary, Debezium-based systems) has had to design defenses around over the last decade.

## Worth avoiding

Nothing distinct surfaced beyond the general CDC hazards above, which apply industry-wide rather than being an Airbyte-specific misstep.

## Facts & figures

- **~600 replication connectors** in the catalog (Airbyte's own count), plus 50+ "agent connectors."
- Destinations V2 / Typing & Deduping is the current architecture generation; pre-V2 destinations handled all failures by failing the whole sync (no per-row granularity).

## Sources

- [Typing and deduping](https://docs.airbyte.com/using-airbyte/core-concepts/typing-deduping)
- [Airbyte metadata fields](https://docs.airbyte.com/platform/understanding-airbyte/airbyte-metadata-fields)
- [Introducing Airbyte Destinations V2](https://airbyte.com/blog/introducing-airbyte-destinations-v2-typing-deduping)
- [Schema change management](https://docs.airbyte.com/platform/using-airbyte/schema-change-management)
- [Managing Breaking Changes in Connectors](https://docs.airbyte.com/platform/connector-development/connector-breaking-changes)
- [Connector catalog](https://airbyte.com/connectors)
- [The Insatiable Postgres Replication Slot — Gunnar Morling](https://www.morling.dev/blog/insatiable-postgres-replication-slot/)
- [Postgres Replication Slots: Confirmed Flush LSN vs. Restart LSN — Gunnar Morling](https://www.morling.dev/blog/postgres-replication-slots-confirmed-flush-lsn-vs-restart-lsn/)
