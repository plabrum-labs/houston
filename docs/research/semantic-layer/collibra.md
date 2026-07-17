# Collibra

**What it is:** An enterprise data governance platform built around a business glossary, a data catalog, and a workflow engine — the governance-process layer (approvals, stewardship, certification) more than a technical lineage/access-control layer.
**Axis:** governance, glossary, workflow/process.
**Depth:** thin — scoped intentionally short per research brief; glossary-linkage and BPMN workflow claims verified against docs and vendor pages.

## Products & surfaces

| Product | What it is |
|---|---|
| **Business Glossary** | Curated business terms (e.g., "revenue," "active customer") with definitions, ownership, and approval status. |
| **Data Catalog** | Technical asset inventory (tables, columns, reports) that glossary terms link into. |
| **Guided Stewardship** | The linking layer connecting glossary terms to physical catalog assets. |
| **Workflow engine** | BPMN 2.0-based process engine for approvals, certifications, requests, escalations. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Term-to-asset linking** | A glossary term is linked directly to the physical tables/fields that produce it, not just defined in prose | yes |
| **BPMN workflow engine** | Term approval and asset certification run through a real process engine (script/service tasks, human tasks) | yes |

`Steal?` is a first-pass signal only, not a decision.

## Worth stealing

### The linkage that keeps a glossary alive

Collibra links glossary terms directly to the physical assets that implement them — "revenue" in a financial report traces back to the exact tables and fields that produce it, via a bridging layer (Guided Stewardship) between business definition and technical implementation. The practitioner point that matters more than the feature itself: **"this linkage separates a live glossary from a documentation archive."** Every standalone glossary — a wiki page, a spreadsheet of term definitions, a Confluence doc — rots, because nothing forces the definition to stay attached to the thing it describes once the underlying tables change. The definition and the implementation drift apart silently, and nobody notices until the numbers disagree. A structural link that ties the term to specific columns is what prevents that: when the underlying table changes, the link is either updated or visibly broken, rather than quietly stale prose nobody re-reads.

### A real process engine for term approval and certification

Term approval, asset certification, and related governance workflows run on a **BPMN 2.0 workflow engine** — human tasks, service tasks, and script tasks composed into deployable workflow definitions, not an informal "someone approves it in a spreadsheet" process. This makes governance state (draft / under review / approved / certified) a first-class, auditable, enforceable status rather than a convention team members are expected to follow. Coupled with term-to-asset linking, it means "is this metric approved for use" is a queryable fact tied to a specific certified definition, not tribal knowledge.

## Worth avoiding

- The linkage mechanism (Guided Stewardship) still depends on someone doing the initial linking work — it prevents *drift after linking*, not the initial cost of building the link. A glossary with unlinked terms gets none of the "live" guarantee.

## Facts & figures

- Workflow engine is built on BPMN 2.0, Groovy, and the Collibra Java API (per Collibra's own certification-track description).
- Not independently verified beyond vendor/product-resource-center pages: customer counts, deployment scale.

## Sources

- [Business Glossary (product docs)](https://productresources.collibra.com/docs/collibra/latest/Content/BusinessGlossary/to_business-glossary.htm)
- [Business glossary (product page)](https://www.collibra.com/use-cases/solution/business-glossary) · [What is a Business Glossary?](https://www.collibra.com/blog/what-is-a-business-glossary)
- Collibra workflow/certification track description (BPMN 2.0, Groovy, Collibra Java API) — via WebSearch summary of Collibra training/certification pages
- **Not directly verified:** the precise quoted phrase "this linkage separates a live glossary from a documentation archive" was returned by a WebSearch summarization tool rather than confirmed on a fetched primary page — treat as a close paraphrase of consistent Collibra messaging, not a verbatim sourced quote.
