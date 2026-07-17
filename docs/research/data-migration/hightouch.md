# Hightouch

**What it is:** Reverse ETL — sync data from the warehouse out to operational tools (CRMs, ad platforms, marketing tools).
**Axis:** data migration (activation/reverse sync), workflow.
**Depth:** thin.

## Products & surfaces

| Product | What it is |
|---|---|
| **Syncs** | Warehouse query → destination, on a schedule or via CDC where the source supports it. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Sync modes** (Update / Insert / Upsert / Mirror-"All" / Snapshot / Diff) | Different strategies for how query results reconcile against existing destination records | maybe |
| **Delete as a separate configurable behavior** | Whether records that left the source get deleted, cleared, or left alone in the destination is its own setting, not bundled automatically into a sync mode | yes |

## Worth stealing

**Snapshot-diffing is a structural necessity, not a design choice, for both Hightouch and Census** — see the shared note below.

**Delete behavior is decoupled from sync mode, not bundled into it.** Hightouch's "Mirror"/"All" mode is documented as overwriting existing destination records with the current query results, but *whether records that dropped out of the source query get deleted* is governed by a **separate configurable delete-behavior setting** (documented options include "Do nothing," "Clear fields," "Delete destination record") — deletion is opt-in per destination, not an automatic consequence of choosing Mirror mode. The one documented exception is **warehouse destinations** (Databricks, Snowflake Iceberg), where Mirror mode is implemented as a hard `TRUNCATE` + full reinsert of the query results — there, "mirror" really does mean full replace, because a warehouse table has no cheaper alternative than replacing the whole table.

## Worth avoiding — same word, opposite default semantics

**WARNING, stated plainly because the two vendors use identical terminology for different defaults: Hightouch's delete behavior is opt-in and separately configured per sync; Census's "Mirror" sync behavior deletes by default as an intrinsic part of the mode** — see `census.md`. A team that configures a "Mirror" sync on one platform and assumes the other platform's Mirror behaves the same way will get a materially different outcome: on Hightouch, forgetting to also set the delete behavior means departed source records silently persist in the destination; on Census, Mirror deletes them automatically. This is exactly the kind of cross-vendor terminology collision that causes real incidents during a platform migration or a multi-tool activation strategy.

## Facts & figures

None beyond the mechanism.

## Sources

- [Sync types and modes — Hightouch docs](https://hightouch.com/docs/syncs/types-and-modes)
- [Syncs overview — Hightouch docs](https://hightouch.com/docs/syncs/overview)
- [Databricks destination docs](https://hightouch.com/docs/destinations/databricks)
