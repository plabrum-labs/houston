# Identity

**What this category is:** authentication, authorization, and enterprise identity infrastructure — SSO/SCIM providers, CIAM platforms, and the ReBAC/policy engines that decide fine-grained "can this principal do this to this resource."
**Why it's in this research:** Houston sells to enterprises and is agent-native, which means it needs both the standard enterprise-identity checklist (SSO, SCIM, audit logs) and a permission model precise enough to scope agent tool access down to individual resources.
**Files:** 8.

## The players

| Company | What it is | Depth |
|---|---|---|
| [workos](workos.md) | "Enterprise-ready" checklist as a product — SSO, SCIM, audit logs, FGA, and MCP OAuth. The reference for what enterprise-ready concretely means | medium |
| [okta](okta.md) | The incumbent IdP most enterprise customers already run — relevant as the integration target, not a platform to build on | thin |
| [auth0](auth0.md) | Developer-first CIAM, now Okta-owned; the step-up-auth (`acr_values`/`max_age`) reference | thin |
| [stytch](stytch.md) | Connected Apps — turns the customer's own app into an OAuth IdP for agent/MCP access; recently acquired by Twilio | thin |
| [descope](descope.md) | Tenant-aware multi-IdP SSO; documents a specific SAML cross-tenant impersonation footgun | thin |
| [openfga](openfga.md) | CNCF-incubating, Zanzibar-inspired ReBAC engine; the shared Zanzibar/ReBAC background lives in this file | thin |
| [spicedb](spicedb.md) | The Zanzibar-purist ReBAC engine — consistency tokens (ZedTokens) and a relationship-change Watch API | thin |
| [cedar](cedar.md) | AWS's policy-language (not graph) authorization engine — the odd one out, strong on RBAC/ABAC, weaker on deep relationship graphs | thin |

WorkOS is the reference implementation for the category — it's the only file that documents the full "enterprise-ready" surface end to end (SSO, SCIM, audit logs, log streaming, FGA, MCP OAuth) with concrete mechanisms rather than positioning. Okta matters as the incumbent IdP on the other side of most integrations, not as something to build on. Auth0, Stytch, and Descope are each thin files anchored on one specific mechanism worth stealing. OpenFGA, SpiceDB, and Cedar form a matched trio — Zanzibar-family ReBAC engines plus the policy-language alternative — and are best read together.

## Convergence

**SCIM exists specifically because JIT provisioning has no offboarding path.** WorkOS's framing, stated as the core argument in `workos.md`: JIT fires on a login event, so it structurally cannot deprovision — an admin disabling a user in the IdP produces no login event, ever, so JIT has no hook to run on. SCIM's proactive push-deactivation is the only mechanism that closes this gap. This isn't disputed anywhere else in the category; it's the load-bearing argument for why "we support SSO" without SCIM is really "we support onboarding but not offboarding."

**ReBAC subsumes RBAC and ABAC, and the category converged on relationship graphs as the general substrate.** `openfga.md` states this precisely: a role is just a relation ("admin of workspace X"); an attribute can be modeled as a relation to a tagged object. Both OpenFGA and SpiceDB implement this Zanzibar-derived model; Cedar takes the opposite shape (explicit policy text over principal/action/resource attributes) but the category's own 2026 consensus, stated in both `openfga.md` and `cedar.md`, is **hybrid, not either/or**: RBAC/ABAC-shaped coarse policy (who can open the app, what plan tier) stays cheap and auditable; ReBAC earns its complexity only at the resource-level layer (can this user edit this document shared via a folder they're a member of).

**The list-endpoint problem is unsolved across every engine in the category.** "Filter this 10k-row query by policy" defeats the naive per-row check-call approach at scale. Zanzibar-family engines (OpenFGA, SpiceDB) mitigate it with reverse-indexed "list objects" queries — but only when the authorization graph itself is the source of truth for what to list. None of them solve the harder case: filtering an arbitrary application query (e.g., "top 50 by last-modified where the user has view access") by policy, because an external policy decision point can't push a predicate into someone else's query planner. Cedar's partial answer — compiling policy toward a SQL `WHERE`-clause-shaped filter — is flagged as unconfirmed against AWS's own docs in `cedar.md`, so treat it as a documented attempt, not a solved problem.

**Step-up authentication converged on the same two OIDC parameters everywhere.** `acr_values` (request a specific assurance level, verify via the returned `acr`/`amr` claims) and `max_age` (force reauthentication for one sensitive action, bounded window) are documented identically across Auth0 and Okta — unsurprising since Auth0 is Okta-owned and both share the same OIDC substrate, but notable that this is standards-level convergence, not vendor-specific innovation. RFC 9470 is now formalizing the resource-server-initiated version of the same pattern.

