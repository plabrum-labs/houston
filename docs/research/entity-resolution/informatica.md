# Informatica (MDM)

**What it is:** Enterprise Master Data Management — consolidates records from multiple source systems into a "golden record" via configurable trust/survivorship rules, with full traceability back to sources.
**Axis:** data migration, semantic layer (golden record construction).
**Depth:** thin — one mechanism researched.

## Products & surfaces

| Product | What it is |
|---|---|
| **Multidomain MDM Hub** | Core consolidation engine: match, merge, trust-based survivorship. |
| **Data Steward tools (Merge Manager, Data Manager)** | UI for reviewing and manually overriding automated consolidation decisions. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **XREF rows** | Per-source-system cross-reference record retaining that system's own last-known values | yes |
| **Cell-level trust override** | A steward can override which source's value wins for a single field on a single merged record | yes |
| **Non-destructive merge** | Losing values are never discarded — retained and recoverable if the merge is later undone | yes |

## Worth stealing

**Non-destructive merge via retained XREF, with per-cell (not per-record) trust override.** For every source-system record that feeds a consolidated "base object," Informatica keeps a **cross-reference (XREF) row**: an identifier for the contributing system, that system's own primary key, and the most recent values it supplied. The consolidated record is a *view* computed from trust rules over these XREFs, not a destructive overwrite — per Informatica's own docs, "values that do not end up in the surviving record are always kept and managed by Informatica MDM Hub so that they are available should you choose to unmerge records." A steward can override survivorship **at the cell level** (which source wins for *this one field*), not just choose one record to dominate wholesale — click the cell that isn't currently highlighted/bold to make that source's value the winner for that field only. The override is scoped to manual merges and has to be applied through the merge action, not silently persisted.

## Worth avoiding

**"Why did this merge happen" is not a first-class query — it's reconstructed after the fact.** Unlike Senzing's `whyEntities`/`howEntity` (see `senzing.md`), Informatica's docs describe no equivalent single API call that explains a consolidation decision; the trail exists (XREF history, trust scores, steward overrides) but assembling "why do these two records share a golden record" into a coherent answer is left to whoever's reading the XREF and trust-score history, not handed back as a structured explanation.

## Facts & figures

None independently verified in this pass beyond the mechanism description.

## Sources

- [Cross-Reference (XREF) Tables](https://docs.informatica.com/master-data-management/multidomain-mdm/10-3/overview-guide/key-concepts/content-metadata/cross-reference--xref--tables.html)
- [Guidelines for Overriding Consolidation Trust Behavior](https://docs.informatica.com/master-data-management/multidomain-mdm/10-5/data-steward-guide/consolidating-data/merging-cell-data/guidelines-for-overriding-consolidation-trust-behavior.html)
- [Overriding Trust Settings](https://docs.informatica.com/master-data-management/multidomain-mdm/10-4/data-steward-guide/managing-data/editing-and-adding-records-manually/overriding-trust-settings.html)
- [About the Merge Manager](https://docs.informatica.com/master-data-management/multidomain-mdm/10-4/data-steward-guide/consolidating-data/about-the-merge-manager.html)
