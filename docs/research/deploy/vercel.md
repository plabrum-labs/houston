# Vercel

**What it is:** The deploy-DX reference. Immutable deployments, instant traffic control, and a platform-for-platforms surface (Vercel for Platforms, Sandbox) aimed explicitly at people building multi-tenant and AI-generated-app products.
**Axis:** deploy, enterprise, agent sandbox.
**Depth:** deep.

## Products & surfaces

| Product | What it is |
|---|---|
| **Deployments** | Immutable build artifacts; a separate "alias" layer decides which artifact serves traffic. |
| **Instant Rollback** | Repoint the production alias to a prior aliased deployment; no rebuild. |
| **Rolling Releases** | Percentage-based canary traffic split between two deployments, staged, observable, abortable. |
| **Skew Protection** | Pins a client session to the exact deployment (frontend + backend) it loaded. |
| **Drains** | Streams logs/traces/analytics/audit-logs to external systems (custom HTTP, native integrations, S3). |
| **Environment Variables** | Scoped secrets store; sensitive variables are write-only. |
| **Secure Compute** | Enterprise dedicated network, static IPs, VPC peering into customer AWS. |
| **Vercel for Platforms** | Docs/tooling for building multi-tenant or multi-project SaaS on Vercel (wildcard domains, per-tenant custom domains). |
| **Vercel Sandbox** | Firecracker microVM compute for running untrusted/agent-generated code. |
| **RBAC / SAML SSO / SCIM** | Team and project role model, enterprise identity integration. |
| **Audit Logs** | Immutable record of team + (per their framing) agent actions. |
| **Turborepo Remote Caching** | Hash-keyed build/task cache shared across local dev and CI. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Instant Rollback** | Alias repoint to a previously-aliased deployment, no rebuild, ~instantaneous | yes |
| Rollback eligibility rule | Only deployments *previously aliased to production* are rollback-eligible | yes |
| "Promote" undoes a rollback | Rollback disables auto-assignment of the production alias; promoting a deployment re-enables it | yes |
| **Rolling Releases** | Multi-stage percentage traffic shift, cookie-bucketed per client, gated on Vercel + external metrics | yes |
| **Skew Protection** | Deployment ID threaded through framework-managed requests (`?dpl=`, header, or `__vdpl` cookie) so client and server never mismatch | yes |
| **Drains** | One data type per drain (`log`/`trace`/`analytics`/`speed_insights`/`audit_log`); custom endpoint or native integration (Dash0, Braintrust) or S3 (audit logs only) | yes |
| **Sensitive env vars** | Write-only once set; unreadable in dashboard or `vercel env ls`; build-log values ≥32 chars auto-`[REDACTED]` | yes |
| **Secure Compute** | Self-service dedicated VPC + static IPs for both deployments and the build container; AWS VPC peering | yes |
| **Region failover** | `functionFailoverRegions` reroutes on regional outage; Enterprise-only automatic function failover | maybe |
| Wildcard multi-tenant domains | Point apex at Vercel nameservers for DNS-01; every subdomain gets its own cert issued on the fly | yes |
| Per-tenant BYO domain | `projectsAddProjectDomain` → issue cert → `projectsVerifyProjectDomain`, with TXT proof if domain already lives elsewhere on Vercel | yes |
| **Vercel Sandbox credential brokering** | Injects credentials into egress HTTP headers at the proxy; sandbox code never holds the secret and can't override the injected header | yes |
| Runtime-updatable egress policy | Sandbox network policy (deny-all / allow-all / domain allowlist) can change on a *running* sandbox, no restart | yes |
| Turborepo Remote Cache | Hash-keyed task cache shared between every developer machine and CI via one API | yes |

## Worth stealing

### Instant Rollback — alias repoint, not rebuild

Every deployment is an immutable artifact; "production" is just which artifact the alias currently points to. Rollback is: *"Vercel points your domains back to the selected deployment"* — no new build. **Eligibility is the load-bearing rule**: *"Deployments previously aliased to a production domain are eligible for Instant Rollback. Deployments that have never been aliased to production... are not eligible"* — most preview deployments are excluded by construction, so rollback candidates are a bounded, curated set, not "any commit ever built."

After a rollback, **auto-assignment of the production domain turns off** — new pushes to the production branch no longer go live automatically, a deliberate circuit-breaker so CI doesn't silently steamroll an incident response. **`vercel promote` is the literal undo**: promoting any deployment both makes it live and re-enables auto-assignment.

Hobby plan: only the immediately previous deployment is eligible. Pro/Enterprise: any eligible deployment, chosen from a list.

### Rolling Releases — percentage canary with a metrics gate

Two or more configured stages, each a larger traffic fraction than the last, final stage always 100%. Routing is **cookie-bucketed per client** (hashed from IP + client-identifying info) so the same device gets a consistent deployment across requests, including in incognito. Vercel surfaces Speed Insights comparison between canary and base automatically; external metrics need the deployment ID propagated manually. Any stage can be aborted via Instant Rollback, which reverts to the base deployment.

