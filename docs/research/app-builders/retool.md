# Retool

**What it is:** Low-code internal-tools builder (drag-drop UI + SQL/JS queries against connected resources), plus Workflows (backend automation) and Retool AI (in-product code/app generation).
**Axis:** app-builder, deploy/migration (source control format), agent (AI-assisted development), workflow.
**Depth:** medium — verified from Retool docs, engineering blog, and community forum; some internals (exact cache-key hashing, Temporal queue tuning) are third-party inference.

## Products & surfaces

| Product | What it is |
|---|---|
| **Retool Apps** | Drag-drop UI builder; queries against 50+ connectors; JS/Python transforms. |
| **Retool Workflows** | Backend automation DAGs (schedule/webhook/event triggers), orchestrated on Temporal. |
| **Query Library** | Named, parameterized, permissioned query artifacts shared org-wide, independent of any one app. |
| **Retool AI / AI-assisted development** | In-editor agent that edits apps by generating/patching Toolscript. |
| **Retool for External Apps** | Customer-facing (non-employee) apps: branded auth/error pages, usage-based billing. |
| **Modules** | Reusable component+query bundles embedded into multiple apps. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Toolscript (`.rsx`)** | JSX-style app serialization that replaced YAML for source control | yes |
| Toolscript omits defaults | Diffs shrink ~80% vs. YAML by not serializing default values | yes |
| Resource environments | One logical resource, env-scoped credentials; prod is undeletable | yes |
| Per-environment resource permissions | Grant view on staging data, deny on prod data, as a permission | yes |
| Query Library | Named, parameterized, permissioned query artifacts, reusable across apps | yes |
| Query caching keyed on inputs | Same query + same inputs within TTL → cached result, no resource hit | yes |
| Modules with no version pin | Every app embedding a module always runs its *live* version | no (cautionary) |
| Audit log query-parameter capture | Logs can include data returned from/sent to queries — PII exposure risk | no (cautionary) |
| Multiple schedule triggers per workflow | One workflow, several independent cron triggers | yes |
| Protected/API-key webhook triggers | Firing a workflow externally requires a key by default; can be made public | yes |
| Temporal-backed Workflows | Orchestration built on Temporal rather than a bespoke job queue | yes |
| AI sees schema, not rows | Retool AI edits apps using metadata/column types only, never actual records | yes |
| Selective schema fetch for AI context | System fetches only schemas relevant to the current edit, not the whole workspace | yes |
| Per-edit AI attribution in version history | Each AI-made change is tagged separately from human edits | yes |
| Permission cascade to generated apps | SSO/RBAC/row-level security apply to AI-generated apps automatically, no reconfiguration | yes |

## Worth stealing

### Toolscript replaced YAML because YAML wasn't reviewable

Retool's source control originally serialized apps to YAML. It has since been deprecated in favor of **Toolscript**, a JSX-style format (`main.rsx`, `functions.rsx`, `lib/`, positioning kept in separate JSON dotfiles) — "commits made by builders in Toolscript are functionally equivalent to YAML, with the exception that Toolscript omits default values to produce more readable diffs." Community and vendor accounts describe diffs shrinking roughly 80%. YAML serialization support is being removed entirely from self-hosted Retool (targeted Q2 2025 stable).

**The reason this mattered for AI, per Retool's own engineering post ("How we built AI-assisted development into Retool"):** Toolscript's JSX-like, nested, file-like structure "gave the LLM something familiar" — "LLMs understand code." The format lets the model target specific components/properties and patch them in place, and queries can reference library files so logic lives alongside structure. Retool explicitly frames the format choice as *why* AI editing worked, not an unrelated nicety adopted earlier for humans.

**Cautionary counterweight they don't emphasize but is implied by the tooling**: Toolscript has no linting or type-checking layer of its own — it's read/written by the app builder's internal model, and hand-editing it outside that path is unsupported and error-prone (per community forum guidance and the "Parsable format for RSX files as tsx" feature request, which exists precisely because users want tooling around a format that currently has none).

### Resource environments: one resource, env-scoped credentials, prod undeletable

A "resource" (e.g., a Postgres connection) is defined once; each environment (dev/staging/production, or custom ones on Business/Enterprise) attaches its own credentials to that same logical resource. A query written against staging runs unmodified against production — only the credential binding changes. **Production is a protected default environment and cannot be removed or renamed.** On Business/Enterprise, admins can set **per-environment resource permissions** — e.g., a user can view staging data but is denied production data — access control scoped to environment, not just to resource.

### Query Library — permissioned, parameterized, shared

Queries live outside any single app: private by default (creator-only read/write), optionally shared org-wide via Settings → Roles & Permissions. Parameters are declared with `{{ }}` interpolation and surfaced as typed inputs. Access to a shared query still requires access to the underlying resource — sharing the query doesn't bypass resource-level permission.

### Caching keyed on query inputs

Retool checks the resource-side cache before running a query: same query, same input values, within the configured TTL → cached result returned, no round-trip to the resource. For JS queries the cache key is derived from variables referenced in the script; for dynamic SQL, from the fully-rendered query text. Builders can override with a custom cache key computed in the query's Advanced section.

### Audit logs can leak PII — and Retool warns about it

