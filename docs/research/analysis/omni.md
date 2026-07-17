# Omni

**What it is:** A BI tool with a three-layer data model — raw schema, governed shared model, ad hoc workbook — where fields built ad hoc can be promoted upward into the governed layer.
**Axis:** semantic layer, workflow.
**Depth:** thin.

## Products & surfaces

| Surface | What it is |
|---|---|
| **Omni** | BI/analytics platform: spreadsheet-like workbooks over a layered semantic model, with SQL, Excel-formula, and NL query modes. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Three-layer model: schema / shared / workbook | Raw-mirroring layer → governed layer → ad hoc per-analysis layer, each extending the one below | yes |
| Field promotion | A field created ad hoc in a workbook can be **promoted** into the shared (governed) model, and from there toward the schema layer | yes |
| Bidirectional dbt sync | Logic can flow from dbt into Omni *and* from Omni's modeling layer back into dbt | yes |
| Excel-formula calc layer | Calculations can be written as Excel-style formulas, alongside SQL and natural language, over the same data | maybe |

## Worth stealing

**Promotion as the resolution to the governed-vs-ad-hoc tension.** Every BI tool has some version of "the analyst needs a field that isn't in the semantic model yet." Most either block it (governance wins, analysts route around the tool) or let it live forever ungoverned (ad hoc wins, nothing is ever trustworthy). Omni's **workbook model** sits explicitly *above* the schema and shared models as a sandbox for exactly this case — a new metric or join can be built and used immediately, scoped to that workbook. The mechanism that matters is the **promotion workflow**: a field that proves valuable can be explicitly promoted from workbook → shared model → (eventually) schema, moving it from "one analyst's ad hoc definition" to "the org's governed definition" without a rebuild or a rewrite, just a change in which layer owns it. This gives governance a *path*, not just a gate.

**Two-way dbt sync, not just read.** Omni reads dbt's models/metrics like most tools, but also pushes logic built in Omni's modeling layer back into the dbt project — described as one of few commercial BI platforms with genuine two-way sync. This matters for the same reason promotion matters: it keeps the semantic layer that analysts actually touch (in the BI tool, during live analysis) from diverging from the semantic layer that's version-controlled (in dbt).

## Worth avoiding

Not enough independent evidence in this pass to identify a specific failure mode; the promotion workflow's actual friction (how much manual review is required, whether promotion requires re-testing) wasn't verified beyond vendor/partner marketing pages.

## Facts & figures

- Positions itself as one of the few BI platforms with **bidirectional** dbt integration (vendor/partner-sourced, not independently benchmarked against competitors here).

## Sources

- [Omni data modeling](https://omni.co/data-modeling) · [Modeling in Omni docs](https://docs.omni.co/modeling) · [Omni's dbt integration](https://omni.co/blog/using-omni-dbt-integration) · [Maximize BI Efficiency with Omni's Three-Layer Model (Tasman)](https://www.tasman.ai/news/maximize-bi-efficiency-with-omnis-3-layer-model)
- **Not directly verified:** independent, non-partner confirmation of the "only BI tool with bidirectional dbt sync" claim.
