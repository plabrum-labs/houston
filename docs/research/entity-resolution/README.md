# Entity resolution

**What this category is:** matching and merging records that refer to the same real-world entity across sources — probabilistic/ML pairwise matching engines (Senzing, Splink, Zingg) and enterprise MDM "golden record" platforms (Informatica, Reltio, Tamr) that consolidate matched records into a single trusted view.
**Why it's in this research:** identity resolution is the layer underneath any semantic object model that ingests from multiple sources — it determines whether "two records" become "one object," and how that decision is audited, overridden, and kept alive as more data arrives.
**Files:** 6.

## The players

| Company | What it is | Depth |
|---|---|---|
| [senzing](senzing.md) | Embeddable real-time resolution engine (library/API, not a UI); `TRUSTED_ID` and `whyEntities`/`howEntity` as first-class primitives | medium |
| [splink](splink.md) | OSS probabilistic (Fellegi-Sunter) record linkage library over SQL backends | medium |
| [zingg](zingg.md) | OSS active-learning matching library — 30–50 labeled pairs to production quality | medium |
| [informatica](informatica.md) | Enterprise MDM — golden record via configurable trust/survivorship, XREF non-destructive merge | thin (one mechanism) |
| [reltio](reltio.md) | Cloud-native MDM competitor to Informatica — survivorship computed at read time, not write time | thin |
| [tamr](tamr.md) | AI-driven MDM; categorization documented in depth, entity-resolution/Mastering only marketing-depth | thin, docs asymmetry flagged |

Senzing is the reference implementation for the matching-engine tier — it's the only one with documented, queryable explanation primitives (`whyEntities`/`howEntity`) and an override mechanism (`TRUSTED_ID`) that's durable by construction rather than by the engine "remembering" a correction. Splink and Zingg are the open, self-hostable alternatives, differentiated by training approach (EM-estimated probabilistic model vs. active-learning-driven). On the MDM side, Informatica is the established enterprise reference (XREF-based, write-time survivorship); Reltio is the architectural counterpoint (read-time survivorship); Tamr is thin and its core ER claims are explicitly flagged as unverified marketing language, not documented mechanism.

## Convergence

**Pairwise matching is at a practical ceiling — the OpenSanctions Pairs finding, shared across `splink.md` and `zingg.md`.** A large real-world benchmark (arXiv:2603.11051 — 755,540 labeled pairs, 293 sources, 31 countries) shows a production rule-based baseline at 91.33% F1, off-the-shelf LLMs (GPT-4o) reaching 98.95% F1, and results approaching observed human labeling consistency. The paper's own conclusion, independently corroborated in both files: further effort should shift to **blocking, clustering, provenance modeling, and uncertainty-aware review** rather than continuing to tune the pairwise classifier. This directly undercuts Zingg's core value proposition (active learning to cheaply train a pairwise matcher) even while the file notes Zingg's mechanism stays valuable for being cheap, auditable, and not dependent on sending data to a third-party model. Error modes are complementary, not overlapping — rule-based systems over-match (false positives), LLMs fail on cross-script transliteration and identifier/date inconsistencies a rule catches trivially — so neither approach dominates outright, but the ceiling finding is the real signal.

**Never mutate the source; re-apply human decisions as inputs, not one-time patches.** This pattern shows up independently across three different architectures:
- **Senzing's `TRUSTED_ID`** is injected as data at every ETL load, not stored as a remembered exception — reprocessing the whole dataset from scratch tomorrow still applies the override, because it was never a mutation to engine state.
- **Informatica's XREF rows** retain every contributing source's last-known values; the golden record is a *view* computed from trust rules over these XREFs, and a losing value is "always kept and managed... available should you choose to unmerge."
- **Reltio's crosswalks** go one step further architecturally: survivorship is computed **at read time**, per API call, from retained per-source values — so changing a survivorship *rule* retroactively changes every past merge's output on next read, with no backfill required.

