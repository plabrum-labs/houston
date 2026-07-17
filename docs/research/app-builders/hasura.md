# Hasura

**What it is:** Instant GraphQL (and now, in DDN, a broader supergraph) API generated from a database schema, with a declarative row/column permission layer and custom-logic escape hatches (Actions) that stay joinable to the generated graph.
**Axis:** semantic layer, enterprise governance.
**Depth:** medium — official docs across Hasura v2 (GraphQL Engine) and v3 (DDN); no independent load-testing.

## Products & surfaces

| Product | What it is |
|---|---|
| **Hasura GraphQL Engine (v2)** | Auto-generated CRUD+subscriptions GraphQL API over Postgres/other sources, with a permission system per role/table/action. |
| **Actions** | Custom-logic GraphQL fields backed by an HTTP endpoint you write, joinable back into the generated graph via Action Relationships. |
| **Remote Relationships / Remote Joins** | Declarative joins across tables, actions, and remote GraphQL/REST services. |
| **Hasura DDN (v3)** | Supergraph/metadata-first architecture; relationships can cross data sources/subgraphs without physical FKs. |
| **Inherited Roles** | Roles composed from other roles' permission sets. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| `filter` vs `check` on UpdatePermission | Pre-condition (which rows are editable) vs post-condition (what the edited row must satisfy) | yes |
| `query_root_fields`/`subscription_root_fields` | Make a table reachable only as a nested relationship, never a top-level query | yes |
| `allow_aggregations: false` by default | Aggregation queries (`avg`, `sum`, etc.) require explicit opt-in per role/table | yes |
| Column presets | Server-injects a column value (e.g. `author_id` from a session variable) and removes that column from the role's input type | yes |
| Inherited roles | A role's permission set can compose from multiple other roles | yes |
| Action Relationships | A custom endpoint's response fields can be joined back to real DB tables in the generated graph | yes |
| Computed fields in SelectPermission | Computed (derived) fields are gated by the same select-permission system as real columns, and can be aggregated | yes |
| DDN relationships without FKs, cross-source | Relationships are metadata, not requiring a physical foreign key or even the same underlying data source | yes |

## Worth stealing

### `filter` (pre) vs `check` (post) on updates

Hasura's UpdatePermission has two separable conditions: **`filter`** determines *which rows* a role may even attempt to update (e.g., `author_id` must equal the caller's `X-Hasura-User-Id`), while **`check`** is evaluated *after* the hypothetical update and must also hold (e.g., the row's `author_id` must *still* equal the caller's id, or `content` must not be empty). Exposing both — not just one generic "permission" — is what lets you express *"you may edit your own row, but you may not reassign it away from yourself (or to someone else)."* A single filter can't distinguish "can touch this row" from "can leave the row in this state."

### Root-field visibility: reachable only through a relationship

`query_root_fields` / `subscription_root_fields` on a role's SelectPermission can be set to an explicit (possibly empty) list of allowed top-level entry points. Setting both to empty for a role means that role **cannot list the table directly at all** — but if a *relationship* into that table exists from another table the role can query, **the role can still reach individual rows through the relationship** (Hasura's own docs flag this as something to keep in mind, not a hidden bug). The pattern this enables: *"you can't list all users, but you can see the author of a post you're already allowed to read"* — visibility scoped to the traversal path, not the table.

### `allow_aggregations` off by default

Aggregation fields (`avg`, `sum`, `min`, `max`, `count` across a filtered set) are **not exposed by default** for a role's SelectPermission — must be explicitly turned on with `allow_aggregations: true`. The reason this matters as a default, not just a toggle: an aggregate computed over a row-filtered set that only shows the *caller's own* row still leaks the aggregate across the *whole* underlying set unless the aggregation is itself subject to the same row filter — `avg(salary)` computed under a "you can only see your own row" filter is either meaningless (aggregate of one row) or, if misconfigured, a leak of the org-wide average through a field that looks properly scoped. Making this opt-in per role/table is a deliberate friction against an easy-to-miss class of leak.

### Column presets change the generated input type, not just the runtime value

