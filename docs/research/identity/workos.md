# WorkOS

**What it is:** The "enterprise-ready" checklist as a product — SSO, SCIM, audit logs, and now MCP auth, sold as drop-in infrastructure so a startup can pass an enterprise security questionnaire without building any of it themselves.
**Axis:** enterprise, agent (MCP auth specifically).
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **AuthKit** | Full auth product: SSO, SCIM, RBAC, MFA, session management, plus (new) MCP OAuth 2.1 authorization server. |
| **SSO** | SAML + OIDC, per-tenant connection, tenant discovery by email domain or a tenant-specific URL, then IdP routing. |
| **Directory Sync (SCIM)** | IdP-driven push provisioning: create, update, **deactivate**. |
| **Domain Verification** | DNS TXT record proving an org controls a domain, gates auto-join/SSO enforcement. |
| **Audit Logs** | Structured, versioned event envelope; queryable + exportable. |
| **Log Streams** | Push Audit Log events to Splunk HEC, Datadog, Elastic (ECS format), S3. |
| **FGA (Fine-Grained Authorization)** | Relationship-based permission layer, positioned explicitly for tool-level agent authorization. |
| **Connect** | Standalone OAuth middleware — MCP auth flows only, no migration of existing app auth. |
| **Service accounts / M2M** | OAuth client-credentials grant, short-lived scoped tokens. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| SCIM deactivate as the point of SCIM | Deprovisioning path independent of any login event | yes |
| Versioned event envelope | Schema evolves without breaking a customer's SIEM parser | yes |
| `targets` as a list | One action can touch many objects in one event | yes |
| Log Streams to SIEM formats | Splunk HEC / Datadog / Elastic ECS / S3, not a bespoke format | yes |
| AuthKit as MCP OAuth 2.1 AS | One config value turns AuthKit into an MCP-compliant authorization server | maybe |
| FGA for tool-level permissions | Same permission model spans app UI and agent tool calls | yes |
| Domain verification via DNS TXT | Standard, unglamorous, load-bearing for auto-join trust | yes |

## Worth stealing

### SCIM's actual argument: JIT has no deprovisioning path

WorkOS's own framing, worth quoting because it's the whole argument in one line: JIT provisioning **"falls completely flat during offboarding."** The mechanism is structural, not a missing feature — JIT provisioning happens *during* an SSO login assertion. Offboarding is the opposite of a login event: an IT admin disables a user in the IdP, and that user simply **never logs in again**. No assertion fires, so JIT has no hook to run on, ever. The account, active sessions, and data footprint sit fully live in the downstream app indefinitely.

**SCIM exists specifically to close this gap** — the IdP proactively pushes a deactivation event to every connected app, independent of whether the user ever attempts to log in again. This reframes SCIM from "nice-to-have sync" to "the only mechanism that can deprovision at all." Any Houston-side pitch of "we support SSO" without SCIM should be read internally as "we support onboarding but not offboarding" — a real gap enterprise security review will catch.

### Audit Log envelope — versioned by design

