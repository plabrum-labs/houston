# App builders

**What this category is:** low-code/no-code internal-tool builders (Retool, Superblocks, Appsmith, Budibase, ToolJet) and backend-as-a-service / data-API layers (Supabase, Convex, Firebase, PocketBase, Appwrite, Hasura, PostGraphile, PostgREST, Directus, Strapi). Two different jobs — "build a UI over data" and "expose data as an API" — bundled into one category because Houston sits across both.
**Why it's in this research:** app-builder (deploy/migration format, override points), semantic layer, enterprise governance (permissions), agent (AI-assisted editing).
**Files:** 15.

## The players

| Company | What it is | Depth |
|---|---|---|
| [retool](retool.md) | Drag-drop internal-tools builder; reference implementation for source-control format and AI-assisted editing | deep |
| [supabase](supabase.md) | Postgres BaaS — auth/storage/realtime/functions layered on one Postgres instance, RLS-gated | medium |
| [convex](convex.md) | Reactive app database; all client access through typed server functions, no client-exposed DB | medium |
| [firebase](firebase.md) | Google's mobile/web BaaS; client-evaluated Security Rules language | medium |
| [pocketbase](pocketbase.md) | Single-binary self-hosted BaaS with a declarative per-collection rules language | medium |
| [hasura](hasura.md) | Auto-generated GraphQL over a DB schema, with a granular declarative permission layer | medium |
| [directus](directus.md) | Headless CMS/data layer; one filter AST reused for query, permission, condition, and validation | medium |
| [strapi](strapi.md) | Headless CMS with a layered policy/middleware/hook customization system | medium |
| [superblocks](superblocks.md) | Retool competitor; rebuilt its runtime as real React specifically to make AI (Clark) and human edits both tractable | thin |
| [appsmith](appsmith.md) | Open-source internal-tools builder; per-resource git diffs as an alternate path to reviewable source control | thin |
| [budibase](budibase.md) | Open-source internal-tools builder; 2026 roadmap bets on per-agent data/API scoping | thin |
| [tooljet](tooljet.md) | Open-source internal-tools builder; GitSync is the category's clearest anti-pattern (whole-file JSON) | thin |
| [appwrite](appwrite.md) | Self-hostable BaaS; permission model is additive-only (no deny primitive) | thin |
| [postgraphile](postgraphile.md) | Auto-generated GraphQL from Postgres introspection, extended via SQL comment metadata | thin |
| [postgrest](postgrest.md) | Auto-generated REST directly from Postgres catalogs; the schema and its grants *are* the API | thin |

**Reference implementations:** Retool for the app-builder half (source format, AI editing, resource/environment model); Supabase and Convex for the BaaS half, as the clearest contrast pair (client-exposed-DB-plus-RLS vs. server-function-only). Appsmith, Budibase, ToolJet, and PostgREST/PostGraphile are thin — single-pass docs research, no hands-on verification.

## Convergence

**Reviewable source format is an unforced convergence, not a coincidence.** Retool deprecated YAML for **Toolscript** specifically because an LLM needed something JSX-like to target and patch (`retool.md`). Superblocks went one step further and rebuilt its entire runtime as **real React+TypeScript** so Clark's output is a normal, IDE-openable codebase (`superblocks.md`). Appsmith reaches for the same goal — reviewable diffs — by a different route: **per-resource file decomposition** instead of a denser serialization (`appsmith.md`). Three independent products, three different mechanisms, one shared conclusion: **a single serialized blob (YAML or JSON) is not AI-editable or human-reviewable; the fix is either a code-shaped format or a file-per-resource layout.** ToolJet's GitSync is the load-bearing negative case — whole-file JSON replacement on every commit, git-shaped but not git-*useful* (`tooljet.md`).

**Row-level access and field/column-level access are consistently modeled as two independent, both-must-pass gates.** Hasura's `filter`/`check` split plus column presets that alter the generated input type per role, Directus's shared filter AST across query/permission/condition/validation, and Salesforce/ServiceNow/Power Platform's row-ACL-plus-field-ACL pattern (see `enterprise-platforms/README.md`) all land on the same two-axis shape independently. Appwrite is the counter-example: its collection/document permissions are **additive-only, OR together, with no restrict primitive** — a genuinely different (and worse) architecture (`appwrite.md`).

**RLS-off-by-default (or its equivalent) is a fail-open pattern multiple platforms ship and multiple platforms warn about.** Supabase's dashboard-created tables get RLS on by default; SQL/migration-created tables do not (`supabase.md`). This is the exact mechanism behind Lovable's CVE-2025-48757 (see `ai-builders/README.md`) — not a Lovable bug, a Supabase-default-plus-codegen interaction that also affects Bolt, v0, and Cursor+Supabase templates. Convex's founding argument (`convex.md`) is that this entire failure class is structural to any platform that exposes the database to the client at all — "RLS is a tax paid by client-oriented databases," patching an exposure instead of removing it. PocketBase independently arrives at a related but distinct fix: a **three-state default** (`null` = locked, `""` = public, expression = filtered) that at least makes "public" a deliberate choice distinct from "someone forgot" (`pocketbase.md`).

