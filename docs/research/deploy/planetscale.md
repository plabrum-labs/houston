# PlanetScale

**What it is:** Managed MySQL (Vitess) whose defining product is the Deploy Request — a pull-request workflow for schema changes, with non-blocking cutover and a genuine post-deploy revert, built on Vitess VReplication. The key contrast with Neon: branches here are schema-only, not data forks.
**Axis:** deploy, migration.
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Branches** | Isolated MySQL instances copying a source branch's **schema only** — no data unless restored from a backup. |
| **Deploy Requests** | A reviewable, diffable proposal to apply a branch's schema changes to a target branch (staging/production). |
| **Non-blocking schema changes** | Online migrations via Vitess VReplication — no table locks, no blocked production traffic during the change. |
| **Schema reverts** | A time-boxed, lossless "undo" of an already-deployed schema change. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Deploy Request = PR for schema** | Visual diff (green/red), optional team approval, queued deploy | yes |
| **Branches are schema-only** | No data copied into a new branch by default — the key contrast with Neon's copy-on-write data branching | yes — as a documented tradeoff, not a gap |
| Non-blocking cutover | Vitess creates a shadow table, syncs data via VReplication, then atomically swaps — no table lock during the sync phase | yes |
| Gated deployments | Deploy can pause after table sync completes, holding cutover until a human clicks to swap | yes |
| **Schema revert** | Up to 30 minutes post-deploy, revert to the previous schema at the MySQL transaction level with no data loss | yes |
| Pre-deploy safety checks | Blocks non-deployable requests, e.g. a table missing a unique key required for VReplication | yes |

## Worth stealing

### Deploy Requests — the PR model applied to schema, not code

A development branch copies a source branch's schema (not its data) into an isolated MySQL instance. Once schema changes are made on the branch, a **Deploy Request** is opened against the target branch, showing a **visual diff** (additions in green, deletions in red) and optionally requiring teammate approval before it can be queued for deployment. PlanetScale's own framing: this gives *"an opportunity for your teammates to review the changes you have made before they are deployed to production"* — treating schema migrations with the same review discipline as application code, rather than as a one-off script run by whoever's on call.

### Non-blocking cutover — the actual Vitess mechanism

The migration process: Vitess creates a shadow copy of the affected table, applies the schema change to the shadow table, then uses **VReplication** to continuously sync data changes from the original table into the shadow table while production traffic keeps writing to the original. Only the final **cutover** step — an atomic table swap — needs a brief metadata lock; if that lock can't be acquired immediately (e.g., a long-running query holds it), Vitess retries until it succeeds rather than failing the whole migration. **Gated deployments** let a human hold that final cutover open indefinitely — sync completes, then a person clicks to actually swap the tables, decoupling "the new schema is ready and synced" from "traffic now uses it."

### Schema revert — VReplication run in reverse, not a snapshot restore

After a deploy, PlanetScale keeps a **30-minute window** during which the change can be reverted. The mechanism reuses VReplication: rather than restoring from a backup (which would lose any writes since the migration), it tracks ongoing changes to the post-migration table and applies them to a shadow table matching the *previous* schema, then cuts back over — a **lossless sync at the MySQL transaction level**, so data written after the schema change is preserved through the revert. This is meaningfully different from "restore yesterday's backup": it's a live, forward-tracking reversal, not a point-in-time rollback.

### The Neon contrast, stated explicitly

PlanetScale branches deliberately **do not** carry data — a new branch is schema-only unless you explicitly restore data from a backup into it. This is the opposite tradeoff from Neon's copy-on-write branching (full schema *and* data, in under a second, regardless of size — see `neon.md`). PlanetScale's bet is that schema review is the valuable, reviewable unit of change; Neon's bet is that a full data fork is cheap enough to give away by default. Houston-relevant framing: "branch" means two different things across these two products, and any Houston design language borrowing the word needs to pick one meaning explicitly.

## Worth avoiding

- **Schema-only branching means realistic testing against production-shaped data requires an explicit backup restore step** — it's not automatic, unlike Neon, so a team that wants "test against real data" has to build that restore into their workflow deliberately.
- **The 30-minute revert window is time-boxed, not indefinite** — past that window, a schema mistake requires a new forward migration rather than a revert, so the safety net has a real expiry.

## Facts & figures

- Schema revert window: **30 minutes** post-deploy.
- Non-blocking migrations use **Vitess VReplication** for both the initial cutover and the revert path.
- Branches copy schema only; data requires an explicit backup restore.

## Sources

- [Branching concepts](https://planetscale.com/docs/concepts/branching)
- [Deploy requests](https://planetscale.com/docs/vitess/schema-changes/deploy-requests) · [Aggressive deploy request cutover](https://planetscale.com/docs/vitess/schema-changes/aggressive-cutover)
- [Safely making database schema changes (blog)](https://planetscale.com/blog/safely-making-database-schema-changes)
- [Behind the scenes: how schema reverts work (blog)](https://planetscale.com/blog/behind-the-scenes-how-schema-reverts-work) · [Revert a migration without losing data (blog)](https://planetscale.com/blog/revert-a-migration-without-losing-data) · [PlanetScale schema reverts feature page](https://planetscale.com/features/revert)
- [Force cutover for deploy requests (changelog)](https://planetscale.com/changelog/force-cutover-deploy-requests)
