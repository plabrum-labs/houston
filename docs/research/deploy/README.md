# Deploy

**What this category is:** how code gets built, versioned, released, rolled back, and run — deploy-DX platforms (Vercel, Heroku, Railway/Render/Northflank), infra runtimes (Fly.io, Cloudflare), serverless/agent-sandbox compute (Modal), and the database layer that has to keep up with all of it (Neon, PlanetScale).
**Why it's in this research:** deploy DX is one leg of Houston's Palantir × Vercel × Fly.io positioning — this folder is the landscape survey of what "good" looks like across artifact immutability, preview environments, multi-tenant runtime isolation, and the honest limits of cold-start/scaling claims.
**Files:** 8 (railway.md covers three products: Railway, Render, Northflank).

## The players

| Company | What it is | Depth |
|---|---|---|
| [vercel](vercel.md) | The deploy-DX reference — immutable deployments, rollback, skew protection, platform-for-platforms surface | deep |
| [fly](fly.md) | Low-level Machines API + proxy layer; the most honest first-party numbers in the market | deep |
| [cloudflare](cloudflare.md) | The multi-tenant-runtime reference — Workers for Platforms, dispatch namespaces, credential-brokering patterns | deep |
| [heroku](heroku.md) | The original PaaS deploy-DX vocabulary; Release Phase remains uncleanly replicated elsewhere | medium |
| [modal](modal.md) | Python-first serverless/sandbox compute; checkpoint/restore (memory + filesystem snapshots) as its distinguishing mechanism | medium |
| [neon](neon.md) | Serverless Postgres; copy-on-write branching as the defining mechanism; acquired by Databricks (~$1B, May 2025) | medium |
| [planetscale](planetscale.md) | Managed MySQL/Vitess; Deploy Requests (PR-for-schema) and non-blocking cutover | medium |
| [railway](railway.md) | Railway + Render preview-environment variants; Northflank as the BYOC reference | thin (per-product, three products) |

Vercel, Fly, and Cloudflare are the three deep reference implementations, each covering a different layer: Vercel for deploy-DX/artifact semantics, Fly for the raw compute-primitive API, Cloudflare for multi-tenant untrusted-code isolation at platform scale. Heroku is the historical reference whose vocabulary (pipelines, slugs, review apps) the others largely re-implemented with more polish — except Release Phase, which nobody has cleanly replicated. Modal is the narrower, workload-specific player (Python compute, agent sandboxes). Neon and PlanetScale are the database layer, with directly opposed branching philosophies. Railway/Render/Northflank are shorter entries covering preview-environment variants and the BYOC vocabulary.

## Convergence

**Immutable artifact + alias flip is the universal pattern for rollback and traffic control.** Vercel's Deployments (immutable build, separate alias layer deciding what serves traffic, Instant Rollback as a repoint with no rebuild) and Cloudflare's Versions & Deployments (immutable version, separate deployment mapping 1–2 versions to a traffic split) are architecturally identical: build once, control what's live by repointing a pointer, never by rebuilding. Fly's Machines API embodies the same idea one layer down — a Machine is a directly addressable unit, and higher-level tooling (`fly deploy`, autoscaling) is a client of the same API, not privileged internal machinery. The one universal caveat, stated explicitly by both Vercel and Cloudflare: **storage/database state is not versioned with code.** A code rollback does not roll back KV/D1/DO state (Cloudflare) or database schema/data (implicitly, everywhere) — this is a documented gap every vendor in the tier has, not a solved problem anywhere.

