# Supabase

**What it is:** Postgres-based backend-as-a-service — auth, storage, realtime, edge functions, auto-generated REST/GraphQL, all layered on a single managed Postgres instance the developer can also reach directly.
**Axis:** semantic layer, deploy/migration, enterprise governance (permissions on the database).
**Depth:** medium — docs, GitHub discussions, and third-party security writeups; internals of Realtime's authorization pipeline are described by Supabase's own docs, not independently load-tested here.

## Products & surfaces

| Product | What it is |
|---|---|
| **Postgres database** | The core; every other product is a layer on top of one Postgres instance. |
| **Auth** | Users table (`auth.users`) plus `raw_user_meta_data`/`raw_app_meta_data`, JWT issuance. |
| **Storage** | Files, modeled as rows in `storage.objects`, access-controlled by the same RLS engine as any table. |
| **Realtime** | Postgres Changes (row-level change stream), Broadcast (pub/sub), Presence. |
| **Edge Functions** | Deno-based serverless functions. |
| **Branching** | Git-linked preview databases per PR/branch. |
| **Database Advisors** | Linter surfacing performance and security anti-patterns in the schema/policies. |
| **PostgREST** | Auto-generates the REST API from the schema (see also `postgrest.md`). |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Storage as a Postgres table | `storage.objects` is a normal table; storage permissions are RLS policies | yes |
| Preview branches start empty | Branching seeds from `seed.sql`, never copies production rows | yes |
| Database linter (advisors) | Flags `auth_rls_initplan`, `multiple_permissive_policies`, and more as lint rules | yes |
| Postgres Changes per-subscriber auth | Every change is authorization-checked against every subscriber | no (cautionary — scaling ceiling) |
| DELETE events unauthorized | Deletes can't be RLS-checked because the row is already gone | no (cautionary, structural) |
| Storage folders as key prefixes | No real folder hierarchy or inherited permissions; must be modeled manually | no (cautionary) |
| `raw_user_meta_data` vs `raw_app_meta_data` | One is user-writable, one is server-only; both land in the JWT | no (cautionary — easy to pick wrong) |
| RLS off by default on SQL/migration-created tables | Only Table-Editor-created tables get RLS on by default | no (cautionary) |

## Worth stealing

### Storage modeled as a table, not a separate subsystem

`storage.objects` (per-file metadata: `bucket_id`, `name`/`path_tokens`, JSON `metadata`, version info) and `storage.buckets` (bucket config: public/private, `file_size_limit`, `allowed_mime_types`) are ordinary Postgres tables. Access control for files is therefore **the same RLS policy language used for every other table** — no separate storage-permissions DSL. "If a user is able to `SELECT` from the `objects` table, they can retrieve the object too."

### Preview branches start with zero production data, deliberately

Branching creates a full schema copy with **no production rows** — stated as a data-protection choice, not a technical limitation. Seeding is explicit: a `./supabase/seed.sql` in the repo runs once, at branch creation, for both local dev and preview branches. There's a distinction between **persistent branches** (long-lived, can be configured to reseed) and **preview branches** (ephemeral, tied to a PR).

