# Neon

**What it is:** Serverless Postgres whose defining mechanism is copy-on-write branching — a full schema+data clone of a database as a metadata operation, independent of dataset size. Acquired by Databricks (~$1B, announced May 2025) explicitly to serve AI agents provisioning databases programmatically.
**Axis:** deploy, migration (database branching for preview environments).
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Branching** | Copy-on-write clone of a Postgres database (schema + data), created as metadata, not a data copy. |
| **Vercel Previews integration** | Auto-creates a Neon branch per Vercel preview deployment and scopes a connection string to it. |
| **Autoscaling / scale-to-zero** | Compute scales down to zero between connections, standard serverless-Postgres behavior. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Copy-on-write branching** | Branch creation is a metadata pointer into WAL history; data isn't physically copied | yes |
| Branch time independent of dataset size | A branch off a 50GB database is ready in under a second, same as a 1GB database | yes |
| No load on parent | Creating a branch does not increase load on or affect the parent branch | yes |
| **Vercel Previews integration** | Webhook on preview deploy creates `preview/<git-branch>`, injects a connection string scoped to that deployment only | yes |
| Agent-driven provisioning at scale | Vendor reports the large majority of databases on the platform are now created by AI agents, not humans | note — vendor-reported, but corroborated across multiple outlets |

## Worth stealing

### Copy-on-write branching — metadata pointer, not a data copy

The mechanism: branches are **pointers into WAL (write-ahead log) history with copy-on-write pages** — a new branch and its parent share the same underlying data pages at the moment of branch creation and diverge only as new writes land, tracked as deltas rather than duplicated storage. Because nothing is physically copied at branch time, **dataset size is irrelevant to branch time**: a branch off a 50GB database is ready in under a second with a full logical copy of both schema and data, the same as branching a 1GB database. Neon's docs are explicit that this also means **creating a branch does not increase load on or affect the parent branch in any way** — the operation is metadata-only from the parent's perspective, not a read-heavy export.

This is the mechanism that makes "give every PR / every preview deployment / every agent session its own real database with real data" operationally cheap rather than a capacity-planning problem.

### The Vercel Previews integration — a concrete instance of the pattern

On a Vercel preview deploy, a webhook fires to Neon, which creates a branch named `preview/<git-branch>` via the Neon API, then returns a **connection string scoped to that specific deployment** — injected as `DATABASE_URL`/`DATABASE_URL_UNPOOLED` (plus legacy `PG*` vars) into that deployment only, not shared across other previews or production. This is the reference implementation of "database branching wired directly into the deploy pipeline" rather than a manually-triggered developer action — the branch lifecycle is driven by the deploy lifecycle.

## Worth avoiding

Nothing distinctly negative surfaced in this pass — Neon's branching model is close to the mechanism as advertised and is corroborated independently (Databricks' own framing of the acquisition centers on exactly this capability). The one caveat worth carrying: **copy-on-write branching is a storage-engine property specific to Neon's architecture** (separated storage/compute, WAL-based) — it is not a pattern that bolts onto a conventional Postgres deployment without that underlying storage design.

## Facts & figures

- Branch creation: **under 1 second**, independent of source database size (vendor docs).
- Databricks announced intent to acquire Neon for **~$1B** (May 14, 2025).
- Neon/Databricks reported that the share of databases on the platform created by **AI agents rather than humans** rose from **~30% at GA to over 80%** by the time of the acquisition announcement — reported consistently across Databricks' own blog/press release and independent trade coverage (TechTarget, InfoWorld, TechRepublic). Treat as vendor-reported but multiply-corroborated, not independently audited.

## Sources

- [Branching overview](https://neon.com/docs/introduction/branching)
- [Vercel Previews integration](https://neon.com/docs/guides/vercel-previews-integration)
- [Databricks and Neon (Neon blog)](https://neon.com/blog/neon-and-databricks) · [Databricks press release](https://www.databricks.com/company/newsroom/press-releases/databricks-agrees-acquire-neon-help-developers-deliver-ai-systems) · [Databricks blog](https://www.databricks.com/blog/databricks-neon)
- [TechTarget coverage](https://www.techtarget.com/searchdatamanagement/news/366623864/Databricks-adds-Postgres-database-with-1B-Neon-acquisition) · [InfoWorld coverage](https://www.infoworld.com/article/3985947/databricks-to-acquire-open-source-database-startup-neon-to-build-the-next-wave-of-ai-agents.html)
- **Not directly verified in this pass:** the specific "30% → 80%+" figures come from search-result summaries of the Databricks/Neon announcement coverage, not a direct fetch of the original blog post text — worth a direct re-fetch of `databricks.com/blog/databricks-neon` before citing the exact percentages in an external-facing document.