A column preset (e.g., `set: {author_id: "x-hasura-user-id"}` on InsertPermission) does two things simultaneously: it injects the value server-side from a session variable *and* **removes that column from the generated GraphQL input type for that role** — the client literally cannot pass `author_id` in the mutation; the field doesn't exist in their schema. The corollary worth generalizing: **the generated input type is role-dependent, not just the generated output type.** Most permission systems only vary what you can *read* per role; Hasura also varies the shape of what you're allowed to *write*, which closes off an entire class of "client passed a value the preset was supposed to override" bugs at the type level instead of the validation level.

### Actions whose results rejoin the graph

An Action (custom business logic behind an HTTP endpoint you write) can declare an **Action Relationship** back into a real table — e.g. a `createUser` action's response includes an `id`, and Hasura joins that response object to the `users` table on that id, so a single GraphQL query can traverse from the custom-logic result straight into ordinary database relationships. Hasura's remote-join execution avoids the N+1 trap by batching: query the custom/remote side first, collect the join keys, then query the target table filtered by those keys as one batched second query. **This is what keeps custom code inside the data model instead of beside it** — the client doesn't need to know which fields came from a database column and which came from an HTTP call; both are just fields in the same graph.

### Computed fields participate in permissions and aggregation

Computed fields (derived from a Postgres function) are governed by the same SelectPermission column-allowlist as physical columns — a role either can or can't see a given computed field, same as a real one. As of Hasura v2.27 (Postgres), computed fields with comparable/numeric return types can also be **aggregated** (min/max for comparable types, avg/sum/etc. for numeric), subject to the same `allow_aggregations` gate above.

### DDN relationships don't need foreign keys or a shared data source

In Hasura DDN, relationships are declared in metadata and explicitly **"do not need to be related in the data source by, for example, a foreign key"** and **"do not need to be backed by the same data source."** A relationship can connect a Postgres model to a Mongo model, or to a model backed by a REST connector, purely by declaring the join keys in metadata — the physical schema is not the source of truth for what's related, the metadata layer is.

## Facts & figures

- `allow_aggregations` default: `false` (confirmed by absence of a default-true example in any official doc; every docs example sets it explicitly when desired).
- Root field visibility (`query_root_fields`/`subscription_root_fields`) supported from Hasura v2.8.0 onward.
- Computed-field aggregation support: Hasura v2.27+ for Postgres sources.

## Sources

- [Configure Row Permissions](https://hasura.io/docs/2.0/auth/authorization/permissions/row-level-permissions/) · [Permissions Examples](https://hasura.io/docs/2.0/auth/authorization/permissions/common-roles-auth-examples/)
- [Root Field Visibility](https://hasura.io/docs/2.0/auth/authorization/permissions/disabling-root-fields/) · [Disable GraphQL Query and Subscription Root Fields Selectively with RBAC](https://hasura.io/blog/disable-query-subscription-root-fields-in-hasura)
- [Aggregation permissions](https://hasura.io/docs/2.0/auth/authorization/permissions/aggregation-permissions/) · [Introducing Aggregation Queries for Computed Fields](https://hasura.io/blog/introducing-aggregation-queries-for-computed-fields)
- [Column Presets](https://hasura.io/docs/2.0/auth/authorization/permissions/column-presets/) · [Postgres: Setting Values for Fields Using Role-Based Column Presets](https://hasura.io/docs/2.0/schema/postgres/default-values/column-presets/)
- [Inherited Roles](https://hasura.io/docs/2.0/auth/authorization/inherited-roles/)
- [Action Relationships](https://hasura.io/docs/2.0/actions/action-relationships/) · [Postgres: Action to Database Relationships](https://hasura.io/docs/2.0/schema/postgres/remote-relationships/action-relationships/) · [Supercharge app development with Hasura Remote Joins and Data Federation](https://hasura.io/blog/supercharge-your-application-development-with-hasura-remote-joins-and-data-federation)
- [Relationships (DDN)](https://hasura.io/docs/3.0/reference/metadata-reference/relationships/) · [Relationships Connect Data (DDN)](https://hasura.io/docs/3.0/data-modeling/relationship/)
- **Not directly verified:** exact wording/version of the "role can still reach a table through a relationship even with root fields disabled" caveat — paraphrased from search summary, not the raw doc page.
