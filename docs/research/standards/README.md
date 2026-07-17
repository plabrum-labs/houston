# Standards

**What this folder is:** specs, not companies. Unlike the other three categories, these files document open, vendor-neutral interop protocols — the wire formats and schemas multiple products in this research set (and beyond) are expected to speak, rather than a single vendor's product surface.
**Why it's in this research:** Houston is agent-native and will need to expose apps to agents (MCP), describe data with enough rigor that other tools can consume it (ODCS), and make lineage legible across pipeline tools it doesn't control (OpenLineage). These are the interop surfaces Houston's own boundaries will likely be measured against.
**Files:** 3.

## The specs

| Spec | What it governs | Depth |
|---|---|---|
| [mcp](mcp.md) | Wire protocol (JSON-RPC 2.0) for connecting LLM applications to external tools, data, and prompts | deep |
| [odcs](odcs.md) | YAML schema for a data contract — schema, quality rules, SLAs, ownership | medium |
| [openlineage](openlineage.md) | Event/facet schema for emitting pipeline lineage — jobs, runs, datasets | medium |

## Convergence

These three specs don't converge with each other directly — they govern different layers (agent-tool wire protocol, data-contract shape, lineage event shape) and were built by different communities. The real through-line is structural, not architectural: **all three are the interop surface a given category depends on, and two of the three are moving fast enough that anything built against today's version has a defined shelf life.**