The generalizable pattern across all three (and Palantir's Object Data Funnel, in `../semantic-layer/palantir.md`, which does the same thing for ontology overlays): **separate "what data exists" (append-only, retained per source) from "what value currently wins" (a rule evaluated fresh) — this is what makes both auditability and rule changes cheap.**

**Explaining a match is not universally a first-class primitive — and the gap is named explicitly.** Senzing ships `whyEntities`/`howEntity` as direct, queryable API calls. Informatica's file states plainly that no equivalent exists in its documentation — "why did these merge" has to be reconstructed after the fact from trust scores and XREF history rather than handed back as a structured answer. This is a real, named capability gap between two enterprise-grade approaches to the same underlying problem, not a difference in marketing emphasis.

## Worth stealing

- **`TRUSTED_ID` as a re-suppliable override, not a remembered exception** — a manual steward decision expressed the same way the automated matcher expresses its own conclusions: as data that travels with the record (`senzing.md`).
- **`whyEntities`/`howEntity` as queryable API primitives** — explanation as a direct call, not an artifact reverse-engineered from logs (`senzing.md`).
- **Cell-level (not record-level) trust override** — a steward can override survivorship for one field on one merged record without dominating the whole record (`informatica.md`).
- **Survivorship as a query-time computation** — decoupling "what data exists" from "what value wins" makes rule changes retroactive and backfill-free (`reltio.md`).
- **Active learning by lowest-model-confidence sampling** — Zingg's `findTrainingData` makes "how many labels do I need" tractable (30–50 pairs, not "label thousands and hope") (`zingg.md`).
- **Term-frequency adjustment decoupled from the trained model** — Splink's TF correction is a separate multiplicative term computed from a frequency table, toggleable without retraining the EM-estimated `m` probability (`splink.md`).
- **Deletes deliberately outside the conflict-resolution policy** — Informatica's non-destructive merge still treats a deletion as final regardless of datasource state, an explicit carve-out from the general survivorship logic (`informatica.md`).

## Worth avoiding

- **Treating a resolved-entity ID as a stable identifier when it explicitly isn't.** Senzing's `ENTITY_ID` is just the lowest `OBS_ENT_ID` in a group — Senzing's own docs call these "transient groupings." Anything downstream that caches it or uses it as a join key will silently break as the ID drifts (`senzing.md`).
- **Citing Tamr's entity-resolution mechanics as documented fact.** The file explicitly flags that ER/Mastering coverage in reachable docs is marketing-depth only ("patented matching techniques," no equivalent of `whyEntities`, XREF, or read-time OV) — the record-matching loop described is inferred from general MDM-category knowledge, not verified against Tamr's own documentation (`tamr.md`).
- **Assuming an unverifiable secondary-source value semantics is fact.** Reltio's `CONSOLIDATION_IND` value 9 ("on hold") is widely reported in secondary sources but the primary docs page 403s — flagged as unverified rather than asserted (`reltio.md`).

## Gaps

- **No researched vendor documents a general clustering/blocking strategy at the depth the OpenSanctions Pairs paper argues effort should now go toward.** All six files describe pairwise matching or merge/survivorship mechanics; none has documented mechanism for the blocking/clustering/uncertainty-aware-review shift the benchmark paper recommends as the next frontier.
- **No cost-per-match or dollar figures exist for any matcher in this set** — the Splink file explicitly notes the OpenSanctions paper reports none, and flags a documented prior hazard of a fabricated cost claim from an earlier, unreliable fetch of the same paper.

## Notes

- The OpenSanctions Pairs paper (arXiv:2603.11051) was cross-checked directly against the abstract page rather than taken from a single search summary, specifically because of a documented prior hazard of fabricated summaries for this exact paper in earlier research.
- Tamr's docs show a real asymmetry: categorization/taxonomy-matching workflow is documented in genuine depth; entity resolution (Mastering), the product's original core offering, is not. This asymmetry is itself worth treating as a finding, not glossed over.
- Reltio's `CONSOLIDATION_IND` value-9 semantics are unverified (403 on primary docs); values 1–4 are confirmed to exist but their exact semantics weren't re-verified beyond that.