**Cross-entity permission checks are a scaling wall, regardless of where the check runs.** Firebase's `get()`/`exists()` cross-document rule lookups bill as reads even on rejected requests; Supabase's guidance is independently "minimize joins in RLS policies" for a different reason (Postgres planner cost). Two architecturally opposite systems — client-evaluated rules vs. server-side SQL policies — converge on the same operational advice (`firebase.md`).

**Declarative capability flags collapse into one composable vocabulary once they accumulate.** PostGraphile replaced a pile of separately-invented smart tags (`@omit`, `@sortable`, `@filterable`...) with one `@behavior +token -token` grammar in v5 (`postgraphile.md`). Directus's interface `types`/`localTypes` matching and Strapi's `pluginOptions` namespacing are adjacent instances of "capability as declarative data the platform reads, not a branch in platform code."

## Worth stealing

- **Toolscript / Enterprise React** — format the AI edits determines whether AI-editing works at all; see `retool.md`, `superblocks.md`.
- **PocketBase's three-state rule default** (`null`/`""`/expression) — makes "intentionally public" distinguishable from "nobody set a rule," see `pocketbase.md`.
- **Convex's query/mutation/action type split** — a type system for side effects; purity buys free retries, `fetch` is walled off into a non-retryable function kind, see `convex.md`.
- **Hasura's `filter` (pre) vs `check` (post) on updates** and **column presets that remove a field from the generated input type per role** — see `hasura.md`.
- **Directus's one filter AST for four surfaces** (query, permission, conditional visibility, validation) — see `directus.md`.
- **Strapi's policies-can-only-reject / middlewares-can-mutate split** — a security primitive enforced by the extension point's type, not convention — see `strapi.md`.
- **Firebase's local, automated unit-test SDK for Security Rules** — almost nothing else in this category has an equivalent test harness for permission logic itself, see `firebase.md`.
- **Named lifecycle hooks as the escape hatch (PocketBase, Strapi's Document Service middleware)** rather than "eject to custom code" — the override point stays inside the platform's own request lifecycle.

## Worth avoiding

- **ToolJet's GitSync**: whole-app-as-one-JSON-file, replaced wholesale on every commit — unreviewable, unmergeable, useless as LLM input. The category's cleanest anti-pattern (`tooljet.md`).
- **Appwrite's additive-only permissions**: no deny primitive means a defense-in-depth layer can only ever widen access, never restrict it (`appwrite.md`).
- **Retool's unversioned Modules**: every app embedding a module runs the *live* version, no per-app pin — any module edit is an unreviewable simultaneous breaking change everywhere it's used (`retool.md`).
- **Supabase Storage's fake folders**: pure key prefixes, no inherited-permission hierarchy — has to be rebuilt in a custom table every time (`supabase.md`).
- **Convex's `storage.getUrl()`**: capability-by-URL with no revocation short of deletion (`convex.md`).
- **PostGraphile's smart comments**: metadata living in `COMMENT ON` strings because Postgres has nowhere else to put it — invisible to tooling, no syntax validation, easy to lose track of (`postgraphile.md`).

## Gaps

- **No product in this survey has both** a reviewable AI-editable source format *and* a first-class permission-unit-test harness. Retool/Superblocks solved the former; Firebase solved the latter; nobody combines them.
- **Nobody has solved cross-entity permission checks at scale** — Firebase bills for them, Supabase's planner chokes on them, and the standard advice everywhere is "avoid joins in your policy," which is a workaround, not a fix.
- **The escape-hatch design question is unresolved category-wide**: PocketBase's named hooks and Directus/Strapi's policy/middleware split are principled; most competitors still offer only "eject to custom code," which forfeits the platform's own guarantees the moment it's used.

## Notes

- Depth varies sharply: Retool/Supabase/Convex/Firebase/PocketBase/Hasura/Directus/Strapi are medium-to-deep; Superblocks/Appsmith/Budibase/ToolJet/Appwrite/PostGraphile/PostgREST are thin, single-source-type research passes — treat their claims as directional, not verified.
- Budibase's 2026 multi-agent roadmap is vendor-forward-looking and explicitly unconfirmed as shipped.
- Appwrite's additive-permission finding is sourced from its "legacy" permissions doc plus community threads, not independently tested against a live instance — flagged as possibly stale if newer docs changed the model.
- Superblocks' Clark and its bidirectional visual↔code sync mechanics are vendor-reported/thin; the generalizable "sync constrains code to whatever the visual model can represent" critique is this research's own inference, not a confirmed Superblocks admission.
