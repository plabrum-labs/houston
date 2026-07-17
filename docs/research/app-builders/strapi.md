# Strapi

**What it is:** A headless CMS with its own content database, a customizable REST/GraphQL API, and a layered backend-customization system (policies, middlewares, lifecycle hooks) built around a "Document Service" abstraction over the raw database.
**Axis:** semantic layer, app-builder (override points).
**Depth:** medium — official v5 docs, with a noted v4 regression found in GitHub issues.

## Products & surfaces

| Product | What it is |
|---|---|
| **Content-Type Builder** | Schema editor for content types (fields, relations, components). |
| **Document Service** | The layer Strapi routes reads/writes through; sits above the raw Query Engine/database. |
| **Policies** | Read-only, boolean-return route guards — can only accept or reject a request. |
| **Middlewares** (route-level and Document-Service-level) | Can inspect *and mutate* the request/response as it flows through. |
| **Lifecycle hooks** | Older, DB-level (Query Engine) event hooks — still available but no longer the recommended extension point. |
| **i18n / plugins** | First-party plugins that attach their own metadata to fields via `pluginOptions`. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Policies vs. middlewares | Policies are read-only (accept/reject only); middlewares can mutate the request/response | yes |
| Document Service over raw DB | Hooks/middleware attach to the document-service layer, not directly to SQL rows | yes |
| `pluginOptions` namespaced metadata | Plugins attach field-level metadata under their own key, without core schema changes | yes |
| `event.state` threading (v4) | Intended to pass state between before/after lifecycle hooks | no (cautionary — documented but reportedly broken in v4) |

## Worth stealing

### Policies can only reject; middlewares can mutate — different strength guarantees

Strapi draws a hard line between two extension points on the same request path: a **policy** receives request context, evaluates a condition, and can only return `true` (allow) or `false`/throw (block with 403) — it is **read-only and cannot alter the request**. A **middleware** sits at the same point in the pipeline but *can* mutate the request or response as it passes through. The design argument worth generalizing: **an auth/authorization check that is structurally incapable of mutating the request is a strictly stronger security primitive than a general-purpose hook that happens not to mutate anything today.** A reviewer auditing "can this policy have side effects that create an inconsistent state" doesn't need to read the policy's body to know the answer is no — it's enforced by the extension point's type, not by convention. Middlewares get the power to transform; policies get the guarantee of no side effects. Splitting these into separate primitives, rather than one hook type with a discipline convention ("policies shouldn't mutate, but technically could"), is the reusable idea.

### Document Service as the seam, not the raw database

Strapi's own v4→v5 migration docs steer developers **away from database-level lifecycle hooks and toward Document Service middlewares** specifically because hooks registered at the Query Engine/DB level fire on raw SQL operations, and Strapi's own v5 breaking-changes notes confirm **"Database lifecycle hooks are triggered differently with the Document Service API methods"** — meaning code that assumes DB-level hooks see every write can silently miss writes that go through the Document Service by a different path. Their guidance: extend at the layer the platform's own abstraction is built on (documents), not at the layer beneath it (SQL rows), or the extension point and the platform's real write path can drift apart. This generalizes past Strapi: whenever a platform introduces a higher-level abstraction over raw storage, hooking the raw layer risks silently missing operations that only exist at the higher layer.

### `pluginOptions` — namespaced metadata as an extension point that doesn't touch core schema

Content-type field definitions carry a `pluginOptions` object keyed by consumer, e.g. `pluginOptions: { i18n: { localized: true } }` or `pluginOptions: { "content-manager": {...} }`. Any plugin (first- or third-party) can read/write its own namespace under `pluginOptions` without requiring a change to Strapi's core field-schema shape. Contrast this directly with Directus (`directus.md`), where every piece of field-level metadata (`conditions`, `validation`, `note`, `width`...) is a **flat column on the single `directus_fields` table**, meaning a new kind of metadata requires a core-schema migration. Strapi's namespaced-map approach trades some ergonomics (no first-class column to index/query against) for **extensibility without touching the core schema** — a plugin author never needs the CMS maintainers to ship a schema change to attach new metadata.

## Worth avoiding

### Documented state-threading between hooks was reportedly non-functional (v4)

Strapi v4's lifecycle-hook docs described an `event.state` object intended to let a `beforeCreate` hook stash data for the corresponding `afterCreate` hook to read (e.g., capture a value before mutation to compare after). A filed GitHub issue (`strapi/strapi#12271`) reports this **did not work in practice** — `event.state` set in a `before` hook was `undefined` when read in the matching `after` hook, contradicting the documented behavior. Whether or not it was ever fixed in v4, it's a useful cautionary data point: **a documented state-passing contract between paired before/after hooks is exactly the kind of feature that's easy to under-test**, since it only manifests as broken when a consumer actually writes matching before/after logic that depends on it — a class of bug that unit tests scoped to a single hook invocation won't catch.

## Facts & figures

- Strapi v5 explicitly recommends Document Service middlewares over Query Engine lifecycle hooks for most use cases (official migration docs).
- `event.state` non-propagation bug reported against Strapi v4.0.5 (GitHub issue, not independently confirmed as fixed/unfixed in latest v4 or as ported forward to v5's hook model).

## Sources

- [Back-end customization (Strapi 5)](https://docs.strapi.io/cms/backend-customization) · [Custom policies](https://docs.strapi.io/cms/backend-customization/examples/policies) · [Middlewares](https://docs.strapi.io/cms/backend-customization/middlewares)
- [Document Service Middleware vs. Lifecycle Hooks (blog)](https://strapi.io/blog/what-are-document-service-middleware-and-what-happened-to-lifecycle-hooks-1) · [Extending the Document Service behavior](https://docs.strapi.io/cms/api/document-service/middlewares)
- [Database lifecycle hooks are triggered differently with the Document Service API methods (v4→v5 breaking changes)](https://docs.strapi.io/cms/migration/v4-to-v5/breaking-changes/lifecycle-hooks-document-service)
- [Internationalization (i18n) — pluginOptions usage](https://docs-v4.strapi.io/dev-docs/plugins/i18n) · [Internationalization (Strapi 5)](https://docs.strapi.io/cms/features/internationalization)
- [`event.state` does not get passed from beforeXxx to afterXxx (GitHub issue #12271)](https://github.com/strapi/strapi/issues/12271)
- **Not directly verified:** whether the `event.state` bug was ever fixed in later v4 patch releases; exact current (v5) status of `event.state`-equivalent behavior in Document Service middlewares.