Fields: `action` (e.g. `user.signed_in`), `actor` (`id`, `type`, optional `name`/`metadata`), `targets` (an **array** — one action can touch many resources, e.g. a bulk role change), `context` (`location`/IP, optional `userAgent`), `occurred_at`, and **`version`** (an integer, explicitly declared and versioned per event schema before it's ever emitted).

The `version` field is the mechanism worth stealing directly: it lets the event *schema* evolve — add fields, change semantics — **without breaking a downstream customer's SIEM parser**, because the parser can branch on version rather than guess at shape. WorkOS also exposes a JSON Schema editor so customers can enforce strongly-typed `metadata` on the events they emit into their own audit trail.

### Log Streams — and its sharp edge

Push audit events directly into a customer's existing SIEM in that SIEM's native ingestion format: Splunk HEC, Datadog, Elastic ECS, S3. This is the right shape — enterprises already have a SIEM and don't want a new one; meeting them in Splunk's or Datadog's own format is lower friction than exporting a WorkOS-shaped JSON blob and making the customer transform it.

**⚠️ Gotcha worth recording, and worth designing around if Houston ever builds a log stream**: **Datadog rejects logs older than 18 hours.** If a stream pauses — a webhook endpoint goes down, a customer's ingestion pipeline breaks — for more than 18 hours, the backlog that accumulates during the outage is **silently and permanently unrecoverable** once the stream resumes, because Datadog's own ingestion API refuses timestamps outside that window. This is not a WorkOS bug; it's a property of streaming into someone else's time-windowed ingestion API that any log-streaming design needs to either buffer around (durable queue with alerting well inside 18h) or explicitly document as a customer risk.

### AuthKit as an MCP authorization server

AuthKit implements the 2025-11-25 MCP authorization spec surface directly: OAuth 2.1, PKCE, DCR (RFC 7591), Resource Indicators (RFC 8707), Protected Resource Metadata (RFC 9728), and CIMD. Architecture: **the MCP server is the resource server; WorkOS is the authorization server** — the MCP server's job shrinks to publishing its own resource metadata and validating bearer tokens, while AuthKit owns the full OAuth dance with the client. First-class framework integrations cited: FastMCP, the official MCP TS/Python SDKs, Cloudflare Workers, Vercel.

**Two integration shapes, worth distinguishing**: full AuthKit adoption (replaces your auth entirely) vs. **Connect**, positioned as *"standalone middleware providing only MCP OAuth flows — no migration of existing auth"* (vendor claim, unverified independently) — i.e., bolt MCP-compliant auth onto an app that already has its own SSO/session system, without touching it.

### FGA for tool-level permissions

WorkOS's own pitch, worth taking seriously as a framing rather than just a product claim: *"It is not enough to ask if an agent can call an API. We must ask if an agent can perform a specific action on a specific resource based on the delegating user, organizational policies, and the resource hierarchy."* FGA extends WorkOS's RBAC (roles/permissions/assignments) with hierarchical resource scoping — permissions flow down a resource tree so, e.g., a workspace admin's access to sub-projects doesn't need separate assignment at each level. The concrete claim for agents: **the same permission graph gates both a human clicking a button in the UI and an agent calling the equivalent MCP tool** — one authorization model, two callers.

## Facts & figures

- Datadog log-ingestion cutoff: **18 hours** — logs older than that at the point of ingestion are rejected. (Datadog's own limit, not WorkOS-specific; relevant to anyone building a paused/resumed log stream.)
- AuthKit MCP surface: OAuth 2.1, PKCE, DCR, RFC 8707, RFC 9728, CIMD — matches the current MCP spec's authorization requirements essentially point-for-point (vendor claim).

## Sources

- [SCIM vs JIT: Key differences explained](https://workos.com/guide/scim-vs-jit) · [JIT provisioning explained](https://workos.com/blog/jit-provisioning-sso-automated-user-provisioning) · [The developer's guide to Directory Sync and SCIM](https://workos.com/guide/the-developers-guide-to-scim)
- [Audit Logs product page](https://workos.com/audit-logs) · [Log Streams docs](https://workos.com/docs/audit-logs/log-streams) · [Introducing Log Streams (changelog)](https://workos.com/changelog/introducing-log-streams)
- [Datadog + Sumo Logic log management integration](https://www.datadoghq.com/blog/datadog-sumo-logic-log-management-integration/) (source for the 18-hour Datadog cutoff)
- [Model Context Protocol – AuthKit docs](https://workos.com/docs/authkit/mcp) · [Secure auth for MCP servers](https://workos.com/mcp) · [Best providers for MCP server authentication in 2026](https://workos.com/blog/best-mcp-server-authentication-providers)
- [Fine-Grained Authorization (FGA) docs](https://workos.com/docs/fga) · [WorkOS FGA: the authorization layer for AI agents](https://workos.com/blog/agents-need-authorization-not-just-authentication)
- **Not directly verified:** the exact Audit Log field-level schema (`action`/`actor`/`targets`/`context`/`occurred_at`/`version`) was reconstructed from search-result excerpts and a PHP SDK example rather than fetched directly from a live, current WorkOS schema-reference page (the `/docs/audit-logs/data-model` path 404'd; `/docs/events` has migrated to a newer unified events API without the same field breakdown). Treat field names as directionally correct, not guaranteed current. Connect's "no migration of existing auth" claim is vendor-stated, not independently tested.