Retool's own docs flag that audit logs, by default, can capture query parameters, request bodies, and returned data — i.e., turning on "View audit logs" access can hand a viewer visibility into records they'd otherwise never see through the app's UI. Mitigations: hide parameters per-query, or org-wide "Omit query content" in Settings → Advanced, which strips parameters/bodies/non-metadata fields from every logged event. Self-hosted instances additionally have `HIDE_ALL_HEADERS_IN_AUDIT_LOG_EVENTS`. The lesson: an audit trail that logs query I/O is itself a sensitive-data surface requiring its own access control, separate from the data source's.

### Workflows: multiple schedules per workflow, protected triggers, Temporal

- A single workflow can have **several independent schedule triggers** plus a webhook trigger, matching real-world cadences like "9am Mondays *and* 3am on the 1st" without forking the workflow.
- Webhook triggers require an API key by default (**protected**); an explicit "Public" toggle removes that requirement — who can fire a workflow externally is a first-class security setting, not an afterthought.
- Retool built Workflows on **Temporal** rather than a bespoke job queue/orchestrator. Temporal handles queueing, scheduling, and cross-block ordering guarantees, and (per Temporal's own case study with Retool) abstracts flaky external APIs and supports pausing mid-sequence pending external input.

### AI-assisted development: metadata-only context, tagged history, cascading permissions

From Retool's engineering post on AI-assisted development:
- **The model never sees actual records** — "it works with schemas, column names, and data types, not the records themselves."
- **Selective schema loading**: rather than dumping the whole workspace's object/schema graph into context (which "would" blow the context window), the system inspects the current edit target — the component being built, the table selected, an @-mentioned resource — and fetches only the relevant schema. This is described as necessary machinery, not an incidental optimization.
- **Every AI edit is separately tagged** in version history, distinguishable from human-authored changes, supporting compliance review and letting builders inspect the model's reasoning path.
- **Permissions cascade automatically**: apps the AI generates or edits inherit the org's existing SSO/RBAC/row-level security without separate configuration — the AI is not a privilege-escalation path.
- Design philosophy, stated directly: **"sensible defaults matter more than endless customization options."** Notable given Retool is among the most customizable products in this category — the AI layer is deliberately opinionated even though the underlying platform isn't.

### External Apps: branded, replaceable auth surface

Retool for External Apps lets you replace the platform's own login, reset-password, claim-invite, 403, and 404 pages with custom Retool-built pages, wired up via Settings → Branding. The auth/error chrome is itself a buildable app, not a fixed template.

## Worth avoiding

### Modules have no version selector

"Different apps cannot use different versions of the same module." Modules can be re-released, but every app embedding a module runs the *live* (latest) version — there is no per-app pin. Any module edit is a simultaneous, unreviewable-per-consumer breaking change to every app that uses it. This is the sharp edge of a shared-component system that has reuse but no dependency versioning.

### Client-side pagination degrades silently, then catastrophically

Per Retool's own partner content: client-side pagination (query returns all rows, browser slices pages) "works until it doesn't — and when it breaks, it breaks badly." Concretely: query time grows linearly with row count, the browser holds the full result set in memory, and any filter/sort re-processes everything client-side. Cited thresholds: noticeable lag at 10k rows, frozen tab at 100k, query timeout before data even arrives at 500k. Server-side pagination is framed as "the correct default for any internal tool operating on real production data," not a premature optimization.

## Facts & figures

- YAML source-control serialization removal targeted for Q2 2025 stable release (self-hosted).
- Toolscript diffs reported ~80% shorter than equivalent YAML (vendor/community-reported, not independently benchmarked).
- Workflows queue described by Temporal's case study as "write-heavy (~100:1 write:read)"; Aurora Serverless scales to absorb spikes (vendor-reported).

## Sources

- [Deprecation of YAML serialization in Source Control](https://docs.retool.com/changelog/yaml-serialization-deprecation)
- [How we built AI-assisted development into Retool](https://retool.com/blog/how-we-built-ai-assisted-development)
- [Configure resource environments](https://docs.retool.com/org-users/guides/configuration/environments)
- [Query Library](https://docs.retool.com/queries/concepts/query-library)
- [Query caching](https://docs.retool.com/queries/concepts/caching)
- [Trigger workflows periodically](https://docs.retool.com/workflows/guides/schedule)
- [Trigger workflows with webhooks](https://docs.retool.com/workflows/guides/webhooks)
- [Temporal Clusters for Self-hosted Retool](https://docs.retool.com/self-hosted/concepts/temporal)
- [How Retool built robust Workflow & Agents products on Temporal](https://temporal.io/resources/on-demand/how-retool-built-robust-workflow-agents-products)
- [Build modules to reuse queries and components](https://docs.retool.com/apps/guides/layout-structure/modules) + [forum: different apps cannot use different module versions](https://community.retool.com/t/specify-what-version-of-module-to-use/13906/16)
- [Server-Side Pagination in Retool & Supabase Tables](https://retoolers.io/blog-posts/using-server-side-pagination-in-queries-and-table-building) (partner content, not official docs — noted as such)
- [Build custom pages (External Apps)](https://docs.retool.com/apps/guides/app-management/external-apps/custom-pages)
- Audit log PII handling: [org-users audit logs guide](https://docs.retool.com/org-users/guides/audit-logs) (fetched via summarizer; exact quoted warning text not independently re-verified against raw HTML)
- **Not directly verified:** exact cache-key hashing algorithm; internal Temporal queue configuration details beyond the public case study.
