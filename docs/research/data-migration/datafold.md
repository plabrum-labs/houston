# Datafold

**What it is:** Data-diffing — verify that two tables (same or cross-database, e.g. a migration source vs. target) contain the same data, without transferring the data itself to compare it.
**Axis:** data migration (verification).
**Depth:** medium. Core algorithm is public and well documented; the OSS project is no longer maintained (see below).

## Products & surfaces

| Product | What it is |
|---|---|
| **`data-diff`** (OSS, archived) | CLI/library implementing the checksum-bisection diff algorithm across SQL backends. |
| **Datafold Cloud** | Commercial product built on the same algorithm, plus CI integration and UI. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Checksum-bisection diff algorithm** | Recursively narrows down to the actual diverging rows without ever transferring row data across the network | yes |

## Worth stealing

### The algorithm, in full

1. Segment both tables into chunks over the primary-key range (configurable `bisection_factor`).
2. Checksum each chunk **independently, in-database, on each side** — the hash computation runs where the data lives, not in a client that pulls rows first.
3. Compare checksums. **Matching checksums eliminate the whole chunk from further consideration** — no row in that chunk is ever transferred to be compared.
4. **Chunks whose checksums differ recursively subdivide** (governed by `bisection_threshold`) until the diverging rows are isolated down to individual records.

**Only hash values cross the network — never row data.** This changes the complexity profile from O(n) data transfer (pull every row from both sides to compare) to roughly **O(k log n)** where k is the actual number of differing rows — the cost scales with how much is *actually wrong*, not with table size. Datafold's own claim: diffing **1 billion rows across PostgreSQL and Snowflake in under 5 minutes on a laptop** (**vendor-reported**, not independently reproduced here). MD5 is the checksum function — chosen for near-universal availability across SQL engines, not cryptographic strength (collision risk is treated as irrelevant for a verification, not security, use case).

This is directly applicable to any "did the migration actually preserve the data" verification step: the algorithm is public, documented, and small enough to reimplement rather than depend on a vendor for.

## Worth avoiding

Nothing distinct in the algorithm itself; the caution is about the project's status (below).

## Facts & figures

- Claimed: 1B rows, cross-database (Postgres ↔ Snowflake), under 5 minutes, on a laptop — **vendor-reported**.
- **The OSS `data-diff` GitHub repository was archived on 2024-05-17** — the maintainer's own description frames this as a sunset tied to Datafold's cloud product strategy, not a statement that the algorithm doesn't work. It had accumulated ~3,000 GitHub stars before archival.
- **The algorithm remains public and reimplementable** — archival affects maintenance/support, not the technique's availability. Anyone building on this should expect to fork or reimplement rather than depend on upstream fixes.

## Sources

- [Open source data-diff (Datafold blog)](https://www.datafold.com/blog/open-source-data-diff/)
- [data-diff technical explanation (GitHub)](https://github.com/datafold/data-diff/blob/master/docs/technical-explanation.md)
- [data-diff repo](https://github.com/datafold/data-diff) — archived 2024-05-17, read-only.
- [Data Diff origin story (Datafold blog/podcast)](https://www.datafold.com/blog/data-engineering-podcast-open-source-data-diff)
