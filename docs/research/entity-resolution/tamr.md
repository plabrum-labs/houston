# Tamr

**What it is:** AI-driven master data management, historically known for machine-learning-based entity resolution at scale; product surface has broadened into categorization/taxonomy matching.
**Axis:** data migration, semantic layer.
**Depth:** thin — docs asymmetry noted below, not glossed over.

## Products & surfaces

| Product | What it is |
|---|---|
| **Categorization projects** | Match records to a taxonomy; find each record's single best-fit category node. |
| **Mastering projects** | The entity-resolution / golden-record product — Tamr's original core offering. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Taxonomy-based categorization with representative-sample labeling | Curator labels a small representative sample against taxonomy nodes; model generalizes | maybe |
| Patented matching/blocking techniques (vendor claim) | Eliminates obvious non-matches, ranks likely candidates before deeper scoring | n/a — undetailed |

## Worth stealing / avoiding

**Not enough was independently documented to assess.** Accessible Tamr documentation covers **categorization and taxonomy matching in real depth** — the workflow of curating a unified dataset, labeling a representative sample against taxonomy nodes, and letting the model generalize is described concretely. **Entity resolution (Mastering) is covered only shallowly** in reachable docs: marketing language about "patented matching techniques" and relevance scoring, but no equivalent of Senzing's `whyEntities`/`howEntity`, Informatica's XREF/trust mechanics, or Reltio's read-time OV computation. **The record-matching loop for Tamr's ER product is inferred from general MDM-category knowledge, not verified against Tamr's own documentation** — flagging this explicitly rather than presenting inferred mechanics as confirmed.

## Facts & figures

None independently verified.

## Sources

- [Entity Resolution — Tamr](https://www.tamr.com/entity-resolution)
- [Categorization Projects — Tamr docs](https://docs.tamr.com/new/docs/overall-workflow-classification)
- [Mastering Projects — Tamr docs](https://docs.tamr.com/new/docs/overall-workflow-mastering)
- [Training Tamr Core to Categorize Records](https://docs.tamr.com/new/docs/training-tamr-to-categorize-records)

**Gap, stated plainly:** the ER/Mastering mechanism claims above are marketing copy, not documented implementation — this file should not be cited as evidence for how Tamr's matching actually works internally.