**Vercel explicitly pairs this with Skew Protection**: *"Without Skew Protection, users may experience inconsistencies between client and server versions during rolling releases."* CI/CD should use dedicated `rolling-release start`/`complete` endpoints, not the general promote API — calling promote while a rolling release is active force-completes it to 100%, which is a foot-gun the docs call out directly.

### Skew Protection — pin the session, not just the tab

The framework auto-attaches the deployment ID (`?dpl=` param, `x-deployment-id` header, or `__vdpl` cookie) to framework-managed requests — static assets, client navigations, prefetches, Server Actions. **Full-page navigations are not pinned by default** — a hard refresh goes to latest and the client detects mismatch and reloads. For long-lived sessions (exams, video calls, checkout flows) the `__vdpl` cookie can be set manually in middleware to pin document navigations too.

Default max age is **one day**; configurable up to the project's deployment retention limit. A **Custom Skew Protection Threshold** lets you kill a buggy deployment and everything older than it, mid-flight, without deleting it. Cross-origin requests ignore the deployment ID by default (routed to latest) unless the serving project explicitly allowlists the origin domain — up to 12 entries, wildcards match one subdomain level only.

### Drains — one schema per drain, sampling implied by data type not volume control

Five data types, each its own REST schema (`log`/`v1`, `trace`/`v1` in OpenTelemetry format, `analytics`/`v2`, `speed_insights`/`v1`, `audit_log`/`v1`). Delivery is custom HTTP endpoint, a native integration (e.g. Dash0, Braintrust), or — audit logs only — direct-to-S3. Pricing is flat per data type ($0.50/unit of "Drains Volume" on Pro), not sampled per-drain in the docs (no explicit sampling knob was found — note this contradicts the brief's claim of "sampling per drain," flagged below).

### Sensitive environment variables — the concrete mechanism

Once created, a sensitive env var's value is **stored unreadable** — not just hidden in the UI, actually non-retrievable, including via `vercel env ls`. Restricted to Production and Preview (not Development). Build-log redaction is conditional: **values ≥32 characters are replaced with `[REDACTED]`** if they appear in build output; shorter secrets are not auto-redacted (a real gap worth noting for Houston's own secret-length guidance). `VERCEL_AUTOMATION_BYPASS_SECRET` and `VERCEL_OIDC_TOKEN` are always redacted regardless of length. Owners can set a team-wide policy forcing all new Production/Preview vars to be sensitive by default.

### Secure Compute — self-service private networking as an Enterprise SKU

Each network gets a dedicated IP pair, NAT gateway, and a chosen AWS region/CIDR/AZ. Deployments *and the build container* both run inside the network by default (the build container can be opted out to skip a **5-second provisioning delay**). VPC peering is bidirectional: Vercel proposes the peering connection, you accept it in AWS, then update route tables — standard AWS VPC peering, not a proprietary tunnel. Active/passive network pairs give automatic region failover per project-environment. Limits: 100 projects per network, 50 peering connections per network. Edge Runtime functions (Routing Middleware, edge-runtime functions) **do not get the dedicated IP** — only Node.js/Python/Ruby runtimes.

### Multi-tenant domains — nameserver delegation is the actual requirement

Wildcard certs can only be issued via ACME DNS-01, which requires Vercel to control DNS — hence *"point your domain to Vercel's nameservers (`ns1.vercel-dns.com`/`ns2.vercel-dns.com`)"* is not optional for wildcard subdomains, unlike ordinary custom domains which can stay on any DNS provider with an A/CNAME record. Once delegated, **every tenant subdomain gets its own certificate issued on the fly** — Vercel doesn't ship one wildcard cert to the edge, it mints per-hostname certs as tenants are created.

Per-tenant BYO custom domain (the "let a customer point their own domain at your SaaS" pattern) is three REST/SDK calls: `projectsAddProjectDomain` → Vercel issues a cert → `projectsVerifyProjectDomain`. If the domain string is already registered to a *different* Vercel project anywhere on the platform, verification falls back to a **TXT record challenge** as ownership proof before the domain can be reassigned.

### Vercel Sandbox — credential brokering at the network layer

Vercel's phrasing: *"Credentials brokering allows the injection of credentials on egressing traffic, while ensuring those secrets never enter the sandbox scope, preventing exfiltration."* Mechanism, per their changelog: a **per-sandbox ephemeral ECDSA CA certificate (24h TTL)** is injected into the sandbox's trust store, with environment variables set for common HTTP clients (`NODE_EXTRA_CA_CERTS`, `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`, `PIP_CERT`) so the proxy can MITM outbound TLS, strip/inject headers, and the injected header **overwrites anything the sandboxed code tried to set** — code cannot spoof or override the broker's credential.

Egress policy (deny-all / allow-all / domain allowlist) is **updatable on a running sandbox without a restart** — the same mechanism used for the credential injection rules. `sandbox config network-policy` is the CLI surface. Multi-agent isolation gives each agent its own Linux user with a private home directory inside the same sandbox VM, sharing files via Unix groups rather than a shared root filesystem. Persistent sandboxes auto-save state on stop and resume by default — no manual snapshot step, distinct from the separate explicit "Snapshots" concept.

### RBAC — Security is a first-class team role

