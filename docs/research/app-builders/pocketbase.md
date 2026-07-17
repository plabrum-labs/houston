# PocketBase

**What it is:** A single-binary, self-hosted BaaS — SQLite-backed, with a REST API, an admin UI, an embedded ES5 JS runtime for hooks/custom routes, and a declarative per-collection API-rules language.
**Axis:** semantic layer, enterprise governance, deploy/migration.
**Depth:** medium — official docs and DeepWiki cross-reference; no production-scale usage confirmed.

## Products & surfaces

| Product | What it is |
|---|---|
| **PocketBase core** | Single Go binary: HTTP server, SQLite database, admin dashboard, auth. |
| **API rules** | Per-collection, per-action (list/view/create/update/delete) filter expressions gating access. |
| **JSVM (Extend with JavaScript)** | Embedded goja (ES5 + partial ES6) engine for `pb_hooks/*.pb.js` — lifecycle hooks and custom routes. |
| **Use as framework** | PocketBase can be imported as a Go library and extended natively, not just via JS hooks. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Three-state API rule default | `null` = superuser-only (locked), `""` = public, non-empty = filter expression | yes |
| `:changed` modifier | Expresses "may update own row but not this specific field" in one clause | yes |
| `:isset`, `:length`, `:each`, `:lower` modifiers | Compose request-shape and value checks directly into the filter expression | yes |
| Named lifecycle hooks + custom routes | The override/extension point, not a full code-ejection | yes |
| Single binary, embedded ES5 (goja) | Zero-dependency deploy; JS layer has no Node/browser APIs (`fetch`, `fs`, etc.) | maybe |

## Worth stealing

### The three-state default is a genuinely good primitive

Every API rule (`listRule`, `viewRule`, `createRule`, `updateRule`, `deleteRule`) on every collection has exactly three possible states, and the **default state is the safe one**:
- **`null`** (unset) — locked; only an authenticated superuser can perform the action. This is what a new collection ships with.
- **`""`** (empty string) — fully public; superusers, authenticated users, and guests can all perform the action.
- **non-empty string** — a filter expression; only requests matching the expression succeed.

This is notable specifically because it's a **fail-closed default expressed as a distinct value from "public,"** not as absence-of-a-rule-meaning-public (the Supabase/PostgREST failure mode — see `supabase.md`) or absence-meaning-locked-with-no-way-to-signal-intentional-public (many RBAC systems). `null` vs `""` lets the schema itself record whether "nobody but a superuser" or "literally everyone" was a deliberate choice.

### `:changed` — column-level immutability as a filter-language primitive

The `:changed` modifier (usable on `@request.body.*` fields) checks whether the client submitted **and actually changed** a given field. This lets one rule expression say, in a single clause, *"users may update their own profile, but not reassign their own `role`"* — e.g. an `updateRule` like `@request.auth.id = id && @request.body.role:changed = false`. Column-level write-immutability is usually bolted on as a trigger or a separate check in most systems in this survey; PocketBase gives it to you as a first-class filter operator, composable with the rest of the rule.

Other modifiers compose the same way: **`:isset`** (did the client submit this field at all — distinct from "changed," since a client can resubmit the same value), **`:length`** (size check on arrayable fields — select/file/relation), **`:each`** (per-element check across an arrayable field), **`:lower`** (case-insensitive comparison). All of these are just modifiers on the same filter-expression grammar used for `list` filtering, so learning the query language once buys you the permission language too.

### Named lifecycle hooks + custom routes as the override point

PocketBase exposes 60+ named lifecycle hooks (record create/update/delete, request handling, etc.) with an explicit `e.Next()` middleware-style chain, plus `routerAdd()` for defining entirely custom API routes — both from `pb_hooks/*.pb.js` with no rebuild step, or natively if PocketBase is imported as a Go framework. The design choice worth noting: the escape hatch is **structured extension points inside the running server**, not "eject into a separate custom backend." A team outgrowing the declarative rules language still writes hooks against the same request/record lifecycle, not a parallel bespoke API.

## Worth avoiding / caveats

### One binary, embedded JS is not Node

The JS layer runs on **goja**, a pure-Go ES5(+partial ES6) implementation — there is no `fetch`, `fs`, `buffer`, `window`, or any other Node/browser runtime API. Most npm packages that assume a Node or browser environment will not run inside a PocketBase hook. This is the direct cost of "single binary, zero dependencies": the extension language is intentionally sandboxed to what a pure-Go interpreter can execute, not a general-purpose JS runtime.

## Facts & figures

- 60+ documented lifecycle hooks (vendor docs, JSVM plugin).
- Embedded JS engine: goja, ES5.1 + partial ES6 (vendor docs).

## Sources

- [API rules and filters](https://pocketbase.io/docs/api-rules-and-filters/) · [API Settings](https://pocketbase.io/docs/api-settings/)
- [Extend with JavaScript — Overview](https://pocketbase.io/docs/js-overview/) · [Extend with JavaScript — Routing](https://pocketbase.io/docs/js-routing/) · [Extending PocketBase — framework](https://pocketbase.io/docs/use-as-framework/)
- [API Rules — blocking a specific field-change (discussion, `:changed` usage)](https://github.com/pocketbase/pocketbase/discussions/4208)
- **Not directly verified:** exact current count/list of lifecycle hooks against the latest release (60+ figure per DeepWiki secondary source, not cross-checked against changelog); full list of `:each`/`:lower` semantics beyond forum/discussion mentions.
