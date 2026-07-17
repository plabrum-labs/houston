# Reltio

**What it is:** Cloud-native MDM competitor to Informatica. Same golden-record problem, different survivorship architecture: computed at read time instead of at merge time.
**Axis:** data migration, semantic layer (golden record construction).
**Depth:** thin.

## Products & surfaces

| Product | What it is |
|---|---|
| **Reltio MDM Hub** | Match/merge engine plus API-driven entity retrieval. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Crosswalks retained per-value** | Every contributing source's value for every attribute is kept, not collapsed at merge time | yes |
| **Survivorship computed at read time** | The "winning" value (Operational Value, OV) for each attribute is calculated on the fly per API call, not baked in during the merge | yes |
| `CONSOLIDATION_IND` | Per-record/relationship consolidation status flag | maybe — see caveat |

## Worth stealing

**Survivorship as a query-time computation, not a write-time decision.** Reltio's documentation states this as an explicit differentiator from other MDM systems: survivorship "doesn't occur during the merge and executes in real-time only when the entity is being retrieved during an API call," processing each attribute according to its survivorship rule to produce an **Operational Value (OV)** computed just-in-time. Because the underlying crosswalk data (every source's contributed value) is retained rather than collapsed, changing a survivorship *rule* retroactively changes what every past merge looks like on next read — no backfill or re-merge required. This is the more general pattern worth noting: separating "what data exists" (crosswalks, append-only) from "what value wins" (a rule evaluated at read time) makes the winning-value logic changeable without touching historical data at all.

## Worth avoiding

Nothing distinct surfaced independently in this pass.

## Facts & figures

**`CONSOLIDATION_IND` value 9 ("on hold") is widely reported in secondary sources but could not be verified here** — the source documentation page returns a 403 and no alternate primary source was found. **Values 1–4 are confirmed to exist** as consolidation-status indicators in Reltio's data model, but their exact semantics beyond that were not independently re-verified in this pass; treat any specific value-9 claim as unverified until the primary docs page is reachable.

## Sources

- [Advanced Survivorship Strategies](https://docs.reltio.com/en/model/consolidate-data/design-survivorship-rules/advanced-survivorship-strategies)
- [Design survivorship rules](https://docs.reltio.com/en/model/consolidate-data/design-survivorship-rules)
- [Consolidating relationship crosswalks](https://docs.reltio.com/en/developer-resources/relation-management-apis/relation-management-apis-at-a-glance/relations-api/create-relationships/consolidating-relationship-crosswalks)
- **Gated/unreachable:** the page documenting `CONSOLIDATION_IND` value semantics 403s; not independently verifiable in this pass.
