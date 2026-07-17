# Cloudflare

**What it is:** The multi-tenant-runtime reference. Workers for Platforms is explicitly sold as the substrate for "anyone building an AI vibe coding platform" — a dispatch namespace holding thousands of untrusted customer Workers, plus a stateful-agent layer (Durable Objects, `McpAgent`, Sandboxes) and an egress-brokering pattern that shows up twice (Outbound Workers for sandboxes, `workers-oauth-provider` for MCP tokens) with the same shape: the credential lives in Cloudflare's layer, never in the untrusted code.
**Axis:** deploy, agent sandbox, enterprise.
**Depth:** deep.

## Products & surfaces

| Product | What it is |
|---|---|
| **Workers for Platforms** | Dispatch namespace + untrusted-mode customer Workers + your own routing Worker in front. |
| **Versions & Deployments** | Immutable code+config versions; deployments map traffic to one or two versions. |
| **Durable Objects** | Single-instance, strongly-consistent stateful compute + storage, addressable by ID. |
| **Containers / Sandboxes** | Longer-lived, heavier compute alongside Workers; 1–3s cold start (first-party). |
| **Agents SDK / `McpAgent`** | A Durable Object per MCP client session; handles SSE + Streamable HTTP transports. |
| **`workers-oauth-provider`** | OAuth 2.1 provider library for MCP servers built on Workers. |
| **Outbound Workers** | A programmable proxy Worker that intercepts and rewrites/authenticates sandbox egress. |
| **Source maps** | Automatic de-minification of production stack traces. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Dispatch namespace** | A single container holding every customer's Worker; no per-account script limit inside it | yes |
| **Untrusted mode** | Customer Workers never share cache even on the same zone; no `request.cf` access | yes |
| Synchronous first-upload | A 200 OK on first deploy now guarantees the script is live and dispatchable, closing a prior race condition | yes |
| Version ≠ deployment | A version is immutable code+config; a deployment maps 1–2 versions to a traffic split | yes |
| Gradual deployments | Percentage traffic split between two versions, via API/Wrangler/dashboard | yes |
| Storage not versioned with code | KV/R2/D1/DO state is explicitly **not** captured by a Worker version | yes — as a documented gap to design around |
| `McpAgent` | One Durable Object per MCP client session; SQL-backed session memory; survives idle-stream watchdog via keepalives | yes |
| `workers-oauth-provider` | Full OAuth 2.1 provider, four auth-source modes, your Worker never re-implements token issuance | yes |
| **Outbound Workers credential injection** | Sandboxed code makes a plain request; the Worker (outside the sandbox) attaches the real credential before it leaves | yes |
| Container/Sandbox cold start | Documented **1–3 seconds** | yes — rare honest first-party number |
| Source maps | Automatic de-minified stack traces in Tail Workers/Logs/Logpush, fetched async post-invocation | yes |

## Worth stealing

### Workers for Platforms — the dispatch namespace as the unit of multi-tenancy

A **dispatch namespace** is a container that holds every one of your customers' Workers. Your own **dynamic dispatch Worker** sits in front and routes each incoming request to the right customer Worker by name — the routing logic is your code, not a Cloudflare-managed router. Two properties do the actual isolation work: user Workers run in **untrusted mode**, which means they *"never shar[e] cache even on the same zone"* and cannot read `request.cf` (the metadata Cloudflare normally exposes about the request/client) — denying a class of side-channel and fingerprinting concerns. Cloudflare's own framing names the target buyer directly: *"anyone building an AI vibe coding platform, e-commerce platform, website builder, or any product that needs to securely execute user-generated code at scale."*

**First-time user Worker uploads are synchronous**: a 200 OK response now guarantees the script is fully provisioned and immediately dispatchable — this closed a real race condition where a platform could get a success response and then dispatch to a Worker that wasn't actually live yet, causing spurious failures right after a customer's first deploy. (Shipped ~February 2025, not April 2026 as the brief suggested — verify against changelog if the date matters.)

### Versions & Deployments — the immutable-artifact pattern, with an explicit storage caveat

A **version** is an immutable snapshot: bundled code, static assets, bindings, and compatibility settings, each with an ID and creator/timestamp metadata. A **deployment** decides which version(s) serve traffic — one version at 100%, or two versions split by percentage for a **gradual deployment**, controllable via dashboard, Wrangler, or the API. `wrangler deploy` couples these by default (new version, immediate 100% release); they can be decoupled for staged rollout control.

The documented gap worth carrying forward explicitly: **"Storage state is not versioned alongside code."** KV, R2, D1, and Durable Object state don't roll back when you roll back a Worker version — a version rollback is a code+config rollback only, and any schema or data assumptions baked into the new code stay in effect regardless of which version is serving traffic.

### `McpAgent` and the OAuth-for-MCP problem, solved as a library

Each MCP client session gets its **own Durable Object instance** with persistent SQL storage — the agent can genuinely "remember previous tool calls and responses it provided" because the DO *is* the session, not a lookup into a shared store. Streamable HTTP survives Cloudflare's ~5-minute idle-stream watchdog through keepalive frames; GET streams recover after disconnect via `Last-Event-ID` against an EventStore.