**The preview-environment story has converged on "clone the whole environment by default," and its database problem has converged on two opposite, deliberate answers.** Heroku's Review Apps (2016) is the ancestor; Railway (full clone with opt-in path-scoping via watch paths) and Render (`render.yaml`-declared full clone, no production data copied) both do git-driven, full-environment-by-default previews with a cost-control escape hatch layered on top, not the reverse. The database question underneath every preview environment splits two ways, both deliberate: **Neon's copy-on-write branching** gives full schema+data in under a second regardless of size (a storage-engine property, not a general pattern — it requires Neon's separated storage/compute architecture), wired directly into Vercel's preview pipeline via webhook. **PlanetScale's branches are schema-only** — no data unless explicitly restored from backup — because PlanetScale's bet is that schema *review* (via Deploy Requests, a PR-for-schema model with visual diff and approval) is the valuable reviewable unit, not a full data fork. Neither vendor is wrong; "branch" means two structurally different things across the two products, and any platform borrowing the word needs to pick one meaning explicitly.

**BYOC vs. self-hosted is a real, load-bearing vocabulary distinction, not marketing hair-splitting.** Northflank's framing (`railway.md`): BYOC means the vendor still operates the control plane (cluster lifecycle, pipelines, upgrades, UI/CLI/API) while only the runtime/data plane lives in the customer's cloud account; self-hosted means the customer runs the control plane too. Enterprises asking for "self-hosted" are very often actually describing BYOC — they want data residency, network control, and billing consolidation, not the operational burden of running the platform itself. Vercel's Secure Compute (dedicated VPC peering into customer AWS) and Cloudflare's whole product model sit adjacent to this same distinction without using the term.

**Credential-brokering at the network layer is the same shape, independently arrived at, in every sandboxed-compute product.** Vercel Sandbox (per-sandbox ephemeral CA cert injected into the trust store, proxy MITMs outbound TLS, injected header overwrites anything the sandboxed code tried to set) and Cloudflare's Outbound Workers (a Worker outside the sandbox holds the real secret, attaches it before the request leaves, "no token is ever passed into the sandbox") and Cloudflare's `workers-oauth-provider` (an encrypted access token stored server-side, the client only ever gets a scoped token the server issued) are all the identical mechanism: **the credential lives in the platform's layer, never in the untrusted code, and cannot be spoofed or overridden by that code.** Modal's egress allowlists (domain + CIDR, TLS/443-scoped) and Fly's Network Policies (port/protocol only, explicitly *not* covering proxy-routed traffic) are the same problem solved less completely — worth noting as the honest gap in the pattern, not a fourth convergence point.

**Honest cold-start numbers are rare enough to be notable when found.** Fly (~2s cold start, few-hundred-ms suspend/resume) and Cloudflare (1–3s container cold start, documented in two separate places) are called out across both files as two of the only vendors in this market publishing real first-party cold-start figures rather than unverifiable marketing numbers. Modal's "sub-second" claim is directly contradicted by its own GPU cold-start disclosures (2–10+s range) — flagged explicitly as the standing house rule for this market: treat cold-start marketing numbers as mostly unverifiable unless first-party and specific.

## Worth stealing

- **Instant Rollback's eligibility rule** — only deployments *previously aliased to production* are rollback-eligible, bounding the candidate set to a curated list rather than "any commit ever built"; rollback also disables auto-assignment as a deliberate circuit-breaker (`vercel.md`).
- **Skew Protection** — pin a client session to the exact deployment (frontend + backend) it loaded via deployment-ID threading, so rolling releases don't produce client/server version mismatches (`vercel.md`).
- **Release Phase as a hard gate, re-run on promotion even with no new build** — a broken migration cannot reach production traffic; slug promotion stays safe because release-time side effects still execute against the target environment's real state (`heroku.md`).
- **The autostop/autostart formula and its explicit documented boundary** — Fly's mechanism never creates/destroys Machines, only toggles state on a pool sized by `fly scale count`; the boundary is stated, not discovered the hard way (`fly.md`).
- **`fly-replay`** — proxy-level request forwarding to a different region/Machine/app with no client redirect round-trip; a clean multi-tenant routing primitive built entirely from proxy behavior (`fly.md`).
- **Dispatch namespace + untrusted mode** — a single container for every customer Worker, isolated by construction (no shared cache, no `request.cf`), explicitly marketed at "anyone building an AI vibe coding platform" (`cloudflare.md`).
- **Deploy Requests as a PR model for schema, with non-blocking Vitess cutover and a genuine lossless post-deploy revert** (30-minute window, VReplication run in reverse rather than a backup restore) (`planetscale.md`).
- **Focused PR Environments' watch-path scoping** — full-fidelity clone as the safe default, path-based scoping as the deliberate cost-reduction opt-in (`railway.md`).
- **Filesystem snapshots as the workaround for a hard session ceiling** — Modal doesn't extend the 24h Sandbox lifetime, it snapshots and restores into a fresh session, achieving continuity without an indefinitely-alive process (`modal.md`).

## Worth avoiding

- **Storage state not versioned with code** — a documented gap in both Vercel and Cloudflare's immutable-artifact models; a rollback can leave code talking to a data shape the older code doesn't expect.
- **Skew Protection doesn't cover custom `fetch()` calls automatically**, and cross-site skew protection requires a manual, capped allowlist — real silent gaps in an otherwise strong mechanism (`vercel.md`).
- **Sensitive env var redaction has a length floor (≥32 chars)** — shorter secrets leak into build logs unredacted by default (`vercel.md`).
- **Release Phase's hard 1-hour timeout, non-configurable** — a genuinely long-running migration cannot use it as specified (`heroku.md`).
- **Fly's Network Policies don't cover proxy-routed traffic** — the policy has a hole exactly where most traffic actually flows; it's a coarse firewall for direct Machine sockets, not an exfiltration control (`fly.md`).
- **Fly's autostop loop falls behind at thousands of Machines per app** — pushing Fly's own guidance toward one-app-per-tenant architectures rather than one giant multi-tenant app (`fly.md`).
- **Modal's "sub-second" cold start is a CPU-warm-only best case**, contradicted by its own GPU cold-start numbers — treat as marketing outside the narrow case (`modal.md`).
- **PlanetScale's schema-only branches mean realistic data-shaped testing requires an explicit, non-automatic backup-restore step** — easy to skip, unlike Neon's default (`planetscale.md`).

## Gaps

- **Nobody has solved "storage state travels with code state" for rollback** — every vendor with an immutable-artifact model treats this as an explicit, named, unsolved caveat rather than a solved problem.
- **No sandbox-compute vendor's domain-aware egress control covers non-TLS or arbitrary-port traffic** — Modal's domain allowlist is TLS/443-only; Fly's policy is port/protocol-only and doesn't cover proxy traffic at all. A genuinely complete egress control (all ports, all protocols, domain-aware) doesn't exist in this set.
- **Cold-start honesty is the exception, not the rule** — most vendors in the adjacent sandbox/serverless market publish unverifiable marketing numbers; only Fly and Cloudflare give real first-party figures.

## Notes

- Cloudflare's brief-stated "April 2026" date for synchronous first-upload provisioning appears to actually be February 2025 per the changelog URL — flagged as a discrepancy in the source file rather than silently corrected.
- Neon's "30% → 80%+ of databases created by AI agents" figure is vendor-reported but multiply-corroborated across Databricks' own materials and independent trade press; the exact percentages come from search-summarized coverage, not a direct re-fetch of the original blog post.
- Turborepo Remote Caching's commonly-cited "~85% CI reduction" figure could not be found on current Vercel docs and should be treated as unsourced until a primary citation surfaces.
- Porter's feature-set characterization in `railway.md` comes from a competitor's (Northflank's) comparison blog, not Porter's own docs — worth a direct check before quoting externally.
