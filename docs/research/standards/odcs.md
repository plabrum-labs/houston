# Open Data Contract Standard (ODCS)

**What it is:** A vendor-neutral YAML specification (Bitol/Linux Foundation) for expressing a data contract — schema, quality rules, SLAs, ownership — in a form any tool can read or write.
**Axis:** semantic layer, data migration (validation), governance.
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **ODCS spec (currently v3.1.0)** | The YAML schema itself — not a product, a shared format multiple vendors (Soda, dbt tooling, Great Expectations, Monte Carlo, custom engines) can target. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Four-tier quality ladder**: `text` → `library` → `sql` → `custom` | Every quality rule declares which tier it lives at, from unexecuted prose up to a vendor-specific executable check | yes |
| `library` tier predefined metrics | Portable, tool-agnostic checks like `nullValues`, `duplicateValues`, `rowCount`, `missingValues`, `invalidValues` | yes |
| `custom` tier with `engine` + passthrough `implementation` | Lets a specific tool (Soda, Great Expectations, dbt, Monte Carlo, etc.) express something the standard doesn't model natively, without breaking portability of everything else | yes |

## Worth stealing

**The four-tier ladder gives every quality rule a home regardless of how automated it currently is — and that's the actual innovation, not the specific tiers.**

1. **`text`** — a human-readable prose description of a quality expectation. **Explicitly not yet executable.** This is the tier that matters most and that nobody else in this research set models: it's a first-class, structured place to write down **"we know this rule exists and we haven't automated checking it yet."** Tribal knowledge — the thing a departing analyst would have told you verbally — gets captured as a real artifact in the contract, not lost, not left as a comment in someone's head.
2. **`library`** — portable, predefined metrics with standardized names (`nullValues`, `duplicateValues`, `rowCount`, `missingValues`, `invalidValues`, etc.) that any conforming tool can execute the same way. Portable because the *name* of the check is the contract, not a tool-specific implementation.
3. **`sql`** — a single query, in the data platform's own SQL dialect, returning a numeric or boolean result. More expressive than the library tier, still portable in principle (any engine that can run SQL against that warehouse can run the check), but tied to a specific dialect.
4. **`custom`** — vendor-specific, carrying an explicit `engine` field plus a passthrough `implementation` blob the standard doesn't try to model. This is the escape hatch: something Soda or Great Expectations or Monte Carlo can do that the standard has no native vocabulary for gets expressed here without forcing the whole contract to be non-portable — only that one rule is tool-locked, not the entire document.

**Why this is worth stealing specifically:** every other data-quality tool researched in this set (Soda, Great Expectations, Monte Carlo) models quality rules as *executable checks* — the only state a rule can be in is "configured and running." ODCS is the only one in this set that models **"known but not yet automated"** as a legitimate, first-class, non-degraded state — a rule at the `text` tier isn't a stub or a TODO comment, it's a real entry in the contract that can be read, audited, and referenced, and that can **graduate to `library`/`sql`/`custom` later without changing where in the document it lives or how it's referenced.** That's a meaningfully different design stance from "quality rules only exist once someone codes them."

## Worth avoiding

Nothing distinct surfaced — the standard is young (v3.1.0) and its main exposure is adoption risk (whether tooling actually converges on it) rather than a documented design flaw.

## Facts & figures

- Current version: **v3.1.0** (backward compatible with v3.0.x).
- Governed under **Bitol** (Linux Foundation project).
- `custom` tier's documented example toolset: Soda, Great Expectations, dbt-tests, Monte Carlo, "and others."

## Sources

- [Data Quality — ODCS v3.1.0 docs](https://bitol-io.github.io/open-data-contract-standard/v3.1.0/data-quality/)
- [ODCS v3.1.0 is Here: Relationships, Richer Metadata, and Stricter Validation](https://dataintelligenceplatform.substack.com/p/odcs-v310-is-here-relationships-richer)
- [open-data-contract-standard — GitHub](https://github.com/bitol-io/open-data-contract-standard)
- [Open Data Contract Standard overview — entropy-data](https://www.entropy-data.com/learn/open-data-contract-standard)
