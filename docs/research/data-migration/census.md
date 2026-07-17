# Census

**What it is:** Reverse ETL, same category as Hightouch. Acquired by Fivetran (agreement announced May 1, 2025); product now ships as **Fivetran Activations**, and its documentation has moved accordingly.
**Axis:** data migration (activation/reverse sync), workflow.
**Depth:** thin.

## Products & surfaces

| Product | What it is |
|---|---|
| **Fivetran Activations** (formerly Census) | Warehouse → operational-tool sync, now under Fivetran's contract/platform. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Mirror sync behavior** | Deletes destination records that have left the source, as an intrinsic default part of the mode | yes/flag |

## Worth stealing / avoiding

**WARNING, stated plainly because this is the load-bearing fact for this file: Census's "Mirror" sync behavior deletes destination records by default.** Documentation confirms this operates as batched delete operations — Activations sends separate batches tagged with operation `upsert` (create/update) and operation `delete` for records that should be removed from the destination, and the sync log records attempted deletions for records that "left the segment." **This is the opposite default from Hightouch's identically-named "Mirror"/"All" mode**, where deletion is a separate opt-in setting layered on top of the sync mode rather than bundled into it — see `hightouch.md` for the full comparison and the practical hazard this creates.

## Facts & figures

- Acquisition agreement announced **May 1, 2025**; Census account holders required to migrate to Fivetran by **April 1, 2026** per the published migration FAQ.
- **Documentation has moved to `fivetran.com/docs/activations`** — `docs.getcensus.com` now 301-redirects there. Anything bookmarked at the old domain needs to be re-found under the Fivetran docs tree.

## Sources

- [Fivetran Signs Agreement to Acquire Census (press release)](https://www.fivetran.com/press/fivetran-signs-agreement-to-acquire-census-delivering-the-first-end-to-end-data-movement-platform-for-the-ai-era)
- [Syncs — Activations docs](https://fivetran.com/docs/activations/syncs)
- [Census Migration FAQ](https://fivetran.com/docs/activations/census-migration-faq)

## Shared finding, both files: why snapshot-diffing is forced, not chosen

Both Hightouch and Census are architecturally forced into **snapshot-diffing** — comparing the current warehouse query results against what was sent last time — because **warehouses generally cannot emit CDC for an arbitrary SQL query result**. A CDC stream exists (if at all) at the table level, upstream of whatever transformation logic produced the model being synced; once a `SELECT`/model has run, there's no changelog for *its* output, only for the raw tables underneath it. So both vendors' "incremental sync" is, mechanically, "run the query again, diff the result against the last run's result, act on the diff" — not a true change stream. This is why deletion is a genuinely hard problem for both: knowing a record "left the source" requires having kept last run's full result set to diff against, not just knowing what changed.
