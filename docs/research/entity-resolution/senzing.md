# Senzing

**What it is:** An entity-resolution engine (library/API, not a UI product) that ingests records tagged `(DATA_SOURCE, RECORD_ID)` and groups them into resolved entities in real time as each record loads.
**Axis:** data migration, semantic layer (identity resolution underneath object mapping).
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Senzing SDK / engine** | Embeddable resolution engine — Python/Java/Go/C bindings, no standalone app. |
| **G2Export / entity APIs** | Read access to resolved entity graphs. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **`TRUSTED_ID`** | A `(TRUSTED_ID_TYPE, TRUSTED_ID_NUMBER)` pair injected on a record at load time forces it to resolve with every other record sharing that pair — and forces apart records with *different* numbers of the same type, even if every other attribute matches | yes |
| **`whyEntities(id1, id2)`** | API primitive: explains how/why two entities relate | yes |
| **`howEntity(id)`** | API primitive: step-by-step reconstruction of how an entity was built up record-by-record | yes |
| Non-persistent `ENTITY_ID` | Resolved-entity identifier is the lowest `OBS_ENT_ID` in the group, and gets reassigned as records are added/changed | no — flag, don't copy |

## Worth stealing

### TRUSTED_ID: override that survives reprocessing by construction, not by memory

`TRUSTED_ID` lives in an audited side table keyed by `(DATA_SOURCE, RECORD_ID)` and is **injected as input at ETL time on every load**, not stored as a one-time correction the engine "remembers." The mechanism that makes a manual override durable isn't a persistence guarantee bolted onto the matching engine — it's that the override is re-supplied as data on every single run. Reprocess the whole dataset from scratch tomorrow and the override still applies, because it was never a mutation to engine state; it's a value that travels with the record. Two records with the *same* `TRUSTED_ID_TYPE`+`TRUSTED_ID_NUMBER` are forced together regardless of how dissimilar their other attributes are; two records with *different* numbers of the same type are forced apart even if everything else matches. A data steward's manual call is expressed the same way the automated matcher expresses its own conclusions — as data, not as a side-channel exception list the engine has to remember to consult.

### whyEntities / howEntity as first-class API primitives, not reconstructed after the fact

Senzing ships explanation as a queryable primitive: `whyEntities(id1, id2)` explains the relationship between two entities, and `howEntity(id)` (`howEntityByEntityID()`) gives a step-by-step, record-by-record account of how an entity was assembled. Contrast Informatica (`informatica.md`), where "why did these merge" has to be reconstructed after the fact from trust scores and XREF history rather than being a direct answer the engine hands back. Making "why" a queryable API call rather than an artifact you reverse-engineer from logs is the structural difference worth stealing.

## Worth avoiding

### ENTITY_ID is not a stable identifier — and Senzing says so explicitly

The Resolved Entity ID (`ENTITY_ID`/`RES_ENT_ID`) is **not** a persistent, globally unique identifier. Mechanically, it's just the **lowest `OBS_ENT_ID` in the group** — so it can and does get reassigned as records are added, updated, or as the resolution graph shifts. Senzing's own documentation calls these **"transient groupings,"** not persistent identifiers. Anything downstream that treats `ENTITY_ID` as a stable foreign key (caching it, using it as a join key in another system, displaying it to end users as "the" identity) will silently break when the ID drifts. This is the single most important gotcha for anyone building on Senzing: the resolved-entity boundary is dynamic and correct; the *number naming* that boundary is not something to persist elsewhere.

## Facts & figures

None independently verified beyond the mechanism descriptions above — no published benchmark numbers found in this pass.

## Sources

- [How does an Entity ID behave?](https://senzing.zendesk.com/hc/en-us/articles/4415858978067-How-does-an-Entity-ID-behave)
- [How to force records together or apart](https://senzing.zendesk.com/hc/en-us/articles/360023523354-How-to-force-records-together-or-apart)
- [How to Handle Drifting Entity IDs in Entity Resolution Systems — Jeff Jonas (Medium)](https://jeffjonas.medium.com/how-to-handle-drifting-entity-ids-in-entity-resolution-systems-a0483a8282f2)
- [why_entities, why_records, why_record_in_entity flags](https://senzing.com/docs/flags/4/flags_why/)
- [G2Engine Why](https://docs.senzing.com/python/3/g2engine/why/index.html)
- [Senzing Entity Specification](https://www.senzing.com/docs/entity_specification/)
