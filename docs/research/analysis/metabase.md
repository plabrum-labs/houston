# Metabase

**What it is:** Open-source BI — point-and-click query builder plus SQL, dashboards, alerting, and multiple embedding tiers.
**Axis:** app-builder, enterprise.
**Depth:** thin (brief per research scope).

## Products & surfaces

| Surface | What it is |
|---|---|
| **Metabase** | Open-source BI: question builder (no-code query), native SQL editor, dashboards, alerts/subscriptions. |
| **Data Studio** | Analyst workbench for structuring data and building a semantic layer on top of raw tables. |
| **Embedding** | Modular (individual chart/dashboard components via JS snippet or React SDK) or full-app (entire product in an iframe) embedding. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Question builder | Point-and-click query construction (tables, filters, aggregations, viz type) with no SQL required | no (table stakes) |
| Modular vs. full-app embedding | Two distinct embed tiers — individual components (JS/React SDK) vs. the entire app in an iframe, aimed at different integration depths | maybe |
| Table/row/column-level permissions | Granular access control down to specific columns/rows | maybe |

## Worth stealing

Metabase's two-tier embedding split — component-level (JS snippet or React SDK, embed a single chart/dashboard) versus full-app (the whole product in an iframe, for multi-tenant self-service) — is a reasonable default menu for "how much of the BI surface do you expose to an external user," and maps cleanly onto a build-vs-buy decision for any platform deciding how much embedded-analytics surface to own natively versus point at an iframe.

## Worth avoiding

Full-app iframe embedding is the same pattern criticized elsewhere in this research set (see `sigma.md`): an iframed BI product reads as a foreign element in a host product, with visible boundaries and no way to inherit the host's design system at the component level. The React SDK / component tier exists specifically to route around that limitation — the lesson generalizes: **iframe embedding is a fallback, not a target,** whenever a component-level SDK is available.

## Note: the embedded-analytics tier as a category

Purpose-built embedded-analytics vendors — **Cube, Luzmo, Explo, Qrvey, Toucan** — treat multi-tenancy as **architectural**, not a configuration flag layered on afterward (contrast Sigma's later, separately-launched "Sigma Tenants," above). The pattern across this tier: tenant isolation enforced server-side from a signed token (Toucan resolves a JWT encoding user identity + tenant ID + filters, and enforces isolation at query time so "no tenant can ever query another tenant's rows, regardless of UI manipulation" — no custom engineering required on the embedding team's side); Qrvey isolates at the infrastructure level rather than the application layer. These vendors also ship **component SDKs** (React/JS components) as the primary integration surface rather than iframes, for the same reason the Metabase React SDK exists — inheriting the host application's design system instead of rendering a foreign, boundary-visible block. The general lesson for anything embedding analytics into a multi-tenant product: **decide tenant isolation and embedding surface (component vs. iframe) as day-one architecture, not as a retrofit** — Sigma's own "Sigma Tenants" launch is a visible example of what the retrofit looks like.

## Facts & figures

- Open source: `metabase/metabase` on GitHub.
- Connects to 20+ data sources (vendor-reported).

## Sources

- [Metabase GitHub](https://github.com/metabase/metabase) · [Metabase dashboards & reporting](https://www.metabase.com/features/analytics-dashboards) · [What is Metabase and how does it work?](https://embeddable.com/blog/what-is-metabase)
