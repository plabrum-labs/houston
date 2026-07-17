# Stytch

**What it is:** Developer-first auth API, historically strongest in consumer/passwordless flows; shipped **Connected Apps**, an explicit play to make an application into its own OAuth 2.0/OIDC identity provider for agent and MCP use cases. Acquired by **Twilio**, announced **2025-10-30**, closed **2025-11-14**.
**Axis:** enterprise, agent.
**Depth:** thin.

## Products & surfaces

Core auth API (passwordless, OTP, biometrics), B2B org/SSO product, and **Connected Apps** — turns the customer's own application into an OAuth 2.0 / OIDC IdP so it can grant scoped, auditable, revocable access to agents/MCP servers instead of sharing raw user credentials. Positioned for remote MCP servers specifically (including a documented Cloudflare Workers integration path).

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Connected Apps | Your app becomes the OAuth IdP; agents get scoped tokens instead of credentials | yes |
| RBAC scope sets | Agents inherit only the permission subset the delegating user already has | yes |

## Worth stealing: Connected Apps as "your app is the IdP"

The core reframe: instead of an agent authenticating *as* the user (shared credentials, session cookies, or a static API key), the application itself becomes the authorization server, and the agent gets an OAuth token scoped to exactly what it needs. Stytch's own framing: this lets an app *"grant agents scoped, auditable, revocable access to user data instead of sharing raw credentials."* The RBAC model is structured so an agent's token can only ever be a subset of the delegating user's own permissions — the agent can't accumulate access the human didn't have.

## Worth noting: the acquisition changes the strategic picture

Twilio announced the Stytch acquisition **October 30, 2025**, closed **November 14, 2025**. Twilio's own stated rationale is to combine Stytch's identity stack with Twilio's phone/email reputation data to distinguish "humans, trusted agents, and rogue agents" — a fraud/reputation play, not an MCP-auth play.

**⚠️ A WorkOS-authored comparison piece makes a pointed claim: "pure MCP authorization is not the strategic priority that drove the deal."** That's a direct competitor characterizing an acquirer's motives to argue customers should discount Stytch's MCP roadmap — **treat as marketing, not fact**, but the underlying observation (Stytch is now a subsidiary of a CPaaS company whose thesis is fraud/reputation data, not purpose-built enterprise CIAM) is verifiable from Twilio's own announcement and is a reasonable thing to weigh when betting on Stytch's MCP investment trajectory. The same WorkOS piece also asserts Stytch's SSO/SCIM/Directory Sync/Admin Portal/audit logs are "weaker... than WorkOS or Auth0" — again vendor-authored, unverified independently here, but consistent with Stytch's historical positioning as consumer/passwordless-first rather than B2B-enterprise-first.

## Facts & figures

- Twilio–Stytch: announced **2025-10-30**, closed **2025-11-14**.
- Connected Apps documented integration path includes Cloudflare Workers-deployed MCP servers.

## Sources

- [Stytch Connected Apps](https://stytch.com/connected-apps) · [Remote MCP servers guide](https://stytch.com/docs/connected-apps/guides/remote-mcp-servers) · [Remote MCP Server Authorization](https://stytch.com/docs/guides/connected-apps/mcp-server-overview) · [Integrate with MCP servers on Cloudflare](https://stytch.com/docs/guides/connected-apps/mcp-servers)
- [The best providers for MCP server authentication in 2026 (WorkOS)](https://workos.com/blog/best-mcp-server-authentication-providers) — source of the "not the strategic priority" characterization; **competitor-authored, discount accordingly.**
- [Stytch's Business Breakdown & Founding Story (Contrary Research)](https://research.contrary.com/company/stytch) — background on the Twilio acquisition timeline.
- **Not directly verified:** exact Twilio deal terms/valuation not fetched; WorkOS's claims about Stytch's relative SSO/SCIM maturity are one vendor's comparison of a competitor, not cross-checked against Stytch's own docs in this pass.
