# Directus

**What it is:** A headless CMS/data layer that wraps an existing SQL database with an auto-generated API, a field-metadata system separate from the DB schema, and a visual automation builder (Flows).
**Axis:** semantic layer, app-builder (override points), enterprise governance.
**Depth:** medium — official docs and DeepWiki cross-reference; no independent load-testing.

## Products & surfaces

| Product | What it is |
|---|---|
| **Data Studio** | Auto-generated admin UI over the connected database. |
| **`directus_fields`** | System table holding field-level metadata (interface, display, validation, conditions, etc.), separate from the DB column. |
| **Permissions** | Role-based, filter-expression access control, using the same filter grammar as everything else. |
| **Flows** | Visual automation builder: trigger → operations, with blocking and non-blocking trigger types. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| `interface` / `display` split | Which component edits a field vs. which component renders it read-only, as separate metadata | yes |
| `conditions` | Field visibility/editability driven by *other field values*, declared as data | yes |
| `validation` as a filter rule | The same filter AST used for queries also validates writes | yes |
| One filter AST, four uses | Query filters, permission rules, conditional field visibility, and validation all share one grammar | yes |
| Filter (blocking) vs Action (non-blocking) triggers | "Reject this write" and "react to this write" are different trigger types, not one hook with a return value | yes |
| Interface `types`/`localTypes` declaration | An interface declares what it applies to; the registry that matches interfaces to fields is data, not a switch statement | yes |
| Flat `directus_fields` schema | `conditions`, `validation`, `note`, etc. are all first-class columns on one system table | no (cautionary) |

## Worth stealing

### The `interface`/`display` split — editing and reading are different concerns

Field metadata lives in `directus_fields`, entirely separate from the underlying database column. Two independent slots: **`interface`** + `options` — which component is used to *edit* the field's value, and **`display`** + `display_options` — which component is used to *render* it read-only (in a list view, a related-item preview, etc.). A date column might use a calendar-picker interface but a relative-time ("3 days ago") display. Alongside these: `readonly`, `hidden`, `required`, `sort`, **`width`** (`half`/`full`/`fill` — a grid-sizing hint for the auto-generated form layout), `note` (inline help text), `conditions`, and `validation`.

The generalizable idea: **the read-shape of a field and the write-shape of a field are different UI problems**, and giving them separate, independently swappable metadata slots means changing how something displays never risks changing how it's edited, and vice versa.

### Matching is declarative — the override registry is data

An interface declares what it's compatible with via `types` (e.g., `['string']`) and `localTypes` (e.g., `standard`/`m2o`/`m2m`/`file`) — a data-described compatibility contract, not a hardcoded `switch (fieldType)` dispatch buried in application code. Adding a new interface means declaring what it matches, not editing a central dispatcher. This is the same shape as PostGraphile's `@behavior` tokens (`postgraphile.md`) and Hasura's role-based generated types (`hasura.md`): **capability/compatibility expressed as declarative metadata the platform reads, rather than as branches in platform code.**

### `conditions` — visibility/editability driven by other fields, as data

A field's `hidden`/`readonly`/`required` state, and even its `options`, can be overridden by a `conditions` array evaluated against the *current values of other fields on the same item* — e.g., "show this field only if `status = 'published'`," or "make this field required only if `type = 'physical'`." This is declared entirely in field metadata, no custom form code, and it composes with the base field settings (the base is the default; a matching condition overrides it).

### One filter AST, reused for four different purposes

The **same filter-expression grammar** (`_and`/`_or`, comparison/logic operators, nested rule groups) is used for: (1) ordinary query filtering (`?filter[status][_eq]=published`), (2) **permission rules** (which rows a role may see/edit — the row-level access-control layer), (3) **`conditions`** (which fields are visible/editable based on sibling field values), and (4) **`validation`** (a filter rule evaluated against the *submitted payload* to accept or reject a write). Learning the filter language once buys correctness across querying, access control, conditional UI, and input validation — four surfaces most systems would give four separate mini-languages.

### Filter-triggers vs action-triggers as distinct primitives

Flows distinguish **Filter (Blocking)** triggers — which pause the transaction, receive the payload, and can validate/transform it or **cancel the transaction outright** (via a reject path or a Throw Error operation) — from **Action (Non-Blocking)** triggers, which fire after the fact purely to react (send a notification, call a webhook) without being able to affect the write at all. Making these two distinct trigger *types*, rather than one hook whose behavior depends on a return value, means a flow author can tell from the trigger type alone whether their flow is capable of rejecting a write. "Reject this write" and "react to this write" are architecturally different problems (one runs inside the transaction and can fail it; one runs after commit and cannot), and Directus keeps them as separate primitives instead of one with implicit modes.

## Worth avoiding

### Flat columns on `directus_fields` don't scale as metadata grows

Because `conditions`, `validation`, `note`, `width`, and every other piece of field-editing metadata are **first-class columns on the single flat `directus_fields` table**, every new kind of field-level metadata Directus wants to add requires a schema migration to that system table, and every consumer of field metadata sees the full flat row regardless of whether it cares about `conditions` or not. **Contrast Strapi's `pluginOptions`**, a namespaced JSON extension map keyed by consumer plugin (`pluginOptions.i18n.localized`, `pluginOptions["content-manager"]...`) — a feature (i18n, content-manager) can attach its own metadata to a field *without* Directus-style core-schema changes, because the extension point is a namespace, not a column. The trade-off: Directus's flat columns are easier to query/index and self-documenting from the table definition; Strapi's namespaced map scales to more consumers without core migrations but pushes structure-checking onto each consumer.

## Facts & figures

- `width` values: `half` (max 380px), `full` (760px, sum of two halves), `fill` (no max, fills available space) — per official docs.
- Filter Rules are explicitly documented as shared across permissions, validations, automations, the API, and extensions (per official docs).

## Sources

- [Fields](https://directus.io/docs/guides/data-model/fields) · [Interfaces](https://directus.com/docs/guides/data-model/interfaces)
- [Filter Rules](https://directus.com/docs/guides/connect/filter-rules) · [Permissions](https://directus.io/docs/api/permissions) · [Access Control](https://directus.com/docs/guides/auth/access-control)
- [Permissions and Access Control (DeepWiki)](https://deepwiki.com/directus/directus/3.6-permissions-and-access-control) — third-party secondary source, cross-check against official docs where load-bearing
- [Triggers](https://directus.io/docs/guides/automate/triggers) · [Flows](https://directus.io/docs/guides/automate/flows) · [Operations](https://directus.io/docs/guides/automate/operations)
- **Not directly verified:** internal `processAst()`/`validateAccess()`/`processPayload()` function names and exact responsibilities (sourced from DeepWiki, a third-party code-summary tool, not from Directus's own architecture docs).