Nine team-level roles including a dedicated **Security** role (*"Manage Firewall, Rate Limiting, Deployment Protection... does not offer deployment permissions by default"*, read-only elsewhere) — a real separation of security administration from deploy authority, not just "admin minus billing." **Contributor** is the only role eligible for project-scoped role assignment; Owner/Member/Developer are inherently team-wide. Permission Groups let you attach fine slices (Create Project, Full Production Deployment, Environment Variable Manager, etc.) onto compatible base roles.

### Audit Logs framed around agents, not just humans

Vercel's Enterprise marketing page states audit logs make inspectable *"every action, every tool call, who initiated it, and what it returned."* Their "Agent Stack" post frames it as tracing "from user to agent to service," so an agent's tool calls are tied back to the human it acted on behalf of. The actual audit log schema (CSV export, or SIEM/Drain streaming to S3/Splunk/Datadog/GCS/custom HTTP) is a flat `actor / action / previous / next` event log — the agent-specific framing is marketing positioning layered on the same event log used for human actions, not a separately documented agent-log schema.

### Turborepo Remote Caching — cache is a REST API, not a CDN trick

Free on every plan (fair-use capped: 100GB/mo Hobby, 1TB/mo Pro, 4TB/mo Enterprise; 10,000 req/min on Pro+). Enabled automatically inside Vercel builds; from external CI it's two env vars (`TURBO_TOKEN`, `TURBO_TEAM`). Artifacts expire after 7 days automatically. **No sampled/estimated CI-reduction percentage appears in current docs** — the "~85% CI reduction" figure in the brief could not be verified on official pages and should be treated as vendor-reported/unsourced until a primary citation is found.

## Worth avoiding

- **Skew Protection doesn't cover custom `fetch()` calls automatically** — only framework-managed requests are pinned; developers must manually thread the deployment ID into any hand-rolled client fetch, which is an easy silent gap.
- **Cross-site skew protection requires an explicit allowlist per serving project** (max 12 domains) — a platform serving many tenant subdomains that all fetch shared assets cross-origin has to manage this list by hand.
- **Sensitive env var redaction has a length floor (32 chars)** — shorter secrets (e.g. short API keys, PINs) leak into build logs unredacted by default.

## Facts & figures

- 20 compute-capable regions; 126 CDN PoPs (docs, July 2026).
- Skew Protection default max age: 1 day; auto-extended to 60 days for Googlebot/Bingbot crawls.
- Sensitive env var build-log redaction threshold: **≥32 characters**.
- Secure Compute: up to 100 projects per network, 50 VPC peering connections per network, 5s build-container provisioning delay.
- SAML SSO session: 24 hours before re-authentication (vendor docs, via search; not independently re-fetched from primary page in this pass).
- Turborepo Remote Cache fair-use: 100GB/mo (Hobby) · 1TB/mo (Pro) · 4TB/mo (Enterprise); artifacts expire after 7 days.
- Drains pricing: $0.50 per unit of Drains Volume (Pro); Audit Log Drains are Enterprise-only.
- Rolling Releases: available Pro (1 project) and Enterprise (custom limits).

## Sources

- [Instant Rollback](https://vercel.com/docs/instant-rollback) · [Rolling Releases](https://vercel.com/docs/rolling-releases) · [Skew Protection](https://vercel.com/docs/skew-protection)
- [Drains overview](https://vercel.com/docs/drains)
- [Environment variables](https://vercel.com/docs/environment-variables) · [Sensitive environment variables](https://vercel.com/docs/environment-variables/sensitive-environment-variables)
- [Secure Compute](https://vercel.com/docs/networking/secure-compute)
- [Regions](https://vercel.com/docs/regions)
- [Vercel for Platforms](https://vercel.com/docs/platforms) · [Wildcard Domains blog](https://vercel.com/blog/wildcard-domains) · [Add a domain to a project](https://vercel.com/docs/rest-api/projects/add-a-domain-to-a-project) · [Verify project domain](https://vercel.com/docs/rest-api/reference/endpoints/projects/verify-project-domain)
- [Vercel Sandbox](https://vercel.com/docs/sandbox) · [Sandbox firewall](https://vercel.com/docs/sandbox/concepts/firewall) · [Advanced egress firewall filtering changelog](https://vercel.com/changelog/advanced-egress-firewall-filtering-for-vercel-sandbox) · [Credential injection in HTTP headers changelog](https://vercel.com/changelog/safely-inject-credentials-in-http-headers-with-vercel-sandbox)
- [Access Roles](https://vercel.com/docs/rbac/access-roles) · [Audit Logs](https://vercel.com/docs/audit-log) · [Vercel Enterprise](https://vercel.com/enterprise) · [The Agent Stack blog](https://vercel.com/blog/agent-stack)
- [Remote Caching](https://vercel.com/docs/monorepos/remote-caching)
- **Not directly verified:** the "~85% CI reduction" Turborepo figure (not found on current docs pages — treat as unverified until sourced); "sampling per drain" (docs show one schema per drain and flat per-unit pricing, no explicit sampling control found); SAML 24h session was confirmed via search snippet, not a direct fetch of `/docs/saml` in this pass.
