# Sigma

**What it is:** A spreadsheet-grid UI (formulas, pivots) compiled to SQL and run live against the warehouse, with writeback tables that make it usable as a lightweight operational app, not just a viewer.
**Axis:** app-builder, workflow, enterprise.
**Depth:** thin.

## Products & surfaces

| Surface | What it is |
|---|---|
| **Sigma workbooks** | Spreadsheet-grid analysis over live warehouse data — formulas/pivots translate to SQL, no data downloaded or duplicated. |
| **Input Tables** | User-entered data written back to the warehouse as native `INSERT`/`UPDATE` statements against dedicated Snowflake/Databricks tables. |
| **Sigma Tables** | Shared, flat warehouse tables readable/writable by "any workbook, app, external system, script, or agent." |
| **Sigma Tenants** | Architectural (not just permission-based) tenant isolation — separate users/data/assets per tenant, added as a distinct capability rather than assumed from day one. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Spreadsheet formulas compile to SQL | Every grid action (formula, pivot, filter) is translated to SQL and run live against the warehouse — no export, no duplication | yes |
| Input Tables | Business users write back to dedicated warehouse tables from inside a workbook UI — real `INSERT`/`UPDATE`, not a side database | yes |
| Sigma Tables as a shared read/write surface | A flat table any workbook, app, script, or agent can read/write — the point is the *use cases* this unlocks (FP&A what-if, budget entry, annotation, human-in-the-loop labeling), not the table mechanism itself | yes |
| Sigma Tenants | Explicit, architecture-level tenant isolation ("its own users, its own data, its own assets") added as a distinct feature | maybe |

## Worth stealing

**Writeback as native SQL, not a bolt-on form.** Input Tables let a non-technical user type values into a spreadsheet-shaped UI and have Sigma issue real `INSERT`/`UPDATE` statements against a warehouse table it manages — this is genuinely rare among BI tools, most of which are read-only by architecture. The mechanism turns Sigma into something closer to a lightweight operational app builder for FP&A, budget entry, forecasting, and manual data annotation/labeling — the value isn't the write path itself but the workflows it unlocks that a read-only BI tool structurally cannot support.

**Sigma Tables generalize the writeback pattern into a shared integration surface.** Rather than treating writeback as a Sigma-internal feature, Sigma Tables are positioned as flat warehouse tables that "any workbook, app, external system, script, or agent" can read or write — i.e., the warehouse table itself, not a Sigma-proprietary API, is the integration point. That's a notably different posture from most BI writeback features, which lock the written data inside the tool.

## Worth avoiding

**Sigma is widely described (including by Sigma itself, in its own "Sigma Tenants" launch post) as having grown up single-tenant/team-segmented first** — the post describing the Sigma Tenants feature frames the prior state as relying on "team-based structure" and access controls within a shared environment, contrasted explicitly against customers who now want "architectural guarantees" that "cross-contamination can't happen because the architecture itself makes it impossible." Independent reviews echo this: Sigma's embedding/multi-tenant story requires more deliberate setup (dataset duplication or careful governance per tenant) compared to platforms purpose-built for embedded, multi-tenant analytics from day one (Cube, Luzmo, Explo, Qrvey, Toucan). **The lesson: retrofitting hard tenant isolation onto a platform is possible but is a distinct, later feature (Sigma Tenants), not free from the base architecture** — worth noting for anything Houston builds that assumes single-tenant internal use first.

## Facts & figures

- Input Tables write to dedicated Snowflake or Databricks-backed tables (vendor-described).
- "Sigma Tenants" is a distinct, separately named/launched capability, not baseline behavior (implies it postdates the core product's initial multi-tenant posture).

## Sources

- [Sigma spreadsheets product page](https://www.sigmacomputing.com/product/spreadsheets) · [Sigma Tenants Isn't A Feature. It's The Future Of Enterprise Analytics.](https://www.sigmacomputing.com/blog/sigma-tenants-is-the-future-of-enterprise-analytics) · [Sigma Computing Review 2026 — Pros, Cons (Knowi)](https://www.knowi.com/blog/the-ultimate-sigma-review-pros-cons-and-who-it-is-for/) · [Embeddable vs Sigma comparison](https://embeddable.com/blog/embeddable-vs-sigma-a-complete-technical-comparison-for-saas-teams)
- **Not directly verified:** the specific phrase "built single-tenant-first" is this research folder's paraphrase of Sigma's own framing plus third-party review commentary, not a direct Sigma quote.
