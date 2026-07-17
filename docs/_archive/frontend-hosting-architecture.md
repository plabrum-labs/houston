# Frontend hosting architecture

Covers how the infra service hosts frontends for vertical apps, alongside the AWS backend covered in `many-backends-architecture.md`.

## Frontend framework support

- **SPA** — Vite + client framework (React/Vue/etc.), talks to a separate backend API.
- **Landing page / blog** — Astro in static mode (SSG by default, content collections for typed markdown/MDX, islands for occasional interactive widgets).
- The infra service's generic primitive is "static build output + optional SPA-fallback flag," not framework-specific branching — keeps it open to other static-output frameworks later without special-casing each one.

## Domain / service split

The common shape for a vertical app deploying all three pieces at once:

- `domain.com` — landing page (Astro static)
- `app.domain.com` — SPA (Vite)
- `api.domain.com` — backend (AWS, via Pulumi)

## Hosting split

- Landing + SPA → **Cloudflare Pages** (free unlimited egress, built-in SPA-fallback rewrite support).
- Backend/API → **AWS**, defined in Pulumi.
- Managed as one deployable unit via Pulumi's Cloudflare provider alongside the AWS provider — one `pulumi up` for the whole stack.

## DNS / TLS

- DNS lives entirely on **Cloudflare** (required for Pages custom domains) — no Route53.
- `api.domain.com` is a plain DNS-only (not proxied) record pointing at AWS, avoiding the extra hop/latency of routing through Cloudflare's edge.
- ACM certs are free on the AWS side (API Gateway custom domain).
- If WAF/DDoS protection on the API is needed later, add AWS WAF/Shield rather than switching the DNS record to proxied.
