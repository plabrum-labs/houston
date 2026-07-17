# OpenFGA

**What it is:** Open-source, CNCF-incubating authorization engine implementing relationship-based access control (ReBAC), directly inspired by Google's Zanzibar paper. Originated at Auth0, now vendor-neutral; Auth0 FGA is Okta's managed offering built on it.
**Axis:** enterprise (permissions substrate — relevant if Houston needs fine-grained authorization for agent tool access, not the schema/RLS layer itself).
**Depth:** thin — see `openfga.md`/`spicedb.md`/`cedar.md` as a set; the shared context (Zanzibar, ReBAC vs RBAC vs ABAC, the list-endpoint problem) is covered once here and referenced from the others.

## What it is, concretely

A relationship graph store plus a query engine: you define object types, relations between them (`owner`, `viewer`, `member`), and a check API answers "does user U have relation R on object O" by walking the graph, including through nested groups and computed unions. REST-first API, positioned as the easier onramp of the Zanzibar-family engines — broader language SDK support, managed-hosting path via Auth0 FGA.

## The shared background: Zanzibar, ReBAC, and why it subsumes RBAC/ABAC

**Google Zanzibar** (the 2019 paper) is the common origin for this entire category: a single, planet-scale authorization service backing Google Drive, YouTube, Calendar, etc., storing authorization as a graph of relationship tuples (`document:123#viewer@user:456`) rather than rows in an ACL table per app.

**ReBAC is a strict superset of RBAC**, and — the detail worth internalizing — **it natively covers ABAC too, when attributes are themselves expressed as relationships.** A role ("admin of workspace X") is just a relation; an attribute ("is in the EU region," "is a contractor") can be modeled as a relation to a tagged object rather than a separate attribute-evaluation system. This is why the category converged on relationship graphs as the general substrate rather than building three separate systems.

**The 2026 consensus, worth stating plainly: hybrid, not either/or.** Coarse policy (who can even open this app, what plan tier they're on) stays RBAC — cheap, auditable, doesn't need a graph. Resource-level policy (can this specific user edit this specific document that was shared with them via a folder they're a member of) is where ReBAC earns its complexity.

## The known hard problem: the list-endpoint problem

Every Zanzibar-style engine — and every policy-engine alternative — hits the same wall on **"filter this 10k-row query by policy."** The naive approach: fetch every candidate row, ask the authorization engine "can user U see row N?" for each one, discard the no's. That's O(n) calls against the policy engine per page render, and it collapses at scale.

Zanzibar-family engines mitigate this with **reverse indexing** — because the graph already knows "Folder X → Group Y" and "User A ∈ Group Y," a **"list objects"**-shaped query ("what can User A see") can be answered directly from the graph without touching application data first. But this only helps when the *authorization* graph is the source of truth for what to list; it does **not** solve the harder version — filtering an arbitrary *application* query (e.g., "top 50 documents by last-modified where the user has view access") by policy, because an external policy decision point can't push a predicate into someone else's query planner. That gap is the reason some engines (see `cedar.md`) ship a dedicated "compile this policy to a SQL WHERE clause" API as a partial answer, while Zanzibar-family engines lean on their own indexed list-objects endpoint instead.

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Relationship tuples as the storage primitive | Object-relation-subject triples, queried both directions (check + list) | yes |
| Contextual tuples | Attach request-scoped relationship facts (e.g., current IP range) to a single Check call without writing them to the store | maybe |
| CNCF incubation, broad SDKs | Positioned as the easiest onramp among Zanzibar-family engines | n/a — adoption signal |

## Facts & figures

- Originated inside Auth0; now a CNCF incubating project — vendor-neutral governance, not Okta-controlled despite the shared lineage.
- Auth0 FGA (Okta's managed hosting of OpenFGA) is REST-first; contrasts with SpiceDB/Authzed's gRPC-first managed offering.

## Sources

- [Alternatives to OpenFGA (Authzed)](https://authzed.com/learn/openfga-alternatives) · [OpenFGA Alternatives (Oso)](https://www.osohq.com/learn/openfga-alternatives)
- [OpenFGA vs Permify vs SpiceDB (2026)](https://www.pkgpulse.com/guides/openfga-vs-permify-vs-spicedb-zanzibar-authorization-2026)
- [SpiceDB vs Auth0 FGA: Relationship Authorization Compared](https://sph.sh/en/posts/spicedb-vs-auth0-fga/)
- [What is Google Zanzibar? (Oso)](https://www.osohq.com/learn/google-zanzibar) · [An Introduction to Google Zanzibar (Authzed)](https://authzed.com/learn/google-zanzibar) · [Why Google Zanzibar shines at building authorization (WorkOS)](https://workos.com/blog/google-zanzibar-authorization)
- [Protecting a List Endpoint (Authzed docs)](https://authzed.com/docs/spicedb/modeling/protecting-a-list-endpoint) — the list-endpoint problem, described from SpiceDB's side but the constraint is engine-agnostic.
- [Understanding ReBAC and ABAC Through OpenFGA and Cedar (Auth0)](https://auth0.com/blog/rebac-abac-openfga-cedar/)
- **Not directly verified:** no OpenFGA-specific benchmark or production-scale figures were located/fetched in this pass; positioning claims ("easier onramp," CNCF incubation status specifics) are aggregated from third-party comparison posts, not OpenFGA's own docs.