Cloudflare's stated rationale for shipping `workers-oauth-provider` as a first-party library: *"OAuth with MCP is hard to implement yourself, so when you build MCP servers on Cloudflare we provide it for you."* Four supported auth-source modes: **Cloudflare Access** (SSO via a configured IdP, Access policies gate entry), **third-party OAuth** (GitHub/Google — the MCP server exchanges the upstream token and issues its own), **your own auth** (email/social/SSO/MFA via the auth provider, self-managed), and **auth-as-a-service** (Stytch, Auth0, WorkOS, Descope as pluggable identity backends).

The token-handling detail worth stealing directly: *"Instead of passing the token it receives from the upstream provider directly to the MCP client, your Worker stores an encrypted access token in Workers KV. It then issues its own token to the client."* If the client-facing token leaks, an attacker gets only the scoped permissions your MCP server's tools expose — not the raw upstream credential (e.g., not a full-scope Google token). The library handles the KV write so application code never touches it directly, closing off an entire class of "developer forgot to encrypt the stored token" mistakes.

### Outbound Workers — the same credential-brokering shape, applied to sandbox egress

Outbound Workers for Sandboxes/Containers run **outside the sandbox**, in the regular Workers runtime, so they can hold real secrets the sandboxed code never sees. A sandboxed workload issues a plain, credential-less HTTP request; the Outbound Worker intercepts it via TLS interception and attaches the real credential before forwarding upstream. Cloudflare's summary: *"credentials are transparently attached before a request is forwarded upstream... No token is ever passed into the sandbox."* Secrets can be rotated in the Worker's environment and take effect on the next request with no sandbox-side change. Egress policy (allow/deny lists, per-instance) is dynamic and updatable without restarting the sandbox — the same "policy is separate from and mutable independent of the running compute" pattern Vercel Sandbox also implements.

### Honest cold-start number

Cloudflare's own docs, in two places (Container lifecycle architecture page and the Containers FAQ): *"Container cold starts can often be in the 1-3 second range, but this is dependent on image size and code execution time, among other factors."* This is one of only two vendors in this research set (with Fly.io) that publishes a real first-party cold-start figure rather than an unverifiable marketing number.

### Source maps as a production-safety default

Set `upload_source_maps = true`, `wrangler deploy`/`versions deploy` auto-generates and uploads the map (Wrangler ≥3.46.0, max 15MB gzipped). The map is fetched **asynchronously after the invocation completes**, so de-minifying a production stack trace costs zero CPU/latency on the request path — it's pulled only when an exception actually needs mapping, then surfaced in Tail Workers, Workers Logs, and Logpush already resolved to original source lines.

## Worth avoiding / caveats

- **Storage state not versioned with code** is a real gap for anyone building rollback semantics on top of Workers — a code rollback can leave the app talking to a schema/shape of KV/D1/DO data that the older code doesn't expect if a newer version's writes already landed.
- Untrusted-mode Workers losing `request.cf` access is a deliberate isolation tradeoff — any platform feature that wants geolocation/bot-score signals for tenant Workers has to proxy that data in deliberately, it isn't ambiently available the way it is for a trusted Worker.

## Facts & figures

- Container/Sandbox cold start: **1–3 seconds** (first-party, docs + FAQ).
- Source maps: GA, max 15MB gzipped, requires Wrangler ≥3.46.0.
- `McpAgent` idle-stream watchdog: ~5 minutes, survived via keepalive frames.
- Synchronous first-upload for dispatch namespaces: shipped via changelog ~February 2025 (`developers.cloudflare.com/changelog/post/2025-02-20-synchronous-uploads/`).
- Outbound Workers credential injection / dynamic egress for Sandboxes: changelog dated April 2026 (`2026-04-13-sandbox-outbound-workers-tls-auth`).

## Sources

- [Workers for Platforms](https://developers.cloudflare.com/cloudflare-for-platforms/workers-for-platforms/) · [Synchronous uploads changelog](https://developers.cloudflare.com/changelog/post/2025-02-20-synchronous-uploads/)
- [Versions and Deployments](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/) · [Gradual deployments](https://developers.cloudflare.com/workers/versions-and-deployments/gradual-deployments/)
- [Containers overview](https://developers.cloudflare.com/containers/) · [Container lifecycle/architecture](https://developers.cloudflare.com/containers/platform-details/architecture/) · [Containers FAQ](https://developers.cloudflare.com/containers/faq/)
- [McpAgent API](https://developers.cloudflare.com/agents/model-context-protocol/mcp-agent-api/) · [MCP Authorization](https://developers.cloudflare.com/agents/model-context-protocol/authorization/) · [Build and deploy remote MCP servers (blog)](https://blog.cloudflare.com/remote-model-context-protocol-servers-mcp/) · [workers-oauth-provider (GitHub)](https://github.com/cloudflare/workers-oauth-provider)
- [Secure credential injection and dynamic egress policies for Sandboxes (changelog)](https://developers.cloudflare.com/changelog/post/2026-04-13-sandbox-outbound-workers-tls-auth/) · [Dynamic, identity-aware, and secure Sandbox auth (blog)](https://blog.cloudflare.com/sandbox-auth/)
- [Source maps and stack traces](https://developers.cloudflare.com/workers/observability/source-maps/) · [New tools for production safety (blog)](https://blog.cloudflare.com/workers-production-safety/)
- **Not directly verified in this pass:** exact per-account script-limit-inside-namespace wording (paraphrased from search summary, not a direct doc fetch); brief's "April 2026" date for synchronous uploads appears to actually be Feb 2025 per the changelog URL — flagging the discrepancy rather than silently correcting it.
