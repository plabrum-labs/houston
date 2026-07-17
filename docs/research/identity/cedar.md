# Cedar

**What it is:** AWS's open-source authorization policy language, used internally at AWS (IAM-adjacent) and exposed externally as **Amazon Verified Permissions (AVP)**. Policy-language-shaped rather than graph-shaped — the odd one out relative to `openfga.md`/`spicedb.md`. See `openfga.md` for shared Zanzibar/ReBAC background.
**Axis:** enterprise (permissions substrate).
**Depth:** thin.

## What distinguishes it

Cedar is a **policy-based** engine, not a relationship-graph engine: you write explicit `permit`/`forbid` statements over principals, actions, resources, and their attributes, and a request is evaluated against the policy set at check time — closer in spirit to OPA/Rego than to Zanzibar. Positioned for readability and static analyzability: policies are meant to be human-reviewable and formally verifiable (AWS has published proofs of certain policy-set properties using Cedar's formal semantics), which graph-shaped relationship stores don't offer in the same way.

**Good fit**: RBAC and ABAC expressed as attribute conditions on principal/resource (`resource.owner == principal.id`, `principal.department == resource.department`) — this is Cedar's comfortable territory, and it's genuinely strong here: explicit, readable, statically checkable policy text.

**Weaker fit**: deep relationship graphs — "is this user a member of a group that's nested three groups deep with an inherited role from a parent workspace" is exactly the shape Zanzibar-family engines were built to index efficiently; Cedar can express it, but doesn't have the graph-native storage/indexing to make deep nested-relationship queries cheap at scale the way SpiceDB/OpenFGA do.

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Policy-as-readable-text | `permit`/`forbid` statements, explicit and reviewable, not a graph traversal | yes — for the coarse-policy half of a hybrid model |
| Formal verification | AWS-published proofs of certain policy-set properties | maybe — high-assurance niche |
| Query Plan-style compilation (category-wide feature, not unique to Cedar) | Compiles policy logic toward a data-layer filter (e.g., a SQL predicate) to partially address the list-endpoint problem | maybe |

## Where it sits in the 2026 hybrid consensus

Per the category-wide 2026 consensus (see `openfga.md`): **RBAC/ABAC-shaped coarse policy, ReBAC for resource-level.** Cedar is the natural engine for the first half — plan tiers, feature flags, department-based rules, anything expressible as attribute conditions without needing to walk a relationship graph. It is a weaker choice than SpiceDB/OpenFGA for the second half, specifically deep or highly nested relationship structures.

## Facts & figures

- Backing product: **Amazon Verified Permissions (AVP)** — AWS-managed Cedar policy evaluation service.
- Cedar has published formal-methods work (proofs about policy-set behavior) — a differentiator from every graph-based engine in this category, none of which offer comparable static verification.

## Sources

- [Top Alternatives to AWS Cedar (Oso)](https://www.osohq.com/learn/aws-cedar-alternatives-authorization-tools)
- [Understanding ReBAC and ABAC Through OpenFGA and Cedar (Auth0)](https://auth0.com/blog/rebac-abac-openfga-cedar/)
- [Google Zanzibar vs OPA — Graph vs. Code Based Authorization (Permit.io)](https://www.permit.io/blog/zanzibar-vs-opa)
- [Control Access to MCP Tools with FGA — Auth0 (Cedar/AVP appears in the broader FGA-for-agents comparison set)](https://auth0.com/ai/docs/mcp/get-started/secure-mcp-server-with-auth0-fga)
- **Not directly verified:** Cedar's formal-verification claims and the specifics of any "Query Plan" style SQL-filter compilation feature were not confirmed against AWS's own Cedar/AVP documentation in this pass — stated here based on third-party comparison posts and general category knowledge; treat as directionally correct, not quoted from a primary source.