**Snaplet died; the ecosystem response is telling.** Snaplet (a dedicated seed-data-generation tool Supabase's docs pointed to) wound down as a company in 2024 and open-sourced its tooling into `@snaplet/seed`, now community-maintained under `supabase-community/seed` with sparse commit activity. Supabase's own current seeding docs suggest **piping seed generation through an LLM** (set `OPENAI_API_KEY`/`GROQ_API_KEY`, generate realistic text fields) rather than relying on the abandoned dedicated tool — a preview-data pipeline's tooling dependency evaporated and the replacement is "ask a model to fill it in," not a new maintained product.

### Database Advisors — the linter as a permissions/performance teacher

Supabase ships a **Performance Advisor** and **Security Advisor** that lint the live schema and policy set, not just static SQL. Concrete rules: `0003_auth_rls_initplan` flags RLS policies that call `auth.uid()` (or similar) unwrapped, forcing Postgres to re-evaluate the function per row instead of once per statement — fix is wrapping in a subquery, `(select auth.uid())`, which lets the planner cache it as an initPlan. `0006_multiple_permissive_policies` flags multiple permissive policies on the same table/role/action, which combine via **OR** — redundant-looking policies can silently widen access beyond what any single policy intends. Both are shipped as **advisory lint output surfaced in the dashboard**, not merely a docs warning — the linter runs against your actual policies, continuously.

### Realtime's Postgres Changes: the authorization model and its ceiling

**Every row change is authorization-checked against every subscriber individually** — one change fanned out to 100 subscribed clients means 100 separate authorization checks, not one. Changes are processed **single-threaded to preserve ordering**, so bigger compute doesn't raise Postgres Changes throughput. Supabase's own guidance: above roughly **3,000 concurrent subscribers on the same change stream**, switch to **Broadcast** (a pub/sub primitive without per-subscriber row-level authorization). At extreme scale this authorization model is reported to collapse toward **0.05–0.1 DB changes/sec** effective throughput (per Supabase's benchmarks docs). This is a clean example of a security-correct design (never send a row to a client unauthorized to see it) that has a hard architectural ceiling baked into the same mechanism that makes it correct.

**DELETE events are structurally exempt from the authorization check** — because the row no longer exists at delete time, Postgres has nothing left to evaluate the RLS policy against. Supabase's stated mitigation is to recursively check RLS on related/foreign tables where possible, but the core gap (a delete can't be policy-checked the same way an insert/update can) is unfixable within this architecture, not a bug to be patched.

## Worth avoiding

### Storage folders are fake — hierarchical permissions require your own table

"Folders" in Supabase Storage are pure key prefixes (like S3). There is no inherited-permission folder tree. Supabase's own troubleshooting docs are explicit: to get folder-level access control, you must model the hierarchy yourself in a custom Postgres table (folder id, parent id, path, permissions), reference `storage.objects` from it, and write RLS policies on `storage.objects` that **join** against your custom table. The abstraction ("folder") that users expect from every filesystem-shaped UI does not exist at the storage layer — it has to be rebuilt in the schema layer, every time, by every app.

### Two metadata fields, one obviously wrong choice, no guardrail

`raw_user_meta_data` is writable by the authenticated user via `auth.update()`. `raw_app_meta_data` requires admin/server-side access to write. **Both are serialized into the JWT.** Nothing in the client SDK or the type system stops a developer from storing a role or a pricing tier in `raw_user_meta_data` — the field that the user holding the JWT can edit themselves. This is purely a naming/documentation-level guardrail, not an enforced one: the platform gives you two boxes that look interchangeable and only one is safe for authorization data.

### RLS-off-by-default outside the dashboard, plus auto-exposure

Every table in the `public` schema is reachable through the auto-generated PostgREST API using the `anon` key, which ships in the browser bundle by design. Tables created via the **dashboard Table Editor get RLS enabled by default**; tables created via **raw SQL, migrations, or an ORM do not** — the developer must remember `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` explicitly. Combined with `public`-schema auto-exposure via PostgREST, the result is a fail-open default in exactly the workflow (SQL/migrations) that experienced developers are most likely to use once they graduate past the dashboard. (This combination — RLS off + auto-publish to the API — is the structural precondition cited in the CVE context covered separately in `lovable.md`.)

## Facts & figures

- Preview branch auto-expiry / seed timing: seed runs once, at creation, for persistent branches configurable to reseed (vendor docs).
- Postgres Changes scaling: ~3,000 concurrent subscribers cited as the practical ceiling before Supabase recommends Broadcast; extreme-scale throughput cited as collapsing to ~0.05–0.1 DB changes/sec (Supabase benchmarks docs — vendor-reported, not independently reproduced here).
- `@snaplet/seed` / `supabase-community/seed`: limited maintainer activity since ~mid-2024 per community reporting; original Snaplet docs site is offline (accessible only via Wayback Machine per community reports).

## Sources

- [Branching](https://supabase.com/docs/guides/deployment/branching) · [Working with branches](https://supabase.com/docs/guides/deployment/branching/working-with-branches)
- [Seeding your database](https://supabase.com/docs/guides/local-development/seeding-your-database) · [Snaplet is now open source](https://supabase.com/blog/snaplet-is-now-open-source) · [supabase-community/seed](https://github.com/supabase-community/seed)
- [Performance and Security Advisors](https://supabase.com/docs/guides/database/database-advisors?lint=0003_auth_rls_initplan)
- [Postgres Changes](https://supabase.com/docs/guides/realtime/postgres-changes) · [Realtime Benchmarks](https://supabase.com/docs/guides/realtime/benchmarks) · [Realtime Limits](https://supabase.com/docs/guides/realtime/limits)
- [Storage: inefficient folder operations and hierarchical RLS challenges](https://supabase.com/docs/guides/troubleshooting/supabase-storage-inefficient-folder-operations-and-hierarchical-rls-challenges-b05a4d) · [The Storage Schema](https://supabase.com/docs/guides/storage/schema/design) · [Storage Access Control](https://supabase.com/docs/guides/storage/security/access-control)
- [User Management (raw_user_meta_data / raw_app_meta_data)](https://supabase.com/docs/guides/auth/managing-user-data)
- [Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security) · [Enable RLS by default on all new tables (discussion)](https://github.com/orgs/supabase/discussions/21747)
- [Realtime delete event discussion](https://github.com/orgs/supabase/discussions/12471)
- **Not directly verified:** exact throughput collapse figures at extreme scale (taken from Supabase's own benchmarks page, not independently reproduced); current maintenance status of `supabase-community/seed` beyond community reports.