- **MCP** is mid-flight on a breaking architectural change. The current published spec is `2025-11-25`; a release candidate (`2026-07-28`, locked 2026-05-21) removes the `initialize`/`initialized` handshake and the `Mcp-Session-Id` header entirely, moving from stateful sessions to a stateless core (state travels in `_meta` on every request instead). The same RC **deprecates Roots, Sampling, and Logging** — Sampling in particular was a 2024–2025 headline capability (server-initiated LLM calls), and its deprecation is a real reversal: the spec authors concluded servers calling back into the model belongs at the application layer, not the protocol layer. A formal Active → Deprecated → Removed lifecycle (minimum 12 months between deprecation and earliest removal) is new as of this RC. **Anything Houston builds against MCP today should assume a defined migration inside the next year**, not treat 2025-11-25 as stable ground.
- **ODCS** is comparatively stable (v3.1.0, backward-compatible with v3.0.x) but its main convergence risk is external: whether the broader data-quality tooling ecosystem (Soda, Great Expectations, dbt tests, Monte Carlo — all named in `dbt.md`'s coverage of the related Open Semantic Interchange initiative) actually standardizes on it, versus each tool keeping its own format and treating ODCS as an export target.
- **OpenLineage** is the most stable of the three (an LF AI & Data Foundation project) but its value is entirely conditional on integrations emitting its schema faithfully — the spec itself has no enforcement mechanism, so a Spark or dbt integration that doesn't populate the `subtype`/`masking` fields correctly produces a lineage graph that looks complete but silently omits exactly the distinctions the spec was designed to carry.

## Worth stealing

- **MCP's Active → Deprecated → Removed lifecycle with a minimum 12-month window** (`mcp.md`) — a concrete, generalizable discipline for retiring a capability in any widely-implemented protocol without breaking existing implementations overnight.
- **MCP's confused-deputy attack writeup** (`mcp.md`) — a precise four-precondition pattern (static client ID + dynamic registration + third-party consent cookie + no per-client consent check) that generalizes to any OAuth proxy, not just MCP. Worth keeping as a checklist if Houston ever proxies OAuth to a third-party AS on an agent's behalf.
- **MCP's token-passthrough prohibition** (`mcp.md`) — "MUST NOT accept any tokens not explicitly issued for the MCP server" as a hard rule, with the reasoning spelled out (audit destruction, security-control circumvention, trust-boundary breakage) rather than left implicit.
- **ODCS's four-tier quality ladder** (`odcs.md`) — `text` → `library` → `sql` → `custom`. The genuinely novel piece is the `text` tier: a first-class, structured place to record "we know this rule exists and haven't automated checking it yet," so tribal knowledge becomes a real, auditable artifact instead of vanishing when the person who knew it leaves. Every quality rule can graduate tiers later without changing where it lives in the document.
- **OpenLineage's DIRECT vs. INDIRECT column lineage** (`openlineage.md`) — DIRECT (the output's value comes from this input, subtyped `IDENTITY`/`TRANSFORMATION`/`AGGREGATION`) versus INDIRECT (the input shaped the output's presence or shape without its value flowing through, subtyped `JOIN`/`GROUP_BY`/`FILTER`/`SORT`/`WINDOW`/`CONDITIONAL`). The canonical case: a column used only in a `WHERE` clause influences the result without ever appearing in the output — a compliance-relevant dependency most lineage systems (including several elsewhere in this research set) simply drop.
- **OpenLineage's `masking` boolean** (`openlineage.md`) — marks that a transformation irreversibly obfuscated a value en route (e.g., a hash of PII). The difference between "this report contains customer emails" and "this report contains a one-way hash of customer emails" is encoded directly on the lineage edge instead of requiring a human to go read the transformation code.
- **Marquez's three-way versioning (code, data, run)** (`openlineage.md`) — because job-code version and input-data version are independently tracked, "why did this number change" decomposes into two directly answerable questions instead of requiring log spelunking.

## Worth avoiding

- **MCP's tool-poisoning gap has no protocol-level fix, and the spec says so directly**: "While MCP itself cannot enforce these security principles at the protocol level, implementors SHOULD..." — followed by application-layer mitigations only. 5.5% of public MCP servers reportedly carry tool-poisoning vulnerabilities (research-benchmark-reported, not independently re-run). This is a real, acknowledged, unresolved gap in the standard as of both the current spec and the 2026-07-28 RC (`mcp.md`).
- **MCP's Client ID Metadata Documents (CIMD) have a spec-acknowledged localhost-impersonation hole**: an attacker can supply the *legitimate* client's metadata URL as its own `client_id`, and both the server and the user see the legitimate client's identity — the spec's own mitigation is UI-only (display and warn on the redirect URI hostname), not a structural fix (`mcp.md`).
- **OpenLineage's value is only as good as integration fidelity** — the DIRECT/INDIRECT typing and `masking` field are meaningless if the emitting integration doesn't populate them, and the spec has no enforcement mechanism to catch a silently-incomplete emitter (`openlineage.md`).
- **Marquez's per-run, per-dataset versioning has a documented storage-growth cost** — a real GitHub issue cites 864,000 field-mapping rows from a 20-column schema re-versioned every 10 minutes over 30 days. The fidelity that makes "why did this change" answerable also demands a retention/compaction story (`openlineage.md`).

## Gaps

- **ODCS models "known but unautomated" as a first-class state; nothing else in this entire research set (across all four categories) does.** Every data-quality tool researched elsewhere treats a quality rule as either configured-and-running or nonexistent — ODCS's `text` tier is the one place a rule can exist, be audited, and be referenced without yet being executable.
- **Cross-spec interop is still unresolved even within a single vendor's stack** — dbt Core 1.12 accepts OSI (Open Semantic Interchange, a separate but related initiative covered in `../semantic-layer/dbt.md`) documents versioned `0.1.0`/`0.1.1` against an "OSI v1.0" spec brand, a numbering mismatch that signals the broader interchange-format layer (adjacent to but distinct from ODCS/OpenLineage/MCP) is still stabilizing.

## Notes

- **MCP's spec status was checked 2026-07-17**: current published spec `2025-11-25`, confirmed live; RC `2026-07-28` locked 2026-05-21. Anything written about MCP's authorization or session model should be re-verified against whichever spec version is current at read time — this is the fastest-moving file in the entire research folder.
- ODCS and OpenLineage are both comparatively low-churn relative to MCP; re-verification urgency is lower but not zero (ODCS is young at v3.1.0; OpenLineage integrations are only as current as each pipeline tool's own emitter).
- MCP's tool-poisoning benchmark figures (MCPTox, MCPSecBench, the Unicode TAG-block concealment paper) were captured at abstract/search-result level, not independently re-verified in full (`mcp.md`).