**Scoped, revocable, short-lived tokens replace shared credentials as the agent-access answer, independently at Stytch and WorkOS.** Stytch's Connected Apps ("your app becomes the IdP; the agent gets an OAuth token scoped to a subset of the delegating user's own permissions") and WorkOS's FGA-for-tool-permissions pitch ("the same permission graph gates both a human clicking a UI button and an agent calling the equivalent MCP tool") are the same underlying move: don't hand the agent a credential, hand it a narrow, expiring, structurally-bounded grant.

## Worth stealing

- **SCIM deactivate as the actual point of SCIM** (`workos.md`) — deprovisioning independent of any login event.
- **A versioned audit-log event envelope** (`workos.md`) — a `version` field lets the event schema evolve without breaking a customer's SIEM parser; `targets` as an array lets one action cover many resources.
- **Log Streams into a customer's own SIEM format** (`workos.md`) — Splunk HEC, Datadog ECS, S3, not a bespoke export blob — with the Datadog 18-hour ingestion-cutoff gotcha worth designing a durable buffer around if Houston ever streams logs.
- **FGA spanning UI and agent tool calls with one permission graph** (`workos.md`) — the same authorization model gates a human's button click and an agent's equivalent MCP tool call.
- **Step-up via standard OIDC params, not a bespoke flow** (`auth0.md`) — `acr_values` + `max_age`, now backed by RFC 9470 at the resource-server layer.
- **Connected Apps: your app becomes the OAuth IdP** (`stytch.md`) — agents get scoped, auditable, revocable tokens instead of shared credentials, with the token constrained to a subset of the delegating user's own permissions.
- **Tenant-aware multi-IdP SSO routed by email domain** (`descope.md`) — each tenant gets its own SAML/OIDC connection.
- **Never select the SAML validation key from inside the assertion being validated** (`descope.md`) — bind the key to the tenant via a channel outside the assertion's control (the resolved connection record from the login route/subdomain), and cross-check `AudienceRestriction`/`aud` against the SP's own registered entity ID. A standing checklist item if Houston ever terminates SAML directly.
- **ZedToken freshness modes** (`spicedb.md`) — `at_least_as_fresh` vs. `at_exact_snapshot` lets a caller trade freshness for latency per-request rather than the engine imposing one global consistency policy; the pattern is the thing to steal even if not the exact API.
- **Watch API for cache invalidation** (`spicedb.md`) — a streaming relationship-change feed for downstream systems maintaining their own denormalized permission caches.
- **Policy-as-readable-text with formal verification** (`cedar.md`) — AWS-published proofs of policy-set properties, a differentiator none of the graph-based engines offer.

## Worth avoiding

- **Okta's pricing model draws live criticism** — module-based, quote-driven, total cost often unclear until late in a sales cycle; some teams reportedly decline auto-renewal specifically to shop the governance/lifecycle add-ons (`okta.md`, analyst-reported).
- **Recursive/nested-group userset resolution is a genuinely hard, unsolved-for-free problem across the entire Zanzibar-family category** — "is this user in a group nested three groups deep with an inherited role" requires a heavily cached, purpose-built graph-index; it isn't a side effect you get from a general-purpose graph database (`spicedb.md`).
- **Cedar is a weak fit for deep relationship graphs** — it can express nested group/role inheritance but lacks the graph-native storage/indexing that makes it cheap at scale for SpiceDB/OpenFGA (`cedar.md`).
- **Stytch's MCP-auth investment trajectory is now uncertain post-Twilio-acquisition** — Twilio's stated rationale is fraud/reputation data, not MCP auth; a WorkOS-authored comparison (competitor-sourced, discount accordingly) claims "pure MCP authorization is not the strategic priority that drove the deal" and separately claims Stytch's SSO/SCIM maturity trails WorkOS/Auth0 — neither claim independently verified (`stytch.md`).

## Gaps

- **The list-endpoint problem has no general solution anywhere in the category** — every engine (OpenFGA, SpiceDB, Cedar) handles "list what this user can see from the authorization graph itself" reasonably, and none handle "filter an arbitrary application query by policy" without either denormalizing into the app's own query layer or accepting per-row check-call cost.
- **No independent (non-vendor) benchmark comparing SpiceDB and OpenFGA latency/consistency tradeoffs was located** — claims in both files trace to the vendors' own docs plus third-party comparison posts, not hands-on testing (`spicedb.md`, `openfga.md`).
- **Ramp Agents' permission model (covered in `../agents/ramp.md`) is a directly relevant unknown for this category too** — whether a customer-facing agent runs as a service principal or inherits individual user scope is unresolved there and worth tracking as identity-category-relevant.

## Notes

- Okta's headline figures (18,000+ customers, 100B+ monthly authentications, ~41% IAM market share) are analyst/vendor-reported and not independently cross-checked in `okta.md`.
- WorkOS's audit-log field schema (`action`/`actor`/`targets`/`context`/`occurred_at`/`version`) was reconstructed from search-result excerpts and an SDK example, not fetched from a current live schema-reference page — directionally correct, not guaranteed current.
- Descope's SAML key-selection warning is stated as a general SAML multi-tenant validation principle, not a confirmed historical Descope vulnerability or CVE.
