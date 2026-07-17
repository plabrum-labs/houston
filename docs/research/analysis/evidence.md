# Evidence.dev

**What it is:** Open-source "BI as code" — named SQL queries embedded in markdown, referenced by visualization components, compiled to a static site.
**Axis:** app-builder, deploy.
**Depth:** thin.

## Products & surfaces

| Surface | What it is |
|---|---|
| **Evidence** | Open-source static site generator/framework: Evidence-flavored Markdown pages with embedded, named SQL and viz components. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Named SQL in markdown fences | A code fence tagged with a query name runs as SQL (DuckDB dialect); the name becomes a referenceable identifier | yes |
| Components reference queries by name | Viz components take `data={query_name}` — no separate binding/wiring layer between query and chart | yes |
| Build-time static compile | Queries run **once at build**, and the site ships as static HTML with no per-viewer query execution | yes |

## Worth stealing

**Code-as-BI, no separate config layer.** A report is a markdown file. A SQL query is a named markdown code fence (` ```sql query_name `). A chart component consumes that query by name (`data={query_name}`). There's no drag-drop binding step and no separate "dataset" object to manage — the report source file *is* the full definition of data + presentation, reviewable as a plain text diff. Combined with **build-time execution** (queries run once, at build, and the deployed site is static HTML+JS with no runtime warehouse dependency — the same tradeoff Observable Framework makes), this produces reports that are simultaneously: version-controllable like code, fast to load like a static site, and deployable anywhere with no vendor runtime.

## Worth avoiding

Same tradeoff family as Observable Framework: freshness is bounded by build cadence, and there's no live drill-down against the warehouse without a rebuild — not a fit for ad hoc self-service exploration.

## Facts & figures

- Open source: `evidence-dev/evidence` on GitHub.
- SQL dialect for query fences: DuckDB.

## Sources

- [Evidence GitHub](https://github.com/evidence-dev/evidence) · [SQL Queries docs](https://docs.evidence.dev/core-concepts/queries) · [Markdown reference](https://docs.evidence.dev/reference/markdown) · [Component Queries](https://docs.evidence.dev/components/custom/component-queries)
